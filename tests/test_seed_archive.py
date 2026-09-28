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


def test_distinct_rows_by_layout():
    from heurbridge.pipeline.seed_archive import distinct, layout_key
    a = {"pos_macros": [[0.1, 0.2], [0.3, 0.4]], "orient_macros": [0, 4], "J": 1.0}
    b = dict(a, J=1.0)                                            # same layout from another seed
    c = dict(a, orient_macros=[0, 5])                             # same positions, other orientation
    d = dict(a, pos_macros=[[0.1, 0.2], [0.3, 0.4 + 1e-6]])
    assert layout_key(a) == layout_key(b) != layout_key(c) != layout_key(d)
    assert distinct([a, b, c, d, b]) == [a, c, d]


@dataclass
class FailingEval(Evaluator):
    """Fails every layout: with a named ORFS-style tool error, a timeout or an unnamed crash."""
    name: str = "fail_fake"
    fidelity: int = 1
    weights: dict = field(default_factory=lambda: dict(TRACK_A_WEIGHTS))
    required_gates: tuple = ()
    mode: str = "tool"
    calls: int = 0

    def evaluate(self, design, layout, run_id, workdir):
        self.calls += 1
        if self.mode == "tool":
            return {"returncode": 2, "design_config": "x", "failure": "DPL-0036 Detailed placement failed."}
        if self.mode == "timeout":
            return {"returncode": "timeout", "design_config": "x", "failure": "timeout in 3_5_place_dp"}
        return {"returncode": -11, "failure": None}


def test_deterministic_failures_are_reused(tmp_path):
    des, ref = synth.make_design(seed=1, n_macros=4, n_cells=40, n_io=6)
    base = cost.Baseline.from_records(des.id, [{"hpwl_um": 1.0, "rudy_of_pct": 1.0}])
    for mode, reused in (("tool", True), ("timeout", True), ("crash", False)):
        ev = FailingEval(mode=mode)
        ledger = SA.Ledger(tmp_path / mode / "evals.jsonl")
        r1 = SA._eval(ev, des, ref, base, "a", tmp_path / mode, ledger, {})
        r2 = SA._eval(ev, des, ref.copy(), base, "b", tmp_path / mode, ledger, {})
        assert r1["status"] == r2["status"] == "eval_failed" and r2["J"] == float("inf")
        assert ev.calls == (1 if reused else 2), mode
        assert (r2.get("reused_from") == "a") == reused
        if reused:
            assert r2["record"]["failure"] == r1["record"]["failure"]
        # a resumed ledger indexes the failure the same way
        assert (SA.Ledger(tmp_path / mode / "evals.jsonl").by_layout != {}) == reused



@dataclass
class TimingEval(Evaluator):
    """Track-B-like f1 record whose setup WNS fails the 0.02 ns guard against the baseline."""
    name: str = "timing_fake"
    fidelity: int = 1
    weights: dict = field(default_factory=lambda: {"rwl": 0.3, "of": 0.15})
    required_gates: tuple = ("setup", "hold")

    def evaluate(self, design, layout, run_id, workdir):
        return {"returncode": 0, "gr_wl": 110.0, "gr_overflow_total": 0, "setup_wns_ns": -0.60, "hold_wns_ns": 0.1}


def test_stored_rows_rescored_under_current_gate_rule(tmp_path):
    des, ref = synth.make_design(seed=2, n_macros=4, n_cells=40, n_io=6)
    base = cost.Baseline.from_records(des.id, [{"gr_wl": 100.0, "gr_overflow_total": 0, "setup_wns_ns": -0.5,
                                                "hold_wns_ns": 0.1}])
    ledger = SA.Ledger(tmp_path / "evals.jsonl")
    ev = TimingEval()
    r = SA._eval(ev, des, ref, base, "x", tmp_path, ledger, {})
    assert r["gates"]["setup"]["status"] == "fail" and r["J"] == r["J_raw"] < float("inf")   # f1: reported only
    old = dict(r, J=float("inf"))                   # the same row as written under cost_v1 (gate enforced at f1)
    (tmp_path / "old").mkdir()
    SA.Ledger(tmp_path / "old" / "evals.jsonl").add(old)
    r2 = SA._eval(ev, des, ref, base, "x", tmp_path, SA.Ledger(tmp_path / "old" / "evals.jsonl"), {})
    assert r2["J"] == r["J"] and r2["gates"]["setup"]["enforced"] is False
