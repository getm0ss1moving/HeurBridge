#!/usr/bin/env python3
"""Offline quality of the bridge's cell sketch (and of its macros) on validation designs, against corrected targets.

For every validation source the bridge endpoint (alpha = 1, K steps) is compared with the source's paired elite, the
nearest symmetry-matched elite exactly as in training, whose cluster targets are DREAMPlace's post-placement centroids
(including the baselines' from scripts/m1_cluster_pos.py):
  cluster error  area-weighted RMS distance (normalized core units) of the cluster nodes
  macro error    area-weighted RMS distance of the movable-macro nodes
The source itself is the reference (its clusters are the quadratic placement).

--placer adds DA0 (what a hand-off would face): each model's endpoint is legalized and placed by DREAMPlace (Track-A
f1, cells from the centre as always), and its sketch is compared with the placed cluster centroids of that very
layout; the control is the quadratic placement of the same legalized macros.  The endpoint's f1 J is recorded too
(does a fine-tune keep the macro quality?).

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


def placed_da0(a, b, xs, srcs, ends, rows, name):
    """DA0 for every model endpoint (alpha 1): the sketch and the quadratic control against DREAMPlace's placement."""
    from heurbridge.bridge import handoff as H
    from heurbridge.core import project
    from heurbridge.eval import cost
    from heurbridge.pipeline.evaluators import track_a_final
    g, des = b.graph, b.design
    final = track_a_final("dreamplace", cluster_of=b.cluster_of)
    baseline = cost.Baseline.from_records(des.id, json.loads((Path(a.runs) / des.id / "baseline.json").read_text())["records"])
    pick = sorted(int(i) for i in np.random.default_rng(0).choice(len(srcs), size=min(a.da0_sources, len(srcs)), replace=False))
    for m, e in ends.items():
        for i in pick:
            pid, s, lay = srcs[i]
            rows[i][m]["da0"] = None
            dep, rep = project.legalize_macros(des, g.to_layout(e[i], lay))
            if not rep.ok:
                continue
            rec = final.evaluate(des, dep, "%s.%s.%s.s%d" % (name, m, pid, s), Path(a.work))
            if rec.get("cluster_pos") is None:
                continue
            cp = np.asarray(rec["cluster_pos"], np.float64)
            rows[i][m]["da0"] = {"sketch": H.sketch_fidelity(g, H.guarded_sketch(g, xs[i], e[i], 1.0), cp),
                                 "quad": H.sketch_fidelity(g, source_nodes(g, dep)[g.cluster_nodes], cp),
                                 "J": float(final.score(rec, baseline).J_inf)}
        d = [rows[i][m]["da0"] for i in pick if rows[i][m]["da0"]]
        print(json.dumps({"design": name, "model": m, "da0_placed": len(d),
                          "sketch_closer": sum(x["sketch"] < x["quad"] for x in d)}), flush=True)


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
    ap.add_argument("--placer", action="store_true", help="also DA0 with DREAMPlace placements (see above)")
    ap.add_argument("--work", default="runs/sketch_quality_work")
    ap.add_argument("--device", default="cpu", help="where the bridges run (cuda on a GPU server)")
    ap.add_argument("--chunk", type=int, default=16, help="sources per bridge batch (a cached design has all its "
                    "cached sources, e.g. 128, whatever --seeds says)")
    ap.add_argument("--da0-sources", type=int, default=32, help="sources per design placed for DA0: the same subset "
                    "rule as training's validation (rng 0, without replacement)")
    a = ap.parse_args()
    arch = Archive(a.archive, min_fidelity=1)
    models = {k: load_bridge(v, device=a.device) for k, v in (c.split("=", 1) for c in a.ckpt)}
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
        ends = {m: np.concatenate([bridge_endpoints(model, g, xs[i:i + a.chunk], K=a.K) for i in range(0, len(xs), a.chunk)])
                for m, model in models.items()}
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
        if a.placer:
            placed_da0(a, b, xs, srcs, ends, rows, name)
        res["cases"][name] = rows
        print(json.dumps({"design": name, "sources": len(srcs), "elites": len(elites),
                          "elites_with_override": sum(1 for e in arch.topk(b.design.id, "M", 5) if ov and int(e["id"]) in ov)}),
              flush=True)
    res["summary"] = {m: {"n": len(v["cluster"]), "cluster_median": float(np.median(v["cluster"])),
                          "cluster_mean": float(np.mean(v["cluster"])), "macro_median": float(np.median(v["macro"])),
                          "macro_mean": float(np.mean(v["macro"]))} for m, v in per.items()}
    if a.placer:
        for m in models:
            d = [r[m]["da0"] for rows in res["cases"].values() for r in rows if r[m].get("da0")]
            if d:
                res["summary"][m]["da0"] = {"n": len(d), "sketch_median": float(np.median([x["sketch"] for x in d])),
                                            "quad_median": float(np.median([x["quad"] for x in d])),
                                            "sketch_closer": int(sum(x["sketch"] < x["quad"] for x in d)),
                                            "J_median": float(np.median([x["J"] for x in d])),
                                            "failures": sum(1 for rows in res["cases"].values() for r in rows
                                                            if "da0" in r[m] and r[m]["da0"] is None)}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res["summary"]), flush=True)


if __name__ == "__main__":
    main()
