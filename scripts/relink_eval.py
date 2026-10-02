#!/usr/bin/env python3
"""Relinking two tool runs against the tool's best of k runs (Track A).

Input: the tool layouts saved by scripts/tool_runs.py or scripts/tool_refine_eval.py (layouts_<design>.npz, key "tool":
one layout per successful tool run, in the order of its rows.jsonl) with their selection-seed and fresh-seed J
(rows.jsonl: one row per tool seed; a failed run has no "J_select" and no saved layout).  Per tool seed s (position i in
the rows) with partner p = the next seed in the rows (cyclic):
  relink   candidates P_M(T_s + a (T_p' - T_s)) for a in --alphas, T_p' = T_p with its interchangeable macros matched to
           T_s (bridge.data.match_symmetric, exact for groups up to --match-block macros); the pick is the best of {T_s, T_p, candidates} by f1 with the selection
           seed; cost = two tool runs + 2 + len(alphas) f1 runs
  best_k   the tool's best of the k seeds at positions i..i+k-1 (cyclic) by the selection seed (from the saved rows; no
           new run); cost = k tool runs + k f1 runs
A failed tool run, a failed P_M or a failed f1 is a +inf candidate (it is picked only if every candidate is +inf); the
row names the failures.  The endpoint of every pick is the median over fresh f1 seeds (the tool layouts' fresh values
come from the saved rows, the relink candidates' are scored here).  Used by the exploratory IBM comparison
(reports/beat_tool_track_a.md) and by the confirmatory ISPD2005 test (reports/relink_preregistration.md).

  python scripts/relink_eval.py --design ibm04 --refine-dir runs/tool_runs/ibm04 --alphas 0.25,0.5,0.75 --out runs/relink/ibm04
"""

import argparse
import json
import math
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


def best_of(i: int, k: int, J_sel: list, J_fresh: list) -> float:
    """Fresh-seed J of the tool's best of the k runs at positions i..i+k-1 (cyclic), picked by the selection seed."""
    S = len(J_sel)
    pick = min([(i + j) % S for j in range(k)], key=lambda q: J_sel[q])   # ties: the earlier position
    return J_fresh[pick]


def main():
    from heurbridge.bridge.data import match_symmetric
    from heurbridge.bridge.sample import source_nodes
    from train_bridge import load_bundle
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--design", required=True)
    ap.add_argument("--runs", default="runs/seed_trackA_dp")
    ap.add_argument("--refine-dir", required=True, help="output directory of tool_runs.py (or tool_refine_eval.py) for this design")
    ap.add_argument("--alphas", default="0.25,0.5,0.75")
    ap.add_argument("--select-seed", type=int, default=0)
    ap.add_argument("--eval-seeds", default="1,2,3")
    ap.add_argument("--match-block", type=int, default=2000,
                    help="interchangeable groups larger than this are matched blockwise (exact below; IBM: all exact)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    write_meta(out, "relink_eval", a.design, config=vars(a), campaign="relinking two tool runs vs the tool's best of k")
    b = load_bundle(a.suite, a.design, a.runs)
    des, g = b.design, b.graph
    base = cost.Baseline.from_records(des.id, json.loads((Path(a.runs) / des.id / "baseline.json").read_text())["records"])
    rd = Path(a.refine_dir)
    rows = [json.loads(l) for l in (rd / "rows.jsonl").read_text().splitlines() if l.strip()]
    ok = [r for r in rows if "J_select" in r]
    L = np.load(rd / ("layouts_%s.npz" % des.id))["tool"] if ok else np.zeros((0, 0, 3))   # (S_ok, M, 3): x, y, orient
    assert len(L) == len(ok), "one saved layout per successful tool run"
    mm = des.is_macro & ~des.is_fixed
    lay_of = {}
    for k, r in enumerate(ok):
        lay = b.base.copy()
        lay.pos[mm], lay.orient[mm] = L[k, :, :2], L[k, :, 2].astype(np.int8)
        lay_of[r["tool_seed"]] = lay
    seeds = [r["tool_seed"] for r in rows]
    tools = [lay_of.get(s) for s in seeds]
    J_sel = [r["J_select"]["tool"] if "J_select" in r else INF for r in rows]
    J_fresh = [r["J_eval"]["tool"] if "J_select" in r else INF for r in rows]
    why_tool = ["tool seed %d: %s" % (s, r.get("failure") or r.get("failures") or "failed")
                for s, r in zip(seeds, rows) if "J_select" not in r]
    ev_sel = DreamplaceEvaluator(cluster_of=b.cluster_of, seed=a.select_seed)
    evs = [DreamplaceEvaluator(cluster_of=b.cluster_of, seed=int(s)) for s in a.eval_seeds.split(",")]
    work = out / "work"

    def f1(ev, lay, tag):
        return float(ev.score(ev.evaluate(des, lay, tag, work), base).J_inf)
    alphas = [float(x) for x in a.alphas.split(",")]
    S = len(rows)
    with open(out / "rows.jsonl", "w") as fh:
        for i in range(S):
            j = (i + 1) % S
            s, p = seeds[i], seeds[j]
            t0 = time.time()
            fails = [w for w in why_tool if w.startswith("tool seed %d:" % s) or w.startswith("tool seed %d:" % p)]
            cands = [(nm, tools[q], J_sel[q], J_fresh[q]) for nm, q in (("tool_s", i), ("tool_p", j)) if tools[q] is not None]
            if tools[i] is not None and tools[j] is not None:
                xs = source_nodes(g, tools[i])
                xp, _ = match_symmetric(g, xs, source_nodes(g, tools[j]), block=a.match_block)
                for al in alphas:
                    lp, rep = project.legalize_macros(des, g.to_layout(xs + al * (xp - xs), tools[i]))
                    if rep.ok:
                        cands.append(("a%g" % al, lp, f1(ev_sel, lp, "s%d.a%g" % (s, al)), None))
                    else:
                        fails.append("P_M failed at a = %g" % al)
            t_method = time.time() - t0
            if cands:
                pick = min(cands, key=lambda c: c[2])                  # ties: T_s, then T_p, then the smaller a
                t1 = time.time()
                fresh = pick[3] if pick[3] is not None else float(np.median([f1(e, pick[1], "s%d.pick.e%d" % (s, e.seed))
                                                                             for e in evs]))
                t_eval = time.time() - t1
                name, J_pick = pick[0], pick[2]
            else:
                name, J_pick, fresh, t_eval = None, INF, INF, 0.0
            row = {"design": des.id, "seed_index": i, "tool_seed": s, "partner": j, "partner_seed": p, "relink_pick": name,
                   "J_eval": {"tool": J_fresh[i], "best2": best_of(i, 2, J_sel, J_fresh), "best3": best_of(i, 3, J_sel, J_fresh),
                              "best4": best_of(i, 4, J_sel, J_fresh), "relink": fresh},
                   "J_select": {"relink": J_pick}, "failures": fails,
                   "cost_s": {"relink_extra": round(t_method, 1), "endpoint_eval": round(t_eval, 1)},
                   "wall_s": round(time.time() - t0, 1)}
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
