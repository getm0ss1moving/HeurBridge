"""scripts/beat_tool_demo.py: the local-search moves start from a layout and change exactly one decision each."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def test_moves_change_one_macro_or_swap_a_pair():
    from heurbridge.core import synth
    import beat_tool_demo as B
    des, lay = synth.make_design(seed=3, n_macros=8, n_cells=30, n_io=6)
    mm = np.flatnonzero(des.is_macro & ~des.is_fixed)
    out = B.moves(des, lay, np.random.default_rng(0), 40)
    assert len(out) == 40
    for what, new in out:
        changed = np.flatnonzero((np.abs(new.pos - lay.pos) > 1e-12).any(1) | (new.orient != lay.orient))
        assert set(changed) <= set(mm)                         # only movable macros move
        assert len(changed) == (2 if what == "swap" else 1) or (what.startswith("shift") and len(changed) <= 1)
        assert np.all(new.pos[mm] >= 0) and np.all(new.pos[mm] <= 1)


def test_refiner_pair_moves_are_shifts_only():
    """scripts/tool_ls_pairs.py: training targets come from shifts only (learnable by the bridge: no swap, no flip)."""
    from heurbridge.core import synth
    import tool_ls_pairs as P
    des, lay = synth.make_design(seed=5, n_macros=8, n_cells=30, n_io=6)
    for new in P.shift_moves(des, lay, np.random.default_rng(1), 30):
        changed = np.flatnonzero((np.abs(new.pos - lay.pos) > 1e-12).any(1))
        assert len(changed) <= 1 and np.array_equal(new.orient, lay.orient)


def test_raw_loader_applies_the_ispd_convention(monkeypatch):
    """scripts/tool_refine_eval.load_raw: ISPD2005 macros become movable (the seeding campaign's MMS convention)."""
    import types
    import tool_refine_eval as T
    from heurbridge.core import bookshelf

    class FakeDesign:
        def __init__(self):
            self.is_fixed = np.array([True, True, False])
            self.is_macro = np.array([True, False, False])

        def schema_hash(self):
            return "h"
    monkeypatch.setattr(bookshelf, "load_bookshelf", lambda path, family: (FakeDesign(), types.SimpleNamespace(schema="")))
    d, l = T.load_raw("ispd2005", "adaptec1")
    assert list(d.is_fixed) == [False, True, False] and l.schema == "h"
    d, l = T.load_raw("ibm", "ibm01")
    assert list(d.is_fixed) == [True, True, False]                 # IBM: unchanged


def test_best_of_k_picks_by_the_selection_seed_and_keeps_failures():
    """scripts/relink_eval.best_of: cyclic window, pick by the selection seed, judge by the fresh seeds; failed = +inf."""
    import relink_eval as R
    inf = float("inf")
    J_sel, J_fresh = [0.50, inf, 0.40, 0.60], [0.45, inf, 0.47, 0.44]
    assert R.best_of(0, 2, J_sel, J_fresh) == 0.45                 # the failed run is never picked over a finite one
    assert R.best_of(1, 2, J_sel, J_fresh) == 0.47
    assert R.best_of(3, 2, J_sel, J_fresh) == 0.45                 # cyclic: positions 3, 0
    assert R.best_of(1, 1, J_sel, J_fresh) == inf                  # every candidate failed
    assert R.best_of(0, 4, J_sel, J_fresh) == 0.47


def test_relink_confirm_units_name_missing_jobs_and_refuse_two_sources(tmp_path):
    """scripts/relink_confirm.units: 64 units; a missing design is +inf by name; two sources for a design stop it."""
    import json
    import math
    import pytest
    import relink_confirm as C
    d = tmp_path / "rlc_a" / "runs"
    (d / "relink" / "adaptec1").mkdir(parents=True)
    (d / "tool_runs" / "adaptec1").mkdir(parents=True)
    rel, tool = [], []
    for s in range(8):
        tool.append({"tool_seed": s, "J_select": {"tool": 0.4}, "cost_s": {"tool": 10.0, "f1": 5.0}})
        rel.append({"tool_seed": s, "partner_seed": (s + 1) % 8, "failures": [], "cost_s": {"relink_extra": 7.0},
                    "J_eval": {"tool": 0.45, "best2": 0.44, "best3": 0.43, "best4": 0.42, "relink": 0.41}})
    (d / "relink" / "adaptec1" / "rows.jsonl").write_text("\n".join(json.dumps(r) for r in rel) + "\n")
    (d / "tool_runs" / "adaptec1" / "rows.jsonl").write_text("\n".join(json.dumps(r) for r in tool) + "\n")
    U, fails, srcs = C.units(tmp_path, "rlc_")
    assert len(U) == 64 and len(srcs) == 2
    a1 = [u for u in U if u["design"] == "adaptec1"]
    assert all(u["relink"] == 0.41 and u["best4"] == 0.42 for u in a1)
    assert a1[0]["cost_relink"] == 2 * 15.0 + 7.0 and a1[0]["cost_best4"] == 4 * 15.0
    assert all(math.isinf(u["relink"]) for u in U if u["design"] != "adaptec1")
    assert sum("no relink row" in f for f in fails) == 56
    dup = tmp_path / "rlc_b" / "runs" / "relink" / "adaptec1"
    dup.mkdir(parents=True)
    (dup / "rows.jsonl").write_text("")
    with pytest.raises(SystemExit):
        C.units(tmp_path, "rlc_")


def test_blockwise_symmetric_matching_is_a_permutation_within_the_group():
    """bridge.data.match_symmetric(block=...): large groups are matched within median-split blocks; exact otherwise."""
    import types
    from heurbridge.bridge import data as BD
    from heurbridge.bridge.graph import KIND_MOV
    rng = np.random.default_rng(0)
    n = 60
    g = types.SimpleNamespace(n=n + 2, area_w=np.ones(n + 2), group=np.r_[np.zeros(n, int), -1, -1],
                              kind=np.full(n + 2, KIND_MOV))
    xh = rng.random((n + 2, 2))
    el = rng.random((n + 2, 2))
    ex, pe = BD.match_symmetric(g, xh, el)
    bx, pb = BD.match_symmetric(g, xh, el, block=8)
    assert sorted(pb[:n]) == list(range(n)) and list(pb[n:]) == [n, n + 1]   # a permutation inside the group only
    cost = lambda x: ((xh[:n] - x[:n]) ** 2).sum()
    assert cost(ex) <= cost(bx) + 1e-12 < cost(el)                          # exact is optimal; blocks still help
    _, pfull = BD.match_symmetric(g, xh, el, block=n)
    assert np.array_equal(pfull, pe)                                        # block >= group size: exact


def test_barycenter_undoes_permutations_of_interchangeable_macros():
    """scripts/consensus_eval.barycenter: the average of matched layouts; relabelled copies of one layout give it back."""
    import types
    import consensus_eval as C
    from heurbridge.bridge.graph import KIND_MOV
    rng = np.random.default_rng(1)
    n = 12
    g = types.SimpleNamespace(n=n, area_w=np.ones(n), group=np.r_[np.zeros(6, int), np.ones(6, int)],
                              kind=np.full(n, KIND_MOV))
    x = rng.random((n, 2))
    p = np.r_[rng.permutation(6), 6 + rng.permutation(6)]           # relabel inside each group
    assert np.allclose(C.barycenter(g, [x, x[p], x]), x)
    y = x + 0.01
    assert np.allclose(C.barycenter(g, [x, y[p]]), x + 0.005)         # matched first, then averaged


def test_flip_pass_lowers_hpwl_and_keeps_positions():
    """scripts/flip_eval.flip_pass: footprint-preserving orientations only, positions untouched, HPWL not worse."""
    from heurbridge.core import synth
    from heurbridge.core.design import hpwl
    import flip_eval as F
    for seed in (0, 1, 2):
        des, lay = synth.make_design(seed=seed, n_macros=10, n_cells=60, n_io=8)
        o, st = F.flip_pass(des, lay, passes=5, max_deg=10 ** 6)
        mm = des.is_macro & ~des.is_fixed
        assert np.array_equal(o[~mm], lay.orient[~mm])                      # only movable macros
        assert set(np.unique(o[mm])) <= set(F.FLIPS) | set(np.unique(lay.orient[mm]))
        new = lay.copy()
        new.orient = o
        assert hpwl(des, new) <= hpwl(des, lay) + 1e-9
        assert st["macros_changed"] == int((o != lay.orient).sum())


def test_trackb_test_shifts_fall_back_in_order_for_both_arms(monkeypatch):
    """scripts/run_seed_orfs.tb_pairs: the six pre-registered shifts; a shift illegal for either arm is replaced by the
    next fallback for both arms; a slot with no legal shift left is reported, never silently filled."""
    import run_seed_orfs as R
    bad = {("c", (2, 0)), ("r", (3, 0)), ("c", (0, 2)), ("r", (-3, 0)), ("c", (0, -2))}
    monkeypatch.setattr(R, "shift_exact", lambda des, lay, dx, dy: None if (lay, (dx, dy)) in bad else (lay, (dx, dy)))
    out = R.tb_pairs(None, "c", "r")
    assert [o[1] for o in out] == [None, (-2, 0), (0, -1), None, (1, 1), (-1, -1)]
    assert all(o[2] == ("c", o[1]) and o[3] == ("r", o[1]) for o in out if o[1] is not None)


def test_external_arm_pick_prefers_admitted_then_before_gates_then_f1():
    """scripts/run_seed_orfs.ext_pick: DREAMPlace's layout for the three-way comparison is picked as HeurBridge's
    candidate was (the best f2 layout admitted under D6); without an admitted one, the best J before the gates; with
    every f2 run failed, the best by f1; each named."""
    import math
    import run_seed_orfs as R
    inf = math.inf
    assert R.ext_pick([(0.95, 0.95, 3), (inf, 0.90, 5), (0.97, 0.97, 1)], 7) == (3, "the best f2 layout admitted under D6")
    k, why = R.ext_pick([(inf, 0.99, 3), (inf, 0.98, 5)], 7)
    assert k == 5 and why.startswith("no f2 layout admitted")
    k, why = R.ext_pick([(inf, inf, 3), (inf, inf, 5)], 7)
    assert k == 7 and why.startswith("every f2 run failed")


def test_external_arm_jsafe_pick_charges_failed_checks_then_falls_back_to_f1():
    """scripts/run_seed_orfs.jsafe_pick (D13 a, TW#5): the lowest one-position J_safe against the tool's unshifted
    replay, so a lower J with a failed timing check loses to a slightly higher J that passes both; ties by J; with
    every f2 run failed, the best by f1."""
    import pytest
    import run_seed_orfs as R
    from heurbridge.paths import eda_dir
    if eda_dir() is None:
        pytest.skip("needs eda/harness/metrics_schema.py")
    from heurbridge.eval import cost
    rec = {"detailed_wirelength_um": 1000.0, "vias": 500, "gr_overflow_total": 0, "setup_tns_ns": 0.0,
           "total_power_w": 0.01, "setup_wns_ns": 1.0, "hold_wns_ns": 0.05, "drc_violations": 0, "returncode": 0}
    base = cost.Baseline.from_records("d", [rec, rec])
    tool = {"setup_wns_ns": 1.0, "hold_wns_ns": 0.05}
    low_j_bad_hold = {"status": "ok", "record": dict(rec, detailed_wirelength_um=990.0, hold_wns_ns=0.0)}
    safe = {"status": "ok", "record": dict(rec, detailed_wirelength_um=995.0)}
    failed = {"status": "eval_failed", "record": {"returncode": "timeout"}}
    assert R.jsafe_pick([(2, low_j_bad_hold), (4, safe), (6, failed)], tool, base, 9) == \
        (4, "the lowest one-position J_safe (D13 a)")
    assert R.jsafe_pick([(2, failed), (4, failed)], tool, base, 9) == (9, "every f2 run failed: the best by f1")


def test_density_confirm_units_pair_the_seed_with_rl1s_best_of_four(tmp_path):
    """scripts/density_confirm.units: unit (design, s) = the density-d* run of seed s vs RL#1's best of 4 from seed s;
    a missing density row is +inf by name."""
    import json
    import math
    import density_confirm as C
    m = tmp_path / "rtd_a" / "runs" / ("tool_runs_td%g" % C.TD) / "adaptec1"
    r = tmp_path / "rlc_a" / "runs" / "relink" / "adaptec1"
    t = tmp_path / "rlc_a" / "runs" / "tool_runs" / "adaptec1"
    for p in (m, r, t):
        p.mkdir(parents=True)
    mrows = [{"tool_seed": s, "J_select": {"tool": 0.4}, "J_eval": {"tool": 0.40 + s / 1000}, "cost_s": {"tool": 30.0, "f1": 20.0}}
             for s in range(7)]                                     # seed 7 missing
    rrows = [{"tool_seed": s, "J_eval": {"tool": 0.45, "best2": 0.445, "best4": 0.44}} for s in range(8)]
    trows = [{"tool_seed": s, "J_select": {"tool": 0.45 if s else 0.3}, "J_eval": {"tool": 0.45},
              "cost_s": {"tool": 20.0, "f1": 20.0}} for s in range(8)]
    for p, rows in ((m, mrows), (r, rrows), (t, trows)):
        (p / "rows.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows))
    U, fails, srcs = C.units(tmp_path, "rtd_", "rlc_")
    a1 = [u for u in U if u["design"] == "adaptec1"]
    assert len(U) == 64 and [u["method"] for u in a1[:2]] == [0.40, 0.401] and a1[0]["best4_09"] == 0.44
    assert math.isinf(a1[7]["method"]) and any("adaptec1 seed 7" in f for f in fails)
    assert a1[0]["cost_method"] == 50.0 and a1[0]["cost_best4"] == 160.0
    assert a1[0]["portfolio"] == 0.45 and a1[1]["portfolio"] == 0.401   # picked by the selection seed (seed 0: 0.9 run)
    assert a1[7]["portfolio"] == 0.45 and a1[0]["best2_09"] == 0.445     # a failed density run falls back to 0.9


def test_portfolio_retest_units(tmp_path):
    """scripts/portfolio_retest_confirm.units: method = better of T_s at 0.9 and 0.6, comparator = better of T_s and
    T_(s+1) at 0.9, by the selection seed; a failed run is +inf and never picked; a missing design is named."""
    import json
    import math
    import portfolio_retest_confirm as C
    for t, rows in ((0.9, [{"tool_seed": s, "J_select": {"tool": 0.45 - s / 1000}, "J_eval": {"tool": 0.45 - s / 1000}}
                           for s in range(8)]),
                    (0.6, [{"tool_seed": 0, "failure": "dreamplace_rc_1"}] +
                          [{"tool_seed": s, "J_select": {"tool": 0.40}, "J_eval": {"tool": 0.41}} for s in range(1, 8)])):
        p = tmp_path / "rc4_x" / "runs" / ("tool_runs_td%g" % t) / "adaptec1"
        p.mkdir(parents=True)
        (p / "rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    U, fails, srcs = C.units(tmp_path, "rc4_")
    a1 = [u for u in U if u["design"] == "adaptec1"]
    assert len(U) == 56 and len(srcs) == 2
    assert a1[0]["method"] == 0.45 and a1[0]["comparator"] == 0.449         # the failed 0.6 run is never picked
    assert a1[1]["method"] == 0.41 and a1[1]["picked_06"]
    assert a1[7]["comparator"] == 0.443                                     # cyclic partner: seed 0 (0.45) vs seed 7
    assert any("adaptec1 seed 0 at 0.6: dreamplace_rc_1" in f for f in fails)
    assert all(math.isinf(u["method"]) for u in U if u["design"] == "bigblue4")


def test_timing_aware_search_score():
    """scripts/run_seed_orfs.tls_score (D13 b): J before the gates plus lam times the share of the setup and hold checks
    that miss the margin over the gate threshold; a failed flow is +inf."""
    import math
    import pytest
    import run_seed_orfs as R
    g = lambda s, h: {"setup": {"candidate": s, "base": -0.5, "guard_ns": 0.02},
                      "hold": {"candidate": h, "base": 0.015, "guard_ns": 0.02}}
    safe = {"status": "ok", "J_raw": 0.90, "gates": g(-0.48, 0.03)}        # clears -0.52 and -0.005 by 0.04, 0.035
    assert R.tls_score(safe, 0.03, 0.04) == pytest.approx(0.90)
    one = {"status": "ok", "J_raw": 0.89, "gates": g(-0.50, 0.03)}         # setup clears by 0.02 only
    assert R.tls_score(one, 0.03, 0.04) == pytest.approx(0.91)
    both = {"status": "ok", "J_raw": 0.85, "gates": g(-0.53, -0.01)}       # both miss
    assert R.tls_score(both, 0.03, 0.04) == pytest.approx(0.89)
    assert math.isinf(R.tls_score({"status": "eval_failed", "J": math.inf}, 0.03, 0.04))
