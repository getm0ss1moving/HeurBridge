#!/usr/bin/env python3
"""Relinking two tool runs against the tool's best of three at about equal compute (Track A; exploratory).

Input: the tool layouts saved by scripts/tool_refine_eval.py (layouts_<design>.npz, key "tool": one layout per tool
seed, in the order of its rows.jsonl) with their selection-seed and fresh-seed J (rows.jsonl).  Per tool seed s with
partner p = the next seed in the list:
  relink   candidates P_M(T_s + a (T_p' - T_s)) for a in --alphas, T_p' = T_p with its interchangeable macros matched to
           T_s (bridge.data.match_symmetric); the pick is the best of {T_s, T_p, candidates} by f1 with the selection
           seed; cost = two tool runs + 2 + len(alphas) f1 runs
  best3    the tool's best of three seeds {s, s+1, s+2} by the selection seed (from the saved rows; no new run); cost =
           three tool runs + 3 f1 runs
The endpoint of every pick is the median over fresh f1 seeds (the tool layouts' fresh values come from the saved rows,
the relink candidates' are scored here).

  python scripts/relink_eval.py --design ibm04 --refine-dir runs/tool_refine3/ibm04 --alphas 0.25,0.5,0.75 --out runs/relink/ibm04
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


def main():
    from heurbridge.bridge.data import match_symmetric
    from heurbridge.bridge.sample import source_nodes
    from train_bridge import load_bundle
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--design", required=True)
    ap.add_argument("--runs", default="runs/seed_trackA_dp")
    ap.add_argument("--refine-dir", required=True, help="output directory of tool_refine_eval.py for this design")
    ap.add_argument("--alphas", default="0.25,0.5,0.75")
    ap.add_argument("--select-seed", type=int, default=0)
    ap.add_argument("--eval-seeds", default="1,2,3")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    write_meta(out, "relink_eval", a.design, config=vars(a), campaign="relinking two tool runs vs best of three")
    b = load_bundle(a.suite, a.design, a.runs)
    des, g = b.design, b.graph
    base = cost.Baseline.from_records(des.id, json.loads((Path(a.runs) / des.id / "baseline.json").read_text())["records"])
    rd = Path(a.refine_dir)
    rows = [json.loads(l) for l in (rd / "rows.jsonl").read_text().splitlines() if l.strip()]
    rows = [r for r in rows if "J_eval" in r]
    L = np.load(rd / ("layouts_%s.npz" % des.id))["tool"]           # (S, M, 3): x, y, orient
    mm = des.is_macro & ~des.is_fixed
    tools = []
    for k in range(len(rows)):
        lay = b.base.copy()
        lay.pos[mm], lay.orient[mm] = L[k, :, :2], L[k, :, 2].astype(np.int8)
        tools.append(lay)
    J_sel = [r["J_select"]["tool"] for r in rows]
    J_fresh = [r["J_eval"]["tool"] for r in rows]
    ev_sel = DreamplaceEvaluator(cluster_of=b.cluster_of, seed=a.select_seed)
    evs = [DreamplaceEvaluator(cluster_of=b.cluster_of, seed=int(s)) for s in a.eval_seeds.split(",")]
    work = out / "work"

    def f1(ev, lay, tag):
        return float(ev.score(ev.evaluate(des, lay, tag, work), base).J_inf)
    alphas = [float(x) for x in a.alphas.split(",")]
    S = len(tools)
    with open(out / "rows.jsonl", "w") as fh:
        for s in range(S):
            p = (s + 1) % S
            t0 = time.time()
            xs = source_nodes(g, tools[s])
            xp, _ = match_symmetric(g, xs, source_nodes(g, tools[p]))
            cands = [("tool_s", tools[s], J_sel[s], J_fresh[s]), ("tool_p", tools[p], J_sel[p], J_fresh[p])]
            for al in alphas:
                lp, rep = project.legalize_macros(des, g.to_layout(xs + al * (xp - xs), tools[s]))
                if rep.ok:
                    cands.append(("a%g" % al, lp, f1(ev_sel, lp, "s%d.a%g" % (s, al)), None))
            pick = min(cands, key=lambda c: c[2])
            fresh = pick[3] if pick[3] is not None else float(np.median([f1(e, pick[1], "s%d.pick.e%d" % (s, e.seed))
                                                                         for e in evs]))
            k2 = min([s, p], key=lambda k: J_sel[k])
            k3 = min([s, (s + 1) % S, (s + 2) % S], key=lambda k: J_sel[k])
            row = {"design": des.id, "seed_index": s, "partner": p, "relink_pick": pick[0],
                   "J_eval": {"tool": J_fresh[s], "best2": J_fresh[k2], "best3": J_fresh[k3], "relink": fresh},
                   "J_select": {"relink": pick[2]}, "wall_s": round(time.time() - t0, 1)}
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
