"""Proxy calibration study E3 and gate G0 (task T6.2; reply_Q1_Q3 s.3.2 L2-L3).

Input rows: one per (design, candidate) with proxy values at fidelity f and signoff values (f2/f3), per
metric and for J.  Per design and metric:
  spearman, kendall            within-design rank agreement (proxy vs signoff)
  top5_recall                  |top-5 by proxy  intersect  top-5 by signoff| / 5
  regret                       signoff(best by proxy) - signoff(true best)
  regret_random                expected regret of a uniformly random choice
Isotonic map signoff ~ g(proxy) (pooled over designs after per-design normalization) with split-conformal
90% intervals (calibration half of the designs, absolute residual quantile).
Gate G0 per (stage, fidelity): mean regret <= 25% of mean random regret AND mean Kendall tau(proxy J,
signoff J) >= 0.5; otherwise the fitness fidelity escalates (f1 -> f2).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import stats as S
from sklearn.isotonic import IsotonicRegression


@dataclass
class GateResult:
    stage: str
    fidelity: str
    admissible: bool
    regret: float
    regret_random: float
    kendall_J: float
    n_designs: int


def per_design(proxy: np.ndarray, signoff: np.ndarray, k: int = 5) -> dict:
    """Lower is better for both arrays (costs)."""
    ok = np.isfinite(proxy) & np.isfinite(signoff)
    p, s = proxy[ok], signoff[ok]
    n = len(p)
    if n < 3:
        return {"n": n}
    kk = min(k, n)
    top_p, top_s = set(np.argsort(p, kind="stable")[:kk]), set(np.argsort(s, kind="stable")[:kk])
    best = s.min()
    return {"n": n, "spearman": float(S.spearmanr(p, s).statistic), "kendall": float(S.kendalltau(p, s).statistic),
            "top5_recall": len(top_p & top_s) / kk, "regret": float(s[int(np.argmin(p))] - best),
            "regret_random": float(s.mean() - best)}


def study(rows: list, metrics: list, design_key: str = "design") -> dict:
    """rows: dicts with design, '<m>_proxy', '<m>_signoff' for m in metrics (use 'J' for the cost)."""
    out = {}
    designs = sorted({r[design_key] for r in rows})
    for m in metrics:
        per = {}
        for d in designs:
            rr = [r for r in rows if r[design_key] == d]
            per[d] = per_design(np.array([r.get(m + "_proxy", np.nan) for r in rr], float),
                                np.array([r.get(m + "_signoff", np.nan) for r in rr], float))
        valid = [v for v in per.values() if v.get("n", 0) >= 3]
        agg = {k: float(np.mean([v[k] for v in valid])) for k in ("spearman", "kendall", "top5_recall", "regret",
                                                                    "regret_random")} if valid else {}
        out[m] = {"per_design": per, "mean": agg, "n_designs": len(valid)}
    return out


def gate_g0(study_J: dict, stage: str, fidelity: str, regret_frac: float = 0.25, tau_min: float = 0.5) -> GateResult:
    m = study_J["mean"]
    if not m:
        return GateResult(stage, fidelity, False, math.nan, math.nan, math.nan, 0)
    ok = (m["regret"] <= regret_frac * m["regret_random"]) and (m["kendall"] >= tau_min)
    return GateResult(stage, fidelity, bool(ok), m["regret"], m["regret_random"], m["kendall"], study_J["n_designs"])


def isotonic_conformal(proxy: np.ndarray, signoff: np.ndarray, design: np.ndarray, level: float = 0.9, seed: int = 0):
    """Fit signoff ~ g(proxy) on half of the designs; conformal half-width from the other half.

    Returns (predict(proxy) -> (lo, mid, hi), info).  Values are per-design normalized by the caller.
    """
    rng = np.random.default_rng(seed)
    ds = np.unique(design)
    rng.shuffle(ds)
    fit_d = set(ds[: max(1, len(ds) // 2)])
    fit = np.array([d in fit_d for d in design])
    ok = np.isfinite(proxy) & np.isfinite(signoff)
    ir = IsotonicRegression(out_of_bounds="clip").fit(proxy[fit & ok], signoff[fit & ok])
    cal = ~fit & ok
    if cal.sum() == 0:
        cal = fit & ok
    res = np.abs(signoff[cal] - ir.predict(proxy[cal]))
    n = len(res)
    q = float(np.quantile(res, min(1.0, math.ceil((n + 1) * level) / n))) if n else math.inf

    def predict(x):
        mid = ir.predict(np.asarray(x, float))
        return mid - q, mid, mid + q
    return predict, {"halfwidth": q, "n_fit": int((fit & ok).sum()), "n_cal": int(cal.sum())}


def write_admissible(results: list, path) -> None:
    import yaml
    doc = {"generated_by": "heurbridge.stats.calibration", "rule": "regret <= 0.25 * random and kendall(J) >= 0.5",
           "stages": {}}
    for r in results:
        doc["stages"].setdefault(r.stage, {})[r.fidelity] = {
            "admissible": r.admissible, "regret": r.regret, "regret_random": r.regret_random,
            "kendall_J": r.kendall_J, "n_designs": r.n_designs}
    for st, fids in doc["stages"].items():
        order = sorted(fids, key=lambda f: int(str(f).lstrip("f")) if str(f).lstrip("f").isdigit() else 9)
        adm = [f for f in order if fids[f]["admissible"]]
        doc["stages"][st]["fitness_fidelity"] = adm[0] if adm else "f2"
    with open(path, "w") as fh:
        yaml.safe_dump(doc, fh, sort_keys=False)
