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
