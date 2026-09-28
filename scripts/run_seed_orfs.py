#!/usr/bin/env python3
"""Track-B seeding on the ORFS flow (T1.7 baselines, T2.7 seeding, f2 verification).

OpenROAD-flow-scripts at 2024-12-13 (8ae3ae36) with the OpenROAD commit it pins (676f8451, built from source:
scripts/server/build_openroad.sh) and its Yosys (0.48): the tool-native flow of the task spec.  --make-var overrides
a design-config value for every run (ariane133: the RTLMP settings upstream adopted later for MPL convergence).

  python scripts/run_seed_orfs.py --flow <ORFS>/flow --design nangate45/bp_fe_top --seeds 5 --top 10 --ls 8 \
      --spread 10 [--base-runs 2] [--work-home runs/orfs_work] [--phase f1|f2|all]

Resumable; everything lands in runs/seed_orfs/<design>/:
  1. base    the unmodified ORFS flow to 6_report (M1 = ORFS's rtl_macro_placer), --base-runs times: the
             repeats test determinism.  Its grt-stage metrics are the f1 baseline, its finish metrics the f2
             baseline (baseline.json / baseline_f2.json).
  2. design  our Design from the pre-macro floorplan (2_2_floorplan_io.odb -> DEF); M1 from 2_3 (m1_macros.tcl).
  3. f1      every program x seed (P_M-legalized) as an ORFS variant to 5_1_grt, starting from the base synthesis
             and pre-macro floorplan; local search around the best (evals.jsonl).
  4. f2      the --top distinct f1 layouts and --spread more across the f1 ranking to 6_report (evals_f2.jsonl);
             every f2-admissible layout enters the archive at fidelity 2.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heurbridge import tools  # noqa: E402
from heurbridge.archive.store import Archive, Candidate  # noqa: E402
from heurbridge.core import orient as O  # noqa: E402
from heurbridge.core.defio import load_def_design  # noqa: E402
from heurbridge.core.odb import odb_to_def  # noqa: E402
from heurbridge.eval import cost, miniflow as MF, orfs  # noqa: E402
from heurbridge.heuristics.cell.cluster import cluster_cells  # noqa: E402
from heurbridge.heuristics.macro.registry import all_programs  # noqa: E402
from heurbridge.meta import write_meta  # noqa: E402
from heurbridge.pipeline import seed_archive as SA  # noqa: E402
from heurbridge.pipeline.evaluators import OrfsEvaluator  # noqa: E402
from heurbridge.pipeline.seed_archive import Ledger, _eval, _layout_from_row, distinct  # noqa: E402

KEYS_F1 = ("gr_wl", "gr_overflow_total", "setup_wns_ns", "setup_tns_ns", "hold_wns_ns", "total_power_w")
KEYS_F2 = ("detailed_wirelength_um", "vias", "drc_violations", "setup_wns_ns", "setup_tns_ns", "hold_wns_ns",
           "total_power_w")


def base_runs(a, cfg, work_home, n):
    """The unmodified ORFS flow n times (variants base, base_r1, ...): f2 records, then f1 records of the same runs."""
    f1, f2 = [], []
    for k in range(n):
        v = "base" if k == 0 else "base_r%d" % k
        r = orfs.OrfsRun(flow_dir=a.flow, design_config=cfg, variant=v, stage="finish", threads=tools.eda_threads(8),
                         timeout_s=a.base_timeout, work_home=str(work_home), yosys=a.yosys,
                         make_vars_extra=tuple(a.make_var))
        rec2 = orfs.run(r)
        rec2["run_id"] = v + ".f2"
        r.stage = "grt"
        rec1 = orfs.run(r)                              # up to date: make does nothing, grt-stage metrics only
        rec1["run_id"] = v + ".f1"
        for rec in (rec1, rec2):
            if rec.get("returncode") == 0 and rec.get("setup_wns_ns") is None:
                rec["returncode"], rec["failure"] = "no_metrics", "ORFS metrics missing"
        f1.append(rec1)
        f2.append(rec2)
        print(json.dumps({"base": v, "f2": {k: rec2.get(k) for k in KEYS_F2}, "f1": {k: rec1.get(k) for k in KEYS_F1},
                          "returncode": rec2.get("returncode"), "duration_s": rec2.get("duration_s")}), flush=True)
    return f1, f2


def load_design(a, name, rdir, base_run_dirs):
    """Design from the pre-macro floorplan; M1 layout from ORFS's macro stage."""
    p, d = MF.Nangate45(a.flow), MF.from_orfs(a.flow, a.design)
    fp_def = rdir / "fp.hb.def"
    if not fp_def.exists():
        odb_to_def(base_run_dirs["results"] / "2_2_floorplan_io.odb", fp_def)
    des, lay = load_def_design(fp_def, [str(p.tech_lef), str(p.sc_lef)] + d.macro_lefs, design_id=name,
                               family="orfs_cpu", tech="nangate45")
    m1_tcl = rdir / "m1_macros.tcl"
    if not m1_tcl.exists():
        r = orfs.OrfsRun(flow_dir=a.flow, design_config="./designs/%s/config.mk" % a.design, variant="base",
                         work_home=a.work_home_abs, yosys=a.yosys, make_vars_extra=tuple(a.make_var))
        orfs.extract_macros(r, base_run_dirs, m1_tcl)
    cmds = orfs.parse_macro_tcl(m1_tcl.read_text())
    if len(cmds) != int(des.is_macro.sum()):
        sys.exit("m1_macros.tcl places %d macros, the design has %d" % (len(cmds), int(des.is_macro.sum())))
    m1 = lay.copy()
    idx = {n: i for i, n in enumerate(des.names)}
    for inst, (x, y, o) in cmds.items():
        i = idx[inst]
        m1.orient[i] = O.from_odb(o)
        eff = O.effective_size(des.size[i:i + 1], m1.orient[i:i + 1])[0]
        m1.pos[i] = des.to_norm(np.array([x, y]) + eff / 2)
    return des, lay, m1, d


def select(rows, top, spread):
    """--top best distinct f1 layouts (by J before the gates) and --spread more evenly across the rest."""
    fin = distinct(sorted([r for r in rows if r.get("status") == "ok" and r.get("J_raw") is not None
                           and math.isfinite(r["J_raw"]) and r["run_id"].endswith(".f1")
                           and r.get("program") != "M1_replay"], key=lambda r: r["J_raw"]))
    pick, rest = fin[:top], fin[top:]
    if spread and rest:
        idx = np.unique(np.linspace(0, len(rest) - 1, min(spread, len(rest))).round().astype(int))
        pick += [rest[i] for i in idx]
    return pick


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--flow", required=True, help="ORFS flow directory (2024-12 checkout)")
    ap.add_argument("--design", default="nangate45/bp_fe_top")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--spread", type=int, default=10)
    ap.add_argument("--ls", type=int, default=8)
    ap.add_argument("--programs", default="")
    ap.add_argument("--archive", default=str(ROOT / "archive_B0_orfs"))
    ap.add_argument("--base-runs", type=int, default=2, help="repeats of the unmodified flow (determinism check)")
    ap.add_argument("--work-home", default=str(ROOT / "runs" / "orfs_work"))
    ap.add_argument("--yosys", default=None, help="Yosys for ORFS (default HB_YOSYS)")
    ap.add_argument("--phase", default="all", choices=["base", "f1", "f2", "all"])
    ap.add_argument("--base-timeout", type=int, default=4 * 7200, help="whole unmodified flow (each step < 7,200 s)")
    ap.add_argument("--timeout", type=int, default=7200, help="one candidate evaluation")
    ap.add_argument("--make-var", action="append", default=[],
                    help="KEY=VALUE override of the design config for every run (recorded in meta.json)")
    a = ap.parse_args()
    a.flow = str(Path(a.flow).resolve())
    a.work_home_abs = str(Path(a.work_home).resolve())
    name = a.design.split("/")[-1]
    cfg = "./designs/%s/config.mk" % a.design
    out = ROOT / "runs" / "seed_orfs"
    rdir = out / name
    rdir.mkdir(parents=True, exist_ok=True)
    track = "B (ORFS 2024-12-13 8ae3ae36; %s)" % tools.describe()

    # 1. baselines
    bpath, b2path = rdir / "baseline.json", rdir / "baseline_f2.json"
    if not (bpath.exists() and b2path.exists()):
        f1r, f2r = base_runs(a, cfg, a.work_home_abs, a.base_runs)
        for path, recs, keys in ((bpath, f1r, KEYS_F1), (b2path, f2r, KEYS_F2)):
            ok = [r for r in recs if r.get("returncode") == 0]
            same = len(ok) == len(recs) and all(r.get(k) == ok[0].get(k) for r in ok for k in keys)
            path.write_text(json.dumps({"records": recs, "deterministic": same, "threads": tools.eda_threads(8)},
                                       indent=1, default=str))
    recs1 = [r for r in json.loads(bpath.read_text())["records"] if r.get("returncode") == 0]
    recs2 = [r for r in json.loads(b2path.read_text())["records"] if r.get("returncode") == 0]
    if not recs1 or not recs2:
        print(json.dumps({"error": "ORFS baseline failed", "records": json.loads(b2path.read_text())["records"]},
                         default=str)[:3000], flush=True)
        sys.exit(1)
    base_dirs = orfs.OrfsRun(flow_dir=a.flow, design_config=cfg, variant="base", work_home=a.work_home_abs,
                             yosys=a.yosys, make_vars_extra=tuple(a.make_var)).dirs()
    des, lay, m1, d = load_design(a, name, rdir, base_dirs)
    for kv in a.make_var:                               # P_M spacing follows an overridden halo too
        k, _, v = kv.partition("=")
        if k == "MACRO_PLACE_HALO":
            d.halo = tuple(float(x) for x in v.split()[:2])
    ev1 = OrfsEvaluator(fidelity=1, flow_dir=a.flow, design_config=cfg, work_home=a.work_home_abs, base_variant="base",
                        yosys=a.yosys, timeout_s=a.timeout, make_vars_extra=tuple(a.make_var))
    ev2 = OrfsEvaluator(fidelity=2, flow_dir=a.flow, design_config=cfg, work_home=a.work_home_abs, base_variant="base",
                        yosys=a.yosys, timeout_s=a.timeout, make_vars_extra=tuple(a.make_var))
    base1, base2 = cost.Baseline.from_records(des.id, recs1), cost.Baseline.from_records(des.id, recs2)
    arch = Archive(a.archive, min_fidelity=1)
    for ev, rec, fid in ((ev1, recs1[0], 1), (ev2, recs2[0], 2)):
        c = ev.score(rec, base1 if fid == 1 else base2)
        arch.insert(Candidate(design_id=des.id, stage="M", layout=m1, fidelity=fid, J=c.J_inf, admissible=c.admissible,
                              metrics=rec, gates=c.gates, provenance={"program": "M1_orfs_rtl_macro_placer"}))
    write_meta(rdir, "seed_orfs_%s" % des.id, des.id, config={k: v for k, v in vars(a).items() if k != "work_home_abs"},
               baseline=base1.to_dict(), baseline_f2=base2.to_dict(), track=track, eda_threads=tools.eda_threads(8),
               record_host=True)
    if a.phase == "base":
        return

    # 2b. same-path control (red line: pairing).  Hier-RTLMP leaves every standard cell PLACED at its cluster
    # position, a warm start for global placement that no imported macro layout gets (a candidate's cells start
    # unplaced).  M1's own layout through the candidates' path is the control their deltas are paired with.
    for ev, base, led, work in ((ev1, base1, "evals.jsonl", "work"), (ev2, base2, "evals_f2.jsonl", "work_f2")):
        row = _eval(ev, des, m1, base, "%s.M1replay.f%d" % (name, ev.fidelity), rdir / work, Ledger(rdir / led),
                    {"program": "M1_replay", "seed": 0, "stage": "M"})
        print(json.dumps({"m1_replay": row["run_id"], "status": row.get("status"), "J": row.get("J"),
                          "J_raw": row.get("J_raw"), "wall_s": row.get("wall_s")}), flush=True)

    progs = all_programs()
    if a.programs:
        progs = [q for q in progs if q["id"] in set(a.programs.split(","))]
    if a.phase in ("f1", "all"):                        # 3. T2.7 at f1
        cpath = rdir / "clusters.npy"
        cl = np.load(cpath) if cpath.exists() else cluster_cells(des, seed=0)
        np.save(cpath, cl)
        halo = 2 * max(d.halo)          # P_M spacing = 2 x the per-side platform halo (see run_seed_miniflow.py)
        s = SA.seed_design(des, lay, progs, ev1, None, arch, base1, out, SA.SeedConfig(
            seeds=a.seeds, top_f2=a.top, ls_steps=a.ls, halo=halo), cluster=cl, log=lambda x: print(x, flush=True))
        print(json.dumps(s), flush=True)
    if a.phase in ("f2", "all"):                        # 4. f2 verification
        ev_path = rdir / "evals.jsonl"
        rows = [json.loads(l) for l in ev_path.read_text().splitlines()] if ev_path.exists() else []
        ledger = Ledger(rdir / "evals_f2.jsonl")
        done = 0
        for r in select(rows, a.top, a.spread):
            lay_r = _layout_from_row(des, lay, r)
            rid = r["run_id"][:-3] + ".f2"
            row = _eval(ev2, des, lay_r, base2, rid, rdir / "work_f2", ledger,
                        {"program": r.get("program"), "seed": r.get("seed"), "stage": "M", "f1_J": r["J"],
                         "f1_J_raw": r["J_raw"], "f1_run_id": r["run_id"]})
            done += 1
            if row.get("status") == "ok" and math.isfinite(row["J"]):
                arch.insert(Candidate(design_id=des.id, stage="M", layout=lay_r, fidelity=2, J=row["J"],
                                      admissible=row.get("admissible", False), metrics=row.get("record", {}),
                                      gates=row.get("gates", {}), provenance={"program": r.get("program"),
                                                                               "seed": r.get("seed"), "run_id": rid,
                                                                               "f1_run_id": r["run_id"]}))
            print(json.dumps({"run_id": rid, "status": row.get("status"), "f1_J_raw": r["J_raw"], "f2_J": row.get("J"),
                              "f2_J_raw": row.get("J_raw")}), flush=True)
        print(json.dumps({"f2_done": done, "snapshot": arch.snapshot("B0_%s" % des.id)}), flush=True)


if __name__ == "__main__":
    main()
