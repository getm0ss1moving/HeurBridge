"""T2.2: the macro seed population passes the program contract (V0) and yields P_M-legal layouts."""

import numpy as np
import pytest

from heurbridge.core import project, synth
from heurbridge.evolve import sandbox as SB
from heurbridge.heuristics.cell.cluster import cluster_cells
from heurbridge.heuristics.macro.registry import FAMILIES, all_programs

PROGRAMS = all_programs()
DES, LAY = synth.make_design(seed=31, n_macros=10, n_cells=120, n_io=12)
CL = cluster_cells(DES, n=12)
SCOPE = DES.is_macro & ~DES.is_fixed
PROBE = synth.make_design(seed=32, n_macros=6, n_cells=40, n_io=6)


def test_population_size_and_families():
    fams = {p["family"] for p in PROGRAMS}
    assert fams == set(FAMILIES) and len(fams) + 1 >= 7            # + M1 (tool wrapper) = 7 families
    assert all(2 <= len(v[2]) <= 3 for v in FAMILIES.values())
    assert len({p["sha256"] for p in PROGRAMS}) == len(PROGRAMS)


@pytest.mark.parametrize("prog", PROGRAMS, ids=[p["id"] for p in PROGRAMS])
def test_program_certifies(prog):
    cert = SB.certify(prog["source"], DES, LAY, SCOPE, seeds=(0, 1), probe=PROBE, cluster=CL)
    assert cert.ok, cert.reasons
    r = SB.run_program(prog["source"], SB.make_view(DES, LAY, CL), None, 3)
    out, rep = project.legalize_macros(DES, SB.to_layout(DES, LAY, r))
    assert rep.ok and project.check_macros(DES, out)["ok"]
