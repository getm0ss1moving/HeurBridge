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


def test_refiner_pair_moves_are_shifts_only():
    """scripts/tool_ls_pairs.py: training targets come from shifts only (learnable by the bridge: no swap, no flip)."""
    from heurbridge.core import synth
    import tool_ls_pairs as P
    des, lay = synth.make_design(seed=5, n_macros=8, n_cells=30, n_io=6)
    for new in P.shift_moves(des, lay, np.random.default_rng(1), 30):
        changed = np.flatnonzero((np.abs(new.pos - lay.pos) > 1e-12).any(1))
        assert len(changed) <= 1 and np.array_equal(new.orient, lay.orient)


def test_raw_loader_applies_the_ispd_convention(monkeypatch):
    """scripts/tool_refine_eval.load_raw: ISPD2005 macros become movable (the seeding campaign's MMS convention)."""
    import types
    import tool_refine_eval as T
    from heurbridge.core import bookshelf

    class FakeDesign:
        def __init__(self):
            self.is_fixed = np.array([True, True, False])
            self.is_macro = np.array([True, False, False])

        def schema_hash(self):
            return "h"
    monkeypatch.setattr(bookshelf, "load_bookshelf", lambda path, family: (FakeDesign(), types.SimpleNamespace(schema="")))
    d, l = T.load_raw("ispd2005", "adaptec1")
    assert list(d.is_fixed) == [False, True, False] and l.schema == "h"
    d, l = T.load_raw("ibm", "ibm01")
    assert list(d.is_fixed) == [True, True, False]                 # IBM: unchanged
