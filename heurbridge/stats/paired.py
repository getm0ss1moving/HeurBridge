"""Statistics for HeurBridge reports and gates (task T7.2).

* paired one-sided Wilcoxon signed-rank (pre-registered direction), with +inf
  costs kept (never dropped): a pair where only one side is +inf counts as a
  maximal difference in the obvious direction; a pair with both +inf is a tie
* Holm-Bonferroni within a hypothesis family
* geometric-mean ratio with stratified bootstrap CI (strata = family)
* Clopper-Pearson interval for failure rates
* Page's L trend test (H5)
* effect floor: practically meaningful only if the CI excludes +-0.5 %
"""

from __future__ import annotations

import math

import numpy as np
from scipy import stats as S

EFFECT_FLOOR = 0.005


def _paired_diffs(a, b) -> np.ndarray:
    """d = a - b with +inf handling; finite big number replaces one-sided infinities."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    fin = np.concatenate([a[np.isfinite(a)], b[np.isfinite(b)]])
    big = 10.0 * (np.abs(fin).max() + 1.0) if len(fin) else 1.0
    d = np.empty_like(a)
    for i, (x, y) in enumerate(zip(a, b)):
        if math.isinf(x) and math.isinf(y):
            d[i] = 0.0
        elif math.isinf(x):
            d[i] = big
        elif math.isinf(y):
            d[i] = -big
        else:
            d[i] = x - y
    return d


def wilcoxon_less(a, b) -> dict:
    """H1: a < b (a is better when lower).  Paired, one-sided.  Zero differences are dropped (Wilcox)."""
    d = _paired_diffs(a, b)
    n_nonzero = int((d != 0).sum())
    if n_nonzero == 0:
        return {"p": 1.0, "n": len(d), "n_nonzero": 0, "median_diff": 0.0, "frac_better": 0.0}
    res = S.wilcoxon(d, alternative="less", zero_method="wilcox")
    return {"p": float(res.pvalue), "stat": float(res.statistic), "n": len(d), "n_nonzero": n_nonzero,
            "median_diff": float(np.median(d)), "frac_better": float((d < 0).mean())}


def holm(pvals: dict | list, alpha: float = 0.05) -> dict:
    """Holm step-down.  Returns {name: {"p": p, "p_adj": ..., "reject": bool}}."""
    items = list(pvals.items()) if isinstance(pvals, dict) else list(enumerate(pvals))
    order = sorted(items, key=lambda kv: kv[1])
    m = len(order)
    out, running, stop = {}, 0.0, False
    for rank, (name, p) in enumerate(order):
        adj = min(1.0, (m - rank) * p)
        running = max(running, adj)
        rej = (not stop) and p <= alpha / (m - rank)
        stop = stop or not rej
        out[name] = {"p": float(p), "p_adj": float(running), "reject": bool(rej)}
    return out


def geomean_ratio(method, base, strata=None, n_boot: int = 10000, seed: int = 0, ci: float = 0.95) -> dict:
    """Geometric mean of method/base (lower is better) with stratified bootstrap CI.

    Pairs with an infinite side are not ratio-able; they are counted and reported, not dropped silently.
    """
    m, b = np.asarray(method, float), np.asarray(base, float)
    ok = np.isfinite(m) & np.isfinite(b) & (m > 0) & (b > 0)
    lr = np.log(m[ok] / b[ok])
    st = np.zeros(len(m), dtype=object) if strata is None else np.asarray(strata, dtype=object)
    st = st[ok]
    rng = np.random.default_rng(seed)
    groups = [np.flatnonzero(st == g) for g in dict.fromkeys(st.tolist())]
    boots = np.empty(n_boot)
    for t in range(n_boot):
        idx = np.concatenate([rng.choice(g, size=len(g), replace=True) for g in groups]) if groups else np.array([], int)
        boots[t] = lr[idx].mean() if len(idx) else np.nan
    lo, hi = np.nanquantile(boots, [(1 - ci) / 2, 1 - (1 - ci) / 2]) if len(lr) else (np.nan, np.nan)
    gm = float(np.exp(lr.mean())) if len(lr) else float("nan")
    r_lo, r_hi = float(np.exp(lo)), float(np.exp(hi))
    return {"ratio": gm, "ci": (r_lo, r_hi), "n": int(ok.sum()), "n_excluded_inf": int((~ok).sum()),
            "meaningful": bool(r_hi < 1 - EFFECT_FLOOR or r_lo > 1 + EFFECT_FLOOR)}


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    lo = 0.0 if k == 0 else float(S.beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(S.beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi


def page_trend(data, predicted_ranks=None) -> dict:
    """Page's L for an increasing trend across columns (e.g. generations); rows = blocks (designs)."""
    res = S.page_trend_test(np.asarray(data, float), ranked=False, predicted_ranks=predicted_ranks)
    return {"L": float(res.statistic), "p": float(res.pvalue), "method": res.method}


def kendall_tau(x, y) -> float:
    return float(S.kendalltau(x, y).statistic)


def spearman(x, y) -> float:
    return float(S.spearmanr(x, y).statistic)


def mmd2(X, Y, bandwidth: float | None = None) -> dict:
    """Unbiased MMD^2 with a Gaussian kernel (median heuristic bandwidth) between samples X (n,d), Y (m,d).

    Used by Algorithm R (T3.7) to compare training conditions with deployment conditions per stage."""
    X, Y = np.asarray(X, float), np.asarray(Y, float)
    Z = np.concatenate([X, Y], 0)
    d2 = ((Z[:, None, :] - Z[None, :, :]) ** 2).sum(-1)
    if bandwidth is None:
        med = np.median(d2[np.triu_indices(len(Z), 1)])
        bandwidth = math.sqrt(0.5 * med) if med > 0 else 1.0
    K = np.exp(-d2 / (2 * bandwidth ** 2))
    n, m = len(X), len(Y)
    kxx, kyy, kxy = K[:n, :n], K[n:, n:], K[:n, n:]
    biased = float(kxx.mean() + kyy.mean() - 2 * kxy.mean())         # V-statistic, >= 0, defined for any n, m
    if n > 1 and m > 1:
        unbiased = float((kxx.sum() - np.trace(kxx)) / (n * (n - 1)) + (kyy.sum() - np.trace(kyy)) / (m * (m - 1))
                         - 2 * kxy.mean())
    else:
        # the unbiased U-statistic needs two samples per side; dropping the missing within-sample term (the earlier
        # behaviour) biased it downward, e.g. -0.26 for 2 training designs vs 1 validation design
        unbiased = float("nan")
    return {"mmd2": unbiased, "mmd2_biased": biased, "bandwidth": float(bandwidth), "n": n, "m": m}
