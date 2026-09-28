#!/usr/bin/env python3
"""Combine several run_e0.py outputs (e.g. one run per design) into one analysis directory for report_e0.py.

  python scripts/e0_combine.py --runs runs/remote/e0demo_spec_ibm04/runs/e0_demo/spec_ibm04 \
      runs/remote/e0demo_spec_ibm06/runs/e0_demo/spec_ibm06 --out runs/e0_demo_spec

The statistics are recomputed over all rows (run_e0.summarize).  The runs must share the protocol (guard fidelity,
equal guard, final cost, bridge checkpoint).  Without --ledger-entry nothing is written to the alpha ledger (a demo,
or runs that recorded their own entries).  With --ledger-entry E0#1 the runs are components (run_e0.py --component)
of a test pre-registered by e0_preregister.py: the entry must be reserved and still open, the combined designs and
protocol must equal the ones registered in it, and the pooled result is recorded into it.
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

PROTOCOL = ("guard_fidelity", "equal_guard", "random_control", "final", "bridge_sha256_16", "frozen", "K", "suite",
            "seeds")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ledger-entry", default="", help="pre-registered entry to record the pooled result into")
    ap.add_argument("--ledger", default=str(ROOT / "stats" / "alpha_ledger.jsonl"))
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
    if a.ledger_entry:
        meta["alpha_ledger_id"] = a.ledger_entry
        meta["ledger_result"] = record(a.ledger_entry, cfg, res, a.ledger)
    (out / "meta.json").write_text(json.dumps(meta, indent=1, default=str))
    print(json.dumps({"combined": len(a.runs), "rows": len(rows), "n_cases": res["n_cases"],
                      "gate_G0prime": res["gate_G0prime"]}, default=str))


def record(ledger_id: str, cfg: dict, res: dict, ledger_path) -> dict:
    """Record the pooled G0' result into its pre-registered, still-open entry after checking the protocol."""
    from heurbridge.stats.alpha_ledger import AlphaLedger
    campaign = ledger_id.split("#")[0]
    led = AlphaLedger(ledger_path, campaign=campaign)
    es = led._entries()
    entry = next((e for e in es if e.get("event") == "reserve" and e["ledger_id"] == ledger_id), None)
    if entry is None:
        sys.exit("ledger entry %s was not reserved" % ledger_id)
    if any(e.get("event") == "result" and e["ledger_id"] == ledger_id for e in es):
        sys.exit("ledger entry %s is already closed" % ledger_id)
    reg = entry["meta"]
    got = {"designs": sorted(cfg["designs"].split(",")), "guard_fidelity": cfg.get("guard_fidelity"),
           "equal_guard": bool(cfg.get("equal_guard")), "final": cfg.get("final"), "seeds": cfg.get("seeds"),
           "bridge_sha256_16": cfg.get("bridge_sha256_16")}
    for k, v in got.items():
        if k in reg and reg[k] != v:
            sys.exit("protocol mismatch for %s: registered %r, runs %r" % (k, reg[k], v))
    g = res["gate_G0prime"]
    return led.record(entry, p_value=max(g["p_memetic"], g["p_repertoire"]), n=res["n_cases"],
                      extra={"gate": "G0prime", **g, "holm": res.get("holm"), "controls": res.get("controls")})


if __name__ == "__main__":
    main()
