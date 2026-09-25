"""Online solving for a new design (task T6.1; proposal s.3.8).  No LLM calls.

1. state card z(c)
2. rank programs (optional ranker; default: portfolio order) and keep the top k
3. real rollouts: every (program, seed) -> sandbox -> P_M -> bridge + guard (f1 guard) -> f1 score
4. the best b per stage go to f2 (beam over M -> C -> R when those stages exist; macro stage today)
5. deploy argmin{ baseline, verified candidates } (Lemma 3: never worse than the baseline where
   verification completes); every rollout, failure and the deployment decision are returned.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import numpy as np

from ..bridge.sample import refine
from ..core import contract, project
from ..core.design import Design, Layout
from ..evolve import sandbox as SB


def state_card(design: Design, layout: Layout) -> dict:
    d = design
    mov = ~d.is_fixed
    core = float(d.core_wh.prod())
    deg = d.degrees()
    return {"objects": int(d.n_objects), "macros": int(d.is_macro.sum()), "movable_macros": int((d.is_macro & mov).sum()),
            "nets": int(d.n_nets), "pins": int(d.n_pins), "avg_degree": float(deg.mean()) if len(deg) else 0.0,
            "utilization": float(d.area[mov].sum() / core), "macro_area_ratio": float(d.area[d.is_macro].sum() / core),
            "aspect": float(d.core_wh[0] / d.core_wh[1]), "pin_density": float(d.n_pins / core), "tech": d.tech}


@dataclass
class OnlineResult:
    deployed: str                 # "baseline" or candidate id
    J: float
    baseline_J: float
    candidates: list = field(default_factory=list)
    card: dict = field(default_factory=dict)
    wall_s: float = 0.0
    llm_calls: int = 0


def solve_macro(design: Design, base: Layout, view, graph, programs: list, bridge, f1, f2=None, baseline_J2: float = math.inf,
                k: int = 6, seeds: int = 3, beam: int = 2, ranker=None, K: int = 20, halo: float = 0.0,
                device: str = "cpu") -> OnlineResult:
    """f1(layout) -> float (guard fidelity); f2(layout) -> float or None (verification)."""
    t0 = time.time()
    card = state_card(design, base)
    progs = ranker(card, programs)[:k] if ranker else programs[:k]
    scope = design.is_macro & ~design.is_fixed
    cands = []
    for p in progs:
        for s in range(seeds):
            cid = "%s.s%d" % (p["id"], s)
            r = SB.run_program(p["source"], view, None, s)
            if r.status != "ok" or SB.validate_output(design, base, r, scope):
                cands.append({"id": cid, "status": "program_" + r.status, "J1": math.inf})
                continue
            lay, rep = project.legalize_macros(design, SB.to_layout(design, base, r), halo=halo)
            try:
                contract.check(design, lay, base, stage="M", scope=scope)
            except contract.ContractViolation as e:
                cands.append({"id": cid, "status": "contract_violation", "J1": math.inf, "error": str(e)[:200]})
                continue
            if not rep.ok:
                cands.append({"id": cid, "status": "projection_failed", "J1": math.inf})
                continue
            res = refine(bridge, graph, design, [lay], f1, K=K, halo=halo, device=device)[0] if bridge is not None else None
            out = res.layout if res else lay
            cands.append({"id": cid, "status": "ok", "J1": min(res.scores) if res else float(f1(lay)),
                          "alpha": res.alpha if res else None, "layout": out})
    ok = sorted([c for c in cands if c["status"] == "ok"], key=lambda c: c["J1"])
    best_id, best_J = "baseline", baseline_J2
    for c in ok[:beam]:
        c["J2"] = float(f2(c["layout"])) if f2 is not None else math.nan
        if f2 is not None and math.isfinite(c["J2"]) and c["J2"] < best_J:
            best_id, best_J = c["id"], c["J2"]
    for c in cands:
        c.pop("layout", None)
    return OnlineResult(deployed=best_id, J=best_J, baseline_J=baseline_J2, candidates=cands, card=card,
                        wall_s=round(time.time() - t0, 2), llm_calls=0)
