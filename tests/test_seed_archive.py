"""T2.7 driver: seeds -> P_M -> f1 -> top -> 'f2' -> archive -> local search; resume; failures by name."""

from dataclasses import dataclass, field

import numpy as np
import torch

from heurbridge.archive.store import Archive
from heurbridge.core import synth
from heurbridge.eval import cost, f0
from heurbridge.heuristics.cell.cluster import cluster_cells
from heurbridge.heuristics.macro.registry import all_programs
from heurbridge.pipeline import seed_archive as SA
from heurbridge.pipeline.evaluators import TRACK_A_WEIGHTS, Evaluator


@dataclass
class F0Eval(Evaluator):
    name: str = "f0_fake"
    fidelity: int = 1
    weights: dict = field(default_factory=lambda: dict(TRACK_A_WEIGHTS))
    required_gates: tuple = ()
    calls: int = 0

    def evaluate(self, design, layout, run_id, workdir):
        self.calls += 1
        ctx = f0.F0Context(design, layout.orient)
        p = torch.as_tensor(layout.pos, dtype=torch.float32)
        r = ctx.rudy(p)
        return {"hpwl_um": float(ctx.hpwl_exact(p)[0]), "rudy_of_pct": 100.0 * float(r["overflow_ratio"][0]), "returncode": 0}


def test_seed_campaign_dev(tmp_path):
    des, ref = synth.make_design(seed=50, n_macros=8, n_cells=80, n_io=8)
    cl = cluster_cells(des, n=8)
    progs = [p for p in all_programs() if p["id"] in ("M6.v0", "M7.v0", "M3.v1")]
    progs.append({"id": "BAD", "sha256": "x", "source": "def heuristic(d,u,r):\n    raise ValueError('boom')\n"})
    ev = F0Eval()
    base_rec = ev.evaluate(des, ref, "base", tmp_path)
    baseline = cost.Baseline.from_records(des.id, [base_rec] * 3)
    arch = Archive(tmp_path / "arch", min_fidelity=1)
    cfg = SA.SeedConfig(seeds=2, top_f2=4, ls_steps=3, ls_neighbours=3)
    s = SA.seed_design(des, ref, progs, ev, None, arch, baseline, tmp_path / "out", cfg, cluster=cl, log=lambda x: None)
    rows = SA.Ledger(tmp_path / "out" / des.id / "evals.jsonl").rows
    assert rows["%s.BAD.s0.f1" % des.id]["status"] == "program_error" and rows["%s.BAD.s0.f1" % des.id]["J"] == float("inf")
    assert sum(r["status"] == "ok" for r in rows.values()) >= 6
    assert 1 <= len(s["archive_top"]) <= 5 and s["archive_top"] == sorted(s["archive_top"])
    assert (tmp_path / "arch" / "DEV_ARCHIVE_MIN_FIDELITY_1").exists()
    n_calls = ev.calls
    SA.seed_design(des, ref, progs, ev, None, arch, baseline, tmp_path / "out", cfg, cluster=cl, log=lambda x: None)
    assert ev.calls == n_calls                      # resumed: nothing re-evaluated
