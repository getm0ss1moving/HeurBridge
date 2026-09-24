from pathlib import Path

import yaml

from heurbridge.eval import cost

ROOT = Path(__file__).resolve().parents[1]


def test_cost_weights_frozen_and_consistent():
    cfg = yaml.safe_load((ROOT / "configs" / "cost.yaml").read_text())
    assert cfg["weights"] == cost.WEIGHTS
    assert abs(sum(cost.WEIGHTS.values()) - 1.0) < 1e-12
    assert cfg["gates"]["setup_wns_guard_ns"] == cost.GUARD_NS


def test_families_have_disjoint_designs():
    fam = yaml.safe_load((ROOT / "configs" / "families.yaml").read_text())["families"]
    seen = {}
    for name, f in fam.items():
        for d in f["designs"]:
            assert d not in seen, (d, name, seen.get(d))
            seen[d] = name
