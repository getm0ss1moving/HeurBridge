"""Cell-stage labels for the look-ahead predictor (heurbridge.bridge.lookahead)."""

import numpy as np

from heurbridge.bridge import lookahead as LA
from heurbridge.core import synth
from heurbridge.heuristics.cell.cluster import cluster_cells


def placed_case(seed=0):
    des, ref = synth.make_design(seed=seed, n_macros=6, n_cells=300, n_io=8)
    cl = cluster_cells(des, n=12, seed=0)
    return des, ref, np.asarray(cl)


def test_cluster_moments_match_direct_computation():
    des, ref, cl = placed_case(1)
    pos, cov, area = LA.cluster_moments(des, ref, cl)
    core = float(np.prod(des.core_wh))
    for c in range(int(cl.max()) + 1):
        m = (cl == c) & np.isfinite(ref.pos).all(1)
        if not m.any():
            continue
        w = des.area[m]
        p = ref.pos[m]
        mu = (w[:, None] * p).sum(0) / w.sum()
        d = p - mu
        assert np.allclose(pos[c], mu)
        assert np.allclose(cov[c], [(w * d[:, 0] ** 2).sum() / w.sum(), (w * d[:, 1] ** 2).sum() / w.sum(),
                                    (w * d[:, 0] * d[:, 1]).sum() / w.sum()])
        assert np.isclose(area[c], w.sum() / core)


def test_density_maps_hold_the_cell_area():
    des, ref, cl = placed_case(2)
    pos, cov, area = LA.cluster_moments(des, ref, cl)
    G = 32
    dm = LA.density_map(des, ref, cl, grid=G)
    gd = LA.gaussian_density(pos, cov, area, grid=G)
    assert dm.shape == gd.shape == (G, G)
    assert np.isclose(dm.sum() / G ** 2, area.sum())
    assert np.isclose(gd.sum() / G ** 2, area.sum(), rtol=1e-9)                # tails folded onto the edge bins
    assert (gd >= 0).all()


def test_gaussian_density_recovers_its_moments():
    pos = np.array([[0.4, 0.55]])
    cov = np.array([[0.004, 0.002, 0.0015]])                                    # rho = 0.53
    gd = LA.gaussian_density(pos, cov, np.array([0.1]), grid=128)
    c = (np.arange(128) + 0.5) / 128
    w = gd / gd.sum()
    mx, my = (w.sum(1) * c).sum(), (w.sum(0) * c).sum()
    vx = (w.sum(1) * (c - mx) ** 2).sum()
    vy = (w.sum(0) * (c - my) ** 2).sum()
    cxy = (w * np.outer(c - mx, c - my)).sum()
    assert np.allclose([mx, my], pos[0], atol=2e-3)
    assert np.allclose([vx, vy, cxy], cov[0], rtol=0.05, atol=1e-4)
    assert np.array_equal(gd, LA.gaussian_density(pos, cov, np.array([0.1]), grid=128))   # deterministic
