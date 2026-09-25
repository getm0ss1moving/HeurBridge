"""Evaluator adapters: one interface over the fidelity backends (f1/f2, Track A/B).

Each evaluator declares its fidelity, the J terms it can produce and the gates it can check; the
cost function is called with exactly those, so a missing metric is never silently treated as passing.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..core.design import Design, Layout
from ..eval import cost

TRACK_A_WEIGHTS = {"rwl": cost.WEIGHTS["rwl"], "of": cost.WEIGHTS["of"]}


@dataclass
class Evaluator:
    name: str
    fidelity: int
    weights: dict = field(default_factory=lambda: dict(cost.WEIGHTS))
    required_gates: tuple | None = None

    def evaluate(self, design: Design, layout: Layout, run_id: str, workdir: Path) -> dict:
        raise NotImplementedError

    def score(self, record: dict, base: cost.Baseline) -> cost.CostResult:
        return cost.evaluate(record, base, fidelity=self.fidelity, weights=self.weights,
                             required_gates=self.required_gates)


@dataclass
class HBGPEvaluator(Evaluator):
    """Track-A development stand-in: HB-GP cell placement with macros fixed + f0 metrics (fidelity 1)."""
    name: str = "hbgp_f1"
    fidelity: int = 1
    weights: dict = field(default_factory=lambda: dict(TRACK_A_WEIGHTS))
    required_gates: tuple | None = ()
    gp_cfg: object = None
    f0cfg: object = None
    cluster_of: object = None          # cell -> cluster id; if given, post-placement cluster centroids are recorded

    def evaluate(self, design, layout, run_id, workdir):
        from ..eval.f1 import run_hbgp_f1
        out, placed = run_hbgp_f1(design, layout, self.gp_cfg, self.f0cfg)
        rec = {"run_id": run_id, "backend": "hbgp", "hpwl_um": out["hpwl"],
               "rudy_overflow": out["rudy"]["rudy_overflow"], "rudy_overflow_ratio": out["rudy"]["rudy_overflow_ratio"],
               "rudy_peak": out["rudy"]["rudy_peak"], "density_overflow": out["rudy"]["density_overflow"],
               "rudy_of_pct": 100.0 * out["rudy"]["rudy_overflow_ratio"],     # bounded OF proxy (percent of demand)
               "gp_overflow": out["gp"]["overflow"], "lg_failed": out["gp"].get("lg_failed"),
               "runtime_s": out["runtime_s"], "unchecked": out["unchecked"], "returncode": 0}
        if self.cluster_of is not None:
            rec["cluster_pos"] = cluster_centroids(design, placed, self.cluster_of).tolist()
        return rec


def cluster_centroids(design, layout, cluster_of) -> "np.ndarray":
    """Area-weighted centroids (normalized) of each cell cluster in a placed layout."""
    import numpy as np
    m = (cluster_of >= 0) & layout.placed
    n = int(cluster_of.max()) + 1 if (cluster_of >= 0).any() else 0
    w = design.area[m]
    cid = cluster_of[m]
    cnt = np.bincount(cid, weights=w, minlength=n)
    out = np.full((n, 2), 0.5)
    nz = cnt > 0
    for d_ in (0, 1):
        out[nz, d_] = np.bincount(cid, weights=w * layout.pos[m, d_], minlength=n)[nz] / cnt[nz]
    return out


@dataclass
class OrfsEvaluator(Evaluator):
    """Track B: ORFS flow with our macro placement (stage 'grt' = f1, 'finish' = f2)."""
    name: str = "orfs"
    fidelity: int = 2
    flow_dir: str = ""
    design_config: str = ""
    threads: int = 8
    timeout_s: int = 7200

    def evaluate(self, design, layout, run_id, workdir):
        from ..eval import orfs
        workdir = Path(workdir)
        workdir.mkdir(parents=True, exist_ok=True)
        tcl = workdir / "macros.tcl"
        tcl.write_text(orfs.macro_placement_tcl(design, layout))
        stage = "finish" if self.fidelity >= 2 else "grt"
        rec = orfs.run(orfs.OrfsRun(flow_dir=self.flow_dir, design_config=self.design_config, variant=run_id,
                                    macro_tcl=str(tcl), stage=stage, threads=self.threads, timeout_s=self.timeout_s,
                                    env={"EDA_THREADS": self.threads}))
        if self.fidelity == 1:                      # f1 timing comes from the GRT-stage estimate
            for a, b in (("grt_setup_wns_ns", "setup_wns_ns"), ("grt_setup_tns_ns", "setup_tns_ns"),
                         ("grt_hold_wns_ns", "hold_wns_ns")):
                if a in rec:
                    rec[b] = rec[a]
        rec["run_id"] = run_id
        (workdir / "record.json").write_text(json.dumps(rec, indent=1, default=str))
        return rec


F1_B_WEIGHTS = {k: v for k, v in cost.WEIGHTS.items() if k != "via"}     # vias are not known before detailed routing


@dataclass
class MiniflowEvaluator(Evaluator):
    """Track-B f1 through the minimal Nangate45 flow (eval/miniflow.py): GP + repair_design + DP + GRT + timing.

    ``timing_stage`` selects the parasitics behind the canonical timing/power fields: 'place' (default;
    GR-stage parasitics fail on some layouts in the local OpenROAD build, see eval/miniflow.py) or 'gr'.
    The baseline and every candidate of a campaign must use the same stage (it is stored in each record)."""
    name: str = "miniflow_f1"
    fidelity: int = 1
    weights: dict = field(default_factory=lambda: dict(F1_B_WEIGHTS))
    required_gates: tuple | None = ("setup", "hold")
    flow_dir: str = ""
    platform_design: str = ""
    fp_odb: str = ""
    threads: int = 6
    docker_image: str | None = "efabless/openlane:master-arm64v8"
    timeout_s: int = 7200
    exact: bool = False               # place_macro -exact exists only in newer OpenROAD builds
    timing_stage: str = "place"
    gr_timing: bool = False           # GR-parasitics timing (unreliable in the local build; opt-in)

    def evaluate(self, design, layout, run_id, workdir):
        from ..eval import miniflow as MF
        from ..eval.orfs import macro_placement_tcl
        work = Path(workdir) / run_id
        work.mkdir(parents=True, exist_ok=True)
        tcl = work / "macros.tcl"
        tcl.write_text(macro_placement_tcl(design, layout, exact=self.exact))
        p, d = MF.Nangate45(self.flow_dir), MF.from_orfs(self.flow_dir, self.platform_design)
        crashes = []
        for attempt in (0, 1):             # one retry on a crash or bad_alloc; every failure is recorded by name
            rc_raw, log, wall = MF.run_tool("openroad", MF.f1_script(p, d, Path(self.fp_odb), tcl, work, self.threads,
                                                                          self.gr_timing or self.timing_stage == "gr"),
                                            work / ("f1.tcl" if attempt == 0 else "f1_retry.tcl"),
                                            docker_image=self.docker_image, timeout=self.timeout_s)
            m, failure, rc = MF.f1_outcome(rc_raw, log, self.timing_stage)
            if attempt == 0 and MF.should_retry(rc, failure):
                crashes.append({"attempt": attempt, "returncode": rc_raw, "wall_s": wall, "failure": failure})
                continue
            break
        keys = ("gr_wl", "gr_overflow_total", "gr_overflow_max", "setup_wns_ns", "setup_tns_ns", "hold_wns_ns",
                "total_power_w", "timing_stage", "wns_place", "tns_place", "hold_place", "power_place_w",
                "wns_gr", "tns_gr", "hold_gr", "power_gr_w", "gr_parasitics_error", "check_placement_ok", "runtime_s")
        rec = {"run_id": run_id, "backend": "miniflow", "returncode": rc, "returncode_raw": rc_raw, "wall_s": wall,
               "crashes": crashes, "failure": failure, **{k: m.get(k) for k in keys},
               "unchecked": ["vias", "drc (f2)", "lvs (f3)"]}
        if m.get("check_placement_ok") is False:
            rec["returncode"] = "check_placement_failed"
        (work / "record.json").write_text(json.dumps(rec, indent=1, default=str))
        return rec


@dataclass
class MiniflowF2Evaluator(Evaluator):
    """Track-B f2 through the mini-flow (eval/miniflow.f2_script): f1 placement, CTS + repair_timing, GRT,
    detailed route, fill, OpenRCX + STA.  All five J terms; gates setup, hold, DRC (LVS is f3)."""
    name: str = "miniflow_f2"
    fidelity: int = 2
    weights: dict = field(default_factory=lambda: dict(cost.WEIGHTS))
    required_gates: tuple | None = ("setup", "hold", "drc")
    flow_dir: str = ""
    platform_design: str = ""
    fp_odb: str = ""
    threads: int = 6
    docker_image: str | None = "efabless/openlane:master-arm64v8"
    timeout_s: int = 7200
    exact: bool = False
    repair_timing: bool = True

    def evaluate(self, design, layout, run_id, workdir):
        from ..eval import miniflow as MF
        from ..eval.orfs import macro_placement_tcl
        work = Path(workdir) / run_id
        work.mkdir(parents=True, exist_ok=True)
        tcl = work / "macros.tcl"
        tcl.write_text(macro_placement_tcl(design, layout, exact=self.exact))
        p, d = MF.Nangate45(self.flow_dir), MF.from_orfs(self.flow_dir, self.platform_design)
        crashes = []
        for attempt in (0, 1):
            rc, log, wall = MF.run_tool("openroad", MF.f2_script(p, d, Path(self.fp_odb), tcl, work, self.threads,
                                                                 repair_timing=self.repair_timing),
                                        work / ("f2.tcl" if attempt == 0 else "f2_retry.tcl"),
                                        docker_image=self.docker_image, timeout=self.timeout_s)
            m = MF.f2_metrics(log)
            failure = None if (rc == 0 and m["done"]) else MF.classify_failure(rc, log)
            if attempt == 0 and MF.should_retry(rc, failure):
                crashes.append({"attempt": attempt, "returncode": rc, "wall_s": wall, "failure": failure})
                continue
            break
        rec = {"run_id": run_id, "backend": "miniflow_f2", "returncode": 0 if failure is None else rc, "wall_s": wall,
               "crashes": crashes, "failure": failure, **{k: v for k, v in m.items() if k != "done"},
               "unchecked": ["lvs (f3)"]}
        if m.get("check_placement_ok") is False:
            rec["returncode"] = "check_placement_failed"
        (work / "record.json").write_text(json.dumps(rec, indent=1, default=str))
        return rec

