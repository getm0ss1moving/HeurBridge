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
