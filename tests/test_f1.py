"""T1.4: f1 script generation, log parsing, Track-A stand-in on ibm01."""

from pathlib import Path

import numpy as np
import pytest

from heurbridge.eval import f1

LOG = """
[INFO GPL-0002] DBU: 2000
HB_CHECK_PLACEMENT 1
HB_WNS_PLACE -0.512
HB_TNS_PLACE -12.75
[INFO GRT-0096] Final congestion report:
Layer         Resource        Demand        Usage (%)    Max H / Max V / Total Overflow
---------------------------------------------------------------------------------------
metal1           31235          2459            7.87%             0 /  0 /  0
metal2           52310         20210           38.64%             3 /  1 / 17
---------------------------------------------------------------------------------------
Total           182330         36842           20.21%             3 /  1 / 17

[INFO GRT-0018] Total wirelength: 71466 um
HB_WNS_GR -0.601
HB_TNS_GR -15.5
HB_RUNTIME_MS 12345
"""


def test_parse_log():
    m = f1.parse_f1_log(LOG)
    assert m["gr_overflow_total"] == 17 and m["gr_overflow_max"] == 3 and m["gr_wl"] == 71466
    assert m["wns_place"] == -0.512 and m["tns_gr"] == -15.5 and m["runtime_s"] == 12.345
    assert m["check_placement_ok"] is True
    empty = f1.parse_f1_log("nothing here")
    assert all(empty[k] is None for k in f1.KEYS)


def test_tcl_contents(tmp_path):
    job = f1.OpenroadJob(def_path="/x/d.def", lefs=["/x/t.lef", "/x/c.lef"], libs=["/x/c.lib"], sdc="/x/d.sdc",
                         min_layer="metal2", max_layer="metal10")
    t = f1.make_f1_tcl(job, tmp_path)
    for s in ("read_lef /x/t.lef", "read_def /x/d.def", "setPlacementStatus FIRM", "-routability_driven",
              "-timing_driven", "detailed_placement", "check_placement", "estimate_parasitics -placement",
              "global_route -congestion_iterations 30", "estimate_parasitics -global_routing",
              "set_routing_layers -signal metal2-metal10"):
        assert s in t, s
    t2 = f1.make_f1_tcl(f1.OpenroadJob(def_path="/x/d.def", lefs=["/x/t.lef"]), tmp_path)
    assert "-timing_driven" not in t2 and "HB_TIMING unchecked" in t2


IBM01 = Path(__file__).resolve().parents[1] / "benchmarks/ibm_bookshelf/ibm01/ibm01.aux"


@pytest.mark.skipif(not IBM01.exists(), reason="IBM benchmark not downloaded")
def test_trackA_hbgp_ibm01():
    from heurbridge.core import bookshelf
    d, l = bookshelf.load_bookshelf(IBM01, family="ibm")
    out, placed = f1.run_hbgp_f1(d, l)
    assert out["backend"] == "hbgp" and out["gp"]["overflow"] < 0.1
    assert 1.5e6 < out["hpwl"] < 4e6                       # reference .pl: 2.44e6
    assert "wns_place" in out["unchecked"] and out["wns_place"] is None


def test_hbgp_f1_reproducible_single_thread():
    """Two HB-GP evaluations of the same layout are bit-identical (the default runs on one thread)."""
    import torch
    from heurbridge.core import synth
    from heurbridge.eval.f1 import run_hbgp_f1
    from heurbridge.eval.gp import GPConfig
    des, ref = synth.make_design(seed=3, n_macros=4, n_cells=300, n_io=12)
    lay = ref.copy()
    lay.pos[~des.is_macro & ~des.is_io & ~des.is_fixed] = np.nan
    cfg = GPConfig(iters=150)
    prev = torch.get_num_threads()
    a, _ = run_hbgp_f1(des, lay, cfg)
    b, _ = run_hbgp_f1(des, lay, cfg)
    assert a["hpwl"] == b["hpwl"] and a["gp"]["threads"] == 1
    assert torch.get_num_threads() == prev                     # the caller's setting is restored
