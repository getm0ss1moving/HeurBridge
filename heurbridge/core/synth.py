"""Synthetic placement instances (tests and noise->layout pretraining, task T3.4).

Generator in the spirit of ChipDiffusion's v1/v2 data: place objects first
(the hidden "intended" layout, macros legal and non-overlapping), then draw
nets between pins that are close in that layout, so the netlist carries the
placement's structure.  The hidden layout is returned as a reference layout.
"""

from __future__ import annotations

import numpy as np

from . import orient as O
from .design import Design, Layout, build_csr


def _place_macros(rng, n, die, sizes, tries=200):
    pos = np.zeros((n, 2))
    placed = []
    for i in range(n):
        w, h = sizes[i]
        for _ in range(tries):
            p = rng.uniform([w / 2, h / 2], [die[0] - w / 2, die[1] - h / 2])
            if all(abs(p[0] - pos[j, 0]) >= (w + sizes[j, 0]) / 2 or abs(p[1] - pos[j, 1]) >= (h + sizes[j, 1]) / 2
                   for j in placed):
                break
        pos[i] = p
        placed.append(i)
    return pos


def make_design(seed: int = 0, n_macros: int = 8, n_cells: int = 200, n_io: int = 16, n_nets: int | None = None,
                die: float = 1000.0, row_h: float = 10.0, macro_frac=(0.06, 0.18), same_size_groups: int = 2,
                family: str = "synth", locality: float = 0.08, max_deg: int = 6,
                allow_macro_orients: bool = False) -> tuple[Design, Layout]:
    """Return (design, reference layout).  Macros are movable, IOs fixed on the boundary."""
    rng = np.random.default_rng(seed)
    n = n_macros + n_cells + n_io
    size = np.zeros((n, 2))
    # macros: a few interchangeable same-size groups (exercises the symmetry matching of T3.2)
    ms = rng.uniform(macro_frac[0], macro_frac[1], (n_macros, 2)) * die
    ms = np.round(ms / row_h) * row_h
    for g in range(min(same_size_groups, n_macros // 2)):
        a, b = 2 * g, 2 * g + 1
        ms[b] = ms[a]
    size[:n_macros] = ms
    size[n_macros:n_macros + n_cells, 0] = rng.integers(2, 12, n_cells).astype(float)
    size[n_macros:n_macros + n_cells, 1] = row_h
    masters = (["macro_%d" % i for i in range(n_macros)] + ["cell_w%d" % int(w) for w in size[n_macros:n_macros + n_cells, 0]]
               + ["__IO__"] * n_io)
    for g in range(min(same_size_groups, n_macros // 2)):
        masters[2 * g + 1] = masters[2 * g]
    pos = np.zeros((n, 2))
    order = np.argsort(-(size[:n_macros].prod(1)))
    mp = _place_macros(rng, n_macros, (die, die), size[:n_macros][order])
    pos[:n_macros][order] = mp
    pos[n_macros:n_macros + n_cells] = rng.uniform(0.02 * die, 0.98 * die, (n_cells, 2))
    side = rng.integers(0, 4, n_io)
    t = rng.uniform(0.02, 0.98, n_io) * die
    pos[n_macros + n_cells:, 0] = np.where(side == 0, 0.0, np.where(side == 1, die, t))
    pos[n_macros + n_cells:, 1] = np.where(side == 2, 0.0, np.where(side == 3, die, t))
    # nets: driver + nearby sinks in the hidden layout
    n_nets = n_nets or int(1.2 * (n_cells + n_macros))
    pin_obj, pin_off, nets = [], [], []

    def add_pin(i):
        w, h = size[i]
        if i < n_macros:     # macro pins on the boundary
            s = rng.integers(0, 4)
            u = rng.uniform(-0.5, 0.5)
            off = [(u * w, -h / 2), (w / 2, u * h), (u * w, h / 2), (-w / 2, u * h)][s]
        else:
            off = (rng.uniform(-w / 2, w / 2), rng.uniform(-h / 2, h / 2)) if w > 0 else (0.0, 0.0)
        pin_obj.append(i)
        pin_off.append(off)
        return len(pin_obj) - 1

    scale = locality * die
    for _ in range(n_nets):
        a = int(rng.integers(0, n))
        d = np.linalg.norm(pos - pos[a], axis=1)
        p = np.exp(-d / scale)
        p[a] = 0.0
        p /= p.sum()
        k = int(rng.integers(1, max_deg))
        sinks = rng.choice(n, size=min(k, n - 1), replace=False, p=p)
        nets.append([add_pin(a)] + [add_pin(int(s)) for s in sinks])
    # every macro and IO connected at least once
    for i in list(range(n_macros)) + list(range(n_macros + n_cells, n)):
        if not any(pin_obj[p] == i for net in nets for p in net):
            j = n_macros + int(rng.integers(0, n_cells))
            nets.append([add_pin(i), add_pin(j)])
    ptr, idx = build_csr(nets)
    is_macro = np.zeros(n, dtype=bool)
    is_macro[:n_macros] = True
    is_io = np.zeros(n, dtype=bool)
    is_io[n_macros + n_cells:] = True
    rows = np.array([(0.0, y, die, row_h) for y in np.arange(0, die, row_h)])
    des = Design(
        id="synth_%d" % seed, family=family, tech="synthetic", names=["o%d" % i for i in range(n)], size=size,
        is_macro=is_macro, is_fixed=is_io.copy(), is_io=is_io,
        pin_obj=np.array(pin_obj, dtype=np.int64), pin_off=np.array(pin_off, dtype=np.float64),
        net_ptr=ptr, pin_idx=idx, net_weight=np.ones(len(nets)), die=(0.0, 0.0, die, die), core=(0.0, 0.0, die, die),
        masters=masters, rows=rows, site=(1.0, row_h), dbu=1.0, source={"format": "synthetic", "seed": seed},
    )
    des.validate()
    ori = np.zeros(n, dtype=np.int8)
    if allow_macro_orients:
        ori[:n_macros] = rng.choice([O.R0, O.MX, O.MY, O.R180], n_macros)
    lay = Layout(pos=des.to_norm(pos), orient=ori, schema=des.schema_hash(), meta={"kind": "synthetic_reference"})
    return des, lay


def write_bookshelf(design: Design, layout: Layout, out_dir, name: str = "synth"):
    """Write a synthetic design as bookshelf (for loader round-trip tests)."""
    from pathlib import Path
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    n = design.n_objects
    with open(out / (name + ".nodes"), "w") as fh:
        fh.write("UCLA nodes 1.0\n\nNumNodes : %d\nNumTerminals : %d\n" % (n, int(design.is_fixed.sum())))
        for i in range(n):
            tag = " terminal" if design.is_fixed[i] else ""
            fh.write("%s %g %g%s\n" % (design.names[i], design.size[i, 0], design.size[i, 1], tag))
    with open(out / (name + ".nets"), "w") as fh:
        fh.write("UCLA nets 1.0\n\nNumNets : %d\nNumPins : %d\n" % (design.n_nets, len(design.pin_idx)))
        for k in range(design.n_nets):
            pins = design.pin_idx[design.net_ptr[k]:design.net_ptr[k + 1]]
            fh.write("NetDegree : %d n%d\n" % (len(pins), k))
            for p in pins:
                fh.write("  %s B : %.6f %.6f\n" % (design.names[design.pin_obj[p]], design.pin_off[p, 0], design.pin_off[p, 1]))
    with open(out / (name + ".wts"), "w") as fh:
        fh.write("UCLA wts 1.0\n\n")
        for k in range(design.n_nets):
            fh.write("n%d %g\n" % (k, design.net_weight[k]))
    ll = design.to_abs(layout.pos) - O.effective_size(design.size, layout.orient) / 2.0
    with open(out / (name + ".pl"), "w") as fh:
        fh.write("UCLA pl 1.0\n\n")
        for i in range(n):
            fh.write("%s %.6f %.6f : %s%s\n" % (design.names[i], ll[i, 0], ll[i, 1], O.to_def(layout.orient[i]),
                                              " /FIXED" if design.is_fixed[i] else ""))
    with open(out / (name + ".scl"), "w") as fh:
        rows = design.rows
        fh.write("UCLA scl 1.0\n\nNumRows : %d\n\n" % len(rows))
        for x, y, w, h in rows:
            fh.write("CoreRow Horizontal\n  Coordinate : %g\n  Height : %g\n  Sitewidth : 1\n  Sitespacing : 1\n"
                     "  Siteorient : 1\n  Sitesymmetry : 1\n  SubrowOrigin : %g NumSites : %d\nEnd\n" % (y, h, x, int(w)))
    (out / (name + ".aux")).write_text("RowBasedPlacement : %s.nodes %s.nets %s.wts %s.pl %s.scl\n" % ((name,) * 5))
    return out / (name + ".aux")
