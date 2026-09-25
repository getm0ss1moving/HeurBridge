"""Cell-stage seeds on cluster centroids (task T2.3).

  quadratic      clique-model quadratic placement of clusters with macros and IOs fixed
  spread(alpha)  quadratic + rank-based spreading toward uniform density (alpha = 0.3, 0.6; pilot)
  dataflow       region assignment: clusters ordered by graph distance (BFS depth) from the fixed objects
                 (IOs, macros) and assigned to a grid of regions in that order, then centred in their region
All seeds are deterministic given rng and return (C, 2) normalized cluster centres; the certified projection
P_C (initialize cells at centroids + reduced global placement + legalization) turns them into cell layouts.
"""

from __future__ import annotations

import math
from collections import deque

import numpy as np

from ...core.cluster_design import ClusteredDesign
from ...core.design import Layout


def quadratic(cd: ClusteredDesign, macro_layout: Layout, rng=None) -> np.ndarray:
    return cd.quadratic_clusters(macro_layout)


def spread(x: np.ndarray, alpha: float, rng: np.random.Generator | None = None, jitter: float = 0.0) -> np.ndarray:
    """Rank-based shifting of each coordinate toward the uniform distribution, strength alpha."""
    out = x.copy()
    for d in (0, 1):
        r = np.argsort(np.argsort(x[:, d], kind="stable"), kind="stable")
        u = (r + 0.5) / len(x)
        out[:, d] = (1 - alpha) * x[:, d] + alpha * (0.05 + 0.9 * u)
    if jitter and rng is not None:
        out = out + rng.normal(0.0, jitter, out.shape)
    return np.clip(out, 0.0, 1.0)


def quadratic_spread(cd, macro_layout, alpha: float, rng=None):
    return spread(quadratic(cd, macro_layout), alpha, rng)


def dataflow(cd: ClusteredDesign, macro_layout: Layout, rng=None, regions: int | None = None) -> np.ndarray:
    d = cd.design
    n, nk, C = d.n_objects, cd.n_keep, cd.n_clusters
    adj = [[] for _ in range(n)]
    objs = d.pin_obj[d.pin_idx]
    for k in range(d.n_nets):
        o = np.unique(objs[d.net_ptr[k]:d.net_ptr[k + 1]])
        if 2 <= len(o) <= 64:
            for a in o:
                adj[a].extend(int(b) for b in o if b != a)
    depth = np.full(n, -1)
    q = deque(int(i) for i in range(nk))
    for i in range(nk):
        depth[i] = 0
    while q:
        u = q.popleft()
        for v in adj[u]:
            if depth[v] < 0:
                depth[v] = depth[u] + 1
                q.append(v)
    cl = np.arange(nk, n)
    dep = np.where(depth[cl] < 0, depth.max() + 1, depth[cl])
    # clusters closer to the fixed objects go to regions nearer those objects' mean position (anchor)
    q0 = quadratic(cd, macro_layout)
    order = np.lexsort((q0[:, 1], q0[:, 0], dep))
    r = regions or int(math.ceil(math.sqrt(C)))
    centres = np.array([((i % r) + 0.5, (i // r) + 0.5) for i in range(r * r)]) / r
    anchor = np.nanmean(macro_layout.pos[cd.keep], 0)
    centres = centres[np.argsort(np.linalg.norm(centres - anchor, axis=1), kind="stable")]
    out = np.zeros((C, 2))
    per = int(math.ceil(C / len(centres)))
    for j, c in enumerate(order):
        out[c] = centres[min(j // per, len(centres) - 1)]
    return np.clip(0.7 * out + 0.3 * q0, 0.0, 1.0)


SEEDS = {"C1.quadratic": quadratic, "C2.spread03": lambda cd, l, rng=None: quadratic_spread(cd, l, 0.3, rng),
         "C3.spread06": lambda cd, l, rng=None: quadratic_spread(cd, l, 0.6, rng), "C4.dataflow": dataflow}
