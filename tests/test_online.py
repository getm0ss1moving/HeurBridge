"""T6.1 online macro-stage solve: Lemma 3 deployment rule, no LLM calls, failures reported."""

import math

import numpy as np

from heurbridge.bridge.model import BridgeConfig, BridgeNet
from heurbridge.core import synth
from heurbridge.heuristics.cell.cluster import cluster_cells
from heurbridge.heuristics.macro.registry import all_programs
from heurbridge.online.solve import solve_macro
from heurbridge.pipeline import bridge_data as BD


def test_online_deploys_best_or_baseline():
    des, ref = synth.make_design(seed=90, n_macros=6, n_cells=60, n_io=8)
    cl = cluster_cells(des, n=8)
    base = ref.copy()
    base.pos[~des.is_macro & ~des.is_io & ~des.is_fixed] = np.nan
    b = BD.make_bundle(des, base, cl)
    progs = [p for p in all_programs() if p["id"] in ("M6.v0", "M7.v0")]
    progs.append({"id": "BAD", "source": "def heuristic(d, u, r):\n    raise RuntimeError('x')\n"})
    bridge = BridgeNet(BridgeConfig(width=64, layers=2, edge_dim=16, pe_freqs=6, t_dim=32)).eval()
    f1 = b.scorer
    r = solve_macro(des, base, b.view, b.graph, progs, bridge, f1, f2=f1, baseline_J2=math.inf, k=3, seeds=2, K=4)
    assert r.llm_calls == 0 and r.deployed != "baseline" and math.isfinite(r.J)
    assert any(c["status"].startswith("program_") for c in r.candidates)          # failure reported by name
    r2 = solve_macro(des, base, b.view, b.graph, progs, bridge, f1, f2=f1, baseline_J2=-1.0, k=3, seeds=2, K=4)
    assert r2.deployed == "baseline" and r2.J == -1.0                               # Lemma 3: baseline kept
