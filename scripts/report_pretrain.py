#!/usr/bin/env python3
"""T3.4 pretraining report: reports/T3_pretrain_<model>.md from a pretrain_bridge.py output directory.

  python scripts/report_pretrain.py --dir runs/remote/pretrain_small/checkpoints/pretrain_small
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
    ap.add_argument("--dir", required=True)
    ap.add_argument("--node", default="225 (RTX 3090, GPU 0)")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    d = Path(a.dir)
    meta = json.loads((d / "meta.json").read_text())
    done = json.loads((d / "pretrain_done.json").read_text())
    rows = [json.loads(l) for l in (d / "pretrain.log").read_text().splitlines()]
    cfg = meta.get("config") or {}
    pick = [r for r in rows if r["step"] % 20000 == 0 or r["step"] in (500, rows[-1]["step"])]
    switch = next((r["step"] for r in rows if r["stage"] == 2), None)
    table = ["| step | stage | loss | flow-matching term | overlap term | elapsed h |", "|---|---|---|---|---|---|"]
    table += ["| %d | %d | %.4f | %.4f | %.4f | %.2f |" % (r["step"], r["stage"], r["loss"], r["fm"], r["ov"],
                                                          r["elapsed_s"] / 3600) for r in pick]
    s1 = [r for r in rows if r["stage"] == 1]
    s2 = [r for r in rows if r["stage"] == 2]
    rate = lambda rr: (rr[-1]["elapsed_s"] - rr[0]["elapsed_s"]) / max(1, rr[-1]["step"] - rr[0]["step"]) if len(rr) > 1 else float("nan")
    name = d.name
    out = a.out or str(ROOT / "reports" / ("T3_%s.md" % name))
    reporting.render({
        "title": "T3.4 pretraining (warm start): %s" % name, "report_id": "T3_%s" % name, "node": "%s; %s" % (
            a.node, meta.get("host") or "?"),
        "track": "Track-independent (synthetic circuits, heurbridge.core.synth)",
        "tools": "PyTorch 2.6.0+cu118, bf16 autocast", "version": meta.get("heurbridge_version", "?"),
        "git_sha": (meta.get("git_sha") or "unknown") + (" (%s)" % meta["code_archive"] if meta.get("code_archive") else ""),
        "gate": "T3.4 (warm start for T3.7); no gate", "samples": "%d steps x batch %d; stage 1: %s circuits (objects); "
        "stage 2: %s from step %s" % (cfg.get("steps", 0), cfg.get("batch", 0), cfg.get("stage1"), cfg.get("stage2"), switch),
        "failures": "none",
        "commands": "python scripts/pretrain_bridge.py " + " ".join(
            "--%s %s" % (k.replace("_", "-"), v) for k, v in cfg.items() if v is not None and v != "" and v is not False),
        "results": "\n".join(["Checkpoint `%s/pretrain_%s.pt`, sha256 `%s` (%d steps)." % (
            name, cfg.get("model", "small"), done.get("sha256"), done.get("steps", 0)), "",
            "Throughput: %.3f s/step in stage 1, %.3f s/step in stage 2; total %.2f h." % (
                rate(s1), rate(s2), rows[-1]["elapsed_s"] / 3600), "", "\n".join(table)]),
        "notes": "Loss = flow-matching (area-weighted velocity residual) + 0.1 x overlap penalty of the extrapolated "
                 "endpoint (T3.5, sigma 0.01, logit-normal tau), noise source uniform on the canvas. Values are 500-step "
                 "means of the training loss; there is no validation set for synthetic pretraining (T3.6 validation "
                 "starts with Algorithm R on real designs)."}, gate_passed=None, out=out)
    print("REPORT_OK", out)


if __name__ == "__main__":
    main()
