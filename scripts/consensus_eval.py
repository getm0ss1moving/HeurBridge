#!/usr/bin/env python3
"""Consensus of several tool runs against the tool's best of k (Track A; exploratory, IBM only).

Relinking's picks are mostly interpolated layouts, often the midpoint (reports/beat_tool_track_a.md, runs relink_*).
This asks whether the average of k tool layouts, with their interchangeable macros matched (a free-support barycenter),
is better than the tool's best of k without any f1 run to choose.  Input: the tool layouts and rows of
scripts/tool_runs.py or scripts/tool_refine_eval.py (layouts_<design>.npz key "tool", rows.jsonl).  Per k in --ks and
window of k consecutive tool seeds (cyclic, first seed i):
  consensus  P_M(barycenter of the k layouts; every layout re-matched to the running mean --iters times); the
             orientations of the window's first run; cost = k tool runs + matching + P_M (no f1)
  best       the tool's best of the k runs by f1 with the selection seed; cost = k tool runs + k f1 runs
  guard      the best of {consensus, the k runs} by the selection seed; cost = k tool runs + k + 1 f1 runs
Every layout is judged by the median J over fresh f1 seeds; failures are +inf candidates, named per row.

  python scripts/consensus_eval.py --design ibm04 --refine-dir runs/tool_refine3/ibm04 --ks 2,4 --out runs/consensus/ibm04
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heurbridge.core import project  # noqa: E402
from heurbridge.eval import cost  # noqa: E402
from heurbridge.meta import write_meta  # noqa: E402
from heurbridge.pipeline.evaluators import DreamplaceEvaluator  # noqa: E402

INF = float("inf")


def barycenter(g, X: list, iters: int = 2, block: int | None = 2000) -> np.ndarray:
    """Node positions of the free-support barycenter of the layouts X (node arrays): every layout's interchangeable
    macros are matched to the running mean (bridge.data.match_symmetric), then averaged; alternating, iters + 1 times."""
    from heurbridge.bridge.data import match_symmetric
    ref = X[0]
    for _ in range(iters + 1):
        ref = np.mean([match_symmetric(g, ref, x, block=block)[0] for x in X], axis=0)
    return ref


def main():
    from heurbridge.bridge.sample import source_nodes
    from relink_eval import best_of
    from train_bridge import load_bundle
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--design", required=True)
    ap.add_argument("--runs", default="runs/seed_trackA_dp")
    ap.add_argument("--refine-dir", required=True, help="output directory of tool_runs.py (or tool_refine_eval.py)")
    ap.add_argument("--ks", default="2,4")
    ap.add_argument("--iters", type=int, default=2)
    ap.add_argument("--select-seed", type=int, default=0)
    ap.add_argument("--eval-seeds", default="1,2,3")
    ap.add_argument("--match-block", type=int, default=2000)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    write_meta(out, "consensus_eval", a.design, config=vars(a), campaign="consensus of k tool runs vs best of k (exploratory)")
    b = load_bundle(a.suite, a.design, a.runs)
    des, g = b.design, b.graph
    base = cost.Baseline.from_records(des.id, json.loads((Path(a.runs) / des.id / "baseline.json").read_text())["records"])
    rd = Path(a.refine_dir)
    rows = [json.loads(l) for l in (rd / "rows.jsonl").read_text().splitlines() if l.strip()]
    ok = [r for r in rows if "J_select" in r]
    L = np.load(rd / ("layouts_%s.npz" % des.id))["tool"]
    assert len(L) == len(ok), "one saved layout per successful tool run"
    mm = des.is_macro & ~des.is_fixed
    lay_of = {}
    for k, r in enumerate(ok):
        lay = b.base.copy()
        lay.pos[mm], lay.orient[mm] = L[k, :, :2], L[k, :, 2].astype(np.int8)
        lay_of[r["tool_seed"]] = lay
    seeds = [r["tool_seed"] for r in rows]
    tools = [lay_of.get(s) for s in seeds]
    nodes = [source_nodes(g, t) if t is not None else None for t in tools]
    J_sel = [r["J_select"]["tool"] if "J_select" in r else INF for r in rows]
    J_fresh = [r["J_eval"]["tool"] if "J_select" in r else INF for r in rows]
    ev_sel = DreamplaceEvaluator(cluster_of=b.cluster_of, seed=a.select_seed)
    evs = [DreamplaceEvaluator(cluster_of=b.cluster_of, seed=int(s)) for s in a.eval_seeds.split(",")]
    work = out / "work"

    def f1(ev, lay, tag):
        return float(ev.score(ev.evaluate(des, lay, tag, work), base).J_inf)
    S = len(rows)
    with open(out / "rows.jsonl", "w") as fh:
        for k in (int(x) for x in a.ks.split(",")):
            for i in range(S if k < S else 1):
                win = [(i + j) % S for j in range(k)]
                fails = ["tool seed %d failed" % seeds[q] for q in win if tools[q] is None]
                live = [q for q in win if tools[q] is not None]
                t0 = time.time()
                J_c, fresh_c, seeds_c = INF, INF, {}
                if len(live) >= 2:
                    xc = barycenter(g, [nodes[q] for q in live], a.iters, a.match_block)
                    lc, rep = project.legalize_macros(des, g.to_layout(xc, tools[live[0]]))
                    t_cons = time.time() - t0
                    if rep.ok:
                        J_c = f1(ev_sel, lc, "k%d.i%d.sel" % (k, i))
                        seeds_c = {e.seed: f1(e, lc, "k%d.i%d.e%d" % (k, i, e.seed)) for e in evs}
                        fresh_c = float(np.median(list(seeds_c.values())))
                    else:
                        fails.append("P_M failed on the consensus")
                else:
                    t_cons = 0.0
                    fails.append("fewer than two tool runs")
                g_pick = min([(J_c, fresh_c)] + [(J_sel[q], J_fresh[q]) for q in win], key=lambda c: c[0])
                row = {"design": des.id, "k": k, "seed_index": i, "tool_seeds": [seeds[q] for q in win],
                       "J_eval": {"tool": J_fresh[i], "best": best_of(i, k, J_sel, J_fresh), "consensus": fresh_c,
                                  "guard": g_pick[1]},
                       "J_select": {"consensus": J_c}, "J_eval_seeds": {"consensus": seeds_c}, "failures": fails,
                       "cost_s": {"tool": round(sum(rows[q].get("cost_s", {}).get("tool", rows[q].get("tool_s", 0.0))
                                                    for q in win), 1), "consensus_extra": round(t_cons, 1)}}
                fh.write(json.dumps(row) + "\n")
                fh.flush()
                print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
