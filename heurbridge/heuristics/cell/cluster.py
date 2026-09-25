"""Standard-cell clustering (task T2.3): N_c = 512 (< 50k cells), 2048 (<= 300k), 8192 (above).

Methods (first available wins unless one is requested):
  kahypar   hypergraph partitioning (python package ``kahypar``), km1 objective, 3% imbalance
  metis     graph partitioning (``pymetis``) of the clique-expanded netlist
  spectral  always available: 8-dimensional spectral embedding of the cell graph
            (normalized Laplacian, clique expansion with weight 1/(deg-1)) followed by
            area-weighted k-means (deterministic seeds)
All methods are deterministic for a fixed seed.  Returns an (N,) int array: cluster id
for movable standard cells, -1 for every other object.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from ...core.design import Design


def n_clusters(n_cells: int) -> int:
    if n_cells < 50_000:
        return 512
    if n_cells <= 300_000:
        return 2048
    return 8192


def cell_mask(design: Design) -> np.ndarray:
    return ~design.is_macro & ~design.is_io & ~design.is_fixed


def cell_graph(design: Design, cells: np.ndarray, max_deg: int = 64) -> sp.csr_matrix:
    """Clique expansion over movable cells (nets larger than max_deg are dropped)."""
    local = -np.ones(design.n_objects, dtype=np.int64)
    local[cells] = np.arange(len(cells))
    rows, cols, vals = [], [], []
    for k in range(design.n_nets):
        objs = np.unique(design.pin_obj[design.pin_idx[design.net_ptr[k]:design.net_ptr[k + 1]]])
        loc = local[objs]
        loc = loc[loc >= 0]
        d = len(loc)
        if d < 2 or d > max_deg:
            continue
        w = design.net_weight[k] / (d - 1)
        a, b = np.meshgrid(loc, loc)
        m = a != b
        rows.append(a[m])
        cols.append(b[m])
        vals.append(np.full(m.sum(), w))
    n = len(cells)
    if not rows:
        return sp.csr_matrix((n, n))
    A = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
    A.sum_duplicates()
    return A


def _spectral(A: sp.csr_matrix, dim: int, seed: int) -> np.ndarray:
    n = A.shape[0]
    deg = np.asarray(A.sum(1)).ravel() + 1e-9
    Dm = sp.diags(1.0 / np.sqrt(deg))
    M = Dm @ A @ Dm                             # largest eigenvectors of D^-1/2 A D^-1/2
    k = min(dim + 1, n - 2)
    if k < 2:
        return np.zeros((n, dim))
    rng = np.random.default_rng(seed)
    try:
        vals, vecs = spla.eigsh(M, k=k, which="LA", v0=rng.standard_normal(n), tol=1e-4, maxiter=5000)
    except spla.ArpackNoConvergence as e:
        vals, vecs = e.eigenvalues, e.eigenvectors
    order = np.argsort(-vals)
    emb = (Dm @ vecs[:, order])[:, 1:dim + 1]      # drop the trivial eigenvector
    emb /= (np.abs(emb).max(0, keepdims=True) + 1e-12)
    # sign convention for determinism
    emb *= np.sign(emb[np.argmax(np.abs(emb), 0), np.arange(emb.shape[1])])
    return emb


def _kmeans(X: np.ndarray, w: np.ndarray, k: int, seed: int, iters: int = 30) -> np.ndarray:
    n = len(X)
    k = min(k, n)
    rng = np.random.default_rng(seed)
    # k-means++ init (weighted)
    c = [X[rng.choice(n, p=w / w.sum())]]
    d2 = ((X - c[0]) ** 2).sum(1)
    for _ in range(1, k):
        p = w * d2
        s = p.sum()
        i = rng.choice(n, p=p / s) if s > 0 else rng.integers(n)
        c.append(X[i])
        d2 = np.minimum(d2, ((X - X[i]) ** 2).sum(1))
    C = np.array(c)
    lab = np.zeros(n, dtype=np.int64)
    for _ in range(iters):
        # squared distances in chunks
        lab_new = np.empty(n, dtype=np.int64)
        for s in range(0, n, 20000):
            D = ((X[s:s + 20000, None, :] - C[None]) ** 2).sum(-1)
            lab_new[s:s + 20000] = D.argmin(1)
        if np.array_equal(lab_new, lab):
            break
        lab = lab_new
        for j in range(k):
            m = lab == j
            if m.any():
                C[j] = (X[m] * w[m, None]).sum(0) / w[m].sum()
    # relabel by first occurrence in a canonical order for stability
    return lab


def cluster_cells(design: Design, n: int | None = None, method: str = "auto", seed: int = 0,
                  canonical_order: np.ndarray | None = None) -> np.ndarray:
    cells = np.flatnonzero(cell_mask(design))
    out = -np.ones(design.n_objects, dtype=np.int64)
    if len(cells) == 0:
        return out
    k = min(n or n_clusters(len(cells)), len(cells))
    lab = None
    if method in ("auto", "kahypar"):
        lab = _try_kahypar(design, cells, k, seed)
    if lab is None and method in ("auto", "metis"):
        lab = _try_metis(design, cells, k, seed)
    if lab is None:
        A = cell_graph(design, cells)
        emb = _spectral(A, dim=8, seed=seed)
        lab = _kmeans(emb, design.area[cells] + 1e-9, k, seed)
    # dense ids 0..k'-1 ordered by the smallest canonical key of their members (labelling-independent)
    if canonical_order is not None:
        rank = np.empty(design.n_objects, dtype=np.int64)
        rank[canonical_order] = np.arange(design.n_objects)
        key = rank[cells]
    else:
        key = np.arange(len(cells))
    first = {}
    for c, kk in zip(lab, key):
        if c not in first or kk < first[c]:
            first[c] = kk
    remap = {c: i for i, c in enumerate(sorted(first, key=first.get))}
    out[cells] = np.array([remap[c] for c in lab])
    return out


def _try_kahypar(design, cells, k, seed):
    try:
        import kahypar  # noqa: F401
    except Exception:
        return None
    return None   # wired on the server after T0.5 confirms the package and its context file


def _try_metis(design, cells, k, seed):
    try:
        import pymetis
    except Exception:
        return None
    A = cell_graph(design, cells).tocsr()
    A.data = np.maximum(1, np.round(A.data * 10)).astype(np.int64)
    opt = pymetis.Options(seed=seed)
    _, parts = pymetis.part_graph(k, xadj=A.indptr, adjncy=A.indices, eweights=A.data.tolist(), options=opt)
    return np.asarray(parts, dtype=np.int64)
