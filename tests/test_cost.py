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
