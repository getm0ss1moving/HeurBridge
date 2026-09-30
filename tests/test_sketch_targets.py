"""Bridge sketch training (30 Sep): cluster targets of elites stored without them, and the cluster loss weight."""

import numpy as np
import torch

from heurbridge.archive.store import Archive, Candidate
from heurbridge.bridge.graph import KIND_CL
from heurbridge.bridge.model import BridgeConfig, BridgeNet
from heurbridge.bridge.sample import source_nodes
from heurbridge.bridge.train import TrainConfig, bridge_loss
from heurbridge.core import project, synth
from heurbridge.heuristics.cell.cluster import cluster_cells
from heurbridge.pipeline import bridge_data as BD

TINY = BridgeConfig(width=64, layers=2, edge_dim=16, pe_freqs=6, t_dim=32)


def bundle(seed=0):
    des, ref = synth.make_design(seed=seed, n_macros=6, n_cells=60, n_io=8)
    cl = cluster_cells(des, n=8, seed=0)
    base = ref.copy()
    base.pos[~des.is_macro & ~des.is_io & ~des.is_fixed] = np.nan
    return BD.make_bundle(des, base, cl), ref


def test_cluster_target_override(tmp_path):
    b, ref = bundle(1)
    g = b.graph
    arch = Archive(tmp_path / "a", min_fidelity=1)
    lay = project.legalize_macros(b.design, ref)[0]
    lay.pos[~b.design.is_macro & ~b.design.is_io & ~b.design.is_fixed] = np.nan
    ok, why = arch.insert(Candidate(design_id=b.design.id, stage="M", layout=lay, fidelity=1, J=0.5, admissible=True,
                                    metrics={}, gates={}, provenance={"program": "BASELINE"}))
    assert ok, why
    e = arch.topk(b.design.id, "M", 5)[0]
    plain = BD.archive_elites(b, arch)[0]
    assert np.array_equal(plain.x, source_nodes(g, arch.layout(e)))          # no targets stored: quadratic stand-in
    cp = np.random.default_rng(0).uniform(0.1, 0.9, (g.n_clusters, 2))
    fixed = BD.archive_elites(b, arch, cluster_pos_override={int(e["id"]): cp})[0]
    assert np.array_equal(fixed.x[g.cluster_nodes], cp)
    assert np.array_equal(fixed.x[g.macro_nodes], plain.x[g.macro_nodes])
    other = BD.archive_elites(b, arch, cluster_pos_override={int(e["id"]) + 999: cp})[0]
    assert np.array_equal(other.x, plain.x)                                      # override keyed by elite id only


def test_cluster_weight_default_and_scaling():
    b, ref = bundle(2)
    g = b.graph
    gt = g.tensors("cpu")
    torch.manual_seed(0)
    m = BridgeNet(TINY).eval()
    rng = np.random.default_rng(0)
    x0 = torch.as_tensor(np.stack([source_nodes(g, b.base)] * 2), dtype=torch.float32)
    x1 = x0 + torch.as_tensor(rng.normal(0, 0.05, x0.shape), dtype=torch.float32) * gt["movable"].view(1, -1, 1)
    w = torch.ones(2)
    tau = torch.tensor([0.3, 0.7])
    eps = torch.randn(x0.shape, generator=torch.Generator().manual_seed(1))
    cfg1 = TrainConfig(lam_ov=0.0, device="cpu")
    l1, i1 = bridge_loss(m, gt, x0, x1, w, cfg1, None, tau=tau, eps=eps)
    l1b, _ = bridge_loss(m, gt, x0, x1, w, TrainConfig(lam_ov=0.0, device="cpu", cluster_weight=1.0), None, tau=tau, eps=eps)
    assert float(l1) == float(l1b)                                              # the default is the old loss
    cfg10 = TrainConfig(lam_ov=0.0, device="cpu", cluster_weight=10.0)
    l10, i10 = bridge_loss(m, gt, x0, x1, w, cfg10, None, tau=tau, eps=eps)
    # by hand: per-node squared velocity error with the cluster weights x10
    t = tau.view(2, 1, 1)
    mov = gt["movable"].view(1, -1, 1)
    e = eps * mov
    xt = (1 - t) * x0 + t * x1 + cfg1.sigma * t * (1 - t) * e
    ut = x1 - x0 + cfg1.sigma * (1 - 2 * t) * e
    with torch.no_grad():
        v = m(xt, tau, gt, xh=x0).float()
    a = gt["area_w"].view(1, -1) * torch.where(gt["kind"].view(1, -1) == KIND_CL, 10.0, 1.0)
    fm = (a * ((v - ut) ** 2).sum(-1)).sum(-1) / a.sum()
    assert abs(float(l10) - float(fm.mean())) < 1e-5
    assert float(l10) != float(l1)


def test_keep_val_ckpts(tmp_path):
    from heurbridge.bridge.train import Trainer
    b, ref = bundle(3)
    g = b.graph
    x1 = source_nodes(g, ref).astype(np.float32)
    x0 = source_nodes(g, b.base).astype(np.float32)
    ps = BD.PairSet(g, x0[None], x1[None], np.ones(1, np.float32), np.zeros((1, g.n), np.int8), [{}])
    for keep, out in ((False, tmp_path / "plain"), (True, tmp_path / "keep")):
        cfg = TrainConfig(steps=4, batch=2, lr=1e-3, warmup=1, val_every=2, device="cpu", bf16=False, keep_val_ckpts=keep)
        torch.manual_seed(0)
        Trainer(BridgeNet(TINY), cfg, [ps], out_dir=out, log=lambda s: None).fit()
        assert (out / "best.pt").exists()
        assert sorted(p.name for p in out.glob("step*.pt")) == (["step2.pt", "step4.pt"] if keep else [])
