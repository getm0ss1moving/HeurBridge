"""T4 partners: each returns a legal layout that is never worse than its input under its own f0 criterion."""

import numpy as np
import pytest

from heurbridge import partners as P
from heurbridge.bridge.graph import build_graph
from heurbridge.bridge.model import BridgeConfig, BridgeNet
from heurbridge.core import project, synth
from heurbridge.core.cluster_design import MacroStageScorer, build_clustered
from heurbridge.evolve import sandbox as SB
from heurbridge.heuristics.cell.cluster import cluster_cells

TINY = BridgeConfig(width=64, layers=2, edge_dim=16, pe_freqs=6, t_dim=32)


@pytest.fixture(scope="module")
def case():
    des, ref = synth.make_design(seed=60, n_macros=10, n_cells=120, n_io=10)
    cl = cluster_cells(des, n=12)
    base = ref.copy()
    base.pos[~des.is_macro & ~des.is_io & ~des.is_fixed] = np.nan
    scorer = MacroStageScorer(build_clustered(des, cl), base)
    view = SB.make_view(des, base, cl)
    rng = np.random.default_rng(0)
    h = base.copy()
    mm = des.is_macro & ~des.is_fixed
    h.pos[mm] = rng.uniform(0.15, 0.85, (mm.sum(), 2))
    h, _ = project.legalize_macros(des, h)
    g = build_graph(des, base, cl)
    return des, h, scorer, view, g


def _check(des, res, scorer, h):
    assert project.check_macros(des, res.layout)["ok"]
    assert scorer(res.layout) <= scorer(h) + 1e-9


def test_none_memetic_repertoire(case):
    des, h, scorer, view, g = case
    rng = np.random.default_rng(1)
    for part in (P.NonePartner(), P.MemeticPartner(scorer), P.RepertoirePartner(scorer, view.macro_aff, view.macro_order)):
        res = part(des, h, rng, budget_s=3.0)
        _check(des, res, scorer, h)
        assert res.wall_s <= 3.0 + 1.5


def test_generator_partners(case):
    des, h, scorer, view, g = case
    import torch
    m = BridgeNet(TINY).eval()
    torch.nn.init.normal_(m.dec[-1].weight, std=0.1)
    rng = np.random.default_rng(2)
    res = P.FrozenGenPartner(m, g, scorer)(des, h, rng)
    _check(des, res, scorer, h)
    res = P.CotrainedPartner(m, g, scorer)(des, h, rng)
    _check(des, res, scorer, h)
    assert res.info["alpha"] in (0.0, 0.25, 0.5, 1.0)
    assert res.info["disp"] >= 0.0


def test_random_guard_control(case):
    """E0 control: same guard as the bridge along a random displacement of matched length."""
    des, h, scorer, view, g = case
    part = P.RandomGuardPartner(g, scorer, scale=0.05)
    r1 = part(des, h, np.random.default_rng(3))
    _check(des, r1, scorer, h)                                   # alpha = 0 (raw) is always a candidate
    assert r1.info["alpha"] in (0.0, 0.25, 0.5, 1.0) and r1.info["scores"][0] == pytest.approx(scorer(h))
    r2 = part(des, h, np.random.default_rng(3))
    assert np.array_equal(r1.layout.pos, r2.layout.pos, equal_nan=True)   # deterministic (cells are NaN)
