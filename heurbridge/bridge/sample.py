"""Inference with guarded partial transport (task T3.8).

refine():  integrate the bridge from each heuristic output (all sources of a design
in one batch), form candidates  P_M(x^h + a (T(x^h) - x^h))  for a in alphas
(a = 0 is the raw heuristic), score each with ``evaluate`` (f1 by default, f0 in
inner loops) and keep the best.  A candidate whose projection fails is scored +inf.
Deterministic: no sampling noise; the same input gives the same output.
Every call's chosen alpha is returned (and logged by the caller).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import torch

from ..core.design import Design, Layout
from ..core.project import legalize_macros
from .graph import BridgeGraph
from .train import integrate

ALPHAS = (0.0, 0.25, 0.5, 1.0)


@dataclass
class RefineResult:
    layout: Layout
    alpha: float
    scores: list
    x_bridge: np.ndarray                  # (n,2) bridge endpoint (node positions)
    legal: list = field(default_factory=list)


def source_nodes(graph: BridgeGraph, layout: Layout) -> np.ndarray:
    """Node positions of a macro-stage source: macros from the layout, clusters by quadratic placement."""
    x = graph.node_positions(layout, cluster_pos=np.zeros((graph.n_clusters, 2)))
    if graph.n_clusters:
        x[graph.cluster_nodes] = graph.quadratic_clusters(x)
    return x


def _det_context():
    """Deterministic algorithms for the duration of inference (CUDA scatter paths)."""
    class Ctx:
        def __enter__(self):
            self.prev = torch.are_deterministic_algorithms_enabled()
            torch.use_deterministic_algorithms(True, warn_only=True)

        def __exit__(self, *a):
            torch.use_deterministic_algorithms(self.prev)
    return Ctx()


@torch.no_grad()
def bridge_endpoints(model, graph: BridgeGraph, sources: np.ndarray, K: int = 20, method: str = "euler",
                     device: str = "cpu", gt: dict | None = None) -> np.ndarray:
    gt = gt or graph.tensors(device)
    xh = torch.as_tensor(np.asarray(sources, np.float32), device=device)
    with _det_context():
        xe = integrate(model.eval(), gt, xh, K=K, method=method)
    out = xe.cpu().numpy().astype(np.float64)
    out[:, ~graph.movable] = np.asarray(sources)[:, ~graph.movable]          # fixed nodes exactly unchanged
    return out


def refine(model, graph: BridgeGraph, design: Design, layouts: list, evaluate, K: int = 20,
           alphas=ALPHAS, halo: float = 0.0, method: str = "euler", device: str = "cpu",
           sources: np.ndarray | None = None, project=None) -> list:
    """Guarded refinement of a batch of heuristic layouts of one design."""
    project = project or (lambda d, l: legalize_macros(d, l, halo=halo))
    src = np.stack([source_nodes(graph, l) for l in layouts]) if sources is None else sources
    ends = bridge_endpoints(model, graph, src, K=K, method=method, device=device)
    return [guarded(graph, design, lay, src[b], ends[b], evaluate, alphas, project) for b, lay in enumerate(layouts)]


def guarded(graph: BridgeGraph, design: Design, lay: Layout, src: np.ndarray, end: np.ndarray, evaluate,
            alphas=ALPHAS, project=None) -> RefineResult:
    """Guarded partial transport along src -> end: P_M(src + a (end - src)) for every a, argmin of evaluate
    (a = 0 is the raw heuristic).  Shared by the bridge and by E0's random-direction control."""
    project = project or (lambda d, l: legalize_macros(d, l))
    scores, legal, cands = [], [], []
    for a in alphas:
        cand, rep = project(design, graph.to_layout(src + a * (end - src), lay))
        cands.append(cand)
        legal.append(bool(rep.ok))
        scores.append(float(evaluate(cand)) if rep.ok else math.inf)
    i = int(np.argmin(scores))
    return RefineResult(layout=cands[i], alpha=float(alphas[i]), scores=scores, x_bridge=end, legal=legal)
