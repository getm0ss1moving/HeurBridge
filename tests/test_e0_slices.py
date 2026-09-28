"""E0 components split over processes: slice bounds, one budget per component, and the combine checks."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import e0_combine  # noqa: E402
from run_e0 import component_budget, slice_bounds  # noqa: E402


def test_slice_bounds_partition():
    for n in (0, 1, 5, 50, 65):
        for m in (1, 2, 3, 4, 7):
            parts = [slice_bounds(n, "%d/%d" % (k, m)) for k in range(m)]
            assert parts[0][0] == 0 and parts[-1][1] == n
            assert all(parts[i][1] == parts[i + 1][0] for i in range(m - 1))      # contiguous, no overlap
    assert slice_bounds(65, "") == (0, 65)
    assert slice_bounds(65, "0/3") == (0, 22)
    with pytest.raises(ValueError):
        slice_bounds(10, "3/3")


class _Cot:
    """Stand-in co-trained partner: fixed wall time and displacement per layout."""
    def __init__(self):
        self.calls = 0

    def __call__(self, design, layout, rng):
        self.calls += 1
        return SimpleNamespace(wall_s=10.0 + layout, info={"disp": 0.1 * layout})

    def displacement(self, layout):
        return 0.1 * layout


def test_component_budget_measured_then_shared(tmp_path):
    b = SimpleNamespace(design=SimpleNamespace(id="d1"))
    srcs = [("p", s, s) for s in range(8)]                  # the layout stand-in is a number
    cot = _Cot()
    a = SimpleNamespace(budget_s=0.0)
    got = component_budget(a, b, cot, srcs, tmp_path)
    assert got == (12.0, pytest.approx(0.2), "measured") and cot.calls == 5   # median over the first five
    again = component_budget(a, b, _Cot(), srcs, tmp_path)                     # a slice: read, not re-measured
    assert again[:2] == got[:2] and again[2] == "cache:measured"


def test_component_budget_given(tmp_path):
    b = SimpleNamespace(design=SimpleNamespace(id="d1"))
    cot = _Cot()
    got = component_budget(SimpleNamespace(budget_s=332.051), b, cot, [("p", s, s) for s in range(8)], tmp_path)
    assert got == (332.051, pytest.approx(0.2), "given") and cot.calls == 0    # no timed probe
    assert json.loads((tmp_path / "budget_d1.json").read_text())["disp"] == pytest.approx([0, .1, .2, .3, .4])


def _run(tmp_path, name, rows):
    d = tmp_path / name
    d.mkdir()
    (d / "e0_rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    cfg = {"guard_fidelity": "f1", "equal_guard": False, "random_control": True, "final": "dreamplace",
           "bridge_sha256_16": "x", "frozen": "f", "K": 20, "suite": "ispd2005", "seeds": 5, "designs": "d1"}
    (d / "meta.json").write_text(json.dumps({"config": cfg}))
    return str(d)


def _row(prog, seed, partner, J, budget=100.0):
    return {"design": "d1", "program": prog, "seed": seed, "partner": partner, "J": J, "budget_s": budget}


def test_combine_rejects_overlapping_slices(tmp_path, monkeypatch):
    r1 = _run(tmp_path, "s0", [_row("p", 0, "cotrained", 1.0), _row("p", 0, "none", 2.0)])
    r2 = _run(tmp_path, "s1", [_row("p", 0, "cotrained", 1.1), _row("p", 0, "none", 2.0)])
    monkeypatch.setattr(sys, "argv", ["e0_combine.py", "--runs", r1, r2, "--out", str(tmp_path / "out")])
    with pytest.raises(SystemExit, match="duplicate"):
        e0_combine.main()


def test_combine_rejects_mixed_budgets(tmp_path, monkeypatch):
    r1 = _run(tmp_path, "s0", [_row("p", 0, "cotrained", 1.0), _row("p", 0, "none", 2.0)])
    r2 = _run(tmp_path, "s1", [_row("q", 0, "cotrained", 1.0, 90.0), _row("q", 0, "none", 2.0, 90.0)])
    monkeypatch.setattr(sys, "argv", ["e0_combine.py", "--runs", r1, r2, "--out", str(tmp_path / "out")])
    with pytest.raises(SystemExit, match="budget"):
        e0_combine.main()
