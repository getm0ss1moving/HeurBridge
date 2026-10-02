#!/usr/bin/env python3
"""The confirmatory test of reports/density_preregistration.md: one tool run at target density d* vs the tool's best
of four runs at density 0.9 (the configuration that defines J = 0.45), on ISPD2005.

  python scripts/density_confirm.py reserve      # once, before any ISPD2005 run at density d* (alpha-ledger RL#2)
  python scripts/density_confirm.py analyze      # once, after every rtd_* and rlc_* job is fetched to runs/remote/

Units (design, tool seed s), s = 0-7: the method is the tool's layout for seed s at d* (scripts/tool_runs.py rows of
the rtd_* jobs); the comparator is the best of the tool's seeds s..s+3 (mod 8) at density 0.9 by the selection seed,
as in RL#1 (the "best4" of scripts/relink_eval.py rows of the rlc_* jobs).  Both are judged by the median J over
fresh f1 seeds 1-3; failures are +inf, named.  Paired one-sided Wilcoxon (heurbridge.stats.paired.wilcoxon_less).
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
sys.path.insert(0, str(ROOT / "scripts"))

from heurbridge.stats.alpha_ledger import AlphaLedger  # noqa: E402
from heurbridge.stats.paired import wilcoxon_less  # noqa: E402
from relink_confirm import DESIGNS, SEEDS, jl  # noqa: E402

TD = 0.6                       # d*, fixed in reports/density_preregistration.md before any ISPD2005 run at it
META = {"family": "ispd2005", "designs": list(DESIGNS), "tool_seeds": list(range(SEEDS)), "target_density": TD,
        "comparator": "the tool's best of 4 seeds (s..s+3 mod 8) at target density 0.9 by the selection seed (RL#1's best4)",
        "select_seed": 0, "eval_seeds": [1, 2, 3], "endpoint": "median J over fresh f1 seeds", "units": 64,
        "preregistration": "reports/density_preregistration.md"}


def one(pattern: str) -> list:
    fs = sorted(glob.glob(pattern))
    if len(fs) > 1:
        sys.exit("more than one source: %s" % fs)
    return fs


def units(remote: Path, prefix: str, ref_prefix: str) -> tuple:
    out, fails, srcs = [], [], []
    for d in DESIGNS:
        mf = one(str(remote / (prefix + "*") / "runs" / ("tool_runs_td%g" % TD) / d / "rows.jsonl"))
        rf = one(str(remote / (ref_prefix + "*") / "runs" / "relink" / d / "rows.jsonl"))
        tf = one(str(remote / (ref_prefix + "*") / "runs" / "tool_runs" / d / "rows.jsonl"))
        srcs += [str(Path(f).relative_to(ROOT)) if Path(f).is_relative_to(ROOT) else f for f in mf + rf + tf]
        mrows = {r["tool_seed"]: r for r in jl(mf[0])} if mf else {}
        rrows = {r["tool_seed"]: r for r in jl(rf[0])} if rf else {}
        trows = {r["tool_seed"]: r for r in jl(tf[0])} if tf else {}
        cost = lambda r: (r.get("cost_s", {}).get("tool", r.get("tool_s", math.nan)) + r.get("cost_s", {}).get("f1", 0.0)) \
            if r else math.nan
        for s in range(SEEDS):
            m, r = mrows.get(s), rrows.get(s)
            if m is None:
                fails.append("%s seed %d: no density-%g row (job missing or incomplete)" % (d, s, TD))
            elif "J_select" not in m:
                fails.append("%s seed %d at density %g: %s" % (d, s, TD, m.get("failure")))
            if r is None:
                fails.append("%s seed %d: no RL#1 row for the comparator" % (d, s))
            J_m = m["J_eval"]["tool"] if m is not None and "J_select" in m else math.inf
            J_r = r["J_eval"]["best4"] if r is not None else math.inf
            out.append({"design": d, "seed": s, "method": J_m, "best4_09": J_r,
                        "single_09": r["J_eval"]["tool"] if r is not None else math.inf,
                        "cost_method": cost(m), "cost_best4": sum(cost(trows.get((s + i) % SEEDS)) for i in range(4))})
    return out, sorted(set(fails)), srcs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["reserve", "analyze"])
    ap.add_argument("--ledger", default=str(ROOT / "stats" / "alpha_ledger.jsonl"))
    ap.add_argument("--remote", default=str(ROOT / "runs" / "remote"))
    ap.add_argument("--prefix", default="rtd_", help="job-name prefix of the density-d* jobs")
    ap.add_argument("--ref-prefix", default="rlc_", help="job-name prefix of RL#1's jobs (the density-0.9 comparator)")
    ap.add_argument("--out", default=str(ROOT / "reports" / "density_confirmatory.md"))
    a = ap.parse_args()
    led = AlphaLedger(a.ledger, campaign="RL")
    es = led._entries()
    if a.cmd == "reserve":
        if any(e.get("event") == "reserve" and e["ledger_id"] == "RL#2" for e in es):
            sys.exit("RL#2 is already reserved")
        e = led.reserve("method_vs_tool", "one tool run at target density %g vs the tool's best of 4 at 0.9 @ISPD2005" % TD,
                        "wilcoxon_less", meta=META)
        if e["ledger_id"] != "RL#2":
            sys.exit("expected RL#2, got %s: check the ledger" % e["ledger_id"])
        print(json.dumps(e))
        return
    entry = next(e for e in es if e.get("event") == "reserve" and e["ledger_id"] == "RL#2")
    if any(e.get("event") == "result" and e["ledger_id"] == "RL#2" for e in es):
        sys.exit("RL#2 already has a recorded result; the test runs once")
    U, fails, srcs = units(Path(a.remote), a.prefix, a.ref_prefix)
    M = np.array([u["method"] for u in U], float)
    B = np.array([u["best4_09"] for u in U], float)
    S1 = np.array([u["single_09"] for u in U], float)
    t = wilcoxon_less(M, B)
    res = led.record(entry, p_value=t["p"], n=len(U), extra={"median_diff": t["median_diff"], "frac_better": t["frac_better"],
                                                              "n_nonzero": t["n_nonzero"], "failures": fails})
    fm = lambda v: "%.4f" % np.mean(v) if np.all(np.isfinite(v)) else "+inf (%d of %d)" % ((~np.isfinite(v)).sum(), len(v))
    L = ["# One tool run at target density %g vs the tool's best of four at 0.9: confirmatory result (Track A, ISPD2005)" % TD, "",
         "| Field | Value |", "|---|---|", "| Report | density_confirmatory |", "| Date | %s |" % time.strftime("%Y-%m-%d %H:%M"),
         "| Pre-registration | reports/density_preregistration.md |",
         "| alpha-ledger | %s, alpha_2 = %.4g, reserved %s, result recorded %s |" % (entry["ledger_id"], entry["alpha_j"],
                                                                                   entry["time"], res["time"]),
         "| Status of the claim | **pre-registered confirmatory test: %s** |" % ("PASSED" if res["promoted"] else "FAILED"), "",
         "## Primary test", "",
         "Paired one-sided Wilcoxon signed-rank on %d units (design, tool seed), one run at density %g lower than the best of "
         "four at 0.9, +inf kept: p = %.3g against alpha_2 = %.4g; median difference %+.4f; lower in %d units, higher in %d." % (
             len(U), TD, t["p"], entry["alpha_j"], t["median_diff"], int((M < B).sum()), int((M > B).sum())), "",
         "## Per design (reported, not tested)", "",
         "| design | density 0.9, one run | density 0.9, best of 4 | density %g, one run | wall-clock s: one run at %g / best of 4 at 0.9 |" % (TD, TD),
         "|---|---|---|---|---|"]
    for d in DESIGNS:
        k = [i for i, u in enumerate(U) if u["design"] == d]
        L.append("| %s | %s | %s | %s | %.0f / %.0f |" % (d, fm(S1[k]), fm(B[k]), fm(M[k]), np.nanmean([U[i]["cost_method"] for i in k]),
                                                       np.nanmean([U[i]["cost_best4"] for i in k])))
    L += ["| **all** | %s | %s | %s | %.0f / %.0f |" % (fm(S1), fm(B), fm(M), np.nanmean([u["cost_method"] for u in U]),
                                                      np.nanmean([u["cost_best4"] for u in U])), "",
          "Wall-clock = tool runs + selection f1 runs (one of each for the method, four of each for the comparator), measured "
          "while jobs shared GPUs; the fresh-seed endpoint runs belong to neither arm.", "",
          "Failures (+inf, by name): %s." % ("; ".join(fails) if fails else "none"), "", "Sources: %s." % ", ".join(srcs), ""]
    Path(a.out).write_text("\n".join(L) + "\n")
    print(json.dumps(res))


if __name__ == "__main__":
    main()
