#!/usr/bin/env python3
"""The T5 demo's decision rule (reports/t5_demo_preregistration.md, Section 5), applied mechanically.

  R1 validity     share of the HB arm's child attempts that were certified and evaluated with every D_evo cost finite
                  >= 0.5 (attempts = generations x parents x children of its config)
  R2 progress     the HB final portfolio's mean post-bridge J on D_evo < the seed portfolio's
  R3 transfer     on V: HB portfolio mean J < seed portfolio mean J, and HB lower on >= 4 of the 6 units
  R4 LLM value    on V: HB portfolio mean J < CTRL portfolio mean J
  R5 cost/safety  LLM calls of the HB arm <= its budget x 1.1; every failed child evaluation carries a named reason

  python scripts/t5_demo_decision.py --hb runs/evo/t5demo_hb --ctrl runs/evo/t5demo_ctrl --val runs/evo/t5demo_V \
      [--ledger logs/llm_ledger.jsonl] --out runs/evo/t5demo_decision.json
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def rules(hb: Path, ctrl: Path, val: Path, ledger: Path | None, units_needed: int = 4) -> dict:
    from eval_t5_portfolio import BIG, population_files, portfolio
    meta = json.loads((hb / "meta.json").read_text())
    cfg = meta.get("config") or {}
    attempts = int(cfg.get("generations", 0)) * int(cfg.get("parents", 0)) * int(cfg.get("children", 0))
    last = json.loads(population_files(hb)[-1].read_text())
    first = json.loads((hb / "population_g0.json").read_text())
    kids = [r for i, r in last["programs"].items() if "@i" not in i and int(r.get("generation") or 0) >= 1]
    ok = [r for r in kids if r.get("B") and np.isfinite(np.asarray(r["B"], float)).all()]
    out = {"R1": {"evaluated_ok": len(ok), "attempts": attempts,
                  "share": len(ok) / attempts if attempts else 0.0}}
    out["R1"]["pass"] = attempts > 0 and out["R1"]["share"] >= 0.5

    def mean_B(pop, ids):
        B = np.array([pop["programs"][i]["B"] for i, _ in ids], float)
        return float(np.where(np.isfinite(B), B, BIG).min(0).mean())       # portfolio J per design, then the mean
    q = int(cfg.get("q", 8)) if "q" in cfg else 8
    out["R2"] = {"hb_final": mean_B(last, portfolio(last, q)), "seed": mean_B(first, portfolio(first, q))}
    out["R2"]["pass"] = out["R2"]["hb_final"] < out["R2"]["seed"]
    s = json.loads((val / "summary.json").read_text())
    pd = s["per_design"]
    hb_name, ctrl_name = hb.name, ctrl.name
    u_hb = np.concatenate([pd[hb_name][d] for d in s["designs"]])
    u_seed = np.concatenate([pd["seed"][d] for d in s["designs"]])
    lower = int((u_hb < u_seed).sum())
    out["R3"] = {"hb_mean": s["mean_J"][hb_name], "seed_mean": s["mean_J"]["seed"], "units_lower": lower,
                 "units": int(len(u_hb))}
    out["R3"]["pass"] = out["R3"]["hb_mean"] < out["R3"]["seed_mean"] and lower >= units_needed
    out["R4"] = {"hb_mean": s["mean_J"][hb_name], "ctrl_mean": s["mean_J"].get(ctrl_name)}
    out["R4"]["pass"] = out["R4"]["ctrl_mean"] is not None and out["R4"]["hb_mean"] < out["R4"]["ctrl_mean"]
    calls = None
    if ledger and ledger.exists():
        scope = "M/%s" % cfg.get("split")
        calls = sum(1 for line in ledger.read_text().splitlines()
                    if line.strip() and json.loads(line).get("budget_scope") == scope and json.loads(line).get("status") == "ok")
    events = [json.loads(line) for line in (hb / "events.jsonl").read_text().splitlines() if line.strip()]
    unnamed = [e["id"] for e in events if e.get("kind") in ("rejected_sandbox", "discarded_malformed", "propose_error")
               and not (e.get("reasons") or e.get("error"))]
    budget = int(cfg.get("budget", 0))
    out["R5"] = {"llm_calls": calls, "budget": budget, "unnamed_failures": unnamed}
    out["R5"]["pass"] = (calls is not None and calls <= budget * 1.1) and not unnamed
    out["propose_full_campaign"] = all(out[k]["pass"] for k in ("R1", "R2", "R3", "R4", "R5"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hb", required=True)
    ap.add_argument("--ctrl", required=True)
    ap.add_argument("--val", required=True)
    ap.add_argument("--ledger", default=str(ROOT / "logs" / "llm_ledger.jsonl"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = rules(Path(a.hb), Path(a.ctrl), Path(a.val), Path(a.ledger) if a.ledger else None)
    Path(a.out).write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
