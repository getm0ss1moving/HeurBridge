"""Evaluation partners for experiment E0 / gate G0' (task T4).

Every partner receives the same heuristic output (a macro layout) and returns a macro layout that
the caller projects with P_M and scores at f2.  Partners that search internally use the macro-stage
f0 scorer (core.cluster_design.MacroStageScorer) and a wall-clock budget; E0 sets the budgets of the
memetic and repertoire partners to the co-trained bridge's median time per call (including its guard).

  none        identity
  memetic     simulated annealing with the T2.7 move set (shift +-1..3 pitch, swap same-size, flip)
  repertoire  SpecAHD-style checked repair: regions = macro clusters; repair programs: move to the
              connected centroid, swap with the nearest same-size macro, snap to the nearest boundary,
              re-tile the group; each tried per region, accepted only if f0 improves (rollback otherwise)
  frozen_gen  pretrained noise->layout model NOT trained on heuristic outputs, used by partial noising:
              x_s = (1-s) noise + s x_h, integrate from tau=s to 1, s in {0.25, 0.5, 0.75}; best by f0
  cotrained   the HeurBridge bridge (trained on the population's outputs) with the guard
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import numpy as np
import torch

from .core import orient as O, project
from .core.design import Design, Layout


@dataclass
class PartnerResult:
    layout: Layout
    wall_s: float
    evals: int = 0
    info: dict = field(default_factory=dict)


class Partner:
    name = "base"

    def __call__(self, design: Design, layout: Layout, rng: np.random.Generator, budget_s: float | None = None) -> PartnerResult:
        raise NotImplementedError


class NonePartner(Partner):
    name = "none"

    def __call__(self, design, layout, rng, budget_s=None):
        return PartnerResult(layout.copy(), 0.0)


def _pitch(design: Design, layout: Layout, i: int) -> np.ndarray:
    return O.effective_size(design.size[i:i + 1], layout.orient[i:i + 1])[0] / design.core_wh


class MemeticPartner(Partner):
    name = "memetic"

    def __init__(self, scorer, halo: float = 0.0, T0: float = 0.01, cool: float = 0.97):
        self.scorer, self.halo, self.T0, self.cool = scorer, halo, T0, cool

    def __call__(self, design, layout, rng, budget_s=10.0):
        t0 = time.time()
        mm = np.flatnonzero(design.is_macro & ~design.is_fixed)
        masters = design.masters or ["%.6g_%.6g" % tuple(v) for v in design.size]
        cur, _ = project.legalize_macros(design, layout, halo=self.halo)
        fc = self.scorer(cur)
        best, fb = cur, fc
        T, n = self.T0, 1
        while time.time() - t0 < (budget_s or 10.0) and len(mm):
            c = cur.copy()
            u = rng.random()
            i = int(rng.choice(mm))
            if u < 0.6:
                ax = int(rng.integers(2))
                p = _pitch(design, c, i)
                c.pos[i, ax] = float(np.clip(c.pos[i, ax] + int(rng.choice([-3, -2, -1, 1, 2, 3])) * p[ax], p[ax] / 2, 1 - p[ax] / 2))
            elif u < 0.85:
                same = [j for j in mm if j != i and masters[j] == masters[i]]
                if not same:
                    continue
                j = int(rng.choice(same))
                c.pos[[i, j]] = c.pos[[j, i]]
            else:
                c.orient[i] = int(rng.choice([o for o in (O.R0, O.MX, O.MY, O.R180) if o != c.orient[i]]))
            c, rep = project.legalize_macros(design, c, halo=self.halo)
            if not rep.ok:
                continue
            f = self.scorer(c)
            n += 1
            if f < fc or rng.random() < math.exp(-(f - fc) / max(T, 1e-12)):
                cur, fc = c, f
                if f < fb:
                    best, fb = c, f
            T *= self.cool
        return PartnerResult(best, time.time() - t0, n, {"f0": fb})


class RepertoirePartner(Partner):
    name = "repertoire"

    def __init__(self, scorer, affinity: np.ndarray, macro_order: np.ndarray, halo: float = 0.0, n_regions: int | None = None):
        self.scorer, self.halo = scorer, halo
        self.aff, self.order = affinity, macro_order          # DesignView.macro_aff / macro_order
        self.n_regions = n_regions

    def _regions(self):
        from scipy.cluster.hierarchy import fcluster, linkage
        M = len(self.order)
        if M < 3:
            return [list(range(M))]
        a = self.aff + self.aff.T
        dist = 1.0 - a / (a.max() or 1.0)
        np.fill_diagonal(dist, 0.0)
        k = self.n_regions or max(2, int(round(math.sqrt(M))))
        lab = fcluster(linkage(dist[np.triu_indices(M, 1)], "average"), t=k, criterion="maxclust")
        return [list(np.flatnonzero(lab == g)) for g in np.unique(lab)]

    def _repairs(self, design, lay, region, rng):
        """Candidate repaired layouts for one region (each a full layout)."""
        idx = self.order[region]
        pos = lay.pos
        out = []
        # 1 move to connected centroid (affinity-weighted mean of connected macros outside the region)
        c = lay.copy()
        for k, i in zip(region, idx):
            w = self.aff[k].copy()
            w[region] = 0
            if w.sum() > 0:
                tgt = (w[:, None] * pos[self.order]).sum(0) / w.sum()
                c.pos[i] = 0.5 * pos[i] + 0.5 * tgt
        out.append(("centroid", c))
        # 2 swap each macro with its nearest same-size macro (outside the region)
        c = lay.copy()
        masters = design.masters or ["%.6g_%.6g" % tuple(v) for v in design.size]
        for i in idx:
            cand = [j for j in self.order if j not in idx and masters[j] == masters[i]]
            if cand:
                j = min(cand, key=lambda j: float(np.linalg.norm(pos[j] - pos[i])))
                c.pos[[i, j]] = c.pos[[j, i]]
        out.append(("swap_nearest", c))
        # 3 snap to the nearest boundary
        c = lay.copy()
        for i in idx:
            h = _pitch(design, c, i) / 2
            p = c.pos[i]
            d = [p[0] - h[0], 1 - h[0] - p[0], p[1] - h[1], 1 - h[1] - p[1]]
            s = int(np.argmin(d))
            c.pos[i] = [(h[0], p[1]), (1 - h[0], p[1]), (p[0], h[1]), (p[0], 1 - h[1])][s]
        out.append(("snap_boundary", c))
        # 4 re-tile the group as a compact row-major block at its centroid
        c = lay.copy()
        cen = pos[idx].mean(0)
        r = int(math.ceil(math.sqrt(len(idx))))
        sz = np.array([_pitch(design, c, i) for i in idx])
        wmax, hmax = sz[:, 0].max(), sz[:, 1].max()
        for q, i in enumerate(idx):
            c.pos[i] = cen + [(q % r - (r - 1) / 2) * wmax, (q // r - (r - 1) / 2) * hmax]
        out.append(("retile", c))
        return out

    def __call__(self, design, layout, rng, budget_s=None):
        t0 = time.time()
        cur, _ = project.legalize_macros(design, layout, halo=self.halo)
        fc = self.scorer(cur)
        n, accepted = 1, []
        regions = self._regions()
        for g in (rng.permutation(len(regions)) if len(regions) > 1 else [0]):
            if budget_s and time.time() - t0 > budget_s:
                break
            best = (fc, None, None)
            for name, cand in self._repairs(design, cur, regions[g], rng):
                cp, rep = project.legalize_macros(design, cand, halo=self.halo)
                if not rep.ok:
                    continue
                f = self.scorer(cp)
                n += 1
                if f < best[0]:
                    best = (f, cp, name)
            if best[1] is not None:                      # checked merge; otherwise rollback (keep cur)
                fc, cur = best[0], best[1]
                accepted.append(best[2])
        return PartnerResult(cur, time.time() - t0, n, {"f0": fc, "accepted": accepted})


class FrozenGenPartner(Partner):
    """Noise->layout generator (T3.4 pretraining) used as a refiner by partial noising (SDEdit-style)."""
    name = "frozen_gen"

    def __init__(self, model, graph, scorer, levels=(0.25, 0.5, 0.75), K: int = 20, halo: float = 0.0, device="cpu"):
        self.model, self.graph, self.scorer = model, graph, scorer
        self.levels, self.K, self.halo, self.device = levels, K, halo, device

    @torch.no_grad()
    def __call__(self, design, layout, rng, budget_s=None):
        from .bridge.sample import source_nodes
        t0 = time.time()
        g = self.graph
        gt = g.tensors(self.device)
        xh = source_nodes(g, layout)
        best_l, _ = project.legalize_macros(design, layout, halo=self.halo)
        best = (self.scorer(best_l), best_l, 0.0)
        mov = g.movable
        for s in self.levels:
            noise = rng.uniform(0.05, 0.95, xh.shape)
            x = xh.copy()
            x[mov] = (1 - s) * noise[mov] + s * xh[mov]
            xt = torch.as_tensor(x[None], dtype=torch.float32, device=self.device)
            k0 = int(round(s * self.K))
            for k in range(k0, self.K):
                v = self.model(xt, torch.full((1,), k / self.K, device=self.device), gt).float()
                xt = xt + v / self.K
            cand, rep = project.legalize_macros(design, g.to_layout(xt[0].cpu().numpy().astype(np.float64), layout), halo=self.halo)
            if rep.ok:
                f = self.scorer(cand)
                if f < best[0]:
                    best = (f, cand, s)
        return PartnerResult(best[1], time.time() - t0, len(self.levels) + 1, {"f0": best[0], "level": best[2]})


class CotrainedPartner(Partner):
    name = "cotrained"

    def __init__(self, model, graph, evaluate, K: int = 20, halo: float = 0.0, device="cpu"):
        self.model, self.graph, self.evaluate = model, graph, evaluate
        self.K, self.halo, self.device = K, halo, device

    def __call__(self, design, layout, rng, budget_s=None):
        from .bridge.sample import refine, source_nodes
        t0 = time.time()
        r = refine(self.model, self.graph, design, [layout], self.evaluate, K=self.K, halo=self.halo, device=self.device)[0]
        mv = self.graph.movable
        disp = float(np.linalg.norm(r.x_bridge[mv] - source_nodes(self.graph, layout)[mv], axis=1).mean()) if mv.any() else 0.0
        return PartnerResult(r.layout, time.time() - t0, len(r.scores), {"alpha": r.alpha, "scores": r.scores, "disp": disp})


class RandomGuardPartner(Partner):
    """E0 control: the co-trained bridge's guard (same alpha grid, P_M and evaluator) applied along a random
    displacement of the movable nodes whose mean length matches the bridge's (``scale``, measured on the
    budget sources).  A bridge that does not beat this control adds nothing beyond guarded perturbation."""
    name = "random_guard"

    def __init__(self, graph, evaluate, scale: float, halo: float = 0.0):
        self.graph, self.evaluate, self.scale, self.halo = graph, evaluate, scale, halo

    def __call__(self, design, layout, rng, budget_s=None):
        from .bridge.sample import guarded, source_nodes
        t0 = time.time()
        g = self.graph
        src = source_nodes(g, layout)
        d = rng.normal(size=src.shape) * g.movable[:, None]
        n = np.linalg.norm(d[g.movable], axis=1).mean() if g.movable.any() else 1.0
        end = src + d * (self.scale / max(n, 1e-12))
        r = guarded(g, design, layout, src, end, self.evaluate,
                    project=lambda dd, l: project.legalize_macros(dd, l, halo=self.halo))
        return PartnerResult(r.layout, time.time() - t0, len(r.scores), {"alpha": r.alpha, "scores": r.scores})
