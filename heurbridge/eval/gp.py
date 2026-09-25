"""HB-GP: analytical standard-cell placement with macros fixed (Track-A f1 stand-in, P_C for bookshelf).

This is a compact ePlace-style placer, used where DREAMPlace is not available (development on the Mac,
or if the DREAMPlace build fails on the server).  It is NOT DREAMPlace; results are labelled "hbgp".

  init      quadratic placement (clique/star model, IOs and macros fixed), sparse CG
  objective WA wirelength (gamma annealed with overflow, ePlace schedule) + lambda * electrostatic energy
  density   bin density of movable cells + fixed macros; potential from the Neumann Poisson equation,
            solved exactly with cosine/sine basis matrices; force on a cell = charge * field at its centre
  optimizer Nesterov-free Adam on cell centres, lambda *= mu per iteration until overflow < stop
  legalize  Tetris row legalization into free row segments (fixed macros cut rows), cells ordered by x
Outputs a Layout (cells placed, macros untouched) and metrics {hpwl_gp, hpwl_lg, overflow, iters, ...}.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
import torch

from ..core import orient as O
from ..core.design import Design, Layout
from .f0 import F0Config, F0Context


@dataclass
class GPConfig:
    iters: int = 2000
    target_density: float = 0.9
    overflow_stop: float = 0.07
    lr: float = 0.5                  # initial step, in bin widths
    lam_mu: float = 1.05
    mu_max: float = 1.05
    bins: int | None = None          # bins per side (default: ~sqrt(#cells), power-of-two clipped to [32, 512])
    legalize: bool = True
    seed: int = 0
    device: str = "cpu"
    log_every: int = 0


def _basis(n: int, device, dtype):
    k = torch.arange(n, device=device, dtype=dtype)
    i = torch.arange(n, device=device, dtype=dtype) + 0.5
    w = math.pi * k / n
    C = torch.cos(w[:, None] * i[None, :])          # (freq, pos)
    S = torch.sin(w[:, None] * i[None, :])
    return w, C, S


class Poisson:
    """Neumann Poisson solver on an nx x ny grid (bin units): returns potential and field (Ex, Ey)."""

    def __init__(self, nx, ny, device, dtype):
        self.wx, self.Cx, self.Sx = _basis(nx, device, dtype)
        self.wy, self.Cy, self.Sy = _basis(ny, device, dtype)
        den = self.wx[:, None] ** 2 + self.wy[None, :] ** 2
        den[0, 0] = 1.0
        self.inv = 1.0 / den
        self.inv[0, 0] = 0.0
        self.nx, self.ny = nx, ny

    def solve(self, rho):
        a = (self.Cx @ rho @ self.Cy.T) * (4.0 / (self.nx * self.ny))
        a[0, :] *= 0.5
        a[:, 0] *= 0.5
        b = a * self.inv
        psi = self.Cx.T @ b @ self.Cy
        ex = self.Sx.T @ (b * self.wx[:, None]) @ self.Cy
        ey = self.Cx.T @ (b * self.wy[None, :]) @ self.Sy
        return psi, ex, ey


def quadratic_init(design: Design, layout: Layout, movable: np.ndarray, iters: int = 200) -> np.ndarray:
    """Clique-model quadratic placement of ``movable`` objects with everything else fixed (absolute coords)."""
    d = design
    pos = d.to_abs(layout.pos)
    n = d.n_objects
    mv_idx = np.flatnonzero(movable)
    col = -np.ones(n, dtype=np.int64)
    col[mv_idx] = np.arange(len(mv_idx))
    deg = d.degrees()
    objs = d.pin_obj[d.pin_idx]
    net_of = d.net_of_pin()
    rows, cols, vals = [], [], []
    bx, by = np.zeros(len(mv_idx)), np.zeros(len(mv_idx))
    diag = np.zeros(len(mv_idx))
    fixed_ok = ~movable & np.isfinite(pos).all(1)
    # star/clique hybrid: nets up to 16 pins as cliques, larger nets through their fixed-or-mean anchor
    starts = d.net_ptr
    for k in range(d.n_nets):
        dk = deg[k]
        if dk < 2:
            continue
        o = objs[starts[k]:starts[k + 1]]
        w = d.net_weight[k] / (dk - 1)
        if dk > 16:
            w = d.net_weight[k] * 2.0 / dk
        m = col[o]
        mv = m[m >= 0]
        fx = o[(m < 0) & fixed_ok[o]]
        if dk <= 16:
            if len(mv) >= 2:
                a, b = np.meshgrid(mv, mv)
                sel = a != b
                rows.append(a[sel]); cols.append(b[sel]); vals.append(np.full(sel.sum(), -w))
            diag_add = w * (len(mv) - 1 + len(fx))
            np.add.at(diag, mv, diag_add)
            if len(fx):
                np.add.at(bx, mv, w * pos[fx, 0].sum())
                np.add.at(by, mv, w * pos[fx, 1].sum())
        else:
            np.add.at(diag, mv, w)
            if len(fx):
                np.add.at(bx, mv, w * pos[fx, 0].mean())
                np.add.at(by, mv, w * pos[fx, 1].mean())
            else:
                c = d.core_ll + d.core_wh / 2
                np.add.at(bx, mv, w * c[0])
                np.add.at(by, mv, w * c[1])
    eps = 1e-6 * (diag.mean() if len(diag) else 1.0)
    c = d.core_ll + d.core_wh / 2
    diag += eps
    bx += eps * c[0]
    by += eps * c[1]
    A = sp.coo_matrix((np.concatenate(vals) if vals else np.zeros(0),
                       (np.concatenate(rows) if rows else np.zeros(0, int), np.concatenate(cols) if cols else np.zeros(0, int))),
                      shape=(len(mv_idx), len(mv_idx))).tocsr()
    A = A + sp.diags(diag)
    M = sp.diags(1.0 / diag)
    x0 = np.where(np.isfinite(pos[mv_idx, 0]), pos[mv_idx, 0], c[0])
    y0 = np.where(np.isfinite(pos[mv_idx, 1]), pos[mv_idx, 1], c[1])
    x, _ = spla.cg(A, bx, x0=x0, M=M, maxiter=iters, rtol=1e-6)
    y, _ = spla.cg(A, by, x0=y0, M=M, maxiter=iters, rtol=1e-6)
    out = pos.copy()
    out[mv_idx, 0], out[mv_idx, 1] = x, y
    return out


def _free_segments(design: Design, layout: Layout):
    """Row segments not covered by fixed/placed macros: list of (y, height, x_start, x_end)."""
    d = design
    eff = O.effective_size(d.size, layout.orient)
    mac = np.flatnonzero(d.is_macro & layout.placed)
    c = d.to_abs(layout.pos[mac])
    lo, hi = c - eff[mac] / 2, c + eff[mac] / 2
    segs = []
    for x, y, w, h in d.rows:
        cuts = [(lx, hx) for (lx, ly), (hx, hy) in zip(lo, hi) if ly < y + h - 1e-9 and hy > y + 1e-9 and hx > x and lx < x + w]
        cuts.sort()
        cur = x
        for lx, hx in cuts:
            if lx > cur:
                segs.append((y, h, cur, min(lx, x + w)))
            cur = max(cur, hx)
        if cur < x + w:
            segs.append((y, h, cur, x + w))
    return segs


def tetris_legalize(design: Design, layout: Layout, cells: np.ndarray, site_w: float, search_rows: int = 6):
    """Hill's Tetris legalization of ``cells`` (object indices) into free row segments.  Returns (layout, n_failed)."""
    d = design
    out = layout.copy()
    segs = _free_segments(design, layout)
    if not segs:
        return out, len(cells)
    seg_y = np.array([s[0] for s in segs])
    seg_h = np.array([s[1] for s in segs])
    seg_x0 = np.array([s[2] for s in segs])
    seg_x1 = np.array([s[3] for s in segs])
    frontier = seg_x0.copy()
    rows_y = np.unique(seg_y)
    by_row = {y: np.flatnonzero(seg_y == y) for y in rows_y}
    pos = d.to_abs(layout.pos)
    w = d.size[cells, 0]
    ll = pos[cells] - d.size[cells] / 2
    order = np.argsort(ll[:, 0], kind="stable")
    failed = 0
    row_h = float(np.median(seg_h))
    for t in order:
        i = cells[t]
        want_x, want_y = ll[t]
        r0 = int(np.clip(np.searchsorted(rows_y, want_y), 0, len(rows_y) - 1))
        best = None
        for span in (search_rows, 4 * search_rows, len(rows_y)):
            lo_r, hi_r = max(0, r0 - span), min(len(rows_y), r0 + span + 1)
            for ry in rows_y[lo_r:hi_r]:
                dy = abs(ry - want_y)
                if best is not None and dy >= best[0]:
                    continue
                for s in by_row[ry]:
                    x = max(frontier[s], want_x)
                    x = seg_x0[s] + math.ceil((x - seg_x0[s]) / site_w - 1e-9) * site_w
                    if x + w[t] > seg_x1[s] + 1e-9:
                        continue
                    cost = abs(x - want_x) + dy
                    if best is None or cost < best[0]:
                        best = (cost, s, x)
            if best is not None:
                break
        if best is None:
            failed += 1
            continue
        _, s, x = best
        frontier[s] = x + w[t]
        c = np.array([x + w[t] / 2, seg_y[s] + d.size[i, 1] / 2])
        out.pos[i] = d.to_norm(c)
    return out, failed


def place(design: Design, layout: Layout, cfg: GPConfig | None = None, f0cfg: F0Config | None = None,
          log=print) -> tuple[Layout, dict]:
    """Place movable standard cells with macros (and all fixed objects) held at ``layout``."""
    cfg = cfg or GPConfig()
    t0 = time.time()
    d = design
    dev, dt = torch.device(cfg.device), torch.float32
    cells = np.flatnonzero(~d.is_macro & ~d.is_io & ~d.is_fixed)
    info = {"method": "hbgp", "n_cells": int(len(cells))}
    if len(cells) == 0:
        return layout.copy(), info
    init = quadratic_init(d, layout, np.isin(np.arange(d.n_objects), cells))
    lay = layout.copy()
    lay.pos = d.to_norm(init)
    ctx = F0Context(d, lay.orient, cfg=f0cfg, device=dev)
    W, H = float(d.core_wh[0]), float(d.core_wh[1])
    nb = cfg.bins or int(np.clip(2 ** round(math.log2(max(32.0, math.sqrt(len(cells))))), 32, 512))
    bw, bh = W / nb, H / nb
    pois = Poisson(nb, nb, dev, dt)
    mov = torch.zeros(d.n_objects, dtype=torch.bool, device=dev)
    mov[torch.as_tensor(cells, device=dev)] = True
    area = torch.as_tensor(d.area, dtype=dt, device=dev)
    pos = torch.as_tensor(lay.pos, dtype=dt, device=dev).clone()
    rng = torch.Generator().manual_seed(cfg.seed)
    pos[mov] += (torch.rand(int(mov.sum()), 2, generator=rng) - 0.5).to(dev) * torch.tensor([bw / W, bh / H], device=dev)
    pos = pos.clamp(0, 1)
    fixed_macro = torch.as_tensor(d.is_macro, device=dev)
    pa0 = ctx.to_abs(pos.unsqueeze(0))
    # fixed macro density on the GP grid (exact overlap), rectangular bins handled by separate scaling
    sel = torch.nonzero(fixed_macro).flatten()
    rho_fix = torch.zeros(nb, nb, device=dev, dtype=dt)
    if len(sel):
        c = pa0[0, sel] - ctx.core_ll
        h = ctx.eff[sel] / 2
        ex = torch.arange(nb + 1, device=dev, dtype=dt) * bw
        ey = torch.arange(nb + 1, device=dev, dtype=dt) * bh
        ox = torch.clamp(torch.minimum(c[:, 0:1] + h[:, 0:1], ex[1:]) - torch.maximum(c[:, 0:1] - h[:, 0:1], ex[:-1]), min=0)
        oy = torch.clamp(torch.minimum(c[:, 1:2] + h[:, 1:2], ey[1:]) - torch.maximum(c[:, 1:2] - h[:, 1:2], ey[:-1]), min=0)
        rho_fix = (ox.T @ oy) / (bw * bh)
    rho_fix = rho_fix.clamp(max=1.0)
    total_mov = float(area[mov].sum())
    target = cfg.target_density
    cap = torch.clamp(1.0 - rho_fix, min=0) * target
    cidx = torch.as_tensor(cells, device=dev)
    ch = torch.as_tensor(d.size[cells] / 2, dtype=dt, device=dev)
    q = area[cidx] / (bw * bh)                                   # charge in bin-area units
    npins = torch.bincount(torch.as_tensor(d.pin_obj, device=dev), minlength=d.n_objects).to(dt)[cidx]
    ex = torch.arange(nb + 1, device=dev, dtype=dt) * bw
    ey = torch.arange(nb + 1, device=dev, dtype=dt) * bh
    ctx_gamma0 = ctx.gamma

    def density(p):
        """(rho (nb,nb), overflow) of movable cells at normalized positions p (cells only)."""
        cc = ctx.to_abs(p.unsqueeze(0))[0] - ctx.core_ll
        i0 = torch.clamp(torch.floor((cc[:, 0] - ch[:, 0]) / bw).long(), 0, nb - 1)
        j0 = torch.clamp(torch.floor((cc[:, 1] - ch[:, 1]) / bh).long(), 0, nb - 1)
        rho = torch.zeros(nb * nb, device=dev, dtype=dt)
        for di in (0, 1):
            ii = torch.clamp(i0 + di, 0, nb - 1)
            oxx = torch.clamp(torch.minimum(cc[:, 0] + ch[:, 0], ex[ii + 1]) - torch.maximum(cc[:, 0] - ch[:, 0], ex[ii]), min=0)
            oxx = oxx * ((i0 + di) <= nb - 1)
            for dj in (0, 1):
                jj = torch.clamp(j0 + dj, 0, nb - 1)
                oyy = torch.clamp(torch.minimum(cc[:, 1] + ch[:, 1], ey[jj + 1]) - torch.maximum(cc[:, 1] - ch[:, 1], ey[jj]), min=0)
                oyy = oyy * ((j0 + dj) <= nb - 1)
                rho.index_add_(0, ii * nb + jj, oxx * oyy / (bw * bh))
        rho = rho.view(nb, nb)
        return rho, cc, float(torch.relu(rho - cap).sum() * bw * bh / total_mov)

    def field_at(f, cc):
        """Bilinear interpolation of a bin-centred field at absolute (core-relative) points."""
        u = torch.clamp(cc[:, 0] / bw - 0.5, 0, nb - 1)
        v = torch.clamp(cc[:, 1] / bh - 0.5, 0, nb - 1)
        i0, j0 = torch.floor(u).long().clamp(max=nb - 2), torch.floor(v).long().clamp(max=nb - 2)
        fu, fv = u - i0, v - j0
        return ((1 - fu) * (1 - fv) * f[i0, j0] + fu * (1 - fv) * f[i0 + 1, j0]
                + (1 - fu) * fv * f[i0, j0 + 1] + fu * fv * f[i0 + 1, j0 + 1])

    def grad(p_full, lam, ovf):
        p_full = p_full.detach().requires_grad_(True)
        ctx.gamma = 8.0 * bw * 10 ** ((20.0 / 9.0) * min(max(ovf, 0.0), 1.0) - 11.0 / 9.0)
        wl = ctx.hpwl_wa(p_full)[0]
        g_wl = torch.autograd.grad(wl, p_full)[0][cidx]
        with torch.no_grad():
            rho, cc, ov = density(p_full[cidx])
            _, fx, fy = pois.solve(rho + cfg.target_density * rho_fix)   # DREAMPlace: fixed charge at target density
            gd = torch.stack([-q * field_at(fx, cc) * nb, -q * field_at(fy, cc) * nb], 1)
        return g_wl, gd, float(wl), ov

    pos = pos.detach()
    lam, ovf = None, 1.0
    g_wl, gd, wl, ovf = grad(pos, 0.0, ovf)
    lam = float(g_wl.abs().sum() / (gd.abs().sum() + 1e-12))
    precond = lambda lam_: 1.0 / torch.clamp(npins + lam_ * q, min=1.0).unsqueeze(1)
    u_prev = pos[cidx].clone()
    v = pos[cidx].clone()
    g_prev = (g_wl + lam * gd) * precond(lam)
    v_prev = None
    a = 1.0
    alpha = cfg.lr * bw / W
    best_ovf, stall, prev_hpwl = ovf, 0, None
    it_done = 0
    full = pos.clone()
    for it in range(cfg.iters):
        full[cidx] = v
        g_wl, gd, wl, ovf = grad(full, lam, ovf)
        g = (g_wl + lam * gd) * precond(lam)
        if v_prev is not None:
            dg = (g - g_prev).norm()
            if dg > 0:
                alpha = float((v - v_prev).norm() / dg)
        u = (v - alpha * g).clamp(0.0, 1.0)
        a_next = (1 + math.sqrt(4 * a * a + 1)) / 2
        v_prev, g_prev = v, g
        v = (u + (a - 1) / a_next * (u - u_prev)).clamp(0.0, 1.0)
        u_prev, a = u, a_next
        with torch.no_grad():
            full[cidx] = u
            hp = float(ctx.hpwl_exact(full)[0])
        if prev_hpwl is not None and hp is not None:
            dh = (hp - prev_hpwl) / max(prev_hpwl, 1e-12)
            mu = min(cfg.mu_max, max(0.75, cfg.mu_max ** (1.0 - dh / 0.0035)))     # ePlace: dHPWL_ref ~ 0.35% of HPWL
        else:
            mu = 1.1
        lam *= mu
        prev_hpwl = hp
        it_done = it + 1
        if cfg.log_every and it % cfg.log_every == 0:
            log("gp it=%d hpwl=%.4g wa=%.4g ovf=%.3f lam=%.3g alpha=%.3g" % (it, hp or -1, wl, ovf, lam, alpha))
        if ovf < best_ovf - 0.005:
            best_ovf, stall = ovf, 0
        else:
            stall += 1
        if (ovf < cfg.overflow_stop and it > 30) or stall > 200:
            break
    pos = full.detach()
    pos[cidx] = u_prev
    ctx.gamma = ctx_gamma0
    lay.pos = pos.detach().cpu().double().numpy()
    lay.pos[~mov.cpu().numpy()] = layout.pos[~mov.cpu().numpy()]
    info.update({"iters": it_done, "overflow": ovf, "hpwl_gp": float(ctx.hpwl_exact(torch.as_tensor(lay.pos, dtype=dt, device=dev))[0]),
                 "bins": nb, "gp_s": round(time.time() - t0, 2)})
    if cfg.legalize:
        t1 = time.time()
        site_w = d.site[0] if d.site and d.site[0] else 1.0
        lay, failed = tetris_legalize(d, lay, cells, site_w)
        info.update({"lg_failed": int(failed), "lg_s": round(time.time() - t1, 2),
                     "hpwl_lg": float(ctx.hpwl_exact(torch.as_tensor(lay.pos, dtype=dt, device=dev))[0])})
    info["runtime_s"] = round(time.time() - t0, 2)
    return lay, info
