"""Hint programs: cell-stage hints computed from the macro layout of each run (method D's hand-written families).

A recipe names a program and its parameters (CellRecipe.programs); CellStage.prepare runs it on the run's design and
macro layout, and the hints it returns join the recipe's own.  The recipe's id covers the program and its
parameters, so one recipe gives each layout its own hints.

channel_caps   soft density caps over the channels of the macro layout: every gap of width in (min_gap, max_gap]
               microns between two facing macro edges, or between a macro edge and the core edge, over the span
               where the two faces overlap; macros are cut out and the union is written as disjoint rectangles.
               Disjoint, because global placement blocks each partial blockage's share of sites on its own
               (third_party/OpenROAD-676f8451/src/gpl/src/placerBase.cpp:1151-1182), so overlapping caps would block
               more than either one.  ORFS already blocks a band of max(halo, channel / 2) microns around every
               macro for global placement (third_party/ORFS-2024-12/flow/scripts/macro_place_util.tcl:22-24, :70-71;
               scripts/placement_blockages.tcl:1-44: soft blockages with no density set, which is 0, so global
               placement uses none of their sites: third_party/OpenROAD-676f8451/src/odb/src/db/dbBlockage.h:84); a
               cap over that band changes nothing there.
"""

from __future__ import annotations

import numpy as np

from ..core.design import centres_abs, eff_size

PARAMS = {"channel_caps": {"max_gap": True, "max_density": True, "min_gap": False}}


def _snap(x, design):
    """Microns on the design's database grid (1 / dbu um), so that edges equal in the database compare equal here
    after the normalized-coordinate round trip."""
    dbu = float(getattr(design, "dbu", 1.0) or 1.0)
    return np.round(np.asarray(x, float) * dbu) / dbu


def macro_boxes(design, layout) -> np.ndarray:
    """(K, 4) boxes xl, yl, xh, yh in microns of the design's placed macros, on the database grid."""
    m = np.flatnonzero(np.asarray(design.is_macro, bool) & layout.placed)
    if not len(m):
        return np.zeros((0, 4))
    c, s = centres_abs(design, layout)[m], eff_size(design, layout)[m]
    return _snap(np.column_stack([c - s / 2, c + s / 2]), design)


def disjoint_union(rects, holes=(), box=None) -> list:
    """The union of ``rects`` minus ``holes``, clipped to ``box``, as disjoint rectangles: maximal runs along x on a
    grid of every edge, then equal runs of neighbouring grid rows joined.  Deterministic for a given input."""
    rects = [tuple(map(float, r)) for r in rects]
    holes = [tuple(map(float, h)) for h in holes]
    if box is not None:
        bx = tuple(map(float, box))
        rects = [(max(r[0], bx[0]), max(r[1], bx[1]), min(r[2], bx[2]), min(r[3], bx[3])) for r in rects]
    rects = [r for r in rects if r[2] > r[0] and r[3] > r[1]]
    if not rects:
        return []
    xs = np.unique([v for r in rects + holes for v in (r[0], r[2])])
    ys = np.unique([v for r in rects + holes for v in (r[1], r[3])])
    grid = np.zeros((len(ys) - 1, len(xs) - 1), bool)
    for r in rects:
        grid[np.searchsorted(ys, r[1]):np.searchsorted(ys, r[3]), np.searchsorted(xs, r[0]):np.searchsorted(xs, r[2])] = True
    for h in holes:
        i0, i1 = np.searchsorted(xs, h[0]), np.searchsorted(xs, h[2])
        j0, j1 = np.searchsorted(ys, h[1]), np.searchsorted(ys, h[3])
        grid[max(j0, 0):j1, max(i0, 0):i1] = False
    out, open_runs = [], {}                        # (i0, i1) -> row where the run started
    for j in range(grid.shape[0] + 1):
        runs = set()
        if j < grid.shape[0]:
            row, i = grid[j], 0
            while i < len(row):
                if row[i]:
                    k = i
                    while k < len(row) and row[k]:
                        k += 1
                    runs.add((i, k))
                    i = k
                else:
                    i += 1
        for run in sorted(set(open_runs) - runs):
            j0 = open_runs.pop(run)
            out.append((float(xs[run[0]]), float(ys[j0]), float(xs[run[1]]), float(ys[j])))
        for run in sorted(runs - set(open_runs)):
            open_runs[run] = j
    return sorted(out, key=lambda r: (r[1], r[0]))


def channel_rects(design, layout, max_gap: float, min_gap: float = 0.0) -> list:
    """The channels of a macro layout as disjoint rectangles (microns): see the module docstring."""
    b = macro_boxes(design, layout)
    core = tuple(map(float, _snap(design.core, design)))
    cand = []

    def gap_ok(g):
        return min_gap < g <= max_gap

    for a in range(len(b)):
        ax0, ay0, ax1, ay1 = b[a]
        for c in range(len(b)):
            if c == a:
                continue
            cx0, cy0, cx1, cy1 = b[c]
            lo, hi = max(ay0, cy0), min(ay1, cy1)          # a left of c, facing over [lo, hi] in y
            if cx0 >= ax1 and gap_ok(cx0 - ax1) and hi > lo:
                cand.append((ax1, lo, cx0, hi))
            lo, hi = max(ax0, cx0), min(ax1, cx1)          # a below c, facing over [lo, hi] in x
            if cy0 >= ay1 and gap_ok(cy0 - ay1) and hi > lo:
                cand.append((lo, ay1, hi, cy0))
        if gap_ok(ax0 - core[0]):
            cand.append((core[0], ay0, ax0, ay1))
        if gap_ok(core[2] - ax1):
            cand.append((ax1, ay0, core[2], ay1))
        if gap_ok(ay0 - core[1]):
            cand.append((ax0, core[1], ax1, ay0))
        if gap_ok(core[3] - ay1):
            cand.append((ax0, ay1, ax1, core[3]))
    return disjoint_union(cand, holes=[tuple(r) for r in b], box=core)


def channel_caps(design, layout, max_gap: float, max_density: float, min_gap: float = 0.0) -> dict:
    """Hints of the channel_caps program: {"density_caps": ((rect, max_density), ...)}."""
    return {"density_caps": tuple((r, float(max_density)) for r in channel_rects(design, layout, max_gap, min_gap))}


PROGRAMS = {"channel_caps": channel_caps}


def check(name: str, params) -> tuple:
    """A program reference in canonical form, (name, ((key, float value), ...)) sorted by key; errors name the
    problem."""
    if name not in PROGRAMS:
        raise ValueError("hint program %r is unknown (known: %s)" % (name, ", ".join(sorted(PROGRAMS))))
    params = dict(params)
    spec = PARAMS[name]
    bad = sorted(set(params) - set(spec))
    if bad:
        raise ValueError("hint program %s: unknown parameters %s" % (name, bad))
    missing = sorted(k for k, req in spec.items() if req and k not in params)
    if missing:
        raise ValueError("hint program %s: missing parameters %s" % (name, missing))
    out = tuple(sorted((k, float(v)) for k, v in params.items()))
    p = dict(out)
    if name == "channel_caps":
        if not 0.0 <= p["max_density"] <= 100.0:
            raise ValueError("channel_caps: max_density is a percentage in [0, 100], got %r" % p["max_density"])
        if not 0.0 <= p.get("min_gap", 0.0) < p["max_gap"]:
            raise ValueError("channel_caps: needs 0 <= min_gap < max_gap, got %r" % (p,))
    return name, out


def run(name: str, params, design, layout) -> dict:
    return PROGRAMS[name](design, layout, **dict(params))
