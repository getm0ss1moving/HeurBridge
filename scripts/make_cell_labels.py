#!/usr/bin/env python3
"""Cell-stage labels for the look-ahead predictor (sketch redesign S2): DREAMPlace's placement of many macro layouts.

Macro layouts per design, each legalized by P_M:
  src  every cached heuristic source (with the training cache: 128 per design, whatever --seeds says)
  br   the bridge's endpoint of a fixed subset of sources (--bridge-sources; training's validation rule), guarded at
       each alpha in --alphas
  el   the archive's top-k elites
Each is placed by the Track-A f1 evaluator (DREAMPlace GP + LG, macros fixed; --cpu where there is no GPU) and
labelled with heurbridge.bridge.lookahead: cluster centroids, second moments and areas, the cell-density map, the f1
record (terms and J), and the placed cells (float16) for labels not thought of yet.

Resumable: one file per placement under <out>/parts/<design>/; <out>/<design>.npz collects a finished design.

  python scripts/make_cell_labels.py --designs ibm01,... --runs runs/seed_trackA_dp --archive archive_A0_trackA \
      --cache-dir <cache> --bridge checkpoints/algR_trackA_final/best.pt --workers 14 --cpu --out runs/cell_labels
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heurbridge.archive.store import Archive  # noqa: E402
from heurbridge.bridge import lookahead as LA  # noqa: E402
from heurbridge.bridge.sample import bridge_endpoints, source_nodes  # noqa: E402
from heurbridge.bridge.train import load_bridge  # noqa: E402
from heurbridge.core import project  # noqa: E402
from heurbridge.eval import cost  # noqa: E402
from heurbridge.heuristics.macro.registry import all_programs  # noqa: E402
from heurbridge.meta import write_meta  # noqa: E402
from heurbridge.pipeline import bridge_data as BD  # noqa: E402
from heurbridge.pipeline.evaluators import DreamplaceEvaluator  # noqa: E402


def macro_layouts(b, arch, model, a):
    """[(id, kind, meta, layout)] for one design, in a fixed order."""
    g, des = b.graph, b.design
    out = []
    srcs = BD.run_sources(b, all_programs(), a.seeds, cache=Path(a.cache_dir))
    for pid, s, lay in srcs:
        out.append(("src.%s.s%d" % (pid, s), "src", {"program": pid, "seed": s}, lay))
    if model is not None and a.bridge_sources > 0:
        pick = sorted(int(i) for i in np.random.default_rng(0).choice(len(srcs), size=min(a.bridge_sources, len(srcs)),
                                                                        replace=False))
        xs = np.stack([source_nodes(g, srcs[i][2]) for i in pick])
        ends = np.concatenate([bridge_endpoints(model, g, xs[j:j + 16], K=a.K) for j in range(0, len(xs), 16)])
        for k, i in enumerate(pick):
            pid, s, lay = srcs[i]
            for al in (float(x) for x in a.alphas.split(",")):
                cand, rep = project.legalize_macros(des, g.to_layout(xs[k] + al * (ends[k] - xs[k]), lay))
                if rep.ok:
                    out.append(("br.%s.s%d.a%g" % (pid, s, al), "br", {"program": pid, "seed": s, "alpha": al}, cand))
    for e in arch.topk(des.id, "M", a.elites):
        lay, rep = project.legalize_macros(des, arch.layout(e))
        if rep.ok:
            out.append(("el.%d" % int(e["id"]), "el", {"elite": int(e["id"]), "J_archive": float(e["J"]),
                                                       "program": (e.get("provenance") or {}).get("program")}, lay))
    return out


def label_one(ev, b, baseline, sid, kind, meta, lay, work, part):
    des = b.design
    t0 = time.time()
    rec, placed = ev.evaluate_placed(des, lay, sid, work)
    row = {"id": sid, "kind": kind, **meta, "failure": rec.get("failure") or (None if placed is not None else "no_placement"),
           "runtime_s": rec.get("runtime_s"), "wall_s": None}
    arrays = {}
    if placed is not None:
        c = ev.score(rec, baseline)
        row.update({"J": float(c.J_inf), "J_raw": float(c.J), "terms": {t: v.get("raw") for t, v in c.terms.items()},
                    "gp_overflow": rec.get("gp_overflow")})
        pos, cov, area = LA.cluster_moments(des, placed, b.cluster_of)
        cm = LA.cell_mask(des, placed, b.cluster_of)
        mm = des.is_macro & ~des.is_fixed
        arrays = {"cluster_pos": pos.astype(np.float32), "cluster_cov": cov.astype(np.float32),
                  "cluster_area": area.astype(np.float32),
                  "density": LA.density_map(des, placed, b.cluster_of).astype(np.float16),
                  "cells": placed.pos[cm].astype(np.float16), "cell_index": np.flatnonzero(cm).astype(np.int32),
                  "macros": np.asarray(lay.pos[mm], np.float32), "macro_orient": np.asarray(lay.orient[mm], np.int8)}
    row["wall_s"] = round(time.time() - t0, 1)
    tmp = part.with_suffix(".tmp.npz")
    np.savez(tmp, row=np.array(json.dumps(row, default=str)), **arrays)
    tmp.rename(part)
    return row


def collect(parts_dir: Path, out_file: Path) -> int:
    rows, arr = [], {}
    for f in sorted(parts_dir.glob("*.npz")):
        if f.name.endswith(".tmp.npz"):
            continue
        z = np.load(f, allow_pickle=False)
        r = json.loads(str(z["row"]))
        if "cluster_pos" not in z.files:
            rows.append(r)
            continue
        r["k"] = len([x for x in rows if "k" in x])
        rows.append(r)
        for k in z.files:
            if k != "row":
                arr.setdefault(k, []).append(z[k])
    np.savez(out_file, rows=np.array(json.dumps(rows, default=str)),
             **{k: np.stack(v) for k, v in arr.items() if k not in ("cluster_area", "cell_index")},
             cluster_area=arr["cluster_area"][0] if arr else np.zeros(0), cell_index=arr["cell_index"][0] if arr else np.zeros(0))
    return len(rows)


def main():
    from train_bridge import load_bundle
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--designs", required=True)
    ap.add_argument("--runs", default="runs/seed_trackA_dp")
    ap.add_argument("--archive", default="archive_A0_trackA")
    ap.add_argument("--cache-dir", required=True)
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--bridge", default="checkpoints/algR_trackA_final/best.pt")
    ap.add_argument("--bridge-sources", type=int, default=32)
    ap.add_argument("--alphas", default="0.25,0.5,0.75,1")
    ap.add_argument("--K", type=int, default=20)
    ap.add_argument("--elites", type=int, default=5)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--cpu", action="store_true", help="DREAMPlace on the CPU (servers without a usable GPU)")
    ap.add_argument("--limit", type=int, default=0, help="first N layouts per design (0 = all; for smoke runs)")
    ap.add_argument("--out", default="runs/cell_labels")
    a = ap.parse_args()
    import torch
    torch.set_num_threads(2)                                    # the placements run in parallel subprocesses
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    write_meta(out, "cell_labels", a.designs, config=vars(a), campaign="sketch redesign S2 labels")
    arch = Archive(a.archive, min_fidelity=1)
    model = load_bridge(a.bridge) if a.bridge and a.bridge_sources > 0 else None
    for name in a.designs.split(","):
        b = load_bundle(a.suite, name, a.runs)
        des = b.design
        if (out / (des.id + ".npz")).exists():
            print(json.dumps({"design": name, "skip": "done"}), flush=True)
            continue
        baseline = cost.Baseline.from_records(des.id, json.loads((Path(a.runs) / des.id / "baseline.json").read_text())["records"])
        ev = DreamplaceEvaluator(cluster_of=b.cluster_of, gpu=not a.cpu)
        todo = macro_layouts(b, arch, model, a)
        if a.limit:
            todo = todo[:a.limit]
        parts = out / "parts" / des.id
        parts.mkdir(parents=True, exist_ok=True)
        work = out / "work" / des.id
        pending = [t for t in todo if not (parts / (t[0] + ".npz")).exists()]
        print(json.dumps({"design": name, "layouts": len(todo), "pending": len(pending),
                          "kinds": {k: sum(1 for t in todo if t[1] == k) for k in ("src", "br", "el")}}), flush=True)
        t0, done, failed = time.time(), 0, 0
        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            futs = [pool.submit(label_one, ev, b, baseline, sid, kind, meta, lay, work, parts / (sid + ".npz"))
                    for sid, kind, meta, lay in pending]
            for f in as_completed(futs):
                r = f.result()
                done += 1
                failed += r["failure"] is not None
                if done % 20 == 0 or done == len(futs):
                    print(json.dumps({"design": name, "done": done, "of": len(futs), "failed": failed,
                                      "elapsed_s": round(time.time() - t0)}), flush=True)
        n = collect(parts, out / (des.id + ".npz"))
        print(json.dumps({"design": name, "collected": n, "wall_s": round(time.time() - t0)}), flush=True)


if __name__ == "__main__":
    main()
