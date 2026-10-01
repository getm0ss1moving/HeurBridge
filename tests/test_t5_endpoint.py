"""T5 demo endpoint (scripts/eval_t5_portfolio.py): portfolio choice and per-unit portfolio J."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def test_portfolio_rule_and_units():
    import eval_t5_portfolio as T
    pop = {"programs": {
        "a": {"B": [1.0, 2.0], "sha256": "sa"},
        "b": {"B": [2.0, 1.0], "sha256": "sb"},
        "c": {"B": [3.0, float("inf")], "sha256": "sc"},           # a failed design counts as 1e6, never best
        "a@i1": {"B": [0.1, 0.1], "sha256": "sa"},                 # island clones are excluded
        "d": {"B": [], "sha256": "sd"}}}                           # never evaluated: excluded
    port = T.portfolio(pop, q=2)
    assert sorted(port) == [("a", "sa"), ("b", "sb")]
    rows = {("sa", "x", 0): {"J_post": 0.5}, ("sb", "x", 0): {"J_post": 0.4},
            ("sa", "x", 1): {"J_post": float("inf")}, ("sb", "x", 1): {"J_post": float("inf")}}
    u = T.unit_table(rows, port, ["x"], 2)
    assert u[0] == 0.4 and np.isinf(u[1])                         # min over members; all failed -> +inf


def test_decision_rule(tmp_path):
    """scripts/t5_demo_decision.py: R1-R5 from the arms' files and the V summary (pre-registered rule)."""
    import json
    import t5_demo_decision as D
    hb, ctrl, val = tmp_path / "hb", tmp_path / "ctrl", tmp_path / "V"
    for d in (hb, ctrl, val):
        d.mkdir()
    seeds = {"s%d" % i: {"B": [0.50, 0.50], "sha256": "x%d" % i, "generation": 0} for i in range(2)}
    kids = {"g1.k%d" % i: {"B": [0.40, 0.45] if i < 3 else [float("inf"), 0.5], "sha256": "k%d" % i, "generation": 1}
            for i in range(4)}
    (hb / "population_g0.json").write_text(json.dumps({"programs": seeds}))
    (hb / "population_g1.json").write_text(json.dumps({"programs": {**seeds, **kids}}))
    (hb / "meta.json").write_text(json.dumps({"config": {"generations": 1, "parents": 2, "children": 2, "budget": 10,
                                                         "split": "t"}}))
    (hb / "events.jsonl").write_text(json.dumps({"kind": "child", "id": "g1.k0"}) + "\n")
    led = tmp_path / "ledger.jsonl"
    led.write_text("\n".join(json.dumps({"budget_scope": "M/t", "status": "ok"}) for _ in range(4)) + "\n")
    (val / "summary.json").write_text(json.dumps({
        "designs": ["a", "b"], "mean_J": {"seed": 0.5, "hb": 0.45, "ctrl": 0.48},
        "per_design": {"seed": {"a": [0.5] * 3, "b": [0.5] * 3}, "hb": {"a": [0.4, 0.45, 0.5], "b": [0.45, 0.46, 0.44]},
                       "ctrl": {"a": [0.48] * 3, "b": [0.48] * 3}}}))
    r = D.rules(hb, ctrl, val, led)
    assert r["R1"]["share"] == 0.75 and r["R1"]["pass"]           # 3 of 4 attempts evaluated with finite costs
    assert r["R2"]["pass"] and r["R3"]["units_lower"] == 5 and r["R3"]["pass"] and r["R4"]["pass"] and r["R5"]["pass"]
    assert r["propose_full_campaign"]
