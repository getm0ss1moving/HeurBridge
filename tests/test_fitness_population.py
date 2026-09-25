"""T5.2 / T5.3: refinability fitness, submodular pruning, probe, MAP-Elites islands."""

import itertools

import numpy as np

from heurbridge.evolve import fitness as FT
from heurbridge.evolve.population import Individual, Population


def test_refinability_fitness_terms():
    port = np.array([[1.0, 2.0, 3.0], [2.0, 1.0, 3.0]])
    f = FT.refinability_fitness([3.0, 3.0, 1.0], port, runtime_s=40.0)   # only helps design 3 (3 -> 1)
    assert abs(f["gain"] - 2.0 / 3) < 1e-12 and abs(f["runtime_pen"] - 0.1) < 1e-12
    assert abs(f["F"] - (2.0 / 3 - 0.2 * 7.0 / 3 - 0.1)) < 1e-12
    f0 = FT.refinability_fitness([1.0, 1.0, 1.0], None, runtime_s=1.0)
    assert f0["gain"] == 0.0 and abs(f0["F"] + 0.2) < 1e-12


def test_greedy_prune_is_near_optimal():
    rng = np.random.default_rng(0)
    B = rng.uniform(0.5, 1.5, (9, 6))
    B0 = np.ones(6) * 1.2
    q = 3
    greedy = FT.portfolio_value(B, B0, FT.greedy_prune(B, B0, q))
    best = max(FT.portfolio_value(B, B0, list(c)) for c in itertools.combinations(range(9), q))
    assert greedy >= (1 - 1 / np.e) * best - 1e-12 and greedy <= best + 1e-12


def test_probe_separates_systematic_from_erratic():
    rng = np.random.default_rng(1)
    S, M = 120, 5
    feats = rng.normal(size=(S, 3))
    xs = rng.uniform(0.2, 0.8, (S, M, 2))
    ids = np.repeat(np.arange(6), S // 6)
    sys_xh = xs + 0.1 * np.tanh(3 * (xs - 0.5))                        # systematic, a function of the solution
    err_xh = xs + 0.03 * rng.normal(size=xs.shape)                      # small but erratic
    w = np.ones(M)
    pi_sys = FT.predictability_probe(feats, sys_xh, xs - sys_xh, w, ids)
    pi_err = FT.predictability_probe(feats, err_xh, xs - err_xh, w, ids)
    assert pi_sys > 0.8 and pi_err < 0.2


def test_population_islands_and_portfolio():
    pop = Population(n_islands=2, migrate_every=1, q=2)
    rng = np.random.default_rng(0)
    for k in range(6):
        ind = Individual(id="p%d" % k, source="", sha256=str(k), family="M%d" % (2 + k % 3), runtime_s=0.5 * k,
                         B=list(rng.uniform(0.5, 1.5, 4)), island=k % 2)
        pop.score(ind)
        pop.add(ind)
    assert len(pop.select_parents(4, rng)) == 4
    n_before = len(pop.all)
    pop.migrate(1)
    assert len(pop.all) > n_before
    port = pop.portfolio()
    assert 1 <= len(port) <= 2 and all("@i" not in p for p in port)
    pop.reanchor({"p0": [0.1, 0.1, 0.1, 0.1]})
    assert "p0" in pop.portfolio()
