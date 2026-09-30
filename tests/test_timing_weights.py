"""Track-B timing-aware macro cost: the timing probe's table, critical-net weights, timing-aware local search."""

import math
import types
from dataclasses import dataclass, field

import numpy as np
import pytest

from heurbridge.archive.store import Archive
from heurbridge.core import synth
from heurbridge.core import timing_weights as TW
from heurbridge.eval import cost, orfs
from heurbridge.heuristics.cell.cluster import cluster_cells
from heurbridge.heuristics.macro.registry import all_programs
from heurbridge.pipeline import seed_archive as SA
from heurbridge.pipeline.evaluators import Evaluator


def named_design(seed=0, n_macros=4):
    des, ref = synth.make_design(seed=seed, n_macros=n_macros, n_cells=40, n_io=6)
    des.pin_names = ["P%d" % p for p in range(des.n_pins)]
    return des, ref


def macro_pin_keys(des):
    return [(des.names[des.pin_obj[p]], des.pin_names[p], p) for p in np.flatnonzero(des.is_macro[des.pin_obj])]


def test_parse_probe_table():
    text = ("inst\tpin\tslack_max\tslack_min\n"
            "m0\tA[0]\t-0.1234\t0.0312\n"
            "m0\tCLK\tINF\t0.2\n"
            "m1\t-\tMISSING\tMISSING\n"
            "m2\tQ\tNOPIN\tNOPIN\n"
            "m2\tD\t1e+30\t-1e+30\n")
    s = orfs.parse_macro_slacks(text)
    assert s[("m0", "A[0]")] == (-0.1234, 0.0312)
    assert s[("m0", "CLK")] == (None, 0.2)                     # unconstrained setup
    assert ("m1", "-") not in s and s[("m2", "Q")] == (None, None) and s[("m2", "D")] == (None, None)


def test_probe_script_template():
    t = orfs.MACRO_SLACK_TCL % {"odb": "3_place.odb", "sdc": "3_place.sdc", "names": "/w/n.names", "out": "/w/o.tsv"}
    assert "load_design 3_place.odb 3_place.sdc" in t and "estimate_parasitics -placement" in t
    assert "{/w/n.names}" in t and "{/w/o.tsv}" in t and "slack_max" in t and "HB_MACRO_SLACK done" in t


def test_weights_follow_criticality():
    des, ref = named_design()
    keys = macro_pin_keys(des)
    net_of = des.net_of_pin()
    rng = np.random.default_rng(0)
    slacks = {(k[0], k[1]): (float(rng.uniform(-0.3, 0.5)), 0.1) for k in keys}
    w, info = TW.critical_net_weights(des, slacks, clock_period_ns=2.0, beta=4.0, frac=0.1)
    s, _ = TW.macro_net_slack(des, slacks)
    macro_nets = np.isfinite(s)
    assert np.array_equal(w[~macro_nets], des.net_weight[~macro_nets])            # nets without macro pins: kept
    assert np.all(w[macro_nets & (s >= 0.2)] == des.net_weight[macro_nets & (s >= 0.2)])   # enough slack: kept
    worst = np.nanargmin(s)
    assert w[worst] == pytest.approx(des.net_weight[worst] * 5.0)                 # most critical: 1 + beta
    crit = np.flatnonzero(macro_nets & (s < 0.2))
    order = crit[np.argsort(s[crit])]
    assert np.all(np.diff(w[order] / des.net_weight[order]) <= 1e-12)             # lower slack, higher weight
    assert info["nets_weighted"] == int((s < 0.2).sum()) and info["worst_slack_ns"] == pytest.approx(s[worst])
    w2, _ = TW.critical_net_weights(des, slacks, clock_period_ns=2.0, beta=4.0, frac=0.1)
    assert np.array_equal(w, w2)                                                   # deterministic


def test_worst_pin_of_a_net_and_unconstrained_pins():
    des, ref = named_design(seed=3)
    keys = macro_pin_keys(des)
    net_of = des.net_of_pin()
    by_net = {}
    for name, pin, p in keys:
        by_net.setdefault(int(net_of[p]), []).append((name, pin))
    net, pins = next((n, ps) for n, ps in by_net.items() if len(ps) >= 2)
    slacks = {pins[0]: (0.3, 0.0), pins[1]: (-0.2, 0.0)}
    s, info = TW.macro_net_slack(des, slacks)
    assert s[net] == -0.2 and info["matched"] == 2
    s, info = TW.macro_net_slack(des, {pins[0]: (None, 0.0)})
    assert np.isnan(s[net]) and info["unconstrained"] == 1
    w, info = TW.critical_net_weights(des, {pins[0]: (None, 0.0)}, clock_period_ns=1.0)
    assert np.array_equal(w, des.net_weight) and "worst_slack_ns" not in info       # nothing constrained: unchanged


def test_weighted_design_is_a_copy():
    des, ref = named_design(seed=4)
    w = des.net_weight * 2.0
    d2 = TW.weighted_design(des, w)
    assert np.array_equal(d2.net_weight, w) and np.array_equal(des.net_weight, w / 2.0)
    assert d2.source["net_weights"]["tag"] == "tw" and len(d2.source["net_weights"]["sha256_16"]) == 16
    for bad in (w[:-1], np.where(np.arange(len(w)) == 0, 0.0, w), np.where(np.arange(len(w)) == 0, np.nan, w)):
        with pytest.raises(ValueError):
            TW.weighted_design(des, bad)
    with pytest.raises(ValueError):
        TW.critical_net_weights(des, {}, clock_period_ns=0.0)
    des.pin_names = None
    with pytest.raises(ValueError):
        TW.macro_net_slack(des, {})


def test_slacks_roundtrip(tmp_path):
    s = {("m0", "A[0]"): (-0.1, 0.02), ("m1", "D"): (None, None)}
    TW.save_slacks(tmp_path / "s.json", s, {"clock_period_ns": 1.8})
    s2, meta = TW.load_slacks(tmp_path / "s.json")
    assert s2 == s and meta["clock_period_ns"] == 1.8


@dataclass
class ScriptedTiming(Evaluator):
    """f1-like record for a scripted local search: wirelength falls as macro ``m`` moves right (twice as fast as up);
    setup fails (against the baseline) once m is right of ``state['x0']``, the local search's start (set by the
    scripted neighbours; the heuristics' layouts before it are all on time)."""
    name: str = "timing_scripted"
    fidelity: int = 1
    weights: dict = field(default_factory=lambda: {"rwl": 0.3, "of": 0.15})
    required_gates: tuple = ("setup", "hold")
    m: int = 0
    state: dict = field(default_factory=dict)

    def evaluate(self, design, layout, run_id, workdir):
        x, y = float(layout.pos[self.m, 0]), float(layout.pos[self.m, 1])
        late = x > self.state.get("x0", math.inf) + 1e-12
        return {"returncode": 0, "gr_wl": 10.0 - 2.0 * x - y, "gr_overflow_total": 0,
                "setup_wns_ns": -0.6 if late else -0.5, "hold_wns_ns": 0.1}


def test_timing_ok():
    assert SA.timing_ok({"gates": {"setup": {"status": "pass"}, "hold": {"status": "pass"}}})
    assert not SA.timing_ok({"gates": {"setup": {"status": "fail"}, "hold": {"status": "pass"}}})
    assert not SA.timing_ok({"gates": {"hold": {"status": "fail"}}})
    assert SA.timing_ok({})


def test_ls_timing_accepts_only_timing_clean_moves(tmp_path, monkeypatch):
    # Scripted, so the result does not hang on a random search path (it did: the clustering differs between METIS
    # versions, and on 231 the unscripted search never proposed a late move).  Each step offers two moves of one
    # macro: right (the lower J, and late) and up (lower J than staying, on time).
    des, ref = synth.make_design(seed=11, n_macros=6, n_cells=60, n_io=8)
    cl = cluster_cells(des, n=8)
    m = int(np.flatnonzero(des.is_macro & ~des.is_fixed)[0])
    base = cost.Baseline.from_records(des.id, [{"gr_wl": 1.0, "gr_overflow_total": 0, "setup_wns_ns": -0.5,
                                                "hold_wns_ns": 0.1}])
    progs = [p for p in all_programs() if p["id"] in ("M6.v0", "M7.v0")]
    monkeypatch.setattr(SA.project, "legalize_macros",
                        lambda design, lay, halo=0.0: (lay, types.SimpleNamespace(ok=True, failed=[], mean_disp=0.0)))
    runs = {}
    for flag in (False, True):
        ev = ScriptedTiming(m=m)

        def scripted(design, layout, rng, n, state=ev.state, d=0.01):
            state.setdefault("x0", float(layout.pos[m, 0]))
            right, up = layout.copy(), layout.copy()
            right.pos[m, 0] += d
            up.pos[m, 1] += d
            return [("right", right), ("up", up)]

        accepted = []
        monkeypatch.setattr(SA, "neighbours", scripted)
        monkeypatch.setattr(SA, "_insert", lambda archive, design, lay, row, e, acc=accepted: acc.append(row))
        cfg = SA.SeedConfig(seeds=1, top_f2=2, ls_steps=6, ls_neighbours=2, ls_timing=flag, seed=3)
        SA.seed_design(des, ref, progs, ev, None, Archive(tmp_path / str(flag) / "a", min_fidelity=1), base,
                       tmp_path / str(flag) / "o", cfg, cluster=cl, log=lambda x: None)
        runs[flag] = [r for r in accepted if r.get("program") == "LS"]
    assert runs[False] and not any(SA.timing_ok(r) for r in runs[False])        # control: J alone takes the late move
    assert runs[True] and all(SA.timing_ok(r) for r in runs[True])
