"""Clustered design for macro-stage scoring (cells unplaced).

Standard cells are replaced by soft cluster nodes (square, area = total cell area of the cluster);
macros, IOs and fixed objects are kept with their pins; nets are remapped to cluster nodes and nets
that collapse to one node are dropped.  Cluster positions for a macro layout come from quadratic
placement with every non-cluster node fixed.  ``MacroStageScorer`` evaluates the f0 surrogate J0
of macro layouts on this design (used by the E0 partners, RLCE attribution and guard inner loops).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
import torch

from .design import Design, Layout, build_csr


@dataclass
class ClusteredDesign:
    design: Design              # the clustered Design
    keep: np.ndarray            # original object indices of the non-cluster objects (in order)
    n_keep: int
    n_clusters: int
    original: Design

    def to_layout(self, layout: Layout, cluster_pos: np.ndarray) -> Layout:
        pos = np.concatenate([layout.pos[self.keep], cluster_pos], 0)
        ori = np.concatenate([layout.orient[self.keep], np.zeros(self.n_clusters, dtype=np.int8)])
        return Layout(pos=pos, orient=ori, schema=self.design.schema_hash())

    def quadratic_clusters(self, layout: Layout, reg: float = 1e-3) -> np.ndarray:
        """Cluster positions from quadratic placement (clique model on the clustered nets)."""
        d = self.design
        n = d.n_objects
        cl = np.arange(self.n_keep, n)
        pos = np.concatenate([layout.pos[self.keep], np.full((self.n_clusters, 2), 0.5)], 0)
        rows, cols, vals = [], [], []
        objs = d.pin_obj[d.pin_idx]
        for k in range(d.n_nets):
            o = np.unique(objs[d.net_ptr[k]:d.net_ptr[k + 1]])
            if len(o) < 2 or len(o) > 64:
                continue
            w = d.net_weight[k] / (len(o) - 1)
            a, b = np.meshgrid(o, o)
            m = a != b
            rows.append(a[m]); cols.append(b[m]); vals.append(np.full(m.sum(), w))
        if not rows:
            return np.full((self.n_clusters, 2), 0.5)
        A = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
        L = sp.diags(np.asarray(A.sum(1)).ravel()) - A
        fixed = np.arange(self.n_keep)
        ok = np.isfinite(pos[fixed]).all(1)
        fixed = fixed[ok]
        Lcc = (L[cl][:, cl] + reg * sp.eye(len(cl))).tocsc()
        Lcf = L[cl][:, fixed]
        out = np.zeros((len(cl), 2))
        for dd in (0, 1):
            out[:, dd] = spla.spsolve(Lcc, -Lcf @ pos[fixed, dd] + reg * 0.5)
        return np.clip(out, 0.0, 1.0)


def build_clustered(design: Design, cluster_of: np.ndarray) -> ClusteredDesign:
    d = design
    cm = cluster_of >= 0
    keep = np.flatnonzero(~cm)
    ncl = int(cluster_of.max()) + 1 if cm.any() else 0
    n_keep = len(keep)
    new_of = -np.ones(d.n_objects, dtype=np.int64)
    new_of[keep] = np.arange(n_keep)
    new_of[cm] = n_keep + cluster_of[cm]
    carea = np.bincount(cluster_of[cm], weights=d.area[cm], minlength=ncl) if ncl else np.zeros(0)
    side = np.sqrt(carea)
    size = np.concatenate([d.size[keep], np.stack([side, side], 1)], 0) if ncl else d.size[keep].copy()
    pin_obj, pin_off, nets, weights = [], [], [], []
    objs = d.pin_obj[d.pin_idx]
    offs = d.pin_off[d.pin_idx]
    for k in range(d.n_nets):
        s, e = d.net_ptr[k], d.net_ptr[k + 1]
        o = new_of[objs[s:e]]
        if len(np.unique(o)) < 2:
            continue
        lst = []
        seen_cluster = set()
        for oi, off in zip(o, offs[s:e]):
            if oi >= n_keep:                       # one pin per cluster per net, at the cluster centre
                if oi in seen_cluster:
                    continue
                seen_cluster.add(oi)
                off = (0.0, 0.0)
            lst.append(len(pin_obj))
            pin_obj.append(oi)
            pin_off.append(off)
        nets.append(lst)
        weights.append(d.net_weight[k])
    ptr, idx = build_csr(nets)
    n = n_keep + ncl
    zeros = np.zeros(ncl, dtype=bool)
    cd = Design(id=d.id + "_clustered", family=d.family, tech=d.tech,
                names=[d.names[i] for i in keep] + ["__cluster_%d" % c for c in range(ncl)], size=size,
                is_macro=np.concatenate([d.is_macro[keep], zeros]), is_fixed=np.concatenate([d.is_fixed[keep], zeros]),
                is_io=np.concatenate([d.is_io[keep], zeros]), pin_obj=np.array(pin_obj, dtype=np.int64),
                pin_off=np.array(pin_off, dtype=np.float64).reshape(-1, 2), net_ptr=ptr, pin_idx=idx,
                net_weight=np.array(weights, dtype=np.float64), die=d.die, core=d.core,
                masters=None if d.masters is None else [d.masters[i] for i in keep] + ["__cluster"] * ncl,
                rows=d.rows, site=d.site, gcell_grid=d.gcell_grid, dbu=d.dbu,
                source={"format": "clustered", "parent": d.id, "layers": d.source.get("layers")})
    cd.validate()
    return ClusteredDesign(design=cd, keep=keep, n_keep=n_keep, n_clusters=ncl, original=d)


class MacroStageScorer:
    """f0 surrogate J0 of macro layouts on the clustered design (lower is better)."""

    def __init__(self, cdesign: ClusteredDesign, reference: Layout, weights: dict | None = None, device="cpu"):
        from ..eval import f0
        self.cd, self.f0 = cdesign, f0
        ref_c = cdesign.to_layout(reference, cdesign.quadratic_clusters(reference))
        self.ctx = f0.F0Context(cdesign.design, ref_c.orient, device=device)
        self.norm = f0.reference_normalizers(self.ctx, ref_c.pos)
        self.weights = weights
        self.device = device

    def clustered(self, layout: Layout) -> Layout:
        return self.cd.to_layout(layout, self.cd.quadratic_clusters(layout))

    def __call__(self, layout: Layout) -> float:
        lc = self.clustered(layout)
        self.ctx.set_orient(lc.orient)
        with torch.no_grad():
            return float(self.f0.surrogate_j0(self.ctx, torch.as_tensor(lc.pos, dtype=torch.float32, device=self.device),
                                              self.norm, self.weights)[0])
