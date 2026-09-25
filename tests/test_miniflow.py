"""Mini-flow (local Track-B development f1): script structure, log parsing, failure naming."""

from pathlib import Path

import pytest

from heurbridge.eval import miniflow as MF

GRT = """[INFO GRT-0096] Final congestion report:
Layer         Resource        Demand        Usage (%)    Max H / Max V / Total Overflow
---------------------------------------------------------------------------------------
metal2          333569        109193           32.73%             0 /  0 /  0
---------------------------------------------------------------------------------------
Total          2419448        733534           30.32%             3 /  5 /  12

[INFO GRT-0018] Total wirelength: 1799231 um
"""

POWER = """Group                  Internal  Switching    Leakage      Total
                          Power      Power      Power      Power (Watts)
----------------------------------------------------------------
Total                  1.01e-01   1.77e-02   9.15e-03   %s 100.0%%
"""


def _log(gr_ok=True, done=True):
    parts = ["HB_CHECK_PLACEMENT 1", "HB_WNS_PLACE -2.12", "HB_TNS_PLACE -82.5", "HB_HOLD_PLACE 0.086",
             "HB_POWER_PLACE_BEGIN", POWER % "1.28e-01", "HB_POWER_PLACE_END", GRT, "HB_RUNTIME_MS 70000",
             "HB_F1_CORE_DONE"]
    if gr_ok is None:                            # bad_alloc: OpenSTA prints this and exits the process
        return "\n".join(parts + ["", "Error: out of memory."]) + "\n"
    if gr_ok:
        parts += ["HB_WNS_GR -2.20", "HB_TNS_GR -310.9", "HB_HOLD_GR 0.087", "HB_POWER_GR_BEGIN",
                  POWER % "1.31e-01", "HB_POWER_GR_END"]
    else:
        parts += ["HB_GR_PARASITICS_FAIL out of memory."]
    if done:
        parts += ["HB_F1_DONE"]
    return "\n".join(parts) + "\n"


def _cfg():
    p = MF.Nangate45("/flow")
    d = MF.DesignCfg(name="x", top="top", verilog=["a.v"], sdc="c.sdc", macro_libs=["m.lib"])
    return p, d


def test_script_order_and_optional_gr_timing():
    p, d = _cfg()
    s = MF.f1_script(p, d, Path("/w/fp.odb"), Path("/w/macros.tcl"), Path("/w"), threads=6, gr_timing=True)
    keys = ["global_placement", "repair_design", "detailed_placement", "HB_WNS_PLACE", "HB_POWER_PLACE_BEGIN",
            "global_route", "HB_RUNTIME_MS", "write_def", "HB_F1_CORE_DONE", "estimate_parasitics -global_routing",
            "HB_F1_DONE"]
    i = {k: s.index(k) for k in keys}
    assert sorted(i, key=i.get) == keys
    assert "catch {estimate_parasitics -global_routing" in s     # a GR-parasitics failure is not fatal
    assert "set_thread_count 6" in s and "source /w/macros.tcl" in s
    assert "-global_routing" not in MF.f1_script(p, d, Path("/w/fp.odb"), None, Path("/w"))   # opt-in


def test_metrics_place_stage_is_default():
    m = MF.f1_metrics(_log())
    assert m["timing_stage"] == "place"
    assert (m["setup_wns_ns"], m["setup_tns_ns"], m["hold_wns_ns"]) == (-2.12, -82.5, 0.086)
    assert m["total_power_w"] == pytest.approx(0.128) and m["power_gr_w"] == pytest.approx(0.131)
    assert (m["wns_gr"], m["tns_gr"], m["hold_gr"]) == (-2.20, -310.9, 0.087)
    assert m["gr_wl"] == 1799231 and m["gr_overflow_total"] == 12 and m["gr_overflow_max"] == 5
    assert m["runtime_s"] == 70.0 and m["gr_parasitics_error"] is None


def test_metrics_gr_stage_and_gr_failure():
    m = MF.f1_metrics(_log(), "gr")
    assert (m["setup_wns_ns"], m["setup_tns_ns"], m["total_power_w"]) == (-2.20, -310.9, pytest.approx(0.131))
    bad = _log(gr_ok=False)
    m = MF.f1_metrics(bad)                       # place-stage values survive a GR-parasitics failure
    assert m["setup_tns_ns"] == -82.5 and m["gr_parasitics_error"] == "out of memory."
    m = MF.f1_metrics(bad, "gr")                 # ... and the GR stage is reported missing, never guessed
    assert m["setup_wns_ns"] is None and m["total_power_w"] is None
    with pytest.raises(ValueError):
        MF.f1_metrics(bad, "signoff")


def test_failure_names():
    assert MF.classify_failure(0, _log()) is None
    assert MF.classify_failure(0, _log(gr_ok=False)) is None          # recorded in gr_parasitics_error
    assert MF.classify_failure(0, _log(done=False)).startswith("returncode_0")
    assert MF.classify_failure(1, "x\nError: out of memory.\n").startswith("tool_oom")
    a = ("stl_vector.h:1125: reference std::vector<gpl::Bin>::operator[](size_type): "
         "Assertion '__n < this->size()' failed.")
    assert MF.classify_failure(133, a).startswith("tool_assertion")
    assert MF.classify_failure(139, "") == "segfault"
    assert MF.classify_failure("timeout", "") == "timeout"
    assert MF.classify_failure(1, "[ERROR GPL-0305] RePlAce diverged.").startswith("tool_error: [ERROR GPL-0305]")


def test_io_exclusions_and_orfs_config(tmp_path):
    io = tmp_path / "io.tcl"
    io.write_text("exclude_io_pin_region -region left:* -region top:10-20\n")
    assert MF.io_exclusions(str(io)) == "-exclude left:* -exclude top:10-20"
    assert MF.io_exclusions(None) == "" and MF.io_exclusions(str(tmp_path / "missing.tcl")) == ""
    ddir = tmp_path / "designs" / "nangate45" / "toy"
    ddir.mkdir(parents=True)
    (ddir / "config.mk").write_text(
        "export DESIGN_NAME = toy_top\nexport PLATFORM = nangate45\n"
        "export VERILOG_FILES = $(DESIGN_HOME)/src/toy/a.v \\\n    $(DESIGN_HOME)/src/toy/b.v\n"
        "export SDC_FILE = $(DESIGN_HOME)/$(PLATFORM)/toy/constraint.sdc\n"
        "export CORE_UTILIZATION ?= 35\nexport MACRO_PLACE_HALO = 7 9\n")
    c = MF.from_orfs(str(tmp_path), "nangate45/toy")
    assert c.top == "toy_top" and c.utilization == 35 and c.halo == (7.0, 9.0)
    assert c.verilog == [str(tmp_path / "designs" / "src/toy/a.v"), str(tmp_path / "designs" / "src/toy/b.v")]
    assert c.sdc == str(tmp_path / "designs" / "nangate45/toy/constraint.sdc")


def test_outcome_gr_stage_failure_after_core_values():
    oom = _log(gr_ok=None)
    m, failure, rc = MF.f1_outcome(1, oom, "place")          # optional GR timing died: f1 is complete
    assert (failure, rc) == (None, 0) and m["setup_tns_ns"] == -82.5
    assert m["gr_parasitics_error"].startswith("tool_oom")
    m, failure, rc = MF.f1_outcome(1, oom, "gr")             # ... but not when GR timing is the f1 timing
    assert failure.startswith("tool_oom") and rc == 1 and MF.should_retry(rc, failure)
    early = "HB_CHECK_PLACEMENT 1\nError: out of memory.\n"   # before the core values: a failed run
    m, failure, rc = MF.f1_outcome(1, early, "place")
    assert failure.startswith("tool_oom") and rc == 1 and MF.should_retry(rc, failure)
    assert MF.should_retry(139, "segfault") and not MF.should_retry(133, "tool_assertion: x")
    assert MF.f1_outcome(0, _log(), "place")[1:] == (None, 0)


def test_orfs_order_tapcell_pdn_and_supply_ports():
    p, d = _cfg()
    d.tapcell_tcl, d.pdn_tcl, d.fastroute_tcl, d.dont_use = "/p/tapcell.tcl", "/p/pdn.tcl", "/d/fastroute.tcl", ("X1",)
    s = MF.f1_script(p, d, Path("/w/fp.odb"), Path("/w/macros.tcl"), Path("/w"))
    keys = ["set_dont_use {X1}", "source /w/macros.tcl", "setPlacementStatus FIRM", "source /p/tapcell.tcl",
            "source /p/pdn.tcl", "pdngen", "odb::dbBTerm_destroy", "source /d/fastroute.tcl", "global_placement",
            "buffer_ports", "HB_POWER_PLACE_BEGIN", "global_route"]
    i = {k: s.index(k) for k in keys}
    assert sorted(i, key=i.get) == keys
    d.pdn_tcl = None                                   # no grid: no supply ports to drop
    assert "dbBTerm_destroy" not in MF.f1_script(p, d, Path("/w/fp.odb"), None, Path("/w"))


F2_LOG = """HB_CHECK_PLACEMENT 1
HB_CTS_DONE
""" + GRT + """HB_GRT_DONE
[INFO DRT-0199]   Number of violations = 57.
[INFO DRT-0199]   Number of violations = 3.
[INFO DRT-0198] Complete detail routing.
Total wire length = 2101234 um.
Total number of vias = 245678.
HB_DRT_DONE
HB_WNS_F2 -0.41
HB_TNS_F2 -12.5
HB_HOLD_F2 0.031
HB_POWER_F2_BEGIN
""" + POWER % "1.52e-01" + """HB_POWER_F2_END
HB_RUNTIME_MS 1800000
HB_F2_DONE
"""


def test_f2_script_order_and_metrics():
    p, d = _cfg()
    s = MF.f2_script(p, d, Path("/w/fp.odb"), Path("/w/macros.tcl"), Path("/w"), threads=6)
    keys = ["global_placement", "detailed_placement", "clock_tree_synthesis", "set_propagated_clock", "repair_timing",
            "global_route", "detailed_route", "filler_placement", "extract_parasitics", "read_spef", "HB_WNS_F2",
            "HB_POWER_F2_BEGIN", "HB_F2_DONE"]
    i = {k: s.index(k) for k in keys}
    assert sorted(i, key=i.get) == keys
    assert "repair_timing" not in MF.f2_script(p, d, Path("/w/fp.odb"), None, Path("/w"), repair_timing=False)
    m = MF.f2_metrics(F2_LOG)
    assert m["drc_violations"] == 3 and m["detailed_wirelength_um"] == 2101234 and m["vias"] == 245678
    assert (m["setup_wns_ns"], m["setup_tns_ns"], m["hold_wns_ns"]) == (-0.41, -12.5, 0.031)
    assert m["total_power_w"] == pytest.approx(0.152) and m["gr_overflow_total"] == 12 and m["done"]
    assert m["runtime_s"] == 1800.0 and m["repair_timing_error"] is None
    m = MF.f2_metrics(F2_LOG.replace("HB_F2_DONE\n", "").replace("Number of violations = 3.", ""))
    assert not m["done"] and m["drc_violations"] == 57     # the last reported count, never a guess
