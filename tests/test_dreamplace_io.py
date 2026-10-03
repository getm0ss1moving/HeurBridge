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


def test_tool_input_frees_the_macros_the_design_keeps_movable(tmp_path):
    """ISPD2005 lists its macros as terminals; in the MMS convention the design keeps them movable.  The tool's input
    (fix_macros=False) must write them as movable nodes, f1's (fix_macros=True) as fixed; IO pads stay terminals."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "t.aux").write_text("RowBasedPlacement : t.nodes t.nets t.pl t.scl\n")
    (src / "t.nodes").write_text("UCLA nodes 1.0\n\nNumNodes : 3\nNumTerminals : 2\nc0 2 4\nm0 20 30 terminal\np0 1 1 terminal\n")
    (src / "t.nets").write_text("UCLA nets 1.0\n\nNumNets : 1\nNumPins : 3\nNetDegree : 3 n0\n"
                               "  c0 O : 0 0\n  m0 I : 1 2\n  p0 I : 0 0\n")
    (src / "t.pl").write_text("UCLA pl 1.0\n\nc0 10 10 : N\nm0 40 40 : N /FIXED\np0 0 0 : N /FIXED\n")
    (src / "t.scl").write_text("UCLA scl 1.0\n\nNumRows : 2\nCoreRow Horizontal\n  Coordinate : 0\n  Height : 4\n"
                               "  Sitewidth : 1\n  Sitespacing : 1\n  Siteorient : 1\n  Sitesymmetry : 1\n"
                               "  SubrowOrigin : 0 NumSites : 100\nEnd\nCoreRow Horizontal\n  Coordinate : 4\n  Height : 4\n"
                               "  Sitewidth : 1\n  Sitespacing : 1\n  Siteorient : 1\n  Sitesymmetry : 1\n"
                               "  SubrowOrigin : 0 NumSites : 100\nEnd\n")
    d, lay = load_bookshelf(src / "t.aux", family="ispd2005")
    m, p = d.names.index("m0"), d.names.index("p0")
    assert d.is_macro[m] and d.is_fixed[m] and d.is_io[p]
    d.is_fixed = d.is_fixed & ~d.is_macro                                    # the MMS convention (load_raw)
    got = {}
    for fix in (False, True):
        out = tmp_path / ("w%d" % fix)
        write_oriented_bookshelf(d, lay, out, name="t", fix_macros=fix)
        text = (out / "t.nodes").read_text()
        nodes = {l.split()[0]: l.split()[3:] for l in text.splitlines() if l.split() and l.split()[0] in ("c0", "m0", "p0")}
        pl = {l.split()[0]: l for l in (out / "t.pl").read_text().splitlines() if l.split() and l.split()[0] in ("c0", "m0", "p0")}
        got[fix] = (nodes, pl, text)
        assert nodes["p0"] == ["terminal"] and "/FIXED" in pl["p0"]           # the IO pad is unchanged
    nodes, pl, text = got[False]                                               # the tool's input: the macro is free
    assert nodes["m0"] == [] and "/FIXED" not in pl["m0"] and "NumTerminals : 1" in text
    nodes, pl, text = got[True]                                                # f1's input: unchanged, fixed
    assert nodes["m0"] == ["terminal"] and "/FIXED" in pl["m0"] and "NumTerminals : 2" in text


def test_bookshelf_from_any_design_round_trips(tmp_path):
    """write_bookshelf_from_design (Track-B designs come from DEF): pins and positions survive the round trip through
    the bookshelf reader; macros and cells movable, IOs fixed; read_bookshelf_layout reads DREAMPlace's .pl back."""
    from heurbridge.core import synth
    from heurbridge.eval.dreamplace import read_bookshelf_layout, write_bookshelf_from_design
    des, lay = synth.make_design(seed=4, n_macros=5, n_cells=40, n_io=6)
    lay.pos[~des.is_io] = np.random.default_rng(0).uniform(0.2, 0.8, (int((~des.is_io).sum()), 2))
    aux = write_bookshelf_from_design(des, lay, tmp_path, name="t", scale=1000.0)
    d2, l2 = load_bookshelf(aux, family="ibm")
    assert not d2.is_fixed[des.is_macro].any() and not d2.is_fixed[~des.is_macro & ~des.is_io].any()
    assert d2.is_fixed[des.is_io].all()
    back = read_bookshelf_layout(des, lay, aux.with_suffix(".pl"), scale=1000.0)
    keep = ~des.is_io | np.isfinite(lay.pos).all(1)
    assert np.abs(des.to_abs(back.pos[keep]) - des.to_abs(lay.pos[keep])).max() < 2e-3   # rounding to 1/1000
    a = pin_positions(des, lay)
    b = pin_positions(d2, l2) / 1000.0
    assert np.abs(a - b).max() < 2e-3
