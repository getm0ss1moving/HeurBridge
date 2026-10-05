"""scripts/equal_budget_confirm.py (D12 b): HeurBridge and DREAMPlace + local search gated alike under D11 (b)."""

import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from heurbridge.paths import eda_dir  # noqa: E402


@pytest.mark.skipif(eda_dir() is None, reason="needs eda/harness/metrics_schema.py")
def test_arms_gate_both_against_the_same_shift(tmp_path):
    import equal_budget_confirm as E
    base = {"detailed_wirelength_um": 1000.0, "vias": 500, "gr_overflow_total": 0, "setup_tns_ns": 0.0,
            "total_power_w": 0.01, "setup_wns_ns": 1.0, "hold_wns_ns": 0.055, "drc_violations": 0, "returncode": 0}
    camp = tmp_path / "seedB_orfs7_x" / "runs" / "seed_orfs" / "d"
    camp.mkdir(parents=True)
    (camp / "baseline_f2.json").write_text(json.dumps({"records": [base, base]}))
    (camp / "evals_f2.jsonl").write_text("".join(json.dumps({"program": "M1_replay", "status": "ok", "record": base}) + "\n"
                                                 for _ in range(4)))
    dirs = {k: tmp_path / ("%s_x" % k) / "runs" / "seed_orfs" / "d" for k in ("tb", "tw", "dpls")}
    for p in dirs.values():
        p.mkdir(parents=True)
    rows = {"tb": [{"run_id": "d.tb.ref.s1.f2", "program": "TB_REF", "status": "ok", "tb_shift": [2, 0],
                    "record": dict(base, hold_wns_ns=0.03)},
                   {"run_id": "d.tb.cand.s1.f2", "program": "TB_CAND", "status": "ok", "tb_shift": [2, 0],
                    "record": dict(base, detailed_wirelength_um=900.0, hold_wns_ns=0.02)}],      # 0.02 >= 0.03 - 0.02
            "tw": [{"run_id": "d.ext_dp.td1.s0.f1", "program": "EXT_DP", "status": "ok", "wall_s": 600.0, "record": base},
                   {"run_id": "d.ext_dp.tb.s1.f2", "program": "EXT_DP_TB", "status": "ok", "tb_shift": [2, 0],
                    "record": dict(base, hold_wns_ns=0.0)}],                                      # 0.0 < 0.01: fails
            "dpls": [{"run_id": "d.dpls.s0.f2", "program": "DPLS_F2", "status": "ok", "wall_s": 1200.0, "record": base},
                     {"run_id": "d.dpls.tb.s1.f2", "program": "DPLS_TB", "status": "ok", "tb_shift": [2, 0],
                      "record": dict(base, detailed_wirelength_um=950.0, hold_wns_ns=0.02)}]}
    names = {"tb": "evals_tb.jsonl", "tw": "evals_ext_dp.jsonl", "dpls": "evals_dpls_f2.jsonl"}
    for k, rs in rows.items():
        (dirs[k] / names[k]).write_text("".join(json.dumps(r) + "\n" for r in rs))
    (dirs["dpls"] / "evals_dpls.jsonl").write_text(json.dumps({"run_id": "d.dpls.s0.n0.f1", "program": "DPLS",
                                                               "status": "ok", "wall_s": 300.0}) + "\n")
    A = E.arms("d", tmp_path)
    assert math.isfinite(A["HeurBridge"][0]["J"]) and math.isfinite(A["DREAMPlace+LS"][0]["J"])
    assert A["HeurBridge"][0]["J"] < A["DREAMPlace+LS"][0]["J"]                     # 900 vs 950 um, both pass
    assert math.isinf(A["DREAMPlace"][0]["J"]) and A["DREAMPlace"][0]["gates_failed"] == ["hold"]
    assert "same shift" in A["DREAMPlace+LS"][0]["reference"]
    assert len(A["dpls_f1"]) == 1 and len(A["dpls_f2"]) == 1 and len(A["dp_select"]) == 1
