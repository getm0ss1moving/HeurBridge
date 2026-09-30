#!/usr/bin/env python3
"""Offline quality of the bridge's cell sketch (and of its macros) on validation designs, against corrected targets.

For every validation source the bridge endpoint (alpha = 1, K steps) is compared with the source's paired elite, the
nearest symmetry-matched elite exactly as in training, whose cluster targets are DREAMPlace's post-placement centroids
(including the baselines' from scripts/m1_cluster_pos.py):
  cluster error  area-weighted RMS distance (normalized core units) of the cluster nodes
  macro error    area-weighted RMS distance of the movable-macro nodes
The source itself is the reference (its clusters are the quadratic placement).  No placer runs.

  python scripts/eval_sketch_quality.py --val ibm04,ibm06 --runs runs/seed_trackA_dp --archive archive_A0_trackA \
      --m1-cluster-pos runs/m1_cluster_pos --cache-dir cache --ckpt final=checkpoints/algR_trackA_final/best.pt \
      --ckpt ft_both=checkpoints/ft_both/best.pt --out reports/sketch_quality.json
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heurbridge.archive.store import Archive  # noqa: E402
from heurbridge.bridge.data import make_pair  # noqa: E402
from heurbridge.bridge.graph import KIND_CL, KIND_MOV  # noqa: E402
from heurbridge.bridge.sample import bridge_endpoints, source_nodes  # noqa: E402
from heurbridge.bridge.train import load_bridge  # noqa: E402
from heurbridge.heuristics.macro.registry import all_programs  # noqa: E402
from heurbridge.pipeline import bridge_data as BD  # noqa: E402


def rms(x, y, w):
    return float(np.sqrt((w * ((x - y) ** 2).sum(1)).sum() / max(w.sum(), 1e-12)))


def main():
    from train_bridge import load_bundle
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--val", default="ibm04,ibm06")
    ap.add_argument("--runs", default="runs/seed_trackA_dp")
    ap.add_argument("--archive", default="archive_A0_trackA")
    ap.add_argument("--m1-cluster-pos", default="")
    ap.add_argument("--cache-dir", default="cache")
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--K", type=int, default=20)
    ap.add_argument("--ckpt", action="append", default=[], help="name=path (repeatable)")
    ap.add_argument("--out", default="sketch_quality.json")
    a = ap.parse_args()
    arch = Archive(a.archive, min_fidelity=1)
    models = {k: load_bridge(v) for k, v in (c.split("=", 1) for c in a.ckpt)}
    res = {"cases": {}, "config": vars(a)}
    per = {m: {"cluster": [], "macro": []} for m in ["source"] + list(models)}
    for name in a.val.split(","):
        b = load_bundle(a.suite, name, a.runs)
        g = b.graph
        ov = None
        f = Path(a.m1_cluster_pos) / (b.design.id + ".npz") if a.m1_cluster_pos else None
        if f is not None and f.exists():
            z = np.load(f)
            ov = {int(i): z["cluster_pos"][j] for j, i in enumerate(z["elite_ids"])}
        elites = BD.archive_elites(b, arch, cluster_pos_override=ov)
        srcs = BD.run_sources(b, all_programs(), a.seeds, cache=Path(a.cache_dir))
        cl, mm = g.kind == KIND_CL, g.kind == KIND_MOV
        wc, wm = g.area_w[cl].astype(np.float64), g.area_w[mm].astype(np.float64)
        xs = np.stack([source_nodes(g, lay) for _, _, lay in srcs])
        targets = [make_pair(g, xs[i], BD.node_orient(g, lay), elites)["x1"] for i, (_, _, lay) in enumerate(srcs)]
        ends = {m: bridge_endpoints(model, g, xs, K=a.K) for m, model in models.items()}
        rows = []
        for i in range(len(srcs)):
            t = np.asarray(targets[i], np.float64)
            r = {"program": srcs[i][0], "seed": srcs[i][1],
                 "source": {"cluster": rms(xs[i][cl], t[cl], wc), "macro": rms(xs[i][mm], t[mm], wm)}}
            for m, e in ends.items():
                r[m] = {"cluster": rms(e[i][cl], t[cl], wc), "macro": rms(e[i][mm], t[mm], wm)}
            for m in per:
                per[m]["cluster"].append(r[m]["cluster"])
                per[m]["macro"].append(r[m]["macro"])
            rows.append(r)
        res["cases"][name] = rows
        print(json.dumps({"design": name, "sources": len(srcs), "elites": len(elites),
                          "elites_with_override": sum(1 for e in arch.topk(b.design.id, "M", 5) if ov and int(e["id"]) in ov)}),
              flush=True)
    res["summary"] = {m: {"n": len(v["cluster"]), "cluster_median": float(np.median(v["cluster"])),
                          "cluster_mean": float(np.mean(v["cluster"])), "macro_median": float(np.median(v["macro"])),
                          "macro_mean": float(np.mean(v["macro"]))} for m, v in per.items()}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res["summary"]), flush=True)


if __name__ == "__main__":
    main()
