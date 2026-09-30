"""Demo 2 helpers: whole-site widths for the inflation arms, and the report's merging and de-duplication of rows."""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from demo_sketch_cells import distinct_rows, merged_rows, widened_widths  # noqa: E402


def test_widened_widths_whole_sites():
    rng = np.random.default_rng(3)
    w = rng.choice([2.0, 4.0, 6.0, 8.0, 14.0, 20.0], 20000)
    f = np.where(rng.random(20000) < 0.1, rng.uniform(1.0, 1.3, 20000), 1.0)
    out = widened_widths(w, f)
    assert np.array_equal(out, np.round(out))                                   # DREAMPlace's parser: integers only
    assert np.array_equal(out[f <= 1.0], w[f <= 1.0])                           # untouched cells keep their width
    assert (out >= w).all() and (out <= np.ceil(w * f - 1e-9) + 0).all()
    assert abs((out - w).sum() / (w * (f - 1)).sum() - 1) < 0.03                # the rule's added area in expectation
    assert np.array_equal(out, widened_widths(w, f))                            # fixed seed


def rows_file(d, rows):
    d.mkdir(parents=True, exist_ok=True)
    (d / "rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))


def row(prog, seed, arm, J):
    return {"design": "ibm04", "program": prog, "seed": seed, "arm": arm, "J": J}


def test_merged_rows_rerun_replaces_the_arm(tmp_path):
    rows_file(tmp_path / "a", [row("M1", 0, "centre", 0.5), row("M1", 0, "infl", float("inf")),
                               row("M2", 0, "centre", 0.6), row("M2", 0, "infl", float("inf"))])
    rows_file(tmp_path / "b", [row("M1", 0, "infl", 0.49)])                     # the re-run did not reach M2
    m = {(r["program"], r["arm"]): r["J"] for r in merged_rows(tmp_path / "a", [tmp_path / "b"])}
    assert m == {("M1", "centre"): 0.5, ("M1", "infl"): 0.49, ("M2", "centre"): 0.6}


def test_distinct_rows_drops_exact_repeats_only():
    rows = [row("M1", 0, "centre", 0.5), row("M1", 0, "keep", 0.51), row("M1", 1, "centre", 0.5), row("M1", 1, "keep", 0.51),
            row("M2", 0, "centre", 0.5), row("M2", 0, "keep", 0.52), row("M2", 1, "centre", 0.5), row("M2", 1, "keep", 0.53),
            row("M3", 0, "centre", 0.5), row("M3", 0, "keep", 0.51)]
    out, dropped = distinct_rows(rows)
    assert dropped == 1
    assert {(r["program"], r["seed"]) for r in out} == {("M1", 0), ("M2", 0), ("M2", 1), ("M3", 0)}   # other programs never merge


def test_distinct_rows_shared_arms():
    # the re-run reached seed 1 but not seed 0 of the same layout: one case, with every arm
    rows = [row("M1", 0, "centre", 0.5), row("M1", 0, "keep", 0.51), row("M1", 1, "centre", 0.5), row("M1", 1, "keep", 0.51),
            row("M1", 1, "infl", 0.505)]
    out, dropped = distinct_rows(rows)
    assert dropped == 1
    assert sorted((r["seed"], r["arm"], r["J"]) for r in out) == [(0, "centre", 0.5), (0, "infl", 0.505), (0, "keep", 0.51)]
