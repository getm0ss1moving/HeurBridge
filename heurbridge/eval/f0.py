"""Fidelity-0 metrics in PyTorch, batched over layouts of one design (task T1.3).

All metrics take normalized centres ``pos`` of shape (B, N, 2) (or (N, 2)) and
report absolute source units (microns for DEF designs).  Differentiable (D):

  hpwl_exact        exact weighted HPWL                                   -
  hpwl_wa           weighted-average smooth HPWL, gamma = 0.5% die width  D
  hpwl_lse          log-sum-exp smooth HPWL                               D
  macro_overlap     pairwise macro overlap area (+ fixed obstacles)       D
  outside_area      macro area outside the core                           D
  density_overflow  DREAMPlace-style cell density overflow, bins sized
                    sqrt(mean movable cell area) x 8                      D
  rudy              RUDY H/V demand map vs capacity; total/peak overflow  D (demand)
  channel_shortage  RUDY overflow in free GCells lying in channels
                    between macros (macro-covered on both sides within
                    2 GCells, horizontally or vertically)                 D (mask not)

Orientation is fixed per call (orientation is never transported).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import torch

from ..core import orient as O
from ..core.design import Design


def _t(x, device, dtype=torch.float32):
    return torch.as_tensor(np.asarray(x), device=device, dtype=dtype)


@dataclass
class F0Config:
    gamma_frac: float = 0.005        # WA/LSE smoothing: fraction of die width
    bin_factor: float = 8.0          # density bin = sqrt(mean movable cell area) * bin_factor
    target_density: float = 1.0
    gcell: float | None = None       # GCell size (source units); default from design.gcell_grid or core/64
    tracks_per_unit_h: float | None = None   # routing capacity per unit length (sum over H layers of 1/pitch)
    tracks_per_unit_v: float | None = None
    macro_block_frac: float = 0.65   # share of routing capacity blocked over macros (pilot MACRO_CAP 0.35)
    channel_reach: int = 2           # GCells on each side for the channel test


class F0Context:
    """Per-design constant tensors; build once, evaluate many layouts."""

    def __init__(self, design: Design, orient: np.ndarray | None = None, cfg: F0Config | None = None,
                 device: str | torch.device = "cpu", dtype=torch.float32):
        self.design, self.cfg, self.device, self.dtype = design, cfg or F0Config(), torch.device(device), dtype
        d, dev = design, self.device
        self.N, self.P = d.n_objects, d.n_pins
        self.core_ll = _t(d.core_ll, dev, dtype)
        self.core_wh = _t(d.core_wh, dev, dtype)
        die_w = d.die[2] - d.die[0] if d.die[2] > d.die[0] else d.core_wh[0]
        self.gamma = float(self.cfg.gamma_frac * die_w)
        self.set_orient(np.zeros(self.N, dtype=np.int8) if orient is None else orient)
        # pins in net order
        self.pin_obj = torch.as_tensor(d.pin_obj[d.pin_idx], device=dev, dtype=torch.long)
        self.pin_off0 = _t(d.pin_off[d.pin_idx], dev, dtype)
        self.pin_net = torch.as_tensor(d.net_of_pin(), device=dev, dtype=torch.long)
        deg = d.degrees()
        self.M = d.n_nets
        self.net_w = _t(d.net_weight * (deg >= 2), dev, dtype)
        # object classes
        self.is_macro = torch.as_tensor(d.is_macro, device=dev)
        self.movable = torch.as_tensor(~d.is_fixed, device=dev)
        self.mov_macro = self.is_macro & self.movable
        self.fix_macro = self.is_macro & ~self.movable
        cell = ~d.is_macro & ~d.is_io & ~d.is_fixed
        self.mov_cell = torch.as_tensor(cell, device=dev)
        # density bins
        ca = d.area[cell]
        b = float(math.sqrt(ca.mean()) * self.cfg.bin_factor) if len(ca) and ca.mean() > 0 else float(d.core_wh.min() / 64)
        self.bin = b
        self.nbx = max(1, int(math.ceil(d.core_wh[0] / b)))
        self.nby = max(1, int(math.ceil(d.core_wh[1] / b)))
        # GCells
        g = self.cfg.gcell
        if g is None and d.gcell_grid and d.gcell_grid.get("X"):
            g = d.gcell_grid["X"][0][2] / d.gcell_grid.get("dbu", 1.0)
        if g is None:
            g = float(d.core_wh.max() / 64)
        self.g = float(g)
        self.ngx = max(1, int(math.ceil(d.core_wh[0] / self.g)))
        self.ngy = max(1, int(math.ceil(d.core_wh[1] / self.g)))
        th, tv = self.cfg.tracks_per_unit_h, self.cfg.tracks_per_unit_v
        if th is None or tv is None:
            lay = (d.gcell_grid or {}).get("layers") or d.source.get("layers") or []
            h = sum(1.0 / l["pitch"] for l in lay if l.get("dir") == "H" and l.get("pitch"))
            v = sum(1.0 / l["pitch"] for l in lay if l.get("dir") == "V" and l.get("pitch"))
            if h <= 0 or v <= 0:   # no tech info: 2 layers per direction at a pitch of 1/50 GCell
                h = v = 2.0 * 50.0 / self.g
            th = th if th is not None else h
            tv = tv if tv is not None else v
        self.cap_h_unit, self.cap_v_unit = float(th), float(tv)

    def set_orient(self, orient: np.ndarray):
        o = np.asarray(orient, dtype=np.int64)
        self.orient = o
        self.mats = _t(O.MATS[o], self.device, self.dtype)                       # (N,2,2)
        self.eff = _t(O.effective_size(self.design.size, o), self.device, self.dtype)  # (N,2)

    # ------------------------------------------------------------------ helpers
    def to_abs(self, pos: torch.Tensor) -> torch.Tensor:
        return pos * self.core_wh + self.core_ll

    def pins(self, pos_abs: torch.Tensor) -> torch.Tensor:
        """(B,N,2) absolute centres -> (B,P,2) pin positions in net order."""
        off = torch.einsum("pij,pj->pi", self.mats[self.pin_obj], self.pin_off0)
        return pos_abs[:, self.pin_obj] + off

    def _net_reduce(self, v: torch.Tensor, reduce: str) -> torch.Tensor:
        B = v.shape[0]
        fill = -torch.inf if reduce == "amax" else torch.inf
        out = torch.full((B, self.M, 2), fill, device=v.device, dtype=v.dtype)
        idx = self.pin_net.view(1, -1, 1).expand(B, -1, 2)
        return out.scatter_reduce(1, idx, v, reduce=reduce, include_self=True)

    @staticmethod
    def _batch(pos):
        return pos.unsqueeze(0) if pos.dim() == 2 else pos

    # ------------------------------------------------------------------ wirelength
    def net_bbox(self, pos: torch.Tensor):
        pp = self.pins(self.to_abs(self._batch(pos)))
        hi, lo = self._net_reduce(pp, "amax"), self._net_reduce(pp, "amin")
        valid = self.net_w > 0
        hi = torch.where(valid.view(1, -1, 1), hi, torch.zeros_like(hi))
        lo = torch.where(valid.view(1, -1, 1), lo, torch.zeros_like(lo))
        return lo, hi

    def hpwl_exact(self, pos: torch.Tensor) -> torch.Tensor:
        lo, hi = self.net_bbox(pos)
        return ((hi - lo).sum(-1) * self.net_w).sum(-1)

    def _smooth(self, pos: torch.Tensor, kind: str) -> torch.Tensor:
        pp = self.pins(self.to_abs(self._batch(pos)))
        g = self.gamma
        B = pp.shape[0]
        idx = self.pin_net.view(1, -1, 1).expand(B, -1, 2)
        total = 0.0
        for sgn in (1.0, -1.0):
            z = sgn * pp / g
            zmax = self._net_reduce(z.detach(), "amax")
            zmax = torch.where(torch.isfinite(zmax), zmax, torch.zeros_like(zmax))
            e = torch.exp(z - zmax.gather(1, idx))
            s = torch.zeros(B, self.M, 2, device=pp.device, dtype=pp.dtype).scatter_add(1, idx, e)
            if kind == "lse":
                term = g * (torch.log(s.clamp_min(1e-30)) + zmax)
            else:
                xs = torch.zeros(B, self.M, 2, device=pp.device, dtype=pp.dtype).scatter_add(1, idx, pp * e)
                term = sgn * xs / s.clamp_min(1e-30)
            total = total + term
        return (total.sum(-1) * self.net_w).sum(-1)

    def hpwl_wa(self, pos):
        return self._smooth(pos, "wa")

    def hpwl_lse(self, pos):
        return self._smooth(pos, "lse")

    # ------------------------------------------------------------------ macros
    def macro_overlap(self, pos: torch.Tensor, halo: float = 0.0, chunk: int = 1024) -> torch.Tensor:
        """Sum of pairwise overlap areas: movable-movable (i<j) + movable-fixed macros."""
        pa = self.to_abs(self._batch(pos))
        mi = torch.nonzero(self.mov_macro).flatten()
        fi = torch.nonzero(self.fix_macro).flatten()
        B = pa.shape[0]
        if len(mi) == 0:
            return torch.zeros(B, device=pa.device, dtype=pa.dtype)
        c, h = pa[:, mi], self.eff[mi] / 2 + halo / 2

        def ov(c1, h1, c2, h2):
            dx = (h1[:, 0].view(1, -1, 1) + h2[:, 0].view(1, 1, -1)) - (c1[..., 0].unsqueeze(2) - c2[..., 0].unsqueeze(1)).abs()
            dy = (h1[:, 1].view(1, -1, 1) + h2[:, 1].view(1, 1, -1)) - (c1[..., 1].unsqueeze(2) - c2[..., 1].unsqueeze(1)).abs()
            dx = torch.minimum(dx, torch.minimum(2 * h1[:, 0].view(1, -1, 1), 2 * h2[:, 0].view(1, 1, -1)))
            dy = torch.minimum(dy, torch.minimum(2 * h1[:, 1].view(1, -1, 1), 2 * h2[:, 1].view(1, 1, -1)))
            return torch.relu(dx) * torch.relu(dy)

        total = torch.zeros(B, device=pa.device, dtype=pa.dtype)
        n = len(mi)
        for s in range(0, n, chunk):
            a = ov(c[:, s:s + chunk], h[s:s + chunk], c, h)
            rows = torch.arange(s, min(n, s + chunk), device=pa.device).view(-1, 1)
            cols = torch.arange(n, device=pa.device).view(1, -1)
            total = total + (a * (cols > rows).to(a.dtype)).sum((1, 2))
        if len(fi):
            cf, hf = pa[:, fi], self.eff[fi] / 2
            for s in range(0, n, chunk):
                total = total + ov(c[:, s:s + chunk], h[s:s + chunk], cf, hf).sum((1, 2))
        return total

    def outside_area(self, pos: torch.Tensor) -> torch.Tensor:
        pa = self.to_abs(self._batch(pos))
        mi = torch.nonzero(self.mov_macro).flatten()
        if len(mi) == 0:
            return torch.zeros(pa.shape[0], device=pa.device, dtype=pa.dtype)
        c, h = pa[:, mi], self.eff[mi] / 2
        lo, hi = self.core_ll, self.core_ll + self.core_wh
        w_in = torch.clamp(torch.minimum(c[..., 0] + h[:, 0], hi[0]) - torch.maximum(c[..., 0] - h[:, 0], lo[0]), min=0)
        h_in = torch.clamp(torch.minimum(c[..., 1] + h[:, 1], hi[1]) - torch.maximum(c[..., 1] - h[:, 1], lo[1]), min=0)
        return (4 * h[:, 0] * h[:, 1] - w_in * h_in).sum(-1)

    # ------------------------------------------------------------------ rasterization
    def _raster(self, pa: torch.Tensor, sel: torch.Tensor, cell: float, nx: int, ny: int,
                weight: torch.Tensor | None = None) -> torch.Tensor:
        """Exact area of the selected rectangles in each grid cell -> (B, nx, ny).  Differentiable."""
        B = pa.shape[0]
        idx = torch.nonzero(sel).flatten()
        if len(idx) == 0:
            return torch.zeros(B, nx, ny, device=pa.device, dtype=pa.dtype)
        c = pa[:, idx] - self.core_ll
        h = self.eff[idx] / 2
        xl, xh = c[..., 0] - h[:, 0], c[..., 0] + h[:, 0]
        yl, yh = c[..., 1] - h[:, 1], c[..., 1] + h[:, 1]
        ex = torch.arange(nx + 1, device=pa.device, dtype=pa.dtype) * cell
        ey = torch.arange(ny + 1, device=pa.device, dtype=pa.dtype) * cell
        w = torch.ones(len(idx), device=pa.device, dtype=pa.dtype) if weight is None else weight
        small = (2 * h[:, 0] <= cell) & (2 * h[:, 1] <= cell)
        out = torch.zeros(B, nx, ny, device=pa.device, dtype=pa.dtype)
        if small.any():   # each small rectangle touches at most 2x2 cells
            s = torch.nonzero(small).flatten()
            i0 = torch.clamp(torch.floor(xl[:, s] / cell).long(), 0, nx - 1)
            j0 = torch.clamp(torch.floor(yl[:, s] / cell).long(), 0, ny - 1)
            for di in (0, 1):
                ii = torch.clamp(i0 + di, 0, nx - 1)
                ox = torch.clamp(torch.minimum(xh[:, s], ex[ii + 1]) - torch.maximum(xl[:, s], ex[ii]), min=0)
                ox = ox * ((i0 + di) <= nx - 1).to(ox.dtype)
                for dj in (0, 1):
                    jj = torch.clamp(j0 + dj, 0, ny - 1)
                    oy = torch.clamp(torch.minimum(yh[:, s], ey[jj + 1]) - torch.maximum(yl[:, s], ey[jj]), min=0)
                    oy = oy * ((j0 + dj) <= ny - 1).to(oy.dtype)
                    flat = (ii * ny + jj)
                    out = out.view(B, -1).scatter_add(1, flat, ox * oy * w[s]).view(B, nx, ny)
        if (~small).any():
            L = torch.nonzero(~small).flatten()
            ox = torch.clamp(torch.minimum(xh[:, L, None], ex[1:]) - torch.maximum(xl[:, L, None], ex[:-1]), min=0)
            oy = torch.clamp(torch.minimum(yh[:, L, None], ey[1:]) - torch.maximum(yl[:, L, None], ey[:-1]), min=0)
            out = out + torch.einsum("bki,bkj,k->bij", ox, oy, w[L])
        return out

    # ------------------------------------------------------------------ density
    def density_overflow(self, pos: torch.Tensor) -> torch.Tensor:
        pa = self.to_abs(self._batch(pos))
        b = self.bin
        mov = self._raster(pa, self.mov_cell, b, self.nbx, self.nby)
        fixed = self._raster(pa, self.is_macro, b, self.nbx, self.nby).detach()   # macros act as blockage
        cap = self.cfg.target_density * torch.clamp(b * b - fixed, min=0)
        total = mov.sum((1, 2)).clamp_min(1e-12)
        return torch.relu(mov - cap).sum((1, 2)) / total

    # ------------------------------------------------------------------ routing
    def rudy(self, pos: torch.Tensor):
        """Returns dict of (B,) overflow scalars and (B,ngx,ngy) demand/capacity maps."""
        pa = self.to_abs(self._batch(pos))
        lo, hi = self.net_bbox(pos)
        g, nx, ny = self.g, self.ngx, self.ngy
        bw = (hi[..., 0] - lo[..., 0]).clamp_min(g)
        bh = (hi[..., 1] - lo[..., 1]).clamp_min(g)
        cx, cy = (lo[..., 0] + hi[..., 0]) / 2 - self.core_ll[0], (lo[..., 1] + hi[..., 1]) / 2 - self.core_ll[1]
        ex = torch.arange(nx + 1, device=pa.device, dtype=pa.dtype) * g
        ey = torch.arange(ny + 1, device=pa.device, dtype=pa.dtype) * g
        ox = torch.clamp(torch.minimum(cx.unsqueeze(-1) + bw.unsqueeze(-1) / 2, ex[1:]) - torch.maximum(cx.unsqueeze(-1) - bw.unsqueeze(-1) / 2, ex[:-1]), min=0)
        oy = torch.clamp(torch.minimum(cy.unsqueeze(-1) + bh.unsqueeze(-1) / 2, ey[1:]) - torch.maximum(cy.unsqueeze(-1) - bh.unsqueeze(-1) / 2, ey[:-1]), min=0)
        w = self.net_w.view(1, -1)
        dem_h = torch.einsum("bki,bkj,bk->bij", ox, oy, w / bh)    # horizontal wire length per GCell
        dem_v = torch.einsum("bki,bkj,bk->bij", ox, oy, w / bw)
        cover = self._raster(pa, self.is_macro, g, nx, ny) / (g * g)
        cover = cover.clamp(max=1.0)
        cell_area = self._gcell_area(nx, ny, g, pa)
        free = 1.0 - self.cfg.macro_block_frac * cover
        cap_h = self.cap_h_unit * cell_area * free
        cap_v = self.cap_v_unit * cell_area * free
        of_h, of_v = torch.relu(dem_h - cap_h), torch.relu(dem_v - cap_v)
        total_dem = (dem_h + dem_v).sum((1, 2)).clamp_min(1e-12)
        ratio = torch.maximum(dem_h / cap_h.clamp_min(1e-12), dem_v / cap_v.clamp_min(1e-12))
        return {"overflow": (of_h + of_v).sum((1, 2)), "overflow_ratio": (of_h + of_v).sum((1, 2)) / total_dem,
                "peak": ratio.flatten(1).max(1).values, "dem_h": dem_h, "dem_v": dem_v, "cap_h": cap_h, "cap_v": cap_v,
                "of_map": of_h + of_v, "cover": cover}

    def _gcell_area(self, nx, ny, g, like):
        wx = torch.clamp(self.core_wh[0] - torch.arange(nx, device=like.device, dtype=like.dtype) * g, max=g)
        wy = torch.clamp(self.core_wh[1] - torch.arange(ny, device=like.device, dtype=like.dtype) * g, max=g)
        return wx.view(-1, 1) * wy.view(1, -1)

    def channel_shortage(self, pos: torch.Tensor, rudy: dict | None = None) -> torch.Tensor:
        r = rudy or self.rudy(pos)
        cov = (r["cover"] > 0.5).to(r["of_map"].dtype)            # (B,nx,ny), no gradient through the mask
        k = self.cfg.channel_reach
        B, nx, ny = cov.shape

        def near(t, dim, sign):
            acc = torch.zeros_like(t)
            for s in range(1, k + 1):
                acc = torch.maximum(acc, torch.roll(t, shifts=sign * s, dims=dim) * self._edge_mask(t, dim, sign * s))
            return acc
        left, right = near(cov, 1, 1), near(cov, 1, -1)
        down, up = near(cov, 2, 1), near(cov, 2, -1)
        chan = (1 - cov) * torch.maximum(left * right, down * up)
        return (r["of_map"] * chan.detach()).sum((1, 2))

    @staticmethod
    def _edge_mask(t, dim, shift):
        n = t.shape[dim]
        idx = torch.arange(n, device=t.device)
        valid = (idx - shift >= 0) & (idx - shift < n)
        shape = [1, 1, 1]
        shape[dim] = n
        return valid.view(shape).to(t.dtype)

    # ------------------------------------------------------------------ bundle
    def all(self, pos: torch.Tensor) -> dict:
        with torch.no_grad():
            r = self.rudy(pos)
            return {
                "hpwl": self.hpwl_exact(pos), "hpwl_wa": self.hpwl_wa(pos), "hpwl_lse": self.hpwl_lse(pos),
                "macro_overlap": self.macro_overlap(pos), "outside_area": self.outside_area(pos),
                "density_overflow": self.density_overflow(pos), "rudy_overflow": r["overflow"],
                "rudy_overflow_ratio": r["overflow_ratio"], "rudy_peak": r["peak"],
                "channel_shortage": self.channel_shortage(pos, r),
            }


# ---------------------------------------------------------------------- surrogate J0
DEFAULT_J0 = {"hpwl_wa": 1.0, "macro_overlap": 4.0, "outside_area": 4.0, "density_overflow": 0.5,
              "rudy_overflow_ratio": 1.0, "channel_shortage": 0.25}


def surrogate_j0(ctx: F0Context, pos: torch.Tensor, ref: dict, weights: dict | None = None) -> torch.Tensor:
    """Differentiable J^(0): weighted, per-design normalized f0 terms.

    ref: normalizers, e.g. {"hpwl_wa": baseline WA wirelength, "macro_area": total movable macro area,
         "rudy_overflow": baseline RUDY overflow}.  Overlap/outside are divided by total macro area.
    """
    w = weights or DEFAULT_J0
    macro_area = max(float(ref.get("macro_area", 1.0)), 1e-12)
    out = 0.0
    if w.get("hpwl_wa"):
        out = out + w["hpwl_wa"] * ctx.hpwl_wa(pos) / max(float(ref["hpwl_wa"]), 1e-12)
    if w.get("macro_overlap"):
        out = out + w["macro_overlap"] * ctx.macro_overlap(pos) / macro_area
    if w.get("outside_area"):
        out = out + w["outside_area"] * ctx.outside_area(pos) / macro_area
    if w.get("density_overflow"):
        out = out + w["density_overflow"] * ctx.density_overflow(pos)
    need_r = w.get("rudy_overflow_ratio") or w.get("channel_shortage")
    if need_r:
        r = ctx.rudy(pos)
        if w.get("rudy_overflow_ratio"):
            out = out + w["rudy_overflow_ratio"] * r["overflow_ratio"]
        if w.get("channel_shortage"):
            out = out + w["channel_shortage"] * ctx.channel_shortage(pos, r) / max(float(ref.get("rudy_overflow", 1.0)), 1e-9)
    return out


def reference_normalizers(ctx: F0Context, pos) -> dict:
    """Normalizers for surrogate_j0 from a reference (baseline) layout."""
    with torch.no_grad():
        p = torch.as_tensor(np.asarray(pos), device=ctx.device, dtype=ctx.dtype)
        mm = ctx.design.is_macro & ~ctx.design.is_fixed
        return {"hpwl_wa": float(ctx.hpwl_wa(p)[0]), "macro_area": float(ctx.design.area[mm].sum()) or 1.0,
                "rudy_overflow": max(float(ctx.rudy(p)["overflow"][0]), 1e-9)}
