#!/usr/bin/env python3
"""Algorithm R for the macro stage (task T3.7): on-policy rounds with DAgger aggregation and promotion gate.

  python scripts/algorithm_r.py --train ibm01,ibm02 --val ibm03 --rounds 3 --archive archive_dev_v2 \
      --out checkpoints/algR_dev --steps 2000 --final hbgp

round r = 0 .. R_max:
  1. (macro stage: no upstream to freeze)
  2. sources  <- population programs x seeds on each training design (cached)
  3. labels   <- archive top-k per design
  4. pairs    <- aggregate rounds 0..r (DAgger), cap 4,000 per design, newest first
  5. train    <- fine-tune from round r-1 (lr 1e-4) or from --pretrained / scratch in round 0
  6. validate <- T3.6 criteria + MMD^2 between training and deployment conditions (design state cards)
  7. promote  <- V5 gate: post-guard final cost (f1) of the new bridge vs the incumbent (round 0: the raw
                 heuristic) on held-out designs, paired one-sided Wilcoxon at the ledger's alpha_j
  stop if the improvement over round r-1 < 0.5% of J, or r = R_max
The round-0 test is the T3 exit gate (post-guard f1 < raw on validation, paired).
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heurbridge.bridge.data import PairSet  # noqa: E402
from heurbridge.bridge.sample import refine  # noqa: E402
from heurbridge.bridge.train import load_bridge  # noqa: E402
from heurbridge.core import project  # noqa: E402
from heurbridge.eval import cost  # noqa: E402
from heurbridge.heuristics.macro.registry import all_programs  # noqa: E402
from heurbridge.meta import write_meta  # noqa: E402
from heurbridge.online.solve import state_card  # noqa: E402
from heurbridge.pipeline import bridge_data as BD  # noqa: E402
from heurbridge.pipeline.evaluators import HBGPEvaluator  # noqa: E402
from heurbridge.stats.alpha_ledger import AlphaLedger  # noqa: E402
from heurbridge.stats.paired import mmd2  # noqa: E402
from heurbridge.verify.gates import promote  # noqa: E402
from train_bridge import load_bundle  # noqa: E402

CARD_KEYS = ("objects", "macros", "nets", "avg_degree", "utilization", "macro_area_ratio", "aspect", "pin_density")


def card_vec(b):
    c = state_card(b.design, b.base)
    return np.array([np.log1p(c[k]) if k in ("objects", "macros", "nets") else c[k] for k in CARD_KEYS], float)


def final_costs(bundle, layouts, runs):
    """Final (f1) cost of each layout on its design (HB-GP stand-in), J vs the design's dev baseline."""
    base = json.loads((Path(runs) / bundle.design.id / "baseline.json").read_text())["records"]
    for r in base:
        r.setdefault("rudy_of_pct", 100.0 * r.get("rudy_overflow_ratio", 0.0))
    ev = HBGPEvaluator()
    bl = cost.Baseline.from_records(bundle.design.id, base)
    out = []
    for k, l in enumerate(layouts):
        try:
            out.append(ev.score(ev.evaluate(bundle.design, l, "algR.%d" % k, Path(runs)), bl).J_inf)
        except Exception:
            out.append(float("inf"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--train", required=True)
    ap.add_argument("--val", required=True)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--archive", default=str(ROOT / "archive_dev_v2"))
    ap.add_argument("--runs", default=str(ROOT / "runs" / "seed_dev"))
    ap.add_argument("--out", default=str(ROOT / "checkpoints" / "algR_dev"))
    ap.add_argument("--steps", type=int, default=2000)
    ap.add_argument("--val-sources", type=int, default=32)
    ap.add_argument("--pretrained", default="")
    ap.add_argument("--campaign", default="algR_dev")
    ap.add_argument("--device", default="cpu")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ledger = AlphaLedger(ROOT / "stats" / "alpha_ledger.jsonl", campaign=a.campaign)
    prev_ckpt, prev_J, history = a.pretrained, None, []
    val_b = [load_bundle(a.suite, n, a.runs) for n in a.val.split(",")]
    tr_b = [load_bundle(a.suite, n, a.runs) for n in a.train.split(",")]
    mm = mmd2(np.stack([card_vec(b) for b in tr_b]), np.stack([card_vec(b) for b in val_b]))
    progs = all_programs()
    for r in range(a.rounds + 1):
        rdir = out / ("round%d" % r)
        cmd = [sys.executable, str(ROOT / "scripts" / "train_bridge.py"), "--suite", a.suite, "--train", a.train, "--val", a.val,
               "--archive", a.archive, "--runs", a.runs, "--out", str(rdir), "--steps", str(a.steps), "--round", str(r),
               "--device", a.device, "--lr", "1e-4" if prev_ckpt else "2e-4"]
        if prev_ckpt:
            cmd += ["--pretrained", prev_ckpt]
        subprocess.run(cmd, check=True)
        # DAgger: aggregate this round's pairs with earlier rounds (cap 4,000 per design, newest first)
        for p in (rdir / "pairs" / ("round%d" % r)).glob("*.pt"):
            agg = PairSet.load(p)
            for q in range(r - 1, -1, -1):
                old = out / ("round%d" % q) / "pairs" / ("round%d" % q) / p.name
                if old.exists():
                    agg = PairSet.load(old).extend(agg)
            agg.cap(4000).save(out / "dagger" / p.name, r)
        ckpt = rdir / "best.pt"
        model = load_bridge(ckpt)
        inc_model = load_bridge(prev_ckpt) if (prev_ckpt and r > 0) else None
        cand, inc = [], []
        for b in val_b:
            srcs = BD.run_sources(b, progs, 8, cache=rdir / "cache")
            pick = np.random.default_rng(0).choice(len(srcs), size=min(a.val_sources, len(srcs)), replace=False)
            lays = [srcs[i][2] for i in sorted(pick)]
            new = [x.layout for x in refine(model, b.graph, b.design, lays, b.scorer)]
            old = [x.layout for x in refine(inc_model, b.graph, b.design, lays, b.scorer)] if inc_model else lays
            cand += final_costs(b, new, a.runs)
            inc += final_costs(b, old, a.runs)
        rec = promote(ledger, "bridge_round", "%s#r%d" % (out.name, r), cand, inc,
                      meta={"round": r, "incumbent": prev_ckpt or "raw heuristic", "val": a.val})
        Jc, Ji = float(np.mean([c for c in cand if np.isfinite(c)])), float(np.mean([c for c in inc if np.isfinite(c)]))
        row = {"round": r, "ckpt": str(ckpt), "mean_J_candidate": Jc, "mean_J_incumbent": Ji, "promoted": rec["promoted"],
               "p": rec["p"], "alpha_j": rec["alpha_j"], "ledger_id": rec["ledger_id"], "mmd2_train_vs_val_cards": mm["mmd2"]}
        history.append(row)
        print(json.dumps(row), flush=True)
        if rec["promoted"]:
            gain = (prev_J - Jc) / prev_J if prev_J else None
            prev_ckpt, prev_J = str(ckpt), Jc
            if gain is not None and gain < 0.005:
                break
        elif r > 0:
            break
    (out / "algorithm_r.json").write_text(json.dumps(history, indent=1))
    write_meta(out, "algR_%s" % out.name, a.train, config=vars(a), bridge_ckpt_hash=None,
               promoted_ckpt=prev_ckpt, history=history)


if __name__ == "__main__":
    main()
