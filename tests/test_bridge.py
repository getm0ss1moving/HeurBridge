"""T3.10 bridge unit tests (must pass before T4)."""

import numpy as np
import pytest
import torch

from heurbridge.bridge import data as BD
from heurbridge.bridge.graph import KIND_MOV, build_graph
from heurbridge.bridge.model import BridgeConfig, BridgeNet
from heurbridge.bridge.sample import bridge_endpoints, refine, source_nodes
from heurbridge.bridge.train import TrainConfig, Trainer, bridge_loss, integrate
from heurbridge.core import project, synth
from heurbridge.eval import f0
from heurbridge.heuristics.cell.cluster import cluster_cells

TINY = BridgeConfig(width=64, layers=2, edge_dim=16, pe_freqs=6, t_dim=32)


def small_case(seed=0, n_macros=6, n_cells=60):
    des, ref = synth.make_design(seed=seed, n_macros=n_macros, n_cells=n_cells, n_io=8)
    cl = cluster_cells(des, n=8, seed=0)
    g = build_graph(des, ref, cl)
    return des, ref, g


def randomize(model: BridgeNet, scale=0.2, seed=0):
    torch.manual_seed(seed)
    for blk in model.blocks:
        torch.nn.init.normal_(blk.film.weight, std=scale)
    torch.nn.init.normal_(model.dec[-1].weight, std=scale)
    return model


def permute_tensors(gt: dict, perm: np.ndarray) -> dict:
    inv = np.empty_like(perm)
    inv[perm] = np.arange(len(perm))
    p, iv = torch.as_tensor(perm), torch.as_tensor(inv)
    out = dict(gt)
    for k in ("static", "movable", "area_w", "size", "kind"):
        out[k] = gt[k][p]
    out["edge_index"] = iv[gt["edge_index"]]
    out["attn"] = iv[gt["attn"]]
    return out


# 1 ----------------------------------------------------------------------------------------
def test_overfit_single_pair():
    des, ref, g = small_case(seed=1)
    rng = np.random.default_rng(0)
    x1 = g.node_positions(ref)
    x0 = x1.copy()
    mv = g.movable
    x0[mv] = np.clip(x1[mv] + rng.normal(0, 0.08, (mv.sum(), 2)), 0.05, 0.95)
    ps = BD.PairSet(g, x0[None].astype(np.float32), x1[None].astype(np.float32), np.ones(1, np.float32),
                    np.zeros((1, g.n), np.int8), [{}])
    cfg = TrainConfig(steps=2000, batch=16, lr=1e-3, warmup=100, lam_ov=0.0, sigma=0.01, tau_dist="uniform",
                      dihedral=False, aspect=0.0, val_every=10**9, ema=0.0, device="cpu", bf16=False)
    tr = Trainer(BridgeNet(TINY), cfg, [ps], log=lambda s: None)
    for it in range(cfg.steps):
        tr.step(it)
    gt = g.tensors()
    xe = integrate(tr.model.eval(), gt, torch.as_tensor(x0[None], dtype=torch.float32), K=20)[0].numpy()
    a = g.area_w
    err = np.sqrt((a * ((xe - x1) ** 2).sum(-1)).sum() / a.sum())
    assert err < 1e-3, err


# 2 ----------------------------------------------------------------------------------------
def test_multimodal_bridge_vs_regression():
    """Port of toy_multimodal.py: mirror-pair elites; regression averages modes, the bridge picks one.
    Both models see fresh samples every batch, so each converges to its population optimum."""
    import math
    from heurbridge.bridge.graph import BridgeGraph
    rng = np.random.default_rng(0)
    W = 0.15                                      # macro width (normalized) = 0.5 toy units

    def sample(n):
        a = rng.uniform(0.3, 0.8, n)
        s = rng.choice([-1.0, 1.0], n)
        x1 = np.stack([-s * a, s * a], 1)
        xh = 0.25 * x1 + 0.35 * rng.standard_normal((n, 2))
        to = lambda u: np.stack([0.5 + 0.3 * u, np.full_like(u, 0.5)], -1)
        return a, to(xh), to(x1)

    g = BridgeGraph(design_id="toy", kind=np.array([KIND_MOV, KIND_MOV], np.int8), obj=np.array([0, 1]),
                    size=np.array([[W, W], [W, W]], np.float32), orient=np.zeros(2, np.int8),
                    pin_count=np.ones(2, np.float32), movable=np.ones(2, bool), area_w=np.ones(2, np.float32),
                    group=np.array([-1, -1]), key=np.array([1, 2]), edge_index=np.array([[0, 1], [1, 0]]),
                    edge_attr=np.zeros((2, 6), np.float32), graph_attr=np.zeros(9, np.float32),
                    attn=np.array([0, 1]), fixed_pos=np.full((2, 2), np.nan), cluster_of=np.zeros(0, np.int64))
    gt = g.tensors()

    def gfeat(av):
        ga = torch.zeros(len(av), 9)
        ga[:, 0] = torch.as_tensor(av, dtype=torch.float32)
        return ga

    torch.manual_seed(0)
    bridge, reg = BridgeNet(TINY), BridgeNet(TINY)
    ob, orr = torch.optim.AdamW(bridge.parameters(), lr=2e-3), torch.optim.AdamW(reg.parameters(), lr=2e-3)
    gen = torch.Generator().manual_seed(0)
    cfg = TrainConfig(sigma=0.3 * 0.15, lam_ov=0.0, tau_dist="uniform", device="cpu", bf16=False)
    steps, B = 1500, 512
    for it in range(steps):
        for o in (ob, orr):
            for pg in o.param_groups:
                pg["lr"] = 2e-3 * 0.5 * (1 + math.cos(math.pi * it / steps))
        a, xh, x1 = sample(B)
        X0, X1 = torch.as_tensor(xh, dtype=torch.float32), torch.as_tensor(x1, dtype=torch.float32)
        g_b = dict(gt, graph_attr=gfeat(a))
        loss, _ = bridge_loss(bridge, g_b, X0, X1, torch.ones(B), cfg, gen)
        ob.zero_grad(); loss.backward(); ob.step()
        lr_ = ((X0 + reg(X0, torch.zeros(B), g_b) - X1) ** 2).sum(-1).mean()
        orr.zero_grad(); lr_.backward(); orr.step()
    at, xht, x1t = sample(2000)
    g_t = dict(gt, graph_attr=gfeat(at))
    X0t = torch.as_tensor(xht, dtype=torch.float32)
    with torch.no_grad():
        xb = integrate(bridge.eval(), g_t, X0t, K=20).numpy()
        xr = (X0t + reg.eval()(X0t, torch.zeros(len(at)), g_t)).numpy()
    ov_b = float((np.abs(xb[:, 0, 0] - xb[:, 1, 0]) < W).mean())
    ov_r = float((np.abs(xr[:, 0, 0] - xr[:, 1, 0]) < W).mean())
    assert ov_b < 0.01 and ov_r > 0.40, (ov_b, ov_r)


# 3 ----------------------------------------------------------------------------------------
def test_equivariance():
    des, ref, g = small_case(seed=2)
    m = randomize(BridgeNet(TINY)).eval()
    gt = g.tensors()
    rng = np.random.default_rng(0)
    x = torch.as_tensor(np.clip(g.node_positions(ref) + rng.normal(0, 0.05, (g.n, 2)), 0, 1)[None], dtype=torch.float32)
    xh = torch.as_tensor(g.node_positions(ref)[None], dtype=torch.float32)
    tau = torch.tensor([0.3])
    perm = rng.permutation(g.n)
    with torch.no_grad():
        v = m(x, tau, gt, xh=xh)[0].numpy()
        vp = m(x[:, perm], tau, permute_tensors(gt, perm), xh=xh[:, perm])[0].numpy()
    assert np.abs(v).max() > 1e-3                        # non-trivial output
    assert np.allclose(vp, v[perm], atol=1e-5), np.abs(vp - v[perm]).max()


# 4, 5 -------------------------------------------------------------------------------------
def test_masking_and_determinism():
    des, ref, g = small_case(seed=3)
    m = randomize(BridgeNet(TINY)).eval()
    rng = np.random.default_rng(1)
    src = np.stack([np.clip(g.node_positions(ref) + rng.normal(0, 0.05, (g.n, 2)) * g.movable[:, None], 0, 1)
                    for _ in range(4)])
    e1 = bridge_endpoints(m, g, src, K=10)
    e2 = bridge_endpoints(m, g, src, K=10)
    fixed = ~g.movable
    assert np.array_equal(e1[:, fixed], src[:, fixed])          # fixed nodes move by exactly 0
    assert np.abs(e1[:, g.movable] - src[:, g.movable]).max() > 1e-4
    assert np.array_equal(e1, e2)                               # same input -> identical output


# 6 ----------------------------------------------------------------------------------------
def test_guard_monotonicity_100_cases():
    n_cases = 0
    for seed in range(4):
        des, ref, g = small_case(seed=10 + seed, n_macros=8)
        m = randomize(BridgeNet(TINY), scale=0.5, seed=seed).eval()
        ctx = f0.F0Context(des, ref.orient)
        norm = f0.reference_normalizers(ctx, ref.pos)

        def evaluate(l):
            return float(f0.surrogate_j0(ctx, torch.as_tensor(l.pos, dtype=torch.float32), norm)[0])

        rng = np.random.default_rng(seed)
        mm = des.is_macro & ~des.is_fixed
        layouts = []
        for _ in range(25):
            l = ref.copy()
            l.pos[mm] = rng.uniform(0.1, 0.9, (mm.sum(), 2))
            layouts.append(project.legalize_macros(des, l)[0])
        res = refine(m, g, des, layouts, evaluate, K=10)
        for r, l in zip(res, layouts):
            raw = evaluate(l)
            assert r.scores[0] == pytest.approx(raw, rel=1e-6)          # alpha = 0 is the raw heuristic
            assert min(r.scores) <= raw + 1e-12 and evaluate(r.layout) <= raw + 1e-9
            assert project.check_macros(des, r.layout)["ok"] and r.alpha in (0.0, 0.25, 0.5, 1.0)
            n_cases += 1
    assert n_cases == 100
