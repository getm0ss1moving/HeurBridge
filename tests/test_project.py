"""T2.5: P_M legalizer — every random layout is projected to a layout that passes the exact checker."""

import numpy as np
import pytest

from heurbridge.core import orient as O, project, synth
from heurbridge.core.design import Design, build_csr


@pytest.mark.parametrize("seed,n_macros,halo", [(0, 8, 0.0), (1, 12, 5.0), (2, 20, 10.0)])
def test_random_layouts_always_legal(seed, n_macros, halo):
    des, lay = synth.make_design(seed=seed, n_macros=n_macros, n_cells=50, n_io=8, macro_frac=(0.05, 0.14),
                                 allow_macro_orients=True)
    rng = np.random.default_rng(seed)
    mm = des.is_macro & ~des.is_fixed
    n_ok = 0
    trials = 1000
    for t in range(trials):
        l = lay.copy()
        l.pos[mm] = rng.uniform(-0.1, 1.1, (mm.sum(), 2))          # includes out-of-core targets
        out, rep = project.legalize_macros(des, l, halo=halo)
        assert rep.ok, (t, rep.failed, rep.check)
        assert np.array_equal(out.orient, l.orient)                   # orientation untouched
        assert np.array_equal(out.pos[~mm], l.pos[~mm])               # only movable macros move
        n_ok += rep.ok
    assert n_ok == trials


def test_legal_input_is_fixed_point_on_grid():
    des, lay = synth.make_design(seed=5, n_macros=6, n_cells=40, n_io=6)
    out, rep = project.legalize_macros(des, lay)
    out2, rep2 = project.legalize_macros(des, out)
    assert rep.ok and rep2.ok and rep2.moved == 0
    assert np.allclose(out2.pos, out.pos)


def test_lower_left_on_site_grid():
    des, lay = synth.make_design(seed=6, n_macros=10, n_cells=40, n_io=6)
    out, rep = project.legalize_macros(des, lay, halo=7.0)
    nx, ny, px, py = rep.grid
    mm = des.is_macro & ~des.is_fixed
    ll = des.to_abs(out.pos[mm]) - O.effective_size(des.size[mm], out.orient[mm]) / 2 - des.core_ll
    assert np.allclose(ll[:, 0] / des.site[0], np.round(ll[:, 0] / des.site[0]), atol=1e-6)
    assert np.allclose(ll[:, 1] / des.site[1], np.round(ll[:, 1] / des.site[1]), atol=1e-6)


def test_fixed_obstacles_and_infeasible_report():
    size = np.array([[600.0, 600.0], [500.0, 500.0], [0.0, 0.0]])
    ptr, idx = build_csr([[0, 1, 2]])
    des = Design(id="f", family="t", tech="t", names=["fix", "mov", "io"], size=size,
                 is_macro=np.array([1, 1, 0], bool), is_fixed=np.array([1, 0, 1], bool),
                 is_io=np.array([0, 0, 1], bool), pin_obj=np.array([0, 1, 2]), pin_off=np.zeros((3, 2)),
                 net_ptr=ptr, pin_idx=idx, net_weight=np.ones(1), die=(0, 0, 1000, 1000), core=(0, 0, 1000, 1000),
                 site=(1.0, 10.0))
    from heurbridge.core.design import Layout
    lay = Layout(pos=np.array([[0.3, 0.3], [0.3, 0.3], [0.0, 0.0]]), orient=np.zeros(3, np.int8), schema=des.schema_hash())
    out, rep = project.legalize_macros(des, lay)
    assert not rep.ok and rep.failed == [1]           # 500x500 cannot fit next to a 600x600 block in 1000x1000
    des.size[1] = [350.0, 350.0]
    des2 = Design(**{**des.__dict__})
    lay.schema = des2.schema_hash()
    out, rep = project.legalize_macros(des2, lay)
    assert rep.ok and project.check_macros(des2, out)["ok"]
