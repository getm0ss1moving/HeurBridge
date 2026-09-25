"""Bridge graph for the macro stage (task T3.2, conditioning features).

Nodes: movable macros (kind 0), fixed macros (1), IOs (2) and standard-cell
clusters as soft nodes (3; size = total cell area, square), in that order.
Only movable macros and clusters move (``movable``); fixed macros and IOs have
zero velocity.  Orientation is part of the condition and never transported.

Static node features  [w, h, is_macro, is_fixed, is_io, is_cluster, log1p(pins)/5, orient one-hot(8)]
Edge features         [dx_src, dy_src, dx_dst, dy_dst, net_weight, 1/(deg-1)]  (star from the driver;
                      offsets normalized to the core and rotated by the node's orientation; both directions)
Graph features        [utilization, log1p(#macros)/10, macro_area_ratio, aspect, tech one-hot(5)]
Attention set         all macro nodes + the 512 largest clusters (ties broken by a label-free key)
Loss weights a_i      movable macro: area / mean movable-macro area; cluster: 0.1 * area / mean macro area;
                      fixed nodes: 0
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
import torch

from ..core import orient as O
from ..core.design import Design, Layout
from ..evolve.sandbox import stable_key

TECHS = ("bookshelf", "nangate45", "sky130hd", "synthetic", "other")
KIND_MOV, KIND_FIX, KIND_IO, KIND_CL = 0, 1, 2, 3
N_STATIC = 15


@dataclass
class BridgeGraph:
    design_id: str
    kind: np.ndarray            # (n,) int8
    obj: np.ndarray             # (n,) design object index (-1 for clusters)
    size: np.ndarray            # (n,2) normalized effective size
    orient: np.ndarray          # (n,) int8
    pin_count: np.ndarray       # (n,)
    movable: np.ndarray         # (n,) bool
    area_w: np.ndarray          # (n,) loss weights
    group: np.ndarray           # (n,) interchangeable macro group id, -1 otherwise
    key: np.ndarray             # (n,) int64 label-free keys
    edge_index: np.ndarray      # (2,E)
    edge_attr: np.ndarray       # (E,6)
    graph_attr: np.ndarray      # (9,)
    attn: np.ndarray            # (A,) node indices in global attention
    fixed_pos: np.ndarray       # (n,2) normalized positions of fixed nodes (NaN for movable)
    cluster_of: np.ndarray      # (N_obj,) cluster id per design object, -1 if none
    n_clusters: int = 0
    meta: dict = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.kind)

    @property
    def macro_nodes(self) -> np.ndarray:
        return np.flatnonzero(self.kind == KIND_MOV)

    @property
    def cluster_nodes(self) -> np.ndarray:
        return np.flatnonzero(self.kind == KIND_CL)

    def static_features(self) -> np.ndarray:
        f = np.zeros((self.n, N_STATIC), dtype=np.float32)
        f[:, 0:2] = self.size
        f[:, 2] = (self.kind == KIND_MOV) | (self.kind == KIND_FIX)
        f[:, 3] = (self.kind == KIND_FIX) | (self.kind == KIND_IO)
        f[:, 4] = self.kind == KIND_IO
        f[:, 5] = self.kind == KIND_CL
        f[:, 6] = np.log1p(self.pin_count) / 5.0
        f[np.arange(self.n), 7 + self.orient.astype(np.int64)] = 1.0
        return f

    # ------------------------------------------------------------------ positions
    def node_positions(self, layout: Layout, cluster_pos: np.ndarray | None = None) -> np.ndarray:
        """(n,2) positions: macros/IOs from the layout, clusters from ``cluster_pos`` (default: centroids)."""
        x = np.zeros((self.n, 2))
        has_obj = self.obj >= 0
        x[has_obj] = layout.pos[self.obj[has_obj]]
        cl = self.cluster_nodes
        if len(cl):
            x[cl] = cluster_pos if cluster_pos is not None else self.cluster_centroids(layout)
        return x

    def cluster_centroids(self, layout: Layout, design_area: np.ndarray | None = None) -> np.ndarray:
        """Area-weighted centroid of each cluster's member cells (NaN-free: unplaced cells ignored)."""
        m = self.cluster_of >= 0
        cid = self.cluster_of[m]
        p = layout.pos[m]
        w = np.ones(len(cid)) if design_area is None else design_area[m]
        ok = np.isfinite(p).all(1)
        cnt = np.bincount(cid[ok], weights=w[ok], minlength=self.n_clusters)
        cx = np.bincount(cid[ok], weights=w[ok] * p[ok, 0], minlength=self.n_clusters)
        cy = np.bincount(cid[ok], weights=w[ok] * p[ok, 1], minlength=self.n_clusters)
        out = np.full((self.n_clusters, 2), 0.5)
        nz = cnt > 0
        out[nz, 0], out[nz, 1] = cx[nz] / cnt[nz], cy[nz] / cnt[nz]
        return out

    def quadratic_clusters(self, x_nodes: np.ndarray, reg: float = 1e-3) -> np.ndarray:
        """Cluster positions from quadratic placement with all non-cluster nodes fixed (T2.3 seed)."""
        cl = self.cluster_nodes
        if len(cl) == 0:
            return np.zeros((0, 2))
        n = self.n
        src, dst = self.edge_index
        w = self.edge_attr[:, 4] * self.edge_attr[:, 5]
        A = sp.coo_matrix((w, (src, dst)), shape=(n, n)).tocsr()
        A = (A + A.T) * 0.5
        L = sp.diags(np.asarray(A.sum(1)).ravel()) - A
        fixed = np.setdiff1d(np.arange(n), cl)
        Lcc = L[cl][:, cl] + reg * sp.eye(len(cl))
        Lcf = L[cl][:, fixed]
        out = np.zeros((len(cl), 2))
        for d in (0, 1):
            b = -Lcf @ x_nodes[fixed, d] + reg * 0.5
            out[:, d] = spla.spsolve(Lcc.tocsc(), b)
        return np.clip(out, 0.0, 1.0)

    def to_layout(self, x_nodes: np.ndarray, base: Layout) -> Layout:
        """Write movable-macro node positions back into a copy of ``base``."""
        out = base.copy()
        m = self.macro_nodes
        out.pos[self.obj[m]] = x_nodes[m]
        return out

    # ------------------------------------------------------------------ tensors
    def tensors(self, device="cpu") -> dict:
        return {
            "static": torch.as_tensor(self.static_features(), device=device),
            "edge_index": torch.as_tensor(self.edge_index, dtype=torch.long, device=device),
            "edge_attr": torch.as_tensor(self.edge_attr, dtype=torch.float32, device=device),
            "graph_attr": torch.as_tensor(self.graph_attr, dtype=torch.float32, device=device),
            "attn": torch.as_tensor(self.attn, dtype=torch.long, device=device),
            "movable": torch.as_tensor(self.movable, dtype=torch.float32, device=device),
            "area_w": torch.as_tensor(self.area_w, dtype=torch.float32, device=device),
            "size": torch.as_tensor(self.size, dtype=torch.float32, device=device),
            "kind": torch.as_tensor(self.kind, dtype=torch.long, device=device),
        }


def _tech_onehot(tech: str) -> np.ndarray:
    v = np.zeros(len(TECHS), dtype=np.float32)
    t = tech.lower()
    v[TECHS.index(t) if t in TECHS else TECHS.index("other")] = 1.0
    return v


def build_graph(design: Design, layout: Layout, cluster_of: np.ndarray, attn_clusters: int = 512,
                macros_movable: bool | None = None) -> BridgeGraph:
    """Build the macro-stage graph.  ``layout`` supplies orientations and fixed positions."""
    d = design
    wh = d.core_wh
    mov_macro = d.is_macro & ~d.is_fixed
    if macros_movable:                          # MMS convention (ISPD2005): large terminals become movable
        mov_macro = d.is_macro & ~d.is_io
    fix_macro = d.is_macro & ~mov_macro
    io = d.is_io & ~d.is_macro
    objs = np.r_[np.flatnonzero(mov_macro), np.flatnonzero(fix_macro), np.flatnonzero(io)].astype(np.int64)
    kinds = np.r_[np.full(mov_macro.sum(), KIND_MOV), np.full(fix_macro.sum(), KIND_FIX),
                  np.full(io.sum(), KIND_IO)].astype(np.int8)
    ncl = int(cluster_of.max()) + 1 if (cluster_of >= 0).any() else 0
    n_obj_nodes = len(objs)
    n = n_obj_nodes + ncl
    node_of_obj = -np.ones(d.n_objects, dtype=np.int64)
    node_of_obj[objs] = np.arange(n_obj_nodes)
    cm = cluster_of >= 0
    node_of_obj[cm] = n_obj_nodes + cluster_of[cm]
    kind = np.r_[kinds, np.full(ncl, KIND_CL, dtype=np.int8)]
    obj = np.r_[objs, -np.ones(ncl, dtype=np.int64)]
    ori = np.zeros(n, dtype=np.int8)
    ori[:n_obj_nodes] = layout.orient[objs]
    size = np.zeros((n, 2))
    size[:n_obj_nodes] = O.effective_size(d.size[objs], layout.orient[objs]) / wh
    carea = np.bincount(cluster_of[cm], weights=d.area[cm], minlength=ncl) if ncl else np.zeros(0)
    if ncl:
        s = np.sqrt(carea)
        size[n_obj_nodes:, 0], size[n_obj_nodes:, 1] = s / wh[0], s / wh[1]
    # keys: object names for macros/IOs; clusters by the smallest member key (label-free)
    key = np.zeros(n, dtype=np.int64)
    key[:n_obj_nodes] = [stable_key(d.names[i]) for i in objs]
    if ncl:
        mk = np.full(ncl, np.iinfo(np.int64).max)
        for i in np.flatnonzero(cm):
            k = stable_key(d.names[i])
            c = cluster_of[i]
            if k < mk[c]:
                mk[c] = k
        key[n_obj_nodes:] = mk
    masters = d.masters or ["%.6g_%.6g" % tuple(v) for v in d.size]
    group = -np.ones(n, dtype=np.int64)
    gmap = {}
    for j in range(int(mov_macro.sum())):
        i = objs[j]
        group[j] = gmap.setdefault((masters[i], float(d.size[i, 0]), float(d.size[i, 1]), int(layout.orient[i]) in (1, 3, 6, 7)), len(gmap))
    # edges: star from the first pin of each net, both directions, parallel cluster-cluster edges merged
    deg = d.degrees()
    pin_off = d.pin_off / wh
    src_l, dst_l, attr_l = [], [], []
    pins = d.pin_idx
    pin_node = node_of_obj[d.pin_obj[pins]]
    pin_rot = np.zeros((len(pins), 2))
    has = pin_node >= 0
    o_pin = layout.orient[d.pin_obj[pins]]
    pin_rot = O.apply(pin_off[pins], o_pin)
    pin_rot[kind[np.maximum(pin_node, 0)] == KIND_CL] = 0.0
    net_of = d.net_of_pin()
    first = d.net_ptr[:-1]
    drv = np.repeat(first, deg)                         # index into pins of each net's driver
    ok = has & has[drv] & (pin_node != pin_node[drv]) & (np.arange(len(pins)) != drv) & (deg[net_of] >= 2)
    s_node, t_node = pin_node[drv[ok]], pin_node[ok]
    w = d.net_weight[net_of[ok]]
    inv = 1.0 / np.maximum(deg[net_of[ok]] - 1, 1)
    attr = np.c_[pin_rot[drv[ok]], pin_rot[ok], w, inv].astype(np.float32)
    # merge cluster-cluster duplicates
    cc = (kind[s_node] == KIND_CL) & (kind[t_node] == KIND_CL)
    if cc.any():
        a, b = np.minimum(s_node[cc], t_node[cc]), np.maximum(s_node[cc], t_node[cc])
        pair = a * n + b
        u, invi = np.unique(pair, return_inverse=True)
        wsum = np.bincount(invi, weights=w[cc])
        isum = np.bincount(invi, weights=inv[cc]) / np.bincount(invi)
        m_attr = np.zeros((len(u), 6), dtype=np.float32)
        m_attr[:, 4], m_attr[:, 5] = wsum, isum
        s_node = np.r_[s_node[~cc], u // n]
        t_node = np.r_[t_node[~cc], u % n]
        attr = np.r_[attr[~cc], m_attr]
    rev = attr[:, [2, 3, 0, 1, 4, 5]]
    edge_index = np.stack([np.r_[s_node, t_node], np.r_[t_node, s_node]]).astype(np.int64)
    edge_attr = np.r_[attr, rev].astype(np.float32)
    pin_count = np.bincount(pin_node[has], minlength=n).astype(np.float32)
    # loss weights
    area_w = np.zeros(n)
    ma = d.area[objs[kind[:n_obj_nodes] == KIND_MOV]]
    mean_ma = ma.mean() if len(ma) else (carea.mean() if ncl else 1.0)
    area_w[kind == KIND_MOV] = ma / mean_ma
    if ncl:
        area_w[kind == KIND_CL] = 0.1 * carea / mean_ma
    movable = (kind == KIND_MOV) | (kind == KIND_CL)
    # attention set: macro nodes + largest clusters (ties by key)
    macro_nodes = np.flatnonzero((kind == KIND_MOV) | (kind == KIND_FIX))
    cl_nodes = np.flatnonzero(kind == KIND_CL)
    if len(cl_nodes) > attn_clusters:
        order = np.lexsort((key[cl_nodes], -carea))
        cl_nodes = np.sort(cl_nodes[order[:attn_clusters]])
    attn = np.r_[macro_nodes, cl_nodes]
    total_mov = d.area[~d.is_fixed | mov_macro].sum()
    ga = np.r_[total_mov / (wh[0] * wh[1]), np.log1p(int(mov_macro.sum())) / 10.0,
               (d.area[mov_macro].sum() / max(total_mov, 1e-12)), wh[0] / wh[1], _tech_onehot(d.tech)].astype(np.float32)
    fixed_pos = np.full((n, 2), np.nan)
    fx = ~movable
    fixed_pos[fx] = layout.pos[obj[fx]]
    return BridgeGraph(design_id=d.id, kind=kind, obj=obj, size=size.astype(np.float32), orient=ori,
                       pin_count=pin_count, movable=movable, area_w=area_w.astype(np.float32), group=group, key=key,
                       edge_index=edge_index, edge_attr=edge_attr, graph_attr=ga, attn=attn.astype(np.int64),
                       fixed_pos=fixed_pos, cluster_of=cluster_of.copy(), n_clusters=ncl,
                       meta={"n_edges": int(edge_index.shape[1]), "macros_movable": bool(macros_movable)})
