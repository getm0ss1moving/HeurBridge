"""T7.1 V5 promotion gate (alpha spending) and H8 null injection; V3 recompute consistency."""

import numpy as np

from heurbridge.core import synth
from heurbridge.core import design as D
from heurbridge.stats.alpha_ledger import AlphaLedger
from heurbridge.verify import gates as G


def test_promotion_and_null_injection(tmp_path):
    L = AlphaLedger(tmp_path / "ledger.jsonl", campaign="t", alpha=0.05)
    rng = np.random.default_rng(0)
    inc = rng.uniform(1.0, 2.0, 30)
    good = inc * 0.9
    r = G.promote(L, "bridge", "ckpt_a", good, inc)
    assert r["promoted"] and r["alpha_j"] == 0.025
    bad = inc.copy()
    bad[:10] = np.inf                                   # failures count as +inf, never dropped
    assert not G.promote(L, "bridge", "ckpt_b", bad, inc)["promoted"]
    L2 = AlphaLedger(tmp_path / "ledger2.jsonl", campaign="h8", alpha=0.05)
    res = G.null_injection(L2, inc, lambda g: inc + g.normal(0, 0.05, len(inc)), n_placebo=50)
    assert res["promoted"] <= 3 and res["rate"] <= 0.05 + 1e-9


def test_recompute_consistency():
    des, lay = synth.make_design(seed=5, n_macros=3, n_cells=30, n_io=4)
    h = D.hpwl(des, lay)
    assert G.recompute_consistency(h * (1 + 1e-5), des, lay)["ok"]
    assert not G.recompute_consistency(h * 1.01, des, lay)["ok"]
