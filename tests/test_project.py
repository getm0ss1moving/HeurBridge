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


def _ram_core():
    """bp_fe_top's macro set on its core (nine 152.57 x 113.4 um RAMs + two small ones), no netlist."""
    sizes = [(152.57, 113.4)] * 9 + [(54.53, 89.4), (10.64, 36.4)]
    n = len(sizes)
    names = ["icache_1/data_mem_banks_%d__data_mem_bank/macro_mem/mem" % k for k in range(8)] + [
        "bp_fe_pc_gen_1/genblk1_branch_prediction_1/btb_1/btb_mem/macro_mem/mem", "icache_1/tag_mem/macro_mem/mem",
        "icache_1/metadata_mem/macro_mem/mem"]          # real names: equal-size ties are broken by a name hash
    des = Design(id="ram_core", family="synth", tech="nangate45", names=names,
                 size=np.array(sizes), is_macro=np.ones(n, bool), is_fixed=np.zeros(n, bool), is_io=np.zeros(n, bool),
                 pin_obj=np.zeros(0, np.int64), pin_off=np.zeros((0, 2)), net_ptr=np.zeros(1, np.int64),
                 pin_idx=np.zeros(0, np.int64), net_weight=np.zeros(0), die=(0.0, 0.0, 645.055, 645.055),
                 core=(2.09, 2.8, 642.96, 642.6), masters=["ram"] * 9 + ["tag", "meta"], site=(0.19, 1.4))
    from heurbridge.core.design import Layout
    lay = Layout(pos=np.full((n, 2), 0.5), orient=np.zeros(n, np.int8), schema=des.schema_hash())
    return des, lay


def test_dense_ram_core_needs_fallback_order():
    """Largest-first greedy fragments this core (the M2.v0 seed-3 output on bp_fe_top); a fallback order
    must legalize it, and the primary order's result is kept whenever it is legal."""
    des, lay = _ram_core()
    ll = np.array(des.core[:2])
    centres = [(89.1, 132.57), (92.09, 245.98), (402.66, 310.01), (245.02, 421.77), (250.52, 182.08), (86.64, 360.61),
               (245.01, 303.73), (90.01, 474.31), (409.32, 527.02), (435.27, 415.18), (289.63, 564.82)]   # um
    orients = [O.R180, O.R180, O.R0, O.R0, O.MX, O.MY, O.R0, O.MY, O.R0, O.R0, O.MX]
    l = lay.copy()
    l.pos[:] = (np.array(centres) - ll) / des.core_wh
    l.orient[:] = orients
    out, rep = project.legalize_macros(des, l, halo=10.0, fallback=False)
    assert not rep.ok and rep.order == "area"
    out, rep = project.legalize_macros(des, l, halo=10.0)
    assert rep.ok and rep.order != "area" and rep.fallback_from[0]["order"] == "area"
    assert project.check_macros(des, out, 10.0)["ok"]
    assert np.array_equal(out.orient, l.orient)


def test_dense_ram_core_random_layouts_always_legal():
    des, lay = _ram_core()
    rng = np.random.default_rng(0)
    for t in range(300):
        l = lay.copy()
        l.pos[:] = rng.random((des.n_objects, 2))
        l.orient[:] = rng.integers(0, 8, des.n_objects)
        out, rep = project.legalize_macros(des, l, halo=10.0)
        assert rep.ok, (t, rep.failed, rep.fallback_from)
        if rep.order == "area":
            assert rep.fallback_from == []
