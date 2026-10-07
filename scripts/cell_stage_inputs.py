#!/usr/bin/env python3
"""Inputs of a cell-stage recipe list, read from fetched Track-B campaigns (local; parses files, runs no tool).

  python scripts/cell_stage_inputs.py --campaigns runs/remote --out reports/cell_stage_c1_inputs.json \
      bp_fe_top:bp_fe_top.ls0.n4.f2 bp_be_top:bp_be_top.ls7.n1.f2 ...

Per design (campaign seedB_orfs7_<design>, or the one named as design:candidate:campaign):
  density       the flow's own placement density, from the baseline runs' 3_3 logs (ORFS prints how it computed it:
                third_party/ORFS-2024-12/flow/scripts/util.tcl:153-168) and gpl's uniform density (the lowest it accepts:
                third_party/OpenROAD-676f8451/src/gpl/src/nesterovBase.cpp:1654-1667)
  routability   over every 3_3 log of the campaign: how the routability loop ended, by the target RC metric
                (GPL-0077) or after three iterations without improvement, and the lowest FinalRC (GPL-0087) reached
                (third_party/OpenROAD-676f8451/src/gpl/src/routeBase.cpp:561-577, :699-710)
  wall_s        median and max wall-clock of the campaign's f1 and f2 flow runs (evals.jsonl, evals_f2.jsonl;
                rows that reused an earlier run, wall_s 0, counted apart)
  channels      per layout (M1 and the named candidate): heurbridge/cellstage/hints.channel_rects at several widths,
                as shares of the core area not covered by macros: all channel area, and the part outside ORFS's own
                channel blockage band (max(halo, channel / 2) = 10 um around every macro for these designs)
With --dreamplace DIR[,DIR]: fetched scripts/cell_positions.py jobs; per design and target density, how DREAMPlace's
runs ended (heurbridge/cellstage/positions.dreamplace_convergence on each run's log).
"""

import argparse
import json
import re
import statistics as st
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

from heurbridge.cellstage import hints as H  # noqa: E402
from heurbridge.cellstage import positions as P  # noqa: E402

GAPS = (30, 40, 50, 60, 80)
BAND_UM = 10.0


def _area(rects):
    return sum((r[2] - r[0]) * (r[3] - r[1]) for r in rects)


def density(logs):
    out = {}
    for f in logs:
        t = f.read_text(errors="replace")
        m = re.search(r"^Placement density is ([0-9.]+), computed from PLACE_DENSITY_LB_ADDON ([0-9.]+) and lower "
                      r"bound ([0-9.]+)", t, re.M)
        if m:
            out = {"density": round(float(m.group(1)), 4), "addon": float(m.group(2)),
                   "lower_bound": round(float(m.group(3)), 4)}
        else:
            m = re.search(r"^global_placement -density ([0-9.]+)", t, re.M)
            if m:
                out = {"density": float(m.group(1)), "addon": None}
        ws = re.search(r"GPL-0049\] WhiteSpaceArea:\s+([0-9.]+)", t)
        na = re.search(r"GPL-0050\] NesterovInstsArea:\s+([0-9.]+)", t)
        if ws and na:
            out["uniform_density"] = round(float(na.group(1)) / float(ws.group(1)), 4)
        out["log"] = str(f.relative_to(ROOT)) if f.is_relative_to(ROOT) else str(f)
        if "density" in out:
            return out
    return out


def routability(logs):
    ends = {"target_reached": 0, "without_improvement": 0, "no_loop": 0}
    low = {"target_reached": [], "without_improvement": []}
    for f in logs:
        t = f.read_text(errors="replace")
        rc = [float(x) for x in re.findall(r"GPL-0087\] FinalRC: ([0-9.eE+-]+)", t)]
        if not rc:
            ends["no_loop"] += 1
            continue
        k = "target_reached" if "GPL-0077]" in t else "without_improvement"
        ends[k] += 1
        low[k].append(min(rc))
    return {"logs": len(logs), "ends": ends,
            "lowest_final_rc": {k: [round(min(v), 3), round(max(v), 3)] for k, v in low.items() if v}}


def wall(path):
    """Wall-clock of the flow runs a ledger holds; rows with wall_s 0 reused an earlier run of the same layout and
    are counted apart."""
    w = [r["wall_s"] for r in (json.loads(x) for x in path.read_text().splitlines() if x.strip())
         if isinstance(r.get("wall_s"), (int, float))]
    run = [x for x in w if x > 0]
    return {"runs": len(run), "reused": len(w) - len(run), "median": round(st.median(run)) if run else None,
            "max": round(max(run)) if run else None}


def channels(d, rdir, layouts):
    import run_seed_orfs as RS
    from run_cell_stage import find_layout
    ns = SimpleNamespace(flow=str(ROOT / "third_party/ORFS-2024-12/flow"), design="nangate45/" + d,
                         work_home_abs="", yosys=None, make_var=[])
    des, lay, m1, _ = RS.load_design(ns, d, rdir, None)
    core = tuple(float(v) for v in H._snap(des.core, des))
    out = {}
    for lid in layouts:
        L, _ = find_layout(des, lay, m1, rdir, lid)
        b = [tuple(r) for r in H.macro_boxes(des, L)]
        free = (core[2] - core[0]) * (core[3] - core[1]) - _area(b)
        band = H.disjoint_union([(r[0] - BAND_UM, r[1] - BAND_UM, r[2] + BAND_UM, r[3] + BAND_UM) for r in b],
                                holes=b, box=core)
        row = {"macros": len(b), "free_area_um2": round(free), "orfs_band_share": round(_area(band) / free, 3)}
        for g in GAPS:
            rects = H.channel_rects(des, L, g)
            beyond = H.disjoint_union(rects, holes=band + b, box=core)
            row["gap_%d" % g] = {"rects": len(rects), "share": round(_area(rects) / free, 3),
                                 "share_beyond_band": round(_area(beyond) / free, 3)}
        out[lid] = row
    return out


def dreamplace_jobs(dirs):
    """{job: {"<design> <density>": summary}} over every rows.jsonl of each fetched job directory."""
    out = {}
    for job in dirs:
        job = Path(job)
        res = {}
        for rows in sorted(job.glob("**/rows.jsonl")):
            groups = {}
            for line in rows.read_text().splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                log = rows.parent / "work" / r["key"][:16] / "dreamplace.log"
                c = P.dreamplace_convergence(log.read_text(errors="replace"), 0.07) if log.exists() else None
                dens = (r.get("info") or {}).get("target_density")
                key = "%s %s" % (rows.parent.name, dens)
                groups.setdefault(key, []).append((r, c))
            for key, got in groups.items():
                cs = [c for _, c in got if c is not None and c["iterations"] is not None]
                res[key] = {"runs": len(got), "ok": sum(r.get("status") == "ok" for r, _ in got),
                            "logs": len(cs), "converged": sum(c["converged"] for c in cs),
                            "diverged": sum(c["diverged"] for c in cs),
                            "iterations": [min(c["iterations"] for c in cs), max(c["iterations"] for c in cs)] if cs else None,
                            "overflow": [round(min(c["overflow"] for c in cs), 4),
                                         round(max(c["overflow"] for c in cs), 4)] if cs else None}
        out[str(job.relative_to(ROOT)) if job.resolve().is_relative_to(ROOT) else str(job)] = res
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pairs", nargs="+", help="design:candidate layout id[:campaign run]")
    ap.add_argument("--campaigns", default=str(ROOT / "runs" / "remote"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--dreamplace", default="", help="comma-separated fetched cell_positions.py job directories")
    a = ap.parse_args()
    res = {"made_by": "scripts/cell_stage_inputs.py", "designs": {}}
    for pair in a.pairs:
        d, cand, *rest = pair.split(":")
        camp = Path(a.campaigns) / (rest[0] if rest else "seedB_orfs7_%s" % d)
        rdir = camp / "runs" / "seed_orfs" / d
        logs = sorted(camp.glob("runs/orfs_work/logs/nangate45/*/*/3_3_place_gp.log"))
        base = [f for f in logs if f.parent.name == "base"] + [f for f in logs if f.parent.name.startswith("base")]
        res["designs"][d] = {"campaign": str(rdir.relative_to(ROOT)) if rdir.is_relative_to(ROOT) else str(rdir),
                             "make_var": (json.loads((rdir / "meta.json").read_text()).get("config") or {}).get("make_var")
                             if (rdir / "meta.json").exists() else None,
                             "density": density(base or logs), "routability": routability(logs),
                             "wall_s": {"f1": wall(rdir / "evals.jsonl"), "f2": wall(rdir / "evals_f2.jsonl")},
                             "channels": channels(d, rdir, ["M1", cand])}
        print(d, json.dumps(res["designs"][d]["density"]), flush=True)
    if a.dreamplace:
        res["dreamplace"] = dreamplace_jobs([ROOT / x if not Path(x).is_absolute() else Path(x)
                                             for x in a.dreamplace.split(",") if x])
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({"out": a.out}))


if __name__ == "__main__":
    main()
