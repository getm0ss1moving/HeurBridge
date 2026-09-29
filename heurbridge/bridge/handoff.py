"""Stage hand-off (task T3.9 interface): the macro bridge's sketch of the cell stage, passed bridge to bridge.

The macro-stage graph carries the standard cells as clusters (``KIND_CL``); the bridge transports them together
with the macros toward downstream-ranked elites, but only the macros are written back (``BridgeGraph.to_layout``).
This module keeps the clusters' guarded positions -- the sketch of the next stage -- so that the next *bridge*
stage can start from them instead of from a quadratic placement.

    sketch             clusters of  src + alpha (end - src)  at the guard's alpha, in [0, 1]
                       (alpha = 0 is the raw heuristic: the sketch is then the quadratic placement)
    Handoff            sketch + the legal macro positions it belongs to + identity checks; saved as .npz
    next_stage_source  (n,2) start positions for the next stage; without a hand-off exactly ``source_nodes``
    transfer_sketch    the sketch on another clustering (e.g. the cell stage's own clusters)
    anchored_clusters  optional re-solve: quadratic placement pulled toward the sketch (mu = 0: quadratic)
    sketch_fidelity    area-weighted RMS distance of a sketch to reference cluster centres (diagnostics)

Off by default: nothing in the evaluation path (partners, E0, f0/f1/f2, evaluators) calls this module.  Handing
a sketch to a tool's placer or router (DREAMPlace initial positions, OpenROAD warm start) is a separate step that
waits for gate G0' (owner's decision, 29 Sep 2026).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from .graph import BridgeGraph
from .sample import source_nodes

FORMAT = "heurbridge.handoff.v1"


class HandoffMismatch(ValueError):
    """A hand-off does not belong to the graph or layout it is applied to."""


def graph_hash(graph: BridgeGraph) -> str:
    """Identity of the graph's nodes and cluster assignment (16 hex): a sketch applies only to the same clustering."""
    h = hashlib.sha256()
    h.update(graph.design_id.encode())
    for a, dt in ((graph.kind, np.int8), (graph.key, np.int64), (graph.cluster_of, np.int64)):
        h.update(np.ascontiguousarray(a, dtype=dt).tobytes())
    return h.hexdigest()[:16]


def guarded_sketch(graph: BridgeGraph, src: np.ndarray, end: np.ndarray, alpha: float) -> np.ndarray:
    """(n_clusters, 2) cluster rows of ``src + alpha (end - src)`` -- the candidate the guard scored -- in [0, 1]."""
    cl = graph.cluster_nodes
    x = np.asarray(src, np.float64) + float(alpha) * (np.asarray(end, np.float64) - np.asarray(src, np.float64))
    return np.clip(x[cl], 0.0, 1.0)


@dataclass
class Handoff:
    """What the macro stage hands to the cell stage for one deployed macro layout."""
    design_id: str
    graph_hash: str
    macros: np.ndarray            # (m,2) legal positions of the graph's movable-macro nodes (normalized centres)
    sketch: np.ndarray            # (n_clusters,2) predicted cluster centres, normalized to the core
    alpha: float                  # the guard's alpha (0 = the raw heuristic)
    origin: str = "bridge"        # "bridge" or "quadratic"
    meta: dict = field(default_factory=dict)

    def save(self, path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        head = {"format": FORMAT, "design_id": self.design_id, "graph_hash": self.graph_hash,
                "alpha": float(self.alpha), "origin": self.origin, "meta": self.meta}
        with open(path, "wb") as fh:
            np.savez_compressed(fh, macros=np.asarray(self.macros, np.float64),
                                sketch=np.asarray(self.sketch, np.float64), head=np.array(json.dumps(head, sort_keys=True)))
        return path

    @classmethod
    def load(cls, path) -> "Handoff":
        with np.load(path, allow_pickle=False) as z:
            head = json.loads(str(z["head"]))
            if head.get("format") != FORMAT:
                raise HandoffMismatch("%s: unknown hand-off format %r" % (path, head.get("format")))
            return cls(design_id=head["design_id"], graph_hash=head["graph_hash"], macros=z["macros"].copy(),
                       sketch=z["sketch"].copy(), alpha=float(head["alpha"]), origin=head["origin"], meta=head["meta"])


def _macro_positions(graph: BridgeGraph, layout) -> np.ndarray:
    return np.asarray(layout.pos[graph.obj[graph.macro_nodes]], np.float64).copy()


def make_handoff(graph: BridgeGraph, layout, src: np.ndarray, end: np.ndarray, alpha: float,
                 meta: dict | None = None) -> Handoff:
    """Hand-off of a guarded bridge output: ``layout`` is the deployed (legal) layout, ``src``/``end`` the node
    positions the guard interpolated between and ``alpha`` its choice."""
    cl = graph.cluster_nodes
    raw = np.asarray(src, np.float64)[cl] + float(alpha) * (np.asarray(end, np.float64)[cl] - np.asarray(src, np.float64)[cl])
    n_clipped = int(((raw < 0.0) | (raw > 1.0)).any(axis=1).sum())
    return Handoff(design_id=graph.design_id, graph_hash=graph_hash(graph), macros=_macro_positions(graph, layout),
                   sketch=guarded_sketch(graph, src, end, alpha), alpha=float(alpha), origin="bridge",
                   meta=dict(meta or {}, n_clusters=int(graph.n_clusters), n_clipped=n_clipped))


def handoff_from_result(graph: BridgeGraph, result, src: np.ndarray, meta: dict | None = None) -> Handoff:
    """Hand-off of a ``refine``/``guarded`` result; ``src`` = the source it started from (``source_nodes``)."""
    return make_handoff(graph, result.layout, src, result.x_bridge, result.alpha, meta)


def quadratic_handoff(graph: BridgeGraph, layout, meta: dict | None = None) -> Handoff:
    """The current behaviour as a hand-off: clusters by quadratic placement around the layout's macros."""
    x = source_nodes(graph, layout)
    return Handoff(design_id=graph.design_id, graph_hash=graph_hash(graph), macros=_macro_positions(graph, layout),
                   sketch=np.asarray(x[graph.cluster_nodes], np.float64).copy(), alpha=0.0, origin="quadratic",
                   meta=dict(meta or {}, n_clusters=int(graph.n_clusters), n_clipped=0))


def check(handoff: Handoff, graph: BridgeGraph, layout=None, tol: float = 1e-9) -> None:
    """Raise HandoffMismatch unless the hand-off belongs to this graph (and, if given, to this layout's macros)."""
    if handoff.design_id != graph.design_id:
        raise HandoffMismatch("design %s, graph is %s" % (handoff.design_id, graph.design_id))
    if handoff.graph_hash != graph_hash(graph):
        raise HandoffMismatch("different nodes or clustering (graph hash %s vs %s)" % (handoff.graph_hash, graph_hash(graph)))
    s = np.asarray(handoff.sketch)
    if s.shape != (graph.n_clusters, 2):
        raise HandoffMismatch("sketch shape %s, graph has %d clusters" % (s.shape, graph.n_clusters))
    if not np.isfinite(s).all() or (s < 0.0).any() or (s > 1.0).any():
        raise HandoffMismatch("sketch has values outside [0, 1] or non-finite values")
    if layout is not None:
        m = _macro_positions(graph, layout)
        if np.asarray(handoff.macros).shape != m.shape:
            raise HandoffMismatch("macro count %s vs layout %s" % (np.asarray(handoff.macros).shape, m.shape))
        d = float(np.abs(np.asarray(handoff.macros) - m).max()) if len(m) else 0.0
        if not d <= tol:
            raise HandoffMismatch("the layout's macros differ from the hand-off's by %.3g (normalized)" % d)


def anchored_clusters(graph: BridgeGraph, x_nodes: np.ndarray, sketch: np.ndarray, mu: float,
                      reg: float = 1e-3) -> np.ndarray:
    """Quadratic cluster placement (all other nodes fixed at ``x_nodes``) pulled toward ``sketch``:

        min  sum_edges w (x_i - x_j)^2  +  reg |x_c - 0.5|^2  +  mu * dbar * |x_c - s_c|^2

    ``dbar`` is the mean weighted degree of the clusters, so ``mu`` is relative to a typical cluster's connectivity.
    mu = 0 returns ``graph.quadratic_clusters`` itself; mu -> inf returns the sketch."""
    if mu < 0:
        raise ValueError("mu must be >= 0")
    if mu == 0:
        return graph.quadratic_clusters(x_nodes, reg)
    cl = graph.cluster_nodes
    if len(cl) == 0:
        return np.zeros((0, 2))
    n = graph.n
    src, dst = graph.edge_index
    w = graph.edge_attr[:, 4] * graph.edge_attr[:, 5]
    A = sp.coo_matrix((w, (src, dst)), shape=(n, n)).tocsr()
    A = (A + A.T) * 0.5
    L = sp.diags(np.asarray(A.sum(1)).ravel()) - A
    fixed = np.setdiff1d(np.arange(n), cl)
    Lcc = L[cl][:, cl]
    dbar = float(Lcc.diagonal().mean()) if len(cl) else 0.0
    k = mu * max(dbar, 1e-12)
    M = (Lcc + (reg + k) * sp.eye(len(cl))).tocsc()
    Lcf = L[cl][:, fixed]
    s = np.asarray(sketch, np.float64)
    out = np.zeros((len(cl), 2))
    for d in (0, 1):
        b = -Lcf @ np.asarray(x_nodes, np.float64)[fixed, d] + reg * 0.5 + k * s[:, d]
        out[:, d] = spla.spsolve(M, b)
    return np.clip(out, 0.0, 1.0)


def next_stage_source(graph: BridgeGraph, layout, handoff: Handoff | None = None,
                      anchor_mu: float | None = None) -> np.ndarray:
    """(n,2) node positions the next stage starts from: macros and IOs from ``layout``; clusters from the
    hand-off's sketch (checked against this graph and layout), optionally re-solved with ``anchored_clusters``.
    Without a hand-off: exactly ``source_nodes`` (the quadratic placement), the current behaviour."""
    if handoff is None:
        return source_nodes(graph, layout)
    check(handoff, graph, layout)
    x = graph.node_positions(layout, cluster_pos=np.asarray(handoff.sketch, np.float64))
    if anchor_mu is not None and graph.n_clusters:
        x[graph.cluster_nodes] = anchored_clusters(graph, x, handoff.sketch, anchor_mu)
    return x


def transfer_sketch(sketch: np.ndarray, src_cluster_of: np.ndarray, dst_cluster_of: np.ndarray,
                    weights: np.ndarray) -> np.ndarray:
    """The sketch on another clustering of the same objects: each destination cluster sits at the weighted mean
    (``weights``: e.g. cell areas) of its members' source-cluster positions -- exactly at the source cluster's
    position when all its members come from one (nested clusterings).  Members outside every source cluster are
    ignored; a destination cluster without any mapped member raises HandoffMismatch."""
    s = np.asarray(sketch, np.float64)
    src_c = np.asarray(src_cluster_of, np.int64)
    dst_c = np.asarray(dst_cluster_of, np.int64)
    w = np.asarray(weights, np.float64)
    if not (len(src_c) == len(dst_c) == len(w)):
        raise HandoffMismatch("cluster assignments and weights must cover the same objects")
    n_dst = int(dst_c.max()) + 1 if (dst_c >= 0).any() else 0
    ok = (dst_c >= 0) & (src_c >= 0)
    if (src_c[ok] >= len(s)).any():
        raise HandoffMismatch("a source cluster id exceeds the sketch (%d clusters)" % len(s))
    tot = np.bincount(dst_c[ok], weights=w[ok], minlength=n_dst)
    if (tot <= 0).any():
        raise HandoffMismatch("%d destination clusters have no member in a source cluster" % int((tot <= 0).sum()))
    out = np.zeros((n_dst, 2))
    for d in (0, 1):
        out[:, d] = np.bincount(dst_c[ok], weights=w[ok] * s[src_c[ok], d], minlength=n_dst) / tot
    lo = np.full(n_dst, np.iinfo(np.int64).max)
    hi = np.full(n_dst, -1, dtype=np.int64)
    np.minimum.at(lo, dst_c[ok], src_c[ok])
    np.maximum.at(hi, dst_c[ok], src_c[ok])
    one = lo == hi                                  # members from a single source cluster: its position exactly
    out[one] = s[lo[one]]
    return out


def member_positions(sketch: np.ndarray, cluster_of: np.ndarray) -> np.ndarray:
    """(N_obj,2) normalized positions: every clustered object at its cluster's sketch position, NaN otherwise."""
    c = np.asarray(cluster_of, np.int64)
    out = np.full((len(c), 2), np.nan)
    m = c >= 0
    out[m] = np.asarray(sketch, np.float64)[c[m]]
    return out


def sketch_fidelity(graph: BridgeGraph, sketch: np.ndarray, reference: np.ndarray,
                    weights: np.ndarray | None = None) -> float:
    """Weighted RMS distance (normalized core units) between a sketch and reference cluster centres, e.g. the
    centroids of a placer's result (``graph.cluster_centroids(layout)``).  Default weights: cluster areas."""
    s = np.asarray(sketch, np.float64)
    r = np.asarray(reference, np.float64)
    if s.shape != r.shape:
        raise HandoffMismatch("sketch %s vs reference %s" % (s.shape, r.shape))
    w = np.asarray(graph.area_w[graph.cluster_nodes], np.float64) if weights is None else np.asarray(weights, np.float64)
    if len(w) != len(s) or w.sum() <= 0:
        raise HandoffMismatch("weights must be positive, one per cluster")
    return float(np.sqrt((w * ((s - r) ** 2).sum(1)).sum() / w.sum()))
