"""scripts/trackb_confirm.py: the exact rank-sum permutation test and the endpoint of the Track-B test (decision D6)."""

import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from heurbridge.paths import eda_dir  # noqa: E402


def test_rank_sum_p_is_exact():
    import trackb_confirm as T
    assert T.rank_sum_p([0.1] * 6, [0.2] * 6) == pytest.approx(1 / 924)          # whole band below: the minimum p
    assert T.rank_sum_p([0.5] * 6, [0.5] * 6) == 1.0                             # all ties: no evidence
    assert T.rank_sum_p([0.1, 0.2, 0.3, 0.4, 0.5, math.inf], [0.6] * 6) > 1 / 924   # +inf ranks above every finite value


@pytest.mark.skipif(eda_dir() is None, reason="needs eda/harness/metrics_schema.py")
def test_endpoint_gates_the_candidate_only_without_the_sign_rule(tmp_path):
    import trackb_confirm as T
    base = {"detailed_wirelength_um": 1000.0, "vias": 500, "gr_overflow_total": 0, "setup_tns_ns": 0.0,
            "total_power_w": 0.01, "setup_wns_ns": 1.0, "hold_wns_ns": 0.015, "drc_violations": 0, "returncode": 0}
    camp = tmp_path / "seedB_orfs7_x" / "runs" / "seed_orfs" / "d"
    camp.mkdir(parents=True)
    (camp / "baseline_f2.json").write_text(json.dumps({"records": [base, base]}))
    (camp / "evals_f2.jsonl").write_text("".join(json.dumps({"program": "M1_replay", "status": "ok", "record": base}) + "\n"
                                                 for _ in range(4)))
    tb = tmp_path / "tb_x" / "runs" / "seed_orfs" / "d"
    tb.mkdir(parents=True)
    rows = []
    for k, hold in enumerate((-0.003, -0.006), 1):                              # within / beyond the 0.02-ns guard
        rows.append({"run_id": "d.tb.cand.s%d.f2" % k, "program": "TB_CAND", "status": "ok", "tb_shift": [k, 0],
                     "record": dict(base, detailed_wirelength_um=900.0, hold_wns_ns=hold)})
    rows.append({"run_id": "d.tb.ref.s1.f2", "program": "TB_REF", "status": "ok", "tb_shift": [1, 0],
                 "record": dict(base, hold_wns_ns=-0.5)})                        # the tool's own: never gated
    rows.append({"run_id": "d.tb.ref.s2.f2", "program": "TB_REF", "status": "fail", "record": {"returncode": 2}})
    (tb / "evals_tb.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    cand, ref, out, srcs = T.endpoint("d", tmp_path, "tb_", "seedB_orfs7_")
    assert math.isfinite(cand[0]) and cand[0] < 1.0 and math.isinf(cand[1])
    assert ref[0] == pytest.approx(1.0) and math.isinf(ref[1])
