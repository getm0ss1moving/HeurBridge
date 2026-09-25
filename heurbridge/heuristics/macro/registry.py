"""Macro seed population (task T2.2): 7 families, 2-3 parameter variants each.

A program's source = shared helpers (_helpers.py) + ``PARAMS = {...}`` + the family body
(programs/*.py), so every variant is a self-contained, content-addressed program that passes
the sandbox contract and can be edited by the LLM as a whole.  M1 is the tool-native macro
placer (Hier-RTLMP / DREAMPlace); its layouts are produced by a cached tool wrapper, not the sandbox.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent

W_BASE = {"area": 0.2, "wl": 1.0, "outline": 5.0, "boundary": 0.3, "notch": 0.2, "overlap": 10.0}

FAMILIES = {
    "M2": ("m2_sa.py", "simulated annealing on Hier-RTLMP cost terms + orientation pass", [
        {"iters": 3000, "w": W_BASE, "step0": 0.08, "T0": 0.05, "cool": 0.999, "notch_gap": 0.01, "flip": True},
        {"iters": 3000, "w": {**W_BASE, "boundary": 1.0, "wl": 0.5}, "step0": 0.08, "T0": 0.05, "cool": 0.999,
         "notch_gap": 0.01, "flip": True},
        {"iters": 6000, "w": {**W_BASE, "wl": 2.0, "area": 0.5}, "step0": 0.05, "T0": 0.02, "cool": 0.9995,
         "notch_gap": 0.02, "flip": False},
    ]),
    "M3": ("m3_boundary.py", "boundary-biased greedy mask placement (FlowPlace prior)", [
        {"grid": 64, "lam": 0.02, "wl_w": 0.0, "temp": 0.05},
        {"grid": 64, "lam": 0.05, "wl_w": 0.5, "temp": 0.05},
        {"grid": 96, "lam": 0.03, "wl_w": 1.0, "temp": 0.02},
    ]),
    "M4": ("m4_tiling.py", "dataflow/hierarchy clustering + tiling of macro groups", [
        {"n_groups": "sqrt", "mode": "perimeter", "gap": 0.005},
        {"n_groups": "sqrt", "mode": "blocks", "gap": 0.005},
        {"n_groups": 4, "mode": "perimeter", "gap": 0.01},
    ]),
    "M5": ("m5_mincut.py", "recursive min-cut bisection with macro slots", [
        {"kl_iters": 10, "pull_w": 1.0},
        {"kl_iters": 30, "pull_w": 0.0},
    ]),
    "M6": ("m6_order.py", "OrderPlace-style ordering policy + greedy placement", [
        {"order": "area", "grid": 64, "beta": 0.5},
        {"order": "conn", "grid": 64, "beta": 0.5},
        {"order": "io", "grid": 64, "beta": 1.0},
    ]),
    "M7": ("m7_random.py", "random legal placement (control)", [
        {"tries": 1},
        {"tries": 30},
    ]),
}
TOOL_FAMILIES = {"M1": "tool-native macro placement: OpenROAD rtl_macro_placer (Track B) or DREAMPlace mixed-size (Track A)"}


def program_source(family: str, variant: int) -> str:
    fname, _, variants = FAMILIES[family]
    params = variants[variant]
    helpers = (HERE / "_helpers.py").read_text()
    body = (HERE / "programs" / fname).read_text()
    head = "# HeurBridge macro seed %s.v%d  (%s)\n" % (family, variant, FAMILIES[family][1])
    return head + helpers + "\n\nPARAMS = %r\n\n\n" % (params,) + body


def all_programs() -> list:
    out = []
    for fam, (fname, desc, variants) in FAMILIES.items():
        for v in range(len(variants)):
            src = program_source(fam, v)
            out.append({"id": "%s.v%d" % (fam, v), "family": fam, "variant": v, "desc": desc, "params": variants[v],
                        "source": src, "sha256": hashlib.sha256(src.encode()).hexdigest()})
    return out
