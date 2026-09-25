#!/usr/bin/env python3
"""T3 exit report: reports/T3_bridge_macro*.md from a training run's history.json (+ PNG curves).

  python scripts/report_bridge.py --run checkpoints/bridge_dev_r0 --out reports/T3_bridge_macro_dev.md --dev
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
    ap.add_argument("--dev", action="store_true", help="development run: descriptive, no gate claim")
    ap.add_argument("--node", default="local (macOS, CPU)")
    ap.add_argument("--track", default="A-dev (HB-GP stand-in f1; f0 guard)")
    a = ap.parse_args()
    run = Path(a.run)
    h = json.loads((run / "history.json").read_text())
    meta = json.loads((run / "meta.json").read_text())
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    steps = h["steps"]
    fig, axs = plt.subplots(1, 4, figsize=(16, 3.4))
    series = [("train loss", [t["loss"] for t in h["train"]]), ("velocity residual", [v.get("residual") for v in h["val"]]),
              ("terminal error", [v.get("terminal") for v in h["val"]]),
              ("guarded post-projection f0 (criterion)", [v.get("criterion") for v in h["val"]])]
    for ax, (name, ys) in zip(axs, series):
        ax.plot(steps, ys, "o-")
        ax.set_title(name, fontsize=9)
        ax.set_xlabel("step")
    if h["val"] and "raw_f0" in h["val"][-1]:
        axs[3].axhline(h["val"][-1]["raw_f0"], color="gray", ls="--", label="raw heuristic")
        axs[3].legend(fontsize=8)
    fig.tight_layout()
    png = Path(a.out).with_suffix(".png")
    png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png, dpi=110)
    plt.close(fig)
    last = h["val"][-1] if h["val"] else {}
    rows = "\n".join("| %d | %.5f | %s | %s | %s | %s | %s |" % (
        s, t["loss"], "%.5f" % v.get("residual", float("nan")), "%.5f" % v.get("terminal", float("nan")),
        "%.5f" % v.get("criterion", float("nan")), "%.5f" % v.get("raw_f0", float("nan")), v.get("alpha_hist", {}))
        for s, t, v in zip(steps, h["train"], h["val"]))
    res = ("![curves](%s)\n\n| step | train loss | velocity residual | terminal error | guarded f0 | raw f0 | alpha histogram |\n"
           "|---|---|---|---|---|---|---|\n%s\n\nShare of validation sources improved by the guard at the last validation: %s.\n"
           "MMD per round: single round (round 0; the macro stage has no upstream)."
           % (png.name, rows, last.get("improved_frac")))
    cfg = meta.get("config", {})
    text = reporting.render({
        "title": "T3 macro-stage bridge — validation report%s" % (" (development)" if a.dev else ""),
        "report_id": run.name, "node": a.node, "track": a.track,
        "tools": "torch %s; HeurBridge %s" % (__import__("torch").__version__, meta.get("heurbridge_version")),
        "gate": "T3 exit (post-guard f1 cost < raw on validation, paired p < 0.05)" + (" — NOT evaluated in a development run" if a.dev else ""),
        "samples": "train designs %s; validation design(s) %s; pairs: see train.log; seeds %s" % (cfg.get("train"), cfg.get("val"), cfg.get("seeds")),
        "failures": "none recorded in train.log" if "Traceback" not in (run / "train.log").read_text() else "see train.log",
        "commands": "python scripts/train_bridge.py " + " ".join("--%s %s" % (k.replace("_", "-"), v) for k, v in cfg.items() if v not in ("", None)),
        "results": res, "alpha_ledger_id": meta.get("alpha_ledger_id") or "-",
        "notes": "bridge checkpoint sha256 %s; archive snapshot %s" % (meta.get("bridge_ckpt_hash"), meta.get("archive_snapshot"))},
        gate_passed=None if a.dev else False, out=a.out)
    print("REPORT_OK", a.out)


if __name__ == "__main__":
    main()
