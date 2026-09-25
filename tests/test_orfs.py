"""T1.4/T1.5 Track B glue: macro placement Tcl round trip and ORFS metric mapping."""

import numpy as np

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
    assert "-exact" in txt


def test_metric_mapping_first_candidate_wins():
    meta = {"finish__timing__setup__ws": "-0.25", "finish__timing__hold__ws": 0.03, "finish__timing__setup__tns": -4.5,
            "finish__power__total": 0.12, "detailedroute__route__wirelength": 123456, "detailedroute__route__drc_errors": 0,
            "globalroute__timing__setup__ws": -0.3, "detailedroute__timing__setup__ws": -0.9}
    m = orfs.map_metrics(meta)
    assert m["setup_wns_ns"] == -0.25 and m["metric_sources"]["setup_wns_ns"] == "finish__timing__setup__ws"
    assert m["hold_wns_ns"] == 0.03 and m["drc_violations"] == 0 and m["detailed_wirelength_um"] == 123456
    assert "vias" not in m                                   # missing -> absent -> 'unchecked' downstream


def test_command_and_dirs():
    r = orfs.OrfsRun(flow_dir="/f/flow", design_config="/f/flow/designs/nangate45/ariane133/config.mk", variant="hb_x",
                     macro_tcl="/tmp/m.tcl", stage="grt")
    c = r.command()
    assert "MACRO_PLACEMENT_TCL=/tmp/m.tcl" in c and c[-1] == "globalroute" and "FLOW_VARIANT=hb_x" in c
    assert str(r.dirs()["logs"]).endswith("logs/nangate45/ariane133/hb_x")
