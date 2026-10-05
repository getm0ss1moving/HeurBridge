#!/usr/bin/env python3
"""The equal-search-budget comparison of reports/trackB_equal_budget_preregistration.md (the owner's decision D12 (b),
5 Oct; alpha-ledger campaign EB): HeurBridge's programs + its flow-scored local search against DREAMPlace's pick + the
same local search, through the OpenROAD flow.

  python scripts/equal_budget_confirm.py reserve --design bp_fe_top    # before the design's runs (EB#1, #2, ... in order)
  python scripts/equal_budget_confirm.py analyze --design bp_fe_top    # once, after the design's dpls_ job is fetched

Arms per design, on the Track-B test's six shifts at f2:
  HeurBridge      the Track-B test's candidate replicates (rows TB_CAND, jobs tb_*): its one-position J_safe pick
                  among the campaign's f2 layouts (D13 a) is the candidate on all four designs
  DREAMPlace+LS   the local search of HeurBridge's campaign (8 steps of 6 neighbours at f1, J only, every kept move at
                  f2) from DREAMPlace's pick, the one-position J_safe pick among DREAMPlace's f2 layouts and the kept
                  moves, at the six shifts (rows DPLS_TB of evals_dpls_f2.jsonl, jobs dpls_*)
Both gated alike under decision D11 (b) (every gate; setup and hold against the tool's replicate at the same shift, the
0.02-ns guard, no sign rule; where that run failed, the median of the tool's completed replicates); a failed gate or
flow is +inf.  Test: the exact one-sided rank-sum permutation test (HeurBridge lower).
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heurbridge.eval import cost  # noqa: E402
from heurbridge.stats.alpha_ledger import AlphaLedger  # noqa: E402
from trackb_confirm import jl, one, rank_sum_p  # noqa: E402
from threeway_confirm import gate_reference  # noqa: E402

ORDER = ("bp_fe_top", "bp_be_top", "ariane136", "swerv_wrapper")       # EB#1, EB#2, ... in this order
DP_START = {"bp_fe_top": "bp_fe_top.ext_dp.td1.s2.f1", "bp_be_top": "bp_be_top.ext_dp.td0.8.s1.f1",
            "ariane136": "ariane136.ext_dp.td1.s1.f1", "swerv_wrapper": "swerv_wrapper.ext_dp.td1.s0.f1"}  # TW's picks


def flow_ok(r):
    rec = r.get("record") if isinstance(r.get("record"), dict) else {}
    return bool(r.get("status") == "ok" and rec.get("returncode") in (0, None) and rec)


def score_d11b(r, tool: dict, completed: list, band_base, gated: bool = True) -> dict:
    """One replicate under D11 (b): (endpoint, J before the gates, failed gates, reference)."""
    out = {"run_id": r["run_id"], "shift": r.get("tb_shift"), "wall_s": r.get("wall_s")}
    if not flow_ok(r):
        return dict(out, J=math.inf, J_before_gates=math.inf, gates_failed=["flow"], reference="-")
    t = tool.get(tuple(r.get("tb_shift") or ()))
    g = cost.same_shift_reference(band_base, t["record"] if t is not None and flow_ok(t) else None, completed)
    c = cost.evaluate(r["record"], g, fidelity=2, timing_sign_rule=False)
    jb = c.J if math.isfinite(c.J) else math.inf
    return dict(out, J=c.J_inf if gated else jb, J_before_gates=jb, reference=g.sources.get("gate_reference", "replay band"),
                gates_failed=[k for k, x in c.gates.items() if x.get("status") == "fail" and x.get("enforced")])


def arms(design: str, remote: Path, dpls_prefix="dpls_", tb_prefix="tb_", tw_prefix="tw_", camp_prefix="seedB_orfs7_") -> dict:
    dp2 = one(str(remote / (dpls_prefix + "*") / "runs" / "seed_orfs" / design / "evals_dpls_f2.jsonl"))
    dp1 = dp2.parent / "evals_dpls.jsonl"
    tb = one(str(remote / (tb_prefix + "*") / "runs" / "seed_orfs" / design / "evals_tb.jsonl"))
    tw = one(str(remote / (tw_prefix + "*") / "runs" / "seed_orfs" / design / "evals_ext_dp.jsonl"))
    camp = one(str(remote / (camp_prefix + "*") / "runs" / "seed_orfs" / design / "evals_f2.jsonl"))
    band_base, _ = gate_reference(camp, design)
    tool = {tuple(r.get("tb_shift") or ()): r for r in jl(tb) if r.get("program") == "TB_REF"}
    completed = [r["record"] for r in tool.values() if flow_ok(r)]
    pick = lambda rows, prog, gated=True: [score_d11b(r, tool, completed, band_base, gated)
                                           for r in sorted(rows, key=lambda r: r["run_id"]) if r.get("program") == prog]
    tws = jl(tw)
    dps = jl(dp2)
    return {"HeurBridge": pick(jl(tb), "TB_CAND"), "DREAMPlace+LS": pick(dps, "DPLS_TB"),
            "DREAMPlace": pick(tws, "EXT_DP_TB"), "tool": pick(jl(tb), "TB_REF", gated=False),
            "dpls_f1": jl(dp1) if dp1.exists() else [], "dpls_f2": [r for r in dps if r.get("program") == "DPLS_F2"],
            "dp_select": [r for r in tws if r.get("program") in ("EXT_DP", "EXT_DP_F2")],
            "sources": [tb, dp2, tw, camp]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["reserve", "analyze"])
    ap.add_argument("--design", required=True, choices=ORDER)
    ap.add_argument("--ledger", default=str(ROOT / "stats" / "alpha_ledger.jsonl"))
    ap.add_argument("--remote", default=str(ROOT / "runs" / "remote"))
    ap.add_argument("--out", default=str(ROOT / "reports" / "trackB_equal_budget.md"))
    a = ap.parse_args()
    led = AlphaLedger(a.ledger, campaign="EB")
    es = led._entries()
    want = "EB#%d" % (ORDER.index(a.design) + 1)
    if a.cmd == "reserve":
        if any(e.get("event") == "reserve" and e.get("meta", {}).get("design") == a.design for e in es):
            sys.exit("%s is already reserved" % a.design)
        e = led.reserve("programs_ls_vs_dreamplace_ls", "%s: HeurBridge (programs + local search) vs DREAMPlace + the same "
                        "local search at f2" % a.design, "exact_rank_sum_permutation",
                        meta={"design": a.design, "dp_start": DP_START[a.design],
                              "replicates": "the Track-B test's six shifts",
                              "gate_rule": "same-shift tool replicate, 0.02-ns guard, no sign rule (D11 b), both arms",
                              "pick_rule": "one-position J_safe (D13 a), both arms",
                              "preregistration": "reports/trackB_equal_budget_preregistration.md"})
        if e["ledger_id"] != want:
            sys.exit("expected %s for %s, got %s: reserve the designs in order" % (want, a.design, e["ledger_id"]))
        print(json.dumps(e))
        return
    entry = next(e for e in es if e.get("event") == "reserve" and e.get("meta", {}).get("design") == a.design)
    if any(e.get("event") == "result" and e["ledger_id"] == entry["ledger_id"] for e in es):
        sys.exit("%s already has a recorded result; the test runs once" % entry["ledger_id"])
    A = arms(a.design, Path(a.remote))
    hb, dl = ([x["J"] for x in A[k]] for k in ("HeurBridge", "DREAMPlace+LS"))
    p = rank_sum_p(hb, dl) if hb and dl else 1.0
    res = led.record(entry, p_value=p, n=len(hb) + len(dl), extra={"heurbridge": hb, "dreamplace_ls": dl})
    fm = lambda v: "%.4f" % v if v is not None and math.isfinite(v) else "+inf"
    med = lambda k: float(np.median([x["J_before_gates"] for x in A[k]])) if A[k] else math.inf
    p_ls = rank_sum_p(dl, [x["J"] for x in A["DREAMPlace"]]) if dl and A["DREAMPlace"] else 1.0
    hrs = lambda rows: sum(float(r.get("wall_s") or 0.0) for r in rows) / 3600.0
    L = ["## %s (%s)" % (a.design, entry["ledger_id"]), "",
         "Recorded %s. **%s**: HeurBridge (programs + local search) lower than DREAMPlace + the same local search, "
         "exact one-sided rank-sum permutation p = %.4g against alpha_j = %.4g." % (
             res["time"], "PASSED" if res["promoted"] else "FAILED", p, entry["alpha_j"]), "",
         "Reported, not tested: median J before the gates: HeurBridge %s, DREAMPlace+LS %s, DREAMPlace %s, tool %s; "
         "DREAMPlace+LS lower than DREAMPlace under the same gates (what the search adds to DREAMPlace): p = %.4g. "
         "DREAMPlace+LS's flow runs: %d at f1 and %d at f2 in its search (%.1f flow-run hours), after DREAMPlace's "
         "selection (%d runs, %.1f flow-run hours)." % (
             fm(med("HeurBridge")), fm(med("DREAMPlace+LS")), fm(med("DREAMPlace")), fm(med("tool")), p_ls,
             len(A["dpls_f1"]), len(A["dpls_f2"]), hrs(A["dpls_f1"]) + hrs(A["dpls_f2"]), len(A["dp_select"]),
             hrs(A["dp_select"])), "",
         "| replicate | arm | shift | J (gated, D11 b; tool: before gates) | J before gates | gates failed |",
         "|---|---|---|---|---|---|"]
    for k in ("HeurBridge", "DREAMPlace+LS", "DREAMPlace", "tool"):
        for x in A[k]:
            L.append("| %s | %s | %s | %s | %s | %s |" % (x["run_id"], k, x["shift"], fm(x["J"]), fm(x["J_before_gates"]),
                                                       ", ".join(x["gates_failed"]) or "-"))
    L += ["", "Sources: %s." % ", ".join(str(q.relative_to(ROOT)) if q.is_relative_to(ROOT) else str(q) for q in A["sources"]), ""]
    out = Path(a.out)
    head = ("# Track B: equal search budget, HeurBridge's programs vs DREAMPlace as the starts of the same local search\n\n"
            "| Field | Value |\n|---|---|\n| Report | trackB_equal_budget |\n"
            "| Pre-registration | reports/trackB_equal_budget_preregistration.md |\n| Status of the claim | per design below |\n\n")
    text = out.read_text() if out.exists() else head
    out.write_text(text + "\n".join(L) + "\n")
    print(json.dumps(res))


if __name__ == "__main__":
    main()
