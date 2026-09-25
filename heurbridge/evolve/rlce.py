"""Residual-localized contrastive evolution, diagnosis step (task T5.4, proposal s.3.7).

1. run: x^h (parent output), x_hat = guarded bridge output, x_star = matched elite
2. attribution: integrated gradients of the differentiable surrogate J0 along x_star -> x_hat (64 steps);
   completeness: sum_i alpha_i = J0(x_hat) - J0(x_star) (macro terms + a cluster residual term)
3. reachability split: rho_M = 90th percentile of per-macro displacements |x^h - x_star| that the bridge
   reduces below one site (calibrated on validation pairs); macros beyond rho_M or with an orientation
   mismatch (struct_err) are structural
4. groups: connected components of structural macros under netlist affinity + spatial proximity; top k_g
5. counterfactual splice: put the group's elite configuration into x^h, re-run bridge + guard, measure
   delta_g = B(x^h) - B(x^h_{g<-star}); g_star = argmax delta_g
6. evidence pack: text for the LLM (+ PNG and JSON for humans)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np
import torch

from ..bridge.sample import refine
from ..core import orient as O
from ..core.design import Design, Layout


@dataclass
class Diagnosis:
    alpha: np.ndarray                 # (M,) attribution per movable macro (macro_order)
    cluster_residual: float
    completeness_gap: float
    structural: np.ndarray            # (M,) bool
    groups: list                      # [list of macro-order indices]
    deltas: list                      # delta per group (same order)
    g_star: int | None
    structural_share: float
    reachable_share: float
    J: dict = field(default_factory=dict)
    evidence: str = ""


def integrated_gradients(scorer, x_star: Layout, x_hat: Layout, steps: int = 64):
    """Per-object IG attribution of J0 on the clustered design; returns (alpha over clustered objects, J0 pair)."""
    cd = scorer.cd
    a = scorer.clustered(x_star)
    b = scorer.clustered(x_hat)
    pa = torch.as_tensor(a.pos, dtype=torch.float32)
    pb = torch.as_tensor(b.pos, dtype=torch.float32)
    diff = pb - pa
    scorer.ctx.set_orient(b.orient)
    grads = torch.zeros_like(pa)
    for k in range(steps):
        beta = (k + 0.5) / steps
        x = (pa + beta * diff).requires_grad_(True)
        j = scorer.f0.surrogate_j0(scorer.ctx, x, scorer.norm, scorer.weights)[0]
        g, = torch.autograd.grad(j, x)
        grads += g
    alpha = (grads / steps * diff).sum(1).numpy()
    with torch.no_grad():
        ja = float(scorer.f0.surrogate_j0(scorer.ctx, pa, scorer.norm, scorer.weights)[0])
        jb = float(scorer.f0.surrogate_j0(scorer.ctx, pb, scorer.norm, scorer.weights)[0])
    return alpha, ja, jb


def calibrate_rho(pairs: list, site: float) -> float:
    """rho_M from validation triples (x_h, x_bridge, x_star) of macro positions (normalized)."""
    d, ok = [], []
    for xh, xb, xs in pairs:
        di = np.linalg.norm(xh - xs, axis=1)
        ei = np.linalg.norm(xb - xs, axis=1)
        d.append(di)
        ok.append(ei < site)
    d, ok = np.concatenate(d), np.concatenate(ok)
    return float(np.quantile(d[ok], 0.9)) if ok.any() else 0.0


def structural_groups(design: Design, view, x_h: Layout, structural: np.ndarray, alpha: np.ndarray,
                      k_g: int = 6, aff_q: float = 0.5, prox: float = 2.0, max_group: int = 8) -> list:
    """Connected components of structural macros (macro_order indices), ranked by positive attribution.

    A component larger than ``max_group`` is split: groups are grown (breadth-first over the same adjacency,
    higher attribution first) from its highest-attribution ungrouped member, up to ``max_group`` macros.
    Without the bound, a weak bridge (rho ~ 0: every macro structural) on a dense design yields one
    component holding every macro (ibm01 dev: 246 of 246), which localizes nothing."""
    mo = view.macro_order
    idx = np.flatnonzero(structural)
    if len(idx) == 0:
        return []
    aff = view.macro_aff[np.ix_(idx, idx)]
    thr = np.quantile(view.macro_aff[view.macro_aff > 0], aff_q) if (view.macro_aff > 0).any() else np.inf
    pos = x_h.pos[mo[idx]]
    sz = view.macro_size[idx]
    reach = prox * np.maximum(sz[:, None, :], sz[None, :, :]).max(-1)
    near = np.linalg.norm(pos[:, None] - pos[None], axis=-1) < reach
    adj = (aff >= thr) | near
    np.fill_diagonal(adj, False)
    a_pos = np.clip(alpha[idx], 0, None)
    seen, comps = set(), []
    for s in range(len(idx)):
        if s in seen:
            continue
        stack, comp = [s], []
        seen.add(s)
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in np.flatnonzero(adj[u]):
                if v not in seen:
                    seen.add(int(v))
                    stack.append(int(v))
        comps.append(comp)
    groups = []
    for comp in comps:
        if len(comp) <= max_group:
            groups.append(comp)
            continue
        left = set(comp)
        while left:
            seed = max(left, key=lambda u: (a_pos[u], -u))
            grp, frontier = [seed], [seed]
            left.discard(seed)
            while frontier and len(grp) < max_group:
                nb = sorted({int(v) for u in frontier for v in np.flatnonzero(adj[u]) if int(v) in left},
                            key=lambda v: (-a_pos[v], v))
                frontier = []
                for v in nb[: max_group - len(grp)]:
                    grp.append(v)
                    frontier.append(v)
                    left.discard(v)
            groups.append(grp)
    out = [sorted(int(idx[u]) for u in g) for g in groups]
    out.sort(key=lambda g: -float(np.clip(alpha[g], 0, None).sum()))
    return out[:k_g]


def splice(design: Design, view, x_h: Layout, x_star: Layout, group: list) -> Layout:
    out = x_h.copy()
    objs = view.macro_order[group]
    out.pos[objs] = x_star.pos[objs]
    out.orient[objs] = x_star.orient[objs]
    return out


def diagnose(design: Design, view, bundle_graph, model, scorer, x_h: Layout, x_star: Layout, rho: float,
             k_g: int = 6, K: int = 20, ig_steps: int = 64, evaluate=None) -> Diagnosis:
    """Full RLCE diagnosis of one parent output on one design (evaluate defaults to the f0 scorer)."""
    evaluate = evaluate or scorer
    mo = view.macro_order
    r0 = refine(model, bundle_graph, design, [x_h], evaluate, K=K)[0]
    x_hat = r0.layout
    alpha_all, j_star, j_hat = integrated_gradients(scorer, x_star, x_hat, ig_steps)
    keep_col = -np.ones(design.n_objects, dtype=np.int64)
    keep_col[scorer.cd.keep] = np.arange(scorer.cd.n_keep)
    alpha = alpha_all[keep_col[mo]]
    cluster_res = float(alpha_all[scorer.cd.n_keep:].sum())
    gap = float(alpha_all.sum() - (j_hat - j_star))
    disp = np.linalg.norm(x_h.pos[mo] - x_star.pos[mo], axis=1)
    orient_err = x_h.orient[mo] != x_star.orient[mo]
    structural = (disp > rho) | orient_err
    pos_a = np.clip(alpha, 0, None)
    tot = pos_a.sum() or 1.0
    ss = float(pos_a[structural].sum() / tot)
    groups = structural_groups(design, view, x_h, structural, alpha, k_g)
    base_B = min(r0.scores)
    deltas = []
    for g in groups:
        rs = refine(model, bundle_graph, design, [splice(design, view, x_h, x_star, g)], evaluate, K=K)[0]
        deltas.append(float(base_B - min(rs.scores)))
    g_star = int(np.argmax(deltas)) if deltas else None
    dg = Diagnosis(alpha=alpha, cluster_residual=cluster_res, completeness_gap=gap, structural=structural,
                   groups=groups, deltas=deltas, g_star=g_star, structural_share=ss, reachable_share=1.0 - ss,
                   J={"J0_star": j_star, "J0_hat": j_hat, "B_parent": base_B, "alpha_bridge": r0.alpha})
    dg.evidence = evidence_text(design, view, x_h, x_star, dg)
    return dg


def evidence_text(design, view, x_h, x_star, dg: Diagnosis, max_members: int = 12) -> str:
    """The LLM's evidence pack (text): decisive group, its members, what differs from the elite."""
    lines = ["Post-bridge cost of the parent: %.4f (bridge step alpha=%s); elite J0 %.4f, bridged J0 %.4f."
             % (dg.J["B_parent"], dg.J["alpha_bridge"], dg.J["J0_star"], dg.J["J0_hat"]),
             "Structural share of the remaining gap: %.0f%% (the bridge already fixes the other %.0f%%: continuous, local offsets)."
             % (100 * dg.structural_share, 100 * dg.reachable_share)]
    if dg.g_star is None:
        lines.append("No structural macro group found: remaining error is bridge-reachable.")
        return "\n".join(lines)
    if dg.deltas[dg.g_star] <= 0:
        lines.append("No structural group improves the post-bridge cost when copied from the elite (best "
                     "counterfactual gain %.4f over %d groups): the parent's remaining error is not localized in a "
                     "macro group; change the global strategy rather than a group." % (dg.deltas[dg.g_star], len(dg.groups)))
        return "\n".join(lines)
    g = dg.groups[dg.g_star]
    mo = view.macro_order
    lines.append("Decisive group (counterfactual gain %.4f if placed like the elite): %d macros." % (dg.deltas[dg.g_star], len(g)))
    for k in g[:max_members]:
        i = mo[k]
        h, s = x_h.pos[i], x_star.pos[i]
        lines.append("  macro #%d size=(%.3f,%.3f) group=%d  yours=(%.3f,%.3f) %s  elite=(%.3f,%.3f) %s  io_pull=(%.2f,%.2f)"
                     % (k, *view.macro_size[k], view.macro_group[k], h[0], h[1], O.NAMES[x_h.orient[i]], s[0], s[1],
                        O.NAMES[x_star.orient[i]], *view.io_pull[k]))
    others = [k2 for k2 in range(len(mo)) if k2 not in g]
    link = view.macro_aff[np.ix_(g, others)].sum() if others else 0.0
    lines.append("Group connectivity: internal %.3g, to other macros %.3g, to fixed objects %.3g."
                 % (view.macro_aff[np.ix_(g, g)].sum() / 2, link, view.io_w[g].sum()))
    return "\n".join(lines)


def save_evidence_png(path, design, view, x_h: Layout, x_hat: Layout, x_star: Layout, group: list | None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    mo = view.macro_order
    fig, axs = plt.subplots(1, 3, figsize=(12, 4))
    for ax, lay, title in zip(axs, (x_h, x_hat, x_star), ("heuristic x^h", "bridged x_hat", "elite x*")):
        eff = O.effective_size(design.size, lay.orient) / design.core_wh
        for k, i in enumerate(mo):
            c = lay.pos[i]
            hi = group is not None and k in group
            ax.add_patch(Rectangle(c - eff[i] / 2, *eff[i], fc="#d62728" if hi else "#9ecae1", ec="k", lw=0.4, alpha=0.8))
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect("equal"); ax.set_title(title); ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
