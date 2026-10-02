#!/usr/bin/env python3
"""The tool started from given macro layouts instead of its random centre start (Track A; exploratory, IBM only).

DREAMPlace's mixed-size run (the tool) starts every movable object near the die centre with seed-dependent noise
(random_center_init_flag = 1), and the seed decides the macro arrangement it ends in.  Here it starts from a macro
layout (random_center_init_flag = 0; standard cells at their cluster's quadratic position around those macros), then
P_M, as every tool run.  Starts per design (--k each):
  heur  the seeding campaign's best distinct layouts by f1 J (heuristic programs and their local search;
        runs/seed_trackA_dp/<design>/evals.jsonl)
  self  the tool's own layouts T_s (a second tool pass)
  cons  the consensus of T_s and T_(s+1) (scripts/consensus_eval.barycenter)
Each warm run is scored by f1 with the selection seed and judged by the median over fresh f1 seeds; the random-start
tool runs (rows of scripts/tool_runs.py or tool_refine_eval.py) are the comparison.  Failures are +inf, named.

  python scripts/warm_tool_eval.py --design ibm04 --refine-dir runs/tool_refine3/ibm04 --out runs/warm_tool/ibm04
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

INF = float("inf")


def main():
    from consensus_eval import barycenter
    from demo_sketch_start import start_from_pl, with_cells
    from tool_refine_eval import load_raw, tool_layout
    from train_bridge import load_bundle
    from heurbridge.bridge.sample import source_nodes
    from heurbridge.core import project
    from heurbridge.eval import cost
    from heurbridge.meta import write_meta
    from heurbridge.pipeline.evaluators import DreamplaceEvaluator
    from heurbridge.pipeline.seed_archive import distinct
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--design", required=True)
    ap.add_argument("--runs", default="runs/seed_trackA_dp")
    ap.add_argument("--refine-dir", required=True, help="output directory of tool_runs.py (or tool_refine_eval.py)")
    ap.add_argument("--starts", default="heur,self,cons")
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--select-seed", type=int, default=0)
    ap.add_argument("--eval-seeds", default="1,2,3")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry", action="store_true", help="build and describe the starts, run nothing")
    ap.add_argument("--target-density", type=float, default=0.9, help="the warm tool run's DREAMPlace target density")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    write_meta(out, "warm_tool_eval", a.design, config=vars(a), campaign="the tool started from given macro layouts (exploratory)")
    b = load_bundle(a.suite, a.design, a.runs)
    des, g = b.design, b.graph
    base = cost.Baseline.from_records(des.id, json.loads((Path(a.runs) / des.id / "baseline.json").read_text())["records"])
    d_raw, l_raw = load_raw(a.suite, a.design)
    mm = des.is_macro & ~des.is_fixed
    rd = Path(a.refine_dir)
    rows = [json.loads(l) for l in (rd / "rows.jsonl").read_text().splitlines() if l.strip()]
    ok = [r for r in rows if "J_select" in r]
    L = np.load(rd / ("layouts_%s.npz" % des.id))["tool"]
    tools = []
    for k in range(len(ok)):
        lay = b.base.copy()
        lay.pos[mm], lay.orient[mm] = L[k, :, :2], L[k, :, 2].astype(np.int8)
        tools.append((ok[k]["tool_seed"], lay, ok[k]["J_eval"]["tool"]))
    starts = []
    for kind in a.starts.split(","):
        if kind == "heur":
            ev = [json.loads(l) for l in (Path(a.runs) / des.id / "evals.jsonl").read_text().splitlines() if l.strip()]
            fin = [r for r in ev if r.get("pos_macros") is not None and r.get("J") is not None and math.isfinite(r["J"])]
            for r in distinct(sorted(fin, key=lambda r: r["J"]))[:a.k]:
                lay = b.base.copy()
                lay.pos[mm], lay.orient[mm] = np.asarray(r["pos_macros"]), np.asarray(r["orient_macros"], np.int8)
                starts.append(("heur", r["run_id"], lay, r["J"]))
        elif kind == "self":
            starts += [("self", "tool_s%d" % s, lay, j) for s, lay, j in tools[:a.k]]
        elif kind == "cons":
            for i in range(min(a.k, len(tools))):
                (s, l1, _), (p, l2, _) = tools[i], tools[(i + 1) % len(tools)]
                xc = barycenter(g, [source_nodes(g, l1), source_nodes(g, l2)], 2, 2000)
                lc, rep = project.legalize_macros(des, g.to_layout(xc, l1))
                starts.append(("cons", "cons_s%d_s%d" % (s, p), lc if rep.ok else None, None))
    if a.dry:
        for kind, src, lay0, J0 in starts:
            ok_ = lay0 is not None and project.check_macros(des, lay0, 0.0)["ok"]
            init = with_cells(des, lay0, source_nodes(g, lay0)[g.cluster_nodes], b.cluster_of) if lay0 is not None else None
            print(json.dumps({"start": kind, "source": src, "start_J": J0, "legal": ok_,
                              "cells_placed": int(np.isfinite(init.pos).all(1).sum()) if init is not None else 0}))
        return
    ev_sel = DreamplaceEvaluator(cluster_of=b.cluster_of, seed=a.select_seed)
    evs = [DreamplaceEvaluator(cluster_of=b.cluster_of, seed=int(s)) for s in a.eval_seeds.split(",")]
    work = out / "work"
    with open(out / "rows.jsonl", "w") as fh:
        for n, (kind, src, lay0, J0) in enumerate(starts):
            row = {"design": des.id, "start": kind, "source": src, "start_J": J0, "failures": [],
                   "target_density": a.target_density}
            if lay0 is None:
                row["failures"].append("P_M failed on the start")
                row.update({"J_select": INF, "J_eval": INF})
            else:
                quad = source_nodes(g, lay0)[g.cluster_nodes]
                init = with_cells(des, lay0, quad, b.cluster_of)
                l0 = l_raw.copy()
                l0.pos[mm], l0.orient[mm] = init.pos[mm], init.orient[mm]
                cells = np.isfinite(init.pos).all(1) & ~des.is_macro & ~des.is_io & ~des.is_fixed
                l0.pos[cells] = init.pos[cells]
                t0 = time.time()
                with start_from_pl():
                    T, why, t_tool = tool_layout(d_raw, l0, b, n, work / ("w%d" % n), a.target_density)
                if T is None:
                    row["failures"].append(why or "tool run failed")
                    row.update({"J_select": INF, "J_eval": INF, "tool_s": round(t_tool, 1)})
                else:
                    rec = ev_sel.evaluate(des, T, "w%d.sel" % n, work)
                    js = float(ev_sel.score(rec, base).J_inf)
                    recs = {e.seed: e.evaluate(des, T, "w%d.e%d" % (n, e.seed), work) for e in evs}
                    fresh = {k: float(ev_sel.score(r, base).J_inf) for k, r in recs.items()}
                    comp = lambda r: {"hpwl_um": r.get("hpwl_um"), "rudy_of_pct": r.get("rudy_of_pct")}
                    row["components"] = {"select": comp(rec), "eval": {k: comp(r) for k, r in recs.items()}}
                    disp = float(np.sqrt(((T.pos[mm] - lay0.pos[mm]) ** 2).sum(1)).mean())
                    row.update({"J_select": js, "J_eval": float(np.median(list(fresh.values()))), "J_eval_seeds": fresh,
                                "tool_s": round(t_tool, 1), "mean_macro_move": disp, "wall_s": round(time.time() - t0, 1)})
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
