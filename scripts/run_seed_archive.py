#!/usr/bin/env python3
"""T2.7 archive-seeding campaign CLI.

Development (Track-A stand-in, local):
  python scripts/run_seed_archive.py --suite ibm --designs ibm01,ibm02 --evaluator hbgp \
      --out runs/seed_dev --archive archive_dev --min-fidelity 1
Server, Track A per spec (T1.4 / T1.6): --evaluator dreamplace (HB_DREAMPLACE = DREAMPlace install, GPU job).
Track B uses scripts/run_seed_miniflow.py.

Baseline (J normalization, T1.6: tool-native macro placement + default flow, 3 seeds, median):
  dreamplace  M1 = DREAMPlace's own mixed-size placement (macros movable; cached as m1.npz), then f1 with
              DREAMPlace seeds 0-2;
  hbgp (dev)  the benchmark's macro positions after P_M, 3 HB-GP seeds.
The programs start from the benchmark layout in both cases.  Resumable (evals.jsonl per design).
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
from heurbridge.pipeline.evaluators import DreamplaceEvaluator, HBGPEvaluator  # noqa: E402

SUITES = {"ibm": ROOT / "benchmarks" / "ibm_bookshelf", "ispd2005": ROOT / "benchmarks" / "ispd2005"}


def macro_stage_layout(design, layout):
    """Macro stage: standard cells unplaced (NaN); macros, IOs, fixed objects kept."""
    l = layout.copy()
    cells = ~design.is_macro & ~design.is_io & ~design.is_fixed
    l.pos[cells] = np.nan
    return l


class DesignFailed(RuntimeError):
    """A design whose M1 or baseline failed: reported by name, the campaign continues with the next design."""


def dreamplace_m1(design, layout, out: Path):
    """M1 for Track A, computed once per design (m1.npz): DREAMPlace mixed-size, then P_M as a legality check
    (its displacement is recorded; a failure stops the campaign)."""
    from heurbridge.eval.dreamplace import run_dreamplace_m1
    path = out / "m1.npz"
    if path.exists():
        z = np.load(path, allow_pickle=False)
        m1 = layout.copy()
        m1.pos, m1.orient = z["pos"], z["orient"]
        rec = json.loads(str(z["record"]))
    else:
        rec, m1 = run_dreamplace_m1(design, layout, out / "m1")
        if m1 is None:
            raise DesignFailed(json.dumps({"design": design.id, "error": "M1 failed", "record": rec}))
        np.savez(path, pos=m1.pos, orient=m1.orient, record=json.dumps(rec))
    bench, rep = project.legalize_macros(design, m1)
    rec = dict(rec, pm_ok=rep.ok, pm_mean_disp=rep.mean_disp)
    if not rep.ok:
        raise DesignFailed(json.dumps({"design": design.id, "error": "M1 not legal after P_M", "record": rec}))
    return bench, rep, rec


def insert_baseline_elite(arch, design, layout, records, baseline, ev):
    """Strong baselines are initial elites (proposal s.3.5: the archive can only improve on the tools)."""
    from heurbridge.archive.store import Candidate
    import statistics
    scored = [ev.score(r, baseline) for r in records]
    J = statistics.median(c.J_inf for c in scored)
    rec = dict(records[0])
    lay = layout.copy()
    if rec.get("cluster_pos") is not None:
        lay.routes = {"cluster_pos": np.asarray(rec["cluster_pos"], dtype=np.float64)}
    ok, why = arch.insert(Candidate(design_id=design.id, stage="M", layout=lay, fidelity=ev.fidelity, J=J,
                                    admissible=all(c.admissible for c in scored),
                                    metrics={k: v for k, v in rec.items() if k != "cluster_pos"},
                                    provenance={"program": "BASELINE", "evaluator": ev.name, "seeds": len(records)}))
    print(json.dumps({"baseline_elite": design.id, "J": J, "admitted": ok, "reason": why}), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm", choices=sorted(SUITES))
    ap.add_argument("--designs", required=True)
    ap.add_argument("--evaluator", default="hbgp", choices=["hbgp", "dreamplace"])
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
    failed = []
    for name in a.designs.split(","):
        try:
            run_design(a, name, progs, arch)
        except DesignFailed as e:
            print(str(e), flush=True)
            failed.append(name)
    if failed:
        print(json.dumps({"failed_designs": failed}), flush=True)
        sys.exit(1)


def run_design(a, name, progs, arch):
    """One design: M1 / baseline (3 seeds, median), baseline elite, then the seeding of T2.7."""
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
    if a.evaluator == "dreamplace":
        bench, rep, m1_rec = dreamplace_m1(d, l, out)
        ev = DreamplaceEvaluator(cluster_of=cl)
        seeded = [DreamplaceEvaluator(seed=s) for s in range(3)]
        track = "A (DREAMPlace f1; M1 = DREAMPlace mixed-size)"
    else:
        bench, rep = project.legalize_macros(d, base)
        m1_rec = None
        ev = HBGPEvaluator(cluster_of=cl)
        seeded = [HBGPEvaluator(gp_cfg=GPConfig(seed=s)) for s in range(3)]
        track = "A-dev (HB-GP stand-in)"
    bpath = out / "baseline.json"
    if bpath.exists():
        bl = json.loads(bpath.read_text())
    else:
        recs = [e.evaluate(d, bench, "baseline.s%d" % s, out) for s, e in enumerate(seeded)]
        bl = {"records": recs, "pm_ok": rep.ok, "m1": m1_rec}
        bpath.write_text(json.dumps(bl, indent=1, default=str))
    failed = [r.get("failure") for r in bl["records"] if r.get("returncode") != 0]
    if failed:                                    # the baseline is the normalizer: no partial baseline
        raise DesignFailed(json.dumps({"design": d.id, "error": "baseline failed", "failures": failed}))
    baseline = cost.Baseline.from_records(d.id, bl["records"])
    insert_baseline_elite(arch, d, bench, bl["records"], baseline, ev)
    write_meta(out, "seed_%s" % d.id, d.id, config=vars(a), seed=0, evaluator=ev.name,
               baseline=baseline.to_dict(), programs=[p["sha256"] for p in progs], track=track, record_host=True)
    cfg = SA.SeedConfig(seeds=a.seeds, top_f2=a.top, ls_steps=a.ls)
    s = SA.seed_design(d, base, progs, ev, None, arch, baseline, a.out, cfg, cluster=cl,
                       log=lambda x: print(x, flush=True))
    s["elapsed_s"] = round(time.time() - t0, 1)
    print(json.dumps(s), flush=True)


if __name__ == "__main__":
    main()
