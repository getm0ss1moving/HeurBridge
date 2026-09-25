# Shared helpers prepended to every macro seed program (T2.2).  Pure numpy/math/heapq only, so the
# concatenated program passes the sandbox allow-list.  All coordinates are normalized to the core box.
import math
import heapq
import numpy as np


def clip_centres(c, sz):
    return np.clip(c, sz / 2.0, 1.0 - sz / 2.0)


def overlap_pairs(c, sz):
    """(M,M) pairwise overlap areas (zero diagonal)."""
    dx = np.minimum(c[:, None, 0] + sz[:, None, 0] / 2, c[None, :, 0] + sz[None, :, 0] / 2) - \
        np.maximum(c[:, None, 0] - sz[:, None, 0] / 2, c[None, :, 0] - sz[None, :, 0] / 2)
    dy = np.minimum(c[:, None, 1] + sz[:, None, 1] / 2, c[None, :, 1] + sz[None, :, 1] / 2) - \
        np.maximum(c[:, None, 1] - sz[:, None, 1] / 2, c[None, :, 1] - sz[None, :, 1] / 2)
    a = np.clip(dx, 0, None) * np.clip(dy, 0, None)
    np.fill_diagonal(a, 0.0)
    return a


def obstacle_overlap(c, sz, obst):
    if len(obst) == 0:
        return np.zeros(len(c))
    dx = np.minimum(c[:, None, 0] + sz[:, None, 0] / 2, obst[None, :, 2]) - np.maximum(c[:, None, 0] - sz[:, None, 0] / 2, obst[None, :, 0])
    dy = np.minimum(c[:, None, 1] + sz[:, None, 1] / 2, obst[None, :, 3]) - np.maximum(c[:, None, 1] - sz[:, None, 1] / 2, obst[None, :, 1])
    return (np.clip(dx, 0, None) * np.clip(dy, 0, None)).sum(1)


def boundary_dist(c, sz):
    lo, hi = c - sz / 2, c + sz / 2
    return np.minimum(np.minimum(lo[:, 0], lo[:, 1]), np.minimum(1 - hi[:, 0], 1 - hi[:, 1]))


def wirelength(c, aff, io_pull, io_w):
    """Connectivity-weighted Manhattan distance between macros and to their fixed anchors."""
    d = np.abs(c[:, None, 0] - c[None, :, 0]) + np.abs(c[:, None, 1] - c[None, :, 1])
    return 0.5 * float((aff * d).sum()) + float((io_w * np.abs(c - io_pull).sum(1)).sum())


class Grid:
    """Occupancy grid over the core for greedy macro placement (lower-left cell indexing)."""

    def __init__(self, n, obst, halo=(0.0, 0.0)):
        self.n = n
        self.occ = np.zeros((n, n), dtype=np.int32)
        self.hx, self.hy = halo
        for xl, yl, xh, yh in obst:
            i0, i1 = max(0, int(math.floor((xl - self.hx) * n))), min(n, int(math.ceil((xh + self.hx) * n)))
            j0, j1 = max(0, int(math.floor((yl - self.hy) * n))), min(n, int(math.ceil((yh + self.hy) * n)))
            if i1 > i0 and j1 > j0:
                self.occ[i0:i1, j0:j1] = 1

    def cells(self, w, h):
        return max(1, int(math.ceil((w + self.hx) * self.n - 1e-9))), max(1, int(math.ceil((h + self.hy) * self.n - 1e-9)))

    def free(self, fw, fh):
        n = self.n
        if fw > n or fh > n:
            return np.zeros((0, 0), dtype=bool)
        ps = np.zeros((n + 1, n + 1), dtype=np.int64)
        ps[1:, 1:] = self.occ.cumsum(0).cumsum(1)
        s = ps[fw:, fh:] - ps[:-fw, fh:] - ps[fw:, :-fh] + ps[:-fw, :-fh]
        return s == 0

    def centres(self, fw, fh):
        """(nfx, nfy, 2) centres of footprints whose lower-left cell is (i, j)."""
        nfx, nfy = self.n - fw + 1, self.n - fh + 1
        ii, jj = np.meshgrid(np.arange(nfx), np.arange(nfy), indexing="ij")
        return np.stack([(ii + fw / 2.0) / self.n, (jj + fh / 2.0) / self.n], -1)

    def place(self, i, j, fw, fh):
        self.occ[i:i + fw, j:j + fh] = 1


def greedy_place(order, sz, cost_fn, grid, rng=None, temp=0.0):
    """Place macros in ``order`` one by one at the free slot minimizing cost_fn(k, centres (P,2), placed) ->
    (P,) costs; temp > 0 samples from a Boltzmann distribution instead (rng required)."""
    placed = {}
    out = {}
    for k in order:
        fw, fh = grid.cells(sz[k, 0], sz[k, 1])
        free = grid.free(fw, fh)
        if free.size == 0 or not free.any():
            continue
        cen = grid.centres(fw, fh)
        idx = np.flatnonzero(free.ravel())
        cand = cen.reshape(-1, 2)[idx]
        cost = cost_fn(k, cand, placed)
        if temp > 0 and rng is not None:
            z = -(cost - cost.min()) / max(temp, 1e-12)
            p = np.exp(z)
            p /= p.sum()
            t = int(rng.choice(len(idx), p=p))
        else:
            t = int(np.argmin(cost))
        flat = idx[t]
        i, j = divmod(int(flat), free.shape[1])
        grid.place(i, j, fw, fh)
        c = cand[t]
        placed[k] = c
        out[k] = c
    return out


def write_back(design, pos_macros):
    """Copy design.init_pos and write macro centres (dict k -> centre, k indexes macro_order)."""
    pos = np.array(design.init_pos, dtype=float)
    mo = design.macro_order
    for k, c in pos_macros.items():
        pos[mo[k]] = c
    missing = [k for k in range(len(mo)) if k not in pos_macros]
    for k in missing:                                   # unplaceable macros: centre of the core (P_M resolves)
        pos[mo[k]] = 0.5
    return pos
