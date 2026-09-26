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
    """Lemma 3 within each fidelity (J at different fidelities has different baselines; the default query
    follows the highest fidelity present and may switch tiers when a verified elite arrives)."""
    a = Archive(tmp_path_factory.mktemp("arch"), k=5)
    best = {(d, f): math.inf for d in range(3) for f in (2, 3)}
    for t, (J, fid, ok, d) in enumerate(seq):
        a.insert(cand(J, fid=fid, ok=ok, jitter=1e-4 * t, design="d%d" % d))
        for dd in range(3):
            for f in (2, 3):
                b = a.best_J("d%d" % dd, "M", fidelity=f)
                assert b <= best[(dd, f)]
                best[(dd, f)] = b
        for f in (2, 3):
            assert len(a.topk("d%d" % d, "M", fidelity=f)) <= 5


def test_fidelities_ranked_separately(tmp_path):
    """J at f1 and f2 have different baselines: a verified f2 elite never competes with f1 entries, and the
    queries use the highest fidelity present unless asked otherwise."""
    from heurbridge.archive.store import Archive, Candidate
    from heurbridge.core import synth
    des, lay = synth.make_design(seed=4, n_macros=3, n_cells=10, n_io=4)
    arch = Archive(tmp_path / "a", k=2, min_fidelity=1)

    def cand(J, fid, shift):
        l = lay.copy()
        l.pos[0, 0] = 0.1 + shift
        return Candidate(design_id=des.id, stage="M", layout=l, fidelity=fid, J=J, admissible=True, metrics={},
                         gates={}, provenance={})
    assert arch.insert(cand(0.80, 1, 0.01))[0] and arch.insert(cand(0.81, 1, 0.02))[0]
    assert arch.topk(des.id, "M")[0]["fidelity"] == 1 and arch.best_J(des.id, "M") == 0.80
    assert arch.insert(cand(0.99, 2, 0.03))[0]                    # admitted although 0.99 > the f1 top-2
    assert [e["fidelity"] for e in arch.topk(des.id, "M")] == [2] and arch.best_J(des.id, "M") == 0.99
    assert [e["J"] for e in arch.topk(des.id, "M", fidelity=1)] == [0.80, 0.81]
    assert arch.insert(cand(0.97, 2, 0.04))[0] and not arch.insert(cand(0.995, 2, 0.05))[0]   # f2 top-2 is full
    arch3 = Archive(tmp_path / "b", k=5, min_fidelity=1)                 # the same layout verified at a higher fidelity
    assert arch3.insert(cand(0.80, 1, 0.01))[0] and arch3.insert(cand(0.98, 2, 0.01))[0]
    assert arch3.insert(cand(0.98, 2, 0.01)) == (False, "duplicate")
