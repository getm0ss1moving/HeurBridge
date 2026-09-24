"""Interface contract checker (mechanism I1, task T1.2).

Called at every stage boundary.  A violation raises ContractViolation and is
never repaired automatically: the caller must fall back (e.g. to the baseline).

Checks
  schema     layout.schema == design.schema_hash()  (object order, sizes, pins, nets)
  shape      pos (N,2) float64, orient (N,) integer
  orient     orientation enum in 0..7
  finite     every object that must be placed has finite coordinates
  range      movable objects inside the core box [0,1]^2 (centres, with tolerance)
  fixed      fixed objects (and IOs) identical to the reference layout
  keep       objects outside the stage's scope unchanged (e.g. cells in the macro stage)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .design import Design, Layout


class ContractViolation(RuntimeError):
    def __init__(self, stage: str, failures: list):
        self.stage = stage
        self.failures = failures
        super().__init__("contract violation at %s: %s" % (stage, "; ".join(failures)))


@dataclass
class ContractReport:
    stage: str
    ok: bool
    failures: list = field(default_factory=list)
    checks: dict = field(default_factory=dict)


def check(design: Design, layout: Layout, reference: Layout | None = None, stage: str = "",
          scope: np.ndarray | None = None, require_placed: np.ndarray | None = None,
          range_tol: float = 1e-9, fixed_atol: float = 0.0, raise_on_fail: bool = True) -> ContractReport:
    """Validate ``layout`` against ``design`` (and against ``reference`` for fixed/unchanged objects).

    scope          bool mask of objects this stage may move (default: all movable objects)
    require_placed bool mask of objects that must have finite positions (default: scope)
    """
    fails, checks = [], {}
    n = design.n_objects

    def rec(name, ok, msg=""):
        checks[name] = bool(ok)
        if not ok:
            fails.append("%s: %s" % (name, msg))

    rec("schema", layout.schema == design.schema_hash(),
        "layout schema %s != design %s" % (layout.schema, design.schema_hash()))
    shape_ok = (isinstance(layout.pos, np.ndarray) and layout.pos.shape == (n, 2) and layout.pos.dtype == np.float64
                and isinstance(layout.orient, np.ndarray) and layout.orient.shape == (n,)
                and np.issubdtype(layout.orient.dtype, np.integer))
    rec("shape", shape_ok, "pos %s/%s orient %s/%s (N=%d)" % (
        getattr(layout.pos, "shape", None), getattr(layout.pos, "dtype", None),
        getattr(layout.orient, "shape", None), getattr(layout.orient, "dtype", None), n))
    if not shape_ok:
        rep = ContractReport(stage, False, fails, checks)
        if raise_on_fail:
            raise ContractViolation(stage, fails)
        return rep

    rec("orient", bool(np.all((layout.orient >= 0) & (layout.orient < 8))),
        "orientation outside 0..7 at %s" % np.flatnonzero((layout.orient < 0) | (layout.orient >= 8))[:5].tolist())

    movable = ~design.is_fixed
    scope = movable if scope is None else (np.asarray(scope, dtype=bool) & movable)
    need = scope if require_placed is None else np.asarray(require_placed, dtype=bool)
    fin = np.isfinite(layout.pos).all(1)
    bad = np.flatnonzero(need & ~fin)
    rec("finite", len(bad) == 0, "%d objects without finite position, e.g. %s" % (len(bad), bad[:5].tolist()))

    p = layout.pos[scope & fin]
    inside = np.all((p >= -range_tol) & (p <= 1 + range_tol), axis=1) if len(p) else np.array([], dtype=bool)
    nbad = int((~inside).sum()) if len(p) else 0
    rec("range", nbad == 0, "%d movable centres outside the core" % nbad)

    if reference is not None:
        rec("reference_schema", reference.schema == layout.schema, "reference schema differs")
        fx = design.is_fixed
        a, b = layout.pos[fx], reference.pos[fx]
        same = np.array_equal(np.isnan(a), np.isnan(b))
        fa = np.isfinite(a)
        same = same and (np.array_equal(a[fa], b[fa]) if fixed_atol == 0.0 else np.allclose(a[fa], b[fa], atol=fixed_atol))
        same = same and np.array_equal(layout.orient[fx], reference.orient[fx])
        rec("fixed", same, "fixed objects moved or re-oriented")
        out_scope = movable & ~scope
        if out_scope.any():
            a, b = layout.pos[out_scope], reference.pos[out_scope]
            fa = np.isfinite(a) & np.isfinite(b)
            keep = np.array_equal(np.isnan(a), np.isnan(b)) and np.array_equal(a[fa], b[fa]) \
                and np.array_equal(layout.orient[out_scope], reference.orient[out_scope])
            rec("keep", keep, "objects outside the stage scope changed")

    rep = ContractReport(stage, not fails, fails, checks)
    if fails and raise_on_fail:
        raise ContractViolation(stage, fails)
    return rep
