#!/usr/bin/env python3
"""Tool + learned refiner against the tool's best of k seeds at about equal compute (Track A; exploratory until
pre-registered).

Per design and tool seed s:
  tool_s       the tool's layout: DREAMPlace mixed-size with seed s, then P_M
  refine_s     a refiner (bridge checkpoint) applied to tool_s, guarded: the candidates P_M(x + a (T(x) - x)) for a in
               {0, 0.25, 0.5, 1}, picked by f1 with the SELECTION seed (a = 0 is tool_s itself)
  best2_s      the tool's best of two seeds (s and s + offset), picked by f1 with the selection seed; about the same
               wall-clock as tool_s + three extra f1 runs
Every picked layout is then scored with fresh EVALUATION seeds the selection never saw; the endpoint is the median J
over those seeds (as the tool's own baseline is a median over three seeds: a single DREAMPlace run can blow the
overflow term up, e.g. J 0.44 under one seed and 1.8 under another on ibm08), so a pick cannot profit from the
selection seed's noise.  Picked layouts are saved (layouts_<design>.npz).  Wall-clock of every tool run, f1 run and
refiner call is recorded.

  python scripts/tool_refine_eval.py --designs ibm04 --tool-seeds 0,1,2,3 --pair-offset 100 \
      --bridge checkpoints/algR_trackA_final/best.pt --eval-seeds 1,2 --out runs/tool_refine/demo
"""

import argparse
import contextlib
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

ALPHAS = (0.25, 0.5, 1.0)


def load_raw(suite: str, name: str):
    """The benchmark design and placement exactly as the seeding campaign loads them (scripts/run_seed_archive.py): on
    ISPD2005 the mixed-size (MMS) convention makes every macro movable, so the tool places them."""
    from heurbridge.core import bookshelf
    from train_bridge import SUITES
    d, l = bookshelf.load_bookshelf(SUITES[suite] / name / (name + ".aux"), family=suite)
    if suite == "ispd2005":
        d.is_fixed = d.is_fixed & ~d.is_macro
        l.schema = d.schema_hash()
    return d, l


def tool_layout(d, l, b, seed, work):
    """The tool's macro layout for one seed (mixed-size, P_M) and its wall-clock; None on failure."""
    from heurbridge.eval.dreamplace import run_dreamplace_m1
    t0 = time.time()
    rec, lay = run_dreamplace_m1(d, l, work / ("tool_s%d" % seed), seed=seed)
    if lay is None:
        return None, rec.get("failure"), time.time() - t0
    out = b.base.copy()
    out.pos, out.orient = lay.pos, lay.orient
    lp, rep = project.legalize_macros(b.design, out)
    return (lp if rep.ok else None), (None if rep.ok else "P_M failed"), time.time() - t0


def main():
    from heurbridge.bridge.sample import bridge_endpoints, source_nodes
    from heurbridge.bridge.train import load_bridge
    from train_bridge import load_bundle
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--designs", required=True)
    ap.add_argument("--runs", default="runs/seed_trackA_dp")
    ap.add_argument("--bridge", required=True)
    ap.add_argument("--K", type=int, default=20)
    ap.add_argument("--tool-seeds", default="0,1,2,3")
    ap.add_argument("--pair-offset", type=int, default=100, help="best-of-2 pairs seed s with seed s + offset")
    ap.add_argument("--select-seed", type=int, default=0, help="f1 seed used to pick (guard and best-of-2)")
    ap.add_argument("--eval-seeds", default="1,2,3", help="fresh f1 seeds for the endpoint (median)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    write_meta(out, "tool_refine_eval", a.designs, config=vars(a), campaign="tool + refiner vs tool best-of-2")
    model = load_bridge(a.bridge)
    ev_sel = None
    rows_f = open(out / "rows.jsonl", "a")
    for name in a.designs.split(","):
        b = load_bundle(a.suite, name, a.runs)
        des = b.design
        base = cost.Baseline.from_records(des.id, json.loads((Path(a.runs) / des.id / "baseline.json").read_text())["records"])
        d, l = load_raw(a.suite, name)
        work = out / "work" / des.id
        work.mkdir(parents=True, exist_ok=True)
        ev_sel = DreamplaceEvaluator(cluster_of=b.cluster_of, seed=a.select_seed)
        evs = {s: DreamplaceEvaluator(cluster_of=b.cluster_of, seed=s) for s in (int(x) for x in a.eval_seeds.split(","))}

        def f1(ev, lay, tag):
            t0 = time.time()
            rec = ev.evaluate(des, lay, tag, work)
            return float(ev.score(rec, base).J_inf), time.time() - t0

        def fresh(lay, tag):
            return {s: f1(e, lay, "%s.e%d" % (tag, s))[0] for s, e in evs.items()}
        saved = {}
        for s in (int(x) for x in a.tool_seeds.split(",")):
            row = {"design": des.id, "tool_seed": s}
            T, why, t_tool = tool_layout(d, l, b, s, work)
            T2, why2, t_tool2 = tool_layout(d, l, b, s + a.pair_offset, work)
            row.update({"tool_s": round(t_tool, 1), "tool2_s": round(t_tool2, 1), "failures": [w for w in (why, why2) if w]})
            if T is None:
                row["J_eval"] = {"tool": float("inf"), "refine": float("inf"), "best2": float("inf")}
                rows_f.write(json.dumps(row) + "\n")
                rows_f.flush()
                continue
            J_T, t_f1 = f1(ev_sel, T, "s%d.tool" % s)
            # refiner: bridge endpoint, guarded by the selection seed
            t0 = time.time()
            x = source_nodes(b.graph, T)
            end = bridge_endpoints(model, b.graph, x[None], K=a.K)[0]
            t_bridge = time.time() - t0
            cands = [(0.0, T, J_T)]
            t_guard = 0.0
            for al in ALPHAS:
                lp, rep = project.legalize_macros(des, b.graph.to_layout(x + al * (end - x), T))
                if rep.ok:
                    J, t = f1(ev_sel, lp, "s%d.a%g" % (s, al))
                    t_guard += t
                    cands.append((al, lp, J))
            al_best, R, J_R = min(cands, key=lambda c: c[2])
            # the tool's best of two seeds, picked by the selection seed
            if T2 is not None:
                J_T2, t_f1b = f1(ev_sel, T2, "s%d.tool2" % s)
                B2, J_B2 = (T, J_T) if J_T <= J_T2 else (T2, J_T2)
            else:
                B2, J_B2, t_f1b = T, J_T, 0.0
            row.update({"J_select": {"tool": J_T, "refine": J_R, "best2": J_B2}, "refine_alpha": al_best,
                        "cost_s": {"tool": round(t_tool, 1), "refine": round(t_tool + t_f1 + t_bridge + t_guard, 1),
                                   "best2": round(t_tool + t_tool2 + t_f1 + t_f1b, 1)}})
            ft, fr = fresh(T, "s%d.tool" % s), (fresh(R, "s%d.ref" % s) if al_best else None)
            fb = fresh(B2, "s%d.best2" % s) if B2 is not T else ft
            fr = fr if fr is not None else ft
            row["J_eval"] = {"tool": float(np.median(list(ft.values()))), "refine": float(np.median(list(fr.values()))),
                             "best2": float(np.median(list(fb.values())))}
            row["J_eval_mean"] = {"tool": float(np.mean(list(ft.values()))), "refine": float(np.mean(list(fr.values()))),
                                  "best2": float(np.mean(list(fb.values())))}
            mm = des.is_macro & ~des.is_fixed
            for k, lay_k in (("tool", T), ("refine", R), ("best2", B2)):
                saved.setdefault(k, []).append(np.c_[lay_k.pos[mm], lay_k.orient[mm]])
            row["J_eval_seeds"] = {"tool": ft, "refine": fr, "best2": fb}
            rows_f.write(json.dumps(row) + "\n")
            rows_f.flush()
            print(json.dumps({k: row[k] for k in ("design", "tool_seed", "J_select", "J_eval", "cost_s", "refine_alpha")
                              if k in row}), flush=True)
        if saved:
            np.savez(out / ("layouts_%s.npz" % des.id), **{k: np.stack(v) for k, v in saved.items()})


if __name__ == "__main__":
    main()
