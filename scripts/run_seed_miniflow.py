#!/usr/bin/env python3
"""Track-B development seeding on an ORFS Nangate45 macro design with the local mini-flow f1.

  python scripts/run_seed_miniflow.py --design nangate45/bp_fe_top --seeds 2 --top 0 --ls 0
Baseline = tool-native macro placement (rtl_macro_placer, M1) evaluated at f1; the archive is a development
archive (fidelity 1).  Every evaluation is appended to runs/seed_miniflow/<design>/evals.jsonl (resumable).
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heurbridge.archive.store import Archive, Candidate  # noqa: E402
from heurbridge.core import orient as O  # noqa: E402
from heurbridge.core.odb import odb_to_def  # noqa: E402
from heurbridge.core.defio import load_def_design  # noqa: E402
from heurbridge.eval import cost, miniflow as MF  # noqa: E402
from heurbridge.eval.orfs import parse_macro_tcl  # noqa: E402
from heurbridge.heuristics.cell.cluster import cluster_cells  # noqa: E402
from heurbridge.heuristics.macro.registry import all_programs  # noqa: E402
from heurbridge.meta import write_meta  # noqa: E402
from heurbridge.pipeline import seed_archive as SA  # noqa: E402
from heurbridge.pipeline.evaluators import MiniflowEvaluator  # noqa: E402

FLOW = ROOT / "third_party" / "OpenROAD-flow-scripts" / "flow"
IMG = MF.DOCKER_IMAGE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", default="nangate45/bp_fe_top")
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--top", type=int, default=0)
    ap.add_argument("--ls", type=int, default=0)
    ap.add_argument("--programs", default="")
    ap.add_argument("--archive", default=str(ROOT / "archive_dev_trackB"))
    ap.add_argument("--base-runs", type=int, default=3, help="baseline flow repeats (T1.7: 3, median)")
    a = ap.parse_args()
    name = a.design.split("/")[-1]
    w = ROOT / "runs" / "miniflow" / name
    p, d = MF.Nangate45(str(FLOW)), MF.from_orfs(str(FLOW), a.design)
    if not (w / "fp.odb").exists():
        MF.run_tool("yosys", MF.synth_script(p, d, w / "synth_hier.v"), w / "synth_hier.ys")
        MF.run_tool("openroad", MF.floorplan_script(p, d, w / "synth_hier.v", w / "fp.odb"), w / "floorplan.tcl")
    if not (w / "m1_macros.tcl").exists():
        MF.run_tool("openroad", MF.m1_script(p, d, w / "fp.odb", w / "m1.odb", w / "m1_macros.tcl"), w / "m1.tcl")
    fp_def = w / "fp.hb.def"
    if not fp_def.exists():
        odb_to_def(w / "fp.odb", fp_def, docker_image=IMG)
    des, lay = load_def_design(fp_def, [str(p.tech_lef), str(p.sc_lef)] + d.macro_lefs, family="orfs_cpu", tech="nangate45")
    # M1 layout from ORFS-style place_macro commands
    m1 = lay.copy()
    idx = {n: i for i, n in enumerate(des.names)}
    for inst, (x, y, o) in parse_macro_tcl((w / "m1_macros.tcl").read_text()).items():
        i = idx[inst]
        m1.orient[i] = O.from_odb(o)
        eff = O.effective_size(des.size[i:i + 1], m1.orient[i:i + 1])[0]
        m1.pos[i] = des.to_norm(np.array([x, y]) + eff / 2)
    ev = MiniflowEvaluator(flow_dir=str(FLOW), platform_design=a.design, fp_odb=str(w / "fp.odb"), docker_image=IMG)
    out = ROOT / "runs" / "seed_miniflow"
    rdir = out / des.id
    rdir.mkdir(parents=True, exist_ok=True)
    bpath = rdir / "baseline.json"
    if bpath.exists():
        recs = json.loads(bpath.read_text())["records"]
    else:
        # M1 and f1 are deterministic at a fixed thread count, so the repeats also test determinism (T1.4)
        recs = [ev.evaluate(des, m1, "baseline_m1" + ("" if k == 0 else "_r%d" % k), rdir / "work")
                for k in range(a.base_runs)]
        keys = ("gr_wl", "gr_overflow_total", "setup_wns_ns", "setup_tns_ns", "hold_wns_ns", "total_power_w")
        same = all(r.get(k) == recs[0].get(k) for r in recs for k in keys)
        bpath.write_text(json.dumps({"records": recs, "deterministic": same, "threads": ev.threads}, indent=1, default=str))
        print(json.dumps({"baseline_runs": len(recs), "deterministic": same,
                          "values": [{k: r.get(k) for k in keys} for r in recs]}), flush=True)
    baseline = cost.Baseline.from_records(des.id, recs)
    arch = Archive(a.archive, min_fidelity=1)
    c = ev.score(recs[0], baseline)
    arch.insert(Candidate(design_id=des.id, stage="M", layout=m1, fidelity=1, J=c.J_inf, admissible=c.admissible,
                          metrics=recs[0], gates=c.gates, provenance={"program": "M1_rtl_macro_placer"}))
    cpath = rdir / "clusters.npy"
    cl = np.load(cpath) if cpath.exists() else cluster_cells(des, seed=0)
    np.save(cpath, cl)
    progs = all_programs()
    if a.programs:
        progs = [q for q in progs if q["id"] in set(a.programs.split(","))]
    write_meta(rdir, "seed_miniflow_%s" % des.id, des.id, config=vars(a), baseline=baseline.to_dict(),
               track="B-dev (local mini-flow f1, OpenLane OpenROAD b16bda7e)")
    halo = max(d.halo)
    s = SA.seed_design(des, lay, progs, ev, None, arch, baseline, out, SA.SeedConfig(seeds=a.seeds, top_f2=a.top,
                       ls_steps=a.ls, halo=halo), cluster=cl, log=lambda x: print(x, flush=True))
    print(json.dumps(s), flush=True)


if __name__ == "__main__":
    main()
