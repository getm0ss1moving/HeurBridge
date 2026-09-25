"""Fidelity-1 evaluator (task T1.4).

Backends
  openroad    Track B.  read_db / read_def with macros FIXED -> global_placement (routability- and
              timing-driven when timing data exist) -> detailed_placement -> check_placement ->
              estimate_parasitics -placement -> report_wns/report_tns -> global_route
              -congestion_iterations 30 -> overflow / GR wirelength -> estimate_parasitics
              -global_routing -> report_wns/report_tns.
  dreamplace  Track A.  DREAMPlace global + legal placement with macros fixed, then f0 RUDY/HPWL.
  hbgp        Track-A development stand-in (heurbridge.eval.gp), then f0 RUDY/HPWL.
Output: {hpwl, gr_wl, gr_overflow_total, gr_overflow_max, wns_place, tns_place, wns_gr, tns_gr,
runtime_s, backend, unchecked: [...]}.  Metrics a backend cannot produce are None and listed in
``unchecked`` (never assumed to pass).  Setup timing uses report_wns/report_tns (max-delay, i.e.
setup, consistent with metrics_schema: worst_slack_max).
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import torch

from ..core import defio, orient as O
from ..core.design import Design, Layout
from .f0 import F0Config, F0Context

KEYS = ("hpwl", "gr_wl", "gr_overflow_total", "gr_overflow_max", "wns_place", "tns_place", "wns_gr", "tns_gr")


# =============================================================================== OpenROAD (Track B)
F1_TCL = r"""
# HeurBridge f1 (Track B) -- generated
{reads}
{sdc}
# macros are fixed at the evaluated positions
foreach inst [[ord::get_db_block] getInsts] {{
  if {{[[$inst getMaster] isBlock]}} {{ $inst setPlacementStatus FIRM }}
}}
{rc_setup}
set_thread_count {threads}
{routing_layers}
set t0 [clock milliseconds]
global_placement {gp_flags} -density {density}
detailed_placement
set cp_ok 1
if {{[catch {{check_placement -verbose}} msg]}} {{ set cp_ok 0; puts "HB_CHECK_PLACEMENT_FAIL $msg" }}
puts "HB_CHECK_PLACEMENT $cp_ok"
{timing_place}
global_route -congestion_iterations {grt_iters} -congestion_report_file {cong_rpt} -verbose
{timing_gr}
puts "HB_RUNTIME_MS [expr {{[clock milliseconds] - $t0}}]"
write_def {out_def}
"""

TIMING_PLACE = """estimate_parasitics -placement
puts "HB_WNS_PLACE [sta::worst_slack -max]"
puts "HB_TNS_PLACE [sta::total_negative_slack -max]"
"""
TIMING_GR = """estimate_parasitics -global_routing
puts "HB_WNS_GR [sta::worst_slack -max]"
puts "HB_TNS_GR [sta::total_negative_slack -max]"
"""


@dataclass
class OpenroadJob:
    def_path: str | None = None
    db_path: str | None = None
    lefs: list = field(default_factory=list)
    libs: list = field(default_factory=list)
    sdc: str | None = None
    rc_setup_tcl: str | None = None          # platform setRC / set_wire_rc script (Track B platforms)
    min_layer: str | None = None
    max_layer: str | None = None
    density: float = 0.7
    threads: int = 8
    grt_iters: int = 30
    routability: bool = True
    timing: bool = True


def make_f1_tcl(job: OpenroadJob, work: Path) -> str:
    reads = []
    if job.db_path:
        reads.append("read_db %s" % job.db_path)
    else:
        reads += ["read_lef %s" % l for l in job.lefs]
        reads.append("read_def %s" % job.def_path)
    reads += ["read_liberty %s" % l for l in job.libs]
    has_timing = bool(job.timing and job.libs and job.sdc)
    flags = []
    if job.routability:
        flags.append("-routability_driven")
    if has_timing:
        flags.append("-timing_driven")
    rl = ""
    if job.min_layer and job.max_layer:
        rl = "set_routing_layers -signal %s-%s" % (job.min_layer, job.max_layer)
    return F1_TCL.format(
        reads="\n".join(reads), sdc=("read_sdc %s" % job.sdc) if job.sdc else "",
        rc_setup=("source %s" % job.rc_setup_tcl) if job.rc_setup_tcl else "", threads=job.threads,
        routing_layers=rl, gp_flags=" ".join(flags), density=job.density,
        timing_place=TIMING_PLACE if has_timing else 'puts "HB_TIMING unchecked"',
        grt_iters=job.grt_iters, cong_rpt=work / "congestion.rpt",
        timing_gr=TIMING_GR if has_timing else "", out_def=work / "f1_out.def")


_GRT_WL = re.compile(r"Total wirelength:\s*([0-9.eE+-]+)\s*um")
_GRT_OVF_TOTAL = re.compile(r"^\s*Total\s+\d+\s+\d+\s+[0-9.]+%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)", re.M)


def parse_f1_log(text: str) -> dict:
    """Parse the HB_* markers and FastRoute's summary table from an OpenROAD f1 log."""
    out = {k: None for k in KEYS}

    def last(tag):
        m = re.findall(r"^%s\s+(\S+)" % tag, text, re.M)
        return float(m[-1]) if m and m[-1] not in ("INF", "-INF", "nan") else None
    out["wns_place"], out["tns_place"] = last("HB_WNS_PLACE"), last("HB_TNS_PLACE")
    out["wns_gr"], out["tns_gr"] = last("HB_WNS_GR"), last("HB_TNS_GR")
    rt = last("HB_RUNTIME_MS")
    out["runtime_s"] = rt / 1000.0 if rt is not None else None
    cp = last("HB_CHECK_PLACEMENT")
    out["check_placement_ok"] = None if cp is None else bool(cp)
    m = _GRT_WL.findall(text)
    out["gr_wl"] = float(m[-1]) if m else None
    # FastRoute final table row: "Total <resource> <demand> <usage%> <max H> / <max V> / <total overflow>"
    tot = re.findall(r"^\s*Total\s+(\d+)\s+(\d+)\s+([0-9.]+)%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)", text, re.M)
    if tot:
        _, _, _, mh, mv, total = tot[-1]
        out["gr_overflow_total"] = float(total)
        out["gr_overflow_max"] = float(max(int(mh), int(mv)))
    return out


def run_openroad_f1(job: OpenroadJob, work: str | Path, openroad: str = "openroad", timeout: int = 7200,
                    env: dict | None = None, docker_image: str | None = None) -> dict:
    """Run the f1 script; returns the parsed metrics plus HPWL recomputed from the output DEF."""
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    tcl = work / "f1.tcl"
    tcl.write_text(make_f1_tcl(job, work))
    cmd = [openroad, "-no_init", "-no_splash", "-exit", str(tcl)]
    if docker_image:
        mounts = sorted({str(Path(p).resolve().parent) for p in [tcl, *(job.lefs or []), *(job.libs or []),
                                                               job.def_path or tcl, job.db_path or tcl, job.sdc or tcl]})
        cmd = ["docker", "run", "--rm"] + sum([["-v", "%s:%s" % (m, m)] for m in mounts], []) + \
              [docker_image, "bash", "-lc", "openroad -no_init -no_splash -exit %s" % tcl]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        log = p.stdout + "\n" + p.stderr
        rc = p.returncode
    except subprocess.TimeoutExpired as e:
        log, rc = (e.stdout or "") if isinstance(e.stdout, str) else "", "timeout"
    (work / "f1.log").write_text(log)
    out = parse_f1_log(log)
    out.update({"backend": "openroad", "returncode": rc, "wall_s": round(time.time() - t0, 2)})
    out["unchecked"] = [k for k in KEYS if out.get(k) is None]
    return out


# =============================================================================== Track A (bookshelf)
def trackA_metrics(design: Design, layout: Layout, f0cfg: F0Config | None = None, device="cpu") -> dict:
    ctx = F0Context(design, layout.orient, cfg=f0cfg, device=device)
    p = torch.as_tensor(layout.pos, dtype=torch.float32, device=device)
    with torch.no_grad():
        r = ctx.rudy(p)
        return {"hpwl": float(ctx.hpwl_exact(p)[0]), "rudy_overflow": float(r["overflow"][0]),
                "rudy_overflow_ratio": float(r["overflow_ratio"][0]), "rudy_peak": float(r["peak"][0]),
                "density_overflow": float(ctx.density_overflow(p)[0]), "channel_shortage": float(ctx.channel_shortage(p, r)[0])}


def run_hbgp_f1(design: Design, layout: Layout, gp_cfg=None, f0cfg: F0Config | None = None,
                threads: int | None = 1) -> dict:
    """Track-A f1 with the HB-GP stand-in: place cells with macros fixed, then f0 metrics.

    ``threads`` (default 1): torch's multi-threaded CPU reductions make HB-GP non-reproducible across runs
    (ibm01, same layout, 3 threads: HPWL 2,646,210 vs 2,651,174; 1 thread: 2,649,741.5 twice), which breaks
    the T1.4 determinism requirement and turns the guard's min over candidates into a winner's curse when
    the guard and the final cost share evaluations.  None keeps the caller's setting."""
    import torch
    from .gp import GPConfig, place
    t0 = time.time()
    prev = torch.get_num_threads()
    if threads:
        torch.set_num_threads(threads)
    try:
        placed, info = place(design, layout, gp_cfg or GPConfig())
        m = trackA_metrics(design, placed, f0cfg)
    finally:
        torch.set_num_threads(prev)
    info = dict(info, threads=threads or prev)
    out = {k: None for k in KEYS}
    out.update({"hpwl": m["hpwl"], "gr_overflow_total": m["rudy_overflow"], "rudy": m, "gp": info, "backend": "hbgp",
                "runtime_s": round(time.time() - t0, 2)})
    out["unchecked"] = ["gr_wl", "gr_overflow_max", "wns_place", "tns_place", "wns_gr", "tns_gr", "vias", "power"]
    return out, placed


def dreamplace_params(aux: str, out_dir: str, gpu: bool = True, iters: int = 1000, target_density: float = 0.9,
                      legalize: bool = True, seed: int = 0) -> dict:
    """DREAMPlace JSON parameters for a bookshelf design whose macros were written FIXED into the .pl."""
    return {"aux_input": aux, "gpu": int(gpu), "num_bins_x": 512, "num_bins_y": 512,
            "global_place_stages": [{"num_bins_x": 512, "num_bins_y": 512, "iteration": iters, "learning_rate": 0.01,
                                     "wirelength": "weighted_average", "optimizer": "nesterov"}],
            "target_density": target_density, "density_weight": 8e-5, "gamma": 4.0, "random_seed": seed,
            "scale_factor": 1.0, "ignore_net_degree": 100, "enable_fillers": 1, "gp_noise_ratio": 0.025,
            "global_place_flag": 1, "legalize_flag": int(legalize), "detailed_place_flag": 0, "stop_overflow": 0.07,
            "dtype": "float32", "plot_flag": 0, "random_center_init_flag": 1, "sort_nets_by_degree": 0,
            "num_threads": 8, "result_dir": out_dir, "routability_opt_flag": 0}
