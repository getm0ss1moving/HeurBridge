#!/usr/bin/env python3
"""T2.7 archive-seeding campaign CLI.

Development (Track-A stand-in, local):
  python scripts/run_seed_archive.py --suite ibm --designs ibm01,ibm02 --evaluator hbgp \
      --out runs/seed_dev --archive archive_dev --min-fidelity 1
Server (Track B, ORFS): --evaluator orfs --flow-dir <ORFS>/flow (f1 = grt stage, f2 = finish).

Baseline (J normalization): Track-A dev = the benchmark's macro positions after P_M, evaluated with
3 GP seeds (median); Track B = the tool-native flow (M1), 3 seeds.  Resumable (evals.jsonl per design).
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heurbridge.archive.store import Archive  # noqa: E402
from heurbridge.core import bookshelf, project  # noqa: E402
from heurbridge.eval import cost  # noqa: E402
from heurbridge.eval.gp import GPConfig  # noqa: E402
from heurbridge.heuristics.cell.cluster import cluster_cells  # noqa: E402
from heurbridge.heuristics.macro.registry import all_programs  # noqa: E402
from heurbridge.meta import write_meta  # noqa: E402
from heurbridge.pipeline import seed_archive as SA  # noqa: E402
from heurbridge.pipeline.evaluators import HBGPEvaluator  # noqa: E402

SUITES = {"ibm": ROOT / "benchmarks" / "ibm_bookshelf", "ispd2005": ROOT / "benchmarks" / "ispd2005"}


def macro_stage_layout(design, layout):
    """Macro stage: standard cells unplaced (NaN); macros, IOs, fixed objects kept."""
    l = layout.copy()
    cells = ~design.is_macro & ~design.is_io & ~design.is_fixed
    l.pos[cells] = np.nan
    return l


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm", choices=sorted(SUITES))
    ap.add_argument("--designs", required=True)
    ap.add_argument("--evaluator", default="hbgp", choices=["hbgp"])
    ap.add_argument("--out", default=str(ROOT / "runs" / "seed_dev"))
    ap.add_argument("--archive", default=str(ROOT / "archive_dev"))
    ap.add_argument("--min-fidelity", type=int, default=1)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--ls", type=int, default=8)
    ap.add_argument("--programs", default="", help="comma-separated program ids (default: all)")
    a = ap.parse_args()
    progs = all_programs()
    if a.programs:
        keep = set(a.programs.split(","))
        progs = [p for p in progs if p["id"] in keep]
    arch = Archive(a.archive, min_fidelity=a.min_fidelity)
    for name in a.designs.split(","):
        t0 = time.time()
        d, l = bookshelf.load_bookshelf(SUITES[a.suite] / name / (name + ".aux"), family=a.suite)
        if a.suite == "ispd2005":                     # MMS convention: large terminals become movable macros
            d.is_fixed = d.is_fixed & ~d.is_macro
            l.schema = d.schema_hash()
        out = Path(a.out) / d.id
        out.mkdir(parents=True, exist_ok=True)
        cpath = out / "clusters.npy"
        if cpath.exists():
            cl = np.load(cpath)
        else:
            cl = cluster_cells(d, seed=0)
            np.save(cpath, cl)
        base = macro_stage_layout(d, l)
        bench, rep = project.legalize_macros(d, base)
        ev = HBGPEvaluator(cluster_of=cl)
        bpath = out / "baseline.json"
        if bpath.exists():
            bl = json.loads(bpath.read_text())
        else:
            recs = [HBGPEvaluator(gp_cfg=GPConfig(seed=s)).evaluate(d, bench, "baseline.s%d" % s, out) for s in range(3)]
            bl = {"records": recs, "pm_ok": rep.ok}
            bpath.write_text(json.dumps(bl, indent=1, default=str))
        baseline = cost.Baseline.from_records(d.id, bl["records"])
        write_meta(out, "seed_%s" % d.id, d.id, config=vars(a), seed=0, evaluator=ev.name,
                   baseline=baseline.to_dict(), programs=[p["sha256"] for p in progs], track="A-dev (HB-GP stand-in)")
        cfg = SA.SeedConfig(seeds=a.seeds, top_f2=a.top, ls_steps=a.ls)
        s = SA.seed_design(d, base, progs, ev, None, arch, baseline, a.out, cfg, cluster=cl,
                           log=lambda x: print(x, flush=True))
        s["elapsed_s"] = round(time.time() - t0, 1)
        print(json.dumps(s), flush=True)


if __name__ == "__main__":
    main()
