#!/usr/bin/env python3
"""Audit of the project's tests (the owner's request of 3 Oct: check whether other tests have problems like the
ISPD2005 tool-input defect).  Recomputes from local run files what can be recomputed and prints a markdown section
per check; reports/test_audit.md is written around this output.

  python scripts/audit_tests.py > /tmp/audit.md

Checks:
  1. alpha-ledger: every reserved test, its result and its notes (stats/alpha_ledger.jsonl).
  2. Track A f1 keeps the macros fixed: the measured maximum macro shift of every f1 record of the Track-A seeding
     campaigns (heurbridge/eval/dreamplace.py writes macro_max_shift; a shift above 1e-6 of the core is a named
     failure, macros_moved).
  3. The tool's runs move the macros: the spread of the tool's J over seeds per design (a frozen run gives the same J for
     every seed), on IBM (relinking runs) and on ISPD2005 (RL#4).
  4. E0's arms are distinct: per protocol, the units where the co-trained partner's J equals another partner's.
  5. E0's same-seed selection: the optimism of the co-trained J (fresh-seed median minus the recorded J) on the
     sampled units (scripts/e0_seed_bias.py; jobs e0bias_a and e0bias_b*).
"""

import glob
import json
import math
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def jl(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def rel(p):
    return str(Path(p).resolve().relative_to(ROOT))


def ledger():
    L = ["## 1 Every registered test (alpha-ledger)", "",
         "| campaign | entry | alpha_j | what | p | outcome | notes |", "|---|---|---|---|---|---|---|"]
    es = jl(ROOT / "stats" / "alpha_ledger.jsonl")
    res = {(e["campaign"], e["ledger_id"]): e for e in es if e.get("event") == "result"}
    notes = defaultdict(list)
    for e in es:
        if e.get("event") == "note":
            notes[(e["campaign"], e["ledger_id"])].append(str(e.get("note") or e.get("text") or e.get("meta") or "")[:90])
    for i, e in enumerate(es, 1):
        if e.get("event") != "reserve":
            continue
        k = (e["campaign"], e.get("ledger_id") or "%s#%d" % (e["campaign"], e["j"]))
        r = res.get(k)
        out = "-" if r is None else ("passed" if r.get("promoted") else "failed")
        L.append("| %s | %s | %.6g | %s | %s | %s | %s |" % (
            k[0], k[1], e["alpha_j"], str(e.get("artifact", ""))[:70], "-" if r is None else "%.3g" % r["p"], out,
            "; ".join(notes.get(k, [])) or "-"))
    L += ["", "Source: stats/alpha_ledger.jsonl (every line).", ""]
    return L


def f1_fixity():
    fs = sorted(glob.glob(str(ROOT / "runs/remote/seedA_*_combined/*/evals.jsonl")))
    n = meas = 0
    mx, named = 0.0, 0
    for f in fs:
        for r in jl(f):
            n += 1
            rec = r.get("record") if isinstance(r.get("record"), dict) else {}
            if (rec.get("failure") or "") == "macros_moved":
                named += 1
            v = rec.get("macro_max_shift")
            if v is not None:
                meas += 1
                mx = max(mx, float(v))
    return ["## 2 Track A: f1 keeps the macros fixed", "",
            "Of %d rows of the Track-A seeding campaigns (%d files), %d carry an f1 record with the measured maximum macro "
            "shift; the largest is %g (source units); %d rows failed with `macros_moved`. The other %d rows failed "
            "before f1 (sandbox, memory, P_M), each by name." % (n, len(fs), meas, mx, named, n - meas), "",
            "Sources: `runs/remote/seedA_*_combined/*/evals.jsonl` (field `record.macro_max_shift`); the guard: "
            "heurbridge/eval/dreamplace.py:258-264 (in place since v0.12.0, before these campaigns).", ""]


def tool_spread():
    L = ["## 3 The tool's runs move the macros (J spread over seeds)", "",
         "A run that leaves the macros where they start gives the same J for every seed (the ISPD2005 defect: "
         "0.4499-0.4503 on seven designs for every seed and density, reports/density_confirmatory.md:19-24).", "",
         "| family | design | runs | J min | J max | spread | source |", "|---|---|---|---|---|---|---|"]
    srcs = []
    for f in sorted(glob.glob(str(ROOT / "runs/remote/relinkall_*/runs/tool_runs/*/rows.jsonl"))):
        rows = [r for r in jl(f) if "J_select" in r]
        js = [r["J_select"]["tool"] for r in rows if math.isfinite(r["J_select"]["tool"])]
        if js:
            L.append("| IBM | %s | %d | %.4f | %.4f | %.4f | %s |" % (Path(f).parent.name, len(js), min(js), max(js),
                                                                    max(js) - min(js), rel(f)))
    for f in sorted(glob.glob(str(ROOT / "runs/remote/rc4_*/runs/tool_runs_td0.9/*/rows.jsonl"))):
        rows = [r for r in jl(f) if "J_select" in r]
        js = [r["J_select"]["tool"] for r in rows if math.isfinite(r["J_select"]["tool"])]
        if js:
            L.append("| ISPD2005 (RL#4, 0.9) | %s | %d | %.4f | %.4f | %.4f | %s |" % (
                Path(f).parent.name, len(js), min(js), max(js), max(js) - min(js), rel(f)))
    return L + [""]


def e0_ties():
    L = ["## 4 E0's arms are distinct", "",
         "| protocol | units | co-trained = memetic | co-trained = repertoire | co-trained = raw layout |",
         "|---|---|---|---|---|"]
    for f in sorted(glob.glob(str(ROOT / "runs/e0_full/*/e0_rows.jsonl"))):
        by = defaultdict(dict)
        for r in jl(f):
            by[(r["design"], r["program"], r["seed"])][r["partner"]] = r["J"]
        u = [v for v in by.values() if "cotrained" in v]
        eq = lambda k: sum(1 for v in u if k in v and v[k] == v["cotrained"])
        L.append("| %s | %d | %d | %d | %d |" % (Path(f).parent.name, len(u), eq("memetic"), eq("repertoire"), eq("none")))
    return L + ["", "Source: `runs/e0_full/*/e0_rows.jsonl` (the combined rows of the full E0).", ""]


def e0_optimism():
    rows, srcs = {}, []
    for f in sorted(glob.glob(str(ROOT / "runs/remote/e0bias_a/runs/e0_bias/*/rows.jsonl"))) + \
            sorted(glob.glob(str(ROOT / "runs/remote/e0bias_b*/runs/e0_bias2/*/rows.jsonl"))):
        srcs.append(rel(f))
        for r in jl(f):
            k = (r["design"], r["program"], r["seed"])
            if "optimism" in r or k not in rows:          # a re-scored unit replaces its excluded first row
                rows[k] = r
    sc = [r for r in rows.values() if "optimism" in r]
    ex = [r for r in rows.values() if "optimism" not in r]
    o = sorted(r["optimism"] for r in sc)
    q = lambda p: o[min(len(o) - 1, int(p * (len(o) - 1) + 0.5))]
    L = ["## 5 E0's same-seed selection (optimism of the co-trained J)", "",
         "Units sampled: %d (6 per design where available); scored: %d; still excluded: %d%s." % (
             len(rows), len(sc), len(ex), (" (" + "; ".join("%s %s s%d: %s" % (r["design"], r["program"], r["seed"],
                                                                             r.get("excluded")) for r in ex) + ")") if ex else ""),
         "", "Optimism = median J over fresh f1 seeds 1-3 minus the recorded J (positive: the recorded J flattered the "
             "layout): median %+.5f, mean %+.5f, quartiles %+.5f / %+.5f, range %+.5f to %+.5f; positive in %d of %d." % (
             st.median(o), st.mean(o), q(0.25), q(0.75), o[0], o[-1], sum(v > 0 for v in o), len(o)) if o else "No unit scored.",
         "", "| design | units scored | median optimism |", "|---|---|---|"]
    by = defaultdict(list)
    for r in sc:
        by[r["design"]].append(r["optimism"])
    for d in sorted(by):
        L.append("| %s | %d | %+.5f |" % (d, len(by[d]), st.median(by[d])))
    return L + ["", "Sources: %s." % ", ".join("`%s`" % s for s in srcs), ""]


HEAD = """# Audit of the project's tests

| Field | Value |
|---|---|
| Report | test_audit |
| Date | %s |
| Why | the owner's request of 3 Oct: make a correct ISPD2005 test and check whether the other tests have problems like the ISPD2005 tool-input defect |
| Label | development / descriptive: an audit; no test is re-run or re-decided here |
| Code | scripts/audit_tests.py (`--report` writes this file; Sections 1-5 are recomputed from local run files) |

## Summary

**Problems found, and what each means for the results:**

1. **The tool's input froze ISPD2005's macros** (found 3 Oct): RL#1-RL#3 are not evidence for their claims (notes in
   Section 1; reports/defect_ispd_tool_runs.md). The corrected re-test RL#4 passed (Section 1;
   reports/portfolio_retest_confirmatory.md). The tool's runs now move the macros on every ISPD2005 design (Section 3),
   and a run that leaves a macro where it started is a named failure (heurbridge/eval/dreamplace.py, commit c9f0008).
2. **The Track-B test's hold gate:** TB#3 failed on a hold gate whose reference (the median of four unshifted replays,
   +0.015 ns) lies above the tool's own shifted replicates, which fail the same check on 5 of 6 shifts; TB#1 passed
   with one replicate exactly at its hold threshold (reports/trackB_confirmatory.md, Summary, notes 1 and 3). Stated in
   that report; no result is changed.
3. **bp_fe_top's same-path replay band was poorer for the tool than fresh runs:** the campaign's four replays of the
   tool's layout at f2 have J 1.03-1.40 and setup TNS -0.50 to -2.14 ns; the Track-B test's six reference replicates of
   the same layout have J 0.96-1.08 and TNS -0.15 to -0.68 ns (local run files
   `runs/remote/seedB_orfs7_bp_fe_top/runs/seed_orfs/bp_fe_top/evals_f2.jsonl:1-4`,
   `runs/remote/tb_bp_fe_top/runs/seed_orfs/bp_fe_top/evals_tb.jsonl`). The default flow path did not change between
   them (git log of heurbridge/eval/orfs.py, heurbridge/pipeline/evaluators.py and scripts/server/trackb.sh since 28 Sep:
   optional phases only; the warm start is off by default, heurbridge/pipeline/evaluators.py:145), so this is
   run-to-run timing variance. The campaign report's comparison with that band (reports/T2_trackB_orfs_bp_fe_top.md:47)
   flattered the candidate; the test's fresh references are the fair comparison, and TB#1 passed on them. On bp_be_top
   and ariane136 the replays and the references agree.
4. **The decision record said HeurBridge does not optimize the flow's score;** its Track-B local search scores every
   move with the flow at f1 (heurbridge/pipeline/seed_archive.py:269-296). Corrected in reports/next_phase_decisions.md
   (D9) and stated in the three-way comparison's pre-registration.
5. **E0's guard and its final cost share one f1 run (seed 0):** measured on rebuilt co-trained layouts, the optimism is
   negligible (Section 5) against the 0.026 gap between the co-trained and the memetic partner's mean J
   (reports/E0_partner_ablation.md:29, :31). G0' stands.
6. **The audit's own first run** excluded 16 of 46 units with a 1e-9 reproduction tolerance (float rounding, all within
   6e-8); the tolerance is 1e-6 now and the units were re-scored (Section 5).
7. **DREAMPlace on the Track-B designs (new code, found before any use):** its Abacus pass aborted 15 of 36 runs, and
   P_M's grid moved its packed macros by 2-6 %% of the die on ariane136; both fixed (CHANGELOG.md, 3 Oct 23:15).

**Checks that found no problem:** f1 keeps the macros fixed (Section 2); the tool's runs move the macros on IBM and,
after the fix, on ISPD2005 (Section 3); E0's arms are distinct (Section 4: the co-trained partner equals another
partner only where both keep the raw layout); Track-B macro imports are honoured: 52,974 macro placements read back
from the flow's outputs on 224, x exact, y within 0.105 um, the tool's macro placer never ran (checked 3 Oct 11:00-12:00,
recorded in HANDOFF.md:%s; the commands were not kept as a script and the flow's outputs are on 224 only).

**Not re-checked here:** the bridge-promotion tests (campaigns algR_dev, algR_trackA, E0_dev) beyond their ledger
entries (Section 1).

"""


def main():
    out = []
    for f in (ledger, f1_fixity, tool_spread, e0_ties, e0_optimism):
        out += f()
    if "--report" in sys.argv:
        import time
        hl = (ROOT / "HANDOFF.md").read_text().splitlines()      # the session-4 record of the import check (its line moves)
        k = next(i for i, l in enumerate(hl, 1) if "52,974 macro placements" in l)
        (ROOT / "reports" / "test_audit.md").write_text(HEAD % (time.strftime("%Y-%m-%d %H:%M"), "%d-%d" % (k - 1, k + 1))
                                                        + "\n".join(out) + "\n")
        print("wrote reports/test_audit.md")
        return
    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
