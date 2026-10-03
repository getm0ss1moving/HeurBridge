#!/usr/bin/env python3
"""The confirmatory re-test of reports/portfolio_retest_preregistration.md (RL#4): two densities vs two seeds for the
tool on ISPD2005 without bigblue3, with tool runs that place every macro.

  python scripts/portfolio_retest_confirm.py reserve      # once, before any corrected ISPD2005 tool run
  python scripts/portfolio_retest_confirm.py analyze      # once, after every rc4_* job is fetched to runs/remote/

Per design, the rows of scripts/tool_runs.py at target density 0.9 and 0.6 (runs/tool_runs_td0.9/<design>,
runs/tool_runs_td0.6/<design>, one job each).  Unit (design, s): method = the better of T_s at 0.9 and at 0.6 by the
selection seed (ties: 0.9); comparator = the better of T_s and T_(s+1 mod 8) at 0.9.  Endpoint: the median J over fresh
f1 seeds; failures are +inf, never picked over a finite run, named.  Paired one-sided Wilcoxon, +inf kept.
"""

import argparse
import glob
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heurbridge.stats.alpha_ledger import AlphaLedger  # noqa: E402
from heurbridge.stats.paired import wilcoxon_less  # noqa: E402

DESIGNS = ("adaptec1", "adaptec2", "adaptec3", "adaptec4", "bigblue1", "bigblue2", "bigblue4")
SEEDS = 8
DENS = (0.9, 0.6)
META = {"family": "ispd2005 without bigblue3", "designs": list(DESIGNS), "tool_seeds": list(range(SEEDS)),
        "densities": list(DENS), "select_seed": 0, "eval_seeds": [1, 2, 3], "endpoint": "median J over fresh f1 seeds",
        "method": "the better of the seed-s runs at 0.9 and 0.6 by the selection seed",
        "comparator": "the better of seeds s and s+1 (mod 8) at 0.9 by the selection seed", "units": 56,
        "tool_input": "every macro movable (commit 157bf21)", "replaces": "RL#3 (defect: reports/defect_ispd_tool_runs.md)",
        "preregistration": "reports/portfolio_retest_preregistration.md"}


def jl(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def sel(r):
    return r["J_select"]["tool"] if r is not None and "J_select" in r else math.inf


def fresh(r):
    return r["J_eval"]["tool"] if r is not None and "J_select" in r else math.inf


def pick(cands):
    """Fresh J of the candidate with the lowest selection J (the first on ties); +inf if all failed."""
    return fresh(min(cands, key=sel))


def units(remote: Path, prefix: str) -> tuple:
    out, fails, srcs = [], [], []
    for d in DESIGNS:
        rows = {}
        for t in DENS:
            fs = sorted(glob.glob(str(remote / (prefix + "*") / "runs" / ("tool_runs_td%g" % t) / d / "rows.jsonl")))
            if len(fs) > 1:
                sys.exit("%s at %g: more than one source %s; the protocol has one run per design" % (d, t, fs))
            srcs += [str(Path(f).relative_to(ROOT)) if Path(f).is_relative_to(ROOT) else f for f in fs]
            rows[t] = {r["tool_seed"]: r for r in jl(fs[0])} if fs else {}
            for s in range(SEEDS):
                r = rows[t].get(s)
                if r is None:
                    fails.append("%s seed %d at %g: no row (job missing or incomplete)" % (d, s, t))
                elif "J_select" not in r:
                    fails.append("%s seed %d at %g: %s" % (d, s, t, r.get("failure")))
        r9, r6 = rows[0.9], rows[0.6]
        for s in range(SEEDS):
            a, b, c = r9.get(s), r6.get(s), r9.get((s + 1) % SEEDS)
            out.append({"design": d, "seed": s, "method": pick([a, b]), "comparator": pick([a, c]),
                        "one_09": fresh(a), "one_06": fresh(b), "picked_06": sel(b) < sel(a)})
    return out, sorted(set(fails)), srcs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["reserve", "analyze"])
    ap.add_argument("--ledger", default=str(ROOT / "stats" / "alpha_ledger.jsonl"))
    ap.add_argument("--remote", default=str(ROOT / "runs" / "remote"))
    ap.add_argument("--prefix", default="rc4_", help="job-name prefix of the corrected tool-run jobs")
    ap.add_argument("--out", default=str(ROOT / "reports" / "portfolio_retest_confirmatory.md"))
    a = ap.parse_args()
    led = AlphaLedger(a.ledger, campaign="RL")
    es = led._entries()
    if a.cmd == "reserve":
        if any(e.get("event") == "reserve" and e["ledger_id"] == "RL#4" for e in es):
            sys.exit("RL#4 is already reserved")
        e = led.reserve("method_vs_tool", "corrected re-test: two densities {0.9, 0.6} vs two seeds at 0.9 @ISPD2005 "
                        "without bigblue3", "wilcoxon_less", meta=META)
        if e["ledger_id"] != "RL#4":
            sys.exit("expected RL#4, got %s: check the ledger" % e["ledger_id"])
        print(json.dumps(e))
        return
    entry = next(e for e in es if e.get("event") == "reserve" and e["ledger_id"] == "RL#4")
    if any(e.get("event") == "result" and e["ledger_id"] == "RL#4" for e in es):
        sys.exit("RL#4 already has a recorded result; the test runs once")
    U, fails, srcs = units(Path(a.remote), a.prefix)
    M = np.array([u["method"] for u in U], float)
    C = np.array([u["comparator"] for u in U], float)
    t = wilcoxon_less(M, C)
    res = led.record(entry, p_value=t["p"], n=len(U), extra={"median_diff": t["median_diff"], "frac_better": t["frac_better"],
                                                              "n_nonzero": t["n_nonzero"], "failures": fails})
    fm = lambda v: "%.4f" % np.mean(v) if np.all(np.isfinite(v)) else "+inf (%d of %d)" % ((~np.isfinite(v)).sum(), len(v))
    L = ["# Two densities vs two seeds for the tool, corrected re-test: confirmatory result (Track A, ISPD2005)", "",
         "| Field | Value |", "|---|---|", "| Report | portfolio_retest_confirmatory |",
         "| Date | %s |" % time.strftime("%Y-%m-%d %H:%M"), "| Pre-registration | reports/portfolio_retest_preregistration.md |",
         "| alpha-ledger | %s, alpha_4 = %.4g, reserved %s, result recorded %s |" % (entry["ledger_id"], entry["alpha_j"],
                                                                                   entry["time"], res["time"]),
         "| Status of the claim | **pre-registered confirmatory test: %s** |" % ("PASSED" if res["promoted"] else "FAILED"), "",
         "## Primary test", "",
         "Paired one-sided Wilcoxon signed-rank on %d units (design, tool seed): the better of the seed-s runs at 0.9 and "
         "0.6 lower than the better of seeds s and s+1 at 0.9, +inf kept: p = %.3g against alpha_4 = %.4g; median "
         "difference %+.4f; lower in %d units, equal in %d, higher in %d. The pick was the run at 0.6 in %d units." % (
             len(U), t["p"], entry["alpha_j"], t["median_diff"], int((M < C).sum()), int((M == C).sum()),
             int((M > C).sum()), sum(u["picked_06"] for u in U)), "",
         "## Per design (reported, not tested; J against the benchmark's macro placement, 0.45)", "",
         "| design | one run at 0.9 | one run at 0.6 | two seeds at 0.9 | two densities |", "|---|---|---|---|---|"]
    for d in DESIGNS:
        k = [i for i, u in enumerate(U) if u["design"] == d]
        col = lambda key: np.array([U[i][key] for i in k], float)
        L.append("| %s | %s | %s | %s | %s |" % (d, fm(col("one_09")), fm(col("one_06")), fm(C[k]), fm(M[k])))
    allc = lambda key: np.array([u[key] for u in U], float)
    L += ["| **all** | %s | %s | %s | %s |" % (fm(allc("one_09")), fm(allc("one_06")), fm(C), fm(M)), "",
          "Failures (+inf, by name): %s." % ("; ".join(fails) if fails else "none"), "", "Sources: %s." % ", ".join(srcs), ""]
    Path(a.out).write_text("\n".join(L) + "\n")
    print(json.dumps(res))


if __name__ == "__main__":
    main()
