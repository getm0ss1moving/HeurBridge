"""T2.6: elite archive admission rules and Lemma 3 (monotone best J) as a property test."""

import math

import numpy as np
from hypothesis import given, settings, strategies as st

from heurbridge.archive.store import Archive, Candidate
from heurbridge.core import synth

DES, LAY = synth.make_design(seed=0, n_macros=4, n_cells=20, n_io=4)


def cand(J, fid=2, ok=True, jitter=0.0, design="d", stage="M", up=()):
    l = LAY.copy()
    l.pos[0, 0] = 0.5 + jitter
    return Candidate(design_id=design, stage=stage, layout=l, fidelity=fid, J=J, admissible=ok,
                     metrics={"J": J}, gates={}, provenance={"seed": 0}, upstream_ids=up)


def test_admission_rules(tmp_path):
    a = Archive(tmp_path, k=3)
    assert a.insert(cand(1.0, fid=1)) == (False, "fidelity<2")
    assert a.insert(cand(1.0, ok=False)) == (False, "inadmissible")
    assert a.insert(cand(math.inf)) == (False, "inadmissible")
    assert a.insert(cand(1.0, jitter=0.01))[0]
    assert a.insert(cand(1.0, jitter=0.01)) == (False, "duplicate")
    for j, x in [(0.9, 0.02), (1.1, 0.03)]:
        assert a.insert(cand(j, jitter=x))[0]
    ok, why = a.insert(cand(1.2, jitter=0.04))          # worse than the 3rd best (1.1)
    assert not ok and why.startswith("not_better_than_kth")
    assert a.insert(cand(0.95, jitter=0.05))[0]
    top = a.topk("d", "M")
    assert [round(t["J"], 3) for t in top] == [0.9, 0.95, 1.0]
    assert np.array_equal(a.layout(top[0]).pos, cand(0.9, jitter=0.02).layout.pos)
    # conditional elites are keyed by their upstream set
    assert a.insert(cand(2.0, stage="C", up=(1,), jitter=0.06))[0]
    assert a.insert(cand(1.5, stage="C", up=(2,), jitter=0.07))[0]
    assert [e["J"] for e in a.conditional("d", "C", 1)] == [2.0]
    s1, s2 = a.snapshot("A0"), a.snapshot("A0")
    assert s1 == s2 and (tmp_path / "snapshots" / (s1 + ".sqlite")).exists()


@settings(max_examples=40, deadline=None)
@given(st.lists(st.tuples(st.floats(0.5, 2.0), st.integers(0, 3), st.booleans(), st.integers(0, 2)), min_size=1, max_size=40))
def test_best_J_non_increasing(tmp_path_factory, seq):
    a = Archive(tmp_path_factory.mktemp("arch"), k=5)
    best = {d: math.inf for d in range(3)}
    for t, (J, fid, ok, d) in enumerate(seq):
        a.insert(cand(J, fid=fid, ok=ok, jitter=1e-4 * t, design="d%d" % d))
        for dd in range(3):
            b = a.best_J("d%d" % dd, "M")
            assert b <= best[dd]
            best[dd] = b
        assert len(a.topk("d%d" % d, "M")) <= 5
