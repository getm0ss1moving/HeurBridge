"""Cell-stage predictor (heurbridge.bridge.lookahead_net, sketch redesign S2)."""

import numpy as np
import torch

from heurbridge.bridge import lookahead as LA
from heurbridge.bridge.graph import KIND_CL
from heurbridge.bridge.lookahead_net import LookaheadNet, from_bridge, lookahead_loss, spread_moments, spread_targets
from heurbridge.bridge.model import BridgeConfig, BridgeNet
from heurbridge.bridge.sample import source_nodes
from heurbridge.core import synth
from heurbridge.heuristics.cell.cluster import cluster_cells
from heurbridge.pipeline import bridge_data as BD

TINY = BridgeConfig(width=64, layers=2, edge_dim=16, pe_freqs=6, t_dim=32)


def case(seed=0):
    des, ref = synth.make_design(seed=seed, n_macros=6, n_cells=200, n_io=8)
    cl = cluster_cells(des, n=10, seed=0)
    base = ref.copy()
    base.pos[~des.is_macro & ~des.is_io & ~des.is_fixed] = np.nan
    return BD.make_bundle(des, base, cl), ref


def test_spread_round_trip():
    cov = torch.tensor([[4e-3, 1e-3, 1e-3], [1e-4, 9e-4, -2e-4]])
    back = spread_moments(spread_targets(cov))
    assert torch.allclose(back, cov, rtol=1e-5, atol=1e-9)


def test_fresh_predictor_is_the_quadratic_placement():
    b, ref = case(1)
    g = b.graph
    gt = g.tensors("cpu")
    x = torch.as_tensor(source_nodes(g, ref)[None], dtype=torch.float32)
    m = LookaheadNet(TINY).eval()
    with torch.no_grad():
        pos, sp = m.predict(x, gt)
    assert torch.equal(pos, x)                                               # zero-initialized shift head
    assert torch.allclose(sp[..., :2], torch.full_like(sp[..., :2], float(np.log(1e-3))))


def test_from_bridge_keeps_the_encoder(tmp_path):
    torch.manual_seed(0)
    br = BridgeNet(TINY)
    for p in br.parameters():
        p.data.normal_(0, 0.02)
    torch.save({"model": br.state_dict(), "ema": br.state_dict(), "model_config": br.export_config()}, tmp_path / "b.pt")
    m = from_bridge(str(tmp_path / "b.pt"))
    for k, v in br.state_dict().items():
        assert torch.equal(m.state_dict()[k], v), k


def test_predictor_learns_one_layout():
    torch.manual_seed(0)
    b, ref = case(2)
    g, des = b.graph, b.design
    gt = g.tensors("cpu")
    x = torch.as_tensor(source_nodes(g, ref)[None], dtype=torch.float32)
    pos, cov, _ = LA.cluster_moments(des, ref, b.cluster_of)
    y_pos = torch.as_tensor(pos[None], dtype=torch.float32)
    y_cov = torch.as_tensor(cov[None], dtype=torch.float32)
    m = LookaheadNet(TINY)
    opt = torch.optim.Adam(m.parameters(), lr=3e-3)
    _, first = lookahead_loss(m, gt, x, y_pos, y_cov)
    for _ in range(300):
        loss, info = lookahead_loss(m, gt, x, y_pos, y_cov)
        opt.zero_grad()
        loss.backward()
        opt.step()
    assert float(info["rms"][0]) < 0.25 * float(first["rms"][0])             # learns the placed centroids
    assert float(first["rms"][0]) == float(first["rms_quad"][0])            # starts at the quadratic placement
    assert int((gt["kind"] == KIND_CL).sum()) == g.n_clusters


def test_moments_follow_the_dihedral_transform():
    """transform_cov matches the second moments of transformed points (augmentation of S2's targets)."""
    import torch
    from heurbridge.bridge.data import transform_positions
    from heurbridge.bridge.lookahead_net import transform_cov
    g = torch.Generator().manual_seed(0)
    p = torch.rand(500, 2, generator=g, dtype=torch.float64) * torch.tensor([0.3, 0.1], dtype=torch.float64) + 0.2
    p[:, 1] += 0.5 * p[:, 0]                                       # correlated, anisotropic

    def moments(q):
        d = q - q.mean(0)
        return torch.stack([(d[:, 0] ** 2).mean(), (d[:, 1] ** 2).mean(), (d[:, 0] * d[:, 1]).mean()])
    for k in range(8):
        assert torch.allclose(transform_cov(moments(p), k), moments(transform_positions(p, k)), atol=1e-12)
