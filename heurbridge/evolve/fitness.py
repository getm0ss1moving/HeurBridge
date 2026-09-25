"""Refinability fitness, predictability probe, portfolio value and pruning (tasks T5.2, T5.3; proposal s.3.4).

B[h, c]  post-bridge cost of program h on design c (guarded partial transport, mean over seeds)
m_H(c)   = min_{h in H} B[h, c]                       (portfolio minimum)
F(h|H)   = E_c[ m_H(c) - min(m_H(c), B[h, c]) ]        (marginal portfolio gain; complementarity)
           - lambda_B * E_c[B[h, c]]                     (standalone term)
           - lambda_t * max(0, runtime_s - t0)           (runtime penalty above t0 = 30 s)
G(H)     = E_c[ max(0, max_{h in H} (B0(c) - B[h, c])) ] (facility location: monotone submodular) -> greedy
           pruning to q programs with the (1 - 1/e) guarantee for a fixed bridge.
pi(h)    = 1 - E||u - g(features, x^h)||_A^2 / E||u - mean(u)||_A^2, u = x* - x^h, g = ridge regression
           fitted on probe designs (Lemma 2 probe; used as a pre-screen only if gate G1 passes).
Raw fitness A(h) (baselines, ablation A1) = cost of P(x^h) without the bridge.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class FitnessConfig:
    lambda_B: float = 0.2
    lambda_t: float = 0.01
    t0: float = 30.0


def refinability_fitness(B_h: np.ndarray, portfolio_B: np.ndarray | None, runtime_s: float,
                         cfg: FitnessConfig | None = None) -> dict:
    """B_h: (C,) post-bridge costs of the candidate; portfolio_B: (H, C) of the current portfolio (or None)."""
    cfg = cfg or FitnessConfig()
    B_h = np.asarray(B_h, float)
    if portfolio_B is None or len(portfolio_B) == 0:
        m = np.full_like(B_h, np.inf)
    else:
        m = np.asarray(portfolio_B, float).min(0)
    new_m = np.minimum(m, B_h)
    gain_terms = np.where(np.isfinite(m), m - new_m, 0.0)          # empty portfolio: no marginal term
    gain = float(np.mean(gain_terms))
    standalone = float(np.mean(np.where(np.isfinite(B_h), B_h, 1e6)))
    pen = cfg.lambda_t * max(0.0, runtime_s - cfg.t0)
    return {"F": gain - cfg.lambda_B * standalone - pen, "gain": gain, "standalone": standalone, "runtime_pen": pen}


def portfolio_value(B: np.ndarray, B0: np.ndarray, members) -> float:
    B = np.asarray(B, float)
    if len(members) == 0:
        return 0.0
    best = (np.asarray(B0, float)[None, :] - B[list(members)]).max(0)
    return float(np.mean(np.clip(best, 0.0, None)))


def greedy_prune(B: np.ndarray, B0: np.ndarray, q: int) -> list:
    """Greedy maximization of the facility-location value G(H) (monotone submodular): (1-1/e)-optimal."""
    chosen, rest = [], list(range(len(B)))
    for _ in range(min(q, len(rest))):
        cur = portfolio_value(B, B0, chosen)
        gains = [(portfolio_value(B, B0, chosen + [h]) - cur, -h) for h in rest]
        g, neg_h = max(gains)
        if g <= 0 and chosen:
            break
        chosen.append(-neg_h)
        rest.remove(-neg_h)
    return chosen


def predictability_probe(features: np.ndarray, xh: np.ndarray, u: np.ndarray, weights: np.ndarray,
                         design_ids: np.ndarray, alpha: float = 1.0) -> float:
    """pi(h) with leave-one-design-out ridge regression.

    features: (S, F) per-sample design/graph features; xh: (S, M, 2) source macro positions; u: (S, M, 2)
    displacement to the matched elite; weights: (M,) area weights a_i; design_ids: (S,) group labels.
    Predicts u per sample from [features, xh (flattened)] -> pi in (-inf, 1].
    """
    S = len(u)
    X = np.concatenate([features, xh.reshape(S, -1)], 1)
    Y = u.reshape(S, -1)
    wa = np.repeat(weights, 2)
    resid, total = 0.0, 0.0
    groups = np.unique(design_ids)
    mean_u = (Y * 1.0).mean(0)
    for g in groups:
        tr, te = design_ids != g, design_ids == g
        if tr.sum() < 2:
            pred = np.tile(mean_u, (te.sum(), 1))
        else:
            mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
            Xt = (X[tr] - mu) / sd
            A = Xt.T @ Xt + alpha * np.eye(X.shape[1])
            W = np.linalg.solve(A, Xt.T @ (Y[tr] - Y[tr].mean(0)))
            pred = ((X[te] - mu) / sd) @ W + Y[tr].mean(0)
        resid += float((wa * (Y[te] - pred) ** 2).sum())
        total += float((wa * (Y[te] - mean_u) ** 2).sum())
    return 1.0 - resid / total if total > 0 else 0.0
