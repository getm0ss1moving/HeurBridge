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


_F1 = {}


def guard_f1(bundle, runs):
    """The T3.8 guard at f1 (HB-GP stand-in; deterministic, cached per layout)."""
    def g(lay):
        mm = bundle.design.is_macro & ~bundle.design.is_fixed
        key = (bundle.design.id, lay.pos[mm].tobytes(), lay.orient[mm].tobytes())
        if key not in _F1:
            _F1[key] = final_costs(bundle, [lay], runs)[0]
        return _F1[key]
    return g


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
    ap.add_argument("--round0-dir", default="", help="reuse an existing round-0 training run (best.pt, pairs/round0)")
    ap.add_argument("--guard", default="f1", choices=["f0", "f1"], help="the bridge's guard in the promotion test (T3.8)")
    ap.add_argument("--val-every", type=int, default=0)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ledger = AlphaLedger(ROOT / "stats" / "alpha_ledger.jsonl", campaign=a.campaign)
    prev_ckpt, prev_J, history = a.pretrained, None, []
    val_b = [load_bundle(a.suite, n, a.runs) for n in a.val.split(",")]
    tr_b = [load_bundle(a.suite, n, a.runs) for n in a.train.split(",")]
    mm = mmd2(np.stack([card_vec(b) for b in tr_b]), np.stack([card_vec(b) for b in val_b]))
    progs = all_programs()
    rdirs = []
    for r in range(a.rounds + 1):
        rdir = out / ("round%d" % r)
        if r == 0 and a.round0_dir:
            rdir = Path(a.round0_dir)                    # an existing round-0 run: its checkpoint and pairs
        else:
            cmd = [sys.executable, str(ROOT / "scripts" / "train_bridge.py"), "--suite", a.suite, "--train", a.train,
                   "--val", a.val, "--archive", a.archive, "--runs", a.runs, "--out", str(rdir), "--steps", str(a.steps),
                   "--round", str(r), "--device", a.device, "--lr", "1e-4" if prev_ckpt else "2e-4",
                   "--val-every", str(a.val_every or max(1, a.steps // 5))]
            if prev_ckpt:
                cmd += ["--pretrained", prev_ckpt]
            if rdirs:                                    # DAgger (T3.7 step 4): rounds 0..r-1, newest last, cap 4,000
                prior = out / ("dagger_r%d" % r)
                names = sorted({f.name for q, d in enumerate(rdirs) for f in (d / "pairs" / ("round%d" % q)).glob("*.pt")})
                for n in names:
                    agg = None
                    for q, d in enumerate(rdirs):
                        f = d / "pairs" / ("round%d" % q) / n
                        if f.exists():
                            agg = PairSet.load(f) if agg is None else agg.extend(PairSet.load(f))
                    agg.cap(4000).save(prior / n, r)
                cmd += ["--prior-pairs", str(prior)]
            subprocess.run(cmd, check=True)
        rdirs.append(rdir)
        ckpt = rdir / "best.pt"
        model = load_bridge(ckpt)
        inc_model = load_bridge(prev_ckpt) if (prev_ckpt and r > 0) else None
        cand, inc = [], []
        # V5: the ledger entry is reserved before any cost of this round's test is computed
        entry = ledger.reserve("bridge_round", "%s#r%d" % (out.name, r), "wilcoxon_less_paired",
                               meta={"round": r, "incumbent": prev_ckpt or "raw heuristic", "val": a.val, "guard": a.guard})
        for b in val_b:
            srcs = BD.run_sources(b, progs, 8, cache=out / "cache")
            pick = np.random.default_rng(0).choice(len(srcs), size=min(a.val_sources, len(srcs)), replace=False)
            lays = [srcs[i][2] for i in sorted(pick)]
            g = b.scorer if a.guard == "f0" else guard_f1(b, a.runs)
            new = [x.layout for x in refine(model, b.graph, b.design, lays, g)]
            old = [x.layout for x in refine(inc_model, b.graph, b.design, lays, g)] if inc_model else lays
            cand += final_costs(b, new, a.runs)
            inc += final_costs(b, old, a.runs)
        rec = promote(ledger, "bridge_round", "%s#r%d" % (out.name, r), cand, inc, entry=entry)
        Jc, Ji = float(np.mean([c for c in cand if np.isfinite(c)])), float(np.mean([c for c in inc if np.isfinite(c)]))
        row = {"round": r, "ckpt": str(ckpt), "mean_J_candidate": Jc, "mean_J_incumbent": Ji, "promoted": rec["promoted"],
               "p": rec["p"], "alpha_j": rec["alpha_j"], "ledger_id": rec["ledger_id"],
               "mmd2_train_vs_val_cards": mm["mmd2"] if mm["mmd2"] == mm["mmd2"] else None,
               "mmd2_biased_train_vs_val_cards": mm["mmd2_biased"], "mmd_n_m": [mm["n"], mm["m"]]}
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
