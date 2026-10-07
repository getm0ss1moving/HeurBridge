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
  6. warmstart (--phase warmstart, demo) M1's replay, its shifts and the --band-top best candidates again at f1 and
             f2 with every standard cell pre-placed at its cluster's quadratic position (OrfsEvaluator warm_start):
             ORFS's first global placement then starts like the unmodified flow does from Hier-RTLMP's placement
             (evals_ws*.jsonl, run ids <design>.ws.<tag>.f1/f2, program WS_DEMO).
  5. band    (--phase band) the --band-top best f2-admitted candidates shifted by one site (+x, -x) or one row
             (+y) through f2, like M1's replays (rows <run>.p1-3.f2, program CAND_BAND): each candidate's own noise
             band, so a candidate counts as better than the tool only if its band is (user decision 2026-09-29).
  8. probe   (--phase probe, diagnosis) given f1 rows (--probe-runs, run ids of evals.jsonl) evaluated again at f1
             with extra make variables (--probe-var KEY=VALUE, e.g. PLACE_DENSITY=0.35) in their own ledger
             evals_probe_<tag>.jsonl (rows <design>.probe_<tag>.<run>.f1, program PROBE), --probe-workers at a time;
             the baselines and every other ledger are untouched.
  7. timingprobe (--phase timingprobe) the unmodified flow (ORFS's own macro placer) to 3_place in its own variant
             (<design>.tprobe), then placement-parasitic setup/hold slack at every macro signal pin
             (macro_pin_slack.json).  With --timing-weights the f1/f2 phases run a separate campaign <design>_tw
             (runs/seed_orfs/<design>_tw/): nets at critical macro pins weigh more for every program, P_M and f0
             (core/timing_weights.py); --ls-timing makes the local search accept only moves whose f1 setup and hold
             gates pass (reported, not enforced, at f1).  Replays, baselines and gate references stay shared.
"""

import argparse
import json
import math
import os
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
from heurbridge.core import timing_weights as TW  # noqa: E402
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


def shifted_m1(des, m1, dx_sites: int, dy_rows: int):
    """M1's macro layout shifted as a whole by whole sites / rows: every relative gap is kept and the macros stay
    on the placement grid, so only the core boundary and fixed objects can be violated.  Checked at zero halo (M1
    itself need not meet P_M's spacing rule); if the shift fails, the opposite direction is used; None if both fail.
    Never re-legalized: P_M would move macros far more than the one-site perturbation."""
    from heurbridge.core import project
    mm = des.is_macro & ~des.is_fixed
    w, h = des.core_wh
    sw, sh = des.site if des.site else (w / 1000.0, h / 1000.0)
    for sign in (1, -1):
        lay = m1.copy()
        lay.pos[mm] = lay.pos[mm] + sign * np.array([dx_sites * sw / w, dy_rows * sh / h])
        if project.check_macros(des, lay, 0.0)["ok"]:
            return lay
    return None


# reports/trackB_preregistration.md, Section 3: six fresh whole-layout shifts (sites, rows), the same for both arms;
# a shift that leaves the core (for either arm) is replaced by the next fallback, in order, for both arms.
TB_SHIFTS = ((2, 0), (-2, 0), (0, -1), (0, 2), (1, 1), (-1, -1))
TB_FALLBACK = ((3, 0), (-3, 0), (0, -2))


def shift_exact(des, lay0, dx_sites: int, dy_rows: int):
    """The layout's macros shifted as a whole by exactly (dx, dy) sites / rows (no change of direction, never
    re-legalized); None if that leaves the core or hits a fixed object (checked at zero halo, as shifted_m1)."""
    from heurbridge.core import project
    mm = des.is_macro & ~des.is_fixed
    w, h = des.core_wh
    sw, sh = des.site if des.site else (w / 1000.0, h / 1000.0)
    lay = lay0.copy()
    lay.pos[mm] = lay.pos[mm] + np.array([dx_sites * sw / w, dy_rows * sh / h])
    return lay if project.check_macros(des, lay, 0.0)["ok"] else None


def ext_pick(sel, f1_best):
    """The external arm's layout from its f2 runs, sel = [(J under D6, J before the gates, index)]: the best admitted;
    if none is admitted, the best J before the gates; if every f2 run failed, the best by f1.  Returns (index, rule)."""
    adm = [(j, k) for j, _, k in sel if math.isfinite(j)]
    fin = [(j, k) for _, j, k in sel if math.isfinite(j)]
    if adm:
        return min(adm)[1], "the best f2 layout admitted under D6"
    if fin:
        return min(fin)[1], "no f2 layout admitted under D6: the best f2 J before the gates"
    return f1_best, "every f2 run failed: the best by f1"


def jsafe_pick(rows, ref0, base, f1_best):
    """D13 (a), for tests registered from 7 Oct (TW#5): the external arm's layout from its f2 runs, rows = [(index, f2
    row)]: the lowest one-position J_safe against the tool's unshifted replay ``ref0`` (D11 b), ties by J; if every f2
    run failed, the best by f1.  Returns (index, rule)."""
    import timing_safety_report as TS
    fin = []
    for k, row in rows:
        s = TS.summary([TS.position(row, ref0, base)])
        if math.isfinite(s["J_safe"]):
            fin.append((s["J_safe"], s["J"], k))
    if fin:
        return min(fin)[2], "the lowest one-position J_safe (D13 a)"
    return f1_best, "every f2 run failed: the best by f1"


def tls_score(row: dict, margin: float, lam: float) -> float:
    """D13 (b): a local-search move's f1 score, J before the gates plus lam times the share of its setup and hold
    checks that do not clear the gate threshold (reference - guard) by ``margin`` ns; a failed flow is +inf."""
    if row.get("status") != "ok" or row.get("J_raw") is None or not math.isfinite(row["J_raw"]):
        return math.inf
    g = row.get("gates") or {}
    short = 0
    for k in ("setup", "hold"):
        x = g.get(k) or {}
        c, b = x.get("candidate"), x.get("base")
        short += c is None or b is None or c - (b - x.get("guard_ns", cost.GUARD_NS)) < margin - 1e-12
    return float(row["J_raw"]) + lam * short / 2.0


def tb_pairs(des, cand, ref):
    """[(slot, (dx, dy), candidate layout, reference layout)]: the pre-registered shifts with their fallbacks; a slot
    without a legal common shift has (None, None, None, None) after its index."""
    out, fb = [], list(TB_FALLBACK)
    for k, sh in enumerate(TB_SHIFTS, 1):
        while True:
            c, r = shift_exact(des, cand, *sh), shift_exact(des, ref, *sh)
            if c is not None and r is not None:
                out.append((k, sh, c, r))
                break
            if not fb:
                out.append((k, None, None, None))
                break
            sh = fb.pop(0)
    return out


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
    ap.add_argument("--phase", default="all",
                    choices=["base", "f1", "f2", "all", "band", "warmstart", "timingprobe", "probe", "tbtest", "extlayouts",
                             "tls"])
    ap.add_argument("--base-timeout", type=int, default=4 * 7200, help="whole unmodified flow (each step < 7,200 s)")
    ap.add_argument("--timeout", type=int, default=7200, help="one candidate evaluation")
    ap.add_argument("--noise-replays", type=int, default=3, help="shifted M1 replays for the noise band (0-3)")
    ap.add_argument("--band-top", type=int, default=3, help="--phase band: candidates that get their own noise band")
    ap.add_argument("--gate-reference", default="replay", choices=["replay", "base"],
                    help="timing gates vs the same-path replay band (cost_v3, default) or the unmodified flow (cost_v2)")
    ap.add_argument("--timing-weights", action="store_true",
                    help="f1/f2 as the campaign <design>_tw with critical-net weights from macro_pin_slack.json")
    ap.add_argument("--tw-beta", type=float, default=4.0, help="weight of the most critical net: 1 + beta")
    ap.add_argument("--tw-frac", type=float, default=0.1, help="nets with more setup slack than this x period: 1")
    ap.add_argument("--ls-timing", action="store_true",
                    help="local search accepts only moves whose f1 setup and hold gates pass")
    ap.add_argument("--ls-timing-margin", type=float, default=None,
                    help="with --ls-timing: both f1 slacks must clear the gate threshold by this many ns (D13 b)")
    ap.add_argument("--tls-start", default="", help="--phase tls (D13 b): the starting layout's f2 or f1 run id")
    ap.add_argument("--tls-steps", type=int, default=8)
    ap.add_argument("--tls-neighbours", type=int, default=6)
    ap.add_argument("--tls-margin", type=float, default=0.03, help="--phase tls: timing margin in ns")
    ap.add_argument("--tls-lambda", type=float, default=0.04, help="--phase tls: J added when both checks miss it")
    ap.add_argument("--tls-seed", type=int, default=1)
    ap.add_argument("--tls-workers", type=int, default=2)
    ap.add_argument("--tls-tag", default="tls", help="--phase tls: names its ledgers, run ids and programs")
    ap.add_argument("--tls-start-ledger", default="evals.jsonl", help="--phase tls: the ledger holding --tls-start")
    ap.add_argument("--tls-verify-f2", action="store_true", help="--phase tls: every kept move also at f2")
    ap.add_argument("--tls-pick", default="final", choices=["final", "jsafe"],
                    help="--phase tls: the final layout, or the lowest one-position J_safe (D13 a) to the six shifts")
    ap.add_argument("--tls-pool-ledger", default="", help="--phase tls --tls-pick jsafe: more f2 layouts to pick from")
    ap.add_argument("--tls-pool-programs", default="", help="--phase tls: their programs, comma-separated")
    ap.add_argument("--workers", type=int, default=1,
                    help="f1 and f2 evaluations at a time (distinct layouts; <= 8 OpenROAD runs on 224 in all)")
    ap.add_argument("--make-var", action="append", default=[],
                    help="KEY=VALUE override of the design config for every run (recorded in meta.json)")
    ap.add_argument("--probe-runs", default="", help="--phase probe: f1 run ids of evals.jsonl (comma separated)")
    ap.add_argument("--probe-tag", default="", help="--phase probe: names the ledger and the variants")
    ap.add_argument("--probe-var", action="append", default=[],
                    help="--phase probe: KEY=VALUE make variable for the probe runs only (after --make-var)")
    ap.add_argument("--probe-workers", type=int, default=3, help="--phase probe: ORFS runs at a time")
    ap.add_argument("--tb-candidate", default="", help="--phase tbtest: the pre-registered candidate's f2 run id")
    ap.add_argument("--tb-workers", type=int, default=4, help="--phase tbtest: f2 runs at a time (<= 8 OpenROAD)")
    ap.add_argument("--tb-arms", default="both", choices=["both", "cand"],
                    help="--phase tbtest: cand runs the candidate's shifts only (the tool's replicates exist already)")
    ap.add_argument("--tb-tag", default="", help="--phase tbtest: a later test's tag (its own ledger and run ids)")
    ap.add_argument("--ext-dir", default="", help="--phase extlayouts: an output dir of dreamplace_trackb.py place")
    ap.add_argument("--ext-tag", default="dp", help="--phase extlayouts: names the ledger and the rows")
    ap.add_argument("--ext-tb", action="store_true", help="--phase extlayouts: also the best layout's f2 shifts")
    ap.add_argument("--ext-pick", default="d6", choices=["d6", "jsafe"],
                    help="--phase extlayouts --ext-f2-top: the layout for the shifts: d6 (ext_pick, TW#1-TW#4) or jsafe "
                         "(jsafe_pick, D13 a, against the tool's unshifted replay; TW#5)")
    ap.add_argument("--ext-f2-top", type=int, default=0, help="--phase extlayouts: f2 for the best K by f1, and the "
                    "shifts for the best f2 layout admitted under the Track-B test's rule (0: the best by f1)")
    a = ap.parse_args()
    a.flow = str(Path(a.flow).resolve())
    a.work_home_abs = str(Path(a.work_home).resolve())
    name = a.design.split("/")[-1]
    cfg = "./designs/%s/config.mk" % a.design
    out = ROOT / "runs" / "seed_orfs"
    rdir = out / name
    rdir.mkdir(parents=True, exist_ok=True)
    # the Yosys ORFS runs (--yosys / HB_YOSYS), not the one on PATH (runs before 2026-09-29 recorded the PATH one)
    track = "B (ORFS 2024-12-13 8ae3ae36; %s)" % tools.describe(yosys=a.yosys or os.environ.get("HB_YOSYS"))

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
    camp, cdir, tw_info = des, rdir, None          # the campaign's design and directory (rdir unless --timing-weights)
    if a.timing_weights:
        slacks, smeta = TW.load_slacks(rdir / "macro_pin_slack.json")
        w, tw_info = TW.critical_net_weights(des, slacks, smeta["clock_period_ns"], a.tw_beta, a.tw_frac)
        camp = TW.weighted_design(des, w, tag="tw")
        camp.id = des.id + "_tw"
        cdir = out / camp.id
        cdir.mkdir(parents=True, exist_ok=True)
        tw_info["probe"] = smeta
        (cdir / "timing_weights.json").write_text(json.dumps(tw_info, indent=1, default=str))
        print(json.dumps({"timing_weights": {k: v for k, v in tw_info.items() if k != "probe"}}), flush=True)
    write_meta(cdir, "seed_orfs_%s" % camp.id, camp.id, config={k: v for k, v in vars(a).items() if k != "work_home_abs"},
               baseline=base1.to_dict(), baseline_f2=base2.to_dict(), track=track, eda_threads=tools.eda_threads(8),
               record_host=True, **({"timing_weights": tw_info} if tw_info else {}))
    if a.phase == "base":
        return
    if a.phase == "timingprobe":                        # 7. critical macro pins in the unmodified flow's placement
        probe = orfs.OrfsRun(flow_dir=a.flow, design_config=cfg, variant="%s.tprobe" % name, stage="place",
                             threads=tools.eda_threads(8), timeout_s=a.timeout, work_home=a.work_home_abs,
                             base_variant="base", yosys=a.yosys, make_vars_extra=tuple(a.make_var),
                             env={"EDA_THREADS": tools.eda_threads(8)})
        rec = orfs.run(probe)
        if rec.get("returncode") != 0:
            sys.exit("timing probe: the flow to 3_place failed: %s" % rec.get("failure"))
        pdir = rdir / "work_probe"
        pdir.mkdir(parents=True, exist_ok=True)
        slacks = orfs.macro_pin_slacks(probe, [des.names[i] for i in np.flatnonzero(des.is_macro)],
                                       pdir / "macro_pin_slack.tsv")
        period = float((base_dirs["results"] / "clock_period.txt").read_text().split()[0])
        smeta = {"variant": probe.variant, "stage": "3_place", "parasitics": "placement",
                 "macro_placement": "ORFS rtl_macro_placer (the unmodified flow)", "clock_period_ns": period,
                 "flow_s": rec.get("duration_s")}
        TW.save_slacks(rdir / "macro_pin_slack.json", slacks, smeta)
        s_ok = [v[0] for v in slacks.values() if v[0] is not None]
        print(json.dumps({"timing_probe": {"pins": len(slacks), "constrained": len(s_ok),
                                           "worst_setup_ns": min(s_ok) if s_ok else None, **smeta}}), flush=True)
        return
    if a.phase == "probe":                              # 8. diagnosis: f1 layouts again under extra make variables
        import dataclasses
        from concurrent.futures import ThreadPoolExecutor
        if not (a.probe_runs and a.probe_tag and a.probe_var):
            sys.exit("--phase probe needs --probe-runs, --probe-tag and --probe-var")
        p1 = cdir / "evals.jsonl"
        rows = {r["run_id"]: r for r in (json.loads(l) for l in (p1.read_text().splitlines() if p1.exists() else [])
                                         if l.strip())}
        evp = dataclasses.replace(ev1, make_vars_extra=tuple(a.make_var) + tuple(a.probe_var))
        ledger = Ledger(cdir / ("evals_probe_%s.jsonl" % a.probe_tag))
        jobs = []
        for rid in a.probe_runs.split(","):
            r = rows.get(rid)
            if r is None or r.get("pos_macros") is None:
                print(json.dumps({"probe": rid, "skipped": "no f1 row with a layout"}), flush=True)
                continue
            jobs.append((rid, _layout_from_row(des, lay, r), r))

        def probe_one(job):
            rid, lay_p, r = job
            pid = "%s.probe_%s.%s" % (name, a.probe_tag, rid[len(name) + 1:] if rid.startswith(name + ".") else rid)
            return rid, _eval(evp, camp, lay_p, base1, pid, cdir / "work_probe", ledger,
                              {"program": "PROBE", "probe_of": rid, "probe_of_program": r.get("program"),
                               "probe_of_status": r.get("status"), "probe_tag": a.probe_tag,
                               "probe_vars": list(a.probe_var), "seed": r.get("seed"), "stage": "M"})
        with ThreadPoolExecutor(max_workers=max(1, a.probe_workers)) as pool:
            for rid, row in pool.map(probe_one, jobs):
                print(json.dumps({"probe_of": rid, "run_id": row["run_id"], "status": row.get("status"),
                                  "J_raw": row.get("J_raw"), "failure": (row.get("record") or {}).get("failure"),
                                  "wall_s": row.get("wall_s")}), flush=True)
        return

    # 2b. same-path control (red line: pairing).  Hier-RTLMP leaves every standard cell PLACED at its cluster
    # position, a warm start for global placement that no imported macro layout gets (a candidate's cells start
    # unplaced).  M1's own layout through the candidates' path is the control their deltas are paired with.
    # 2c. noise band (the task list's "3 seeds" of the baseline; ORFS itself is deterministic): the whole M1 layout
    # shifted by one site (+x, -x) or one row (+y), through the same path.  Global placement reacts chaotically to
    # its start, so J's spread over base, replay and shifts is the band a candidate's improvement must exceed.
    replays = [("M1replay", m1)] + [("M1replay.p%d" % k, shifted_m1(des, m1, dx, dy))
                                    for k, (dx, dy) in enumerate(((1, 0), (-1, 0), (0, 1))[:a.noise_replays], 1)]
    ledgers = {led: Ledger(rdir / led) for led in ("evals.jsonl", "evals_f2.jsonl")}   # one per file: shared by threads
    jobs = []
    for tag, lay_m in replays:
        if lay_m is None:
            print(json.dumps({"m1_replay": tag, "skipped": "the shift leaves the core in both directions"}), flush=True)
            continue
        for ev, base, led, work in ((ev1, base1, "evals.jsonl", "work"), (ev2, base2, "evals_f2.jsonl", "work_f2")):
            jobs.append((tag, lay_m, ev, base, led, work))

    def replay_one(j):                                  # --workers at a time
        tag, lay_m, ev, base, led, work = j
        return _eval(ev, des, lay_m, base, "%s.%s.f%d" % (name, tag, ev.fidelity), rdir / work, ledgers[led],
                     {"program": "M1_replay", "seed": 0 if tag == "M1replay" else int(tag[-1]), "stage": "M"})
    for row in SA._map(replay_one, jobs, a.workers):
        print(json.dumps({"m1_replay": row["run_id"], "status": row.get("status"), "J": row.get("J"),
                          "J_raw": row.get("J_raw"), "wall_s": row.get("wall_s")}), flush=True)

    # 2d. cost_v3 (user decision 2026-09-29): the candidates' timing gates compare with the same-path replay band
    # (median over the replay and its shifts), not with the unmodified flow and its warm-started standard cells.
    # J stays normalized to the unmodified flow (task list T1.6).
    if a.gate_reference == "replay":
        def _replay_recs(led):
            p = rdir / led
            rr = [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
            return [r["record"] for r in rr if r.get("program") == "M1_replay" and r.get("status") == "ok"
                    and isinstance(r.get("record"), dict)]
        base1 = cost.with_gate_reference(base1, _replay_recs("evals.jsonl"))
        base2 = cost.with_gate_reference(base2, _replay_recs("evals_f2.jsonl"))
        print(json.dumps({"gate_reference": {"f1": base1.timing, "f2": base2.timing,
                                             "source": base2.sources.get("gate_reference")}}), flush=True)

    progs = all_programs()
    if a.programs:
        progs = [q for q in progs if q["id"] in set(a.programs.split(","))]
    if a.phase in ("f1", "all"):                        # 3. T2.7 at f1
        cpath = rdir / "clusters.npy"
        cl = np.load(cpath) if cpath.exists() else cluster_cells(des, seed=0)
        np.save(cpath, cl)
        halo = 2 * max(d.halo)          # P_M spacing = 2 x the per-side platform halo (see run_seed_miniflow.py)
        s = SA.seed_design(camp, lay, progs, ev1, None, arch, base1, out, SA.SeedConfig(
            seeds=a.seeds, top_f2=a.top, ls_steps=a.ls, halo=halo, ls_timing=a.ls_timing,
            ls_timing_margin=a.ls_timing_margin, workers=a.workers), cluster=cl,
            log=lambda x: print(x, flush=True))
        print(json.dumps(s), flush=True)
    if a.phase == "warmstart":                          # 6. demo: the same layouts with a standard-cell warm start
        import dataclasses
        cpath = rdir / "clusters.npy"
        cl = np.load(cpath) if cpath.exists() else cluster_cells(des, seed=0)
        ev1w = dataclasses.replace(ev1, warm_start="quadratic", cluster_of=cl)
        ev2w = dataclasses.replace(ev2, warm_start="quadratic", cluster_of=cl)
        p2 = rdir / "evals_f2.jsonl"
        rows2 = [json.loads(l) for l in p2.read_text().splitlines()] if p2.exists() else []
        cands = [SA.rescore(r, ev2, base2) for r in rows2 if r.get("program") not in ("M1_replay", "CAND_BAND")]
        best = distinct(sorted([r for r in cands if r.get("status") == "ok" and math.isfinite(r["J"])],
                               key=lambda r: r["J"]))[:a.band_top]
        items = [("M1replay", m1, "M1")] + [("M1replay.p%d" % k, shifted_m1(des, m1, dx, dy), "M1")
                                            for k, (dx, dy) in enumerate(((1, 0), (-1, 0), (0, 1)), 1)]
        items += [(r["run_id"][len(name) + 1:-3], _layout_from_row(des, lay, r), r["run_id"]) for r in best]
        for tag, lay_x, of in items:
            if lay_x is None:
                continue
            for ev, base, led, work in ((ev1w, base1, "evals_ws.jsonl", "work"), (ev2w, base2, "evals_ws_f2.jsonl", "work_f2")):
                row = _eval(ev, des, lay_x, base, "%s.ws.%s.f%d" % (name, tag, ev.fidelity), rdir / work,
                            Ledger(rdir / led), {"program": "WS_DEMO", "tag": tag, "of": of, "stage": "M"})
                print(json.dumps({"warm_start": row["run_id"], "status": row.get("status"), "J_raw": row.get("J_raw"),
                                  "failure": (row.get("record") or {}).get("failure")}), flush=True)
    if a.phase == "band":                               # 5. the best candidates' own noise band at f2
        p2 = rdir / "evals_f2.jsonl"
        rows2 = [json.loads(l) for l in p2.read_text().splitlines()] if p2.exists() else []
        cands = [SA.rescore(r, ev2, base2) for r in rows2 if r.get("program") not in ("M1_replay", "CAND_BAND")]
        best = distinct(sorted([r for r in cands if r.get("status") == "ok" and math.isfinite(r["J"])],
                               key=lambda r: r["J"]))[:a.band_top]
        ledger = Ledger(p2)
        for r in best:
            lay_r = _layout_from_row(des, lay, r)
            for k, (dx, dy) in enumerate(((1, 0), (-1, 0), (0, 1)), 1):
                lay_s = shifted_m1(des, lay_r, dx, dy)
                if lay_s is None:
                    print(json.dumps({"band_of": r["run_id"], "shift": k, "skipped": "leaves the core"}), flush=True)
                    continue
                row = _eval(ev2, des, lay_s, base2, "%s.p%d.f2" % (r["run_id"][:-3], k), rdir / "work_f2", ledger,
                            {"program": "CAND_BAND", "seed": k, "stage": "M", "band_of": r["run_id"],
                             "band_of_program": r.get("program")})
                print(json.dumps({"band_of": r["run_id"], "run_id": row["run_id"], "status": row.get("status"),
                                  "J": row.get("J"), "J_raw": row.get("J_raw")}), flush=True)
    if a.phase == "tbtest":                             # 9. Track-B confirmatory test (reports/trackB_preregistration.md)
        from concurrent.futures import ThreadPoolExecutor
        p2 = rdir / "evals_f2.jsonl"
        rows2 = {r["run_id"]: r for r in (json.loads(l) for l in (p2.read_text().splitlines() if p2.exists() else [])
                                          if l.strip())}
        r = rows2.get(a.tb_candidate)
        if r is None or r.get("pos_macros") is None:
            sys.exit("--phase tbtest: no f2 row with a layout for --tb-candidate %r" % a.tb_candidate)
        # --tb-tag names a later test's own ledger and rows (evals_tb_<tag>.jsonl, <design>.tb_<tag>.<arm>.s<k>.f2,
        # TB_<TAG>_CAND); --tb-arms cand runs the candidate only, against the tool's replicates of an earlier test
        tag = ("_" + a.tb_tag) if a.tb_tag else ""
        ledger = Ledger(rdir / ("evals_tb%s.jsonl" % tag))
        jobs = []
        for k, sh, c, m in tb_pairs(des, _layout_from_row(des, lay, r), m1):
            if sh is None:
                print(json.dumps({"tb_slot": k, "skipped": "no legal common shift left"}), flush=True)
                continue
            jobs += [("cand", k, sh, c)] + ([("ref", k, sh, m)] if a.tb_arms == "both" else [])

        def tb_one(job):
            arm, k, sh, lay_x = job
            return job, _eval(ev2, des, lay_x, base2, "%s.tb%s.%s.s%d.f2" % (name, tag, arm, k), rdir / "work_tb", ledger,
                              {"program": "TB%s_%s" % (tag.upper(), arm.upper()), "tb_slot": k, "tb_shift": list(sh),
                               "stage": "M", "tb_candidate": a.tb_candidate})
        with ThreadPoolExecutor(max_workers=max(1, min(8, a.tb_workers))) as pool:
            for (arm, k, sh, _), row in pool.map(tb_one, jobs):
                print(json.dumps({"tb": arm, "slot": k, "shift": sh, "run_id": row["run_id"], "status": row.get("status"),
                                  "J": row.get("J"), "J_raw": row.get("J_raw"), "wall_s": row.get("wall_s")}), flush=True)
        return
    if a.phase == "extlayouts":                         # 10. external macro layouts (e.g. DREAMPlace's) through the flow
        from concurrent.futures import ThreadPoolExecutor
        ed = Path(a.ext_dir)
        z = np.load(ed / "layouts.npz")
        meta = {r["index"]: r for r in (json.loads(l) for l in (ed / "rows.jsonl").read_text().splitlines() if l.strip())
                if "index" in r}
        idx = {n: i for i, n in enumerate(des.names)}
        mm = des.is_macro & ~des.is_fixed
        order = np.array([idx[str(n)] for n in z["names"]])          # macros by name: the export's order need not match
        if set(order) != set(np.flatnonzero(mm)):
            sys.exit("--phase extlayouts: the layouts' macros differ from the design's movable macros")
        lays = []
        for k in range(len(z["macros"])):
            lx = lay.copy()
            lx.pos[order] = z["macros"][k][:, :2]
            lx.orient[order] = z["macros"][k][:, 2].astype(np.int8)
            lays.append((k, lx))
        ledger = Ledger(rdir / ("evals_ext_%s.jsonl" % a.ext_tag))
        tagp = "EXT_" + a.ext_tag.upper()

        def f1_one(job):
            k, lx = job
            r = meta.get(k, {})
            return k, _eval(ev1, des, lx, base1, "%s.ext_%s.td%g.s%s.f1" % (name, a.ext_tag, r.get("target_density", -1), r.get("seed", k)),
                            rdir / "work_ext", ledger, {"program": tagp, "ext_index": k, "target_density": r.get("target_density"),
                                                         "seed": r.get("seed"), "stage": "M"})
        with ThreadPoolExecutor(max_workers=max(1, min(8, a.tb_workers))) as pool:
            res = list(pool.map(f1_one, lays))
        for k, row in res:
            print(json.dumps({"ext": k, "run_id": row["run_id"], "status": row.get("status"), "J_raw": row.get("J_raw")}), flush=True)
        ok = [(row.get("J_raw"), k) for k, row in res if row.get("status") == "ok" and row.get("J_raw") is not None
              and math.isfinite(row["J_raw"])]
        if not ok:
            sys.exit("--phase extlayouts: no external layout completed f1")
        best = min(ok)[1]                                           # by f1 J before the gates, as the campaign's f2 pick
        print(json.dumps({"ext_best": best, "f1_J_raw": min(ok)[0], "meta": meta.get(best)}), flush=True)
        if a.ext_f2_top > 0:                                        # the campaign's second stage: f2 for the best few by
            top = [k for _, k in sorted(ok)[:a.ext_f2_top]]          # f1, then the best f2 layout admitted under the
                                                                    # Track-B test's rule (D6: no timing sign rule)
            def f2_one(k):
                r = meta.get(k, {})
                return k, _eval(ev2, des, lays[k][1], base2, "%s.ext_%s.td%g.s%s.f2" % (name, a.ext_tag, r.get("target_density", -1), r.get("seed", k)),
                                rdir / "work_ext", ledger, {"program": tagp + "_F2", "ext_index": k, "target_density": r.get("target_density"),
                                                             "seed": r.get("seed"), "stage": "M"})
            with ThreadPoolExecutor(max_workers=max(1, min(8, a.tb_workers))) as pool:
                res2 = list(pool.map(f2_one, top))
            sel = []
            for k, row in res2:
                rec = row.get("record") if isinstance(row.get("record"), dict) else {}
                c = cost.evaluate(rec, base2, fidelity=2, timing_sign_rule=False) \
                    if row.get("status") == "ok" and rec.get("returncode") in (0, None) and rec else None
                jd6 = c.J_inf if c is not None else math.inf
                jb = c.J if c is not None and math.isfinite(c.J) else math.inf
                sel.append((jd6, jb, k))
                print(json.dumps({"ext_f2": k, "run_id": row["run_id"], "status": row.get("status"), "J_d6": jd6,
                                  "J_before_gates": jb}), flush=True)
            if a.ext_pick == "jsafe":
                p2 = rdir / "evals_f2.jsonl"
                ref0 = next(r["record"] for r in (json.loads(l) for l in p2.read_text().splitlines() if l.strip())
                            if r["run_id"] == "%s.M1replay.f2" % name)
                best, why = jsafe_pick(res2, ref0, base2, best)
            else:
                best, why = ext_pick(sel, best)
            print(json.dumps({"ext_pick": best, "rule": why, "meta": meta.get(best)}), flush=True)
        if a.ext_tb:
            jobs = []
            for k, sh, c, m in tb_pairs(des, lays[best][1], m1):
                if sh is None:
                    print(json.dumps({"tb_slot": k, "skipped": "no legal common shift left"}), flush=True)
                    continue
                jobs.append((k, sh, c))

            def tb_one(job):
                k, sh, lx = job
                return job, _eval(ev2, des, lx, base2, "%s.ext_%s.tb.s%d.f2" % (name, a.ext_tag, k), rdir / "work_ext", ledger,
                                  {"program": tagp + "_TB", "tb_slot": k, "tb_shift": list(sh), "ext_index": best, "stage": "M"})
            with ThreadPoolExecutor(max_workers=max(1, min(8, a.tb_workers))) as pool:
                for (k, sh, _), row in pool.map(tb_one, jobs):
                    print(json.dumps({"ext_tb": k, "shift": sh, "run_id": row["run_id"], "status": row.get("status"),
                                      "J": row.get("J"), "J_raw": row.get("J_raw")}), flush=True)
        return
    if a.phase == "tls":                                # 11. local search from a given layout (D13 b; D12 b)
        # --tls-tag names the ledgers, run ids and programs (default tls: evals_tls.jsonl, <d>.tls.s<k>.n<i>.f1, TLS);
        # --tls-lambda 0 is the campaign's local search (J only); --tls-verify-f2 checks every kept move at f2;
        # --tls-pick jsafe sends the lowest one-position J_safe (D13 a, against the tool's unshifted replay, D11 b) of
        # the pool's f2 layouts and the checked moves to the six shifts, else the final layout
        from heurbridge.core import project
        tag, TAG = a.tls_tag, a.tls_tag.upper()
        p1 = rdir / a.tls_start_ledger
        rows1 = {r["run_id"]: r for r in (json.loads(l) for l in p1.read_text().splitlines() if l.strip())}
        start = rows1.get(a.tls_start[:-3] + ".f1") if a.tls_start.endswith(".f2") else rows1.get(a.tls_start)
        if start is None or start.get("pos_macros") is None:
            sys.exit("--phase tls: no f1 row with a layout for --tls-start %r in %s" % (a.tls_start, p1.name))
        halo = 2 * max(d.halo)
        ledger = Ledger(rdir / ("evals_%s.jsonl" % tag))
        ledger2 = Ledger(rdir / ("evals_%s_f2.jsonl" % tag))
        rng = np.random.default_rng(a.tls_seed)
        cur_lay, cur = _layout_from_row(des, lay, start), tls_score(start, a.tls_margin, a.tls_lambda)
        print(json.dumps({"tls_start": start["run_id"], "score": cur, "J_raw": start.get("J_raw")}), flush=True)
        checked = []
        for step in range(a.tls_steps):
            jobs = []
            for n, (move, l) in enumerate(SA.neighbours(des, cur_lay, rng, a.tls_neighbours)):
                lp, rep = project.legalize_macros(des, l, halo=halo)
                if rep.ok:
                    jobs.append(("%s.%s.s%d.n%d.f1" % (name, tag, step, n), lp, move))
            evals = SA._map(lambda j: _eval(ev1, des, j[1], base1, j[0], rdir / ("work_%s" % tag), ledger,
                                            {"program": TAG, "move": j[2], "stage": "M", "tls_step": step}),
                            jobs, a.tls_workers)
            scored = sorted(((tls_score(r, a.tls_margin, a.tls_lambda), i) for i, r in enumerate(evals)), key=lambda t: t[0])
            took = bool(scored) and scored[0][0] < cur
            if took:
                cur, cur_lay = scored[0][0], jobs[scored[0][1]][1]
                if a.tls_verify_f2:
                    checked.append(_eval(ev2, des, cur_lay, base2, "%s.%s.s%d.f2" % (name, tag, step),
                                         rdir / ("work_%s" % tag), ledger2, {"program": TAG + "_F2", "stage": "M",
                                                                            "tls_step": step}))
            print(json.dumps({"tls_step": step, "evaluated": len(evals), "best": scored[0][0] if scored else None,
                              "accepted": took, "score": cur, "run_id": jobs[scored[0][1]][0] if took else None}),
                  flush=True)
        if a.tls_pick == "jsafe":
            import timing_safety_report as TS
            p2 = rdir / "evals_f2.jsonl"
            ref0 = next(r["record"] for r in (json.loads(l) for l in p2.read_text().splitlines() if l.strip())
                        if r["run_id"] == "%s.M1replay.f2" % name)
            pool = []
            if a.tls_pool_ledger:
                progs = set(a.tls_pool_programs.split(","))
                pool = [r for r in (json.loads(l) for l in (rdir / a.tls_pool_ledger).read_text().splitlines() if l.strip())
                        if r.get("program") in progs and r.get("pos_macros") is not None]
            cands = [(TS.summary([TS.position(r, ref0, base2)]), r) for r in pool + checked if r.get("pos_macros") is not None]
            if not cands:
                sys.exit("--phase tls --tls-pick jsafe: no f2 layout to pick from")
            best_s, best_r = min(cands, key=lambda t: (t[0]["J_safe"], t[0]["J"]))
            cur_lay = _layout_from_row(des, lay, best_r)
            print(json.dumps({"tls_pick": best_r["run_id"], "J_safe": best_s["J_safe"], "J": best_s["J"],
                              "marks": best_s["marks"], "pool": len(pool), "checked": len(checked)}), flush=True)
        jobs = []
        for k, sh, c, m in tb_pairs(des, cur_lay, m1):      # the layout at the Track-B test's six shifts
            if sh is None:
                print(json.dumps({"tb_slot": k, "skipped": "no legal common shift left"}), flush=True)
            else:
                jobs.append((k, sh, c))
        for (k, sh, _), row in zip(jobs, SA._map(lambda j: _eval(
                ev2, des, j[2], base2, "%s.%s.tb.s%d.f2" % (name, tag, j[0]), rdir / ("work_%s" % tag), ledger2,
                {"program": TAG + "_TB", "tb_slot": j[0], "tb_shift": list(j[1]), "stage": "M"}), jobs, a.tls_workers)):
            print(json.dumps({"tls_tb": k, "shift": sh, "run_id": row["run_id"], "status": row.get("status"),
                              "J_raw": row.get("J_raw")}), flush=True)
        return
    if a.phase in ("f2", "all"):                        # 4. f2 verification
        ev_path = cdir / "evals.jsonl"
        rows = [json.loads(l) for l in ev_path.read_text().splitlines()] if ev_path.exists() else []
        ledger = Ledger(cdir / "evals_f2.jsonl")
        done = 0
        chosen = select(rows, a.top, a.spread)

        def f2_one(r):                                  # --workers at a time; distinct layouts (select)
            return _eval(ev2, des, _layout_from_row(des, lay, r), base2, r["run_id"][:-3] + ".f2", cdir / "work_f2",
                         ledger, {"program": r.get("program"), "seed": r.get("seed"), "stage": "M", "f1_J": r["J"],
                                  "f1_J_raw": r["J_raw"], "f1_run_id": r["run_id"]})
        for r, row in zip(chosen, SA._map(f2_one, chosen, a.workers)):
            lay_r = _layout_from_row(des, lay, r)
            rid = r["run_id"][:-3] + ".f2"
            done += 1
            if row.get("status") == "ok" and math.isfinite(row["J"]):
                arch.insert(Candidate(design_id=camp.id, stage="M", layout=lay_r, fidelity=2, J=row["J"],
                                      admissible=row.get("admissible", False), metrics=row.get("record", {}),
                                      gates=row.get("gates", {}), provenance={"program": r.get("program"),
                                                                               "seed": r.get("seed"), "run_id": rid,
                                                                               "f1_run_id": r["run_id"]}))
            print(json.dumps({"run_id": rid, "status": row.get("status"), "f1_J_raw": r["J_raw"], "f2_J": row.get("J"),
                              "f2_J_raw": row.get("J_raw")}), flush=True)
        print(json.dumps({"f2_done": done, "snapshot": arch.snapshot("B0_%s" % camp.id)}), flush=True)


if __name__ == "__main__":
    main()
