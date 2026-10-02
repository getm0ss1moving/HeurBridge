#!/usr/bin/env python3
"""Training pairs for a refiner of the tool's own layout: (tool layout -> better layout found by local search).

Per design and tool seed s (the tool = DREAMPlace mixed-size, then P_M):
  1. local search from the tool's layout with macro SHIFTS only (a fraction of the macro's size; each candidate
     legalized by P_M; scored by f1 with the selection seed): the bridge transports positions, so swaps of identical
     macros (removed by its symmetric matching) and orientation flips (a condition, never transported) would not be
     learnable targets;
  2. the tool's layout and the search's final layout are re-scored with fresh f1 seeds; the pair is kept only if the
     median over those seeds improves (an improvement that is the selection seed's noise is not a target);
  3. the target's cluster positions are the placed cell clusters of its f1 placement (DREAMPlace), its interchangeable
     macros matched to the source (bridge.data.match_symmetric), as the bridge's own pairs are built.
Output: <out>/pairs/<design>.pt (bridge.data.PairSet, for train_bridge.py --prior-pairs) and <out>/rows.jsonl (every
start: costs, J under the selection and the fresh seeds, kept or not).  Exploratory data generation.

  python scripts/tool_ls_pairs.py --designs ibm01 --tool-seeds 0,1,2,3 --steps 10 --moves 8 --par 2 --out runs/tool_ls/ibm01
"""

import argparse
import json
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heurbridge.core import orient as O, project  # noqa: E402
from heurbridge.eval import cost  # noqa: E402
from heurbridge.meta import write_meta  # noqa: E402
from heurbridge.pipeline.evaluators import DreamplaceEvaluator  # noqa: E402

SHIFTS = (-1.0, -0.5, -0.25, 0.25, 0.5, 1.0)


def shift_moves(design, layout, rng, n: int) -> list:
    """n candidates, each one movable macro shifted along one axis by a fraction of its own size."""
    mm = np.flatnonzero(design.is_macro & ~design.is_fixed)
    eff = O.effective_size(design.size, layout.orient) / design.core_wh
    out = []
    for _ in range(n):
        lay = layout.copy()
        i, ax, k = int(rng.choice(mm)), int(rng.integers(2)), float(rng.choice(SHIFTS))
        lay.pos[i, ax] = float(np.clip(lay.pos[i, ax] + k * eff[i, ax], eff[i, ax] / 2, 1 - eff[i, ax] / 2))
        out.append(lay)
    return out


def main():
    from heurbridge.bridge.data import PairSet, match_symmetric
    from heurbridge.bridge.sample import source_nodes
    from heurbridge.core import bookshelf
    from tool_refine_eval import tool_layout
    from train_bridge import SUITES, load_bundle
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--designs", required=True)
    ap.add_argument("--runs", default="runs/seed_trackA_dp")
    ap.add_argument("--tool-seeds", default="0,1,2,3")
    ap.add_argument("--steps", type=int, default=10)
    ap.add_argument("--moves", type=int, default=8)
    ap.add_argument("--par", type=int, default=2)
    ap.add_argument("--select-seed", type=int, default=0)
    ap.add_argument("--eval-seeds", default="1,2,3")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    (out / "pairs").mkdir(parents=True, exist_ok=True)
    write_meta(out, "tool_ls_pairs", a.designs, config=vars(a), campaign="refiner pairs: tool layout -> local search")
    rows_f = open(out / "rows.jsonl", "a")
    for name in a.designs.split(","):
        b = load_bundle(a.suite, name, a.runs)
        des, g = b.design, b.graph
        base = cost.Baseline.from_records(des.id, json.loads((Path(a.runs) / des.id / "baseline.json").read_text())["records"])
        d, l = bookshelf.load_bookshelf(SUITES[a.suite] / name / (name + ".aux"), family=a.suite)
        work = out / "work" / des.id
        work.mkdir(parents=True, exist_ok=True)
        ev_sel = DreamplaceEvaluator(cluster_of=b.cluster_of, seed=a.select_seed)
        evs = [DreamplaceEvaluator(cluster_of=b.cluster_of, seed=int(s)) for s in a.eval_seeds.split(",")]
        rng = np.random.default_rng(a.seed)
        x0s, x1s, metas = [], [], []

        def f1(ev, lay, tag):
            return float(ev.score(ev.evaluate(des, lay, tag, work), base).J_inf)
        for s in (int(x) for x in a.tool_seeds.split(",")):
            t0 = time.time()
            T, why, t_tool = tool_layout(d, l, b, s, work)
            row = {"design": des.id, "tool_seed": s, "tool_s": round(t_tool, 1), "failure": why}
            if T is None:
                rows_f.write(json.dumps(row) + "\n")
                continue
            cur, cur_J = T, f1(ev_sel, T, "s%d.tool" % s)
            J_tool_sel, n_eval, t_ls = cur_J, 1, time.time()
            with ThreadPoolExecutor(max_workers=max(1, a.par)) as pool:
                for step in range(a.steps):
                    cands = [lp for lp, rep in (project.legalize_macros(des, c) for c in shift_moves(des, cur, rng, a.moves))
                             if rep.ok]
                    Js = list(pool.map(lambda c: f1(ev_sel, c[1], "s%d.ls%d.%d" % (s, step, c[0])), enumerate(cands)))
                    n_eval += len(Js)
                    if Js and min(Js) < cur_J:
                        k = int(np.argmin(Js))
                        cur, cur_J = cands[k], Js[k]
            fresh_T = [f1(e, T, "s%d.tool.e%d" % (s, e.seed)) for e in evs]
            fresh_L = [f1(e, cur, "s%d.ls.e%d" % (s, e.seed)) for e in evs]
            keep = cur is not T and float(np.median(fresh_L)) < float(np.median(fresh_T))
            row.update({"J_select": {"tool": J_tool_sel, "ls": cur_J}, "J_fresh": {"tool": fresh_T, "ls": fresh_L},
                        "median_fresh": {"tool": float(np.median(fresh_T)), "ls": float(np.median(fresh_L))},
                        "kept": bool(keep), "ls_evals": n_eval, "ls_s": round(time.time() - t_ls, 1),
                        "wall_s": round(time.time() - t0, 1)})
            if keep:                                    # the target's clusters: its own f1 placement
                _, placed = ev_sel.evaluate_placed(des, cur, "s%d.ls.placed" % s, work)
                if placed is None:
                    row["kept"] = False
                    row["failure"] = "target placement failed"
                else:
                    x0 = source_nodes(g, T)
                    x1 = g.node_positions(cur, cluster_pos=g.cluster_centroids(placed, des.area))
                    _, perm = match_symmetric(g, x0, x1)
                    x0s.append(x0.astype(np.float32))
                    x1s.append(x1[perm].astype(np.float32))
                    metas.append({"elite": -1, "J": float(np.median(fresh_L)), "dist2": 0.0, "tool_seed": s,
                                  "J_tool": float(np.median(fresh_T))})
            rows_f.write(json.dumps(row) + "\n")
            rows_f.flush()
            print(json.dumps({k: row.get(k) for k in ("design", "tool_seed", "median_fresh", "kept", "ls_evals", "wall_s")}),
                  flush=True)
        if x0s:
            n = len(x0s)
            PairSet(g, np.stack(x0s), np.stack(x1s), np.ones(n, np.float32),
                    np.zeros((n, g.n), np.int8), metas).save(out / "pairs" / (des.id + ".pt"), round_id=90)


if __name__ == "__main__":
    main()
