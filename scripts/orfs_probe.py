#!/usr/bin/env python3
"""Probe ORFS design-config overrides up to one stage (default: the floorplan, which ends with the PDN).

The first --variant runs synthesis; the others are seeded from its synthesis and pre-macro floorplan, so each one
re-runs only macro placement onwards.  One JSON line per variant: return code, step times, the MPL / PDN messages
and the macro geometry (distance to the core edge, smallest macro-to-macro gap).

  python scripts/orfs_probe.py --flow .../ORFS-2024-12/flow --design nangate45/ariane133 \
      --variant t1 RTLMP_MAX_LEVEL=1 'MACRO_PLACE_HALO=10 10' --variant t2 RTLMP_MAX_LEVEL=1
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heurbridge import tools  # noqa: E402
from heurbridge.eval import orfs  # noqa: E402

GEOMETRY_TCL = """read_db {odb}
set block [ord::get_db_block]
set core [$block getCoreArea]
puts "DBU [$block getDbUnitsPerMicron]"
puts "CORE [$core xMin] [$core yMin] [$core xMax] [$core yMax]"
foreach inst [$block getInsts] {{
  if {{[[$inst getMaster] isBlock]}} {{
    set b [$inst getBBox]
    puts "MACRO [$inst getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]"
  }}
}}
"""


def geometry(odb: Path) -> dict:
    """Macro count, smallest distance of a macro to each core edge and smallest macro-to-macro gap (um)."""
    with tempfile.TemporaryDirectory() as tmp:
        tcl = Path(tmp) / "geom.tcl"
        tcl.write_text(GEOMETRY_TCL.format(odb=odb))
        p = subprocess.run([tools.binary("openroad"), "-no_init", "-exit", str(tcl)], capture_output=True, text=True,
                           timeout=600)
    dbu = float(re.search(r"^DBU (\d+)", p.stdout, re.M).group(1))
    core = [int(v) / dbu for v in re.search(r"^CORE (.+)$", p.stdout, re.M).group(1).split()]
    boxes = [[int(v) / dbu for v in m.split()] for m in re.findall(r"^MACRO \S+ (.+)$", p.stdout, re.M)]
    edge = {"left": min(b[0] - core[0] for b in boxes), "bottom": min(b[1] - core[1] for b in boxes),
            "right": min(core[2] - b[2] for b in boxes), "top": min(core[3] - b[3] for b in boxes)}
    gap = float("inf")
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            dx, dy = max(b[0] - a[2], a[0] - b[2]), max(b[1] - a[3], a[1] - b[3])
            if dy < 0 <= dx:                            # facing each other across a vertical channel
                gap = min(gap, dx)
            elif dx < 0 <= dy:                          # ... across a horizontal channel
                gap = min(gap, dy)
    return {"macros": len(boxes), "core_um": core, "edge_min_um": {k: round(v, 3) for k, v in edge.items()},
            "gap_min_um": round(gap, 3)}


def step_report(log_dir: Path) -> dict:
    steps, msgs, gpl = {}, [], {}
    for log in sorted(log_dir.glob("*.log")):
        text = log.read_text(errors="replace")
        m = re.search(r"Elapsed time: (\S+)\[h:\]min:sec", text)
        steps[log.stem] = m.group(1) if m else None
        msgs += ["%s: %s" % (log.stem, l.strip()) for l in text.splitlines()
                 if re.search(r"(ERROR|WARNING) (MPL|PDN|PPL|GPL|DPL|GRT)-", l)][:8]
        if log.stem.startswith("3_3_place_gp"):         # global placement convergence
            it = re.findall(r"\[NesterovSolve\] Iter:\s*(\d+) overflow: ([0-9.]+)", text)
            fin = re.search(r"Finished with Overflow: ([0-9.]+)", text)
            gpl = {"iterations": int(it[-1][0]) if it else None, "last_overflow": float(it[-1][1]) if it else None,
                   "finished_overflow": float(fin.group(1)) if fin else None,
                   "dummies": int(re.search(r"NumDummyInstances:\s+(\d+)", text).group(1))
                   if re.search(r"NumDummyInstances:\s+(\d+)", text) else None}
    return {"steps": steps, "messages": msgs, "gpl": gpl}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--flow", required=True)
    ap.add_argument("--design", required=True, help="platform/design, e.g. nangate45/ariane133")
    ap.add_argument("--stage", default="floorplan", choices=sorted(orfs.STAGE_LAST))
    ap.add_argument("--variant", nargs="+", action="append", required=True, metavar=("NAME", "KEY=VALUE"))
    ap.add_argument("--yosys", default="")
    ap.add_argument("--work-home", default="runs/orfs_work")
    ap.add_argument("--timeout", type=float, default=3600)
    a = ap.parse_args()
    work_home = Path(a.work_home).resolve()
    first = a.variant[0][0]
    for name, *kv in a.variant:
        r = orfs.OrfsRun(flow_dir=a.flow, design_config="./designs/%s/config.mk" % a.design, variant=name,
                         stage=a.stage, threads=tools.eda_threads(8), timeout_s=a.timeout, work_home=str(work_home),
                         base_variant=first, yosys=a.yosys, make_vars_extra=tuple(kv))
        rec = orfs.run(r)
        d = r.dirs()
        out = {"variant": name, "make_vars": kv, "stage": a.stage, "returncode": rec.get("returncode"),
               "duration_s": rec.get("duration_s"), "seeded_from_base": bool(rec.get("seeded_from_base"))}
        out.update(step_report(d["logs"]))
        odb = d["results"] / "2_3_floorplan_macro.odb"
        if odb.exists():
            try:
                out["geometry"] = geometry(odb)
            except (AttributeError, ValueError, subprocess.SubprocessError) as e:
                out["geometry"] = {"error": str(e)[:200]}
        if rec.get("returncode") != 0:
            out["log_tail"] = rec.get("log_tail", "")[-600:]
        print(json.dumps(out), flush=True)


if __name__ == "__main__":
    main()
