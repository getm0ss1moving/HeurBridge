"""T5.1 prompt parsing and T5.4 RLCE diagnosis (completeness, structural split, counterfactuals)."""

import numpy as np
import torch

from heurbridge.bridge.model import BridgeConfig, BridgeNet
from heurbridge.core import orient as O, project, synth
from heurbridge.evolve import prompts as PR, rlce
from heurbridge.heuristics.macro.registry import program_source
from heurbridge.pipeline import bridge_data as BD
from heurbridge.heuristics.cell.cluster import cluster_cells


def test_prompt_roundtrip():
    src = PR.with_markers(program_source("M6", 0))
    pre, block, post = PR.split_program(src)
    assert block.startswith(PR.START) and "def heuristic" in block and "class Grid" in pre
    resp = "Strategy: order by io weight to fix the corner group.\n```python\n" + block.replace("0.5", "0.7") + "```"
    p = PR.parse_response(resp)
    assert p.ok and "0.7" in p.block
    new = PR.assemble(src, p.block)
    assert new.count(PR.START) == 1 and "class Grid" in new
    assert not PR.parse_response("no code here").ok
    assert not PR.parse_response("```python\ndef heuristic(d,u,r): pass\n```").ok      # markers missing
    sysp = PR.system_prompt(PR.load_skill("v0"))
    assert "macro_order" in sysp and "EVOLVE" not in sysp and len(sysp.split()) < 1500


def test_rlce_diagnosis():
    des, ref = synth.make_design(seed=70, n_macros=10, n_cells=100, n_io=10, allow_macro_orients=True)
    cl = cluster_cells(des, n=10)
    base = ref.copy()
    base.pos[~des.is_macro & ~des.is_io & ~des.is_fixed] = np.nan
    b = BD.make_bundle(des, base, cl)
    star, _ = project.legalize_macros(des, base)
    rng = np.random.default_rng(0)
    xh = star.copy()
    mo = b.view.macro_order
    xh.pos[mo[:3]] = rng.uniform(0.1, 0.9, (3, 2))            # three far-misplaced macros
    xh.orient[mo[3]] = O.MX if xh.orient[mo[3]] != O.MX else O.MY   # one orientation mismatch
    xh, _ = project.legalize_macros(des, xh)
    model = BridgeNet(BridgeConfig(width=64, layers=2, edge_dim=16, pe_freqs=6, t_dim=32)).eval()
    d = rlce.diagnose(des, b.view, b.graph, model, b.scorer, xh, star, rho=0.02, k_g=4, K=4, ig_steps=64)
    # midpoint-rule IG on a surrogate with ReLU kinks converges as O(1/steps) (measured: 26%, 17%, 12%, 6%
    # at 16..128 steps); 64 steps (task spec) -> require < 25% and report the gap in every diagnosis
    assert abs(d.completeness_gap) < 0.25 * (abs(d.J["J0_hat"] - d.J["J0_star"]) + 1e-3)
    assert d.structural[:3].all() and d.structural[3]
    assert d.groups and len(d.deltas) == len(d.groups) and d.g_star is not None
    assert max(d.deltas) >= -1e-9 and "Decisive group" in d.evidence


def test_structural_groups_bounded_and_ranked():
    des, ref = synth.make_design(seed=71, n_macros=30, n_cells=60, n_io=8)
    cl = cluster_cells(des, n=6)
    base = ref.copy()
    base.pos[~des.is_macro & ~des.is_io & ~des.is_fixed] = np.nan
    b = BD.make_bundle(des, base, cl)
    lay, _ = project.legalize_macros(des, base)
    M = len(b.view.macro_order)
    alpha = np.linspace(1.0, 0.0, M)                          # macro 0 carries the most attribution
    everything = np.ones(M, bool)                             # weak bridge: every macro structural
    g = rlce.structural_groups(des, b.view, lay, everything, alpha, k_g=6, prox=100.0, max_group=8)
    assert 1 <= len(g) <= 6 and all(1 <= len(x) <= 8 for x in g)
    assert 0 in g[0]                                          # the top group is seeded at the top macro
    flat = [i for x in g for i in x]
    assert len(flat) == len(set(flat))                        # groups are disjoint
    few = np.zeros(M, bool)
    few[[3, 4]] = True                                        # small components stay whole
    g2 = rlce.structural_groups(des, b.view, lay, few, alpha, prox=100.0)
    assert sorted(i for x in g2 for i in x) == [3, 4]


def test_evidence_without_positive_counterfactual():
    des, ref = synth.make_design(seed=72, n_macros=6, n_cells=40, n_io=6)
    cl = cluster_cells(des, n=4)
    base = ref.copy()
    base.pos[~des.is_macro & ~des.is_io & ~des.is_fixed] = np.nan
    b = BD.make_bundle(des, base, cl)
    lay, _ = project.legalize_macros(des, base)
    M = len(b.view.macro_order)
    dg = rlce.Diagnosis(alpha=np.zeros(M), cluster_residual=0.0, completeness_gap=0.0, structural=np.ones(M, bool),
                        groups=[[0, 1], [2]], deltas=[-0.01, -0.002], g_star=1, structural_share=1.0,
                        reachable_share=0.0, J={"B_parent": 1.0, "alpha_bridge": 1.0, "J0_star": 1.0, "J0_hat": 0.9})
    txt = rlce.evidence_text(des, b.view, lay, lay, dg)
    assert "No structural group improves" in txt and "Decisive group" not in txt
