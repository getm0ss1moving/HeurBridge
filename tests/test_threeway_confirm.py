"""scripts/threeway_confirm.py: HeurBridge and DREAMPlace are gated alike (D6); the tool's replicates are scored before
the gates; failed flows are +inf."""

import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from heurbridge.paths import eda_dir  # noqa: E402


@pytest.mark.skipif(eda_dir() is None, reason="needs eda/harness/metrics_schema.py")
def test_arms_gate_heurbridge_and_dreamplace_alike(tmp_path):
    import threeway_confirm as W
    base = {"detailed_wirelength_um": 1000.0, "vias": 500, "gr_overflow_total": 0, "setup_tns_ns": 0.0,
            "total_power_w": 0.01, "setup_wns_ns": 1.0, "hold_wns_ns": 0.015, "drc_violations": 0, "returncode": 0,
            "duration_s": 3600.0}
    camp = tmp_path / "seedB_orfs7_x" / "runs" / "seed_orfs" / "d"
    camp.mkdir(parents=True)
    (camp / "baseline_f2.json").write_text(json.dumps({"records": [base, base]}))
    (camp / "evals_f2.jsonl").write_text("".join(json.dumps({"program": "M1_replay", "status": "ok", "record": base}) + "\n"
                                                 for _ in range(4)))
    tb = tmp_path / "tb_x" / "runs" / "seed_orfs" / "d"
    tw = tmp_path / "tw_x" / "runs" / "seed_orfs" / "d"
    tb.mkdir(parents=True)
    tw.mkdir(parents=True)
    tbrows = [{"run_id": "d.tb.cand.s1.f2", "program": "TB_CAND", "status": "ok", "tb_shift": [2, 0],
               "record": dict(base, detailed_wirelength_um=900.0)},
              {"run_id": "d.tb.ref.s1.f2", "program": "TB_REF", "status": "ok", "tb_shift": [2, 0],
               "record": dict(base, hold_wns_ns=-0.5)}]                       # the tool: never gated
    twrows = [{"run_id": "d.ext_dp.td0.6.s0.f1", "program": "EXT_DP", "status": "ok", "wall_s": 1800.0, "record": base,
               "J_raw": 1.0, "ext_index": 0, "target_density": 0.6, "seed": 0},
              {"run_id": "d.ext_dp.td0.6.s0.f2", "program": "EXT_DP_F2", "status": "ok", "wall_s": 3600.0, "record": base,
               "ext_index": 0, "target_density": 0.6, "seed": 0},
              {"run_id": "d.ext_dp.tb.s1.f2", "program": "EXT_DP_TB", "status": "ok", "tb_shift": [2, 0], "ext_index": 0,
               "record": dict(base, detailed_wirelength_um=800.0, hold_wns_ns=-0.006)},   # beyond the guard: +inf
              {"run_id": "d.ext_dp.tb.s2.f2", "program": "EXT_DP_TB", "status": "eval_failed", "tb_shift": [-2, 0], "ext_index": 0,
               "record": {"returncode": 2}}]
    (tb / "evals_tb.jsonl").write_text("".join(json.dumps(r) + "\n" for r in tbrows))
    (tw / "evals_ext_dp.jsonl").write_text("".join(json.dumps(r) + "\n" for r in twrows))
    A = W.arms("d", tmp_path, "tb_", "tw_", "seedB_orfs7_")
    hb, dp, tool = ([x["J"] for x in A[k]] for k in ("HeurBridge", "DREAMPlace", "tool"))
    assert math.isfinite(hb[0]) and hb[0] < 1.0
    assert dp == [math.inf, math.inf] and A["DREAMPlace"][0]["J_before_gates"] < hb[0]
    assert tool[0] == pytest.approx(1.0)
    assert len(A["dp_f1"]) == 1 and len(A["dp_f2"]) == 1 and A["tool_run_s"] == 3600.0
    assert A["dp_pick"]["index"] == 0 and A["dp_pick"]["consistent"] and A["dp_pick"]["target_density_seed"] == (0.6, 0)


@pytest.mark.skipif(eda_dir() is None, reason="needs eda/harness/metrics_schema.py")
def test_tw5_gates_against_the_same_shift_tool_replicate_and_picks_by_jsafe(tmp_path):
    """TW#5 (ariane133; D11 b and D13 a): a DREAMPlace replicate whose hold slack the replay band would reject passes
    against the tool's replicate at the same shift; where the tool's run failed, the completed tool replicates are the
    reference; DREAMPlace's pick is recomputed by one-position J_safe (a lower J that fails hold loses)."""
    import threeway_confirm as W
    d = "ariane133"
    assert d in W.D11B and W.ORDER.index(d) == 4
    base = {"detailed_wirelength_um": 1000.0, "vias": 500, "gr_overflow_total": 0, "setup_tns_ns": 0.0,
            "total_power_w": 0.01, "setup_wns_ns": 1.0, "hold_wns_ns": 0.015, "drc_violations": 0, "returncode": 0,
            "duration_s": 3600.0}
    camp = tmp_path / "seedB_orfs9_x" / "runs" / "seed_orfs" / d
    camp.mkdir(parents=True)
    (camp / "baseline_f2.json").write_text(json.dumps({"records": [base, base]}))
    (camp / "evals_f2.jsonl").write_text("".join(json.dumps({"run_id": "%s.M1replay%s.f2" % (d, s), "program": "M1_replay",
                                                             "status": "ok", "record": base}) + "\n"
                                                 for s in ("", ".p1", ".p2", ".p3")))
    tb = tmp_path / "tb10_x" / "runs" / "seed_orfs" / d
    tw = tmp_path / "tw_x" / "runs" / "seed_orfs" / d
    tb.mkdir(parents=True)
    tw.mkdir(parents=True)
    tbrows = [{"run_id": "%s.tb.cand.s1.f2" % d, "program": "TB_CAND", "status": "ok", "tb_shift": [2, 0],
               "record": dict(base, detailed_wirelength_um=900.0)},
              {"run_id": "%s.tb.ref.s1.f2" % d, "program": "TB_REF", "status": "ok", "tb_shift": [2, 0],
               "record": dict(base, hold_wns_ns=-0.5)},
              {"run_id": "%s.tb.ref.s2.f2" % d, "program": "TB_REF", "status": "eval_failed", "tb_shift": [-2, 0],
               "record": {"returncode": "timeout"}}]
    f1 = lambda k, j: {"run_id": "%s.ext_dp.td1.s%d.f1" % (d, k), "program": "EXT_DP", "status": "ok", "record": base,
                       "J_raw": j, "ext_index": k, "target_density": 1.0, "seed": k}
    f2 = lambda k, rec: {"run_id": "%s.ext_dp.td1.s%d.f2" % (d, k), "program": "EXT_DP_F2", "status": "ok",
                         "record": rec, "ext_index": k, "target_density": 1.0, "seed": k}
    twrows = [f1(0, 0.99), f1(1, 1.0),
              f2(0, dict(base, detailed_wirelength_um=990.0, hold_wns_ns=-0.1)),     # lower J, fails hold at the pick
              f2(1, dict(base, detailed_wirelength_um=1002.0)),
              {"run_id": "%s.ext_dp.tb.s1.f2" % d, "program": "EXT_DP_TB", "status": "ok", "tb_shift": [2, 0],
               "ext_index": 1, "record": dict(base, detailed_wirelength_um=800.0, hold_wns_ns=-0.006)},
              {"run_id": "%s.ext_dp.tb.s2.f2" % d, "program": "EXT_DP_TB", "status": "ok", "tb_shift": [-2, 0],
               "ext_index": 1, "record": dict(base, detailed_wirelength_um=800.0, hold_wns_ns=-0.006)}]
    (tb / "evals_tb.jsonl").write_text("".join(json.dumps(r) + "\n" for r in tbrows))
    (tw / "evals_ext_dp.jsonl").write_text("".join(json.dumps(r) + "\n" for r in twrows))
    A = W.arms(d, tmp_path, "tb10_", "tw_", "seedB_orfs9_")
    dp = [x["J"] for x in A["DREAMPlace"]]
    assert all(math.isfinite(v) for v in dp) and all(not x["gates_failed"] for x in A["DREAMPlace"])
    assert math.isinf(A["tool"][1]["J"]) and A["tool"][1]["gates_failed"] == ["flow"]
    assert A["dp_pick"]["index"] == 1 and A["dp_pick"]["rule"].startswith("the lowest one-position J_safe")
    assert A["dp_pick"]["consistent"]
