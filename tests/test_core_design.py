"""T1.1 / T1.2: data model, loaders/writers, HPWL conventions, interface contract."""

from pathlib import Path

import numpy as np
import pytest

from heurbridge.core import bookshelf, contract, defio, orient as O, synth
from heurbridge.core import design as D
from heurbridge.paths import eda_dir

EDA = eda_dir()
LEF = EDA / "pdk" / "sky130A" / "sky130_fd_sc_hd.lef" if EDA else None
SPM = [EDA / "openlane_runs" / "spm_phase0_0001_src" / "results" / s / "spm.def"
       for s in ("placement", "cts", "routing")] if EDA else []
HAVE_SPM = bool(EDA) and LEF.exists() and all(p.exists() for p in SPM)


# ---------------------------------------------------------------- orientation algebra
def test_orient_effective_size_and_matrices():
    size = np.array([[3.0, 1.0]] * 8)
    eff = O.effective_size(size, np.arange(8))
    for k in range(8):
        # a transformed box of half-extents (w/2,h/2) has half-extents eff/2
        corners = np.array([[1.5, 0.5], [-1.5, 0.5], [1.5, -0.5], [-1.5, -0.5]])
        t = O.apply(corners, np.full(4, k))
        assert np.allclose(np.abs(t).max(0), eff[k] / 2)
        assert abs(abs(np.linalg.det(O.MATS[k])) - 1) < 1e-12
    assert O.to_def(O.MX90) == "FW" and O.to_def(O.MY90) == "FE"
    assert O.from_def("FS") == O.MX and O.from_odb("MXR90") == O.MX90


def test_lef_def_v1_matches_geometry_only_for_N():
    rng = np.random.default_rng(0)
    des, lay = synth.make_design(seed=1, n_macros=4, n_cells=30, n_io=6)
    lay.orient[:] = O.R0
    a = D.pin_positions(des, lay, "centre")
    b = D.pin_positions(des, lay, "lef_def_v1")
    assert np.allclose(a, b)
    lay.orient[:4] = rng.choice([O.MX, O.R180, O.MY], 4)
    a = D.pin_positions(des, lay, "centre")
    b = D.pin_positions(des, lay, "lef_def_v1")
    moved = np.isin(des.pin_obj, np.arange(4))
    assert not np.allclose(a[moved], b[moved])


# ---------------------------------------------------------------- bookshelf
def test_bookshelf_roundtrip_identity(tmp_path):
    des0, lay0 = synth.make_design(seed=3, n_macros=6, n_cells=120, n_io=10)
    aux = synth.write_bookshelf(des0, lay0, tmp_path / "src", name="t")
    d1, l1 = bookshelf.load_bookshelf(aux, family="synth")
    aux2 = bookshelf.write_bookshelf_copy(d1, l1, tmp_path / "rt", name="t")
    d2, l2 = bookshelf.load_bookshelf(aux2, family="synth")
    assert d1.schema_hash() == d2.schema_hash()
    assert l1.equals(l2), np.nanmax(np.abs(l1.pos - l2.pos))
    assert D.hpwl(d1, l1) == pytest.approx(D.hpwl(d2, l2), rel=0, abs=0)
    assert d1.is_macro.sum() == 6 and d1.is_io.sum() == 10 and d1.is_fixed.sum() == 10


def test_bookshelf_perturbed_roundtrip(tmp_path):
    des0, lay0 = synth.make_design(seed=4, n_macros=5, n_cells=80, n_io=8)
    aux = synth.write_bookshelf(des0, lay0, tmp_path / "src", name="t")
    d1, l1 = bookshelf.load_bookshelf(aux)
    rng = np.random.default_rng(0)
    mv = np.flatnonzero(~d1.is_fixed)
    # integer lower-left corners are representable exactly in bookshelf
    ll = np.round(d1.to_abs(l1.pos) - d1.size / 2)
    ll[mv] += rng.integers(-20, 20, (len(mv), 2))
    l1.pos = d1.to_norm(ll + d1.size / 2)
    aux2 = bookshelf.write_bookshelf_copy(d1, l1, tmp_path / "rt", name="t")
    d2, l2 = bookshelf.load_bookshelf(aux2)
    assert l1.equals(l2)


# ---------------------------------------------------------------- DEF (needs the HA-PR eda/ copy)
@pytest.mark.skipif(not HAVE_SPM, reason="HA-PR eda/ spm DEFs not available")
@pytest.mark.parametrize("def_path", SPM, ids=["placement", "cts", "routing"])
def test_def_hpwl_equals_lef_def(def_path):
    from heurbridge._eda import harness
    lef_def = harness("lef_def")
    des, lay = defio.load_def_design(def_path, [LEF], pin_fallback="origin")
    ref = lef_def.def_metrics(def_path, LEF, 1, 1)
    assert des.source["pin_misses"] == ref["pin_misses"] == 0
    h = D.hpwl(des, lay, convention="lef_def_v1")
    # lef_def rounds to 3 decimals; relative tolerance 1e-6 per the task spec
    assert h == pytest.approx(ref["hpwl_um"], rel=1e-6)


@pytest.mark.skipif(not HAVE_SPM, reason="HA-PR eda/ spm DEFs not available")
def test_def_roundtrip_identity(tmp_path):
    des, lay = defio.load_def_design(SPM[1], [LEF])
    out = defio.write_def(des, lay, tmp_path / "rt.def")
    des2, lay2 = defio.load_def_design(out, [LEF])
    assert des.schema_hash() == des2.schema_hash()
    assert lay.equals(lay2)
    # perturb movable cells on the DBU grid + flip orientations, then round-trip
    rng = np.random.default_rng(0)
    mv = np.flatnonzero(~des.is_fixed & lay.placed)
    ll = D.centres_abs(des, lay) - O.effective_size(des.size, lay.orient) / 2
    ll[mv] += rng.integers(-50, 50, (len(mv), 2)) / des.dbu
    lay.orient[mv] = rng.choice([O.R0, O.MX, O.MY, O.R180], len(mv))
    ll = np.round(ll * des.dbu) / des.dbu
    lay.pos = des.to_norm(ll + O.effective_size(des.size, lay.orient) / 2)
    out = defio.write_def(des, lay, tmp_path / "rt2.def")
    des3, lay3 = defio.load_def_design(out, [LEF])
    assert lay.equals(lay3)


# ---------------------------------------------------------------- contract
def test_contract_checks():
    des, lay = synth.make_design(seed=5, n_macros=4, n_cells=40, n_io=6)
    ref = lay.copy()
    contract.check(des, lay, ref, stage="ok")
    bad = lay.copy()
    bad.pos[des.is_fixed] += 0.01
    with pytest.raises(contract.ContractViolation, match="fixed"):
        contract.check(des, bad, ref, stage="M")
    bad = lay.copy()
    bad.pos[0] = [1.5, 0.5]
    with pytest.raises(contract.ContractViolation, match="range"):
        contract.check(des, bad, ref, stage="M")
    bad = lay.copy()
    bad.orient[0] = 9
    with pytest.raises(contract.ContractViolation, match="orient"):
        contract.check(des, bad, ref, stage="M")
    bad = lay.copy()
    bad.schema = "0" * 16
    with pytest.raises(contract.ContractViolation, match="schema"):
        contract.check(des, bad, ref, stage="M")
    # macro stage may not move cells
    macro_scope = des.is_macro & ~des.is_fixed
    bad = lay.copy()
    bad.pos[~des.is_macro & ~des.is_fixed] += 0.001
    with pytest.raises(contract.ContractViolation, match="keep"):
        contract.check(des, bad, ref, stage="M", scope=macro_scope)
    rep = contract.check(des, bad, ref, stage="M", scope=macro_scope, raise_on_fail=False)
    assert not rep.ok and rep.checks["keep"] is False
