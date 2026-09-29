"""Critical-net weights for macro placement (Track-B plan: timing-aware macro cost).

A timing probe (``eval.orfs.macro_pin_slacks``) reads the setup slack at every signal pin of every macro, with
the tool's own macro layout placed by the flow and placement parasitics.  A net that touches a macro pin gets

    w = w0 * (1 + beta * c^2),   c = clip((s_thr - s) / (s_thr - s_min), 0, 1)

where s is the worst setup slack over the net's macro pins, s_min the worst over all macro pins and
s_thr = frac * clock period (default 10 %).  Nets with more slack than s_thr keep their weight; the most critical
get 1 + beta times it.  Unconstrained pins (no timing path) and nets without macro pins keep their weight.

Every macro program (through the sandbox view), P_M's affinity and f0 read ``Design.net_weight``, so a weighted
copy of the design makes all of them timing-aware without touching a program.  No hold term: hold is repaired by
buffering, not by macro distance.  Deterministic.
"""

from __future__ import annotations

import copy
import hashlib
import json

import numpy as np

from .design import Design


def macro_net_slack(design: Design, slacks: dict) -> tuple[np.ndarray, dict]:
    """(M,) worst setup slack per net over its macro pins (NaN: no constrained macro pin) and a coverage summary.
    ``slacks``: {(macro name, pin name): (setup, hold)} as returned by ``orfs.macro_pin_slacks``."""
    if design.pin_names is None:
        raise ValueError("the design has no pin names (bookshelf input): the probe cannot be mapped")
    net_of = design.net_of_pin()
    s = np.full(design.n_nets, np.nan)
    found = unconstrained = 0
    macro_pins = np.flatnonzero(design.is_macro[design.pin_obj])
    keys = set()
    for p in macro_pins:
        k = (design.names[design.pin_obj[p]], design.pin_names[p])
        v = slacks.get(k)
        if v is None:
            continue
        keys.add(k)
        found += 1
        if v[0] is None:
            unconstrained += 1
            continue
        n = net_of[p]
        if n >= 0 and not (s[n] <= v[0]):          # NaN or larger: keep the worst
            s[n] = v[0]
    probe_only = len([k for k in slacks if k not in keys])
    return s, {"macro_pins": int(len(macro_pins)), "matched": found, "unconstrained": unconstrained,
               "probe_pins_unmatched": probe_only, "nets_with_slack": int(np.isfinite(s).sum())}


def critical_net_weights(design: Design, slacks: dict, clock_period_ns: float, beta: float = 4.0,
                         frac: float = 0.1) -> tuple[np.ndarray, dict]:
    """(M,) net weights and a summary; see the module docstring."""
    if not clock_period_ns or clock_period_ns <= 0:
        raise ValueError("clock period must be positive")
    s, info = macro_net_slack(design, slacks)
    w = np.asarray(design.net_weight, np.float64).copy()
    ok = np.isfinite(s)
    s_thr = frac * float(clock_period_ns)
    if ok.any():
        s_min = float(s[ok].min())
        c = np.zeros(design.n_nets)
        if s_min < s_thr:
            c[ok] = np.clip((s_thr - s[ok]) / (s_thr - s_min), 0.0, 1.0)
        w *= 1.0 + beta * c ** 2
        info.update(worst_slack_ns=s_min, nets_weighted=int((c > 0).sum()), max_weight=float(w.max()))
    info.update(beta=beta, frac=frac, clock_period_ns=float(clock_period_ns), threshold_ns=s_thr)
    return w, info


def weighted_design(design: Design, weights: np.ndarray, tag: str = "tw") -> Design:
    """A copy of ``design`` with ``weights`` as its net weights; ``source['net_weights']`` records their hash."""
    w = np.asarray(weights, np.float64)
    if w.shape != (design.n_nets,) or not np.isfinite(w).all() or (w <= 0).any():
        raise ValueError("net weights must be positive and finite, one per net")
    d = copy.copy(design)
    d.net_weight = w.copy()
    d.source = dict(design.source, net_weights={"tag": tag, "sha256_16": hashlib.sha256(w.tobytes()).hexdigest()[:16]})
    return d


def save_slacks(path, slacks: dict, meta: dict) -> None:
    rows = [[k[0], k[1], v[0], v[1]] for k, v in sorted(slacks.items())]
    with open(path, "w") as fh:
        json.dump({"meta": meta, "pins": rows}, fh)


def load_slacks(path) -> tuple[dict, dict]:
    with open(path) as fh:
        d = json.load(fh)
    return {(r[0], r[1]): (r[2], r[3]) for r in d["pins"]}, d["meta"]
