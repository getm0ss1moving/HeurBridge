"""Standard-cell start positions for a cell-stage recipe with start = "positions" (CellStage.positions).

A positions function maps (design, macro layout) to (standard-cell object indices, lower-left corners in microns[,
info dict]) for EVERY standard cell: in a partly placed design the first global placement would start the placed cells where they
are and the rest at the core centre (third_party/OpenROAD-676f8451/src/gpl/src/initialPlace.cpp:135-142), and
orfs.cell_locations_tcl stops the flow on a name it cannot find (heurbridge/eval/orfs.py:85-105).

  hbgp(cfg)        HB-GP (heurbridge/eval/gp.py) places the cells with the macros and IOs held at the layout
  from_npz(path)   a placement another tool wrote: arrays "names" (instance names) and "ll_um" (n x 2)
  from_npz_dir(d)  the file <d>/<macro layout key>.npz for whichever layout is evaluated (key: layout_key)
  from_source(s)   the function a recipe's source names: "hbgp", "npz:<file>" or "npzdir:<dir>"
  write_npz(...)   writes that file
  dreamplace(...)  DREAMPlace places the standard cells around the macros held fixed (GPU servers; HB_DREAMPLACE)
Standard cells are the objects that are neither macros, IOs nor fixed (heuristics/cell/cluster.cell_mask).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..heuristics.cell.cluster import cell_mask


def lower_left(design, layout, cells: np.ndarray) -> np.ndarray:
    """Lower-left corners (microns) of ``cells`` placed at ``layout`` (standard cells are not rotated here)."""
    return design.to_abs(layout.pos[cells]) - design.size[cells] / 2


def hbgp(cfg=None, threads: int = 1):
    """A positions function backed by HB-GP, returning (cells, lower-left corners, HB-GP's info).  One thread by
    default: torch's multi-threaded reductions make HB-GP differ from run to run (heurbridge/eval/f1.py run_hbgp_f1),
    and a recipe's start must be the same every time."""
    def fn(design, layout):
        import torch
        from ..eval import gp
        prev = torch.get_num_threads()
        torch.set_num_threads(threads)
        try:
            placed, info = gp.place(design, layout, cfg)
        finally:
            torch.set_num_threads(prev)
        cells = np.flatnonzero(cell_mask(design))
        if not np.isfinite(placed.pos[cells]).all():
            raise RuntimeError("HB-GP left %d standard cells unplaced" % int((~np.isfinite(placed.pos[cells]).all(1)).sum()))
        return cells, lower_left(design, placed, cells), info
    return fn


def layout_key(design, layout) -> str:
    """The macro layout's identity, as the campaign ledgers key it (heurbridge/pipeline/seed_archive.layout_key)."""
    from ..pipeline.seed_archive import layout_key as key
    mm = design.is_macro & ~design.is_fixed
    return key({"pos_macros": layout.pos[mm].tolist(), "orient_macros": layout.orient[mm].tolist()})


def from_npz_dir(directory):
    """Positions precomputed per macro layout (scripts/cell_positions.py): <directory>/<layout_key>.npz."""
    directory = Path(directory)

    def fn(design, layout):
        path = directory / ("%s.npz" % layout_key(design, layout))
        if not path.exists():
            raise FileNotFoundError("no precomputed positions for this macro layout: %s" % path)
        return from_npz(path)(design, layout)
    return fn


def from_source(source: str, gp_cfg=None):
    """The positions function a recipe's ``source`` names: "hbgp", "npz:<file>" or "npzdir:<dir>" (paths relative to
    the working directory)."""
    if source == "hbgp":
        return hbgp(gp_cfg)
    if source.startswith("npz:") and len(source) > 4:
        return from_npz(source[4:])
    if source.startswith("npzdir:") and len(source) > 7:
        return from_npz_dir(source[7:])
    raise ValueError("unknown positions source %r" % source)


def write_npz(path, design, cells, ll_um) -> Path:
    path = Path(path)
    np.savez_compressed(path, names=np.asarray([design.names[int(i)] for i in cells]), ll_um=np.asarray(ll_um, float))
    return path


def from_npz(path):
    """A positions function reading a placement file; every standard cell of the design must be in it.  The info it
    returns names the file and the start of its sha256, so a run's record traces its start to the file."""
    path = Path(path)

    def fn(design, layout):
        import hashlib
        info = {"positions_file": path.name, "positions_sha256": hashlib.sha256(path.read_bytes()).hexdigest()[:16]}
        z = np.load(path, allow_pickle=False)
        names, ll = [str(n) for n in z["names"]], np.asarray(z["ll_um"], float)
        if ll.shape != (len(names), 2) or not np.isfinite(ll).all():
            raise ValueError("%s: ll_um must be a finite (n, 2) array matching names" % path)
        idx = {n: i for i, n in enumerate(design.names)}
        unknown = [n for n in names if n not in idx]
        if unknown:
            raise ValueError("%s names %d instances the design does not have, e.g. %s" % (path, len(unknown), unknown[0]))
        given = np.array([idx[n] for n in names], dtype=np.int64)
        cells = np.flatnonzero(cell_mask(design))
        missing = np.setdiff1d(cells, given)
        if len(missing):
            raise ValueError("%s misses %d standard cells, e.g. %s" % (path, len(missing), design.names[int(missing[0])]))
        keep = np.isin(given, cells)
        return given[keep], ll[keep], info
    return fn


def dreamplace_convergence(log: str, stop_overflow: float) -> dict:
    """DREAMPlace's last logged global-placement iteration and its overflow, whether it reported a divergence (it
    then rolls back to its best position), and whether it stopped at its overflow target without one."""
    import re
    last = None
    for m in re.finditer(r"iteration\s+(\d+),.*?Overflow\s+([0-9.Ee+-]+),", log):
        last = (int(m.group(1)), float(m.group(2)))
    div = "DIVERGENCE" in log
    if last is None:
        return {"iterations": None, "overflow": None, "diverged": div, "converged": False}
    return {"iterations": last[0], "overflow": last[1], "diverged": div,
            "converged": bool(last[1] <= stop_overflow + 1e-9 and not div)}


def dreamplace(design, layout, work, target_density: float = 0.8, seed: int = 0, gpu: bool = True, iters: int = 1000,
               timeout: int = 3600, scale: float = 1000.0) -> tuple:
    """(cells, lower-left corners in microns, info): DREAMPlace's global placement and greedy legalization of the
    standard cells with every macro held fixed at ``layout`` (a copy of the design marks them fixed, so the
    bookshelf writer makes them /FIXED terminals: heurbridge/eval/dreamplace.py write_bookshelf_from_design).  The
    Abacus pass stays off, as for DREAMPlace's Track-B macro runs (scripts/dreamplace_trackb.py).  A run that moves
    a macro is an error."""
    import copy
    from ..eval.dreamplace import params, read_bookshelf_layout, run_placer, write_bookshelf_from_design
    work = Path(work)
    fixed = copy.copy(design)
    fixed.is_fixed = np.asarray(design.is_fixed, bool) | np.asarray(design.is_macro, bool)
    aux = write_bookshelf_from_design(fixed, layout, work / "in", name=design.id, scale=scale)
    pj = params(str(aux.resolve()), str((work / "out").resolve()), gpu=gpu, iters=iters, seed=seed,
                target_density=target_density)
    pj["abacus_legalize_flag"] = 0
    rc, log, wall = run_placer(pj, work, timeout)
    pl = work / "out" / design.id / ("%s.gp.pl" % design.id)
    info = {"dreamplace_rc": rc, "dreamplace_s": wall, "target_density": target_density, "seed": seed,
            **dreamplace_convergence(log, pj.get("stop_overflow", 0.07))}
    if rc != 0 or not pl.exists():
        raise RuntimeError("DREAMPlace failed (rc %s): %s" % (rc, log[-400:]))
    placed = read_bookshelf_layout(fixed, layout, pl, scale=scale)
    mm = np.asarray(design.is_macro, bool) & layout.placed
    moved = float(np.abs(design.to_abs(placed.pos[mm]) - design.to_abs(layout.pos[mm])).max()) if mm.any() else 0.0
    if moved > 1.0 / scale:
        raise RuntimeError("DREAMPlace moved a fixed macro by %.4g um" % moved)
    cells = np.flatnonzero(cell_mask(design))
    if not np.isfinite(placed.pos[cells]).all():
        raise RuntimeError("DREAMPlace left standard cells unplaced")
    info["macro_max_shift_um"] = moved
    return cells, lower_left(design, placed, cells), info
