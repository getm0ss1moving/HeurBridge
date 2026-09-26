"""T7.2 / T7.3: paired statistics and the alpha-spending ledger."""

import math

import numpy as np
import pytest

from heurbridge.stats import paired as P
from heurbridge.stats.alpha_ledger import AlphaLedger


def test_wilcoxon_direction_and_inf():
    rng = np.random.default_rng(0)
    base = rng.uniform(1, 2, 30)
    better = base * 0.95
    r = P.wilcoxon_less(better, base)
    assert r["p"] < 1e-6 and r["frac_better"] == 1.0
    assert P.wilcoxon_less(base, better)["p"] > 0.99
    # failures of the method are counted as +inf cost, never dropped
    worse = better.copy()
    worse[:20] = math.inf
    assert P.wilcoxon_less(worse, base)["p"] > 0.5
    both = np.full(5, math.inf)
    assert P.wilcoxon_less(both, both)["p"] == 1.0


def test_holm_hand_example():
    h = P.holm({"a": 0.01, "b": 0.04, "c": 0.03}, alpha=0.05)
    assert h["a"]["reject"] and not h["c"]["reject"] and not h["b"]["reject"]
    assert h["a"]["p_adj"] == pytest.approx(0.03)
    assert h["c"]["p_adj"] == pytest.approx(0.06) and h["b"]["p_adj"] == pytest.approx(0.06)


def test_geomean_ratio_and_floor():
    rng = np.random.default_rng(1)
    base = rng.uniform(1, 3, 40)
    r = P.geomean_ratio(base * 0.9, base, strata=["f%d" % (i % 3) for i in range(40)], n_boot=2000)
    assert r["ratio"] == pytest.approx(0.9) and r["ci"][0] == pytest.approx(0.9) and r["meaningful"]
    r = P.geomean_ratio(base * 0.999, base, n_boot=500)
    assert not r["meaningful"]
    m = base.copy()
    m[0] = math.inf
    assert P.geomean_ratio(m, base, n_boot=200)["n_excluded_inf"] == 1


def test_clopper_pearson_and_page():
    lo, hi = P.clopper_pearson(0, 50)
    assert lo == 0.0 and hi == pytest.approx(0.0711, abs=5e-4)
    data = np.array([[1, 2, 3, 4], [1, 3, 2, 4], [2, 1, 3, 4], [1, 2, 4, 3], [1, 2, 3, 5]], float)
    assert P.page_trend(data)["p"] < 0.01


def test_alpha_ledger(tmp_path):
    L = AlphaLedger(tmp_path / "alpha_ledger.jsonl", campaign="macro_ibm", alpha=0.05)
    e1 = L.reserve("program", "sha:aaa", "wilcoxon_less")
    e2 = L.reserve("bridge", "ckpt:bbb", "wilcoxon_less")
    assert e1["alpha_j"] == pytest.approx(0.025) and e2["alpha_j"] == pytest.approx(0.0125)
    r1 = L.record(e1, p_value=0.01, n=30)
    r2 = L.record(e2, p_value=0.02, n=30)
    assert r1["promoted"] and not r2["promoted"]
    other = AlphaLedger(tmp_path / "alpha_ledger.jsonl", campaign="other")
    assert other.reserve("program", "x", "t")["j"] == 1          # campaigns are independent
    s = L.summary()
    assert s["tests"] == 2 and s["promoted"] == 1 and s["spent"] < 0.05 and s["open"] == []


def test_mmd2_small_samples():
    import math
    from heurbridge.stats.paired import mmd2
    X = np.array([[0.0, 0.0], [1.0, 0.0]])
    r = mmd2(X, np.array([[0.5, 3.0]]))                  # one sample on one side: the U-statistic is undefined
    assert math.isnan(r["mmd2"]) and r["mmd2_biased"] >= 0.0
    r = mmd2(X, X + 0.0)                                  # identical samples
    assert abs(r["mmd2_biased"]) < 1e-12 and r["mmd2"] <= 1e-12
    rng = np.random.default_rng(0)
    far = mmd2(rng.normal(0, 1, (30, 3)), rng.normal(3, 1, (30, 3)))
    near = mmd2(rng.normal(0, 1, (30, 3)), rng.normal(0, 1, (30, 3)))
    assert far["mmd2"] > near["mmd2"] and far["mmd2_biased"] > near["mmd2_biased"]
