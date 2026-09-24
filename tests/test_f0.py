"""T1.3: f0 metrics (torch) against numpy references and analytic cases."""

import numpy as np
import pytest
import torch

from heurbridge.core import orient as O, synth
from heurbridge.core import design as D
from heurbridge.core.design import Design, Layout, build_csr
from heurbridge.eval import f0


def _two_macro_design(w=100.0, h=100.0, die=1000.0):
    size = np.array([[w, h], [w, h], [0.0, 0.0], [0.0, 0.0]])
    nets = [[0, 1], [2, 3]]
    ptr, idx = build_csr(nets)
    des = Design(id="t", family="t", tech="t", names=["m0", "m1", "io0", "io1"], size=size,
                 is_macro=np.array([1, 1, 0, 0], bool), is_fixed=np.array([0, 0, 1, 1], bool),
                 is_io=np.array([0, 0, 1, 1], bool), pin_obj=np.array([0, 1, 2, 3]),
                 pin_off=np.zeros((4, 2)), net_ptr=ptr, pin_idx=idx, net_weight=np.ones(2),
                 die=(0, 0, die, die), core=(0, 0, die, die))
    return des


def test_exact_hpwl_matches_numpy_with_orientations():
    des, lay = synth.make_design(seed=7, n_macros=6, n_cells=150, n_io=12, allow_macro_orients=True)
    ctx = f0.F0Context(des, lay.orient)
    got = float(ctx.hpwl_exact(torch.tensor(lay.pos, dtype=torch.float32))[0])
    ref = D.hpwl(des, lay, "centre")
    assert got == pytest.approx(ref, rel=1e-5)


def test_smooth_wirelength_bounds_and_gradients():
    des, lay = synth.make_design(seed=8, n_macros=5, n_cells=100, n_io=8)
    ctx = f0.F0Context(des, lay.orient)
    p = torch.tensor(lay.pos, dtype=torch.float32, requires_grad=True)
    exact = float(ctx.hpwl_exact(p.detach())[0])
    wa, lse = ctx.hpwl_wa(p)[0], ctx.hpwl_lse(p)[0]
    wa_v, lse_v = float(wa.detach()), float(lse.detach())
    assert wa_v <= exact * (1 + 1e-5) and lse_v >= exact * (1 - 1e-5)
    assert abs(wa_v - exact) / exact < 0.2 and abs(lse_v - exact) / exact < 0.2
    wa.backward()
    g = p.grad.numpy()
    assert np.isfinite(g).all() and np.abs(g[~des.is_fixed]).sum() > 0


def test_batched_equals_single():
    des, lay = synth.make_design(seed=9, n_macros=4, n_cells=60, n_io=6)
    ctx = f0.F0Context(des, lay.orient)
    rng = np.random.default_rng(0)
    batch = np.stack([np.clip(lay.pos + rng.normal(0, 0.02, lay.pos.shape) * (~des.is_fixed)[:, None], 0, 1)
                      for _ in range(4)])
    tb = torch.tensor(batch, dtype=torch.float32)
    mb = ctx.all(tb)
    for b in range(4):
        m1 = ctx.all(tb[b])
        for k in mb:
            assert float(mb[k][b]) == pytest.approx(float(m1[k][0]), rel=1e-4, abs=1e-6), k


def test_macro_overlap_exact_area():
    des = _two_macro_design()
    ctx = f0.F0Context(des)
    pos = np.array([[0.30, 0.30], [0.36, 0.33], [0.0, 0.0], [1.0, 1.0]])
    ov = float(ctx.macro_overlap(torch.tensor(pos, dtype=torch.float32))[0])
    assert ov == pytest.approx((100 - 60) * (100 - 30), rel=1e-5)
    pos[1] = [0.5, 0.5]
    assert float(ctx.macro_overlap(torch.tensor(pos, dtype=torch.float32))[0]) == 0.0
    pos[1] = [0.30, 0.30]   # identical placement -> full area
    assert float(ctx.macro_overlap(torch.tensor(pos, dtype=torch.float32))[0]) == pytest.approx(100 * 100, rel=1e-5)


def test_outside_area():
    des = _two_macro_design()
    ctx = f0.F0Context(des)
    pos = np.array([[0.02, 0.5], [0.5, 0.5], [0, 0], [1, 1]])   # m0 extends 30 units past x=0
    assert float(ctx.outside_area(torch.tensor(pos, dtype=torch.float32))[0]) == pytest.approx(30 * 100, rel=1e-5)


def test_density_overflow_clumped_vs_spread():
    des, lay = synth.make_design(seed=10, n_macros=0, n_cells=400, n_io=4)
    ctx = f0.F0Context(des, lay.orient)
    clump = lay.pos.copy()
    cells = ~des.is_fixed
    clump[cells] = 0.5
    rng = np.random.default_rng(1)
    spread = lay.pos.copy()
    spread[cells] = rng.uniform(0.02, 0.98, (cells.sum(), 2))
    oc = float(ctx.density_overflow(torch.tensor(clump, dtype=torch.float32))[0])
    os_ = float(ctx.density_overflow(torch.tensor(spread, dtype=torch.float32))[0])
    assert oc > 0.8 and os_ < 0.3


def test_raster_conserves_area():
    des, lay = synth.make_design(seed=11, n_macros=6, n_cells=200, n_io=8)
    ctx = f0.F0Context(des, lay.orient)
    pa = ctx.to_abs(torch.tensor(lay.pos, dtype=torch.float64).unsqueeze(0)).float()
    sel = torch.as_tensor(~des.is_io)
    m = ctx._raster(pa, sel, ctx.bin, ctx.nbx, ctx.nby)
    inside_area = des.area[~des.is_io].sum()     # synthetic objects lie inside the core
    assert float(m.sum()) == pytest.approx(inside_area, rel=1e-4)


def test_rudy_total_demand_equals_hpwl_for_large_nets():
    des = _two_macro_design(w=10, h=10)
    ctx = f0.F0Context(des, cfg=f0.F0Config(gcell=50.0))
    pos = np.array([[0.2, 0.3], [0.7, 0.6], [0.1, 0.9], [0.8, 0.2]])
    r = ctx.rudy(torch.tensor(pos, dtype=torch.float32))
    total = float((r["dem_h"] + r["dem_v"]).sum())
    exact = float(ctx.hpwl_exact(torch.tensor(pos, dtype=torch.float32))[0])
    assert total == pytest.approx(exact, rel=1e-4)


def test_channel_shortage_detects_gap_between_macros():
    # two tall macros with a 1-GCell gap; many nets squeezed through the gap
    size = np.array([[300.0, 800.0], [300.0, 800.0]] + [[0.0, 0.0]] * 40)
    nets = [[2 * k, 2 * k + 1] for k in range(20)]      # pin indices; pin p sits on object p + 2
    ptr, idx = build_csr(nets)
    n = 42
    des = Design(id="c", family="t", tech="t", names=["o%d" % i for i in range(n)], size=size,
                 is_macro=np.r_[[True, True], np.zeros(40, bool)], is_fixed=np.r_[[False, False], np.ones(40, bool)],
                 is_io=np.r_[[False, False], np.ones(40, bool)], pin_obj=np.arange(2, 42),
                 pin_off=np.zeros((40, 2)), net_ptr=ptr, pin_idx=idx, net_weight=np.ones(20),
                 die=(0, 0, 1000, 1000), core=(0, 0, 1000, 1000))
    pos = np.zeros((n, 2))
    pos[0], pos[1] = [0.325, 0.5], [0.675, 0.5]          # gap of 50 units = 1 GCell at x in [475,525]
    xs = np.linspace(0.49, 0.51, 20)                     # 20 bottom-to-top nets through the gap
    pos[2::2] = np.c_[xs, np.full(20, 0.05)]
    pos[3::2] = np.c_[xs, np.full(20, 0.95)]
    ctx = f0.F0Context(des, cfg=f0.F0Config(gcell=50.0, tracks_per_unit_h=0.2, tracks_per_unit_v=0.2))
    t = torch.tensor(pos, dtype=torch.float32)
    r = ctx.rudy(t)
    cs = float(ctx.channel_shortage(t, r)[0])
    assert float(r["overflow"][0]) > 0 and cs > 0
    far = pos.copy()
    far[0], far[1] = [0.15, 0.5], [0.85, 0.5]
    assert float(ctx.channel_shortage(torch.tensor(far, dtype=torch.float32))[0]) == 0.0


def test_surrogate_j0_differentiable():
    des, lay = synth.make_design(seed=12, n_macros=5, n_cells=80, n_io=8)
    ctx = f0.F0Context(des, lay.orient)
    ref = f0.reference_normalizers(ctx, lay.pos)
    p = torch.tensor(lay.pos, dtype=torch.float32, requires_grad=True)
    j = f0.surrogate_j0(ctx, p, ref)
    j.sum().backward()
    assert torch.isfinite(p.grad).all()
    assert float(j[0]) == pytest.approx(float(f0.surrogate_j0(ctx, p.detach(), ref)[0]), rel=1e-6)
