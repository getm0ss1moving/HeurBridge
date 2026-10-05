"""Racing, the J_safe pick and the headroom demo's go rule for cell-stage recipes.

These rules are fixed in code before any run of the headroom demo (C1 in the local cell-stage plan).  A position is
one run of a layout under a recipe at one shift: (J before the gates, setup check passed, hold check passed), with
+inf and two failed checks for a failed flow, as in scripts/timing_safety_report.py:44-53.

  race(scores, k)      the k best recipes by f1 J before the gates (failures last; ties by recipe id)
  summarize(pos)       J = median J over the positions, S = share of the timing checks passed,
                       J_safe = J + lam (1 - S) with lam = 0.04 (decision D13 (a); scripts/timing_safety_report.py:56-63)
  pick(arms)           the lowest J_safe among the recipes measured at the most positions (ties: lower J, then id);
                       None when none is finite
  band_below(a, b)     every J of band a is finite and below every J of band b
  go_rule(results, r0) the go rule: method work beyond the best single recipe starts only if (a) on at least 2
                       designs some recipe's whole shift band lies below the default's (r0) for a layout, or some
                       recipe completes every shift of a layout on which the default has a flow failure (the stalls
                       appear as DPL-0036 failures, timeouts or unparsed failures: reports/PROGRESS.md, section 8, the
                       failure taxonomy), and (b) on at least one design the picked recipe differs between two layouts
"""

from __future__ import annotations

import math

import numpy as np

LAMBDA = 0.04


def _j(p) -> float:
    return float(p[0]) if p[0] is not None and math.isfinite(float(p[0])) else math.inf


def race(scores: dict, k: int, exclude=()) -> list:
    """Recipe ids, the k best by score (lower is better; a failure is +inf and ranks last)."""
    ids = sorted((rid for rid in scores if rid not in set(exclude)),
                 key=lambda rid: (_j((scores[rid],)), str(rid)))
    return ids[:max(0, int(k))]


def summarize(positions, lam: float = LAMBDA) -> dict:
    pos = list(positions)
    if not pos:
        return {"J": math.inf, "S": 0.0, "J_safe": math.inf, "positions": 0, "failed": 0}
    js = [_j(p) for p in pos]
    passed = sum(bool(p[1]) + bool(p[2]) for p in pos)
    s = passed / (2.0 * len(pos))
    j = float(np.median(js))
    return {"J": j, "S": s, "J_safe": j + lam * (1.0 - s), "positions": len(pos),
            "failed": sum(not math.isfinite(x) for x in js)}


def pick(arms: dict, lam: float = LAMBDA):
    """The recipe id with the lowest J_safe among those measured at the most positions (decision D13 (a): compared
    layouts have equal positions)."""
    if not arms:
        return None
    npos = max(len(v) for v in arms.values())
    cands = []
    for rid, pos in arms.items():
        if len(pos) == npos:
            s = summarize(pos, lam)
            cands.append((s["J_safe"], s["J"], str(rid), rid))
    best = min(cands)
    return best[3] if math.isfinite(best[0]) else None


def band_below(a, b) -> bool:
    ja, jb = [_j((x,)) for x in a], [_j((x,)) for x in b]
    return bool(ja and jb and all(math.isfinite(x) for x in ja) and max(ja) < min(jb))


def go_rule(results: dict, r0, lam: float = LAMBDA) -> dict:
    """``results``: {design: {layout: {recipe id: [positions]}}}, every recipe of a layout at the same shifts as the
    default ``r0``.  Returns the decision and every part of it."""
    below, removed, best, differs = {}, [], {}, []
    for d, layouts in results.items():
        for lay, arms in layouts.items():
            if r0 not in arms:
                raise ValueError("%s/%s has no run of the default recipe %r" % (d, lay, r0))
            ref = [_j(p) for p in arms[r0]]
            for rid, pos in arms.items():
                if rid == r0:
                    continue
                if len(pos) != len(arms[r0]):
                    raise ValueError("%s/%s: recipe %r has %d positions, the default %d" % (d, lay, rid, len(pos), len(ref)))
                js = [_j(p) for p in pos]
                if band_below(js, ref):
                    below.setdefault(d, []).append((lay, rid))
                if any(not math.isfinite(x) for x in ref) and all(math.isfinite(x) for x in js):
                    removed.append((d, lay, rid))
            best[(d, lay)] = pick(arms, lam)
        picks = {best[(d, lay)] for lay in layouts}
        if len(layouts) >= 2 and len(picks) > 1:
            differs.append(d)
    a = len(below) >= 2 or bool(removed)
    return {"go": bool(a and differs), "a": a, "b": bool(differs), "designs_below": below,
            "failures_removed": removed, "picks": {"%s/%s" % k: v for k, v in best.items()}, "designs_differ": differs}
