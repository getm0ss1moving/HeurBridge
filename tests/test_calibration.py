"""T6.2: calibration statistics, gate G0 and conformal intervals on synthetic proxies."""

import numpy as np
import yaml

from heurbridge.stats import calibration as C


def make_rows(noise, n_designs=9, n=60, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(n_designs):
        s = rng.uniform(0.9, 1.3, n)
        p = s + noise * rng.normal(size=n)
        rows += [{"design": "d%d" % d, "J_proxy": p[i], "J_signoff": s[i]} for i in range(n)]
    return rows


def test_gate_passes_for_good_proxy_and_fails_for_bad():
    good = C.study(make_rows(0.01), ["J"])["J"]
    bad = C.study(make_rows(0.5), ["J"])["J"]
    g1, g2 = C.gate_g0(good, "M", "f1"), C.gate_g0(bad, "M", "f1")
    assert g1.admissible and g1.kendall_J > 0.8
    assert not g2.admissible and g2.regret > 0.25 * g2.regret_random


def test_conformal_coverage():
    rows = make_rows(0.05, n_designs=20, seed=1)
    p = np.array([r["J_proxy"] for r in rows])
    s = np.array([r["J_signoff"] for r in rows])
    d = np.array([r["design"] for r in rows])
    predict, info = C.isotonic_conformal(p, s, d, level=0.9)
    rows2 = make_rows(0.05, n_designs=10, seed=2)
    p2 = np.array([r["J_proxy"] for r in rows2])
    s2 = np.array([r["J_signoff"] for r in rows2])
    lo, mid, hi = predict(p2)
    cover = np.mean((s2 >= lo) & (s2 <= hi))
    assert 0.85 <= cover <= 0.97, cover


def test_write_admissible(tmp_path):
    res = [C.gate_g0(C.study(make_rows(0.01), ["J"])["J"], "M", "f1"),
           C.gate_g0(C.study(make_rows(0.5), ["J"])["J"], "C", "f1")]
    C.write_admissible(res, tmp_path / "fid.yaml")
    doc = yaml.safe_load((tmp_path / "fid.yaml").read_text())
    assert doc["stages"]["M"]["fitness_fidelity"] == "f1" and doc["stages"]["C"]["fitness_fidelity"] == "f2"
