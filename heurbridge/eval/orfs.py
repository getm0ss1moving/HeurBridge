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

from ..core import orient as O
from ..core.design import Design, Layout
from .f1 import parse_f1_log

STAGE_TARGET = {"floorplan": "floorplan", "place": "place", "cts": "cts", "grt": "globalroute",
                "route": "route", "finish": "finish", "signoff": "finish"}

CANDIDATES = {
    "setup_wns_ns": ["finish__timing__setup__ws", "detailedroute__timing__setup__ws", "globalroute__timing__setup__ws"],
    "hold_wns_ns": ["finish__timing__hold__ws", "detailedroute__timing__hold__ws", "globalroute__timing__hold__ws"],
    "setup_tns_ns": ["finish__timing__setup__tns", "detailedroute__timing__setup__tns", "globalroute__timing__setup__tns"],
    "hold_tns_ns": ["finish__timing__hold__tns", "detailedroute__timing__hold__tns"],
    "total_power_w": ["finish__power__total", "detailedroute__power__total"],
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


def macro_placement_tcl(design: Design, layout: Layout, exact: bool = True) -> str:
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
    design_config: str                # designs/nangate45/ariane133/config.mk
    variant: str                      # FLOW_VARIANT (one directory per evaluated candidate)
    macro_tcl: str | None = None
    stage: str = "finish"
    threads: int = 8
    timeout_s: int = 7200
    env: dict = field(default_factory=dict)

    def dirs(self) -> dict:
        cfg = Path(self.design_config)
        platform, name = cfg.parent.parent.name, cfg.parent.name
        base = Path(self.flow_dir)
        return {k: base / k / platform / name / self.variant for k in ("results", "logs", "reports", "objects")}

    def command(self) -> list:
        args = ["make", "-C", self.flow_dir, "DESIGN_CONFIG=%s" % self.design_config, "FLOW_VARIANT=%s" % self.variant,
                "NUM_CORES=%d" % self.threads]
        if self.macro_tcl:
            args.append("MACRO_PLACEMENT_TCL=%s" % self.macro_tcl)
        args.append(STAGE_TARGET[self.stage])
        return args


def run(r: OrfsRun) -> dict:
    """Run ORFS to ``r.stage``; then ``make metadata`` for f2.  Never raises: failures are recorded."""
    env = os.environ.copy()
    env.update({k: str(v) for k, v in r.env.items()})
    env.setdefault("OPENROAD_THREADS", str(r.threads))
    t0 = time.time()
    rec = {"variant": r.variant, "stage": r.stage, "design_config": r.design_config, "macro_tcl": r.macro_tcl}
    try:
        p = subprocess.run(r.command(), capture_output=True, text=True, timeout=r.timeout_s, env=env)
        rec["returncode"] = p.returncode
        tail = (p.stdout + p.stderr)[-4000:]
    except subprocess.TimeoutExpired:
        rec["returncode"] = "timeout"
        tail = ""
    rec["duration_s"] = round(time.time() - t0, 1)
    d = r.dirs()
    if r.stage in ("route", "finish", "signoff") and rec["returncode"] == 0:
        subprocess.run(["make", "-C", r.flow_dir, "DESIGN_CONFIG=%s" % r.design_config, "FLOW_VARIANT=%s" % r.variant,
                        "metadata"], capture_output=True, text=True, env=env, timeout=1800)
    meta = {}
    for cand in (d["reports"] / "metadata.json", d["logs"] / "metadata.json"):
        if cand.exists():
            meta = json.loads(cand.read_text())
            break
    if not meta:                                         # per-stage JSON logs
        for js in sorted(d["logs"].glob("*.json")):
            try:
                meta.update(json.loads(js.read_text()))
            except Exception:
                pass
    rec.update(map_metrics(meta))
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
        p = subprocess.run(["make", "-C", r.flow_dir, "DESIGN_CONFIG=%s" % r.design_config,
                            "FLOW_VARIANT=%s" % r.variant, target], capture_output=True, text=True, env=env, timeout=r.timeout_s)
        out["signoff"][target] = p.returncode
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
