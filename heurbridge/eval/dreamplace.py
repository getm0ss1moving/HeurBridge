"""Track-A f1 backend (T1.4): DREAMPlace global + legal placement of the cells with the macro layout FIXED,
then the f0 RUDY / HPWL metrics (timing unavailable: ``unchecked``).

DREAMPlace's bookshelf reader applies the .pl orientation neither to node footprints nor to pin offsets, and
our macro programs rotate and flip macros.  Every layout is therefore written as its own bookshelf copy with
the orientations baked in: rotated nodes get swapped sizes in .nodes, pin offsets in .nets are transformed, and
the .pl says N.  Macros carry /FIXED (DREAMPlace keeps FIXED nodes in place); IO terminals keep their original
flags.  The placed .pl is read back and the layout keeps its orientations, so the metrics are computed on the
layout that was evaluated (``write_oriented_bookshelf`` is tested for identical absolute pin positions).

Environment: HB_DREAMPLACE = DREAMPlace install prefix (contains dreamplace/Placer.py); Placer.py runs with the
current interpreter unless HB_DREAMPLACE_PYTHON is set.  The GPU is the job's CUDA_VISIBLE_DEVICES.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from .. import tools
from ..core import orient as O
from ..core.bookshelf import _fmt, parse_nets, parse_nodes, parse_pl
from ..core.design import Design, Layout


def write_oriented_bookshelf(design: Design, layout: Layout, out_dir: str | Path, name: str = "hb",
                             fix_macros: bool = True) -> Path:
    """Bookshelf copy of ``design`` placed at ``layout`` with every orientation baked in (all nodes N).

    Unplaced nodes (NaN) are written at the core centre.  Returns the .aux path."""
    files = {k: Path(v) for k, v in design.source["files"].items()}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    names, _, term, term_ni = parse_nodes(files["nodes"])
    if list(names) != list(design.names):
        raise ValueError("node order differs from the design's source .nodes")
    index = {n: i for i, n in enumerate(names)}
    _, _, pin_obj, _, pin_dir = parse_nets(files["nets"], index)
    if not np.array_equal(pin_obj, design.pin_obj):
        raise ValueError("pin order differs from the design's source .nets")
    eff = O.effective_size(design.size, layout.orient)
    n = len(names)
    with open(out / (name + ".nodes"), "w") as fh:
        fh.write("UCLA nodes 1.0\n# heurbridge: orientations baked in\n\nNumNodes : %d\nNumTerminals : %d\n" % (n, int(term.sum())))
        for i in range(n):
            kind = " terminal_NI" if term_ni[i] else (" terminal" if term[i] else "")
            fh.write("%s %s %s%s\n" % (names[i], _fmt(eff[i, 0]), _fmt(eff[i, 1]), kind))
    off = O.apply(design.pin_off, layout.orient[design.pin_obj])
    with open(out / (name + ".nets"), "w") as fh:
        fh.write("UCLA nets 1.0\n# heurbridge: pin offsets in the oriented frame\n\nNumNets : %d\nNumPins : %d\n"
                 % (len(design.net_ptr) - 1, len(design.pin_obj)))
        for k in range(len(design.net_ptr) - 1):
            pins = design.pin_idx[design.net_ptr[k]:design.net_ptr[k + 1]]
            fh.write("NetDegree : %d %s\n" % (len(pins), design.net_names[k] if design.net_names else "n%d" % k))
            for p in pins:
                fh.write("  %s %s : %s %s\n" % (names[design.pin_obj[p]], pin_dir[p], _fmt(off[p, 0]), _fmt(off[p, 1])))
    centre = design.to_abs(layout.pos)
    centre[~np.isfinite(centre).all(1)] = [(design.core[0] + design.core[2]) / 2, (design.core[1] + design.core[3]) / 2]
    ll = centre - eff / 2.0
    with open(out / (name + ".pl"), "w") as fh:
        fh.write("UCLA pl 1.0\n# heurbridge: orientations baked in\n\n")
        for i in range(n):
            flag = " /FIXED_NI" if term_ni[i] else (" /FIXED" if (term[i] or (fix_macros and design.is_macro[i])) else "")
            fh.write("%s %s %s : N%s\n" % (names[i], _fmt(ll[i, 0]), _fmt(ll[i, 1]), flag))
    parts = [name + ".nodes", name + ".nets"]
    # .wts: DREAMPlace reads net weights and asserts on unknown names, but the ICCAD04 files list node weights
    # (p1 0, a0 128, ...), which Design ignores (all IBM net weights are 1).  Written from Design.net_weight,
    # and only when some weight differs from 1.
    w = np.asarray(design.net_weight, dtype=np.float64)
    if len(w) and np.any(w != 1.0):
        with open(out / (name + ".wts"), "w") as fh:
            fh.write("UCLA wts 1.0\n\n")
            for k in range(len(w)):
                fh.write("%s %s\n" % (design.net_names[k] if design.net_names else "n%d" % k, _fmt(w[k])))
        parts.append(name + ".wts")
    parts.append(name + ".pl")
    if "scl" in files:
        dst = out / (name + ".scl")
        if not dst.exists():
            dst.symlink_to(files["scl"].resolve())
        parts.append(dst.name)
    aux = out / (name + ".aux")
    aux.write_text("RowBasedPlacement : " + " ".join(parts) + "\n")
    return aux


def read_placed(design: Design, layout: Layout, pl: str | Path) -> Layout:
    """Layout from a .pl of an oriented copy: centres from the baked footprints, orientations kept."""
    index = {n: i for i, n in enumerate(design.names)}
    ll, _, _ = parse_pl(Path(pl), index, len(design.names))
    eff = O.effective_size(design.size, layout.orient)
    out = layout.copy()
    out.pos = design.to_norm(ll + eff / 2.0)
    return out


def params(aux: str, out_dir: str, gpu: bool = True, iters: int = 1000, target_density: float = 0.9,
           legalize: bool = True, seed: int = 0, threads: int = 8) -> dict:
    """DREAMPlace JSON parameters (the values of eval.f1.dreamplace_params)."""
    return {"aux_input": aux, "gpu": int(gpu), "num_bins_x": 512, "num_bins_y": 512,
            "global_place_stages": [{"num_bins_x": 512, "num_bins_y": 512, "iteration": iters, "learning_rate": 0.01,
                                     "wirelength": "weighted_average", "optimizer": "nesterov"}],
            "target_density": target_density, "density_weight": 8e-5, "gamma": 4.0, "random_seed": seed,
            "scale_factor": 1.0, "ignore_net_degree": 100, "enable_fillers": 1, "gp_noise_ratio": 0.025,
            "global_place_flag": 1, "legalize_flag": int(legalize), "detailed_place_flag": 0, "stop_overflow": 0.07,
            "dtype": "float32", "plot_flag": 0, "random_center_init_flag": 1, "sort_nets_by_degree": 0,
            "num_threads": threads, "result_dir": out_dir, "routability_opt_flag": 0, "deterministic_flag": 1}


def run_placer(param: dict, work: Path, timeout: int = 3600) -> tuple:
    """Run DREAMPlace's Placer.py on a parameter dict; returns (returncode, log, wall seconds)."""
    root = os.environ.get("HB_DREAMPLACE")
    if not root:
        raise RuntimeError("HB_DREAMPLACE (DREAMPlace install prefix) is not set")
    pj = (work / "dreamplace.json").resolve()             # Placer.py runs in the install directory
    pj.write_text(json.dumps(param, indent=1))
    py = os.environ.get("HB_DREAMPLACE_PYTHON", sys.executable)
    t0 = time.time()
    try:
        p = tools.run_group([py, str(Path(root) / "dreamplace" / "Placer.py"), str(pj)], timeout=timeout, cwd=root)
        rc, log = p.returncode, p.stdout + "\n" + p.stderr
    except subprocess.TimeoutExpired as e:
        rc, log = "timeout", str(e.stdout or "")
    (work / "dreamplace.log").write_text(log)
    return rc, log, round(time.time() - t0, 1)


def run_dreamplace_f1(design: Design, layout: Layout, work: str | Path, f0cfg=None, gpu: bool = True,
                      iters: int = 1000, seed: int = 0, timeout: int = 3600, keep_files: bool = False) -> tuple:
    """Track-A f1: cells placed by DREAMPlace (GP + LG) around the FIXED macros of ``layout``; f0 metrics.
    Returns (record, placed layout or None).  Without ``keep_files`` the bookshelf copy and DREAMPlace's output
    are deleted once read (tens of MB per evaluation on the larger designs; the workspaces are in RAM); the
    parameters and the log stay."""
    try:
        return _run_f1(design, layout, Path(work), f0cfg, gpu, iters, seed, timeout)
    finally:
        if not keep_files:
            import shutil
            for sub in ("in", "out"):
                shutil.rmtree(Path(work) / sub, ignore_errors=True)


def _run_f1(design, layout, work, f0cfg, gpu, iters, seed, timeout):
    from .f1 import KEYS, trackA_metrics
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    aux = write_oriented_bookshelf(design, layout, work / "in", name=design.id)
    rc, log, wall = run_placer(params(str(aux.resolve()), str((work / "out").resolve()), gpu=gpu, iters=iters,
                                      seed=seed), work, timeout)
    out = {k: None for k in KEYS}
    out.update({"backend": "dreamplace", "returncode": rc, "wall_s": wall,
                "unchecked": ["gr_wl", "gr_overflow_max", "wns_place", "tns_place", "wns_gr", "tns_gr", "vias", "power"]})
    pl = work / "out" / design.id / ("%s.gp.pl" % design.id)
    if rc != 0 or not pl.exists():
        out["failure"] = "dreamplace_rc_%s" % rc if rc != 0 else "dreamplace_no_output"
        return out, None
    ov = re.findall(r"Overflow ([0-9.E+-]+)", log)
    out["gp_overflow"] = float(ov[-1]) if ov else None
    placed = read_placed(design, layout, pl)
    mac = design.is_macro & layout.placed
    moved = float(np.abs(design.to_abs(placed.pos[mac]) - design.to_abs(layout.pos[mac])).max()) if mac.any() else 0.0
    m = trackA_metrics(design, placed, f0cfg)
    out.update({"hpwl": m["hpwl"], "gr_overflow_total": m["rudy_overflow"], "rudy": m,
                "macro_max_shift": moved, "runtime_s": wall})
    if moved > 1e-6 * max(design.core[2] - design.core[0], 1.0):
        out["failure"] = "macros_moved"          # FIXED not honoured: never score such a run
        out["returncode"] = "macros_moved"
    return out, placed


def run_dreamplace_m1(design: Design, layout: Layout, work: str | Path, gpu: bool = True, iters: int = 1000,
                      seed: int = 0, timeout: int = 3600) -> tuple:
    """Track-A M1 (tool-native macro placement, spec T2.1): DREAMPlace's mixed-size placement of the design with
    the macros movable (its macro placement and macro legalization switch on by themselves), started from
    ``layout`` (the benchmark placement).  Returns (record, macro-stage layout or None): macros at DREAMPlace's
    positions (orientations kept), IOs and fixed objects unchanged, standard cells unplaced (NaN)."""
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    aux = write_oriented_bookshelf(design, layout, work / "in", name=design.id, fix_macros=False)
    rc, log, wall = run_placer(params(str(aux.resolve()), str((work / "out").resolve()), gpu=gpu, iters=iters,
                                      seed=seed), work, timeout)
    rec = {"backend": "dreamplace_m1", "returncode": rc, "wall_s": wall, "seed": seed,
           "macro_place_enabled": "automatically enabling macro_place_flag" in log}
    pl = work / "out" / design.id / ("%s.gp.pl" % design.id)
    if rc != 0 or not pl.exists():
        rec["failure"] = "dreamplace_rc_%s" % rc if rc != 0 else "dreamplace_no_output"
        return rec, None
    placed = read_placed(design, layout, pl)
    import shutil
    for sub in ("in", "out"):                            # the caller stores the M1 layout itself
        shutil.rmtree(work / sub, ignore_errors=True)
    m1 = layout.copy()
    mac = design.is_macro & ~design.is_fixed
    m1.pos[mac] = placed.pos[mac]
    cells = ~design.is_macro & ~design.is_io & ~design.is_fixed
    m1.pos[cells] = np.nan
    fixed = design.is_fixed | design.is_io
    rec["fixed_max_shift"] = float(np.nanmax(np.abs(design.to_abs(placed.pos[fixed]) - design.to_abs(layout.pos[fixed])))) \
        if fixed.any() else 0.0
    rec["failure"] = None
    return rec, m1
