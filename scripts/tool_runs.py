#!/usr/bin/env python3
"""The tool's layouts for several seeds, scored by f1 with a selection seed and with fresh seeds (Track A).

Per design and tool seed s: DREAMPlace mixed-size with seed s, P_M, f1 J with the selection seed, f1 J with every fresh
seed (median = the endpoint).  Output in the format scripts/relink_eval.py reads: rows.jsonl (J_select, J_eval,
J_eval_seeds, cost) and layouts_<design>.npz (key "tool": (S, M, 3) macro x, y, orientation).  Infrastructure for the
relinking and best-of-k comparisons (exploratory).

  python scripts/tool_runs.py --designs ibm01 --tool-seeds 0,1,2,3,4,5,6,7 --out runs/tool_runs/ibm01
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

from heurbridge.eval import cost  # noqa: E402
from heurbridge.meta import write_meta  # noqa: E402
from heurbridge.pipeline.evaluators import DreamplaceEvaluator  # noqa: E402


def main():
    from heurbridge.core import bookshelf
    from tool_refine_eval import tool_layout
    from train_bridge import SUITES, load_bundle
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--designs", required=True)
    ap.add_argument("--runs", default="runs/seed_trackA_dp")
    ap.add_argument("--tool-seeds", default="0,1,2,3,4,5,6,7")
    ap.add_argument("--select-seed", type=int, default=0)
    ap.add_argument("--eval-seeds", default="1,2,3")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    write_meta(out, "tool_runs", a.designs, config=vars(a), campaign="tool layouts per seed, selection and fresh f1")
    for name in a.designs.split(","):
        b = load_bundle(a.suite, name, a.runs)
        des = b.design
        base = cost.Baseline.from_records(des.id, json.loads((Path(a.runs) / des.id / "baseline.json").read_text())["records"])
        d, l = bookshelf.load_bookshelf(SUITES[a.suite] / name / (name + ".aux"), family=a.suite)
        work = out / "work" / des.id
        ev_sel = DreamplaceEvaluator(cluster_of=b.cluster_of, seed=a.select_seed)
        evs = [DreamplaceEvaluator(cluster_of=b.cluster_of, seed=int(s)) for s in a.eval_seeds.split(",")]
        mm = des.is_macro & ~des.is_fixed
        saved = []
        with open(out / "rows.jsonl", "a") as fh:
            for s in (int(x) for x in a.tool_seeds.split(",")):
                T, why, t_tool = tool_layout(d, l, b, s, work)
                row = {"design": des.id, "tool_seed": s, "tool_s": round(t_tool, 1), "failure": why}
                if T is None:                           # a failed tool run is recorded by name (no layout, no J_eval row)
                    fh.write(json.dumps(row) + "\n")
                    continue
                t0 = time.time()
                js = float(ev_sel.score(ev_sel.evaluate(des, T, "s%d.sel" % s, work), base).J_inf)
                t_f1 = time.time() - t0
                fresh = {e.seed: float(e.score(e.evaluate(des, T, "s%d.e%d" % (s, e.seed), work), base).J_inf) for e in evs}
                row.update({"J_select": {"tool": js}, "J_eval": {"tool": float(np.median(list(fresh.values())))},
                            "J_eval_seeds": {"tool": fresh}, "cost_s": {"tool": round(t_tool, 1), "f1": round(t_f1, 1)}})
                saved.append(np.c_[T.pos[mm], T.orient[mm]])
                fh.write(json.dumps(row) + "\n")
                fh.flush()
                print(json.dumps({k: row[k] for k in ("design", "tool_seed", "J_select", "J_eval", "cost_s")}), flush=True)
        if saved:
            np.savez(out / ("layouts_%s.npz" % des.id), tool=np.stack(saved))


if __name__ == "__main__":
    main()
