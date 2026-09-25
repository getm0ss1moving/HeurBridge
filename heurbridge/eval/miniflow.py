"""Minimal Nangate45 flow without ORFS/make (Track B development + fallback if ORFS and the installed
OpenROAD disagree).  Uses only commands verified by the T0.3 probe.

  synth       Yosys: read RTL + fakeram liberty as black boxes, flatten, map to NangateOpenCellLibrary
  floorplan   read LEF/liberty/netlist/SDC, initialize_floorplan (utilization), make_tracks, IO constraints,
              place_pins, tapcells -> fp.odb
  m1          tool-native macro placement: rtl_macro_placer (Hier-RTLMP) with the platform halo -> m1.odb,
              macro placement written as Tcl (the M1 seed layout)
  f1          fp.odb + our macro placement (place_macro, FIRM) -> platform RC -> global_placement
              (routability- and timing-driven) -> detailed_placement -> check_placement ->
              estimate_parasitics -placement -> setup/hold slack -> global_route (30 congestion iterations)
              -> estimate_parasitics -global_routing -> slack, power -> f1 DEF
Outputs the f1 JSON of eval/f1.py (parse_f1_log) plus power.  Timing: sta::worst_slack -max = setup WNS
(worst_slack_max), -min = hold; sta::total_negative_slack -max = setup TNS (METRIC_CONVENTIONS).
"""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from .f1 import parse_f1_log

DOCKER_IMAGE = "efabless/openlane:master-arm64v8"


@dataclass
class Nangate45:
    flow_dir: str            # .../OpenROAD-flow-scripts/flow

    @property
    def pdir(self) -> Path:
        return Path(self.flow_dir) / "platforms" / "nangate45"

    tech_lef = property(lambda s: s.pdir / "lef" / "NangateOpenCellLibrary.tech.lef")
    sc_lef = property(lambda s: s.pdir / "lef" / "NangateOpenCellLibrary.macro.mod.lef")
    lib = property(lambda s: s.pdir / "lib" / "NangateOpenCellLibrary_typical.lib")
    set_rc = property(lambda s: s.pdir / "setRC.tcl")
    tapcell = property(lambda s: s.pdir / "tapcell.tcl")
    site = "FreePDK45_38x28_10R_NP_162NW_34O"
    min_layer, max_layer = "metal2", "metal10"
    io_h, io_v = "metal5", "metal6"


@dataclass
class DesignCfg:
    name: str                          # ORFS design dir name, e.g. bp_fe_top
    top: str
    verilog: list
    sdc: str
    macro_lefs: list = field(default_factory=list)
    macro_libs: list = field(default_factory=list)
    utilization: float = 50.0
    place_density: float = 0.6
    halo: tuple = (10.0, 10.0)
    io_tcl: str | None = None
    fastroute_tcl: str | None = None


def from_orfs(flow_dir: str, platform_design: str) -> DesignCfg:
    """Parse the subset of an ORFS config.mk this flow needs (e.g. 'nangate45/bp_fe_top')."""
    ddir = Path(flow_dir) / "designs" / platform_design
    txt = (ddir / "config.mk").read_text()
    txt = re.sub(r"\\\n\s*", " ", txt)

    def get(k, default=None):
        m = re.search(r"^export\s+%s\s*\??=\s*(.+)$" % k, txt, re.M)
        return m.group(1).strip() if m else default
    subst = {"$(DESIGN_HOME)": str(Path(flow_dir) / "designs"), "$(PLATFORM)": "nangate45",
             "$(PLATFORM_DIR)": str(Path(flow_dir) / "platforms" / "nangate45"), "$(DESIGN_NAME)": get("DESIGN_NAME", ""),
             "$(DESIGN_NICKNAME)": get("DESIGN_NICKNAME", get("DESIGN_NAME", ""))}

    def expand(v):
        for a, b in subst.items():
            v = v.replace(a, b)
        return v
    ver = [expand(v) for v in (get("VERILOG_FILES") or "").split()]
    halo = tuple(float(x) for x in (get("MACRO_PLACE_HALO") or "10 10").split()[:2])
    return DesignCfg(name=ddir.name, top=get("DESIGN_NAME"), verilog=ver,
                     sdc=expand(get("SDC_FILE") or str(ddir / "constraint.sdc")),
                     macro_lefs=[expand(v) for v in (get("ADDITIONAL_LEFS") or "").split()],
                     macro_libs=[expand(v) for v in (get("ADDITIONAL_LIBS") or "").split()],
                     utilization=float(get("CORE_UTILIZATION") or 50), place_density=float(get("PLACE_DENSITY") or 0.6),
                     halo=halo, io_tcl=expand(get("IO_CONSTRAINTS")) if get("IO_CONSTRAINTS") else None,
                     fastroute_tcl=expand(get("FASTROUTE_TCL")) if get("FASTROUTE_TCL") else None)


def synth_script(p: Nangate45, d: DesignCfg, out_v: Path, flatten: bool = False) -> str:
    """Hierarchical by default (ORFS SYNTH_HIERARCHICAL=1): Hier-RTLMP clusters by the logical hierarchy and
    this OpenROAD build crashes in TritonPart when it has to split one large flat cluster."""
    lines = ["read_liberty -lib %s" % l for l in d.macro_libs]
    lines += ["read_verilog -defer -sv %s" % v for v in d.verilog]
    lines += ["hierarchy -top %s" % d.top, "synth -top %s%s" % (d.top, " -flatten" if flatten else ""),
              "dfflibmap -liberty %s" % p.lib, "abc -liberty %s" % p.lib,
              "hilomap -singleton -hicell LOGIC1_X1 Z -locell LOGIC0_X1 Z", "setundef -zero", "splitnets",
              "opt_clean -purge", "write_verilog -noattr -noexpr -nohex -nodec %s" % out_v]
    return "\n".join(lines) + "\n"


def _reads(p: Nangate45, d: DesignCfg) -> str:
    lefs = [p.tech_lef, p.sc_lef] + d.macro_lefs
    libs = [p.lib] + d.macro_libs
    return "\n".join(["read_lef %s" % l for l in lefs] + ["read_liberty %s" % l for l in libs])


def io_exclusions(io_tcl: str | None) -> str:
    """Translate ORFS ``exclude_io_pin_region -region edge:range`` (newer OpenROAD) into the older
    ``place_pins -exclude edge:range`` arguments."""
    if not io_tcl or not Path(io_tcl).exists():
        return ""
    regs = re.findall(r"-region\s+(\S+)", Path(io_tcl).read_text())
    return " ".join("-exclude %s" % r for r in regs)


def floorplan_script(p: Nangate45, d: DesignCfg, netlist: Path, out_odb: Path) -> str:
    return "\n".join([
        _reads(p, d), "read_verilog %s" % netlist, "link_design %s" % d.top, "read_sdc %s" % d.sdc,
        "initialize_floorplan -utilization %g -aspect_ratio 1 -core_space 2 -site %s" % (d.utilization, p.site),
        "make_tracks", "place_pins -hor_layers %s -ver_layers %s -random %s" % (p.io_h, p.io_v, io_exclusions(d.io_tcl)),
        "write_db %s" % out_odb]) + "\n"


def m1_script(p: Nangate45, d: DesignCfg, fp_odb: Path, out_odb: Path, out_tcl: Path) -> str:
    return "\n".join([
        "read_db %s" % fp_odb, "\n".join("read_liberty %s" % l for l in [p.lib] + d.macro_libs), "read_sdc %s" % d.sdc,
        "rtl_macro_placer -halo_width %g -halo_height %g" % d.halo,
        "write_macro_placement %s" % out_tcl, "write_db %s" % out_odb, 'puts "HB_M1_DONE"']) + "\n"


def f1_script(p: Nangate45, d: DesignCfg, fp_odb: Path, macro_tcl: Path | None, work: Path, threads: int = 8) -> str:
    adj = "set_global_routing_layer_adjustment metal2-metal3 0.4\nset_global_routing_layer_adjustment metal4-metal10 0.15"
    return "\n".join([
        "read_db %s" % fp_odb, "\n".join("read_liberty %s" % l for l in [p.lib] + d.macro_libs), "read_sdc %s" % d.sdc,
        "set_thread_count %d" % threads,
        ("source %s" % macro_tcl) if macro_tcl else "",
        "foreach inst [[ord::get_db_block] getInsts] { if {[[$inst getMaster] isBlock]} { $inst setPlacementStatus FIRM } }",
        "source %s" % p.set_rc, "set_routing_layers -signal %s-%s" % (p.min_layer, p.max_layer), adj,
        "set t0 [clock milliseconds]",
        "global_placement -routability_driven -timing_driven -density %g" % d.place_density,
        # ORFS 3_4 resize: electrical repair after global placement (buffering / resizing of long, high-fanout nets)
        "estimate_parasitics -placement", "repair_design", "repair_tie_fanout -separation 5 LOGIC0_X1/Z",
        "repair_tie_fanout -separation 5 LOGIC1_X1/Z",
        "detailed_placement",
        'set cp_ok 1\nif {[catch {check_placement} msg]} { set cp_ok 0; puts "HB_CHECK_PLACEMENT_FAIL $msg" }\nputs "HB_CHECK_PLACEMENT $cp_ok"',
        "estimate_parasitics -placement",
        'puts "HB_WNS_PLACE [sta::worst_slack -max]"', 'puts "HB_TNS_PLACE [sta::total_negative_slack -max]"',
        'puts "HB_HOLD_PLACE [sta::worst_slack -min]"',
        "global_route -congestion_iterations 30 -congestion_report_file %s -verbose" % (work / "congestion.rpt"),
        "estimate_parasitics -global_routing",
        'puts "HB_WNS_GR [sta::worst_slack -max]"', 'puts "HB_TNS_GR [sta::total_negative_slack -max]"',
        'puts "HB_HOLD_GR [sta::worst_slack -min]"',
        "report_power", 'puts "HB_RUNTIME_MS [expr {[clock milliseconds] - $t0}]"',
        "write_def %s" % (work / "f1_out.def")]) + "\n"


def run_tool(cmd: str, script_text: str, script_path: Path, docker_image: str | None = DOCKER_IMAGE,
             timeout: int = 7200, mount: str | None = None) -> tuple:
    """Run 'openroad' or 'yosys' on a script; returns (returncode, log)."""
    script_path.write_text(script_text)
    if cmd == "openroad":
        inner = "openroad -no_init -no_splash -exit %s" % script_path
    else:
        inner = "yosys -q -s %s" % script_path
    if docker_image:
        m = mount or str(Path.home())
        full = ["docker", "run", "--rm", "-v", "%s:%s" % (m, m), docker_image, "bash", "-lc", inner]
    else:
        full = ["bash", "-lc", inner]
    t0 = time.time()
    try:
        pr = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
        log = pr.stdout + "\n" + pr.stderr
        rc = pr.returncode
    except subprocess.TimeoutExpired as e:
        log, rc = str(e.stdout or ""), "timeout"
    (script_path.with_suffix(".log")).write_text(log)
    return rc, log, round(time.time() - t0, 1)


def parse_power(log: str):
    m = re.findall(r"^Total\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)", log, re.M)
    return float(m[-1][3]) if m else None


def f1_metrics(log: str) -> dict:
    out = parse_f1_log(log)
    for tag, key in (("HB_HOLD_PLACE", "hold_place"), ("HB_HOLD_GR", "hold_gr")):
        mm = re.findall(r"^%s\s+(\S+)" % tag, log, re.M)
        out[key] = float(mm[-1]) if mm and mm[-1] not in ("INF", "-INF") else None
    out["total_power_w"] = parse_power(log)
    out["setup_wns_ns"], out["setup_tns_ns"], out["hold_wns_ns"] = out["wns_gr"], out["tns_gr"], out["hold_gr"]
    out["gr_wl"] = out.get("gr_wl")
    return out
