"""T2.1: sandbox contract — accepted programs, rejected/contained escapes, determinism and MR1."""

import numpy as np
import pytest

from heurbridge.core import synth
from heurbridge.evolve import sandbox as SB

DES, LAY = synth.make_design(seed=0, n_macros=6, n_cells=30, n_io=6)
SCOPE = DES.is_macro & ~DES.is_fixed

GOOD = '''
import numpy as np
def heuristic(design, upstream, rng):
    pos = np.array(design.init_pos, dtype=float)
    order = [i for i in design.canonical_order if design.is_macro[i] and design.movable[i]]
    for i in order:                       # randomness drawn in canonical (label-free) order
        pos[i] = rng.uniform(0.2, 0.8, 2)
    return pos
'''

NOT_EQUIVARIANT = '''
import numpy as np
def heuristic(design, upstream, rng):
    pos = np.array(design.init_pos, dtype=float)
    idx = design.macro_idx                # index order depends on labelling
    pos[idx] = rng.uniform(0.2, 0.8, (len(idx), 2))
    return pos
'''

NONDET = '''
import numpy as np
def heuristic(design, upstream, rng):
    r = np.random.default_rng()           # unseeded: OS entropy
    pos = np.array(design.init_pos, dtype=float)
    pos[design.macro_idx] = r.uniform(0.2, 0.8, (len(design.macro_idx), 2))
    return pos
'''


def test_good_program_certifies():
    cert = SB.certify(GOOD, DES, LAY, SCOPE, seeds=(0, 1))
    assert cert.ok, cert.reasons
    assert cert.checks == {"ast": True, "determinism": True, "mr1": True}


@pytest.mark.parametrize("src,frag", [
    ("import os\ndef heuristic(d,u,r):\n    return d.init_pos", "import os"),
    ("def heuristic(d,u,r):\n    open('x','w')\n    return d.init_pos", "name open"),
    ("import numpy as np\ndef heuristic(d,u,r):\n    return np.load('x.npy')", "attribute .load"),
    ("def heuristic(d,u,r):\n    return getattr(d,'init_pos')", "name getattr"),
    ("def heuristic(d,u,r):\n    return ().__class__.__bases__[0].__subclasses__()", "attribute .__class__"),
    ("from scipy import io\ndef heuristic(d,u,r):\n    return d.init_pos", "from scipy import io"),
    ("import networkx as nx\ndef heuristic(d,u,r):\n    nx.write_gml(None,'x')\n    return d.init_pos", "attribute .write_gml"),
    ("def f(d,u,r):\n    return d.init_pos", "no function 'heuristic'"),
])
def test_static_rejections(src, frag):
    v = SB.check_source(src)
    assert any(frag in x for x in v), v
    assert SB.run_program(src, SB.make_view(DES, LAY), None, 0).status == "rejected"


def test_runtime_containment_and_errors():
    view = SB.make_view(DES, LAY)
    # the AST cannot see this: numpy internals opening a file are stopped by the audit hook
    sneaky = "import numpy as np\ndef heuristic(d,u,r):\n    f = np.DataSource\n    return d.init_pos"
    assert SB.run_program(sneaky, view, None, 0).status == "rejected"      # DataSource is a forbidden attr
    loop = "def heuristic(d,u,r):\n    x = 0\n    while True:\n        x += 1\n"
    r = SB.run_program(loop, view, None, 0, cpu_s=2, wall_s=15)
    assert r.status == "timeout"
    err = "def heuristic(d,u,r):\n    raise ValueError('boom')\n"
    r = SB.run_program(err, view, None, 0)
    assert r.status == "error" and "boom" in r.error
    write = "import numpy as np\ndef heuristic(d,u,r):\n    d.size[0,0] = 1.0\n    return d.init_pos\n"
    r = SB.run_program(write, view, None, 0)
    assert r.status == "error" and "read-only" in r.error


def test_output_validation():
    bad_shape = "import numpy as np\ndef heuristic(d,u,r):\n    return np.zeros((3,2))\n"
    cert = SB.certify(bad_shape, DES, LAY, SCOPE, check_mr1=False)
    assert not cert.ok and "shape" in cert.reasons[0]
    move_fixed = ("import numpy as np\ndef heuristic(d,u,r):\n    p = np.array(d.init_pos)\n"
                  "    p[d.is_fixed] = 0.5\n    return p\n")
    cert = SB.certify(move_fixed, DES, LAY, SCOPE, check_mr1=False)
    assert not cert.ok and "outside the stage scope" in cert.reasons[0]


def test_determinism_and_mr1_failures():
    cert = SB.certify(NONDET, DES, LAY, SCOPE, check_mr1=False)
    assert not cert.ok and "non-deterministic" in cert.reasons[0]
    cert = SB.certify(NOT_EQUIVARIANT, DES, LAY, SCOPE)
    assert not cert.ok and cert.checks.get("mr1") is False


def test_store_program(tmp_path):
    p = SB.store_program(GOOD, tmp_path, meta={"family": "M7"})
    assert p.name == SB.program_hash(GOOD) + ".py" and p.read_text() == GOOD


def test_certify_with_unplaced_cells():
    """Real designs carry unplaced cells as NaN rows in every output; identical runs must certify
    (regression: the determinism check compared NaN != NaN and rejected every program)."""
    lay = LAY.copy()
    cells = ~DES.is_macro & ~DES.is_io & ~DES.is_fixed
    lay.pos[cells] = np.nan
    cert = SB.certify(GOOD, DES, lay, SCOPE, seeds=(0,))
    assert cert.ok, cert.reasons
    assert cert.checks["determinism"]
    cert = SB.certify(NONDET, DES, lay, SCOPE, check_mr1=False)       # a real non-determinism is still caught
    assert not cert.ok and "non-deterministic" in cert.reasons[0]
