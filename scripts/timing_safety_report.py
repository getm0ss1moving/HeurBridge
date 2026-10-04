#!/usr/bin/env python3
"""J and timing safety of every Track-B layout (the owner's decision D13 (a), 4 Oct): two outputs and one score.

  python scripts/timing_safety_report.py            # writes reports/trackB_timing_safety.md

Per layout and position (a layout run at f2 unshifted or shifted): the setup and hold checks of decision D11 (b)
(slack >= the tool's run at the same shift - 0.02 ns, no sign rule); a failed flow fails both checks.
  J      median J before the gates over the layout's positions (+inf if half or more failed)
  S      share of the timing checks passed
  J_safe J + LAMBDA * (1 - S)      (LAMBDA = 0.04: failing every check costs 0.04 J)
For new tests the pick of every arm is the lowest J_safe (ties: lower J).

Selection stage: the campaigns' unshifted f2 layouts (the tool's unshifted replay as reference) and the three best
layouts' shifted bands (the `band` phase, references the replays at the same nominal shifts); DREAMPlace's f2 layouts.
Test stage: every layout run at the Track-B test's six shifts (the tool's replicates as references).
"""

import glob
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heurbridge.eval import cost  # noqa: E402

LAMBDA = 0.04
DESIGNS = ("bp_fe_top", "bp_be_top", "ariane136", "swerv_wrapper")


def jl(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def flow_ok(r):
    rec = r.get("record") if isinstance(r.get("record"), dict) else {}
    return bool(r.get("status") == "ok" and rec.get("returncode") in (0, None) and rec)


def position(r, ref, base):
    """(J before the gates, setup passed, hold passed, smaller margin) of one run against the tool's run ``ref``."""
    if not flow_ok(r):
        return math.inf, False, False, -math.inf
    c = cost.evaluate(r["record"], base, fidelity=2, timing_sign_rule=False)
    out = []
    for k in ("setup", "hold"):
        x, t = cost._num(r["record"].get(k + "_wns_ns")), cost._num((ref or {}).get(k + "_wns_ns"))
        out.append(-math.inf if x is None or t is None else x - (t - cost.GUARD_NS))
    return (c.J if math.isfinite(c.J) else math.inf), out[0] >= -1e-12, out[1] >= -1e-12, min(out)


def summary(pos: list, lam: float = LAMBDA) -> dict:
    js = [p[0] for p in pos]
    passed = sum(p[1] + p[2] for p in pos)
    s = passed / (2.0 * len(pos))
    j = float(np.median(js)) if js else math.inf
    marks = " ".join(("S" if p[1] else "-") + ("H" if p[2] else "-") if math.isfinite(p[0]) else "xx" for p in pos)
    return {"J": j, "S": s, "passed": passed, "checks": 2 * len(pos), "marks": marks,
            "margin": min(p[3] for p in pos) if pos else -math.inf, "J_safe": j + lam * (1.0 - s)}


def one(pattern):
    fs = sorted(glob.glob(str(ROOT / pattern)))
    return Path(fs[0]) if len(fs) == 1 else None


def selection_stage(d: str) -> tuple:
    camp = ROOT / ("runs/remote/seedB_orfs7_%s/runs/seed_orfs/%s" % (d, d))
    recs2 = [r for r in json.loads((camp / "baseline_f2.json").read_text())["records"] if r.get("returncode") == 0]
    base = cost.Baseline.from_records(d, recs2)
    rows = jl(camp / "evals_f2.jsonl")
    reps = {}
    for r in rows:
        if r.get("program") == "M1_replay" and flow_ok(r):
            k = r["run_id"]
            reps[int(k[-4]) if k[-5] == "p" else 0] = r["record"]
    band = one("runs/remote/seedB_band_%s/runs/seed_orfs/%s/evals_f2.jsonl" % (d, d))
    bands = {}
    for r in (jl(band) if band else []):
        if r.get("program") == "CAND_BAND":
            bands.setdefault(r["band_of"], []).append((int(r["seed"]), r))
    out = []
    for r in rows:
        if r.get("program") == "M1_replay":
            continue
        pos = [position(r, reps.get(0), base)] + [position(b, reps.get(k), base) for k, b in sorted(bands.get(r["run_id"], []))]
        arm = "HeurBridge (local search)" if r.get("program") == "LS" else "HeurBridge (programs)"
        out.append(dict(summary(pos), layout=r["run_id"][:-3], arm=arm, positions=len(pos)))
    tw = one("runs/remote/tw_*/runs/seed_orfs/%s/evals_ext_dp.jsonl" % d)
    for r in (jl(tw) if tw else []):
        if r.get("program") == "EXT_DP_F2":
            out.append(dict(summary([position(r, reps.get(0), base)]), layout=r["run_id"][:-3], arm="DREAMPlace",
                            positions=1))
    return out, base, reps


def test_stage(d: str, base) -> list:
    tb = one("runs/remote/tb_%s/runs/seed_orfs/%s/evals_tb.jsonl" % (d, d))
    if tb is None:
        return []
    rows = jl(tb)
    tool = {tuple(r.get("tb_shift") or ()): r for r in rows if r.get("program") == "TB_REF"}
    done = [r["record"] for r in tool.values() if flow_ok(r)]
    fallback = {"setup_wns_ns": float(np.median([cost._num(x["setup_wns_ns"]) for x in done])),
                "hold_wns_ns": float(np.median([cost._num(x["hold_wns_ns"]) for x in done]))} if done else None
    ref = lambda r: (tool[tuple(r["tb_shift"])]["record"] if tuple(r.get("tb_shift") or ()) in tool
                     and flow_ok(tool[tuple(r["tb_shift"])]) else fallback)
    arms = [("HeurBridge (local search)", rows, "TB_CAND"), ("tool", rows, "TB_REF")]
    for pat, prog, arm in (("runs/remote/tp_*/runs/seed_orfs/%s/evals_tb_pg.jsonl", "TB_PG_CAND", "HeurBridge (programs)"),
                           ("runs/remote/tw_*/runs/seed_orfs/%s/evals_ext_dp.jsonl", "EXT_DP_TB", "DREAMPlace"),
                           ("runs/remote/tls_*/runs/seed_orfs/%s/evals_tls_f2.jsonl", "TLS_TB", "HeurBridge (timing-aware search, D13 b)")):
        p = one(pat % d)
        if p is not None:
            arms.append((arm, jl(p), prog))
    out = []
    for arm, rs, prog in arms:
        sel = sorted([r for r in rs if r.get("program") == prog], key=lambda r: r["run_id"])
        if sel:
            out.append(dict(summary([position(r, ref(r), base) for r in sel]), arm=arm, positions=len(sel)))
    return out


def fm(v, f="%.4f"):
    return f % v if v is not None and math.isfinite(v) else ("+inf" if v and v > 0 else "-inf" if v else "-")


def main():
    L = ["# Track B: J and timing safety of every layout (decision D13 (a))", "",
         "| Field | Value |", "|---|---|", "| Report | trackB_timing_safety |",
         "| Label | descriptive (existing runs; no test is re-decided; the recorded TB, TW and TP results stand) |",
         "| Code | scripts/timing_safety_report.py |", "",
         "**The rule for new tests (the owner's decision D13 (a), 4 Oct).** Every position a layout ran at (f2,",
         "unshifted or shifted) has two timing checks, setup and hold, each passed if its slack is at least the tool's run",
         "at the same shift minus 0.02 ns (decision D11 (b)); a failed flow fails both. Two outputs per layout: **J**, the",
         "median J before the gates over its positions, and **S**, the share of its timing checks passed. One score:",
         "**J_safe = J + %.2f x (1 - S)**: failing every check costs %.2f J, about the margin's price measured on"
         % (LAMBDA, LAMBDA),
         "swerv_wrapper (reports/timing_margin_explore.md). For new tests the best few layouts of every arm by J are run at",
         "the band's shifts too, so that compared layouts have the same positions, and each arm's pick is its lowest J_safe",
         "among them. Below, layouts with one position are listed for completeness; the picks compare equal positions.",
         "Marks per position: S/H passed setup/hold, - failed, xx flow failed; margin = the smallest slack minus its",
         "threshold, ns.", ""]
    for d in DESIGNS:
        sel, base, _ = selection_stage(d)
        sel.sort(key=lambda x: (x["J_safe"], x["J"]))
        L += ["## %s" % d, "", "**Selection stage** (each campaign's f2 layouts; the three with a shifted band have 4"
              " positions; DREAMPlace's f2 layouts, 1 position):", "",
              "| rank | layout | arm | positions | J | checks passed | marks | margin (ns) | J_safe |",
              "|---|---|---|---|---|---|---|---|---|"]
        for i, x in enumerate(sel, 1):
            L.append("| %d | %s | %s | %d | %s | %d of %d | %s | %s | %s |" % (
                i, x["layout"], x["arm"], x["positions"], fm(x["J"]), x["passed"], x["checks"], x["marks"],
                fm(x["margin"], "%.3f"), fm(x["J_safe"])))
        L.append("")
        for arm in ("HeurBridge", "DREAMPlace"):
            cands = [x for x in sel if x["arm"].startswith(arm)]
            if cands:                                   # compared only with as many positions as the best-measured
                npos = max(x["positions"] for x in cands)
                cands = [x for x in cands if x["positions"] == npos]
                pk = {lam: min(cands, key=lambda x: (x["J"] + lam * (1 - x["S"]), x["J"]))["layout"]
                      for lam in (0.0, 0.02, 0.04, 0.08)}
                L.append("- %s's pick by J_safe among its layouts with %d position%s: %s (lambda 0: %s; 0.02: %s; 0.08: %s)." % (
                    arm, npos, "s" if npos > 1 else "", pk[0.04], pk[0.0], pk[0.02], pk[0.08]))
        test = test_stage(d, base)
        if test:
            L += ["", "**Test stage** (the Track-B test's six shifts; the tool's same-shift replicate as reference):", "",
                  "| arm | positions | J | checks passed | marks | margin (ns) | J_safe |", "|---|---|---|---|---|---|---|"]
            for x in test:
                L.append("| %s | %d | %s | %d of %d | %s | %s | %s |" % (
                    x["arm"], x["positions"], fm(x["J"]), x["passed"], x["checks"], x["marks"], fm(x["margin"], "%.3f"),
                    fm(x["J_safe"]) if x["arm"] != "tool" else "- (reference)"))
        L.append("")
    L += ["Sources: local run files `runs/remote/seedB_orfs7_<design>/runs/seed_orfs/<design>/evals_f2.jsonl` and"
          " `baseline_f2.json`, `runs/remote/seedB_band_<design>/.../evals_f2.jsonl` (bands),"
          " `runs/remote/tb_<design>/.../evals_tb.jsonl`, `runs/remote/tw_*/.../evals_ext_dp.jsonl`,"
          " `runs/remote/tp_*/.../evals_tb_pg.jsonl`, `runs/remote/tls_*/.../evals_tls_f2.jsonl` (when present).", ""]
    (ROOT / "reports" / "trackB_timing_safety.md").write_text("\n".join(L))
    print("wrote reports/trackB_timing_safety.md")


if __name__ == "__main__":
    main()
