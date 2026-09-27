"""Track-B flow integration with OpenROAD-flow-scripts (tasks T1.4 Track B, T1.5, T1.7, M1 wrapper).

A macro layout is evaluated by writing ``place_macro`` commands to a Tcl file and running the
ORFS flow with ``MACRO_PLACEMENT_TCL`` (sourced by the macro-place stage before rtl_macro_placer,
which then only places macros that are still unplaced).  Stages:
  f1  ... -> 5_1_grt   (global placement, detailed placement, CTS, global route; timing after GRT)
  f2  ... -> 6_finish  (detailed route, RC extraction, signoff STA, power) + ``make metadata``
The tool-native macro placement (seed family M1) is the baseline run without MACRO_PLACEMENT_TCL;
ORFS writes it as results/.../2_2_floorplan_macro.tcl.

Metric keys differ between ORFS versions, so each canonical field lists candidates; the first
present wins and the chosen key is recorded (``sources``).  Every record is canonicalized through
eda metrics_schema by eval.cost before use.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .. import tools
from ..core import orient as O
from ..core.design import Design, Layout
from .f1 import parse_f1_log

CANDIDATES = {
    "setup_wns_ns": ["finish__timing__setup__ws", "detailedroute__timing__setup__ws", "globalroute__timing__setup__ws"],
    "hold_wns_ns": ["finish__timing__hold__ws", "detailedroute__timing__hold__ws", "globalroute__timing__hold__ws"],
    "setup_tns_ns": ["finish__timing__setup__tns", "detailedroute__timing__setup__tns", "globalroute__timing__setup__tns"],
    "hold_tns_ns": ["finish__timing__hold__tns", "detailedroute__timing__hold__tns"],
    "total_power_w": ["finish__power__total", "detailedroute__power__total", "globalroute__power__total"],
    "detailed_wirelength_um": ["detailedroute__route__wirelength", "finish__route__wirelength"],
    "vias": ["detailedroute__route__vias", "detailedroute__route__via__count", "detailedroute__route__vias__total"],
    "drc_violations": ["detailedroute__route__drc_errors", "finish__route__drc_errors"],
    "antenna_errors": ["detailedroute__antenna__violating__nets", "finish__antenna__violating__nets"],
    "gr_wl": ["globalroute__route__wirelength"],
    "gr_overflow_total": ["globalroute__route__overflow", "globalroute__route__overflow__total"],
    "clock_skew_ns": ["finish__clock__skew__setup", "cts__clock__skew__setup"],
    "instance_count": ["finish__design__instance__count", "floorplan__design__instance__count"],
    "grt_setup_wns_ns": ["globalroute__timing__setup__ws"],
    "grt_setup_tns_ns": ["globalroute__timing__setup__tns"],
    "grt_hold_wns_ns": ["globalroute__timing__hold__ws"],
}


def map_metrics(meta: dict) -> dict:
    """Canonical fields from an ORFS metadata/metrics dict (flat keys)."""
    out, src = {}, {}
    for f, keys in CANDIDATES.items():
        for k in keys:
            if k in meta and meta[k] not in (None, "N/A", "ERR"):
                try:
                    out[f] = float(meta[k])
                    src[f] = k
                    break
                except (TypeError, ValueError):
                    continue
    out["metric_sources"] = src
    out["metric_convention_version"] = "orfs_map_v1_2026-09-25"
    return out


def macro_placement_tcl(design: Design, layout: Layout, exact: bool = False) -> str:
    """``place_macro`` commands (lower-left location in microns, ODB orientation) for movable macros."""
    lines = ["# HeurBridge macro placement (%s)" % design.id]
    mm = np.flatnonzero(design.is_macro & ~design.is_fixed)
    eff = O.effective_size(design.size, layout.orient)
    ll = design.to_abs(layout.pos) - eff / 2
    dbu = design.dbu or 1000.0
    for i in mm:
        x, y = np.round(ll[i] * dbu) / dbu
        lines.append("place_macro -macro_name {%s} -location {%.4f %.4f} -orientation %s%s"
                     % (design.names[i], x, y, O.NAMES[int(layout.orient[i])].replace("MX90", "MXR90").replace("MY90", "MYR90"),
                        " -exact" if exact else ""))
    return "\n".join(lines) + "\n"


def parse_macro_tcl(text: str) -> dict:
    """Read ORFS' own 2_2_floorplan_macro.tcl (M1 layouts): {inst: (x_ll, y_ll, orient)}."""
    out = {}
    for m in re.finditer(r"place_macro\s+-macro_name\s+\{?([^\s}]+)\}?\s+-location\s+\{([-0-9.]+)\s+([-0-9.]+)\}"
                         r"(?:\s+-orientation\s+(\S+))?", text):
        out[m.group(1)] = (float(m.group(2)), float(m.group(3)), m.group(4) or "R0")
    return out


@dataclass
class OrfsRun:
    flow_dir: str                     # .../OpenROAD-flow-scripts/flow
    design_config: str                # ./designs/nangate45/ariane133/config.mk (relative to flow_dir) or absolute
    variant: str                      # FLOW_VARIANT (one directory per evaluated candidate)
    macro_tcl: str | None = None
    stage: str = "finish"
    threads: int = 8
    timeout_s: int = 7200
    env: dict = field(default_factory=dict)
    work_home: str | None = None      # ORFS WORK_HOME: results/logs/reports/objects go here (the encrypted workspace)
    base_variant: str | None = None   # reuse this variant's synthesis and pre-macro floorplan (stages 1 - 2_2)
    yosys: str | None = None          # YOSYS_EXE (default: tools.binary('yosys'))
    make_vars_extra: tuple = ()       # KEY=VALUE overrides of the design config (make command line wins)

    def make_vars(self, variant: str | None = None) -> list:
        v = ["DESIGN_CONFIG=%s" % self.design_config, "FLOW_VARIANT=%s" % (variant or self.variant),
             "NUM_CORES=%d" % self.threads, "OPENROAD_EXE=%s" % tools.binary("openroad"),
             "YOSYS_EXE=%s" % (self.yosys or tools.binary("yosys"))]
        if self.work_home:
            v.append("WORK_HOME=%s" % self.work_home)
        v += list(self.make_vars_extra)
        if self.macro_tcl and variant in (None, self.variant):
            v.append("MACRO_PLACEMENT_TCL=%s" % self.macro_tcl)
        return v

    def dirs(self, variant: str | None = None) -> dict:
        """ORFS's own output directories for this design and variant (``make print-%``: the design's
        DESIGN_NICKNAME, not its directory name, names them -- bp_fe_top -> bp_fe)."""
        p = subprocess.run(["make", "-s", "-C", self.flow_dir] + self.make_vars(variant) +
                           ["print-%s" % k for k in ("LOG_DIR", "RESULTS_DIR", "REPORTS_DIR", "OBJECTS_DIR")],
                           capture_output=True, text=True, timeout=120)
        got = dict(re.findall(r"^(\w+) = (.*)$", p.stdout, re.M))
        if len(got) < 4:
            raise RuntimeError("ORFS did not report its directories: %s" % (p.stdout + p.stderr)[-400:])
        return {"logs": Path(got["LOG_DIR"]), "results": Path(got["RESULTS_DIR"]),
                "reports": Path(got["REPORTS_DIR"]), "objects": Path(got["OBJECTS_DIR"])}

    def target(self, d: dict) -> str:
        """File target of the stage.  f2 stops at 6_report (metrics, RCX, STA): ``finish`` also streams the GDS
        through KLayout, which the servers do not have and the metrics do not need."""
        res, logs = d["results"], d["logs"]
        return str({"floorplan": res / "2_floorplan.odb", "place": res / "3_place.odb", "cts": res / "4_cts.odb",
                    "grt": res / "5_1_grt.odb", "route": res / "5_route.odb", "finish": logs / "6_report.log",
                    "signoff": logs / "6_report.log"}[self.stage])

    # the synthesis chain make checks (1_synth.rtlil -> 1_1_yosys.v -> 1_synth.v; timestamps kept, so nothing is
    # rebuilt) and the pre-macro floorplan (2_1, 2_2): a candidate variant starts at 2_3 macro placement
    SEED_FILES = ("1_synth.rtlil", "1_1_yosys.v", "1_synth.v", "1_synth.sdc", "clock_period.txt", "synth_stats.txt",
                  "mem.json", "mem_hierarchical.json", "2_1_floorplan.odb", "2_1_floorplan.sdc", "2_2_floorplan_io.odb")

    def seed_from_base(self) -> list:
        """Copy the base variant's synthesis and pre-macro floorplan (and its objects: merged libraries) into this
        variant, timestamps kept, so make starts at the macro placement (2_3).  Returns the copied files."""
        import shutil
        if not self.base_variant or self.base_variant == self.variant:
            return []
        src, dst = self.dirs(self.base_variant), self.dirs()
        copied = []
        for f in self.SEED_FILES:
            if (src["results"] / f).exists() and not (dst["results"] / f).exists():
                dst["results"].mkdir(parents=True, exist_ok=True)
                shutil.copy2(src["results"] / f, dst["results"] / f)
                copied.append(f)
        if src["objects"].exists() and not dst["objects"].exists():
            shutil.copytree(src["objects"], dst["objects"], symlinks=True)
        return copied

    def command(self, d: dict | None = None) -> list:
        return ["make", "-C", self.flow_dir] + self.make_vars() + [self.target(d or self.dirs())]


STAGE_ORDER = ("1_", "2_", "3_", "4_", "5_1", "5_2", "5_3", "6_")
STAGE_LAST = {"floorplan": "2_", "place": "3_", "cts": "4_", "grt": "5_1", "route": "5_3", "finish": "6_",
              "signoff": "6_"}
STAGE_REPORT = {"grt": "5_global_route.rpt", "route": "5_global_route.rpt", "finish": "6_finish.rpt",
                "signoff": "6_finish.rpt"}


def stage_metrics(log_dir: Path, stage: str) -> dict:
    """Merged per-step JSON metrics of the steps up to ``stage`` only: a variant that continued to finish still
    gives its f1 (grt) record from the grt-stage metrics (the finish keys come first in CANDIDATES)."""
    last = STAGE_ORDER.index(STAGE_LAST[stage])
    meta = {}
    for js in sorted(Path(log_dir).glob("*.json")):
        if not any(js.name.startswith(pfx) for pfx in STAGE_ORDER[:last + 1]):
            continue
        try:
            meta.update(json.loads(js.read_text()))
        except (OSError, ValueError):
            pass
    return meta


def parse_stage_report(text: str) -> dict:
    """ORFS stage report (5_global_route.rpt / 6_finish.rpt): worst hold slack = the first path of
    ``report_checks -path_delay min``, worst setup slack = the first of ``-path_delay max`` (2 decimals)."""
    out = {}
    for key, title in (("hold_wns_ns", "report_checks -path_delay min"), ("setup_wns_report_ns", "report_checks -path_delay max")):
        i = text.find(title)
        if i < 0:
            continue
        m = re.search(r"^\s*(-?[0-9.]+)\s+slack \((?:MET|VIOLATED)\)", text[i:], re.M)
        if m:
            out[key] = float(m.group(1))
    return out


def extract_macros(r: OrfsRun, d: dict, out_tcl: Path, timeout: int = 1800) -> Path:
    """ORFS's own macro placement (M1) as place_macro commands, from the 2_3 macro-stage database."""
    script = Path(out_tcl).with_suffix(".extract.tcl")
    script.write_text("read_db %s\nwrite_macro_placement %s\n" % (d["results"] / "2_3_floorplan_macro.odb", Path(out_tcl).resolve()))
    p = tools.run_group([tools.binary("openroad"), "-no_init", "-no_splash", "-exit", str(script)], timeout=timeout)
    if p.returncode != 0 or not Path(out_tcl).exists():
        raise RuntimeError("M1 extraction failed: %s" % (p.stdout + p.stderr)[-600:])
    return Path(out_tcl)


def run(r: OrfsRun) -> dict:
    """Run ORFS to ``r.stage``; then ``make metadata`` for f2.  Never raises: failures are recorded."""
    env = os.environ.copy()
    env.update({k: str(v) for k, v in r.env.items()})
    env.setdefault("OMP_NUM_THREADS", str(r.threads))      # OpenMP is not bounded by -threads (red line A.2)
    t0 = time.time()
    rec = {"variant": r.variant, "stage": r.stage, "design_config": r.design_config, "macro_tcl": r.macro_tcl}
    d = r.dirs()
    rec["seeded_from_base"] = r.seed_from_base()
    try:                                                # own process group: a timeout kills the sub-makes too
        p = tools.run_group(r.command(d), timeout=r.timeout_s, env=env)
        rec["returncode"] = p.returncode
        tail = (p.stdout + p.stderr)[-4000:]
    except subprocess.TimeoutExpired as e:
        rec["returncode"] = "timeout"
        tail = ((e.output or "") + (e.stderr or ""))[-4000:]
    rec["duration_s"] = round(time.time() - t0, 1)
    meta = stage_metrics(d["logs"], r.stage)
    rec.update(map_metrics(meta))
    rpt = d["reports"] / STAGE_REPORT.get(r.stage, "")
    if STAGE_REPORT.get(r.stage) and rpt.exists():     # hold WNS: not an ORFS 2024-12 metric (report only)
        h = parse_stage_report(rpt.read_text(errors="replace"))
        rec["hold_wns_ns"] = h.get("hold_wns_ns")
        rec["hold_wns_resolution_ns"] = 0.01
        rec["metric_sources"]["hold_wns_ns"] = "%s: report_checks -path_delay min" % rpt.name
        if r.stage == "grt":
            rec["grt_hold_wns_ns"] = rec["hold_wns_ns"]
    for k in ("finish__timing__drv__hold_violation_count", "globalroute__timing__drv__hold_violation_count"):
        if k in meta:
            rec.setdefault("hold_violation_count", meta[k])
    grt_log = d["logs"] / "5_1_grt.log"
    if grt_log.exists():
        g = parse_f1_log(grt_log.read_text(errors="replace"))
        rec.setdefault("gr_wl", g["gr_wl"])
        rec["gr_overflow_total"] = rec.get("gr_overflow_total", g["gr_overflow_total"])
        rec["gr_overflow_max"] = g["gr_overflow_max"]
    if r.stage == "signoff" and rec["returncode"] == 0:
        rec.update(run_signoff(r, env, d))
    rec["log_tail"] = tail[-1500:]
    return rec


def run_signoff(r: OrfsRun, env: dict, d: dict) -> dict:
    """f3: KLayout DRC and LVS via the ORFS ``drc`` / ``lvs`` targets (when the platform ships the decks).
    Canonical DRC (METRIC_CONVENTIONS s.8): signoff DRC when available, else the detailed-route count."""
    out = {"drc_detailed_route": None, "drc_klayout": None, "lvs_errors": None, "signoff": {}}
    for target in ("drc", "lvs"):
        try:
            p = tools.run_group(["make", "-C", r.flow_dir, "DESIGN_CONFIG=%s" % r.design_config,
                                 "FLOW_VARIANT=%s" % r.variant, target], timeout=r.timeout_s, env=env)
            out["signoff"][target] = p.returncode
        except subprocess.TimeoutExpired:
            out["signoff"][target] = "timeout"
    cnt = d["reports"] / "6_drc_count.rpt"
    if cnt.exists():
        try:
            out["drc_klayout"] = int(cnt.read_text().split()[0])
        except (ValueError, IndexError):
            pass
    lvs_log = d["logs"] / "6_lvs.log"
    if lvs_log.exists():
        t = lvs_log.read_text(errors="replace")
        if re.search(r"Congratulations! Netlists match|netlists match", t, re.I):
            out["lvs_errors"] = 0
        elif re.search(r"don't match|do not match|mismatch", t, re.I):
            out["lvs_errors"] = 1
    return out


def canonical_drc(rec: dict) -> dict:
    """drc_violations = signoff DRC (KLayout; max with Magic when both exist), else the detailed-route count."""
    rec = dict(rec)
    rec["drc_detailed_route"] = rec.get("drc_violations")
    signoff = [v for v in (rec.get("drc_klayout"), rec.get("drc_magic")) if v is not None]
    if signoff:
        rec["drc_violations"] = max(signoff)
    return rec
