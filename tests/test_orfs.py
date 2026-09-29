"""T1.4/T1.5 Track B glue: macro placement Tcl round trip and ORFS metric mapping."""

from pathlib import Path

import numpy as np
import pytest

from heurbridge.core import orient as O, synth
from heurbridge.eval import orfs


def test_macro_tcl_roundtrip():
    des, lay = synth.make_design(seed=40, n_macros=5, n_cells=20, n_io=4, allow_macro_orients=True)
    des.dbu = 1000.0
    txt = orfs.macro_placement_tcl(des, lay)
    got = orfs.parse_macro_tcl(txt)
    mm = np.flatnonzero(des.is_macro & ~des.is_fixed)
    assert set(got) == {des.names[i] for i in mm}
    eff = O.effective_size(des.size, lay.orient)
    ll = des.to_abs(lay.pos) - eff / 2
    for i in mm:
        x, y, o = got[des.names[i]]
        assert abs(x - ll[i, 0]) < 1e-3 and abs(y - ll[i, 1]) < 1e-3
        assert O.from_odb(o) == lay.orient[i]
    assert "-exact" not in txt                       # OpenROAD 2024-12's place_macro has no -exact (probe)
    assert "-exact" in orfs.macro_placement_tcl(des, lay, exact=True)


def test_metric_mapping_first_candidate_wins():
    meta = {"finish__timing__setup__ws": "-0.25", "finish__timing__hold__ws": 0.03, "finish__timing__setup__tns": -4.5,
            "finish__power__total": 0.12, "detailedroute__route__wirelength": 123456, "detailedroute__route__drc_errors": 0,
            "globalroute__timing__setup__ws": -0.3, "detailedroute__timing__setup__ws": -0.9}
    m = orfs.map_metrics(meta)
    assert m["setup_wns_ns"] == -0.25 and m["metric_sources"]["setup_wns_ns"] == "finish__timing__setup__ws"
    assert m["hold_wns_ns"] == 0.03 and m["drc_violations"] == 0 and m["detailed_wirelength_um"] == 123456
    assert "vias" not in m                                   # missing -> absent -> 'unchecked' downstream


ORFS_FLOW = Path(__file__).resolve().parents[1] / "third_party" / "ORFS-2024-12" / "flow"


@pytest.mark.skipif(not (ORFS_FLOW / "Makefile").exists(), reason="needs the ORFS 2024-12 checkout")
def test_command_and_dirs(tmp_path):
    r = orfs.OrfsRun(flow_dir=str(ORFS_FLOW), design_config="./designs/nangate45/bp_fe_top/config.mk", variant="hb_x",
                     macro_tcl="/tmp/m.tcl", stage="finish", work_home=str(tmp_path), base_variant="base")
    d = r.dirs()                                    # ORFS names its directories by DESIGN_NICKNAME (bp_fe)
    assert d["logs"] == tmp_path / "logs" / "nangate45" / "bp_fe" / "hb_x"
    c = r.command(d)
    assert "MACRO_PLACEMENT_TCL=/tmp/m.tcl" in c and "FLOW_VARIANT=hb_x" in c and "WORK_HOME=%s" % tmp_path in c
    assert c[-1] == str(d["logs"] / "6_report.log")            # f2 stops at the report: no GDS / KLayout
    assert "MACRO_PLACEMENT_TCL=/tmp/m.tcl" not in r.make_vars("base")    # the base variant is M1 (rtl_macro_placer)
    base = r.dirs("base")                           # a candidate starts from the base synthesis and floorplan
    base["results"].mkdir(parents=True)
    for f in orfs.OrfsRun.SEED_FILES:
        (base["results"] / f).write_text(f)
    (base["objects"] / "lib").mkdir(parents=True)
    assert r.seed_from_base() == list(orfs.OrfsRun.SEED_FILES)
    assert (d["results"] / "2_2_floorplan_io.odb").read_text() == "2_2_floorplan_io.odb" and (d["objects"] / "lib").is_dir()
    r.stage = "grt"
    assert r.command(d)[-1] == str(d["results"] / "5_1_grt.odb")


def test_failure_reason_names_the_tool_error():
    grt = ("[INFO GRT-0014] Routed nets: 58762\n[ERROR GRT-0116] Global routing finished with congestion. Check the "
           "congestion regions in the DRC Viewer.\nError: global_route.tcl, 110 GRT-0116\nmake[1]: *** "
           "[Makefile:765: do-5_1_grt] Error 1\nmake: *** [Makefile:763: /x/5_1_grt.odb] Error 2\n")
    assert orfs.failure_reason(grt, 2).startswith("GRT-0116 Global routing finished with congestion.")
    killed = "[INFO GRT-0103] Extra Run for hard benchmark.\nmake[1]: *** [Makefile:765: do-5_1_grt] Terminated\n"
    assert orfs.failure_reason(killed, "timeout") == "timeout in 5_1_grt"
    assert orfs.failure_reason("", "timeout") == "timeout"
    assert orfs.failure_reason("make[1]: *** [Makefile:1: do-3_3_place_gp] Error 1\n", 2) == "make returncode 2 in 3_3_place_gp"
    assert orfs.failure_reason("anything", 0) is None


def test_warm_start_places_every_cell():
    """Track-B warm start: every standard cell gets a location (OpenROAD locks placed cells if any stay unplaced),
    at its cluster's quadratic position; a missing name stops the flow with a named error."""
    import re
    import numpy as np
    from heurbridge.core import synth
    from heurbridge.heuristics.cell.cluster import cluster_cells
    from heurbridge.pipeline.evaluators import OrfsEvaluator
    des, ref = synth.make_design(seed=3, n_macros=6, n_cells=200, n_io=10)
    cl = cluster_cells(des, n=16)
    t = OrfsEvaluator(fidelity=1, warm_start="quadratic", cluster_of=cl)._warm_start_tcl(des, ref)
    xy = [(float(a), float(b)) for a, b in re.findall(r"^  \{[^}]+\} ([-0-9.]+) ([-0-9.]+)$", t, re.M)]
    assert len(xy) == int((cl >= 0).sum()) and np.isfinite(np.array(xy)).all()
    assert "setPlacementStatus PLACED" in t and "HB-WARM-START" in t
