#!/usr/bin/env python3
"""The confirmatory test of reports/relink_preregistration.md: relinking two tool runs vs the tool's best of four.

  python scripts/relink_confirm.py reserve      # once, before any ISPD2005 run of the protocol (alpha-ledger RL#1)
  python scripts/relink_confirm.py analyze      # once, after every rlc_* job is fetched to runs/remote/

`analyze` reads, per design, the relink rows (scripts/relink_eval.py: relink pick and the tool's best of 2, 3, 4, each
judged by the median J over fresh f1 seeds; +inf candidates for failures) and the tool-run rows (scripts/tool_runs.py:
wall-clock) of the confirmatory jobs (one source per design), builds the 64 paired units (design, tool seed), runs the
paired one-sided Wilcoxon relink < best of 4 (heurbridge.stats.paired.wilcoxon_less, +inf kept), records the result
under RL#1 and writes reports/relink_confirmatory.md.
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

DESIGNS = ("adaptec1", "adaptec2", "adaptec3", "adaptec4", "bigblue1", "bigblue2", "bigblue3", "bigblue4")
SEEDS = 8
META = {"family": "ispd2005", "designs": list(DESIGNS), "tool_seeds": list(range(SEEDS)), "select_seed": 0,
        "eval_seeds": [1, 2, 3], "endpoint": "median J over fresh f1 seeds", "relink_alphas": [0.25, 0.5, 0.75],
        "comparator": "best of 4 tool seeds (s..s+3 mod 8) by the selection seed", "units": 64,
        "preregistration": "reports/relink_preregistration.md"}


def jl(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


ARMS = ("tool", "best2", "best3", "best4", "relink")


def units(remote: Path, prefix: str) -> tuple:
    """64 units (design, tool seed) from the relink rows of the confirmatory jobs (one source per design), with costs."""
    out, fails, srcs = [], [], []
    for d in DESIGNS:
        rf = sorted(glob.glob(str(remote / (prefix + "*") / "runs" / "relink" / d / "rows.jsonl")))
        tf = sorted(glob.glob(str(remote / (prefix + "*") / "runs" / "tool_runs" / d / "rows.jsonl")))
        if len(rf) > 1 or len(tf) > 1:
            sys.exit("%s: more than one source (%s); the protocol has one run per design" % (d, rf + tf))
        rows = {r["tool_seed"]: r for r in jl(rf[0])} if rf else {}
        trs = {r["tool_seed"]: r for r in jl(tf[0])} if tf else {}
        srcs += [str(Path(f).relative_to(ROOT)) if Path(f).is_relative_to(ROOT) else f for f in rf + tf]
        c = {s: trs[s].get("cost_s", {}).get("tool", trs[s].get("tool_s", 0.0)) + trs[s].get("cost_s", {}).get("f1", 0.0)
             for s in trs}
        for s in range(SEEDS):
            r = rows.get(s)
            if r is None:
                fails.append("%s seed %d: no relink row (job missing or incomplete)" % (d, s))
                out.append(dict({"design": d, "seed": s, "cost_relink": math.nan, "cost_best4": math.nan},
                                **{k: math.inf for k in ARMS}))
                continue
            fails += ["%s seed %d: %s" % (d, s, w) for w in r.get("failures", [])]
            p = r["partner_seed"]
            out.append(dict({"design": d, "seed": s,
                             "cost_relink": c.get(s, math.nan) + c.get(p, math.nan) + r["cost_s"]["relink_extra"],
                             "cost_best4": sum(c.get((s + i) % SEEDS, math.nan) for i in range(4))},
                            **{k: r["J_eval"][k] for k in ARMS}))
    return out, sorted(set(fails)), srcs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["reserve", "analyze"])
    ap.add_argument("--ledger", default=str(ROOT / "stats" / "alpha_ledger.jsonl"))
    ap.add_argument("--remote", default=str(ROOT / "runs" / "remote"))
    ap.add_argument("--prefix", default="rlc_", help="job-name prefix of the confirmatory jobs under --remote")
    ap.add_argument("--out", default=str(ROOT / "reports" / "relink_confirmatory.md"))
    a = ap.parse_args()
    led = AlphaLedger(a.ledger, campaign="RL")
    es = led._entries()
    if a.cmd == "reserve":
        if any(e.get("event") == "reserve" for e in es):
            sys.exit("RL already has a reservation: %s" % sorted({e["ledger_id"] for e in es}))
        print(json.dumps(led.reserve("method_vs_tool", "relink two tool runs vs the tool's best of 4 @ISPD2005",
                                     "wilcoxon_less", meta=META)))
        return
    entry = next(e for e in es if e.get("event") == "reserve" and e["ledger_id"] == "RL#1")
    if any(e.get("event") == "result" and e["ledger_id"] == "RL#1" for e in es):
        sys.exit("RL#1 already has a recorded result; the test runs once")
    U, fails, srcs = units(Path(a.remote), a.prefix)
    A = {k: np.array([u[k] for u in U], float) for k in ARMS}
    t = wilcoxon_less(A["relink"], A["best4"])
    res = led.record(entry, p_value=t["p"], n=len(U), extra={"median_diff": t["median_diff"], "frac_better": t["frac_better"],
                                                              "n_nonzero": t["n_nonzero"], "failures": fails})
    fin = np.isfinite(A["relink"])
    rng = np.random.default_rng(0)
    r = A["relink"][fin]
    boot = np.array([rng.choice(r, len(r)).mean() for _ in range(10000)]) if len(r) else np.array([math.nan])
    m = lambda v: "%.4f" % np.mean(v) if np.all(np.isfinite(v)) else "+inf (%d of %d)" % ((~np.isfinite(v)).sum(), len(v))
    L = ["# Relinking two tool runs vs the tool's best of four: confirmatory result (Track A, ISPD2005)", "",
         "| Field | Value |", "|---|---|", "| Report | relink_confirmatory |", "| Date | %s |" % time.strftime("%Y-%m-%d %H:%M"),
         "| Pre-registration | reports/relink_preregistration.md |",
         "| alpha-ledger | %s, alpha_1 = %.4g, reserved %s, result recorded %s |" % (entry["ledger_id"], entry["alpha_j"],
                                                                                   entry["time"], res["time"]),
         "| Status of the claim | **pre-registered confirmatory test: %s** |" % ("PASSED" if res["promoted"] else "FAILED"), "",
         "## Primary test", "",
         "Paired one-sided Wilcoxon signed-rank on %d units (design, tool seed), relink lower than best of 4, +inf kept: "
         "p = %.3g against alpha_1 = %.4g; median difference %+.4f; relink lower in %d units, equal in %d, higher in %d." % (
             len(U), t["p"], entry["alpha_j"], t["median_diff"], int((A["relink"] < A["best4"]).sum()),
             int((A["relink"] == A["best4"]).sum()), int((A["relink"] > A["best4"]).sum())), "",
         "## Per design (reported, not tested; mean of the fresh-seed medians over the 8 tool seeds)", "",
         "| design | single tool run | best of 2 | best of 3 | best of 4 | relink | wall-clock s: relink / best of 4 |",
         "|---|---|---|---|---|---|---|"]
    for d in DESIGNS:
        sel = [k for k, u in enumerate(U) if u["design"] == d]
        cr, c4 = np.mean([U[k]["cost_relink"] for k in sel]), np.mean([U[k]["cost_best4"] for k in sel])
        L.append("| %s | %s | %.0f / %.0f |" % (d, " | ".join(m(A[k][sel]) for k in ARMS), cr, c4))
    cr, c4 = np.nanmean([u["cost_relink"] for u in U]), np.nanmean([u["cost_best4"] for u in U])
    L += ["| **all** | %s | %.0f / %.0f |" % (" | ".join(m(A[k]) for k in ARMS), cr, c4), "",
          "Mean J of the relink arm over its %d finite units: %.4f, bootstrap 95 %% interval %.4f-%.4f (reported, not tested; "
          "0.45 is the tool's own seed-0 layout by construction). Wall-clock = tool runs + selection f1 runs (+ the relink "
          "candidates' P_M and f1 runs); the fresh-seed endpoint runs are not part of either arm's cost." % (
              len(r), r.mean() if len(r) else math.nan, np.percentile(boot, 2.5), np.percentile(boot, 97.5)), "",
          "Failures (+inf candidates, by name): %s." % ("; ".join(fails) if fails else "none"), "",
          "Sources: %s." % ", ".join(srcs), ""]
    Path(a.out).write_text("\n".join(L) + "\n")
    print(json.dumps(res))


if __name__ == "__main__":
    main()
