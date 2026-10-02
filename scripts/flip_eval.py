#!/usr/bin/env python3
"""Macro orientation pass on the tool's layouts against the tool's best of k (Track A; exploratory, IBM only).

The tool (DREAMPlace mixed-size) never flips a macro: every macro keeps the benchmark's orientation.  The pass picks,
per movable macro, the footprint-preserving orientation (N, S, FS, FN: positions and legality unchanged) that
minimizes the weighted HPWL of the macro's nets with every other pin where f1 placed it, greedily, until no macro
changes (at most --passes sweeps).  Per tool seed s (layouts and rows of scripts/tool_runs.py or tool_refine_eval.py):
  flip        the pass applied to T_s, using T_s's f1 placement with the selection seed; cost = one more f1 run
  flip_guard  the better of T_s and flip(T_s) by the selection seed
  best_k      the tool's best of k by the selection seed (k tool runs and k f1 runs; from the saved rows)
The analysis adds best2+flip (the guarded pass on the best-of-2 pick: two tool runs and three f1 runs).  Every
layout is judged by the median J over fresh f1 seeds; failures are +inf and named.

  python scripts/flip_eval.py --design ibm04 --refine-dir runs/tool_runs/ibm04 --out runs/flip/ibm04
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

from heurbridge.core import orient as O  # noqa: E402
from heurbridge.core.design import centres_abs, pin_positions  # noqa: E402

INF = float("inf")
FLIPS = (O.R0, O.R180, O.MX, O.MY)          # N, S, FS, FN: width and height unchanged


def flip_pass(des, placed, passes: int = 3, max_deg: int = 1000, cand=FLIPS) -> tuple:
    """Orientations after the greedy pass (movable macros only) and (weighted HPWL of the touched nets before, after,
    macros changed).  ``placed``: a layout with every object placed (f1's output); nets above ``max_deg`` pins are
    skipped (one macro hardly moves their box)."""
    orient = placed.orient.copy()
    lay = placed.copy()
    pos = pin_positions(des, lay)
    cen = centres_abs(des, lay)
    deg = np.diff(des.net_ptr)
    net_of = np.empty(des.n_pins, np.int64)
    net_of[des.pin_idx] = np.repeat(np.arange(des.n_nets), deg)
    w = des.net_weight
    order = np.argsort(des.pin_obj, kind="stable")
    bounds = np.searchsorted(des.pin_obj[order], np.arange(des.n_objects + 1))
    mov = np.flatnonzero(des.is_macro & ~des.is_fixed)
    before = 0.0
    changed = set()
    for sweep in range(passes):
        moved = 0
        for m in mov:
            pm = order[bounds[m]:bounds[m + 1]]
            if not len(pm):
                continue
            nets = np.unique(net_of[pm])
            nets = nets[deg[nets] <= max_deg]
            if not len(nets):
                continue
            lo = np.full((len(nets), 2), INF)
            hi = np.full((len(nets), 2), -INF)
            mine = []
            for j, k in enumerate(nets):
                pk = des.pin_idx[des.net_ptr[k]:des.net_ptr[k + 1]]
                other = pk[des.pin_obj[pk] != m]
                if len(other):
                    lo[j], hi[j] = pos[other].min(0), pos[other].max(0)
                mine.append(np.flatnonzero(net_of[pm] == k))
            cost = []
            for o in cand:
                pp = cen[m] + O.apply(des.pin_off[pm], np.full(len(pm), o))
                c = 0.0
                for j, k in enumerate(nets):
                    q = pp[mine[j]]
                    c += w[k] * (np.maximum(hi[j], q.max(0)) - np.minimum(lo[j], q.min(0))).sum()
                cost.append(c)
            cur = cand.index(orient[m]) if orient[m] in cand else None
            if cur is None:
                continue                                   # a rotated macro keeps its orientation
            best = int(np.argmin(cost))
            if sweep == 0:
                before += cost[cur]
            if cost[best] < cost[cur] - 1e-9:
                orient[m] = cand[best]
                pos[pm] = cen[m] + O.apply(des.pin_off[pm], np.full(len(pm), cand[best]))
                changed.add(int(m))
                moved += 1
        if not moved:
            break
    return orient, {"macros_changed": int((orient != placed.orient).sum()), "sweeps": sweep + 1,
                    "touched_nets_cost_before": before}


def main():
    from relink_eval import best_of
    from train_bridge import load_bundle
    from heurbridge.eval import cost
    from heurbridge.meta import write_meta
    from heurbridge.pipeline.evaluators import DreamplaceEvaluator
    from heurbridge.core.design import hpwl
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--design", required=True)
    ap.add_argument("--runs", default="runs/seed_trackA_dp")
    ap.add_argument("--refine-dir", required=True, help="output directory of tool_runs.py (or tool_refine_eval.py)")
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--select-seed", type=int, default=0)
    ap.add_argument("--eval-seeds", default="1,2,3")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    write_meta(out, "flip_eval", a.design, config=vars(a), campaign="macro orientation pass on the tool's layouts (exploratory)")
    b = load_bundle(a.suite, a.design, a.runs)
    des = b.design
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
    J_sel = [r["J_select"]["tool"] if "J_select" in r else INF for r in rows]
    J_fresh = [r["J_eval"]["tool"] if "J_select" in r else INF for r in rows]
    ev_sel = DreamplaceEvaluator(cluster_of=b.cluster_of, seed=a.select_seed)
    evs = [DreamplaceEvaluator(cluster_of=b.cluster_of, seed=int(s)) for s in a.eval_seeds.split(",")]
    work = out / "work"
    S = len(rows)
    with open(out / "rows.jsonl", "w") as fh:
        for i in range(S):
            s = seeds[i]
            row = {"design": des.id, "seed_index": i, "tool_seed": s, "failures": [],
                   "J_eval": {"tool": J_fresh[i], "best2": best_of(i, 2, J_sel, J_fresh), "best3": best_of(i, 3, J_sel, J_fresh),
                              "best4": best_of(i, 4, J_sel, J_fresh)},
                   "best2_pick": min([i, (i + 1) % S], key=lambda q: J_sel[q])}
            if tools[i] is None:
                row["failures"].append("tool seed %d failed" % s)
                row["J_eval"].update({"flip": INF, "flip_guard": INF})
                row["J_select"] = {"tool": INF, "flip": INF}
            else:
                t0 = time.time()
                rec, placed = ev_sel.evaluate_placed(des, tools[i], "s%d.sel" % s, work)
                J0 = float(ev_sel.score(rec, base).J_inf)
                t_f1 = time.time() - t0
                if placed is None:
                    row["failures"].append("f1 of the tool layout failed")
                    row["J_eval"].update({"flip": INF, "flip_guard": J_fresh[i]})
                    row["J_select"] = {"tool": J_sel[i], "tool_rerun": J0, "flip": INF}
                else:
                    t1 = time.time()
                    o, st = flip_pass(des, placed, a.passes)
                    T2 = tools[i].copy()
                    T2.orient = o
                    t_pass = time.time() - t1
                    pl2 = placed.copy()
                    pl2.orient = o
                    h0, h1 = float(hpwl(des, placed)), float(hpwl(des, pl2))
                    J1 = float(ev_sel.score(ev_sel.evaluate(des, T2, "s%d.flip.sel" % s, work), base).J_inf) if st["macros_changed"] else J0
                    fresh = (float(np.median([e.score(e.evaluate(des, T2, "s%d.flip.e%d" % (s, e.seed), work), base).J_inf
                                              for e in evs])) if st["macros_changed"] else J_fresh[i])
                    row["J_select"] = {"tool": J_sel[i], "tool_rerun": J0, "flip": J1}
                    row["J_eval"].update({"flip": fresh, "flip_guard": fresh if J1 < J0 else J_fresh[i]})
                    row.update({"flip_stats": st, "hpwl_placed": {"before": h0, "after_cells_fixed": h1},
                                "cost_s": {"f1": round(t_f1, 1), "pass": round(t_pass, 1)}})
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
