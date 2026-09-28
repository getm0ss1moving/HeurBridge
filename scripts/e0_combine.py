#!/usr/bin/env python3
"""Combine several run_e0.py outputs (e.g. one run per design) into one analysis directory for report_e0.py.

  python scripts/e0_combine.py --runs runs/remote/e0demo_spec_ibm04/runs/e0_demo/spec_ibm04 \
      runs/remote/e0demo_spec_ibm06/runs/e0_demo/spec_ibm06 --out runs/e0_demo_spec

The statistics are recomputed over all rows (run_e0.summarize); nothing is written to the alpha ledger (each
source run already reserved and recorded its own entry, listed in the combined meta.json).  The runs must share the
protocol (guard fidelity, equal guard, final cost, bridge checkpoint).
"""

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from run_e0 import summarize  # noqa: E402

PROTOCOL = ("guard_fidelity", "equal_guard", "random_control", "final", "bridge", "frozen", "K", "suite")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows, metas = [], []
    for r in a.runs:
        rows += [json.loads(l) for l in (Path(r) / "e0_rows.jsonl").read_text().splitlines() if l.strip()]
        metas.append(json.loads((Path(r) / "meta.json").read_text()))
    cfgs = [m.get("config", {}) for m in metas]
    for k in PROTOCOL:
        vals = {json.dumps(c.get(k)) for c in cfgs}
        if len(vals) > 1:
            sys.exit("runs differ in %s: %s" % (k, sorted(vals)))
    cfg = dict(cfgs[0])
    cfg["designs"] = ",".join(sorted({d for c in cfgs for d in str(c.get("designs", "")).split(",") if d}))
    res = summarize(rows, SimpleNamespace(**cfg))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "e0_rows.jsonl").write_text("".join(json.dumps(r, default=str) + "\n" for r in rows))
    (out / "e0_summary.json").write_text(json.dumps(res, indent=1, default=str))
    meta = {"heurbridge_version": metas[0].get("heurbridge_version"), "git_sha": metas[0].get("git_sha"),
            "code_archive": metas[0].get("code_archive"), "config": cfg, "combined_from": [str(r) for r in a.runs],
            "alpha_ledger_id": ", ".join(str(m.get("alpha_ledger_id")) for m in metas)}
    (out / "meta.json").write_text(json.dumps(meta, indent=1, default=str))
    print(json.dumps({"combined": len(a.runs), "rows": len(rows), "n_cases": res["n_cases"],
                      "gate_G0prime": res["gate_G0prime"]}, default=str))


if __name__ == "__main__":
    main()
