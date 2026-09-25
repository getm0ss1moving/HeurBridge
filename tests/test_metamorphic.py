"""T7.1 V1: metamorphic relations MR1-MR6 on f0 metrics and the P_M projection (hypothesis, 50 cases each)."""

import numpy as np
import torch
from hypothesis import given, settings, strategies as st

from heurbridge.core import orient as O, project, synth
from heurbridge.core import design as D
from heurbridge.eval import f0
from heurbridge.verify import metamorphic as MR

SET = settings(max_examples=50, deadline=None)


def case(seed, orients=False):
    des, lay = synth.make_design(seed=seed, n_macros=5, n_cells=40, n_io=6, allow_macro_orients=orients)
    return des, lay


def metrics(des, lay, cfg=None):
    """f0 metrics in float64 (metamorphic relations are exact up to round-off)."""
    ctx = f0.F0Context(des, lay.orient, cfg=cfg or f0.F0Config(gcell=50.0), dtype=torch.float64)
    m = ctx.all(torch.as_tensor(lay.pos, dtype=torch.float64))
    return {k: float(v[0]) for k, v in m.items()}


@SET
@given(st.integers(0, 10_000))
def test_mr1_relabel(seed):
    des, lay = case(seed, orients=True)
    d2, l2, perm = MR.mr1_relabel(des, lay, np.random.default_rng(seed))
    assert abs(D.hpwl(des, lay) - D.hpwl(d2, l2)) <= 1e-9 * D.hpwl(des, lay)
    out1, _ = project.legalize_macros(des, lay)
    out2, _ = project.legalize_macros(d2, l2)
    assert np.allclose(out2.pos, out1.pos[perm], atol=1e-12)          # P_M is permutation-equivariant


@SET
@given(st.integers(0, 10_000))
def test_mr2_mirror(seed):
    des, lay = case(seed, orients=True)
    d2, l2 = MR.mr2_mirror_x(des, lay)
    assert abs(D.hpwl(des, lay) - D.hpwl(d2, l2)) <= 1e-9 * D.hpwl(des, lay)
    a, b = metrics(des, lay), metrics(d2, l2)
    for k in ("macro_overlap", "outside_area"):
        assert abs(a[k] - b[k]) <= 1e-3 * (abs(a[k]) + 1.0), k


@SET
@given(st.integers(0, 10_000), st.floats(-500, 500), st.floats(-500, 500))
def test_mr3_translate(seed, dx, dy):
    des, lay = case(seed)
    d2, l2 = MR.mr3_translate(des, lay, dx, dy)
    assert abs(D.hpwl(des, lay) - D.hpwl(d2, l2)) <= 1e-9 * D.hpwl(des, lay)
    a, b = metrics(des, lay), metrics(d2, l2)
    for k in ("hpwl", "macro_overlap", "density_overflow", "rudy_overflow"):
        assert abs(a[k] - b[k]) <= 1e-3 * (abs(a[k]) + 1e-3), k


@SET
@given(st.integers(0, 10_000))
def test_mr4_dummy_net(seed):
    des, lay = case(seed)
    rng = np.random.default_rng(seed)
    a, b = rng.choice(des.n_objects, 2, replace=False)
    d2, l2 = MR.mr4_dummy_net(des, lay, int(a), int(b))
    x, y = metrics(des, lay), metrics(d2, l2)
    for k in ("hpwl", "hpwl_wa", "rudy_overflow", "density_overflow"):
        assert abs(x[k] - y[k]) <= 1e-5 * (abs(x[k]) + 1e-6), k


@SET
@given(st.integers(0, 10_000), st.floats(0.05, 0.9))
def test_mr5_capacity(seed, frac):
    des, lay = case(seed)
    ctx = f0.F0Context(des, lay.orient, cfg=f0.F0Config(gcell=50.0))
    p = torch.as_tensor(lay.pos, dtype=torch.float32)
    r = ctx.rudy(p)
    i, j = np.unravel_index(int(torch.argmax(r["dem_h"][0])), r["dem_h"].shape[1:])
    cap_h = r["cap_h"].clone()
    cap_h[0, i, j] *= frac
    before = float(torch.relu(r["dem_h"][0, i, j] - r["cap_h"][0, i, j]))
    after = float(torch.relu(r["dem_h"][0, i, j] - cap_h[0, i, j]))
    assert after >= before


@SET
@given(st.integers(0, 10_000))
def test_mr6_duplicate(seed):
    des, lay = case(seed)
    d2, l2 = MR.mr6_duplicate(des, lay)
    assert abs(D.hpwl(d2, l2) - 2 * D.hpwl(des, lay)) <= 1e-8 * D.hpwl(des, lay)
    a, b = metrics(des, lay), metrics(d2, l2)
    assert abs(b["macro_overlap"] - 2 * a["macro_overlap"]) <= 1e-3 * (a["macro_overlap"] + 1.0)
