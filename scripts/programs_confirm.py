#!/usr/bin/env python3
"""HeurBridge's heuristic programs without the flow-scored local search against DREAMPlace, through the OpenROAD flow
(the owner's decision D12 (c), 4 Oct; reports/trackB_programs_preregistration.md; alpha-ledger campaign TP).

  python scripts/programs_confirm.py pick --design bp_fe_top       # the registered pick, recomputed from the rows
  python scripts/programs_confirm.py reserve --design bp_fe_top    # before the design's runs (TP#1, #2, ... in order)
  python scripts/programs_confirm.py analyze --design bp_fe_top    # once, after the design's tp_ job is fetched

Arms per design, on the Track-B test's six shifts at f2:
  programs    the campaign's best admitted program layout (no local-search move) picked like DREAMPlace's (rows
              TB_PG_CAND of runs/seed_orfs/<d>/evals_tb_pg.jsonl, jobs tp_*)
  DREAMPlace  the three-way comparison's replicates (rows EXT_DP_TB of runs/seed_orfs/<d>/evals_ext_dp.jsonl, jobs tw_*)
Both gated alike under decision D11 (b): every gate enforced; setup and hold against the tool's replicate at the same
shift (rows TB_REF of the Track-B test, jobs tb_*) with the 0.02-ns guard and no sign rule; where the tool's run at that
shift failed, against the median of its completed replicates (heurbridge/eval/cost.py same_shift_reference).  A failed
gate or flow is +inf.  Test: the exact one-sided rank-sum permutation test (programs lower).
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

ORDER = ("bp_fe_top", "bp_be_top", "ariane136", "swerv_wrapper")        # TP#1, TP#2, ... in this order
PICKS = {"bp_fe_top": "bp_fe_top.M3.v0.s2.f2", "bp_be_top": "bp_be_top.M2.v1.s0.f2",
         "ariane136": "ariane136.M4.v2.s0.f2", "swerv_wrapper": "swerv_wrapper.M4.v0.s0.f2"}   # fixed 4 Oct by `pick`


def flow_ok(r: dict) -> bool:
    rec = r.get("record") if isinstance(r.get("record"), dict) else {}
    return bool(r.get("status") == "ok" and rec.get("returncode") in (0, None) and rec)


def pick(design: str, remote: Path, camp_prefix: str) -> tuple:
    """The registered rule: among the campaign's f2 rows of program layouts (no replay, no local-search move), the best
    admitted under D6 (as DREAMPlace's pick), else the best J before the gates, else the best program by f1."""
    from run_seed_orfs import ext_pick
    camp = one(str(remote / (camp_prefix + "*") / "runs" / "seed_orfs" / design / "evals_f2.jsonl"))
    ref_base, _ = gate_reference(camp, design)
    sel = []
    for r in jl(camp):
        if r.get("program") in ("M1_replay", "LS", "CAND_BAND"):
            continue
        c = cost.evaluate(r["record"], ref_base, fidelity=2, timing_sign_rule=False) if flow_ok(r) else None
        sel.append((c.J_inf if c else math.inf, c.J if c is not None and math.isfinite(c.J) else math.inf, r["run_id"]))
    f1 = sorted((r["J_raw"], r["run_id"]) for r in jl(camp.parent / "evals.jsonl")
                if r.get("program") not in ("M1_replay", "LS") and r.get("status") == "ok" and r.get("J_raw") is not None)
    return ext_pick(sel, f1[0][1][:-3] + ".f2" if f1 else None) + (len(sel),)


def arms(design: str, remote: Path, tp_prefix: str, tw_prefix: str, tb_prefix: str, camp_prefix: str) -> dict:
    tp = one(str(remote / (tp_prefix + "*") / "runs" / "seed_orfs" / design / "evals_tb_pg.jsonl"))
    tw = one(str(remote / (tw_prefix + "*") / "runs" / "seed_orfs" / design / "evals_ext_dp.jsonl"))
    tb = one(str(remote / (tb_prefix + "*") / "runs" / "seed_orfs" / design / "evals_tb.jsonl"))
    camp = one(str(remote / (camp_prefix + "*") / "runs" / "seed_orfs" / design / "evals_f2.jsonl"))
    band_base, _ = gate_reference(camp, design)                       # used only if no tool replicate completed
    tool = {tuple(r.get("tb_shift") or ()): r for r in jl(tb) if r.get("program") == "TB_REF"}
    completed = [r["record"] for r in tool.values() if flow_ok(r)]

    def score(r: dict, gated: bool = True) -> dict:
        out = {"run_id": r["run_id"], "shift": r.get("tb_shift"), "wall_s": r.get("wall_s")}
        if not flow_ok(r):
            return dict(out, J=math.inf, J_before_gates=math.inf, gates_failed=["flow"], reference="-")
        t = tool.get(tuple(r.get("tb_shift") or ()))
        g = cost.same_shift_reference(band_base, t["record"] if t is not None and flow_ok(t) else None, completed)
        c = cost.evaluate(r["record"], g, fidelity=2, timing_sign_rule=False)
        jb = c.J if math.isfinite(c.J) else math.inf
        return dict(out, J=c.J_inf if gated else jb, J_before_gates=jb, reference=g.sources.get("gate_reference", "replay band"),
                    gates_failed=[k for k, x in c.gates.items() if x.get("status") == "fail" and x.get("enforced")])
    return {"programs": [score(r) for r in sorted(jl(tp), key=lambda r: r["run_id"]) if r.get("program") == "TB_PG_CAND"],
            "DREAMPlace": [score(r) for r in sorted(jl(tw), key=lambda r: r["run_id"]) if r.get("program") == "EXT_DP_TB"],
            "HeurBridge (local search)": [score(r) for r in sorted(jl(tb), key=lambda r: r["run_id"])
                                          if r.get("program") == "TB_CAND"],
            "tool": [score(r, gated=False) for r in sorted(jl(tb), key=lambda r: r["run_id"]) if r.get("program") == "TB_REF"],
            "sources": [tp, tw, tb, camp]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["pick", "reserve", "analyze"])
    ap.add_argument("--design", required=True, choices=ORDER)
    ap.add_argument("--ledger", default=str(ROOT / "stats" / "alpha_ledger.jsonl"))
    ap.add_argument("--remote", default=str(ROOT / "runs" / "remote"))
    ap.add_argument("--tp-prefix", default="tp_")
    ap.add_argument("--tw-prefix", default="tw_")
    ap.add_argument("--tb-prefix", default="tb_")
    ap.add_argument("--campaign-prefix", default="seedB_orfs7_")
    ap.add_argument("--out", default=str(ROOT / "reports" / "trackB_programs_vs_dreamplace.md"))
    a = ap.parse_args()
    if a.cmd == "pick":
        rid, rule, n = pick(a.design, Path(a.remote), a.campaign_prefix)
        print(json.dumps({"design": a.design, "pick": rid, "rule": rule, "program_f2_rows": n, "registered": PICKS[a.design]}))
        return
    led = AlphaLedger(a.ledger, campaign="TP")
    es = led._entries()
    want = "TP#%d" % (ORDER.index(a.design) + 1)
    if a.cmd == "reserve":
        if any(e.get("event") == "reserve" and e.get("meta", {}).get("design") == a.design for e in es):
            sys.exit("%s is already reserved" % a.design)
        e = led.reserve("programs_vs_dreamplace", "%s: %s (no local search) vs DREAMPlace's pick at f2" % (a.design, PICKS[a.design]),
                        "exact_rank_sum_permutation", meta={"design": a.design, "pick": PICKS[a.design],
                                                            "replicates": "the Track-B test's six shifts",
                                                            "gate_rule": "same-shift tool replicate, 0.02-ns guard, no sign rule (D11 b), both arms",
                                                            "preregistration": "reports/trackB_programs_preregistration.md"})
        if e["ledger_id"] != want:
            sys.exit("expected %s for %s, got %s: reserve the designs in order" % (want, a.design, e["ledger_id"]))
        print(json.dumps(e))
        return
    entry = next(e for e in es if e.get("event") == "reserve" and e.get("meta", {}).get("design") == a.design)
    if any(e.get("event") == "result" and e["ledger_id"] == entry["ledger_id"] for e in es):
        sys.exit("%s already has a recorded result; the test runs once" % entry["ledger_id"])
    A = arms(a.design, Path(a.remote), a.tp_prefix, a.tw_prefix, a.tb_prefix, a.campaign_prefix)
    pg, dp = ([x["J"] for x in A[k]] for k in ("programs", "DREAMPlace"))
    p = rank_sum_p(pg, dp) if pg and dp else 1.0
    res = led.record(entry, p_value=p, n=len(pg) + len(dp), extra={"programs": pg, "dreamplace": dp})
    fm = lambda v: "%.4f" % v if v is not None and math.isfinite(v) else "+inf"
    med = lambda k: float(np.median([x["J_before_gates"] for x in A[k]])) if A[k] else math.inf
    p_ls = rank_sum_p([x["J"] for x in A["HeurBridge (local search)"]], pg) if pg else 1.0
    L = ["## %s (%s)" % (a.design, entry["ledger_id"]), "",
         "Program pick %s. Recorded %s. **%s**: programs lower than DREAMPlace, exact one-sided rank-sum permutation "
         "p = %.4g against alpha_j = %.4g." % (PICKS[a.design], res["time"], "PASSED" if res["promoted"] else "FAILED", p,
                                              entry["alpha_j"]), "",
         "Reported, not tested: median J before the gates: programs %s, DREAMPlace %s, HeurBridge with local search %s, "
         "tool %s; HeurBridge with local search lower than the programs under the same gates: p = %.4g." % (
             fm(med("programs")), fm(med("DREAMPlace")), fm(med("HeurBridge (local search)")), fm(med("tool")), p_ls), "",
         "| replicate | arm | shift | J (gated, D11 b; tool: before gates) | J before gates | gates failed | timing reference |",
         "|---|---|---|---|---|---|---|"]
    for k in ("programs", "DREAMPlace", "HeurBridge (local search)", "tool"):
        for x in A[k]:
            L.append("| %s | %s | %s | %s | %s | %s | %s |" % (x["run_id"], k, x["shift"], fm(x["J"]), fm(x["J_before_gates"]),
                                                            ", ".join(x["gates_failed"]) or "-", x["reference"]))
    L += ["", "Sources: %s." % ", ".join(str(q.relative_to(ROOT)) if q.is_relative_to(ROOT) else str(q) for q in A["sources"]), ""]
    out = Path(a.out)
    head = ("# Track B: HeurBridge's programs (no local search) and DREAMPlace through the OpenROAD flow\n\n"
            "| Field | Value |\n|---|---|\n| Report | trackB_programs_vs_dreamplace |\n"
            "| Pre-registration | reports/trackB_programs_preregistration.md |\n| Status of the claim | per design below |\n\n")
    text = out.read_text() if out.exists() else head
    out.write_text(text + "\n".join(L) + "\n")
    print(json.dumps(res))


if __name__ == "__main__":
    main()
