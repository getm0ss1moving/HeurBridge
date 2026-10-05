"""Hint programs of the cell stage (heurbridge/cellstage/hints.py) and their path through CellRecipe and CellStage."""

import numpy as np
import pytest

from heurbridge.cellstage import hints as H
from heurbridge.cellstage.recipe import CellRecipe, CellStage
from heurbridge.core import synth
from heurbridge.core.design import Layout


def _area(rects):
    return sum((r[2] - r[0]) * (r[3] - r[1]) for r in rects)


def _overlap(a, b):
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def _disjoint(rects):
    return all(_overlap(a, b) == 0 for i, a in enumerate(rects) for b in rects[i + 1:])


def _design(boxes):
    """A synthetic design whose macros are exactly ``boxes`` (xl, yl, xh, yh) in a 300 x 200 um core."""
    des, ref = synth.make_design(seed=5, n_macros=len(boxes), n_cells=40, n_io=4)
    des.core = des.die = (0.0, 0.0, 300.0, 200.0)
    m = np.flatnonzero(des.is_macro)
    assert len(m) == len(boxes)
    pos = ref.pos.copy()
    for k, (xl, yl, xh, yh) in zip(m, boxes):
        des.size[k] = (xh - xl, yh - yl)
        pos[k] = des.to_norm(np.array([(xl + xh) / 2, (yl + yh) / 2]))
    orient = ref.orient.copy()
    orient[m] = 0
    return des, Layout(pos, orient, ref.schema)


A, B, C = (20.0, 20.0, 60.0, 60.0), (90.0, 30.0, 130.0, 70.0), (70.0, 40.0, 80.0, 50.0)


def test_disjoint_union_covers_the_union_once():
    rects = [(0, 0, 10, 10), (5, 5, 15, 15), (20, 0, 30, 5)]
    out = H.disjoint_union(rects)
    assert _disjoint(out) and _area(out) == pytest.approx(100 + 100 - 25 + 50)
    cut = H.disjoint_union(rects, holes=[(4, 4, 6, 6)], box=(0, 0, 25, 20))
    assert _disjoint(cut) and _area(cut) == pytest.approx(175 - 4 + 25)
    assert H.disjoint_union([(0, 0, 1, 1)], box=(2, 2, 3, 3)) == []
    assert H.disjoint_union(rects) == H.disjoint_union(list(reversed(rects)))


def test_channels_between_facing_macros_and_core_edges():
    des, lay = _design([A, B])
    got = H.channel_rects(des, lay, max_gap=35.0)
    assert np.allclose(H.macro_boxes(des, lay), [A, B])
    want = [(20, 0, 60, 20), (90, 0, 130, 30), (0, 20, 20, 60), (60, 30, 90, 60)]
    assert sorted(got) == sorted(tuple(map(float, w)) for w in want)
    assert H.channel_rects(des, lay, max_gap=35.0, min_gap=25.0) == [(90.0, 0.0, 130.0, 30.0), (60.0, 30.0, 90.0, 60.0)]
    assert H.channel_rects(des, lay, max_gap=15.0) == []


def test_a_macro_inside_a_channel_is_cut_out():
    des, lay = _design([A, B, C])
    got = H.channel_rects(des, lay, max_gap=35.0)
    assert _disjoint(got)
    assert all(_overlap(r, m) == 0 for r in got for m in (A, B, C))
    assert _area(got) == pytest.approx(40 * 20 + 40 * 30 + 20 * 40 + (30 * 30 - 10 * 10))


def test_recipe_programs_identity_and_checks():
    r = CellRecipe(name="R8", programs=(("channel_caps", {"max_gap": 60, "max_density": 50}),))
    assert r.programs == (("channel_caps", (("max_density", 50.0), ("max_gap", 60.0))),)
    assert CellRecipe.from_dict(r.to_dict()) == r
    assert r.id == CellRecipe(programs=(("channel_caps", (("max_gap", 60.0), ("max_density", 50))),)).id
    assert r.id != CellRecipe(programs=(("channel_caps", {"max_gap": 61, "max_density": 50}),)).id
    assert "programs" not in CellRecipe().settings()          # ids of recipes without programs are unchanged
    for bad in [("rings", {"max_gap": 1}), ("channel_caps", {"max_gap": 60}),
                ("channel_caps", {"max_gap": 60, "max_density": 50, "width": 2}),
                ("channel_caps", {"max_gap": 60, "max_density": 150}),
                ("channel_caps", {"max_gap": 60, "max_density": 50, "min_gap": 60})]:
        with pytest.raises(ValueError):
            CellRecipe(programs=(bad,))


def test_cell_stage_writes_and_records_the_program_caps(tmp_path):
    des, lay = _design([A, B, C])
    ev = type("Ev", (), {"cluster_of": None, "flow_dir": "", "design_config": "", "make_vars_extra": ()})()
    r = CellRecipe(name="R8", density_caps=(((250, 150, 300, 200), 70),),
                   programs=(("channel_caps", {"max_gap": 35, "max_density": 50}),))
    cs = CellStage(r, inspect_runs=False)
    text, mv = cs.prepare(ev, des, lay, "run1", tmp_path)
    n = len(H.channel_rects(des, lay, 35.0))
    assert mv == [] and "HB_DENSITY_CAPS created %d" % (n + 1) in text
    assert "250.0000 150.0000 300.0000 200.0000 70" in text.splitlines()[4]   # the recipe's own cap first
    got = cs.inspect(type("Run", (), {"variant": "run1"})())
    caps = got["program_hints"]["density_caps"]
    assert len(caps) == n and all(c[1] == 50.0 for c in caps)
    assert got["program_hints"]["cap_area_um2"] == pytest.approx(_area(H.channel_rects(des, lay, 35.0)))
    assert cs.inspect(type("Run", (), {"variant": "run1"})()) == {}          # recorded once per run
