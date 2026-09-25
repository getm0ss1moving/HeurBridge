"""Metamorphic relations MR1-MR6 (task T7.1, verification layer V1; proposal s.7.3).

Transformations of a (Design, Layout) pair that must leave metrics (or outputs) related in a known way.
They need no reference solution, so they test f0 metrics, the projection P_M, heuristics and bridges.
  MR1 relabel objects and nets            metrics equal; outputs permuted
  MR2 mirror die about x = W/2            metrics equal (orientation N<->FN mapping on objects)
  MR3 translate the die origin            metrics identical
  MR4 add an isolated zero-weight net     metrics unchanged
  MR5 tighten capacity on one GCell       overflow on that GCell does not decrease
  MR6 two disconnected copies side by side  additive metrics double (per-copy = single design)
"""

from __future__ import annotations

import numpy as np

from ..core import orient as O
from ..core.design import Design, Layout, build_csr
from ..evolve.sandbox import permute_design


def mr1_relabel(design: Design, layout: Layout, rng: np.random.Generator):
    perm = rng.permutation(design.n_objects)
    nperm = rng.permutation(design.n_nets)
    d2, l2, inv = permute_design(design, layout, perm, nperm)
    return d2, l2, perm


def _mirror_table():
    """Orientation after mirroring the die about a vertical axis: MY composed with the orientation."""
    from ..bridge.data import COMP
    return {o: int(COMP[O.MY][o]) for o in range(8)}


MIRROR = _mirror_table()


def mr2_mirror_x(design: Design, layout: Layout):
    """Mirror about the core's vertical centre line: x -> 1 - x, pin offsets dx -> -dx, orientation mirrored."""
    d2 = Design(**{**design.__dict__})
    d2.pin_off = design.pin_off.copy()
    # pin offsets are in the master frame; mirroring the placement composes MY with the orientation instead
    l2 = layout.copy()
    l2.pos = layout.pos.copy()
    l2.pos[:, 0] = 1.0 - layout.pos[:, 0]
    l2.orient = np.array([MIRROR[int(o)] for o in layout.orient], dtype=np.int8)
    return d2, l2


def mr3_translate(design: Design, layout: Layout, dx: float, dy: float):
    d2 = Design(**{**design.__dict__})
    d2.core = (design.core[0] + dx, design.core[1] + dy, design.core[2] + dx, design.core[3] + dy)
    d2.die = (design.die[0] + dx, design.die[1] + dy, design.die[2] + dx, design.die[3] + dy)
    if design.rows is not None:
        d2.rows = design.rows + np.array([dx, dy, 0, 0])
    l2 = layout.copy()
    l2.schema = d2.schema_hash()
    return d2, l2


def mr4_dummy_net(design: Design, layout: Layout, a: int, b: int):
    """Add a zero-weight 2-pin net between objects a and b."""
    nets = [list(design.pin_idx[design.net_ptr[k]:design.net_ptr[k + 1]]) for k in range(design.n_nets)]
    P = design.n_pins
    pin_obj = np.r_[design.pin_obj, [a, b]]
    pin_off = np.r_[design.pin_off, np.zeros((2, 2))]
    nets.append([P, P + 1])
    ptr, idx = build_csr(nets)
    d2 = Design(**{**design.__dict__, "pin_obj": pin_obj, "pin_off": pin_off, "net_ptr": ptr, "pin_idx": idx,
                   "net_weight": np.r_[design.net_weight, 0.0], "net_names": None, "pin_names": None})
    l2 = layout.copy()
    l2.schema = d2.schema_hash()
    return d2, l2


def mr6_duplicate(design: Design, layout: Layout):
    """Two copies side by side along x (core width doubles); nets stay within copies."""
    n, W = design.n_objects, design.core_wh[0]
    nets = [list(design.pin_idx[design.net_ptr[k]:design.net_ptr[k + 1]]) for k in range(design.n_nets)]
    P = design.n_pins
    nets2 = nets + [[p + P for p in net] for net in nets]
    ptr, idx = build_csr(nets2)
    xl, yl, xh, yh = design.core
    d2 = Design(id=design.id + "_x2", family=design.family, tech=design.tech,
                names=list(design.names) + [nm + "__copy" for nm in design.names], size=np.r_[design.size, design.size],
                is_macro=np.r_[design.is_macro, design.is_macro], is_fixed=np.r_[design.is_fixed, design.is_fixed],
                is_io=np.r_[design.is_io, design.is_io], pin_obj=np.r_[design.pin_obj, design.pin_obj + n],
                pin_off=np.r_[design.pin_off, design.pin_off], net_ptr=ptr, pin_idx=idx,
                net_weight=np.r_[design.net_weight, design.net_weight], die=(xl, yl, xl + 2 * W, yh),
                core=(xl, yl, xl + 2 * W, yh), masters=None, rows=None, site=design.site, dbu=design.dbu)
    abs1 = design.to_abs(layout.pos)
    abs2 = abs1 + np.array([W, 0.0])
    pos = d2.to_norm(np.r_[abs1, abs2])
    l2 = Layout(pos=pos, orient=np.r_[layout.orient, layout.orient], schema=d2.schema_hash())
    return d2, l2
