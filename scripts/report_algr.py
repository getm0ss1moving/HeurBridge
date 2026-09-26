#!/usr/bin/env python3
"""Algorithm R report (T3.7 / T3 exit): reports/T3_algorithmR*.md from <out>/algorithm_r.json + meta.json.

  python scripts/report_algr.py --run checkpoints/algR_dev --out reports/T3_algorithmR_dev.md --dev
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heurbridge import reporting  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dev", action="store_true")
    ap.add_argument("--caveat", default="")
    a = ap.parse_args()
    run = Path(a.run)
    hist = json.loads((run / "algorithm_r.json").read_text())
    meta = json.loads((run / "meta.json").read_text())
    cfg = meta.get("config", {})
    rows = ["| round | checkpoint | mean J (candidate) | mean J (incumbent) | one-sided p | alpha_j | promoted | ledger |",
            "|---|---|---|---|---|---|---|---|"]
    for h in hist:
        rows.append("| %d | %s | %.4f | %.4f | %.3g | %.4g | %s | %s |" % (
            h["round"], h["ckpt"], h["mean_J_candidate"], h["mean_J_incumbent"], h["p"], h["alpha_j"], h["promoted"],
            h["ledger_id"]))
    mmd = hist[-1].get("mmd2_train_vs_val_cards") if hist else None
    mmdb = hist[-1].get("mmd2_biased_train_vs_val_cards") if hist else None
    res = ("> **Caveat.** %s\n\n" % a.caveat if a.caveat else "") + "\n".join(rows) + (
        "\n\nRound 0's incumbent is the raw heuristic (the T3 exit test: post-guard f1 cost < raw, paired); round r > 0 "
        "compares the round-r bridge with the promoted incumbent, both guarded. Stop rule: improvement < 0.5%% of J "
        "or a failed promotion. MMD^2 between training and validation design state cards: %s." % (
            ("unbiased %s, biased %.4f" % ("n/a (fewer than 2 designs on a side)" if mmd is None else "%.4f" % mmd, mmdb))
            if mmdb is not None else
            "not valid in this run (%s came from the estimator fixed in 0.10.6: with one validation design the unbiased "
            "statistic is undefined)" % mmd))
    reporting.render({
        "title": "Algorithm R (T3.7) — macro-stage bridge rounds%s" % (" (development)" if a.dev else ""),
        "report_id": run.name, "node": "local (macOS, CPU)", "track": "A-dev (HB-GP stand-in f1, single-threaded)",
        "tools": "HeurBridge %s" % meta.get("heurbridge_version"),
        "gate": "T3 exit (round 0: post-guard f1 < raw on validation, paired p < 0.05) and V5 promotion per round",
        "test": "paired one-sided Wilcoxon at the ledger's alpha_j (reserved before the round's costs are computed)",
        "samples": "validation designs %s, %s sources per design; training designs %s" % (
            cfg.get("val"), cfg.get("val_sources"), cfg.get("train")),
        "failures": "none" if all(h["mean_J_candidate"] == h["mean_J_candidate"] for h in hist) else "see algorithm_r.json",
        "commands": "python scripts/algorithm_r.py " + " ".join("--%s %s" % (k.replace("_", "-"), v) for k, v in cfg.items()
                                                                if v not in ("", None, False)),
        "results": res, "alpha_ledger_id": ", ".join(h["ledger_id"] for h in hist),
        "notes": "Per-round pairs and checkpoints under %s (not in the repository)." % run},
        gate_passed=None if a.dev else bool(hist and hist[0]["promoted"]), out=a.out)
    print("REPORT_OK", a.out)


if __name__ == "__main__":
    main()
