#!/usr/bin/env python3
"""T3.4 warm start: noise -> layout flow matching on synthetic circuits (ChipDiffusion-style data).

  python scripts/pretrain_bridge.py --steps 200000 --batch 64 --stage1 100000:200 --stage2 5000:1000 \
      --device cuda --out checkpoints/pretrain_small

Data: synthetic circuits generated on the fly by worker processes (heurbridge.core.synth): stage 1
circuits of ~200 objects, stage 2 of ~1000 (the last 25% of steps).  Cells are clustered (8 cells per
cluster) as in the macro-stage graph.  Source x0 = uniform on the canvas for movable nodes (FlowPlace's
choice); target = the circuit's hidden layout.  One circuit per step, ``batch`` noise draws (graph shared).
Same loss as the bridge (sigma, overlap penalty).  The model is the bridge backbone (use_source=False).
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, IterableDataset

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heurbridge.bridge.graph import build_graph  # noqa: E402
from heurbridge.bridge.model import BridgeConfig, BridgeNet  # noqa: E402
from heurbridge.bridge.train import EMA, TrainConfig, bridge_loss, file_sha256, integrate, lr_at  # noqa: E402
from heurbridge.core import synth  # noqa: E402
from heurbridge.heuristics.cell.cluster import cluster_cells  # noqa: E402


def circuit(seed: int, n_obj: int):
    rng = np.random.default_rng(seed)
    n_macros = int(rng.integers(max(2, n_obj // 40), max(3, n_obj // 10)))
    n_io = int(rng.integers(8, max(9, n_obj // 10)))
    n_cells = max(8, n_obj - n_macros - n_io)
    des, ref = synth.make_design(seed=seed, n_macros=n_macros, n_cells=n_cells, n_io=n_io,
                                 macro_frac=(0.04, 0.16), same_size_groups=int(rng.integers(0, 3)),
                                 locality=float(rng.uniform(0.05, 0.15)))
    cl = cluster_cells(des, n=max(4, n_cells // 8), seed=0)
    g = build_graph(des, ref, cl)
    x1 = g.node_positions(ref)
    return g, x1.astype(np.float32)


class Circuits(IterableDataset):
    def __init__(self, base_seed: int, n_circuits: int, n_obj: int):
        self.base, self.n, self.n_obj = base_seed, n_circuits, n_obj

    def __iter__(self):
        info = torch.utils.data.get_worker_info()
        wid, nw = (info.id, info.num_workers) if info else (0, 1)
        rng = np.random.default_rng(self.base + 7919 * wid)
        while True:
            seed = self.base + int(rng.integers(0, self.n))
            g, x1 = circuit(seed, self.n_obj)
            yield g, x1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=200000)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--stage1", default="100000:200")
    ap.add_argument("--stage2", default="5000:1000")
    ap.add_argument("--model", default="small", choices=["small", "base"])
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--out", default=str(ROOT / "checkpoints" / "pretrain_small"))
    ap.add_argument("--log-every", type=int, default=500)
    ap.add_argument("--save-every", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    n1, o1 = map(int, a.stage1.split(":"))
    n2, o2 = map(int, a.stage2.split(":"))
    cfg = TrainConfig(steps=a.steps, batch=a.batch, lr=a.lr, device=a.device, warmup=min(1000, a.steps // 10),
                      tau_dist="logit_normal", sigma=0.01, lam_ov=0.1)
    torch.manual_seed(a.seed)
    model = BridgeNet(BridgeConfig.small() if a.model == "small" else BridgeConfig.base()).to(a.device)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=cfg.weight_decay)
    ema = EMA(model, cfg.ema)
    gen = torch.Generator().manual_seed(a.seed)
    rng = np.random.default_rng(a.seed)
    switch = int(0.75 * a.steps)
    loaders = {1: iter(DataLoader(Circuits(10_000_000, n1, o1), batch_size=None, num_workers=a.workers)),
               2: iter(DataLoader(Circuits(20_000_000, n2, o2), batch_size=None, num_workers=a.workers))}
    logf = open(out / "pretrain.log", "a")
    t0, run = time.time(), []
    use_bf16 = a.device.startswith("cuda")
    for it in range(a.steps):
        g, x1 = next(loaders[1 if it < switch else 2])
        gt = g.tensors(a.device)
        X1 = torch.as_tensor(x1, device=a.device).unsqueeze(0).repeat(a.batch, 1, 1)
        X0 = X1.clone()
        mov = torch.as_tensor(g.movable, device=a.device)
        noise = torch.as_tensor(rng.uniform(0.02, 0.98, (a.batch, int(mov.sum()), 2)), dtype=torch.float32, device=a.device)
        X0[:, mov] = noise
        for pg in opt.param_groups:
            pg["lr"] = lr_at(it, cfg)
        with torch.autocast(device_type="cuda" if use_bf16 else "cpu", dtype=torch.bfloat16, enabled=use_bf16):
            loss, parts = bridge_loss(model, gt, X0, X1, torch.ones(a.batch, device=a.device), cfg, gen)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
        opt.step()
        ema.update(model)
        run.append((float(loss), parts["fm"], parts["ov"]))
        if (it + 1) % a.log_every == 0:
            m = np.mean(run, 0)
            run = []
            s = json.dumps({"step": it + 1, "loss": float(m[0]), "fm": float(m[1]), "ov": float(m[2]),
                            "stage": 1 if it < switch else 2, "elapsed_s": round(time.time() - t0, 1)})
            print(s, flush=True)
            logf.write(s + "\n")
            logf.flush()
        if (it + 1) % a.save_every == 0 or it + 1 == a.steps:
            path = out / ("pretrain_%s.pt" % a.model)
            torch.save({"model": model.state_dict(), "ema": ema.shadow.state_dict(), "model_config": model.export_config(),
                        "train_config": vars(a), "step": it + 1}, path)
    h = file_sha256(out / ("pretrain_%s.pt" % a.model))
    (out / "pretrain_done.json").write_text(json.dumps({"sha256": h, "steps": a.steps}, indent=1))
    print(json.dumps({"done": True, "sha256": h}), flush=True)


if __name__ == "__main__":
    main()
