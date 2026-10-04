"""scripts/programs_confirm.py: decision D11 (b) in a test: each replicate's timing gates refer to the tool's replicate at
the same shift (the median of the tool's completed replicates where that run failed); both arms gated alike."""

import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from heurbridge.paths import eda_dir  # noqa: E402


@pytest.mark.skipif(eda_dir() is None, reason="needs eda/harness/metrics_schema.py")
def test_arms_use_the_tool_replicate_at_the_same_shift(tmp_path):
    import programs_confirm as P
    base = {"detailed_wirelength_um": 1000.0, "vias": 500, "gr_overflow_total": 0, "setup_tns_ns": 0.0,
            "total_power_w": 0.01, "setup_wns_ns": 1.0, "hold_wns_ns": 0.055, "drc_violations": 0, "returncode": 0,
            "duration_s": 3600.0}
    camp = tmp_path / "seedB_orfs7_x" / "runs" / "seed_orfs" / "d"
    camp.mkdir(parents=True)
    (camp / "baseline_f2.json").write_text(json.dumps({"records": [base, base]}))
    (camp / "evals_f2.jsonl").write_text("".join(json.dumps({"program": "M1_replay", "status": "ok", "record": base}) + "\n"
                                                 for _ in range(4)))                    # replay band: hold +0.055
    dirs = {k: tmp_path / ("%s_x" % k) / "runs" / "seed_orfs" / "d" for k in ("tb", "tw", "tp")}
    for p in dirs.values():
        p.mkdir(parents=True)
    tool = [{"run_id": "d.tb.ref.s1.f2", "program": "TB_REF", "status": "ok", "tb_shift": [2, 0],
             "record": dict(base, hold_wns_ns=0.03)},                                   # the tool at (2, 0): +0.03
            {"run_id": "d.tb.ref.s2.f2", "program": "TB_REF", "status": "eval_failed", "tb_shift": [-2, 0],
             "record": {"returncode": 2}}]                                               # failed at (-2, 0)
    (dirs["tb"] / "evals_tb.jsonl").write_text("".join(json.dumps(r) + "\n" for r in tool))
    prog = [{"run_id": "d.tb_pg.cand.s1.f2", "program": "TB_PG_CAND", "status": "ok", "tb_shift": [2, 0],
             "record": dict(base, detailed_wirelength_um=900.0, hold_wns_ns=0.02)},     # >= 0.03 - 0.02: passes
            {"run_id": "d.tb_pg.cand.s2.f2", "program": "TB_PG_CAND", "status": "ok", "tb_shift": [-2, 0],
             "record": dict(base, detailed_wirelength_um=900.0, hold_wns_ns=0.0)}]       # vs the completed median 0.03: fails
    dp = [{"run_id": "d.ext_dp.tb.s1.f2", "program": "EXT_DP_TB", "status": "ok", "tb_shift": [2, 0],
           "record": dict(base, detailed_wirelength_um=950.0, hold_wns_ns=0.02)}]
    (dirs["tp"] / "evals_tb_pg.jsonl").write_text("".join(json.dumps(r) + "\n" for r in prog))
    (dirs["tw"] / "evals_ext_dp.jsonl").write_text("".join(json.dumps(r) + "\n" for r in dp))
    A = P.arms("d", tmp_path, "tp_", "tw_", "tb_", "seedB_orfs7_")
    pg = [x["J"] for x in A["programs"]]
    assert math.isfinite(pg[0]) and math.isinf(pg[1])                                  # the band (+0.055) would fail both
    assert "same shift" in A["programs"][0]["reference"] and "completed" in A["programs"][1]["reference"]
    assert math.isfinite(A["DREAMPlace"][0]["J"]) and A["DREAMPlace"][0]["J"] > pg[0]   # gated alike
    assert A["tool"][0]["J"] == pytest.approx(1.0) and math.isinf(A["tool"][1]["J"])
