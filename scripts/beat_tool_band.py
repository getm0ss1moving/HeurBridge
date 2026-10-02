#!/usr/bin/env python3
"""Noise band of the beat-the-tool demo's best layouts (exploratory, no claim).

The registered Track-A f1 is DREAMPlace with a random seed; the same macro layout scored with other seeds moves J (the
tool's own baseline is the median over seeds 0-2 for this reason).  A layout counts as better than the tool only if
its whole band (f1 seeds 0-2) lies below the tool's band (the baseline's three records, the same seeds), the rule
Track B uses with one-site shifts.  Per design: the local-search best of scripts/beat_tool_demo.py (ls_best_<d>.npz;
seed 0 is its demo value, seeds 1-2 are scored here) and, with --bridge, the frozen bridge's guarded layout (rebuilt
deterministically from the tool's layout at the alpha the demo recorded; seeds 0-2 scored here), against the tool's
band.

  python scripts/beat_tool_band.py --demo runs/beat_tool/g0 --runs runs/seed_trackA_dp --out runs/beat_tool/g0/band.json
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
from heurbridge.pipeline.evaluators import DreamplaceEvaluator  # noqa: E402


def main():
    from train_bridge import load_bundle
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", required=True, help="output directory of scripts/beat_tool_demo.py")
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--runs", default="runs/seed_trackA_dp")
    ap.add_argument("--seeds", default="1,2", help="f1 seeds to add to the demo's seed 0")
    ap.add_argument("--bridge", default="", help="bridge checkpoint: also the band of the bridge's guarded layout")
    ap.add_argument("--K", type=int, default=20)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    demo = Path(a.demo)
    res = []
    for s in json.loads((demo / "summary.json").read_text()):
        name = s["design"]
        b = load_bundle(a.suite, name, a.runs)
        des = b.design
        rdir = Path(a.runs) / des.id
        recs = json.loads((rdir / "baseline.json").read_text())["records"]
        base = cost.Baseline.from_records(des.id, recs)
        ev0 = DreamplaceEvaluator(cluster_of=b.cluster_of)
        tool_band = sorted(float(ev0.score(r, base).J_inf) for r in recs)
        z = np.load(demo / ("ls_best_%s.npz" % des.id), allow_pickle=False)
        mm = des.is_macro & ~des.is_fixed
        lay = b.base.copy()
        lay.pos[mm], lay.orient[mm] = z["pos"], z["orient"]
        band = [float(z["J"])]
        t0 = time.time()
        for seed in (int(x) for x in a.seeds.split(",")):
            ev = DreamplaceEvaluator(cluster_of=b.cluster_of, seed=seed)
            band.append(float(ev.score(ev.evaluate(des, lay, "band.s%d" % seed, demo / "work_band" / des.id), base).J_inf))
        r = {"design": des.id, "tool_band": tool_band, "ls_band": sorted(band), "ls_seed0": band[0],
             "ls_band_below_tool_band": max(band) < min(tool_band), "ls_mean": float(np.mean(band)),
             "ls_median": float(np.median(band)), "tool_mean": float(np.mean(tool_band)),
             "tool_median": float(np.median(tool_band))}
        al = (s.get("bridge_tool") or {}).get("alpha")
        if a.bridge and al:                              # alpha 0 is the tool's layout itself: its band is the tool's
            from heurbridge.bridge.sample import bridge_endpoints, source_nodes
            from heurbridge.bridge.train import load_bridge
            from heurbridge.core import project
            zt = np.load(rdir / "m1.npz", allow_pickle=False)
            m1 = b.base.copy()
            m1.pos, m1.orient = zt["pos"], zt["orient"]
            tool, _ = project.legalize_macros(des, m1)
            x = source_nodes(b.graph, tool)
            end = bridge_endpoints(load_bridge(a.bridge), b.graph, x[None], K=a.K)[0]
            lay_b, rep = project.legalize_macros(des, b.graph.to_layout(x + al * (end - x), tool))
            bb = []
            for seed in [0] + [int(v) for v in a.seeds.split(",")]:
                ev = DreamplaceEvaluator(cluster_of=b.cluster_of, seed=seed)
                bb.append(float(ev.score(ev.evaluate(des, lay_b, "bandb.s%d" % seed, demo / "work_band" / des.id),
                                         base).J_inf))
            r.update({"bridge_alpha": al, "bridge_band": sorted(bb), "bridge_seed0": bb[0],
                      "bridge_seed0_in_demo": s["bridge_tool"]["J"],
                      "bridge_band_below_tool_band": max(bb) < min(tool_band), "bridge_mean": float(np.mean(bb)),
                      "bridge_median": float(np.median(bb))})
        r["wall_s"] = round(time.time() - t0, 1)
        res.append(r)
        print(json.dumps(r), flush=True)
    Path(a.out).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
