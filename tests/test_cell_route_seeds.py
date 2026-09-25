"""T2.3 cell seeds and T2.4 pattern router."""

import numpy as np

from heurbridge.core import synth
from heurbridge.core.cluster_design import build_clustered
from heurbridge.heuristics.cell import seeds as CS
from heurbridge.heuristics.cell.cluster import cluster_cells
from heurbridge.heuristics.route import pattern as RP


def test_cell_seeds_shapes_and_spread():
    des, ref = synth.make_design(seed=100, n_macros=6, n_cells=200, n_io=10)
    cd = build_clustered(des, cluster_cells(des, n=24))
    outs = {name: fn(cd, ref, np.random.default_rng(0)) for name, fn in CS.SEEDS.items()}
    for name, x in outs.items():
        assert x.shape == (cd.n_clusters, 2) and np.isfinite(x).all() and (x >= 0).all() and (x <= 1).all(), name
    assert outs["C3.spread06"].std(0).mean() >= outs["C1.quadratic"].std(0).mean()


def test_pattern_router_conservation_and_congestion():
    rng = np.random.default_rng(0)
    GX = GY = 16
    nets = [rng.integers(0, 16, (rng.integers(2, 5), 2)) for _ in range(120)]
    cap_h, cap_v = np.full((GX - 1, GY), 6.0), np.full((GX, GY - 1), 6.0)
    for name, cfg in RP.SEEDS.items():
        r = RP.route(nets, cap_h, cap_v, cfg, criticality=rng.uniform(size=len(nets)))
        pairs = np.concatenate([RP.mst_pairs(n) for n in nets])
        assert abs(r["U_h"].sum() - np.abs(pairs[:, 2] - pairs[:, 0]).sum()) < 1e-9, name
        assert abs(r["U_v"].sum() - np.abs(pairs[:, 3] - pairs[:, 1]).sum()) < 1e-9, name
    # ten identical connections (0,0)->(5,5) through capacity-2 edges, routed one at a time: once the first
    # L-shape fills up, later connections take the other L (usage spreads instead of piling up)
    ch, cv = np.full((GX - 1, GY), 2.0), np.full((GX, GY - 1), 2.0)
    r = RP.route([np.array([[0, 0], [5, 5]])] * 10, ch, cv, RP.RouteSeed(n_z=0, batch=1))
    row0, row5 = r["U_h"][:5, 0].max(), r["U_h"][:5, 5].max()
    assert row0 > 0 and row5 > 0 and abs(row0 - row5) <= 1
    greedy = RP.route([np.array([[0, 0], [5, 5]])] * 10, ch, cv, RP.RouteSeed(n_z=0, batch=10))
    assert greedy["overflow"] > r["overflow"]                    # no congestion feedback inside one batch
