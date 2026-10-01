#!/usr/bin/env python3
"""Why do Track-B candidates fail?  Logs and macro geometry of ORFS seeding campaigns (diagnostic, no claim).

For every f1 row of runs/seed_orfs/<design>/evals.jsonl, from the variant's ORFS logs
(<work-home>/logs/<platform>/<nickname>/<run_id>/):
  last step     the last step log that exists and how it ends (elapsed time, last error)
  rows          floorplan rows after the tapcell step's row cutting (ODB-0303 when printed)
  gpl           target density, final overflow, divergence messages
  resizer       buffers inserted, instances resized, utilization after repair_design
  dpl           instances detailed placement could not place (and the first names), displacement statistics
and, from the macro layout: gaps between facing macros and to the core edge, against ORFS's channel blockage
(``block_channels``: every macro bloated by max(halo, channel / 2) as a soft placement blockage), i.e. the free strip
a channel leaves for standard cells.  Writes <out>/rows.jsonl and <out>/summary.md (counts per design and failure).

  python scripts/diag_trackb_failures.py --designs ariane133,ariane136 --flow <ORFS>/flow --out runs/diag_trackb
"""

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ERR = re.compile(r"\[ERROR (\w+-\d+)\] ([^\n]*)")
WARN = re.compile(r"\[WARNING (\w+-\d+)\]")
ELAPSED = re.compile(r"Elapsed time: ([\d:.]+)")
ROWS = re.compile(r"The initial (\d+) rows \((\d+) sites\) were cut with (\d+) shapes for a total of (\d+) rows "
                  r"\((\d+) sites\)")
TAPS = re.compile(r"Inserted (\d+) (endcaps|tapcells)")
DENS = re.compile(r"target density:?\s*([\d.]+)", re.I)
OVF = re.compile(r"overflow:\s*([\d.]+)", re.I)
UTIL = re.compile(r"Design area ([\d.]+) u\^2 ([\d.]+)% utilization")
BUF = re.compile(r"Inserted (\d+) (?:input |output )?buffers")
RESZ = re.compile(r"Resized (\d+) instances")
DPL_FAIL = re.compile(r"failed on the following (\d+) instances", re.I)
DISP = re.compile(r"^\s*(total|average|max) displacement\s+([\d.]+)", re.I | re.M)


def step_logs(d: Path) -> list:
    return sorted(p for p in d.glob("*.log") if re.match(r"\d_\d", p.name))


def tail(p: Path, n: int = 4000) -> str:
    b = p.read_bytes()
    return b[-n:].decode("utf-8", "replace")


def parse_variant(d: Path) -> dict:
    """Facts from one variant's ORFS step logs."""
    out = {"logs": [p.name for p in step_logs(d)]}
    if not out["logs"]:
        return out
    last = step_logs(d)[-1]
    t = tail(last)
    out["last_step"] = last.name[:-4]
    out["last_elapsed"] = (ELAPSED.findall(t) or [None])[-1]
    out["last_errors"] = ["%s %s" % e for e in ERR.findall(t)][-3:]
    out["last_lines"] = [l for l in t.strip().splitlines() if l.strip()][-3:]
    for p in step_logs(d):
        txt = p.read_text("utf-8", "replace")
        name = p.name[:-4]
        w = Counter(WARN.findall(txt))
        if w:
            out.setdefault("warnings", {})[name] = dict(w.most_common(6))
        m = ROWS.findall(txt)
        if m:
            r0, s0, shapes, r1, s1 = map(int, m[-1])
            out["rows"] = {"initial": r0, "initial_sites": s0, "cut_shapes": shapes, "rows": r1, "sites": s1}
        m = TAPS.findall(txt)
        if m:
            out.setdefault("taps", {}).update({k: int(v) for v, k in m})
        if name.startswith("3_3"):
            dn, ov = DENS.findall(txt), OVF.findall(txt)
            out["gpl"] = {"target_density": float(dn[-1]) if dn else None,
                          "final_overflow": float(ov[-1]) if ov else None,
                          "divergence": len(re.findall(r"divergence", txt, re.I)),
                          "elapsed": (ELAPSED.findall(txt) or [None])[-1]}
        if name.startswith("3_4"):
            u = UTIL.findall(txt)
            out["resizer"] = {"buffers": sum(int(x) for x in BUF.findall(txt)),
                              "resized": sum(int(x) for x in RESZ.findall(txt)),
                              "area_um2": float(u[-1][0]) if u else None, "util_pct": float(u[-1][1]) if u else None}
        if name.startswith("2_1"):
            u = UTIL.findall(txt)
            if u:
                out["util_floorplan_pct"] = float(u[-1][1])
        if name.startswith("3_5"):
            f = DPL_FAIL.findall(txt)
            names = []
            if f:
                after = txt.split(DPL_FAIL.search(txt).group(0), 1)[1].splitlines()[1:40]
                names = [l.strip() for l in after if l.strip() and not l.lstrip().startswith("[")][:12]
            out["dpl"] = {"failed_instances": int(f[-1]) if f else 0, "first_failed": names,
                          "displacement": {k.lower(): float(v) for k, v in DISP.findall(txt)},
                          "errors": ["%s %s" % e for e in ERR.findall(txt)][-3:],
                          "elapsed": (ELAPSED.findall(txt) or [None])[-1], "log_bytes": p.stat().st_size}
    return out


def gaps(des, lay, blockage_um: float) -> dict:
    """Gaps (um) between facing movable/fixed macros and from macros to the core edge.  ``strip`` = gap - 2 x the
    channel blockage (between macros) or gap - blockage (to the edge): the width left free for standard cells."""
    from heurbridge.core import orient as O
    mi = np.flatnonzero(des.is_macro)
    w, h = des.core_wh
    eff = O.effective_size(des.size[mi], lay.orient[mi])                     # um
    c = lay.pos[mi] * np.array([w, h])                                         # centre in um from the core origin
    lo, hi = c - eff / 2, c + eff / 2
    strips = []
    n = len(mi)
    for i in range(n):
        for j in range(i + 1, n):
            ov_y = min(hi[i, 1], hi[j, 1]) - max(lo[i, 1], lo[j, 1])          # facing horizontally
            ov_x = min(hi[i, 0], hi[j, 0]) - max(lo[i, 0], lo[j, 0])          # facing vertically
            if ov_y > 0:
                gx = max(lo[j, 0] - hi[i, 0], lo[i, 0] - hi[j, 0])
                if gx >= 0:
                    strips.append(("x", gx, ov_y))
            if ov_x > 0:
                gy = max(lo[j, 1] - hi[i, 1], lo[i, 1] - hi[j, 1])
                if gy >= 0:
                    strips.append(("y", gy, ov_x))
    # keep each macro's nearest facing neighbour per side only (a far macro behind a near one is not a channel)
    edge = np.concatenate([lo[:, 0], lo[:, 1], w - hi[:, 0], h - hi[:, 1]])
    g = np.array([s[1] for s in strips]) if strips else np.zeros(0)
    free = g - 2 * blockage_um
    e_free = edge - blockage_um
    return {"macros": int(n), "pairs_facing": int(len(g)),
            "min_gap_um": float(g.min()) if len(g) else None,
            "channels_blocked": int(np.sum((free <= 0) & (g < 4 * blockage_um))),
            "channels_sliver_lt5um": int(np.sum((free > 0) & (free < 5.0))),
            "channels_5_20um": int(np.sum((free >= 5.0) & (free < 20.0))),
            "edge_gaps_sliver_lt5um": int(np.sum((e_free > 0) & (e_free < 5.0))),
            "macro_area_frac": float(np.prod(eff, axis=1).sum() / (w * h)),
            "bbox_frac": float(np.prod(hi.max(0) - lo.min(0)) / (w * h)),
            "touch_edge_frac": float(np.mean(np.minimum.reduce([lo[:, 0], lo[:, 1], w - hi[:, 0], h - hi[:, 1]])
                                             < blockage_um + 1e-6))}


def load_design(flow: str, design: str, cdir: Path):
    from heurbridge.core.defio import load_def_design
    from heurbridge.eval import miniflow as MF
    p, d = MF.Nangate45(flow), MF.from_orfs(flow, "nangate45/" + design)
    return load_def_design(cdir / "fp.hb.def", [str(p.tech_lef), str(p.sc_lef)] + d.macro_lefs, design_id=design,
                           family="orfs_cpu", tech="nangate45")


def m1_layout(des, lay, cdir: Path):
    from heurbridge.core import orient as O
    from heurbridge.eval import orfs
    cmds = orfs.parse_macro_tcl((cdir / "m1_macros.tcl").read_text())
    m1 = lay.copy()
    idx = {n: i for i, n in enumerate(des.names)}
    for inst, (x, y, o) in cmds.items():
        i = idx[inst]
        m1.orient[i] = O.from_odb(o)
        eff = O.effective_size(des.size[i:i + 1], m1.orient[i:i + 1])[0]
        m1.pos[i] = des.to_norm(np.array([x, y]) + eff / 2)
    return m1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--designs", required=True)
    ap.add_argument("--campaigns", default=str(ROOT / "runs" / "seed_orfs"))
    ap.add_argument("--work-home", default=str(ROOT / "runs" / "orfs_work"))
    ap.add_argument("--platform", default="nangate45")
    ap.add_argument("--flow", default="", help="ORFS flow dir (for the LEFs of the geometry check; empty: skip it)")
    ap.add_argument("--blockage-um", type=float, default=10.0, help="max(halo, channel / 2) of the design config")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows_all, md = [], ["# Track-B failure diagnosis", ""]
    for design in a.designs.split(","):
        cdir = Path(a.campaigns) / design
        ev = cdir / "evals.jsonl"
        if not ev.exists():
            md += ["## %s" % design, "", "no evals.jsonl under %s" % cdir, ""]
            continue
        rows = [json.loads(l) for l in ev.read_text().splitlines() if l.strip()]
        logroot = Path(a.work_home) / "logs" / a.platform / design
        des = base = None
        if a.flow:
            try:
                from heurbridge.pipeline.seed_archive import _layout_from_row
                des, base = load_design(a.flow, design, cdir)
            except Exception as e:                                   # geometry is optional; the logs are the point
                print("geometry skipped for %s: %s: %s" % (design, type(e).__name__, e), flush=True)
        agg = defaultdict(list)
        for r in rows:
            rid = r.get("run_id", "")
            if not rid.endswith(".f1"):
                continue
            rec = {"design": design, "run_id": rid, "program": r.get("program"), "status": r.get("status"),
                   "failure": r.get("failure"), "J_raw": r.get("J_raw"), "duration_s": r.get("duration_s")}
            vd = logroot / rid
            rec.update(parse_variant(vd) if vd.is_dir() else {"logs": [], "no_log_dir": str(vd)})
            if des is not None and r.get("pos_macros") is not None:
                rec["geometry"] = gaps(des, _layout_from_row(des, base, r), a.blockage_um)
            if des is not None and r.get("program") == "M1_replay":
                rec["geometry"] = gaps(des, m1_layout(des, base, cdir), a.blockage_um)
            rows_all.append(rec)
            key = "ok" if r.get("status") == "ok" else (r.get("failure") or "failed (no reason)")
            agg[key].append(rec)
        md += ["## %s" % design, "", "| outcome | n | last step (most common) | gpl overflow | buffers | util after "
               "resize % | DPL failed inst. | rows after cut | slivers <5 um | min gap um |", "|---|---|---|---|---|---|---|---|---|---|"]

        def med(v):
            v = [x for x in v if x is not None and not (isinstance(x, float) and math.isnan(x))]
            return "%.4g" % float(np.median(v)) if v else "-"
        for key, rs in sorted(agg.items(), key=lambda kv: -len(kv[1])):
            steps = Counter(x.get("last_step") for x in rs).most_common(2)
            md.append("| %s | %d | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                key[:60], len(rs), ", ".join("%s (%d)" % s for s in steps),
                med([(x.get("gpl") or {}).get("final_overflow") for x in rs]),
                med([(x.get("resizer") or {}).get("buffers") for x in rs]),
                med([(x.get("resizer") or {}).get("util_pct") for x in rs]),
                med([(x.get("dpl") or {}).get("failed_instances") for x in rs]),
                med([(x.get("rows") or {}).get("rows") for x in rs]),
                med([(x.get("geometry") or {}).get("channels_sliver_lt5um") for x in rs]),
                med([(x.get("geometry") or {}).get("min_gap_um") for x in rs])))
        md.append("")
    with open(out / "rows.jsonl", "w") as fh:
        for r in rows_all:
            fh.write(json.dumps(r, default=str) + "\n")
    (out / "summary.md").write_text("\n".join(md) + "\n")
    print("\n".join(md), flush=True)


if __name__ == "__main__":
    main()
