"""Route-stage seeds: a vectorized congestion-aware pattern router (task T2.4; pilot Routing.pattern).

Nets -> GCell pins -> 2-pin connections by Prim's MST on Manhattan distance.  Connections are routed in
batches (order: HPWL ascending | criticality descending | congestion-aware); inside a batch every
connection picks the cheapest of the two L-shapes and n_z Z-shapes, costed in O(1) each with prefix sums
of the current edge costs; after each batch the usage is added with difference arrays.  Edge cost
functions: linear, quadratic or exponential in the utilization u/cap.  Output: demand tensors
U_h (GX-1, GY) and U_v (GX, GY-1) in tracks, plus per-connection routed lengths.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class RouteSeed:
    order: str = "hpwl"          # hpwl | criticality | congestion
    cost: str = "quadratic"      # linear | quadratic | exp
    n_z: int = 3
    batch: int = 256


def mst_pairs(cells: np.ndarray) -> np.ndarray:
    cells = np.unique(cells, axis=0)
    n = len(cells)
    if n < 2:
        return np.zeros((0, 4), dtype=np.int64)
    inT = np.zeros(n, bool)
    inT[0] = True
    best = np.abs(cells - cells[0]).sum(1).astype(float)
    parent = np.zeros(n, dtype=np.int64)
    best[0] = np.inf
    out = []
    for _ in range(n - 1):
        j = int(np.argmin(np.where(inT, np.inf, best)))
        out.append((*cells[parent[j]], *cells[j]))
        inT[j] = True
        d = np.abs(cells - cells[j]).sum(1)
        upd = (~inT) & (d < best)
        best[upd] = d[upd]
        parent[upd] = j
        best[j] = np.inf
    return np.array(out, dtype=np.int64)


def edge_cost(u, cap, kind):
    r = u / np.maximum(cap, 1e-9)
    if kind == "linear":
        return 1.0 + r
    if kind == "exp":
        return 1.0 + np.expm1(np.clip(3.0 * (r - 0.5), -5, 20)).clip(min=0)
    return 1.0 + r ** 2 + 10.0 * np.clip(r - 1.0, 0, None) ** 2


def _h_seg(PH, y, xa, xb):
    """Sum of horizontal edge costs on row y from x=min to x=max (PH: (GX, GY) prefix over edges)."""
    lo, hi = np.minimum(xa, xb), np.maximum(xa, xb)
    return PH[hi, y] - PH[lo, y]


def _v_seg(PV, x, ya, yb):
    lo, hi = np.minimum(ya, yb), np.maximum(ya, yb)
    return PV[x, hi] - PV[x, lo]


def route(pins_gcell: list, cap_h: np.ndarray, cap_v: np.ndarray, cfg: RouteSeed | None = None,
          criticality: np.ndarray | None = None, rng: np.random.Generator | None = None) -> dict:
    """pins_gcell: per net an (k, 2) int array of GCell coordinates."""
    cfg = cfg or RouteSeed()
    GX, GY = cap_v.shape[0], cap_h.shape[1]
    conns, net_of = [], []
    for k, cells in enumerate(pins_gcell):
        p = mst_pairs(np.asarray(cells, dtype=np.int64))
        conns.append(p)
        net_of.append(np.full(len(p), k))
    C = np.concatenate(conns) if conns else np.zeros((0, 4), np.int64)
    net_of = np.concatenate(net_of) if net_of else np.zeros(0, np.int64)
    uh, uv = np.zeros_like(cap_h, dtype=float), np.zeros_like(cap_v, dtype=float)
    if len(C) == 0:
        return {"U_h": uh, "U_v": uv, "length": np.zeros(0)}
    x0, y0, x1, y1 = C.T
    hp = np.abs(x1 - x0) + np.abs(y1 - y0)
    if cfg.order == "criticality" and criticality is not None:
        order = np.lexsort((hp, -criticality[net_of]))
    else:
        order = np.argsort(hp, kind="stable")
    length = np.zeros(len(C))
    for s in range(0, len(order), cfg.batch):
        b = order[s:s + cfg.batch]
        ch, cv = edge_cost(uh, cap_h, cfg.cost), edge_cost(uv, cap_v, cfg.cost)
        PH = np.zeros((GX, GY))
        PH[1:] = np.cumsum(ch, 0)
        PV = np.zeros((GX, GY))
        PV[:, 1:] = np.cumsum(cv, 1)
        a0, b0, a1, b1 = x0[b], y0[b], x1[b], y1[b]
        cand_cost, cand = [], []
        # L1: horizontal on row b0, then vertical on column a1;  L2: vertical on column a0, then horizontal on row b1
        cand_cost.append(_h_seg(PH, b0, a0, a1) + _v_seg(PV, a1, b0, b1)); cand.append(("L1", None))
        cand_cost.append(_v_seg(PV, a0, b0, b1) + _h_seg(PH, b1, a0, a1)); cand.append(("L2", None))
        for z in range(cfg.n_z):
            t = (z + 1) / (cfg.n_z + 1)
            xm = np.round(a0 + t * (a1 - a0)).astype(np.int64)
            cand_cost.append(_h_seg(PH, b0, a0, xm) + _v_seg(PV, xm, b0, b1) + _h_seg(PH, b1, xm, a1)); cand.append(("ZH", t))
            ym = np.round(b0 + t * (b1 - b0)).astype(np.int64)
            cand_cost.append(_v_seg(PV, a0, b0, ym) + _h_seg(PH, ym, a0, a1) + _v_seg(PV, a1, ym, b1)); cand.append(("ZV", t))
        pick = np.argmin(np.stack(cand_cost, 0), 0)
        dh = np.zeros((GX + 1, GY))
        dv = np.zeros((GX, GY + 1))

        def add_h(y, xa, xb, m):
            lo, hi = np.minimum(xa, xb)[m], np.maximum(xa, xb)[m]
            np.add.at(dh, (lo, y[m]), 1.0)
            np.add.at(dh, (hi, y[m]), -1.0)

        def add_v(x, ya, yb, m):
            lo, hi = np.minimum(ya, yb)[m], np.maximum(ya, yb)[m]
            np.add.at(dv, (x[m], lo), 1.0)
            np.add.at(dv, (x[m], hi), -1.0)
        for ci, (kind, t) in enumerate(cand):
            m = pick == ci
            if not m.any():
                continue
            if kind == "L1":
                add_h(b0, a0, a1, m); add_v(a1, b0, b1, m)
            elif kind == "L2":
                add_v(a0, b0, b1, m); add_h(b1, a0, a1, m)
            elif kind == "ZH":
                xm = np.round(a0 + t * (a1 - a0)).astype(np.int64)
                add_h(b0, a0, xm, m); add_v(xm, b0, b1, m); add_h(b1, xm, a1, m)
            else:
                ym = np.round(b0 + t * (b1 - b0)).astype(np.int64)
                add_v(a0, b0, ym, m); add_h(ym, a0, a1, m); add_v(a1, ym, b1, m)
        uh += np.cumsum(dh, 0)[:GX - 1]
        uv += np.cumsum(dv, 1)[:, :GY - 1]
        length[b] = np.abs(a1 - a0) + np.abs(b1 - b0)
    of = np.clip(uh - cap_h, 0, None).sum() + np.clip(uv - cap_v, 0, None).sum()
    return {"U_h": uh, "U_v": uv, "length": length, "overflow": float(of), "wirelength": float(uh.sum() + uv.sum())}


SEEDS = {"R1.hpwl_quad": RouteSeed("hpwl", "quadratic"), "R2.crit_quad": RouteSeed("criticality", "quadratic"),
         "R3.hpwl_exp": RouteSeed("hpwl", "exp"), "R4.hpwl_linear_L": RouteSeed("hpwl", "linear", n_z=0)}
