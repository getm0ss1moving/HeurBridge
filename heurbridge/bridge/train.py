"""Bridge loss, optimization and validation (tasks T3.5, T3.6).

Loss (v1.1 corrected stochastic interpolant):
  x_tau = (1-tau) x0 + tau x1 + sigma tau(1-tau) eps,   u = x1 - x0 + sigma (1-2tau) eps
  L = E[ w * sum_i a_i ||v(x_tau,tau) - u||^2 / sum_i a_i ] + lam_ov * E[Overlap(x1_hat)],
  x1_hat = x_tau + (1-tau) v,  Overlap = pairwise macro overlap / total movable macro area
  (movable-movable and movable-fixed), in normalized units.
Optimizer: AdamW (lr 2e-4; 1e-4 when fine-tuning), wd 0.01, cosine schedule with warm-up,
grad clip 1.0, bf16 autocast on CUDA, EMA 0.999 (validation uses EMA weights).
Batches hold ``batch`` pairs of one design, so the graph is shared inside a batch.
Validation (every ``val_every`` steps): (1) velocity residual on a fixed tau/eps grid,
(2) terminal error of Euler_K(x^h) to the matched elite, (3) the guarded post-projection
cost from ``evaluator`` (the model-selection criterion), (4) the guard's alpha histogram.
Early stopping when (3) has not improved for ``patience`` validations.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import torch

from .data import PairSet, augment_graph, random_augmentation, transform_positions
from .graph import KIND_FIX, KIND_MOV
from .model import BridgeConfig, BridgeNet


@dataclass
class TrainConfig:
    steps: int = 20000
    batch: int = 32
    lr: float = 2e-4
    weight_decay: float = 0.01
    warmup: int = 1000
    grad_clip: float = 1.0
    ema: float = 0.999
    sigma: float = 0.01
    tau_dist: str = "logit_normal"     # or "uniform"
    lam_ov: float = 0.1
    bf16: bool = True
    val_every: int = 2000
    patience: int = 5
    seed: int = 0
    dihedral: bool = True
    aspect: float = 0.05
    K: int = 20
    val_pairs: int = 32
    device: str = "cuda" if torch.cuda.is_available() else "cpu"


def sample_tau(B: int, dist: str, gen: torch.Generator, device) -> torch.Tensor:
    if dist == "uniform":
        return torch.rand(B, generator=gen, device="cpu").to(device)
    return torch.sigmoid(torch.randn(B, generator=gen, device="cpu")).to(device)


def macro_overlap(x: torch.Tensor, gt: dict) -> torch.Tensor:
    """(B,) pairwise overlap area of movable macros (with each other and with fixed macros) / movable macro area."""
    kind = gt["kind"]
    mi = torch.nonzero(kind == KIND_MOV).flatten()
    if mi.numel() == 0:
        return x.new_zeros(x.shape[0])
    fi = torch.nonzero(kind == KIND_FIX).flatten()
    size = gt["size"].to(x.dtype)
    hm = size[mi] / 2
    c = x[:, mi]

    def ov(c1, h1, c2, h2):
        dx = torch.minimum(h1[:, 0].view(1, -1, 1) + h2[:, 0].view(1, 1, -1) - (c1[..., 0:1] - c2[..., 0].unsqueeze(1)).abs(),
                           2 * torch.minimum(h1[:, 0].view(1, -1, 1), h2[:, 0].view(1, 1, -1)))
        dy = torch.minimum(h1[:, 1].view(1, -1, 1) + h2[:, 1].view(1, 1, -1) - (c1[..., 1:2] - c2[..., 1].unsqueeze(1)).abs(),
                           2 * torch.minimum(h1[:, 1].view(1, -1, 1), h2[:, 1].view(1, 1, -1)))
        return torch.relu(dx) * torch.relu(dy)

    a = ov(c, hm, c, hm)
    n = mi.numel()
    tri = torch.triu(torch.ones(n, n, device=x.device, dtype=x.dtype), diagonal=1)
    total = (a * tri).sum((1, 2))
    if fi.numel():
        total = total + ov(c, hm, x[:, fi], size[fi] / 2).sum((1, 2))
    area = (size[mi, 0] * size[mi, 1]).sum().clamp_min(1e-12)
    return total / area


def bridge_loss(model: BridgeNet, gt: dict, x0: torch.Tensor, x1: torch.Tensor, w: torch.Tensor, cfg: TrainConfig,
                gen: torch.Generator, tau: torch.Tensor | None = None, eps: torch.Tensor | None = None) -> tuple:
    B = x0.shape[0]
    mov = gt["movable"].view(1, -1, 1)
    if tau is None:
        tau = sample_tau(B, cfg.tau_dist, gen, x0.device)
    if eps is None:
        eps = torch.randn(x0.shape, generator=gen, device="cpu").to(x0.device)
    eps = eps * mov
    t = tau.view(B, 1, 1)
    xt = (1 - t) * x0 + t * x1 + cfg.sigma * t * (1 - t) * eps
    ut = x1 - x0 + cfg.sigma * (1 - 2 * t) * eps
    v = model(xt, tau, gt, xh=x0).float()
    a = gt["area_w"].view(1, -1)
    fm = (a * ((v - ut) ** 2).sum(-1)).sum(-1) / a.sum().clamp_min(1e-12)       # (B,)
    loss_fm = (w * fm).mean()
    loss = loss_fm
    ov = torch.zeros((), device=x0.device)
    if cfg.lam_ov:
        x1_hat = xt + (1 - t) * v
        ov = macro_overlap(x1_hat, gt).mean()
        loss = loss + cfg.lam_ov * ov
    return loss, {"fm": float(loss_fm.detach()), "ov": float(ov.detach()), "fm_raw": fm.detach()}


@torch.no_grad()
def integrate(model: BridgeNet, gt: dict, xh: torch.Tensor, K: int = 20, method: str = "euler") -> torch.Tensor:
    """Euler (default) or Heun integration of dx/dtau = v from tau=0 to 1."""
    x = xh.clone()
    B = xh.shape[0]
    for k in range(K):
        tau = torch.full((B,), k / K, device=xh.device)
        v = model(x, tau, gt, xh=xh).float()
        if method == "heun":
            xp = x + v / K
            v2 = model(xp, torch.full((B,), (k + 1) / K, device=xh.device), gt, xh=xh).float()
            x = x + 0.5 * (v + v2) / K
        else:
            x = x + v / K
    return x


class EMA:
    def __init__(self, model: torch.nn.Module, decay: float):
        self.decay = decay
        self.shadow = copy.deepcopy(model).eval()
        for p in self.shadow.parameters():
            p.requires_grad_(False)

    @torch.no_grad()
    def update(self, model: torch.nn.Module):
        for s, p in zip(self.shadow.parameters(), model.parameters()):
            s.mul_(self.decay).add_(p.detach(), alpha=1 - self.decay)
        for s, b in zip(self.shadow.buffers(), model.buffers()):
            s.copy_(b)


def lr_at(step: int, cfg: TrainConfig) -> float:
    if step < cfg.warmup:
        return cfg.lr * (step + 1) / cfg.warmup
    p = (step - cfg.warmup) / max(1, cfg.steps - cfg.warmup)
    return cfg.lr * 0.5 * (1 + math.cos(math.pi * min(1.0, p)))


def file_sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class History:
    steps: list = field(default_factory=list)
    train: list = field(default_factory=list)
    val: list = field(default_factory=list)


class Trainer:
    """Trains a BridgeNet on PairSets (one per design); ``evaluator(ema_model, val_sets) -> dict`` must
    return {"criterion": float (lower is better), "alpha_hist": {...}, ...} (guarded post-projection cost)."""

    def __init__(self, model: BridgeNet, cfg: TrainConfig, train_sets: list, val_sets: list | None = None,
                 evaluator=None, out_dir: str | Path | None = None, log=print):
        self.model, self.cfg = model.to(cfg.device), cfg
        self.train_sets = [s for s in train_sets if len(s)]
        self.val_sets = [s for s in (val_sets or []) if len(s)]
        self.evaluator, self.log = evaluator, log
        self.out = Path(out_dir) if out_dir else None
        self.opt = torch.optim.AdamW(self.model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
        self.ema = EMA(self.model, cfg.ema)
        self.gen = torch.Generator().manual_seed(cfg.seed)
        self.rng = np.random.default_rng(cfg.seed)
        self._gt = [s.graph.tensors(cfg.device) for s in self.train_sets]
        self._gt_val = [s.graph.tensors(cfg.device) for s in self.val_sets]
        self.hist = History()
        self.best = (math.inf, None)

    def _batch(self):
        sizes = np.array([len(s) for s in self.train_sets], float)
        i = int(self.rng.choice(len(sizes), p=sizes / sizes.sum()))
        s = self.train_sets[i]
        idx = self.rng.integers(0, len(s), size=self.cfg.batch)
        dev = self.cfg.device
        x0 = torch.as_tensor(s.x0[idx], device=dev)
        x1 = torch.as_tensor(s.x1[idx], device=dev)
        w = torch.as_tensor(s.weight[idx], device=dev)
        gt = self._gt[i]
        if self.cfg.dihedral or self.cfg.aspect:
            k, sc = random_augmentation(self.rng, self.cfg.dihedral, self.cfg.aspect)
            gt = augment_graph(gt, k, sc)
            x0, x1 = transform_positions(x0, k), transform_positions(x1, k)
        return gt, x0, x1, w

    def step(self, it: int) -> dict:
        cfg = self.cfg
        self.model.train()
        for gparam in self.opt.param_groups:
            gparam["lr"] = lr_at(it, cfg)
        gt, x0, x1, w = self._batch()
        use_bf16 = cfg.bf16 and cfg.device.startswith("cuda")
        with torch.autocast(device_type="cuda" if cfg.device.startswith("cuda") else "cpu", dtype=torch.bfloat16,
                            enabled=use_bf16):
            loss, parts = bridge_loss(self.model, gt, x0, x1, w, cfg, self.gen)
        self.opt.zero_grad(set_to_none=True)
        loss.backward()
        gn = torch.nn.utils.clip_grad_norm_(self.model.parameters(), cfg.grad_clip)
        self.opt.step()
        self.ema.update(self.model)
        return {"loss": float(loss.detach()), "fm": parts["fm"], "ov": parts["ov"], "grad_norm": float(gn)}

    @torch.no_grad()
    def validate(self) -> dict:
        m = self.ema.shadow
        out = {"residual": [], "terminal": []}
        g = torch.Generator().manual_seed(1234)
        for s, gt in zip(self.val_sets, self._gt_val):
            n = min(len(s), self.cfg.val_pairs)
            x0 = torch.as_tensor(s.x0[:n], device=self.cfg.device)
            x1 = torch.as_tensor(s.x1[:n], device=self.cfg.device)
            w = torch.ones(n, device=self.cfg.device)
            res = []
            for tv in (0.1, 0.3, 0.5, 0.7, 0.9):
                tau = torch.full((n,), tv, device=self.cfg.device)
                eps = torch.randn(x0.shape, generator=g).to(self.cfg.device)
                cfg0 = copy.copy(self.cfg)
                cfg0.lam_ov = 0.0
                _, parts = bridge_loss(m, gt, x0, x1, w, cfg0, g, tau=tau, eps=eps)
                res.append(parts["fm"])
            out["residual"].append(float(np.mean(res)))
            xe = integrate(m, gt, x0, K=self.cfg.K)
            a = gt["area_w"].view(1, -1)
            term = torch.sqrt((a * ((xe - x1) ** 2).sum(-1)).sum(-1) / a.sum()).mean()
            out["terminal"].append(float(term))
        res = {"residual": float(np.mean(out["residual"])) if out["residual"] else math.nan,
               "terminal": float(np.mean(out["terminal"])) if out["terminal"] else math.nan}
        if self.evaluator is not None:
            res.update(self.evaluator(m, self.val_sets))
        res.setdefault("criterion", res["terminal"])
        return res

    def save(self, path: str | Path, extra: dict | None = None) -> str:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({"model": self.model.state_dict(), "ema": self.ema.shadow.state_dict(),
                    "model_config": self.model.export_config(), "train_config": asdict(self.cfg),
                    "history": asdict(self.hist), "extra": extra or {}}, path)
        return file_sha256(path)

    def fit(self, start_step: int = 0) -> dict:
        cfg = self.cfg
        bad, t0 = 0, time.time()
        run = []
        for it in range(start_step, cfg.steps):
            run.append(self.step(it))
            if (it + 1) % cfg.val_every == 0 or it + 1 == cfg.steps:
                tr = {k: float(np.mean([r[k] for r in run])) for k in run[0]}
                run = []
                val = self.validate() if self.val_sets else {"criterion": tr["loss"]}
                self.hist.steps.append(it + 1)
                self.hist.train.append(tr)
                self.hist.val.append(val)
                self.log(json.dumps({"step": it + 1, "train": tr, "val": {k: v for k, v in val.items() if not isinstance(v, (list, dict))},
                                     "elapsed_s": round(time.time() - t0, 1)}))
                if val["criterion"] < self.best[0] - 1e-9:
                    self.best = (val["criterion"], copy.deepcopy(self.ema.shadow.state_dict()))
                    bad = 0
                    if self.out:
                        self.save(self.out / "best.pt", {"step": it + 1, "val": val})
                else:
                    bad += 1
                    if bad >= cfg.patience:
                        self.log(json.dumps({"early_stop": it + 1, "best": self.best[0]}))
                        break
        if self.best[1] is not None:
            self.ema.shadow.load_state_dict(self.best[1])
        return {"best": self.best[0], "steps": self.hist.steps[-1] if self.hist.steps else 0}


def load_bridge(path: str | Path, device: str = "cpu", use_ema: bool = True) -> BridgeNet:
    z = torch.load(path, map_location=device, weights_only=False)
    m = BridgeNet(BridgeConfig(**z["model_config"]))
    m.load_state_dict(z["ema" if use_ema else "model"])
    return m.to(device).eval()
