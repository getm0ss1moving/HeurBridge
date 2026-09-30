"""Cell-stage labels for the look-ahead predictor (sketch redesign S2, 30 Sep 2026).

What the placer did with the cells of one macro layout, in the bridge's normalized core frame ([0, 1]^2):

  cluster_pos   (C, 2)  area-weighted centroid of each cell cluster
  cluster_cov   (C, 3)  area-weighted second moments about it: var_x, var_y, cov_xy
  cluster_area  (C,)    the cluster's cell area as a fraction of the core area
  density       (G, G)  cell area per bin / bin area (cells only; [ix, iy] = [x bin, y bin])

``gaussian_density`` turns (pos, cov, area) back into a density map, so a prediction, a label and the quadratic
control all have the same form.  Pure numpy, deterministic.
"""

from __future__ import annotations

import numpy as np

GRID = 64


def cell_mask(design, layout, cluster_of) -> np.ndarray:
    """Objects that belong to a cell cluster and are placed."""
    return (np.asarray(cluster_of) >= 0) & np.isfinite(layout.pos).all(1)


def cluster_moments(design, layout, cluster_of):
    """(cluster_pos (C,2), cluster_cov (C,3), cluster_area (C,)) of a placed layout; empty clusters sit at the core
    centre with zero area and zero spread."""
    cluster_of = np.asarray(cluster_of)
    C = int(cluster_of.max()) + 1 if (cluster_of >= 0).any() else 0
    m = cell_mask(design, layout, cluster_of)
    cid = cluster_of[m]
    w = np.asarray(design.area, np.float64)[m]
    p = np.asarray(layout.pos, np.float64)[m]
    W = np.bincount(cid, weights=w, minlength=C)
    nz = W > 0
    pos = np.full((C, 2), 0.5)
    for d in (0, 1):
        pos[nz, d] = np.bincount(cid, weights=w * p[:, d], minlength=C)[nz] / W[nz]
    dx, dy = p[:, 0] - pos[cid, 0], p[:, 1] - pos[cid, 1]
    cov = np.zeros((C, 3))
    for k, v in enumerate((dx * dx, dy * dy, dx * dy)):
        cov[nz, k] = np.bincount(cid, weights=w * v, minlength=C)[nz] / W[nz]
    core = float(np.prod(design.core_wh))
    return pos, cov, W / core


def density_map(design, layout, cluster_of, grid: int = GRID) -> np.ndarray:
    """(G, G) cell area per bin over the bin's area: each cell's area is deposited at its centre (cells are far
    smaller than a bin: an IBM cell is about 1e-5 of the core, a 64 x 64 bin 2.4e-4)."""
    m = cell_mask(design, layout, np.asarray(cluster_of))
    p = np.asarray(layout.pos, np.float64)[m]
    ix = np.clip((p[:, 0] * grid).astype(int), 0, grid - 1)
    iy = np.clip((p[:, 1] * grid).astype(int), 0, grid - 1)
    a = np.asarray(design.area, np.float64)[m] / float(np.prod(design.core_wh))
    out = np.zeros((grid, grid))
    np.add.at(out, (ix, iy), a)
    return out * grid * grid


def gaussian_density(pos, cov, area, grid: int = GRID, floor: float = 1e-6, chunk: int = 256) -> np.ndarray:
    """(G, G) density of clusters spread as correlated Gaussians (pos, cov as in ``cluster_moments``; area = core
    fraction).  Mass outside the core is folded onto the edge bins, so the map holds each cluster's whole area.
    Exact per x bin up to the y-conditional being evaluated at the bin centre."""
    from scipy.special import erf
    pos, cov, area = np.asarray(pos, np.float64), np.asarray(cov, np.float64), np.asarray(area, np.float64)
    keep = area > 0
    pos, cov, area = pos[keep], cov[keep], area[keep]
    edges = np.linspace(0.0, 1.0, grid + 1)
    xc = 0.5 * (edges[:-1] + edges[1:])

    def mass(mu, sigma):                              # (..., G) probability per bin, tails folded onto edge bins
        c = 0.5 * (1 + erf((edges - mu[..., None]) / (sigma[..., None] * np.sqrt(2))))
        m = np.diff(c, axis=-1)
        m[..., 0] += c[..., 0]
        m[..., -1] += 1 - c[..., -1]
        return m

    out = np.zeros((grid, grid))
    for s in range(0, len(area), chunk):
        p, v, a = pos[s:s + chunk], cov[s:s + chunk], area[s:s + chunk]
        sx, sy = np.sqrt(np.maximum(v[:, 0], floor)), np.sqrt(np.maximum(v[:, 1], floor))
        rho = np.clip(v[:, 2] / (sx * sy), -0.95, 0.95)
        mx = mass(p[:, 0], sx)                                                    # (c, G)
        my_mu = p[:, 1, None] + (rho * sy / sx)[:, None] * (xc[None, :] - p[:, 0, None])  # (c, G): y mean per x bin
        my = mass(my_mu, np.broadcast_to((sy * np.sqrt(1 - rho ** 2))[:, None], my_mu.shape))  # (c, G, G)
        out += np.einsum("c,ci,cij->ij", a, mx, my)
    return out * grid * grid
