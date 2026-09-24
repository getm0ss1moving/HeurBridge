"""Unified design object shared by every stage (task T1.1).

Design   static netlist + geometry.  Object order = netlist order and never changes.
Layout   one placement of a Design: object centres normalized to the core box
         ([0,1]^2 = core), orientation enum per object, optional routing state.

Conventions
-----------
* Units are the source's units (microns for LEF/DEF, bookshelf units otherwise).
* Pin offsets are measured from the object centre in the master (R0) frame;
  ``orient.apply`` maps them to the placed frame.  This needs no bounding-box
  shift, so every orientation is handled exactly.
* ``Layout.pos`` is float64 so that DEF DBU coordinates round-trip exactly;
  models take a float32 copy.  Unplaced objects have NaN positions.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np

from . import orient as O

SCHEMA_VERSION = "hb_design_v1"


@dataclass
class Design:
    id: str
    family: str
    tech: str
    names: list
    size: np.ndarray          # (N,2) master width/height
    is_macro: np.ndarray      # (N,) bool
    is_fixed: np.ndarray      # (N,) bool
    is_io: np.ndarray         # (N,) bool
    pin_obj: np.ndarray       # (P,) int64 owning object
    pin_off: np.ndarray       # (P,2) offset from object centre, R0 frame
    net_ptr: np.ndarray       # (M+1,) int64; net k owns pin_idx[net_ptr[k]:net_ptr[k+1]]
    pin_idx: np.ndarray       # (P',) int64 pin indices grouped by net
    net_weight: np.ndarray    # (M,) float64
    die: tuple                # (xl, yl, xh, yh)
    core: tuple               # (xl, yl, xh, yh); normalization box
    masters: list | None = None
    net_names: list | None = None
    pin_names: list | None = None
    rows: np.ndarray | None = None        # (R,4) x, y, width, height
    site: tuple | None = None              # (w, h)
    gcell_grid: dict | None = None         # {"x": edges, "y": edges, "layers": [...], "capacity": ...}
    timing: dict | None = None             # {"sdc":..., "liberty": [...], "clock_period_ns": ...}
    dbu: float = 1.0                       # DEF database units per micron (1 for bookshelf)
    source: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ sizes
    @property
    def n_objects(self) -> int:
        return len(self.names)

    @property
    def n_pins(self) -> int:
        return len(self.pin_obj)

    @property
    def n_nets(self) -> int:
        return len(self.net_ptr) - 1

    @property
    def core_wh(self) -> np.ndarray:
        xl, yl, xh, yh = self.core
        return np.array([xh - xl, yh - yl], dtype=np.float64)

    @property
    def core_ll(self) -> np.ndarray:
        return np.array(self.core[:2], dtype=np.float64)

    @property
    def movable(self) -> np.ndarray:
        return ~self.is_fixed

    @property
    def area(self) -> np.ndarray:
        return self.size[:, 0] * self.size[:, 1]

    def net_of_pin(self) -> np.ndarray:
        """(P',) net index for each entry of pin_idx."""
        deg = np.diff(self.net_ptr)
        return np.repeat(np.arange(self.n_nets), deg)

    def degrees(self) -> np.ndarray:
        return np.diff(self.net_ptr)

    # ------------------------------------------------------------------ coordinates
    def to_norm(self, xy_abs: np.ndarray) -> np.ndarray:
        return (np.asarray(xy_abs, dtype=np.float64) - self.core_ll) / self.core_wh

    def to_abs(self, xy_norm: np.ndarray) -> np.ndarray:
        return np.asarray(xy_norm, dtype=np.float64) * self.core_wh + self.core_ll

    def size_norm(self) -> np.ndarray:
        return self.size / self.core_wh

    # ------------------------------------------------------------------ identity
    def schema_hash(self) -> str:
        """Hash of everything a Layout must agree with (object order, sizes, flags, pins, nets)."""
        h = hashlib.sha256()
        h.update(SCHEMA_VERSION.encode())
        h.update("\x00".join(map(str, self.names)).encode())
        for arr in (self.size, self.is_macro, self.is_fixed, self.is_io, self.pin_obj,
                    self.pin_off, self.net_ptr, self.pin_idx):
            a = np.ascontiguousarray(arr)
            h.update(str(a.dtype).encode() + str(a.shape).encode())
            h.update(a.tobytes())
        h.update(np.asarray(self.core, dtype=np.float64).tobytes())
        return h.hexdigest()[:16]

    def validate(self) -> None:
        n, p = self.n_objects, self.n_pins
        assert self.size.shape == (n, 2), self.size.shape
        for a in (self.is_macro, self.is_fixed, self.is_io):
            assert a.shape == (n,) and a.dtype == bool
        assert self.pin_off.shape == (p, 2)
        assert self.pin_obj.min(initial=0) >= 0 and self.pin_obj.max(initial=-1) < n
        assert self.net_ptr[0] == 0 and self.net_ptr[-1] == len(self.pin_idx)
        assert np.all(np.diff(self.net_ptr) >= 0)
        assert self.net_weight.shape == (self.n_nets,)
        assert self.core[2] > self.core[0] and self.core[3] > self.core[1]

    def summary(self) -> dict:
        return {
            "id": self.id, "family": self.family, "tech": self.tech,
            "objects": self.n_objects, "macros": int(self.is_macro.sum()),
            "movable_macros": int((self.is_macro & ~self.is_fixed).sum()),
            "fixed": int(self.is_fixed.sum()), "io": int(self.is_io.sum()),
            "pins": self.n_pins, "nets": self.n_nets,
            "core": [float(v) for v in self.core], "die": [float(v) for v in self.die],
            "schema": self.schema_hash(),
        }


@dataclass
class Layout:
    pos: np.ndarray                 # (N,2) float64 normalized centres (NaN = unplaced)
    orient: np.ndarray              # (N,) int8
    schema: str                     # Design.schema_hash()
    routes: dict | None = None      # optional routing state (demand tensor, guides)
    meta: dict = field(default_factory=dict)

    def copy(self) -> "Layout":
        return Layout(self.pos.copy(), self.orient.copy(), self.schema,
                      None if self.routes is None else dict(self.routes), dict(self.meta))

    @property
    def placed(self) -> np.ndarray:
        return np.isfinite(self.pos).all(1)

    def equals(self, other: "Layout", atol: float = 0.0) -> bool:
        if self.schema != other.schema or self.pos.shape != other.pos.shape:
            return False
        a, b = self.pos, other.pos
        same_nan = np.array_equal(np.isnan(a), np.isnan(b))
        fin = np.isfinite(a)
        close = np.allclose(a[fin], b[fin], rtol=0.0, atol=atol) if atol else np.array_equal(a[fin], b[fin])
        return bool(same_nan and close and np.array_equal(self.orient, other.orient))


# ---------------------------------------------------------------------- geometry
def centres_abs(design: Design, layout: Layout) -> np.ndarray:
    return design.to_abs(layout.pos)


def eff_size(design: Design, layout: Layout) -> np.ndarray:
    return O.effective_size(design.size, layout.orient)


def pin_positions(design: Design, layout: Layout, convention: str = "centre") -> np.ndarray:
    """Absolute pin positions (P,2).

    convention="centre"     geometric (OpenDB) pin position; the canonical HeurBridge value.
    convention="lef_def_v1" reproduces eda/harness/lef_def.py (pin_offset_v1_2026-09-22),
                            which omits the orientation bounding-box shift; for regression only.
    """
    c = centres_abs(design, layout)[design.pin_obj]
    o = layout.orient[design.pin_obj]
    if convention == "centre":
        return c + O.apply(design.pin_off, o)
    if convention == "lef_def_v1":
        size = design.size[design.pin_obj]
        eff = O.effective_size(size, o)
        ll_off = design.pin_off + size / 2.0
        return c - eff / 2.0 + O.lef_def_v1_offset(ll_off, o)
    raise ValueError(convention)


def hpwl(design: Design, layout: Layout, convention: str = "centre", weighted: bool = True,
         per_net: bool = False):
    """Exact HPWL in source units (numpy reference implementation; eval.f0 has the torch one)."""
    pp = pin_positions(design, layout, convention)[design.pin_idx]
    deg = design.degrees()
    out = np.zeros(design.n_nets)
    nz = deg > 0
    starts = design.net_ptr[:-1][nz]
    if len(starts):
        for d in (0, 1):
            mx = np.maximum.reduceat(pp[:, d], starts)
            mn = np.minimum.reduceat(pp[:, d], starts)
            out[nz] += mx - mn
    out[deg < 2] = 0.0
    if weighted:
        out = out * design.net_weight
    return out if per_net else float(out.sum())


def build_csr(net_pin_lists: list) -> tuple[np.ndarray, np.ndarray]:
    """[[pin, ...], ...] -> (net_ptr, pin_idx)."""
    deg = np.array([len(x) for x in net_pin_lists], dtype=np.int64)
    ptr = np.zeros(len(deg) + 1, dtype=np.int64)
    np.cumsum(deg, out=ptr[1:])
    idx = np.fromiter((p for lst in net_pin_lists for p in lst), dtype=np.int64, count=int(ptr[-1]))
    return ptr, idx
