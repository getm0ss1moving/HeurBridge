#!/usr/bin/env python3
"""V3-style check of the pin-geometry convention against OpenROAD (closes CHANGELOG 0.1.0 finding on
eda/harness/lef_def.py): OpenDB computes every pin's location from the master's port shapes and the
instance transform; we compare its HPWL with HeurBridge's geometric convention ("centre") and with the
lef_def reproduction ("lef_def_v1").

  python scripts/verify_pin_geometry.py            # the HA-PR spm DEFs (placement, cts, routing)

OpenROAD needs technology layers to read the cell LEF; pin geometry does not depend on their electrical
data, so a minimal technology LEF with the sky130 layer and site names is generated.  Pin location =
centre of the bounding box of all port rectangles (dbITerm::getBBox / dbBTerm::getBBox), the same rule as
lef_def.lef_info.  Nets with fewer than two pins and supply nets are skipped on both sides.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heurbridge.core import defio, design as D  # noqa: E402
from heurbridge.eval.miniflow import run_tool  # noqa: E402
from heurbridge.paths import eda_dir  # noqa: E402

TECH = """VERSION 5.7 ;
BUSBITCHARS "[]" ;
DIVIDERCHAR "/" ;
UNITS
  DATABASE MICRONS 1000 ;
END UNITS
MANUFACTURINGGRID 0.005 ;
SITE unithd
  SYMMETRY Y ;
  CLASS CORE ;
  SIZE 0.46 BY 2.72 ;
END unithd
SITE unithddbl
  SYMMETRY Y ;
  CLASS CORE ;
  SIZE 0.46 BY 5.44 ;
END unithddbl
LAYER nwell
  TYPE MASTERSLICE ;
END nwell
LAYER pwell
  TYPE MASTERSLICE ;
END pwell
""" + "".join("""LAYER %s
  TYPE ROUTING ;
  DIRECTION %s ;
  PITCH %s ;
  WIDTH %s ;
END %s
%s""" % (n, d, p, w, n, ("LAYER %s\n  TYPE CUT ;\nEND %s\n" % (c, c)) if c else "")
    for n, d, p, w, c in (("li1", "VERTICAL", "0.46", "0.17", "mcon"), ("met1", "HORIZONTAL", "0.34", "0.14", "via"),
                          ("met2", "VERTICAL", "0.46", "0.14", "via2"), ("met3", "HORIZONTAL", "0.68", "0.3", "via3"),
                          ("met4", "VERTICAL", "0.92", "0.3", "via4"), ("met5", "HORIZONTAL", "3.4", "1.6", ""))) + \
    "END LIBRARY\n"

TCL = r"""
read_lef %(tech)s
read_lef %(lef)s
read_def %(def)s
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set total 0.0
set n 0
foreach net [$block getNets] {
  if {[lsearch {POWER GROUND} [$net getSigType]] >= 0} { continue }
  set xs {}
  set ys {}
  foreach it [$net getITerms] {
    set bb [$it getBBox]
    lappend xs [expr {([$bb xMin] + [$bb xMax]) / 2.0}]
    lappend ys [expr {([$bb yMin] + [$bb yMax]) / 2.0}]
  }
  foreach bt [$net getBTerms] {
    set bb [$bt getBBox]
    lappend xs [expr {([$bb xMin] + [$bb xMax]) / 2.0}]
    lappend ys [expr {([$bb yMin] + [$bb yMax]) / 2.0}]
  }
  if {[llength $xs] < 2} { continue }
  set xs [lsort -real $xs]
  set ys [lsort -real $ys]
  set total [expr {$total + ([lindex $xs end] - [lindex $xs 0]) + ([lindex $ys end] - [lindex $ys 0])}]
  incr n
}
puts "HB_HPWL_UM [expr {$total / $dbu}]"
puts "HB_NETS $n"
"""


def connectivity_only(def_text: str, masters: set) -> str:
    """Drop VIAS and SPECIALNETS, the routing of every net, and components whose master is not in the cell
    LEF (the routing DEF's sky130_ef_sc_hd fill/decap cells: no signal pins).  Placement of every other
    component, the pins and the connectivity are unchanged; generated vias would need the full technology
    LEF, and HPWL depends on none of the dropped items."""
    t = re.sub(r"^VIAS \d+ ;.*?^END VIAS\s*$", "", def_text, flags=re.M | re.S)
    m = re.search(r"^COMPONENTS \d+ ;(.*?)^END COMPONENTS", t, re.M | re.S)
    if m:
        comps = [x for x in m.group(1).split(";") if x.strip()]
        keep = [x for x in comps if x.split()[2] in masters]
        t = t[:m.start()] + "COMPONENTS %d ;" % len(keep) + "".join(x + ";" for x in keep) + "\n" + t[m.end(1):]
    t = re.sub(r"^SPECIALNETS \d+ ;.*?^END SPECIALNETS\s*$", "", t, flags=re.M | re.S)
    m = re.search(r"^NETS \d+ ;(.*?)^END NETS", t, re.M | re.S)
    if m:
        body = m.group(1)
        stmts = [x for x in body.split(";") if x.strip()]
        keep = [re.split(r"\+\s*(?:ROUTED|FIXED|COVER|NOSHIELD)\b", x, maxsplit=1)[0].rstrip() for x in stmts]
        t = t[:m.start(1)] + "\n" + " ;\n".join(keep) + " ;\n" + t[m.end(1):]
    return t


def main():
    eda = eda_dir()
    if not eda:
        sys.exit("HA-PR eda/ directory not found (HEURA_EDA_BASE)")
    lef = eda / "pdk" / "sky130A" / "sky130_fd_sc_hd.lef"
    work = ROOT / "runs" / "verify_pin_geometry"
    work.mkdir(parents=True, exist_ok=True)
    tech = work / "sky130_min_tech.lef"
    tech.write_text(TECH)
    from heurbridge._eda import harness
    lef_def = harness("lef_def")
    rows = []
    for stage in ("placement", "cts", "routing"):
        dp = eda / "openlane_runs" / "spm_phase0_0001_src" / "results" / stage / "spm.def"
        conn = work / ("spm_%s_conn.def" % stage)
        conn.write_text(connectivity_only(dp.read_text(), set(re.findall(r"^MACRO (\S+)", lef.read_text(), re.M))))
        rc, log, wall = run_tool("openroad", TCL % {"tech": tech, "lef": lef, "def": conn}, work / ("hpwl_%s.tcl" % stage),
                                 mount=str(Path.home()))
        m = re.findall(r"^HB_HPWL_UM\s+(\S+)", log, re.M)
        orr = float(m[-1]) if m else None
        des, lay = defio.load_def_design(dp, [lef])
        # the same net set as OpenROAD: signal nets with >= 2 pins (HeurBridge's hpwl skips 1-pin nets)
        ours = D.hpwl(des, lay, convention="centre")
        v1 = D.hpwl(des, lay, convention="lef_def_v1")
        ref = lef_def.def_metrics(dp, lef, 1, 1)["hpwl_um"]
        rows.append({"stage": stage, "openroad_um": orr, "heurbridge_centre_um": ours, "heurbridge_lef_def_v1_um": v1,
                     "lef_def_um": ref, "rel_centre_vs_openroad": (ours - orr) / orr if orr else None,
                     "rel_lef_def_vs_openroad": (ref - orr) / orr if orr else None, "openroad_rc": rc})
        print(json.dumps(rows[-1]), flush=True)
    out = ROOT / "reports" / "V3_pin_geometry_vs_openroad.json"
    out.write_text(json.dumps(rows, indent=1))
    print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
