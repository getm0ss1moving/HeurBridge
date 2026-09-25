"""Bridge training data (task T3.2): pairs, symmetry matching, weights, augmentation, shards.

Pair = (x0 = heuristic output x^h, x1 = matched elite x*), both as node positions of a
BridgeGraph.  The elite is the nearest of the top-k elites in area-weighted distance
after Hungarian matching inside each group of interchangeable macros (same master,
size and footprint orientation), which permutes the elite's macros within the group.
A matched macro whose elite orientation differs from the source keeps the source
orientation and is flagged struct_err = 1.  Pair weight w = exp(-(J* - J_min)/T_J).

Augmentation: the 8 dihedral transforms of the die act on normalized coordinates by
the orientation matrices about (0.5, 0.5); they are applied jointly to positions,
sizes (w/h swap), pin offsets in edge features, macro orientations and the aspect
feature.  Aspect jitter s ~ U(1-a, 1+a) rescales normalized x-sizes and x-offsets by 1/s.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import torch
from scipy.optimize import linear_sum_assignment

from ..core import orient as O
from .graph import KIND_MOV, BridgeGraph

T_J = 0.02

# composition table: COMP[k, o] = index of MATS[k] @ MATS[o]
COMP = np.zeros((8, 8), dtype=np.int64)
for _k in range(8):
    for _o in range(8):
        prod = O.MATS[_k] @ O.MATS[_o]
        COMP[_k, _o] = int(np.argmin([np.abs(prod - m).sum() for m in O.MATS]))
SWAPS = np.array([abs(O.MATS[k][0, 1]) > 0 for k in range(8)])


def dist2(a: np.ndarray, x: np.ndarray, y: np.ndarray) -> float:
    return float((a * ((x - y) ** 2).sum(-1)).sum())


def match_symmetric(graph: BridgeGraph, xh: np.ndarray, elite: np.ndarray, a: np.ndarray | None = None):
    """Permute elite macros within interchangeable groups to best match xh.  Returns (elite', perm)."""
    a = graph.area_w if a is None else a
    perm = np.arange(graph.n)
    grp = graph.group
    for gid in np.unique(grp[grp >= 0]):
        idx = np.flatnonzero((grp == gid) & (graph.kind == KIND_MOV))
        if len(idx) < 2:
            continue
        C = a[idx][:, None] * ((xh[idx][:, None, :] - elite[idx][None, :, :]) ** 2).sum(-1)
        r, c = linear_sum_assignment(C)
        perm[idx[r]] = idx[c]
    return elite[perm], perm


@dataclass
class Elite:
    x: np.ndarray            # (n,2) node positions
    orient: np.ndarray       # (n,) node orientations
    J: float
    ident: str = ""


def make_pair(graph: BridgeGraph, xh: np.ndarray, xh_orient: np.ndarray, elites: list, T: float = T_J) -> dict:
    """Pair a source with its nearest (symmetry-matched) elite among ``elites`` (the archive's top-k)."""
    if not elites:
        raise ValueError("no elites for design %s" % graph.design_id)
    a = graph.area_w
    best = None
    for k, e in enumerate(elites):
        x1, perm = match_symmetric(graph, xh, e.x, a)
        d = dist2(a, xh, x1)
        if best is None or d < best[0]:
            best = (d, k, x1, perm)
    d, k, x1, perm = best
    x1 = x1.copy()
    fixed = ~graph.movable
    x1[fixed] = xh[fixed]                                     # fixed nodes never move
    e = elites[k]
    struct = np.zeros(graph.n, dtype=np.int8)
    mm = graph.kind == KIND_MOV
    struct[mm] = (e.orient[perm][mm] != xh_orient[mm]).astype(np.int8)
    j_min = min(el.J for el in elites)
    return {"x0": xh.astype(np.float32), "x1": x1.astype(np.float32), "weight": float(np.exp(-(e.J - j_min) / T)),
            "struct_err": struct, "elite": e.ident or str(k), "J": float(e.J), "dist2": float(d)}


@dataclass
class PairSet:
    """All pairs of one design (one shard)."""
    graph: BridgeGraph
    x0: np.ndarray = field(default_factory=lambda: np.zeros((0, 0, 2), np.float32))
    x1: np.ndarray = field(default_factory=lambda: np.zeros((0, 0, 2), np.float32))
    weight: np.ndarray = field(default_factory=lambda: np.zeros(0, np.float32))
    struct_err: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), np.int8))
    meta: list = field(default_factory=list)

    @classmethod
    def from_pairs(cls, graph: BridgeGraph, pairs: list, meta: list | None = None) -> "PairSet":
        return cls(graph, np.stack([p["x0"] for p in pairs]), np.stack([p["x1"] for p in pairs]),
                   np.array([p["weight"] for p in pairs], np.float32), np.stack([p["struct_err"] for p in pairs]),
                   meta or [{k: p[k] for k in ("elite", "J", "dist2")} for p in pairs])

    def __len__(self) -> int:
        return len(self.weight)

    def cap(self, n: int) -> "PairSet":
        """Keep the newest n pairs (DAgger cap, T3.7)."""
        if len(self) <= n:
            return self
        s = slice(len(self) - n, len(self))
        return PairSet(self.graph, self.x0[s], self.x1[s], self.weight[s], self.struct_err[s], self.meta[s])

    def extend(self, other: "PairSet") -> "PairSet":
        if len(self) == 0:
            return other
        return PairSet(self.graph, np.concatenate([self.x0, other.x0]), np.concatenate([self.x1, other.x1]),
                       np.concatenate([self.weight, other.weight]), np.concatenate([self.struct_err, other.struct_err]),
                       self.meta + other.meta)

    def save(self, path: str | Path, round_id: int = 0) -> Path:
        g = self.graph
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "x0": torch.from_numpy(self.x0), "x1": torch.from_numpy(self.x1), "weight": torch.from_numpy(self.weight),
            "node_feat": torch.from_numpy(g.static_features()), "edge_index": torch.from_numpy(g.edge_index),
            "edge_feat": torch.from_numpy(g.edge_attr), "graph_feat": torch.from_numpy(g.graph_attr),
            "movable_mask": torch.from_numpy(g.movable), "struct_err": torch.from_numpy(self.struct_err),
            "graph": g, "meta": self.meta, "round": round_id, "design_id": g.design_id,
        }, path)
        return path

    @classmethod
    def load(cls, path: str | Path) -> "PairSet":
        z = torch.load(path, weights_only=False)
        return cls(z["graph"], z["x0"].numpy(), z["x1"].numpy(), z["weight"].numpy(), z["struct_err"].numpy(), z["meta"])


# ---------------------------------------------------------------------- augmentation
def transform_positions(x: torch.Tensor, k: int) -> torch.Tensor:
    """Dihedral transform k of the unit square about its centre; x (..., 2)."""
    if k == 0:
        return x
    m = torch.as_tensor(O.MATS[k], dtype=x.dtype, device=x.device)
    return (x - 0.5) @ m.T + 0.5


def augment_graph(gt: dict, k: int, s: float = 1.0) -> dict:
    """Transform graph tensors (BridgeGraph.tensors()) by dihedral k and aspect factor s (x-scale)."""
    if k == 0 and s == 1.0:
        return gt
    out = dict(gt)
    st = gt["static"].clone()
    if SWAPS[k]:
        st[:, [0, 1]] = st[:, [1, 0]]
    st[:, 0] = st[:, 0] / s
    oh = st[:, 7:15]
    o = oh.argmax(1).cpu().numpy()
    no = torch.as_tensor(COMP[k][o], device=st.device)
    st[:, 7:15] = 0.0
    st[torch.arange(len(st), device=st.device), 7 + no] = 1.0
    st[:, 7:15] *= (oh.sum(1, keepdim=True) > 0).to(st.dtype)        # keep all-zero rows (none expected)
    out["static"] = st
    ea = gt["edge_attr"].clone()
    if k:
        m = torch.as_tensor(O.MATS[k], dtype=ea.dtype, device=ea.device)
        ea[:, 0:2] = ea[:, 0:2] @ m.T
        ea[:, 2:4] = ea[:, 2:4] @ m.T
    ea[:, 0] /= s
    ea[:, 2] /= s
    out["edge_attr"] = ea
    ga = gt["graph_attr"].clone()
    if SWAPS[k]:
        ga[3] = 1.0 / ga[3]
    ga[3] = ga[3] * s
    out["graph_attr"] = ga
    sz = gt["size"].clone()
    if SWAPS[k]:
        sz = sz[:, [1, 0]]
    sz[:, 0] /= s
    out["size"] = sz
    return out


def random_augmentation(rng: np.random.Generator, dihedral: bool = True, aspect: float = 0.05) -> tuple:
    k = int(rng.integers(0, 8)) if dihedral else 0
    s = float(rng.uniform(1 - aspect, 1 + aspect)) if aspect else 1.0
    return k, s
