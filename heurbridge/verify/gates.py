"""Verification layers V3 (metric recompute consistency) and V5 (statistical promotion gate), task T7.1.

V5  promote(candidate, incumbent) for programs, bridge checkpoints and skill edits: the alpha-ledger entry
    is reserved BEFORE the paired data are examined; one-sided paired Wilcoxon (candidate < incumbent) over
    held-out (design, seed) pairs with every failure as +inf; promoted iff p <= alpha_j (Proposition 5).
    Also used for the bridge promotion of Algorithm R (T3.7) and the H8 null-injection check.
V3  recompute_consistency(record, def_path, lefs): HPWL recomputed from the output DEF with the HeurBridge
    loader must match the reported value (relative tolerance), else the record is flagged for a re-run.
"""

from __future__ import annotations

import math

import numpy as np

from ..stats.alpha_ledger import AlphaLedger
from ..stats.paired import wilcoxon_less


def promote(ledger: AlphaLedger, kind: str, artifact: str, candidate: list, incumbent: list, meta: dict | None = None,
            min_pairs: int = 6) -> dict:
    """candidate/incumbent: paired costs (lower is better), +inf for failures.  Returns the decision record."""
    entry = ledger.reserve(kind, artifact, "wilcoxon_less_paired", meta=meta)      # before looking at data
    cand, inc = np.asarray(candidate, float), np.asarray(incumbent, float)
    if len(cand) != len(inc):
        raise ValueError("unpaired data")
    if len(cand) < min_pairs:
        rec = ledger.record(entry, p_value=1.0, n=len(cand), extra={"reason": "too few pairs"})
        return {**rec, "promoted": False}
    t = wilcoxon_less(cand, inc)
    rec = ledger.record(entry, p_value=t["p"], n=len(cand),
                        extra={"median_diff": t["median_diff"], "frac_better": t["frac_better"],
                               "failures_candidate": int(np.isinf(cand).sum()), "failures_incumbent": int(np.isinf(inc).sum())})
    return rec


def null_injection(ledger: AlphaLedger, incumbent_costs: list, placebo_fn, n_placebo: int = 50, seed: int = 0) -> dict:
    """H8: push n placebo artifacts (same behaviour, fresh noise) through the promotion gate; the empirical
    promotion rate must stay <= alpha (Clopper-Pearson upper bound reported)."""
    from ..stats.paired import clopper_pearson
    rng = np.random.default_rng(seed)
    promoted = 0
    for k in range(n_placebo):
        cand = placebo_fn(rng)
        r = promote(ledger, "placebo", "placebo_%d" % k, cand, incumbent_costs)
        promoted += bool(r["promoted"])
    lo, hi = clopper_pearson(promoted, n_placebo)
    return {"n": n_placebo, "promoted": promoted, "rate": promoted / n_placebo, "cp_upper": hi, "alpha": ledger.alpha}


def recompute_consistency(reported_hpwl: float, design, layout, rel_tol: float = 1e-3) -> dict:
    from ..core.design import hpwl
    re = hpwl(design, layout)
    ok = math.isfinite(reported_hpwl) and abs(re - reported_hpwl) <= rel_tol * max(abs(re), 1e-9)
    return {"ok": bool(ok), "reported": reported_hpwl, "recomputed": re,
            "rel_diff": abs(re - reported_hpwl) / max(abs(re), 1e-9) if math.isfinite(reported_hpwl) else math.inf}
