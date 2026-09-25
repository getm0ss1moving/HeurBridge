"""Certified projections (task T2.5).  P_M: macro legalizer + exact macro checker.

P_M  greedy grid legalization: movable macros, largest area first, each moved to
     the free grid slot nearest its target (a windowed "spiral" search over a
     prefix-sum occupancy map).  Greedy placement can fragment a dense core so that
     the last macros find no slot (bp_fe_top: nine 153 x 113 um RAMs, at most 15
     halo footprints in a perfect packing); only then are fallback orders tried
     (sweeps by target y and x, centre-out, and as the last resort bottom-left packing
     that ignores the targets) and the legal result with the least displacement is kept.
     The primary order's result is unchanged whenever it is legal.  Footprints are the orientation-aware macro size
     plus the halo (minimum macro-to-macro spacing), rounded up to grid cells, so
     legalized macros can never overlap.  Fixed macros are obstacles.  Orientation,
     fixed objects and non-macro objects are never changed.  The grid pitch is a
     multiple of the site width / row height, so lower-left corners stay on the
     placement grid.

check_macros  exact continuous check (the check_placement-equivalent for macros):
     inside the core, pairwise spacing >= halo (movable-movable and movable-fixed).

P_C and P_R wrap OpenROAD and live in heurbridge/eval (Track B).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from . import orient as O
from .design import Design, Layout


def _name_key(name: str) -> int:
    import hashlib
    return int.from_bytes(hashlib.blake2b(name.encode(), digest_size=8).digest(), "little") >> 1


@dataclass
class LegalizeReport:
    ok: bool
    moved: int = 0
    mean_disp: float = 0.0          # mean displacement, core-normalized units (area-weighted)
    max_disp: float = 0.0
    failed: list = field(default_factory=list)
    grid: tuple = ()
    check: dict = field(default_factory=dict)
    order: str = "area"                         # macro order that produced this result
    fallback_from: list = field(default_factory=list)   # failed attempts before a fallback order succeeded


def _pitch(design: Design, max_cells: int) -> tuple[float, float]:
    w, h = design.core_wh
    sw = (design.site[0] if design.site and design.site[0] else None) or w / max_cells
    sh = (design.site[1] if design.site and design.site[1] else None) or h / max_cells
    kx = max(1, math.ceil((w / max_cells) / sw))
    ky = max(1, math.ceil((h / max_cells) / sh))
    return kx * sw, ky * sh


def _window_free(occ_ps: np.ndarray, fw: int, fh: int) -> np.ndarray:
    """free[i, j] = True if cells [i, i+fw) x [j, j+fh) are all empty. occ_ps: 2D prefix sum with zero border."""
    s = occ_ps[fw:, fh:] - occ_ps[:-fw, fh:] - occ_ps[fw:, :-fh] + occ_ps[:-fw, :-fh]
    return s == 0


def _nearest_free(free: np.ndarray, tx: float, ty: float, px: float, py: float):
    """Nearest True cell of ``free`` to the continuous cell coordinate (tx, ty); windowed, exact."""
    nfx, nfy = free.shape
    ci, cj = int(np.clip(round(tx), 0, nfx - 1)), int(np.clip(round(ty), 0, nfy - 1))
    r = 4
    while True:
        a0, a1 = max(0, ci - r), min(nfx, ci + r + 1)
        b0, b1 = max(0, cj - r), min(nfy, cj + r + 1)
        whole = a0 == 0 and b0 == 0 and a1 == nfx and b1 == nfy
        sub = free[a0:a1, b0:b1]
        if sub.any():
            ii, jj = np.nonzero(sub)
            ii, jj = ii + a0, jj + b0
            d2 = ((ii - tx) * px) ** 2 + ((jj - ty) * py) ** 2
            k = int(np.argmin(d2))
            # any cell outside the window is at least this far from the target
            reach = min((tx - (a0 - 1)) * px if a0 > 0 else np.inf, (a1 - tx) * px if a1 < nfx else np.inf,
                        (ty - (b0 - 1)) * py if b0 > 0 else np.inf, (b1 - ty) * py if b1 < nfy else np.inf)
            if whole or d2[k] <= reach ** 2:
                return int(ii[k]), int(jj[k])
        if whole:
            return None
        r *= 2


FALLBACK_ORDERS = ("y", "x", "centre_out", "bottom_left")


def legalize_macros(design: Design, layout: Layout, halo: float = 0.0, max_cells: int = 512,
                    scope: np.ndarray | None = None, fallback: bool = True) -> tuple[Layout, LegalizeReport]:
    """P_M.  Returns a new Layout (macros in ``scope`` legalized) and a report; never raises on infeasibility."""
    out, rep = _legalize(design, layout, halo, max_cells, scope, "area")
    if rep.ok or not fallback or not len(rep.failed):
        return out, rep
    tried = [rep]
    best = None
    for order in FALLBACK_ORDERS:
        o2, r2 = _legalize(design, layout, halo, max_cells, scope, order)
        tried.append(r2)
        if r2.ok and (best is None or r2.mean_disp < best[1].mean_disp - 1e-12):
            best = (o2, r2)
    if best is None:
        return out, rep                              # every order failed: report the primary attempt
    best[1].fallback_from = [{"order": t.order, "failed": t.failed} for t in tried if not t.ok]
    return best


def _legalize(design: Design, layout: Layout, halo: float, max_cells: int, scope, order_by: str):
    out = layout.copy()
    mov = design.is_macro & ~design.is_fixed
    if scope is not None:
        mov &= np.asarray(scope, bool)
    idx = np.flatnonzero(mov)
    px, py = _pitch(design, max_cells)
    W, H = design.core_wh
    nx, ny = int(math.floor(W / px + 1e-9)), int(math.floor(H / py + 1e-9))
    rep = LegalizeReport(ok=True, grid=(nx, ny, px, py), order=order_by)
    if len(idx) == 0:
        rep.check = check_macros(design, out, halo)
        return out, rep
    hx, hy = int(math.ceil(halo / 2 / px - 1e-9)), int(math.ceil(halo / 2 / py - 1e-9))   # halo in whole cells
    occ = np.zeros((nx, ny), dtype=np.int32)
    ll0 = design.core_ll
    eff = O.effective_size(design.size, layout.orient)
    for i in np.flatnonzero(design.is_macro & design.is_fixed & layout.placed):   # obstacles, conservative
        c = design.to_abs(layout.pos[i]) - ll0
        xl, yl = c - eff[i] / 2 - halo / 2
        xh, yh = c + eff[i] / 2 + halo / 2
        i0, i1 = max(0, int(math.floor(xl / px))), min(nx, int(math.ceil(xh / px)))
        j0, j1 = max(0, int(math.floor(yl / py))), min(ny, int(math.ceil(yh / py)))
        if i1 > i0 and j1 > j0:
            occ[i0:i1, j0:j1] = 1
    # ties broken by a label-free key (object name) so that relabelling permutes the output
    keys = np.array([_name_key(design.names[i]) for i in idx], dtype=np.int64)
    target = design.to_abs(layout.pos) - ll0
    target = np.where(np.isfinite(target), target, np.array([W, H]) / 2)
    ll_t = target[idx] - eff[idx] / 2                                # target lower-left corners
    if order_by == "area":                                           # largest first
        order = idx[np.lexsort((keys, -design.area[idx]))]
    elif order_by == "y":                                            # bottom-up sweep (Tetris-like)
        order = idx[np.lexsort((keys, ll_t[:, 0], ll_t[:, 1]))]
    elif order_by == "x":                                            # left-to-right sweep
        order = idx[np.lexsort((keys, ll_t[:, 1], ll_t[:, 0]))]
    elif order_by == "centre_out":                                   # macros nearest the core centre first
        r2 = ((target[idx] - np.array([W, H]) / 2) ** 2).sum(1)
        order = idx[np.lexsort((keys, r2))]
    elif order_by == "bottom_left":      # last resort: packing, targets only order the macros (largest first)
        order = idx[np.lexsort((keys, ll_t[:, 0], ll_t[:, 1], -design.area[idx]))]
    else:
        raise ValueError("unknown order %r" % order_by)
    disp = np.full(design.n_objects, np.nan)
    for i in order:
        mw = int(math.ceil(eff[i, 0] / px - 1e-9))
        mh = int(math.ceil(eff[i, 1] / py - 1e-9))
        fw, fh = max(1, mw + 2 * hx), max(1, mh + 2 * hy)
        if fw > nx or fh > ny:
            rep.failed.append(int(i))
            continue
        ps = np.zeros((nx + 1, ny + 1), dtype=np.int64)
        ps[1:, 1:] = occ.cumsum(0).cumsum(1)
        free = _window_free(ps, fw, fh)          # lower-left cell of the footprint (incl. halo cells)
        tx = (target[i, 0] - eff[i, 0] / 2) / px - hx
        ty = (target[i, 1] - eff[i, 1] / 2) / py - hy
        if order_by == "bottom_left":                                # lowest row, then leftmost free slot
            ii, jj = np.nonzero(free)
            best = (int(ii[np.lexsort((ii, jj))[0]]), int(jj[np.lexsort((ii, jj))[0]])) if len(ii) else None
        else:
            best = _nearest_free(free, tx, ty, px, py)
        if best is None:
            rep.failed.append(int(i))
            continue
        bi, bj = best
        occ[bi:bi + fw, bj:bj + fh] = 1
        new_c = np.array([(bi + hx) * px + eff[i, 0] / 2, (bj + hy) * py + eff[i, 1] / 2])
        new_n = new_c / np.array([W, H])
        if layout.placed[i]:
            disp[i] = float(np.linalg.norm(new_n - layout.pos[i]))
        out.pos[i] = new_n
    ok_moved = idx[np.isfinite(disp[idx])]
    a = design.area[ok_moved]
    rep.moved = int((disp[ok_moved] > 1e-12).sum())
    rep.mean_disp = float((disp[ok_moved] * a).sum() / a.sum()) if len(ok_moved) and a.sum() > 0 else 0.0
    rep.max_disp = float(disp[ok_moved].max()) if len(ok_moved) else 0.0
    rep.check = check_macros(design, out, halo)
    rep.ok = (not rep.failed) and rep.check["ok"]
    return out, rep


def check_macros(design: Design, layout: Layout, halo: float = 0.0, tol: float = 1e-6) -> dict:
    """Exact macro legality: inside the core and pairwise spacing >= halo (tolerance in source units)."""
    mov = np.flatnonzero(design.is_macro & ~design.is_fixed)
    fix = np.flatnonzero(design.is_macro & design.is_fixed)
    eff = O.effective_size(design.size, layout.orient)
    c = design.to_abs(layout.pos) - design.core_ll
    res = {"ok": True, "unplaced": [], "outside": [], "overlaps": []}
    if len(mov) == 0:
        return res
    un = mov[~np.isfinite(c[mov]).all(1)]
    res["unplaced"] = un.tolist()
    m = mov[np.isfinite(c[mov]).all(1)]
    lo, hi = c[m] - eff[m] / 2, c[m] + eff[m] / 2
    W, H = design.core_wh
    out = (lo[:, 0] < -tol) | (lo[:, 1] < -tol) | (hi[:, 0] > W + tol) | (hi[:, 1] > H + tol)
    res["outside"] = m[out].tolist()
    allm = np.r_[m, fix[np.isfinite(c[fix]).all(1)]] if len(fix) else m
    clo, chi = c[allm] - eff[allm] / 2, c[allm] + eff[allm] / 2
    nm = len(m)
    for a in range(nm):
        gx = np.maximum(clo[a + 1:, 0] - chi[a, 0], clo[a, 0] - chi[a + 1:, 0])
        gy = np.maximum(clo[a + 1:, 1] - chi[a, 1], clo[a, 1] - chi[a + 1:, 1])
        bad = np.flatnonzero(np.maximum(gx, gy) < halo - tol)
        for b in bad[:20]:
            res["overlaps"].append((int(allm[a]), int(allm[a + 1 + b])))
    res["ok"] = not (res["unplaced"] or res["outside"] or res["overlaps"])
    return res
