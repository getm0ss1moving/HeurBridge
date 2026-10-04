"""scripts/timing_safety_report.py (decision D13 (a)): per position two timing checks against the tool's run at the same
shift (D11 b); J = median J before the gates, S = share of checks passed, J_safe = J + LAMBDA * (1 - S)."""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from heurbridge.paths import eda_dir  # noqa: E402


@pytest.mark.skipif(eda_dir() is None, reason="needs eda/harness/metrics_schema.py")
def test_j_safe_counts_checks_and_charges_lambda():
    import timing_safety_report as T
    from heurbridge.eval import cost
    rec = {"detailed_wirelength_um": 1000.0, "vias": 500, "gr_overflow_total": 0, "setup_tns_ns": 0.0,
           "total_power_w": 0.01, "setup_wns_ns": 1.0, "hold_wns_ns": 0.05, "drc_violations": 0, "returncode": 0}
    base = cost.Baseline.from_records("d", [rec, rec])
    tool = {"setup_wns_ns": 1.0, "hold_wns_ns": 0.05}
    ok = {"status": "ok", "record": dict(rec)}                                   # J 1.0, both checks pass
    low_hold = {"status": "ok", "record": dict(rec, hold_wns_ns=0.02)}            # 0.02 < 0.05 - 0.02: hold fails
    failed = {"status": "eval_failed", "record": {"returncode": 2}}               # fails both checks
    pos = [T.position(r, tool, base) for r in (ok, low_hold, ok, failed)]
    assert pos[0][:3] == (pytest.approx(1.0), True, True) and pos[1][1:3] == (True, False)
    assert math.isinf(pos[3][0]) and pos[3][1:3] == (False, False)
    s = T.summary(pos)
    assert s["passed"] == 5 and s["checks"] == 8 and s["marks"] == "SH S- SH xx"
    assert s["J"] == pytest.approx(1.0) and s["J_safe"] == pytest.approx(1.0 + T.LAMBDA * 3 / 8)
    assert math.isinf(T.summary(pos[1:] + [pos[3]])["J"])                        # half or more failed: J +inf
