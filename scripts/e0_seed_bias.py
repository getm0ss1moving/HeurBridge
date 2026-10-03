#!/usr/bin/env python3
"""Same-seed selection in E0 (audit, exploratory).

E0's co-trained partner picks its alpha among (0, 0.25, 0.5, 1.0) with the f1 run (seed 0) that also gives its final J
(scripts/run_e0.py: the guard and the final cost share one cached f1 run), while the unguarded partners (memetic,
repertoire in the spec protocol) are scored on a single draw.  The co-trained J is therefore optimistic by an unknown
amount.  This rebuilds the co-trained layout of sampled E0 units from the row's alpha (the source program re-run with
its seed, the bridge's endpoint, P_M as in run_e0.py), checks that f1 with seed 0 reproduces the row's J (else the unit
is named and left out), and scores the layout with fresh f1 seeds; optimism = the fresh-seed median minus the row's J
(positive: the recorded J was better than fresh seeds judge the same layout).

  python scripts/e0_seed_bias.py --suite ispd2005 --design adaptec1 --rows runs/e0/spec_adaptec1/e0_rows.jsonl \
      --runs runs/seed_trackA_ispd --bridge checkpoints/algR_trackA_final/best.pt --n 6 --out runs/e0_bias/adaptec1
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


def main():
    from train_bridge import load_bundle
    from heurbridge.bridge.sample import bridge_endpoints, source_nodes
    from heurbridge.bridge.train import load_bridge
    from heurbridge.core import project
    from heurbridge.eval import cost
    from heurbridge.heuristics.macro.registry import all_programs
    from heurbridge.meta import write_meta
    from heurbridge.pipeline import bridge_data as BD
    from heurbridge.pipeline.evaluators import DreamplaceEvaluator, track_a_final
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ispd2005")
    ap.add_argument("--design", required=True)
    ap.add_argument("--rows", required=True, help="E0's e0_rows.jsonl for this design")
    ap.add_argument("--runs", default="runs/seed_trackA_ispd")
    ap.add_argument("--bridge", default="checkpoints/algR_trackA_final/best.pt")
    ap.add_argument("--K", type=int, default=20)
    ap.add_argument("--n", type=int, default=6, help="units sampled (uniformly, fixed seed)")
    ap.add_argument("--eval-seeds", default="1,2,3")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    write_meta(out, "e0_seed_bias", a.design, config=vars(a), campaign="E0 same-seed selection audit (exploratory)")
    rows = [json.loads(l) for l in Path(a.rows).read_text().splitlines() if l.strip()]
    by = {}
    for r in rows:
        if r["design"] == a.design:
            by.setdefault((r["program"], r["seed"]), {})[r["partner"]] = r
    units = sorted(k for k, v in by.items() if "cotrained" in v and np.isfinite(v["cotrained"]["J"]))
    pick = np.random.default_rng(0).choice(len(units), size=min(a.n, len(units)), replace=False)
    b = load_bundle(a.suite, a.design, a.runs)
    des, g = b.design, b.graph
    base = cost.Baseline.from_records(des.id, json.loads((Path(a.runs) / des.id / "baseline.json").read_text())["records"])
    final = track_a_final("dreamplace", cluster_of=b.cluster_of)               # seed 0: E0's guard and final cost
    evs = [DreamplaceEvaluator(cluster_of=b.cluster_of, seed=int(s)) for s in a.eval_seeds.split(",")]
    model = load_bridge(a.bridge)
    progs = {p["id"]: p for p in all_programs()}
    work = out / "work"
    with open(out / "rows.jsonl", "w") as fh:
        for k in sorted(pick):
            pid, s = units[k]
            v = by[(pid, s)]
            alpha = float(v["cotrained"]["info"]["alpha"])
            row = {"design": des.id, "program": pid, "seed": s, "alpha": alpha, "J_row": v["cotrained"]["J"],
                   "J_row_partners": {p: v[p]["J"] for p in ("none", "memetic", "repertoire") if p in v}}
            srcs = [l for q, t, l in BD.run_sources(b, [progs[pid]], s + 1) if q == pid and t == s]
            if not srcs:
                row["excluded"] = "the source program did not run again"
            else:
                lay = srcs[0]
                x = source_nodes(g, lay)
                end = bridge_endpoints(model, g, x[None], K=a.K)[0]
                cand, rep = project.legalize_macros(des, g.to_layout(x + alpha * (end - x), lay))
                lp, rep2 = project.legalize_macros(des, cand)
                if not (rep.ok and rep2.ok):
                    row["excluded"] = "P_M failed on the rebuilt layout"
                else:
                    tag = "%s.s%d" % (pid, s)
                    J0 = float(final.score(final.evaluate(des, lp, tag + ".e0", work), base).J_inf)
                    row["J_seed0_rebuilt"] = J0
                    if abs(J0 - row["J_row"]) > 1e-6:                   # float rounding in the placer: below 1e-6
                        row["excluded"] = "seed-0 J not reproduced (%.6f vs %.6f)" % (J0, row["J_row"])
                    else:
                        fr = {e.seed: float(e.score(e.evaluate(des, lp, "%s.e%d" % (tag, e.seed), work), base).J_inf)
                              for e in evs}
                        med = float(np.median(list(fr.values())))
                        row.update({"J_fresh_seeds": fr, "J_fresh": med, "optimism": med - row["J_row"]})
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
