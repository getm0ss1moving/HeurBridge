"""scripts/beat_tool_demo.py: the local-search moves start from a layout and change exactly one decision each."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def test_moves_change_one_macro_or_swap_a_pair():
    from heurbridge.core import synth
    import beat_tool_demo as B
    des, lay = synth.make_design(seed=3, n_macros=8, n_cells=30, n_io=6)
    mm = np.flatnonzero(des.is_macro & ~des.is_fixed)
    out = B.moves(des, lay, np.random.default_rng(0), 40)
    assert len(out) == 40
    for what, new in out:
        changed = np.flatnonzero((np.abs(new.pos - lay.pos) > 1e-12).any(1) | (new.orient != lay.orient))
        assert set(changed) <= set(mm)                         # only movable macros move
        assert len(changed) == (2 if what == "swap" else 1) or (what.startswith("shift") and len(changed) <= 1)
        assert np.all(new.pos[mm] >= 0) and np.all(new.pos[mm] <= 1)
