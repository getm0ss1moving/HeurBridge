"""Track-A f1 input for DREAMPlace (eval/dreamplace.py): orientations baked into a bookshelf copy."""

import numpy as np
import pytest

from heurbridge.core.bookshelf import load_bookshelf
from heurbridge.core.design import pin_positions
from heurbridge.eval.dreamplace import read_placed, write_oriented_bookshelf
from heurbridge.paths import data_root

AUX = data_root() / "ibm_bookshelf" / "ibm01" / "ibm01.aux"
pytestmark = pytest.mark.skipif(not AUX.exists(), reason="needs the IBM bookshelf benchmarks")


def test_oriented_copy_preserves_every_pin(tmp_path):
    d, lay = load_bookshelf(AUX, family="ibm")
    rng = np.random.default_rng(0)
    lay.orient[d.is_macro] = rng.integers(0, 8, int(d.is_macro.sum()))      # all eight orientations
    free = ~lay.placed
    lay.pos[free] = rng.uniform(0.1, 0.9, (int(free.sum()), 2))
    aux = write_oriented_bookshelf(d, lay, tmp_path, name="ibm01")
    d2, lay2 = load_bookshelf(aux, family="ibm")
    assert set(np.unique(lay2.orient)) == {0}                               # DREAMPlace sees N only
    assert np.abs(pin_positions(d, lay) - pin_positions(d2, lay2)).max() < 1e-9
    assert (d2.is_fixed[d.is_macro]).all()                                  # macros FIXED
    assert np.array_equal(d2.is_io, d.is_io)
    back = read_placed(d, lay, aux.with_suffix(".pl"))
    assert np.abs(d.to_abs(back.pos) - d.to_abs(lay.pos)).max() < 1e-9
    assert np.array_equal(back.orient, lay.orient)
