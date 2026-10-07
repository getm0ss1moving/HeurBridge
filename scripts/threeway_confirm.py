#!/usr/bin/env python3
"""The three-way comparison of reports/trackB_threeway_preregistration.md (alpha-ledger campaign TW): HeurBridge's
macro layout against DREAMPlace's through the OpenROAD flow, next to the tool's own macro placement.

  python scripts/threeway_confirm.py reserve --design bp_fe_top    # before the design's DREAMPlace flow runs (in order)
  python scripts/threeway_confirm.py analyze --design bp_fe_top    # once, after the design's tw_ job is fetched

Arms per design, on the Track-B test's six shifts at f2:
  HeurBridge  the Track-B test's candidate replicates (TB_CAND rows of runs/seed_orfs/<d>/evals_tb.jsonl, job tb_<d>)
  DREAMPlace  its picked layout's replicates (EXT_DP_TB rows of runs/seed_orfs/<d>/evals_ext_dp.jsonl, job tw_<d>)
  tool        the Track-B test's reference replicates (TB_REF rows; reported, not tested)
HeurBridge and DREAMPlace are scored alike: f2 J with every gate enforced, the timing gates against the campaign's
same-path replay band's median with the 0.02-ns guard and no sign rule (decision D6); a failed gate or flow is +inf.
TW#5 (ariane133, reports/trackB_threeway_ariane133_preregistration.md, registered 7 Oct): the timing gates against the
tool's replicate at the same shift (D11 b, equal_budget_confirm.score_d11b) and DREAMPlace's pick by one-position
J_safe (D13 a, run_seed_orfs.jsafe_pick).  Test: the exact one-sided rank-sum permutation test of trackb_confirm.py
(HeurBridge lower).
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

ORDER = ("bp_fe_top", "bp_be_top", "ariane136", "swerv_wrapper", "ariane133")      # TW#1, TW#2, ... in this order
D11B = ("ariane133",)            # TW#5, registered 7 Oct: gates under D11 (b), DREAMPlace's pick under D13 (a)
PREREG = {"ariane133": "reports/trackB_threeway_ariane133_preregistration.md"}


def gate_reference(camp: Path, design: str):
    recs2 = [r for r in json.loads((camp.parent / "baseline_f2.json").read_text())["records"] if r.get("returncode") == 0]
    rep = [r["record"] for r in jl(camp) if r.get("program") == "M1_replay" and r.get("status") == "ok"
           and isinstance(r.get("record"), dict)]
    return cost.with_gate_reference(cost.Baseline.from_records(design, recs2), rep), recs2


def score(r: dict, ref_base, gated: bool) -> tuple:
    """(endpoint value, J before the gates, failed gates); a failed flow is +inf."""
    rec = r.get("record") if isinstance(r.get("record"), dict) else {}
    if not (r.get("status") == "ok" and rec.get("returncode") in (0, None) and rec):
        return math.inf, math.inf, ["flow"]
    c = cost.evaluate(rec, ref_base, fidelity=2, timing_sign_rule=False)
    jb = c.J if math.isfinite(c.J) else math.inf
    failed = [k for k, g in c.gates.items() if g.get("status") == "fail" and g.get("enforced")]
    return (c.J_inf if gated else jb), jb, failed


def arms(design: str, remote: Path, tb_prefix: str, tw_prefix: str, camp_prefix: str) -> dict:
    tb = one(str(remote / (tb_prefix + "*") / "runs" / "seed_orfs" / design / "evals_tb.jsonl"))
    tw = one(str(remote / (tw_prefix + "*") / "runs" / "seed_orfs" / design / "evals_ext_dp.jsonl"))
    camp = one(str(remote / (camp_prefix + "*") / "runs" / "seed_orfs" / design / "evals_f2.jsonl"))
    ref_base, recs2 = gate_reference(camp, design)
    out = {"HeurBridge": [], "DREAMPlace": [], "tool": [], "sources": [tb, tw, camp]}
    d11b = design in D11B
    if d11b:                                                        # the tool's replicate at the same shift (D11 b)
        from equal_budget_confirm import flow_ok, score_d11b
        tool = {tuple(r.get("tb_shift") or ()): r for r in jl(tb) if r.get("program") == "TB_REF"}
        completed = [r["record"] for r in tool.values() if flow_ok(r)]
    for name, path, prog, gated in (("HeurBridge", tb, "TB_CAND", True), ("tool", tb, "TB_REF", False),
                                    ("DREAMPlace", tw, "EXT_DP_TB", True)):
        for r in sorted(jl(path), key=lambda r: r["run_id"]):
            if r.get("program") == prog:
                if d11b:
                    x = score_d11b(r, tool, completed, ref_base, gated)
                    v, jb, failed = x["J"], x["J_before_gates"], x["gates_failed"]
                else:
                    v, jb, failed = score(r, ref_base, gated)
                out[name].append({"run_id": r["run_id"], "shift": r.get("tb_shift"), "J": v, "J_before_gates": jb,
                                  "gates_failed": failed, "wall_s": r.get("wall_s")})
    dp = jl(tw)
    out["dp_f1"] = [r for r in dp if r.get("program") == "EXT_DP"]
    out["dp_f2"] = [r for r in dp if r.get("program") == "EXT_DP_F2"]
    f1ok = [(r["J_raw"], r["ext_index"]) for r in out["dp_f1"] if r.get("status") == "ok" and r.get("J_raw") is not None
            and math.isfinite(r["J_raw"])]
    sel = []
    for r in out["dp_f2"]:
        v, jb, _ = score(r, ref_base, True)
        sel.append((v, jb, r["ext_index"]))
    from run_seed_orfs import ext_pick, jsafe_pick                  # the registered rule, recomputed from the rows
    if not f1ok:
        pick, rule = None, "no layout completed f1"
    elif d11b:
        ref0 = next(r["record"] for r in jl(camp) if r["run_id"] == "%s.M1replay.f2" % design)
        pick, rule = jsafe_pick([(r["ext_index"], r) for r in out["dp_f2"]], ref0, ref_base, min(f1ok)[1])
    else:
        pick, rule = ext_pick(sel, min(f1ok)[1])
    used = {r.get("ext_index") for r in dp if r.get("program") == "EXT_DP_TB"}
    meta = {r["ext_index"]: (r.get("target_density"), r.get("seed")) for r in out["dp_f1"]}
    out["dp_pick"] = {"index": pick, "rule": rule, "target_density_seed": meta.get(pick), "replicates_used": sorted(used),
                      "consistent": used <= {pick}}
    out["tool_run_s"] = float(np.median([float(r["duration_s"]) for r in recs2]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["reserve", "analyze"])
    ap.add_argument("--design", required=True, choices=ORDER)
    ap.add_argument("--ledger", default=str(ROOT / "stats" / "alpha_ledger.jsonl"))
    ap.add_argument("--remote", default=str(ROOT / "runs" / "remote"))
    ap.add_argument("--tb-prefix", default="tb_", help="job-name prefix of the Track-B test's runs")
    ap.add_argument("--tw-prefix", default="tw_", help="job-name prefix of DREAMPlace's flow runs")
    ap.add_argument("--campaign-prefix", default="seedB_orfs7_", help="job-name prefix of the seeding campaign")
    ap.add_argument("--out", default=str(ROOT / "reports" / "trackB_threeway.md"))
    a = ap.parse_args()
    led = AlphaLedger(a.ledger, campaign="TW")
    es = led._entries()
    want = "TW#%d" % (ORDER.index(a.design) + 1)
    if a.cmd == "reserve":
        if any(e.get("event") == "reserve" and e.get("meta", {}).get("design") == a.design for e in es):
            sys.exit("%s is already reserved" % a.design)
        rule = ("the tool's replicate at the same shift, 0.02-ns guard, no sign rule (D11 b), both arms; DREAMPlace's pick "
                "by one-position J_safe (D13 a)" if a.design in D11B else "0.02-ns guard, no sign rule (D6), both arms")
        e = led.reserve("heurbridge_vs_dreamplace", "%s: HeurBridge's macro layout vs DREAMPlace's at f2" % a.design,
                        "exact_rank_sum_permutation", meta={"design": a.design, "replicates": "the Track-B test's six shifts",
                                                            "gate_rule": rule,
                                                            "preregistration": PREREG.get(a.design, "reports/trackB_threeway_preregistration.md")})
        if e["ledger_id"] != want:
            sys.exit("expected %s for %s, got %s: reserve the designs in order" % (want, a.design, e["ledger_id"]))
        print(json.dumps(e))
        return
    entry = next(e for e in es if e.get("event") == "reserve" and e.get("meta", {}).get("design") == a.design)
    if any(e.get("event") == "result" and e["ledger_id"] == entry["ledger_id"] for e in es):
        sys.exit("%s already has a recorded result; the test runs once" % entry["ledger_id"])
    A = arms(a.design, Path(a.remote), a.tb_prefix, a.tw_prefix, a.campaign_prefix)
    hb, dp, tool = ([x["J"] for x in A[k]] for k in ("HeurBridge", "DREAMPlace", "tool"))
    p = rank_sum_p(hb, dp) if hb and dp else 1.0
    res = led.record(entry, p_value=p, n=len(hb) + len(dp), extra={"heurbridge": hb, "dreamplace": dp})
    p_dt = rank_sum_p(dp, tool) if dp and tool else 1.0              # reported, not tested
    fm = lambda v: "%.4f" % v if v is not None and math.isfinite(v) else "+inf"
    med = lambda k: float(np.median([x["J_before_gates"] for x in A[k]])) if A[k] else math.inf
    hrs = lambda rows: sum(float(r.get("wall_s") or 0.0) for r in rows) / 3600.0
    L = ["## %s (%s)" % (a.design, entry["ledger_id"]), "",
         "Recorded %s. **%s**: HeurBridge lower than DREAMPlace, exact one-sided rank-sum permutation p = %.4g against "
         "alpha_j = %.4g." % (res["time"], "PASSED" if res["promoted"] else "FAILED", p, entry["alpha_j"]), "",
         "Reported, not tested: DREAMPlace lower than the tool (DREAMPlace gated, the tool before the gates): p = %.4g. "
         "Median J before the gates: HeurBridge %s, DREAMPlace %s, tool %s." % (p_dt, fm(med("HeurBridge")),
                                                                               fm(med("DREAMPlace")), fm(med("tool"))), "",
         "| replicate | arm | shift | J (HeurBridge, DREAMPlace: gated; tool: before gates) | J before gates | gates failed |",
         "|---|---|---|---|---|---|"]
    for k in ("HeurBridge", "DREAMPlace", "tool"):
        for x in A[k]:
            L.append("| %s | %s | %s | %s | %s | %s |" % (x["run_id"], k, x["shift"], fm(x["J"]), fm(x["J_before_gates"]),
                                                       ", ".join(x["gates_failed"]) or "-"))
    pk = A["dp_pick"]
    L += ["", "DREAMPlace's selection: %d layouts to f1 (%d completed), %d to f2, %.1f flow-run hours; the tool's own "
          "flow run: %.2f h (the campaign's f2 baseline, median). Pick: layout %s (target density, seed: %s), %s; the "
          "replicates used layout %s (%s)." % (
              len(A["dp_f1"]), sum(r.get("status") == "ok" for r in A["dp_f1"]), len(A["dp_f2"]),
              hrs(A["dp_f1"]) + hrs(A["dp_f2"]), A["tool_run_s"] / 3600.0, pk["index"], pk["target_density_seed"],
              pk["rule"], pk["replicates_used"], "consistent" if pk["consistent"] else "INCONSISTENT with the rule"), "",
          "Sources: %s." % ", ".join(str(q.relative_to(ROOT)) if q.is_relative_to(ROOT) else str(q) for q in A["sources"]), ""]
    out = Path(a.out)
    head = ("# Track B: HeurBridge, DREAMPlace and the tool through the OpenROAD flow\n\n| Field | Value |\n|---|---|\n"
            "| Report | trackB_threeway |\n| Pre-registration | reports/trackB_threeway_preregistration.md |\n"
            "| Status of the claim | per design below |\n\n")
    text = out.read_text() if out.exists() else head
    out.write_text(text + "\n".join(L) + "\n")
    print(json.dumps(res))


if __name__ == "__main__":
    main()
