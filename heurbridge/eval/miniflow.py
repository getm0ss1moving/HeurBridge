"""Minimal Nangate45 flow without ORFS/make (Track B development + fallback if ORFS and the installed
OpenROAD disagree).  Uses only commands verified by the T0.3 probe.

  synth       Yosys: read RTL + fakeram liberty as black boxes, flatten, map to NangateOpenCellLibrary
  floorplan   read LEF/liberty/netlist/SDC, initialize_floorplan (utilization), make_tracks, IO constraints,
              place_pins, tapcells -> fp.odb
  m1          tool-native macro placement: rtl_macro_placer (Hier-RTLMP) with the platform halo -> m1.odb,
              macro placement written as Tcl (the M1 seed layout)
  f1          fp.odb + our macro placement (place_macro, FIRM) -> platform RC -> global_placement
              (routability- and timing-driven) -> repair_design -> detailed_placement -> check_placement ->
              estimate_parasitics -placement -> setup/hold slack, power (placement stage) -> global_route
              (30 congestion iterations) -> f1 DEF -> [estimate_parasitics -global_routing -> slack, power]
Outputs the f1 JSON of eval/f1.py (parse_f1_log) plus power.  Timing: sta::worst_slack -max = setup WNS
(worst_slack_max), -min = hold; sta::total_negative_slack -max = setup TNS (METRIC_CONVENTIONS).

Timing stage.  In the local OpenROAD build (b16bda7e) ``estimate_parasitics -global_routing`` fails at
random: "Error: out of memory." (bad_alloc; OpenSTA then exits the process) on 5 of 14 bp_fe_top layouts in
the first campaign and on a repeat of the M1 layout that had passed before, a segfault on others, and an
OOM kill (rc 137) when two runs shared the VM.  GR-stage timing is therefore opt-in (``gr_timing``).
Determinism: f1 values are identical across repeats at a fixed thread count, but differ between thread
counts (bp_fe_top M1: setup TNS -113.5 ns with 6 threads, -86.9 ns with 3), so one campaign uses one count.  The development f1 therefore takes timing and power from the
placement-stage parasitics, which exist for every candidate and the baseline alike; the GR-stage values
are recorded when available (``timing_stage="gr"`` selects them, for a build without the bug).
"""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from .. import tools
from .f1 import parse_f1_log

DOCKER_IMAGE = tools.docker_image()          # None when HB_OPENROAD is set (servers: native tools)


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
    clkgate_map = property(lambda s: s.pdir / "cells_clkgate.v")    # CLKGATE_MAP_FILE (OPENROAD_CLKGATE)
    latch_map = property(lambda s: s.pdir / "cells_latch.v")        # LATCH_MAP_FILE
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
    place_density: float = 0.30        # Nangate45 platform default (PLACE_DENSITY ?= 0.30)
    place_density_lb_addon: float | None = None   # ORFS: density = uniform lower bound + addon (util.tcl)
    die_area: tuple | None = None      # DIE_AREA + CORE_AREA (ORFS floorplan method 3; else CORE_UTILIZATION)
    core_area: tuple | None = None
    rtlmp_args: tuple = ()             # (flag, value) from the design's RTLMP_* variables (macro_place_util.tcl)
    rtlmp_override: str | None = None  # RTLMP_ARGS replaces every argument (ORFS)
    cell_pad_gpl: int = 0              # CELL_PAD_IN_SITES_GLOBAL_PLACEMENT (ORFS default 0)
    halo: tuple = (22.4, 15.12)        # Nangate45 platform default (MACRO_PLACE_HALO ?= 22.4 15.12)
    io_tcl: str | None = None
    fastroute_tcl: str | None = None
    core_margin: float = 1.0           # ORFS default CORE_MARGIN
    aspect_ratio: float = 1.0          # ORFS default CORE_ASPECT_RATIO
    tapcell_tcl: str | None = None
    tap_cell_name: str = "TAPCELL_X1"
    pdn_tcl: str | None = None
    make_tracks_tcl: str | None = None
    dont_use: tuple = ()
    min_layer: str = "metal2"
    max_layer: str = "metal10"
    min_clk_layer: str = "metal4"
    io_h: str = "metal5"
    io_v: str = "metal6"


def mk_vars(path, into: dict | None = None) -> dict:
    """``export KEY = VALUE`` / ``export KEY ?= VALUE`` lines of a config.mk (continuation lines joined).
    Make semantics for the ORFS include order (design config first, then the platform config): ``=``
    assigns, ``?=`` assigns only if the key is still unset."""
    out = dict(into or {})
    txt = re.sub(r"\\\n\s*", " ", Path(path).read_text())
    for m in re.finditer(r"^export\s+(\w+)\s*(\??)=\s*(.*?)\s*$", txt, re.M):
        k, weak, v = m.groups()
        if weak and k in out:
            continue
        out[k] = v
    return out


def from_orfs(flow_dir: str, platform_design: str) -> DesignCfg:
    """The subset of the ORFS configuration this flow needs (e.g. 'nangate45/bp_fe_top'): the design's
    config.mk, then the platform's (defaults and platform-wide settings), as ORFS includes them."""
    plat = platform_design.split("/")[0]
    ddir = Path(flow_dir) / "designs" / platform_design
    pdir = Path(flow_dir) / "platforms" / plat
    v = mk_vars(ddir / "config.mk")
    if (pdir / "config.mk").exists():
        v = mk_vars(pdir / "config.mk", v)
    subst = {"$(DESIGN_HOME)": str(Path(flow_dir) / "designs"), "$(PLATFORM)": plat, "$(PLATFORM_DIR)": str(pdir),
             "$(DESIGN_NAME)": v.get("DESIGN_NAME", ""), "$(DESIGN_NICKNAME)": v.get("DESIGN_NICKNAME", v.get("DESIGN_NAME", "")),
             "$(DESIGN_DIR)": str(ddir)}

    def get(k, default=None):
        x = v.get(k)
        if x is None or x == "":
            return default
        for a, b in subst.items():
            x = x.replace(a, b)
        return x

    def path_or_none(k):
        x = get(k)
        return x if x and Path(x).exists() else None
    tracks = pdir / "make_tracks.tcl"
    halo = tuple(float(x) for x in get("MACRO_PLACE_HALO", "22.4 15.12").split()[:2])
    missing = [f for f in get("VERILOG_FILES", "").split() if not Path(f).exists()]
    if missing:                        # e.g. a sparse ORFS checkout without designs/nangate45/swerv/macros.v
        raise FileNotFoundError("%s: VERILOG_FILES missing: %s" % (platform_design, " ".join(missing)))
    addon = get("PLACE_DENSITY_LB_ADDON")
    die, core = get("DIE_AREA"), get("CORE_AREA")
    if die and core and v.get("CORE_UTILIZATION"):
        raise ValueError("%s: DIE_AREA/CORE_AREA and CORE_UTILIZATION are mutually exclusive (ORFS)" % platform_design)
    rtlmp = tuple((flag, get(var)) for var, flag in RTLMP_VARS if get(var))
    return DesignCfg(name=ddir.name, top=get("DESIGN_NAME"), verilog=get("VERILOG_FILES", "").split(),
                     sdc=get("SDC_FILE") or str(ddir / "constraint.sdc"),
                     macro_lefs=get("ADDITIONAL_LEFS", "").split(), macro_libs=get("ADDITIONAL_LIBS", "").split(),
                     utilization=float(get("CORE_UTILIZATION", 50)), place_density=float(get("PLACE_DENSITY", 0.30)),
                     place_density_lb_addon=float(addon) if addon else None,
                     die_area=tuple(float(x) for x in die.split()) if die and core else None,
                     core_area=tuple(float(x) for x in core.split()) if die and core else None,
                     rtlmp_args=rtlmp, rtlmp_override=get("RTLMP_ARGS"),
                     cell_pad_gpl=int(get("CELL_PAD_IN_SITES_GLOBAL_PLACEMENT", 0)),
                     halo=halo, io_tcl=get("IO_CONSTRAINTS"), fastroute_tcl=path_or_none("FASTROUTE_TCL"),
                     core_margin=float(get("CORE_MARGIN", "1.0").split()[0]),
                     aspect_ratio=float(get("CORE_ASPECT_RATIO", 1.0)), tapcell_tcl=path_or_none("TAPCELL_TCL"),
                     tap_cell_name=get("TAP_CELL_NAME", "TAPCELL_X1"), pdn_tcl=path_or_none("PDN_TCL"),
                     make_tracks_tcl=str(tracks) if tracks.exists() else None,
                     dont_use=tuple(get("DONT_USE_CELLS", "").split()),
                     min_layer=get("MIN_ROUTING_LAYER", "metal2"), max_layer=get("MAX_ROUTING_LAYER", "metal10"),
                     min_clk_layer=get("MIN_CLK_ROUTING_LAYER", "metal4"),
                     io_h=get("IO_PLACER_H", "metal5"), io_v=get("IO_PLACER_V", "metal6"))


def synth_script(p: Nangate45, d: DesignCfg, out_v: Path, flatten: bool = False) -> str:
    """Hierarchical by default (ORFS SYNTH_HIERARCHICAL=1): Hier-RTLMP clusters by the logical hierarchy and
    this OpenROAD build crashes in TritonPart when it has to split one large flat cluster."""
    # ORFS synth_preamble.tcl reads the platform's OPENROAD_CLKGATE definition (-> CLKGATE_X1) and the standard
    # cells as black boxes.  Only swerv_wrapper's RTL instantiates OPENROAD_CLKGATE; for the others the extra
    # standard-cell library changes the netlist (bp_fe_top: output ports driven through assigns, 362 diff lines)
    # without being needed, so both are read only when the RTL uses the clock gate: every other netlist stays
    # bit-identical to the one the earlier Track-B results were made with (checked on bp_fe_top).
    clkgate = p.clkgate_map.exists() and any("OPENROAD_CLKGATE" in Path(v).read_text(errors="ignore") for v in d.verilog)
    lines = ["read_liberty -lib %s" % l for l in ([p.lib] if clkgate else []) + d.macro_libs]
    lines += ["read_verilog -defer -sv %s" % v for v in d.verilog]
    if clkgate:
        lines.append("read_verilog -defer %s" % p.clkgate_map)
    du = "".join(" -dont_use %s" % c for c in d.dont_use)
    lines += ["hierarchy -top %s" % d.top, "synth -top %s%s" % (d.top, " -flatten" if flatten else "")]
    if p.latch_map.exists():                               # ORFS: latches to the platform's latch cells
        lines.append("techmap -map %s" % p.latch_map)
    # ORFS synth.tcl order after mapping: opt, setundef -zero before abc, then splitnets, opt_clean -purge, hilomap,
    # and insbuf (SYNTH_INSBUF=1).  The earlier order (hilomap before setundef) left the constants that setundef creates
    # without tie cells: bp_be_top's be_calculator/zero_ reached OpenROAD as a GROUND net that detailed routing
    # refuses (DRT-0305); without insbuf, output ports were driven through assigns.
    lines += ["dfflibmap -liberty %s" % p.lib, "opt", "setundef -zero",
              "abc -liberty %s%s" % (p.lib, du),                      # (no dont-use flip-flops)
              "splitnets", "opt_clean -purge",
              "hilomap -singleton -hicell LOGIC1_X1 Z -locell LOGIC0_X1 Z",
              "insbuf -buf BUF_X1 A Z",
              "write_verilog -noattr -noexpr -nohex -nodec %s" % out_v]
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
    """ORFS 2_1 floorplan (DIE_AREA/CORE_AREA when the design gives them, else utilization, aspect ratio and core
    margin; platform tracks) + random IO placement
    with the design's exclusions.  Tapcells and the power grid follow the macro placement (ORFS 2_3/2_4),
    so they are part of f1 (every candidate gets them after its macros are placed)."""
    return "\n".join([
        _reads(p, d), "read_verilog %s" % netlist, "link_design %s" % d.top, "read_sdc %s" % d.sdc,
        ("initialize_floorplan -die_area {%s} -core_area {%s} -site %s" % (
            " ".join("%g" % x for x in d.die_area), " ".join("%g" % x for x in d.core_area), p.site)) if d.die_area else
        "initialize_floorplan -utilization %g -aspect_ratio %g -core_space %g -site %s" % (
            d.utilization, d.aspect_ratio, d.core_margin, p.site),
        ("source %s" % d.make_tracks_tcl) if d.make_tracks_tcl else "make_tracks",
        "place_pins -hor_layers %s -ver_layers %s -random %s" % (d.io_h, d.io_v, io_exclusions(d.io_tcl)),
        "write_db %s" % out_odb]) + "\n"


def m1_script(p: Nangate45, d: DesignCfg, fp_odb: Path, out_odb: Path, out_tcl: Path, threads: int | None = None) -> str:
    """Tool-native macro placement (M1).  ORFS runs every stage as ``openroad -threads $(NUM_CORES)``, and
    Hier-RTLMP's annealing runs in parallel with the thread count, so M1 uses EDA_THREADS threads (the earlier
    single-threaded M1 took over an hour on ariane133 and is not ORFS's configuration)."""
    return "\n".join([
        "read_db %s" % fp_odb, "\n".join("read_liberty %s" % l for l in [p.lib] + d.macro_libs), "read_sdc %s" % d.sdc,
        "set_thread_count %d" % (threads or tools.eda_threads(8)), _rtlmp_call(d),
        "write_macro_placement %s" % out_tcl, "write_db %s" % out_odb, 'puts "HB_M1_DONE"']) + "\n"


def _route_setup(p: Nangate45, d: DesignCfg) -> str:
    """Platform RC, routing layers and the design's FastRoute adjustments (ORFS sources FASTROUTE_TCL)."""
    env = "\n".join("set ::env(%s) %s" % kv for kv in (("MIN_ROUTING_LAYER", d.min_layer), ("MAX_ROUTING_LAYER", d.max_layer),
                                                     ("MIN_CLK_ROUTING_LAYER", d.min_clk_layer)))
    fr = ("source %s" % d.fastroute_tcl) if d.fastroute_tcl else "set_routing_layers -signal %s-%s" % (d.min_layer, d.max_layer)
    return "\n".join(["source %s" % p.set_rc, env, fr])


def _macro_env(d: DesignCfg, macro_tcl: Path | None) -> str:
    """Macro placement (FIRM), then ORFS 2_3 tapcells and 2_4 power grid around the placed macros."""
    out = [("source %s" % macro_tcl) if macro_tcl else "",
           "foreach inst [[ord::get_db_block] getInsts] { if {[[$inst getMaster] isBlock]} { $inst setPlacementStatus FIRM } }"]
    if d.tapcell_tcl:
        out += ["set ::env(TAP_CELL_NAME) %s" % d.tap_cell_name, "source %s" % d.tapcell_tcl]
    if d.pdn_tcl:
        out += ["source %s" % d.pdn_tcl, "pdngen", _drop_supply_ports()]
    return "\n".join(out)


def _drop_supply_ports() -> str:
    """Remove the VDD/VSS block terminals pdngen creates (``-pins``); the grid's nets and wires stay (GR sees
    them).  With these vertex-less ports present during placement and repair, report_power of this OpenSTA
    build dereferences a stale vertex in Power::seedActivities and segfaults (bisected on bp_fe_top)."""
    return ("foreach net [[ord::get_db_block] getNets] { if {[lsearch {POWER GROUND} [$net getSigType]] >= 0} "
            "{ foreach bt [$net getBTerms] { odb::dbBTerm_destroy $bt } } }")


RTLMP_VARS = (("RTLMP_MAX_LEVEL", "-max_num_level"), ("RTLMP_MAX_INST", "-max_num_inst"),
              ("RTLMP_MIN_INST", "-min_num_inst"), ("RTLMP_MAX_MACRO", "-max_num_macro"),
              ("RTLMP_MIN_MACRO", "-min_num_macro"), ("RTLMP_MIN_AR", "-min_ar"), ("RTLMP_AREA_WT", "-area_weight"),
              ("RTLMP_WIRELENGTH_WT", "-wirelength_weight"), ("RTLMP_OUTLINE_WT", "-outline_weight"),
              ("RTLMP_BOUNDARY_WT", "-boundary_weight"), ("RTLMP_NOTCH_WT", "-notch_weight"),
              ("RTLMP_FENCE_LX", "-fence_lx"), ("RTLMP_FENCE_LY", "-fence_ly"), ("RTLMP_FENCE_UX", "-fence_ux"),
              ("RTLMP_FENCE_UY", "-fence_uy"))


def _density_tcl(d: DesignCfg) -> str:
    """Sets hb_density as ORFS's ``place_density_with_lb_addon`` (flow/scripts/util.tcl)."""
    if d.place_density_lb_addon is not None:
        return ("set hb_lb [gpl::get_global_placement_uniform_density -pad_left %d -pad_right %d]\n"
                "set hb_density [expr {$hb_lb + (1.0 - $hb_lb) * %r + 0.01}]\n"
                "if {$hb_density > 1.0} { error \"HB_PLACE_DENSITY_ABOVE_1 $hb_density\" }\n"
                % (d.cell_pad_gpl, d.cell_pad_gpl, d.place_density_lb_addon))
    return "set hb_density %r\n" % d.place_density


def _rtlmp_call(d: DesignCfg) -> str:
    """rtl_macro_placer as ORFS 2_3 calls it (macro_place_util.tcl): the design's RTLMP_* arguments, the platform
    halo and -target_util = the placement density (the earlier M1 passed only the halo).  RTLMP_ARGS replaces
    all of them, as in ORFS.  Flags this build does not have are dropped and logged (HB_RTLMP_DROPPED)."""
    if d.rtlmp_override:
        return "rtl_macro_placer %s" % d.rtlmp_override
    args = " ".join("%s %s" % fv for fv in d.rtlmp_args)
    return (_density_tcl(d) +
            "set hb_rtlmp [list %s -halo_width %g -halo_height %g -target_util $hb_density]\n" % (args, d.halo[0], d.halo[1]) +
            "set hb_keep {}\n"
            "foreach {f v} $hb_rtlmp { if {![info exists sta::cmd_args(rtl_macro_placer)] || "
            "[string first $f $sta::cmd_args(rtl_macro_placer)] >= 0} { lappend hb_keep $f $v } "
            "else { puts \"HB_RTLMP_DROPPED $f\" } }\n"
            'puts "HB_RTLMP_ARGS $hb_keep"\n'
            "rtl_macro_placer {*}$hb_keep")


def _global_placement(d: DesignCfg) -> str:
    """Routability- and timing-driven global placement with *virtual* timing-driven repairs.

    Builds that have ``-keep_resize_below_overflow`` (OpenROAD 2024-12 on 224; default 0.3) keep the resizer's
    buffers inside global placement once the overflow falls below that value.  On bp_fe_top (M1 layout) that
    step added 21,726 um^2 of buffers (+49 % cell area) at iteration 336, after which the placement diverged
    (HPWL 2.4e9 -> 3e10, overflow stuck near 0.4-0.8 until iteration 5,000) and detailed placement failed
    (DPL-0036).  0 keeps every timing-driven repair virtual -- the only behaviour of the older local build
    (b16bda7e) -- and electrical repair stays in the explicit ORFS 3_4 step below.  The flag is used only when
    the build has it, so one script serves both builds; the arguments are logged (HB_GPL_ARGS).

    Density as ORFS's ``place_density_with_lb_addon`` (flow/scripts/util.tcl): with PLACE_DENSITY_LB_ADDON the
    uniform-density lower bound of the placement area (after macros, tapcells and grid) plus the addon share
    of the remainder plus 0.01 (bp_be_top, swerv_wrapper; a fixed 0.30 is below their utilization: GPL-0302);
    otherwise PLACE_DENSITY (design, else the platform's 0.30)."""
    return (_density_tcl(d) + 'puts "HB_PLACE_DENSITY $hb_density"\n'
            "set hb_gpl [list -routability_driven -timing_driven -density $hb_density]\n"
            "if {[info exists sta::cmd_args(global_placement)] && "
            "[string first -keep_resize_below_overflow $sta::cmd_args(global_placement)] >= 0} "
            "{ lappend hb_gpl -keep_resize_below_overflow 0 }\n"
            'puts "HB_GPL_ARGS $hb_gpl"\n'
            "global_placement {*}$hb_gpl")


def _place_steps(p: Nangate45, d: DesignCfg, fp_odb: Path, macro_tcl: Path | None, threads: int) -> list:
    """Shared by f1 and f2: macros + tapcells + grid, global placement, ORFS 3_4 resize, detailed placement."""
    return [
        "read_db %s" % fp_odb, "\n".join("read_liberty %s" % l for l in [p.lib] + d.macro_libs), "read_sdc %s" % d.sdc,
        "set_thread_count %d" % threads,
        ("set_dont_use {%s}" % " ".join(d.dont_use)) if d.dont_use else "",
        _macro_env(d, macro_tcl), _route_setup(p, d),
        "set t0 [clock milliseconds]",
        _global_placement(d),
        # ORFS 3_4 resize: port buffering, electrical repair (buffering / resizing of long, high-fanout nets), tie cells
        "estimate_parasitics -placement", "buffer_ports", "repair_design",
        "repair_tie_fanout -separation 5 LOGIC0_X1/Z", "repair_tie_fanout -separation 5 LOGIC1_X1/Z",
        "detailed_placement",
        'set cp_ok 1\nif {[catch {check_placement} msg]} { set cp_ok 0; puts "HB_CHECK_PLACEMENT_FAIL $msg" }\nputs "HB_CHECK_PLACEMENT $cp_ok"']


def f1_script(p: Nangate45, d: DesignCfg, fp_odb: Path, macro_tcl: Path | None, work: Path, threads: int = 8,
              gr_timing: bool = False) -> str:
    """``gr_timing`` adds GR-parasitics timing/power after the core f1 values (off by default: in the local
    OpenROAD build that step allocates without bound, see the module docstring)."""
    tail = []
    if gr_timing:
        tail = ['if {[catch {estimate_parasitics -global_routing\n'
                '  puts "HB_WNS_GR [sta::worst_slack -max]"; puts "HB_TNS_GR [sta::total_negative_slack -max]"\n'
                '  puts "HB_HOLD_GR [sta::worst_slack -min]"\n'
                '  puts "HB_POWER_GR_BEGIN"; report_power; puts "HB_POWER_GR_END"} msg]} {\n'
                '  puts "HB_GR_PARASITICS_FAIL [string map {\\n { }} $msg]" }']
    return "\n".join(_place_steps(p, d, fp_odb, macro_tcl, threads) + [
        "estimate_parasitics -placement",
        'puts "HB_WNS_PLACE [sta::worst_slack -max]"', 'puts "HB_TNS_PLACE [sta::total_negative_slack -max]"',
        'puts "HB_HOLD_PLACE [sta::worst_slack -min]"',
        'puts "HB_POWER_PLACE_BEGIN"', "report_power", 'puts "HB_POWER_PLACE_END"',
        # -allow_congestion: FastRoute reports the remaining overflow instead of failing (GRT-0119), so the
        # (1+OF) term of J is measured at f1; f2 keeps the ORFS default (a congested layout fails there)
        "global_route -congestion_iterations 30 -allow_congestion -congestion_report_file %s -verbose"
        % (work / "congestion.rpt"),
        'puts "HB_RUNTIME_MS [expr {[clock milliseconds] - $t0}]"',
        "write_def %s" % (work / "f1_out.def"), 'puts "HB_F1_CORE_DONE"'] + tail + ['puts "HB_F1_DONE"']) + "\n"


FILL_CELLS = "FILLCELL_X1 FILLCELL_X2 FILLCELL_X4 FILLCELL_X8 FILLCELL_X16 FILLCELL_X32"


def _stage_head(p: Nangate45, d: DesignCfg, odb: Path, threads: int) -> list:
    """Start of a later f2 stage: a fresh process reading the previous stage's database (as ORFS does)."""
    return ["read_db %s" % odb, "\n".join("read_liberty %s" % l for l in [p.lib] + d.macro_libs),
            "read_sdc %s" % d.sdc, "set_thread_count %d" % threads,
            ("set_dont_use {%s}" % " ".join(d.dont_use)) if d.dont_use else "", _route_setup(p, d),
            "set_propagated_clock [all_clocks]"]


def f2_stages(p: Nangate45, d: DesignCfg, fp_odb: Path, macro_tcl: Path | None, work: Path, threads: int = 8,
              repair_timing: bool = True, hold_margin: float = 0.03) -> list:
    """f2 (task T1.5) as ORFS runs it: one OpenROAD process per stage, each reading the previous stage's
    database.  In the local build, repair_timing in the same process as CTS segfaults in the STA arrival
    search (stale graph after the netlist edits); a fresh process per stage avoids that class of bug.

      cts     f1 placement (recomputed; deterministic at a fixed thread count) + 4_1 CTS + detailed placement
      rt      setup / hold repair_timing (design hold margin) + detailed placement + check_placement
      route   5_1 global route + 5_2 detailed route + 5_3 fill (the routes stay in memory between GR and DR)
      final   6: OpenRCX extraction (platform rcx_patterns.rules), STA on the extracted parasitics, power
    Returns [(stage, script, done_marker)]."""
    rcx = p.pdir / "rcx_patterns.rules"
    cts = _place_steps(p, d, fp_odb, macro_tcl, threads) + [
        "estimate_parasitics -placement",
        "clock_tree_synthesis -root_buf BUF_X4 -buf_list {BUF_X4} -sink_clustering_enable",
        "set_propagated_clock [all_clocks]", "repair_clock_nets", "estimate_parasitics -placement",
        "detailed_placement", "write_db %s" % (work / "f2_cts.odb"), 'puts "HB_STAGE_DONE cts"']
    rt_in = work / "f2_cts.odb"
    stages = [("cts", cts)]
    if repair_timing:
        stages.append(("rt", _stage_head(p, d, rt_in, threads) + [
            "estimate_parasitics -placement",
            "repair_timing -setup -repair_tns 100", "repair_timing -hold -hold_margin %g" % hold_margin,
            "detailed_placement", "check_placement", "write_db %s" % (work / "f2_rt.odb"), 'puts "HB_STAGE_DONE rt"']))
        rt_in = work / "f2_rt.odb"
    stages.append(("route", _stage_head(p, d, rt_in, threads) + [
        "global_route -congestion_iterations 30 -verbose",
        "detailed_route -output_drc %s -verbose 1" % (work / "drc.rpt"),
        "filler_placement {%s}" % FILL_CELLS, "write_db %s" % (work / "f2_route.odb"), 'puts "HB_STAGE_DONE route"']))
    stages.append(("final", _stage_head(p, d, work / "f2_route.odb", threads) + [
        "extract_parasitics -ext_model_file %s" % rcx, "write_spef %s" % (work / "f2.spef"),
        "read_spef %s" % (work / "f2.spef"),
        'puts "HB_WNS_F2 [sta::worst_slack -max]"', 'puts "HB_TNS_F2 [sta::total_negative_slack -max]"',
        'puts "HB_HOLD_F2 [sta::worst_slack -min]"',
        'puts "HB_POWER_F2_BEGIN"', "report_power", 'puts "HB_POWER_F2_END"',
        "write_def %s" % (work / "f2_out.def"), 'puts "HB_F2_DONE"']))
    return [(name, "\n".join(lines) + "\n", "HB_F2_DONE" if name == "final" else "HB_STAGE_DONE %s" % name)
            for name, lines in stages]


def run_f2(p: Nangate45, d: DesignCfg, fp_odb: Path, macro_tcl: Path | None, work: Path, threads: int = 8,
           repair_timing: bool = True, docker_image: str | None = DOCKER_IMAGE, timeout: int = 7200) -> tuple:
    """Run the f2 stages in order (one retry for a crashed stage); stop at the first failed stage.
    Returns (returncode, concatenated log, wall seconds, per-stage [(stage, rc, wall, failure)])."""
    logs, done, total = [], [], 0.0
    rc = 0
    for name, script, marker in f2_stages(p, d, fp_odb, macro_tcl, work, threads, repair_timing):
        for attempt in (0, 1):
            rc, log, wall = run_tool("openroad", script, work / ("f2_%s%s.tcl" % (name, "" if attempt == 0 else "_retry")),
                                     docker_image=docker_image, timeout=timeout)
            total += wall
            ok = rc == 0 and re.search(r"^%s$" % re.escape(marker), log, re.M)
            failure = None if ok else classify_failure(rc, log)
            done.append((name, rc, wall, failure))
            logs.append("### stage %s (attempt %d)\n%s" % (name, attempt, log))
            if ok or not should_retry(rc, failure):
                break
        if not ok:
            return (rc if rc != 0 else "stage_%s_incomplete" % name), "\n".join(logs), round(total, 1), done
    return 0, "\n".join(logs), round(total, 1), done


def f2_metrics(log: str) -> dict:
    """Canonical f2 fields from the HB_* markers and TritonRoute's final summary."""
    def last(tag):
        m = re.findall(r"^%s\s+(\S+)" % tag, log, re.M)
        return float(m[-1]) if m and m[-1] not in ("INF", "-INF", "nan") else None
    viol = re.findall(r"Number of violations = (\d+)", log)
    wl = re.findall(r"Total wire length = ([0-9.]+) um", log)
    vias = re.findall(r"Total number of vias = (\d+)", log)
    gr = parse_f1_log(log)
    rt = last("HB_RUNTIME_MS")
    return {"setup_wns_ns": last("HB_WNS_F2"), "setup_tns_ns": last("HB_TNS_F2"), "hold_wns_ns": last("HB_HOLD_F2"),
            "total_power_w": parse_power(log, "F2"), "drc_violations": int(viol[-1]) if viol else None,
            "detailed_wirelength_um": float(wl[-1]) if wl else None, "vias": int(vias[-1]) if vias else None,
            "gr_overflow_total": gr.get("gr_overflow_total"), "gr_overflow_max": gr.get("gr_overflow_max"),
            "gr_wl": gr.get("gr_wl"), "check_placement_ok": gr.get("check_placement_ok"),
            "repair_timing_error": (re.findall(r"^HB_REPAIR_(?:TIMING|HOLD)_FAIL\s*(.*)$", log, re.M) or [None])[-1],
            "runtime_s": rt / 1000.0 if rt is not None else None, "done": bool(re.search(r"^HB_F2_DONE$", log, re.M))}


def run_tool(cmd: str, script_text: str, script_path: Path, docker_image: str | None = DOCKER_IMAGE,
             timeout: int = 7200, mount: str | None = None) -> tuple:
    """Run 'openroad' or 'yosys' on a script; returns (returncode, log)."""
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script_text)
    args = ["-no_init", "-no_splash", "-exit", str(script_path)] if cmd == "openroad" else ["-q", "-s", str(script_path)]
    if docker_image:
        m = mount or str(Path.home())
        full = ["docker", "run", "--rm", "-v", "%s:%s" % (m, m), docker_image, "bash", "-lc", " ".join([cmd] + args)]
    else:                                  # no login shell: the shared account's profile must not pick the binary
        full = [tools.binary(cmd)] + args
    env = None
    if not docker_image:                   # native runs: OpenMP is not bounded by set_thread_count
        import os
        env = dict(os.environ, OMP_NUM_THREADS=str(tools.eda_threads(8)))
    t0 = time.time()
    try:
        pr = subprocess.run(full, capture_output=True, text=True, timeout=timeout, env=env)
        log = pr.stdout + "\n" + pr.stderr
        rc = pr.returncode
    except subprocess.TimeoutExpired as e:
        log, rc = str(e.stdout or ""), "timeout"
    (script_path.with_suffix(".log")).write_text(log)
    return rc, log, round(time.time() - t0, 1)


def parse_power(log: str, stage: str | None = None):
    """Total power (W) from ``report_power``; ``stage`` = 'PLACE' / 'GR' reads the marked block only."""
    if stage:
        m = re.search(r"^HB_POWER_%s_BEGIN$(.*?)^HB_POWER_%s_END$" % (stage, stage), log, re.M | re.S)
        if not m:
            return None
        log = m.group(1)
    m = re.findall(r"^Total\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)", log, re.M)
    return float(m[-1][3]) if m else None


FAILURES = (("tool_oom", r"^Error: out of memory"), ("tool_assertion", r"Assertion .* failed"),
            ("check_placement_failed", r"^HB_CHECK_PLACEMENT_FAIL"), ("tool_error", r"^(?:\[ERROR [A-Z]+-\d+\].*|Error: .*)$"))


def classify_failure(rc, log: str) -> str | None:
    """Name the reason of a failed run (None if the run completed): every failure is reported by name."""
    if rc == 0 and re.search(r"^HB_F1_DONE$", log, re.M):
        return None
    if rc == "timeout":
        return "timeout"
    if rc in (139, -11):
        return "segfault"
    for name, pat in FAILURES:
        m = re.search(pat, log, re.M)
        if m:
            return "%s: %s" % (name, m.group(0).strip()[:160])
    return "returncode_%s" % rc


def f1_metrics(log: str, timing_stage: str = "place") -> dict:
    """Parsed f1 values.  The canonical timing/power fields come from ``timing_stage`` ('place' or 'gr')."""
    out = parse_f1_log(log)
    for tag, key in (("HB_HOLD_PLACE", "hold_place"), ("HB_HOLD_GR", "hold_gr")):
        mm = re.findall(r"^%s\s+(\S+)" % tag, log, re.M)
        out[key] = float(mm[-1]) if mm and mm[-1] not in ("INF", "-INF") else None
    out["power_place_w"], out["power_gr_w"] = parse_power(log, "PLACE"), parse_power(log, "GR")
    fail = re.findall(r"^HB_GR_PARASITICS_FAIL\s*(.*)$", log, re.M)
    out["gr_parasitics_error"] = fail[-1].strip() if fail else None
    if timing_stage not in ("place", "gr"):
        raise ValueError("timing_stage must be 'place' or 'gr'")
    sfx = "place" if timing_stage == "place" else "gr"
    out["setup_wns_ns"], out["setup_tns_ns"] = out["wns_" + sfx], out["tns_" + sfx]
    out["hold_wns_ns"], out["total_power_w"] = out["hold_" + sfx], out["power_%s_w" % sfx]
    out["timing_stage"] = timing_stage
    out["core_done"] = bool(re.search(r"^HB_F1_CORE_DONE$", log, re.M))
    return out


CRASH_CODES = (139, -11, 134, -6)


def f1_outcome(rc, log: str, timing_stage: str = "place") -> tuple:
    """(metrics, failure name or None, effective returncode).  With the placement timing stage, a failure
    after every core f1 value and the DEF were written (HB_F1_CORE_DONE: only the optional GR-stage timing
    was running) is recorded in ``gr_parasitics_error`` and does not fail the evaluation."""
    m = f1_metrics(log, timing_stage)
    failure = classify_failure(rc, log)
    if failure and timing_stage == "place" and m["core_done"]:
        m["gr_parasitics_error"] = m["gr_parasitics_error"] or failure
        return m, None, 0
    return m, failure, rc


def should_retry(rc, failure) -> bool:
    """One retry for crashes and for the flaky bad_alloc; deterministic failures are not retried."""
    return rc in CRASH_CODES or bool(failure and failure.startswith("tool_oom"))
