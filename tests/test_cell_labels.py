"""make_cell_labels.collect: per-placement parts gathered into one file per design."""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from make_cell_labels import collect  # noqa: E402


def part(d, sid, ok, C=4, N=6, M=2, seed=0):
    rng = np.random.default_rng(seed)
    row = {"id": sid, "kind": "src", "failure": None if ok else "no_placement"}
    arrays = {}
    if ok:
        arrays = {"cluster_pos": rng.random((C, 2), np.float32), "cluster_cov": rng.random((C, 3), np.float32),
                  "cluster_area": np.full(C, 0.1, np.float32), "density": rng.random((8, 8)).astype(np.float16),
                  "cells": rng.random((N, 2)).astype(np.float16), "cell_index": np.arange(N, dtype=np.int32),
                  "macros": rng.random((M, 2), np.float32), "macro_orient": np.zeros(M, np.int8)}
    np.savez(d / (sid + ".npz"), row=np.array(json.dumps(row)), **arrays)


def test_collect_stacks_labelled_parts_and_keeps_failures(tmp_path):
    parts = tmp_path / "parts"
    parts.mkdir()
    part(parts, "a", True, seed=1)
    part(parts, "b", False)
    part(parts, "c", True, seed=2)
    (parts / "d.tmp.npz").write_bytes(b"unfinished")                          # an interrupted write is skipped
    n = collect(parts, tmp_path / "x.npz")
    z = np.load(tmp_path / "x.npz")
    rows = json.loads(str(z["rows"]))
    assert n == 3 and [r["id"] for r in rows] == ["a", "b", "c"]
    assert [r.get("k") for r in rows] == [0, None, 1]                           # index into the stacked arrays
    assert z["cluster_pos"].shape == (2, 4, 2) and z["cells"].shape == (2, 6, 2)
    assert z["cluster_area"].shape == (4,) and z["cell_index"].shape == (6,)    # per design, stored once
    c = np.load(parts / "c.npz")
    assert np.array_equal(z["cluster_pos"][1], c["cluster_pos"])
