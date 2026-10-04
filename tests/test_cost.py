"""T1.6: J and gates against hand-computed values."""

import math

import pytest

from heurbridge.eval import cost
from heurbridge.paths import eda_dir

pytestmark = pytest.mark.skipif(eda_dir() is None, reason="needs eda/harness/metrics_schema.py")

BASE_RECS = [
    {"detailed_wirelength_um": 1000.0, "vias": 500, "gr_overflow_total": 0, "setup_tns_ns": -10.0,
     "total_power_w": 0.010, "setup_wns_ns": -0.50, "hold_wns_ns": 0.10},
    {"detailed_wirelength_um": 1100.0, "vias": 520, "gr_overflow_total": 2, "setup_tns_ns": -12.0,
     "total_power_w": 0.011, "setup_wns_ns": -0.40, "hold_wns_ns": 0.12},
    {"detailed_wirelength_um": 900.0, "vias": 480, "gr_overflow_total": 4, "setup_tns_ns": -8.0,
     "total_power_w": 0.009, "setup_wns_ns": -0.60, "hold_wns_ns": 0.08},
]


def base():
    return cost.Baseline.from_records("d", BASE_RECS)


def test_baseline_is_median():
    b = base()
    assert b.values == {"rwl": 1000.0, "via": 500, "of": 2, "tns": -10.0, "power": 0.010}
    assert b.timing == {"setup_wns_ns": -0.50, "hold_wns_ns": 0.10}


def test_baseline_record_scores_one():
    rec = dict(BASE_RECS[0], gr_overflow_total=2, drc_violations=0)
    r = cost.evaluate(rec, base(), fidelity=2)
    # rWL 1, via 1, (1+2)/(1+2)=1, (1+10)/(1+10)=1, P 1  ->  J = 1
    assert r.J == pytest.approx(1.0) and r.admissible and not r.partial


def test_hand_computed_J():
    rec = {"detailed_wirelength_um": 900.0, "vias": 550, "gr_overflow_total": 0, "setup_tns_ns": -5.0,
           "total_power_w": 0.012, "setup_wns_ns": -0.51, "hold_wns_ns": 0.09, "drc_violations": 0}
    r = cost.evaluate(rec, base(), fidelity=2)
    expect = 0.30 * 0.9 + 0.05 * 1.1 + 0.15 * (1 / 3) + 0.30 * (6 / 11) + 0.20 * 1.2
    assert r.J == pytest.approx(expect, rel=1e-12)
    assert r.J_inf == r.J and r.admissible
    d = cost.decompose(r, cost.evaluate(dict(BASE_RECS[0], gr_overflow_total=2, drc_violations=0), base()))
    assert d["rwl"]["raw_delta"] == -100.0 and d["rwl"]["dJ"] == pytest.approx(0.30 * (0.9 - 1.0))


def test_gates():
    ok = {"detailed_wirelength_um": 1000.0, "vias": 500, "gr_overflow_total": 2, "setup_tns_ns": -10.0,
          "total_power_w": 0.010, "setup_wns_ns": -0.52, "hold_wns_ns": 0.08, "drc_violations": 0}
    assert cost.evaluate(ok, base()).gates["setup"]["status"] == "pass"       # -0.52 >= -0.50 - 0.02
    bad = dict(ok, setup_wns_ns=-0.53)
    r = cost.evaluate(bad, base())
    assert r.gates["setup"]["status"] == "fail" and math.isinf(r.J_inf) and not r.admissible
    bad = dict(ok, hold_wns_ns=-0.01)                                          # base hold >= 0 -> must stay >= 0
    r = cost.evaluate(bad, base())
    assert r.gates["hold"]["reason"] == "new_violation_from_met_baseline" and math.isinf(r.J_inf)
    bad = dict(ok, drc_violations=3)
    assert math.isinf(cost.evaluate(bad, base()).J_inf)
    bad = dict(ok, lvs_errors=1)
    assert math.isinf(cost.evaluate(bad, base(), fidelity=3).J_inf)



def test_f1_gates_reported_not_enforced():
    """cost_v2 (2026-09-28): at f0/f1 timing and DRC gates are reported, only a failed flow is enforced."""
    bad = {"gr_wl": 1000.0, "gr_overflow_total": 2, "setup_tns_ns": -10.0, "total_power_w": 0.010,
           "setup_wns_ns": -0.53, "hold_wns_ns": -0.01}                   # setup and hold both fail the guard
    r1 = cost.evaluate(bad, base(), fidelity=1)
    assert r1.gates["setup"]["status"] == "fail" and r1.gates["setup"]["enforced"] is False
    assert r1.gates["hold"]["status"] == "fail" and math.isfinite(r1.J_inf) and r1.J_inf == r1.J
    r2 = cost.evaluate(dict(bad, detailed_wirelength_um=1000.0, vias=500, drc_violations=0), base(), fidelity=2)
    assert r2.gates["setup"]["enforced"] is True and math.isinf(r2.J_inf) and not r2.admissible
    flow = cost.evaluate(dict(bad, returncode=2), base(), fidelity=1)
    assert flow.gates["flow"]["enforced"] is True and math.isinf(flow.J_inf)

def test_missing_fields_are_unchecked_not_passed():
    rec = {"detailed_wirelength_um": 1000.0, "vias": 500, "setup_tns_ns": -10.0, "total_power_w": 0.010,
           "setup_wns_ns": -0.5}
    r = cost.evaluate(rec, base(), fidelity=2)
    assert r.partial and not r.admissible
    assert "of" in r.unchecked and "gate:hold" in r.unchecked and "gate:drc" in r.unchecked
    assert r.gates["hold"]["status"] == "unchecked"
    r3 = cost.evaluate(dict(rec, gr_overflow_total=2, hold_wns_ns=0.1, drc_violations=0), base(), fidelity=3)
    assert not r3.admissible and "gate:lvs" in r3.unchecked


def test_legacy_fields_go_through_metrics_schema():
    # old phase0 raw dict: setup from DRT::worst_slack_max, hold from DRT::worst_slack_min
    rec = {"raw": {"DRT::worst_slack_max": -0.50, "DRT::worst_slack_min": 0.10, "DRT::tns_max": -10.0},
           "detailed_wirelength_um": 1000.0, "vias": 500, "gr_overflow_total": 2, "total_power_w": 0.010,
           "drc_violations": 0}
    r = cost.evaluate(rec, base())
    assert r.gates["setup"]["candidate"] == -0.50 and r.gates["hold"]["candidate"] == 0.10
    assert r.J == pytest.approx(1.0)


def test_gate_reference_same_path_replay():
    """cost_v3 (2026-09-29): Track-B timing gates compare with the same-path replay band (median), J unchanged."""
    b = base()
    ok = {"detailed_wirelength_um": 1000.0, "vias": 500, "gr_overflow_total": 2, "setup_tns_ns": -10.0,
          "total_power_w": 0.010, "setup_wns_ns": -0.60, "hold_wns_ns": 0.08, "drc_violations": 0}
    assert cost.evaluate(ok, b).gates["setup"]["status"] == "fail"             # -0.60 < -0.50 - 0.02
    replays = [dict(ok, setup_wns_ns=w) for w in (-0.55, -0.62, -0.70, -0.58)]  # median -0.60
    g = cost.with_gate_reference(b, replays)
    assert g.timing["setup_wns_ns"] == pytest.approx(-0.60) and g.values == b.values
    assert "median of 4" in g.sources["gate_reference"]
    r_old, r_new = cost.evaluate(ok, b), cost.evaluate(ok, g)
    assert r_new.gates["setup"]["status"] == "pass" and r_new.J == pytest.approx(r_old.J)   # same J, new gate
    assert cost.with_gate_reference(b, []) is b                                  # nothing to refer to: unchanged


def test_timing_gate_without_the_sign_rule():
    """Decision D6 (3 Oct): the Track-B test keeps the 0.02-ns guard but drops the sign rule; cost_v3 is unchanged."""
    ok = {"detailed_wirelength_um": 1000.0, "vias": 500, "gr_overflow_total": 2, "setup_tns_ns": -10.0,
          "total_power_w": 0.010, "setup_wns_ns": -0.52, "hold_wns_ns": 0.08, "drc_violations": 0}
    b = cost.Baseline("d", base().values, {"setup_wns_ns": -0.50, "hold_wns_ns": 0.015}, 3)
    small_neg = dict(ok, hold_wns_ns=-0.003)                                   # within 0.02 of +0.015, but negative
    assert math.isinf(cost.evaluate(small_neg, b).J_inf)                       # cost_v3: the sign rule fails it
    r = cost.evaluate(small_neg, b, timing_sign_rule=False)
    assert r.gates["hold"]["status"] == "pass" and math.isfinite(r.J_inf)
    worse = dict(ok, hold_wns_ns=-0.006)                                       # more than 0.02 below the reference
    r = cost.evaluate(worse, b, timing_sign_rule=False)
    assert r.gates["hold"]["reason"] == "degrades_more_than_guard" and math.isinf(r.J_inf)


def test_same_shift_reference():
    """Decision D11 (b), 4 Oct: a replicate's timing gates compare with the tool's replicate at the same shift; if that
    run failed, with the median of the tool's completed replicates in the test; J's normalization unchanged."""
    ok = {"detailed_wirelength_um": 1000.0, "vias": 500, "gr_overflow_total": 2, "setup_tns_ns": -10.0,
          "total_power_w": 0.010, "setup_wns_ns": -0.52, "hold_wns_ns": 0.02, "drc_violations": 0}
    b = cost.Baseline("d", base().values, {"setup_wns_ns": -0.50, "hold_wns_ns": 0.055}, 3)   # replay band: hold +0.055
    assert math.isinf(cost.evaluate(ok, b, timing_sign_rule=False).J_inf)       # +0.02 < +0.055 - 0.02: fails vs the band
    ref = dict(ok, setup_wns_ns=-0.51, hold_wns_ns=0.03, returncode=0)          # the tool at the same shift
    g = cost.same_shift_reference(b, ref, [ref])
    assert g.timing == {"setup_wns_ns": -0.51, "hold_wns_ns": 0.03} and g.values == b.values
    assert "same shift" in g.sources["gate_reference"]
    r = cost.evaluate(ok, g, timing_sign_rule=False)
    assert r.gates["hold"]["status"] == "pass" and r.gates["setup"]["status"] == "pass" and math.isfinite(r.J_inf)
    failed = {"returncode": 2}                                                  # the tool's run at this shift failed
    others = [dict(ref, hold_wns_ns=h) for h in (0.04, 0.05, 0.06)]              # median +0.05
    g2 = cost.same_shift_reference(b, failed, [failed] + others)
    assert g2.timing["hold_wns_ns"] == pytest.approx(0.05) and "completed replicates" in g2.sources["gate_reference"]
    assert cost.same_shift_reference(b, failed, [failed]) is b                  # nothing completed: the base's reference
