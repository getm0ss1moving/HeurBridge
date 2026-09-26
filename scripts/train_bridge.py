#!/usr/bin/env python3
"""Macro-stage bridge training, one round of Algorithm R (tasks T3.2, T3.6, T3.7).

  python scripts/train_bridge.py --suite ibm --train ibm01,ibm02 --val ibm03 \
      --archive archive_dev --runs runs/seed_dev --out checkpoints/bridge_dev_r0 --steps 3000 --device cpu

Sources: the seed population x --seeds seeds (sandbox + P_M), on-policy for the macro stage (no upstream).
Labels: the archive's top-5 per design.  Pairs: symmetry-matched nearest elites, weights exp(-(J*-Jmin)/T_J).
Validation criterion (model selection): mean guarded post-projection f0 cost on --val-sources sources per
validation design; also the alpha histogram and the share of sources the guard improves.
Outputs: best.pt (+ sha256), history.json, meta.json, pair shards under <out>/pairs/round<r>/.
"""

import argparse
import collections
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heurbridge.archive.store import Archive  # noqa: E402
from heurbridge.bridge.model import BridgeConfig, BridgeNet  # noqa: E402
from heurbridge.bridge.sample import refine  # noqa: E402
from heurbridge.bridge.train import TrainConfig, Trainer, file_sha256  # noqa: E402
from heurbridge.core import bookshelf, project  # noqa: E402
from heurbridge.heuristics.cell.cluster import cluster_cells  # noqa: E402
from heurbridge.heuristics.macro.registry import all_programs  # noqa: E402
from heurbridge.meta import write_meta  # noqa: E402
from heurbridge.pipeline import bridge_data as BD  # noqa: E402

SUITES = {"ibm": ROOT / "benchmarks" / "ibm_bookshelf", "ispd2005": ROOT / "benchmarks" / "ispd2005"}


def load_bundle(suite, name, runs):
    d, l = bookshelf.load_bookshelf(SUITES[suite] / name / (name + ".aux"), family=suite)
    if suite == "ispd2005":
        d.is_fixed = d.is_fixed & ~d.is_macro
        l.schema = d.schema_hash()
    cpath = Path(runs) / d.id / "clusters.npy"
    cl = np.load(cpath) if cpath.exists() else cluster_cells(d, seed=0)
    base = l.copy()
    base.pos[~d.is_macro & ~d.is_io & ~d.is_fixed] = np.nan
    return BD.make_bundle(d, base, cl)


def guard_evaluator(val, K, log):
    def ev(model, _sets):
        Js, raws, alphas = [], [], []
        for b, srcs in val:
            res = refine(model, b.graph, b.design, [l for _, _, l in srcs], b.scorer, K=K)
            for r in res:
                Js.append(min(r.scores))
                raws.append(r.scores[0])
                alphas.append(r.alpha)
        Js, raws = np.array(Js), np.array(raws)
        out = {"criterion": float(Js.mean()), "raw_f0": float(raws.mean()),
               "improved_frac": float((Js < raws - 1e-9).mean()),
               "alpha_hist": {str(k): v for k, v in sorted(collections.Counter(alphas).items())}}
        log(json.dumps({"val_guard": out}))
        return out
    return ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--train", required=True)
    ap.add_argument("--val", required=True)
    ap.add_argument("--archive", default=str(ROOT / "archive_dev"))
    ap.add_argument("--runs", default=str(ROOT / "runs" / "seed_dev"))
    ap.add_argument("--out", default=str(ROOT / "checkpoints" / "bridge_dev_r0"))
    ap.add_argument("--round", type=int, default=0)
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--val-sources", type=int, default=32)
    ap.add_argument("--model", default="small", choices=["small", "base"])
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--val-every", type=int, default=500)
    ap.add_argument("--lam-ov", type=float, default=0.1)
    ap.add_argument("--sigma", type=float, default=0.01)
    ap.add_argument("--K", type=int, default=20)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--pretrained", default="")
    ap.add_argument("--prior-pairs", default="", help="DAgger: directory of earlier rounds' aggregated pair shards "
                                                      "(<design>.pt), merged before this round's pairs, cap 4,000 newest")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    log_f = open(out / "train.log", "a")

    def log(s):
        print(s, flush=True)
        log_f.write(s + "\n")
        log_f.flush()

    torch.manual_seed(a.seed)
    arch = Archive(a.archive, min_fidelity=1)
    progs = all_programs()
    sets, val = [], []
    for split, names in (("train", a.train), ("val", a.val)):
        for name in names.split(","):
            t0 = time.time()
            b = load_bundle(a.suite, name, a.runs)
            srcs = BD.run_sources(b, progs, a.seeds, cache=out / "cache")
            el = BD.archive_elites(b, arch)
            if not el:
                log(json.dumps({"skip": name, "reason": "no elites in archive"}))
                continue
            ps = BD.build_pairs(b, srcs, el)
            ps.save(out / "pairs" / ("round%d" % a.round) / (b.design.id + ".pt"), a.round)
            log(json.dumps({"design": name, "split": split, "sources": len(srcs), "elites": [e.J for e in el],
                            "pairs": len(ps), "nodes": b.graph.n, "edges": int(b.graph.edge_index.shape[1]),
                            "prep_s": round(time.time() - t0, 1)}))
            if split == "train":
                prior = Path(a.prior_pairs) / (b.design.id + ".pt") if a.prior_pairs else None
                if prior is not None and prior.exists():              # T3.7 step 4: aggregate rounds 0..r
                    n_new = len(ps)
                    ps = BD.PairSet.load(prior).extend(ps).cap(4000)
                    log(json.dumps({"design": name, "dagger_prior": len(ps) - min(n_new, len(ps)), "round_pairs": n_new,
                                    "train_pairs": len(ps)}))
                sets.append(ps)
            else:
                rng = np.random.default_rng(0)
                pick = rng.choice(len(srcs), size=min(a.val_sources, len(srcs)), replace=False)
                val.append((b, [srcs[i] for i in sorted(pick)]))
                sets_val = ps
    cfg_m = BridgeConfig.small() if a.model == "small" else BridgeConfig.base()
    model = BridgeNet(cfg_m)
    if a.pretrained:
        z = torch.load(a.pretrained, map_location="cpu", weights_only=False)
        model.load_state_dict(z["ema"])
    tcfg = TrainConfig(steps=a.steps, batch=a.batch, lr=a.lr, val_every=a.val_every, lam_ov=a.lam_ov, sigma=a.sigma,
                       K=a.K, device=a.device, warmup=min(1000, a.steps // 10), seed=a.seed)
    tr = Trainer(model, tcfg, sets, [p for p in [sets_val]] if val else [], evaluator=guard_evaluator(val, a.K, log),
                 out_dir=out, log=log)
    log(json.dumps({"params": model.n_params(), "train_designs": [s.graph.design_id for s in sets],
                    "pairs": sum(len(s) for s in sets), "device": a.device}))
    res = tr.fit()
    h = tr.save(out / "last.pt", {"result": res})
    best = out / "best.pt"
    write_meta(out, "bridge_%s_r%d" % (a.suite, a.round), a.train, config=vars(a),
               bridge_ckpt_hash=file_sha256(best) if best.exists() else h, seed=a.seed,
               archive_snapshot=arch.snapshot("train_r%d" % a.round), result=res)
    (out / "history.json").write_text(json.dumps({"steps": tr.hist.steps, "train": tr.hist.train, "val": tr.hist.val},
                                                 indent=1, default=str))
    log(json.dumps({"done": res}))


if __name__ == "__main__":
    main()
