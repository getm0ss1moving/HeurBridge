"""Final cost J and gates (task T1.6; weights frozen in configs/cost.yaml, task spec B.3).

  J = 0.30*rWL~ + 0.05*via~ + 0.15*(1+OF)~ + 0.30*(1-TNS)~ + 0.20*P~,   y~ = y / y_base

with y_base the per-design median over the baseline flow's seeds.  Gates:
  setup WNS, hold WNS   cand >= base - 0.02 ns, and base >= 0 => cand >= 0
                        (eda/docs/METRIC_CONVENTIONS.md s.2, via metrics_schema.guard_status)
  DRC                   == 0
  LVS                   clean, when checked (required at f3)
J_inf = +inf if any gate fails.  Missing inputs are *unchecked*, never passed:
a missing J term makes J partial; a missing required gate makes the result
inadmissible for the elite archive.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import median

WEIGHTS = {"rwl": 0.30, "via": 0.05, "of": 0.15, "tns": 0.30, "power": 0.20}
GUARD_NS = 0.02
REQUIRED_GATES = {0: (), 1: ("setup", "hold"), 2: ("setup", "hold", "drc"), 3: ("setup", "hold", "drc", "lvs")}

# canonical record field for each J term (first present wins)
FIELDS = {
    "rwl": ("detailed_wirelength_um", "wirelength_um", "gr_wl", "hpwl_um"),       # hpwl_um: Track-A proxy only
    "via": ("vias", "gr_vias"),
    "of": ("gr_overflow_total", "rudy_of_pct"),        # rudy_of_pct = 100 * overflow share of RUDY demand: Track-A proxy
    "tns": ("setup_tns_ns",),
    "power": ("total_power_w",),
}


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def canonical(record: dict) -> dict:
    """Canonical timing fields via the HA-PR metrics_schema (red line A.2); fails loudly without it."""
    from .._eda import harness
    return harness("metrics_schema").canonicalize_record(record)


def term_value(record: dict, term: str):
    for key in FIELDS[term]:
        v = _num(record.get(key))
        if v is not None:
            return v, key
    return None, None


def transformed(term: str, v: float) -> float:
    if term == "of":
        return 1.0 + v
    if term == "tns":
        return 1.0 - v          # TNS <= 0 -> 1 + |TNS|
    return v


@dataclass
class Baseline:
    design: str
    values: dict                 # term -> median raw value
    timing: dict                 # setup_wns_ns / hold_wns_ns medians
    n_seeds: int
    sources: dict = field(default_factory=dict)

    @classmethod
    def from_records(cls, design: str, records: list) -> "Baseline":
        recs = [canonical(r) for r in records]
        vals, srcs = {}, {}
        for t in WEIGHTS:
            xs = [term_value(r, t) for r in recs]
            got = [v for v, _ in xs if v is not None]
            if got:
                vals[t] = median(got)
                srcs[t] = sorted({k for _, k in xs if k})
        tim = {}
        for k in ("setup_wns_ns", "hold_wns_ns"):
            got = [_num(r.get(k)) for r in recs]
            got = [v for v in got if v is not None]
            if got:
                tim[k] = median(got)
        return cls(design, vals, tim, len(records), srcs)

    def to_dict(self) -> dict:
        return {"design": self.design, "values": self.values, "timing": self.timing, "n_seeds": self.n_seeds,
                "sources": self.sources}


@dataclass
class CostResult:
    J: float                     # weighted cost over available terms (nan if none)
    J_inf: float                 # +inf if a gate failed, else J
    partial: bool                # some J term missing
    admissible: bool             # no failed gate, all required gates checked, J complete
    terms: dict                  # term -> {raw, base, norm, weighted, source}
    gates: dict                  # gate -> {"status": pass|fail|unchecked, ...}
    fidelity: int
    unchecked: list

    def to_dict(self) -> dict:
        return {"J": self.J, "J_inf": self.J_inf, "partial": self.partial, "admissible": self.admissible,
                "terms": self.terms, "gates": self.gates, "fidelity": self.fidelity, "unchecked": self.unchecked}


def _timing_gate(cand, base, guard=GUARD_NS):
    if cand is None or base is None:
        return {"status": "unchecked", "candidate": cand, "base": base}
    ok = cand >= base - guard and not (base >= 0.0 and cand < 0.0)
    reason = "ok" if ok else ("new_violation_from_met_baseline" if base >= 0 and cand < 0 else "degrades_more_than_guard")
    return {"status": "pass" if ok else "fail", "candidate": cand, "base": base, "guard_ns": guard, "reason": reason}


def evaluate(record: dict, base: Baseline, fidelity: int = 2, weights: dict | None = None,
             required_gates: tuple | None = None) -> CostResult:
    """weights: subset of WEIGHTS (e.g. Track A: rwl + of); required_gates overrides REQUIRED_GATES[fidelity]
    (Track A has no timing: pass ()).  Gates that are not required but missing stay 'unchecked'."""
    w = weights or WEIGHTS
    r = canonical(record)
    terms, unchecked, total, wsum = {}, [], 0.0, 0.0
    for t, wt in w.items():
        v, src = term_value(r, t)
        b = base.values.get(t)
        if v is None or b is None:
            unchecked.append(t)
            terms[t] = {"raw": v, "base": b, "norm": None, "weighted": None, "source": src}
            continue
        denom = transformed(t, b)
        norm = transformed(t, v) / denom if denom != 0 else math.inf
        terms[t] = {"raw": v, "base": b, "norm": norm, "weighted": wt * norm, "source": src}
        total += wt * norm
        wsum += wt
    J = total if wsum > 0 else math.nan
    gates = {
        "setup": _timing_gate(_num(r.get("setup_wns_ns")), base.timing.get("setup_wns_ns")),
        "hold": _timing_gate(_num(r.get("hold_wns_ns")), base.timing.get("hold_wns_ns")),
    }
    drc = _num(r.get("drc_violations"))
    gates["drc"] = {"status": "unchecked"} if drc is None else {"status": "pass" if drc == 0 else "fail", "value": drc}
    lvs = r.get("lvs_errors")
    lvs = _num(lvs)
    gates["lvs"] = {"status": "unchecked"} if lvs is None else {"status": "pass" if lvs == 0 else "fail", "value": lvs}
    if r.get("returncode") not in (None, 0):
        gates["flow"] = {"status": "fail", "returncode": r.get("returncode")}
    failed = any(g["status"] == "fail" for g in gates.values())
    required = REQUIRED_GATES.get(fidelity, ()) if required_gates is None else tuple(required_gates)
    missing_req = [g for g in required if gates[g]["status"] == "unchecked"]
    unchecked += ["gate:" + g for g in missing_req]
    partial = bool([t for t in w if terms[t]["norm"] is None])
    admissible = (not failed) and not missing_req and not partial and math.isfinite(J)
    return CostResult(J=J, J_inf=math.inf if failed else J, partial=partial, admissible=admissible,
                      terms=terms, gates=gates, fidelity=fidelity, unchecked=unchecked)


def decompose(a: CostResult, b: CostResult) -> dict:
    """Per-term Delta J = J(a) - J(b) with raw deltas (L4: never report J without its terms)."""
    out = {}
    for t in WEIGHTS:
        ta, tb = a.terms.get(t, {}), b.terms.get(t, {})
        out[t] = {
            "dJ": None if ta.get("weighted") is None or tb.get("weighted") is None else ta["weighted"] - tb["weighted"],
            "raw_delta": None if ta.get("raw") is None or tb.get("raw") is None else ta["raw"] - tb["raw"],
        }
    return out
