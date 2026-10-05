"""Cell-stage recipes, start positions and selection rules (heurbridge/cellstage)."""

import math
import sys
from pathlib import Path

import numpy as np
import pytest

from heurbridge.cellstage import recipe as R
from heurbridge.cellstage import positions as P
from heurbridge.cellstage import select as S
from heurbridge.cellstage.recipe import CellRecipe, CellStage, DensityCap, RouteAdjust
from heurbridge.core import synth
from heurbridge.heuristics.cell.cluster import cell_mask

ROOT = Path(__file__).resolve().parents[1]


def test_id_is_stable_and_ignores_the_name():
    a = CellRecipe(name="a", density=("addon", 0.2), hold="continue")
    b = CellRecipe(name="b", density=("addon", 0.20), hold="continue")
    assert a.id == b.id and len(a.id) == 12
    assert CellRecipe(density=("addon", 0.21), hold="continue").id != a.id
    assert CellRecipe(start="positions", source="hbgp").id != CellRecipe(start="positions", source="npz:a.npz").id
    assert CellRecipe().is_default() and not a.is_default()
    assert CellRecipe.from_dict(a.to_dict()) == a
    d = a.to_dict()
    d["hold"] = "restart"                          # settings changed but the stored id kept
    with pytest.raises(ValueError, match="does not match"):
        CellRecipe.from_dict(d)


@pytest.mark.parametrize("kw", [dict(start="middle"), dict(hold="freeze"), dict(start="centre", hold="keep"),
                                dict(density=("addon", 1.0)), dict(density=("absolute", 0.0)), dict(density=("x", 0.5)),
                                dict(pad_global=-1), dict(pad_detail=1.5), dict(gpl=(("-density", "0.5"),)),
                                dict(gpl=(("-skip_initial_place", None),)), dict(gpl=(("-bogus", "1"),)),
                                dict(density_caps=(((0, 0, 10, 10), 120.0),)), dict(density_caps=(((5, 0, 5, 10), 50.0),)),
                                dict(route_adjust=(((0, 0, 10, 10), "metal3", 1.5),)),
                                dict(route_adjust=(((0, 0, 10, 10), "metal 3", 0.5),)),
                                dict(start="positions"), dict(start="quadratic", source="hbgp"),
                                dict(start="positions", source="dreamplace")])
def test_invalid_recipes_are_refused(kw):
    with pytest.raises(ValueError):
        CellRecipe(**kw)


def test_make_vars_per_field():
    assert CellRecipe().make_vars() == []
    assert CellRecipe(density=("addon", 0.05)).make_vars() == ["PLACE_DENSITY_LB_ADDON=0.05"]
    assert CellRecipe(density=("absolute", 0.4)).make_vars() == ["PLACE_DENSITY=0.4", "PLACE_DENSITY_LB_ADDON="]
    assert CellRecipe(pad_global=1, pad_detail=0, timing_driven=False, routability_driven=True).make_vars() == [
        "CELL_PAD_IN_SITES_GLOBAL_PLACEMENT=1", "CELL_PAD_IN_SITES_DETAIL_PLACEMENT=0", "GPL_TIMING_DRIVEN=0",
        "GPL_ROUTABILITY_DRIVEN=1"]
    assert CellRecipe(hold="continue").make_vars() == ["GLOBAL_PLACEMENT_ARGS=-skip_initial_place"]
    assert CellRecipe(start="quadratic", hold="keep").make_vars() == [
        "GLOBAL_PLACEMENT_ARGS=-skip_initial_place -skip_nesterov_place"]
    r = CellRecipe(gpl=(("-timing_driven_net_reweight_overflow", "79 64 49"), ("-keep_resize_below_overflow", 0.3)))
    assert r.make_vars() == ["GLOBAL_PLACEMENT_ARGS=-timing_driven_net_reweight_overflow {79 64 49} "
                             "-keep_resize_below_overflow 0.3"]


def test_tcl_words_and_gpl_args_round_trip():
    assert R.tcl_words('-a {1 2 {3}} "x y" -b') == ["-a", "1 2 {3}", "x y", "-b"]
    text = "-timing_driven_net_reweight_overflow {79 64} -skip_initial_place -overflow 0.1"
    pairs = R.parse_gpl_args(text)
    assert pairs == [("-timing_driven_net_reweight_overflow", "79 64"), ("-skip_initial_place", None), ("-overflow", "0.1")]
    assert R.render_gpl_args(pairs) == text
    with pytest.raises(ValueError, match="unknown"):
        R.parse_gpl_args("-overflow 0.1 -nonsense")
    with pytest.raises(ValueError, match="no value"):
        R.parse_gpl_args("-overflow")
    with pytest.raises(ValueError, match="unbalanced"):
        R.tcl_words("{a b")


def test_make_vars_merge_keeps_the_campaign_settings():
    base = ("RTLMP_MAX_LEVEL=1", "GLOBAL_PLACEMENT_ARGS=-keep_resize_below_overflow 0.01")
    extra = CellRecipe(density=("absolute", 0.35), hold="continue", gpl=(("-overflow", "0.12"),)).make_vars()
    out = R.merge_make_vars(base, extra)
    assert out == ("RTLMP_MAX_LEVEL=1", "GLOBAL_PLACEMENT_ARGS=-keep_resize_below_overflow 0.01 -overflow 0.12 "
                   "-skip_initial_place", "PLACE_DENSITY=0.35", "PLACE_DENSITY_LB_ADDON=")
    over = R.merge_make_vars(base, ["GLOBAL_PLACEMENT_ARGS=-keep_resize_below_overflow 0.3"])
    assert over[1] == "GLOBAL_PLACEMENT_ARGS=-keep_resize_below_overflow 0.3"
    with pytest.raises(ValueError):
        R.merge_make_vars(("NOEQUALS",), [])


def test_density_caps_tcl_is_soft_and_clipped():
    r = CellRecipe(density_caps=(DensityCap((-5, 10, 50, 60), 40), ((100, 100, 120, 130), 0)))
    t = r.hint_tcl((0.0, 0.0, 110.0, 110.0))
    assert "0.0000 10.0000 50.0000 60.0000 40" in t and "100.0000 100.0000 110.0000 110.0000 0" in t
    assert "setSoft" in t and "setMaxDensity $_hb_d" in t and 'HB_DENSITY_CAPS created 2' in t
    assert CellRecipe().hint_tcl((0, 0, 1, 1)) == ""
    with pytest.raises(ValueError, match="outside"):
        CellRecipe(density_caps=(((200, 200, 300, 300), 50),)).hint_tcl((0, 0, 110, 110))


def test_fastroute_chain_sources_the_design_file_first():
    r = CellRecipe(route_adjust=(RouteAdjust((10, 10, 2000, 50), "metal3", 0.3),))
    t = r.fastroute_tcl("/x/fastroute.tcl", (0, 0, 800, 600))
    lines = t.splitlines()
    assert lines[1] == "source {/x/fastroute.tcl}"
    assert lines[2] == "set_global_routing_region_adjustment {10.0000 10.0000 800.0000 50.0000} -layer metal3 -adjustment 0.3"
    d = r.fastroute_tcl("", (0, 0, 800, 600))
    assert "set_global_routing_layer_adjustment $::env(MIN_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER)" in d
    assert "set_routing_layers -signal" in d and "HB_ROUTE_ADJUST applied 1" in d


def _small():
    des, ref = synth.make_design(seed=3, n_macros=4, n_cells=60, n_io=8)
    return des, ref


def test_cell_stage_prepare_positions_and_routing(tmp_path):
    des, ref = _small()
    cells = np.flatnonzero(cell_mask(des))
    seen = {}

    def pos_fn(design, layout):
        seen["called"] = True
        return cells, P.lower_left(design, layout, cells)

    ev = type("Ev", (), {"cluster_of": None, "flow_dir": "", "design_config": "", "make_vars_extra": ()})()
    r = CellRecipe(name="t", start="positions", source="hbgp", hold="keep",
                   density_caps=((tuple(des.core), 70),), route_adjust=((tuple(des.die), "metal3", 0.2),))
    cs = CellStage(r, positions=pos_fn, design_fastroute="", inspect_runs=False)
    text, mv = cs.prepare(ev, des, ref, "run1", tmp_path)
    assert seen and "HB_WARM_START placed %d cells" % len(cells) in text and "HB_DENSITY_CAPS created 1" in text
    assert mv[0] == "GLOBAL_PLACEMENT_ARGS=-skip_initial_place -skip_nesterov_place"
    assert mv[1] == "FASTROUTE_TCL=%s" % (tmp_path / "run1.fastroute.tcl").resolve()
    assert "metal3 -adjustment 0.2" in (tmp_path / "run1.fastroute.tcl").read_text()
    with pytest.raises(ValueError, match="cluster_of"):
        CellStage(CellRecipe(start="quadratic")).prepare(ev, des, ref, "run2", tmp_path)
    cs3 = CellStage(CellRecipe(start="positions", source="hbgp"), inspect_runs=False)
    cs3.positions = None                           # the source normally sets it
    with pytest.raises(ValueError, match="positions is not set"):
        cs3.prepare(ev, des, ref, "run3", tmp_path)


def test_orfs_evaluator_applies_the_recipe(tmp_path, monkeypatch):
    from heurbridge.eval import orfs
    from heurbridge.pipeline.evaluators import OrfsEvaluator
    des, ref = _small()
    got = {}

    def fake_run(run):
        got["run"] = run
        return {"returncode": 0, "variant": run.variant}
    monkeypatch.setattr(orfs, "run", fake_run)
    rec_ = CellRecipe(name="cap", density=("addon", 0.2), hold="continue", density_caps=((tuple(des.core), 60),))
    ev = OrfsEvaluator(fidelity=2, flow_dir="/flow", design_config="cfg.mk", keep_results=True,
                       make_vars_extra=("GLOBAL_PLACEMENT_ARGS=-keep_resize_below_overflow 0.01",),
                       cell_stage=CellStage(rec_, inspect_runs=False))
    rec = ev.evaluate(des, ref, "r0", tmp_path)
    assert got["run"].make_vars_extra == ("GLOBAL_PLACEMENT_ARGS=-keep_resize_below_overflow 0.01 -skip_initial_place",
                                          "PLACE_DENSITY_LB_ADDON=0.2")
    tcl = Path(got["run"].macro_tcl).read_text()
    assert tcl.index("place_macro") < tcl.index("HB_DENSITY_CAPS")
    assert rec["cell_stage"]["recipe_id"] == rec_.id and rec["cell_stage"]["make_vars"] == list(got["run"].make_vars_extra)
    plain = OrfsEvaluator(fidelity=2, flow_dir="/flow", design_config="cfg.mk", keep_results=True)
    assert "cell_stage" not in plain.evaluate(des, ref, "r1", tmp_path)
    assert got["run"].make_vars_extra == ()
    both = OrfsEvaluator(fidelity=2, keep_results=True, warm_start="quadratic",
                         cell_stage=CellStage(CellRecipe(), inspect_runs=False))
    with pytest.raises(ValueError, match="both set"):
        both.evaluate(des, ref, "r2", tmp_path)


def test_npz_positions_round_trip_and_checks(tmp_path):
    des, ref = _small()
    cells = np.flatnonzero(cell_mask(des))
    ll = P.lower_left(des, ref, cells)
    path = P.write_npz(tmp_path / "p.npz", des, cells, ll)
    c2, ll2, info = P.from_npz(path)(des, ref)
    assert np.array_equal(c2, cells) and np.allclose(ll2, ll)
    assert info["positions_file"] == "p.npz" and len(info["positions_sha256"]) == 16
    P.write_npz(tmp_path / "short.npz", des, cells[1:], ll[1:])
    with pytest.raises(ValueError, match="misses 1 standard cells"):
        P.from_npz(tmp_path / "short.npz")(des, ref)
    np.savez_compressed(tmp_path / "bad.npz", names=np.asarray(["nope"]), ll_um=np.zeros((1, 2)))
    with pytest.raises(ValueError, match="does not have"):
        P.from_npz(tmp_path / "bad.npz")(des, ref)


def test_race_summarize_and_pick():
    assert S.race({"a": 0.9, "b": math.inf, "c": 0.8, "d": 0.85}, 2) == ["c", "d"]
    assert S.race({"r0": 0.7, "a": 0.9, "c": 0.8}, 1, exclude=("r0",)) == ["c"]
    sys.path.insert(0, str(ROOT / "scripts"))
    import timing_safety_report as T
    pos = [(0.95, True, True), (0.97, True, False), (math.inf, False, False), (0.93, True, True)]
    mine, theirs = S.summarize(pos), T.summary([p + (0.0,) for p in pos])
    assert (mine["J"], mine["S"], mine["J_safe"]) == (theirs["J"], theirs["S"], theirs["J_safe"])
    arms = {"x": [(0.90, False, False)] * 6, "y": [(0.92, True, True)] * 6, "z": [(0.80, True, True)] * 5}
    assert S.pick(arms) == "y"                         # z has fewer positions; x pays 0.04 for missing every check
    assert S.pick({"f": [(math.inf, False, False)]}) is None


def test_band_below_and_go_rule():
    assert S.band_below([0.9, 0.91], [0.95, math.inf]) and not S.band_below([0.9, math.inf], [0.95, 1.0])
    ok = lambda js: [(j, True, True) for j in js]
    r0 = ok([1.0, 1.01, 1.02, 0.99, 1.0, 1.03])
    lower, other = ok([0.9] * 6), ok([0.95, 1.05, 1.0, 1.0, 0.97, 0.99])
    res = {"d1": {"L1": {"R0": r0, "R1": lower, "R2": other}, "L2": {"R0": r0, "R1": other, "R2": lower}},
           "d2": {"L1": {"R0": r0, "R1": lower}, "L2": {"R0": r0, "R1": lower}}}
    g = S.go_rule(res, "R0")
    assert g["go"] and g["a"] and g["designs_differ"] == ["d1"] and sorted(g["designs_below"]) == ["d1", "d2"]
    same = {"d1": {"L1": {"R0": r0, "R1": lower}, "L2": {"R0": r0, "R1": lower}},
            "d2": {"L1": {"R0": r0, "R1": lower}, "L2": {"R0": r0, "R1": lower}}}
    assert not S.go_rule(same, "R0")["go"] and not S.go_rule(same, "R0")["b"]
    failing = ok([1.0] * 5) + [(math.inf, False, False)]
    rescue = {"d1": {"L1": {"R0": failing, "R1": ok([1.02] * 6)}, "L2": {"R0": r0, "R1": ok([1.1] * 6)}}}
    g2 = S.go_rule(rescue, "R0")                   # (a) holds through the rescued failure, but both layouts pick R0
    assert g2["failures_removed"] == [("d1", "L1", "R1")] and g2["a"] and not g2["b"] and not g2["go"]
    rescue["d1"]["L2"]["R1"] = ok([0.9] * 6)       # now L2 picks R1: (b) holds on d1
    assert S.go_rule(rescue, "R0")["go"]
    with pytest.raises(ValueError, match="positions"):
        S.go_rule({"d": {"L": {"R0": r0, "R1": ok([0.9] * 5)}}}, "R0")
    with pytest.raises(ValueError, match="no run of the default"):
        S.go_rule({"d": {"L": {"R1": r0}}}, "R0")


def test_positions_from_source():
    assert callable(P.from_source("hbgp")) and callable(P.from_source("npz:x.npz"))
    with pytest.raises(ValueError):
        P.from_source("dreamplace")
    cs = CellStage(CellRecipe(start="positions", source="hbgp", hold="continue"))
    assert callable(cs.positions)


def test_log_marks_and_drift(tmp_path):
    (tmp_path / "2_3_floorplan_macro.log").write_text("HB_WARM_START placed 5 cells\nHB_DENSITY_CAPS created 2\n")
    (tmp_path / "5_1_grt.log").write_text("x\nHB_ROUTE_ADJUST applied 1\n")
    (tmp_path / "3_3_place_gp.log").write_text("nothing of ours\n")
    assert R.log_marks(tmp_path) == {"2_3_floorplan_macro": {"HB_WARM_START": 1, "HB_DENSITY_CAPS": 1},
                                     "5_1_grt": {"HB_ROUTE_ADJUST": 1}}
    names, ll = ["a", "b", "c"], np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]])
    d = R.drift(names, ll, {"a": (0.0, 0.0), "b": (4.0, 5.0)})
    assert d["compared"] == 2 and d["missing"] == 1 and d["max_um"] == 5.0 and d["moved_share"] == 0.5
    assert R.drift(names, ll, {}) == {"compared": 0, "missing": 3}


def test_npz_dir_finds_the_file_of_the_layout_evaluated(tmp_path):
    des, ref = _small()
    cells = np.flatnonzero(cell_mask(des))
    key = P.layout_key(des, ref)
    P.write_npz(tmp_path / ("%s.npz" % key), des, cells, P.lower_left(des, ref, cells))
    c, ll, info = P.from_source("npzdir:%s" % tmp_path)(des, ref)
    assert np.array_equal(c, cells) and info["positions_file"] == "%s.npz" % key
    other = ref.copy()
    mm = des.is_macro & ~des.is_fixed
    other.pos[np.flatnonzero(mm)[0]] += 0.001
    assert P.layout_key(des, other) != key
    with pytest.raises(FileNotFoundError, match="no precomputed positions"):
        P.from_npz_dir(tmp_path)(des, other)
    assert CellRecipe(start="positions", source="npzdir:x", hold="keep").source == "npzdir:x"


def test_dreamplace_positions_hold_the_macros(tmp_path, monkeypatch):
    from heurbridge.eval import dreamplace as D
    des, ref = _small()

    def fake_run(param, work, timeout=3600, move_macro=False):
        aux = Path(param["aux_input"])
        pl_in = aux.with_suffix(".pl").read_text().splitlines()
        out = Path(param["result_dir"]) / des.id
        out.mkdir(parents=True, exist_ok=True)
        lines = []
        for line in pl_in:
            p = line.split()
            if len(p) >= 3 and p[0].startswith("o") and p[0][1:].isdigit():
                i = int(p[0][1:])
                x, y = int(p[1]), int(p[2])
                if cell_mask(des)[i]:
                    x, y = x + 5000, y + 3000           # cells moved by 5 um, 3 um
                elif des.is_macro[i] and fake_run.move:
                    x += 2000
                lines.append("%s %d %d : N" % (p[0], x, y))
        (out / ("%s.gp.pl" % des.id)).write_text("\n".join(lines) + "\n")
        return 0, "ok", 1.0
    fake_run.move = False
    monkeypatch.setattr(D, "run_placer", fake_run)
    cells, ll, info = P.dreamplace(des, ref, tmp_path / "w")
    assert np.array_equal(cells, np.flatnonzero(cell_mask(des)))
    assert info["converged"] is False and info["iterations"] is None     # the fake log has no iterations
    assert info["macro_max_shift_um"] < 1e-3                 # the bookshelf copy rounds to 1/scale
    # placed cells started at the core centre (the reference layout's cells are placed, so: their own positions)
    assert np.isfinite(ll).all()
    fake_run.move = True
    with pytest.raises(RuntimeError, match="moved a fixed macro"):
        P.dreamplace(des, ref, tmp_path / "w2")


def test_dreamplace_convergence_from_its_log():
    it = "[INFO   ] DREAMPlace - iteration %4d, ( %d,  0,  0), Obj 1E+07, DensityWeight 1E-01, wHPWL 1E+07, Overflow %s, MaxDensity 1.0E+00, gamma 1E+01, time 2ms"
    ok = "\n".join([it % (0, 0, "1.000000E+00"), it % (547, 547, "6.991584E-02"), "[INFO   ] done"])
    assert P.dreamplace_convergence(ok, 0.07) == {"iterations": 547, "overflow": 0.06991584, "diverged": False,
                                                   "converged": True}
    stuck = "\n".join([it % (999, 999, "2.159000E-01")])
    assert P.dreamplace_convergence(stuck, 0.07)["converged"] is False
    div = ok + "\n[ERROR  ] DREAMPlace - possible DIVERGENCE detected, roll back to the best position recorded"
    assert P.dreamplace_convergence(div, 0.07)["diverged"] and not P.dreamplace_convergence(div, 0.07)["converged"]
