"""On-policy bridge data for the macro stage (tasks T3.2, T3.7 round data).

bundle(design) -> graph + view + scorer;  sources = population programs x seeds run in the sandbox and
projected by P_M (cached per design);  elites = the archive's top-k for the design, as graph node
positions (macros from the layout, clusters from the elite's recorded post-placement centroids when
present, else quadratic placement given the elite's macros);  pairs = symmetry-matched nearest elites.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..archive.store import Archive
from ..bridge.data import Elite, PairSet, make_pair
from ..bridge.graph import BridgeGraph, build_graph
from ..bridge.sample import source_nodes
from ..core import project
from ..core.cluster_design import MacroStageScorer, build_clustered
from ..core.design import Design, Layout
from ..evolve import sandbox as SB


@dataclass
class Bundle:
    design: Design
    base: Layout                 # macro-stage layout (cells unplaced)
    cluster_of: np.ndarray
    graph: BridgeGraph
    view: object
    scorer: MacroStageScorer


def make_bundle(design: Design, base: Layout, cluster_of: np.ndarray, reference: Layout | None = None) -> Bundle:
    g = build_graph(design, base, cluster_of)
    view = SB.make_view(design, base, cluster_of)
    ref = reference or project.legalize_macros(design, base)[0]
    return Bundle(design, base, cluster_of, g, view, MacroStageScorer(build_clustered(design, cluster_of), ref))


def node_orient(graph: BridgeGraph, layout: Layout) -> np.ndarray:
    o = np.zeros(graph.n, dtype=np.int8)
    has = graph.obj >= 0
    o[has] = layout.orient[graph.obj[has]]
    return o


def run_sources(b: Bundle, programs: list, seeds: int, cache: Path | None = None, cpu_s: float = 60.0) -> list:
    """[(program_id, seed, layout)] for every program x seed that runs and projects legally (cached)."""
    rows = []
    cpath = cache / ("sources_%s.npz" % b.design.id) if cache else None
    if cpath and cpath.exists():
        z = np.load(cpath, allow_pickle=False)
        meta = json.loads(str(z["meta"]))
        for k, (pid, s) in enumerate(meta):
            l = b.base.copy()
            l.pos, l.orient = z["pos"][k].copy(), z["orient"][k].copy()
            rows.append((pid, s, l))
        return rows
    scope = b.design.is_macro & ~b.design.is_fixed
    for p in programs:
        for s in range(seeds):
            r = SB.run_program(p["source"], b.view, None, 1000 + s, cpu_s=cpu_s)
            if r.status != "ok" or SB.validate_output(b.design, b.base, r, scope):
                continue
            lay, rep = project.legalize_macros(b.design, SB.to_layout(b.design, b.base, r))
            if rep.ok:
                rows.append((p["id"], s, lay))
    if cpath:
        cpath.parent.mkdir(parents=True, exist_ok=True)
        np.savez(cpath, pos=np.stack([l.pos for _, _, l in rows]), orient=np.stack([l.orient for _, _, l in rows]),
                 meta=np.array(json.dumps([(pid, s) for pid, s, _ in rows])))
    return rows


def archive_elites(b: Bundle, archive: Archive, k: int = 5, stage: str = "M") -> list:
    out = []
    for e in archive.topk(b.design.id, stage, k):
        lay = archive.layout(e)
        cp = (lay.routes or {}).get("cluster_pos")
        if cp is not None and len(cp) == b.graph.n_clusters:
            x = b.graph.node_positions(lay, cluster_pos=np.asarray(cp))
        else:
            x = source_nodes(b.graph, lay)
        out.append(Elite(x=x, orient=node_orient(b.graph, lay), J=float(e["J"]), ident=str(e["id"])))
    return out


def build_pairs(b: Bundle, sources: list, elites: list, T_J: float = 0.02) -> PairSet:
    pairs, meta = [], []
    for pid, s, lay in sources:
        xh = source_nodes(b.graph, lay)
        p = make_pair(b.graph, xh, node_orient(b.graph, lay), elites, T=T_J)
        pairs.append(p)
        meta.append({"program": pid, "seed": s, "elite": p["elite"], "J": p["J"], "dist2": p["dist2"]})
    return PairSet.from_pairs(b.graph, pairs, meta)
