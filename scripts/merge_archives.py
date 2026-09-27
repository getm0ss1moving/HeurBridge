#!/usr/bin/env python3
"""Merge elite archives written by parallel campaign streams with disjoint designs (e.g. seedA_dp_s1 / _s2).

  python scripts/merge_archives.py --out archive_A0_trackA --inputs archive_A0_trackA_s1 archive_A0_trackA_s2

Each input's elite rows are re-inserted in their original id order through Archive.insert, so every design's
admission sequence is replayed exactly (inputs must not share a design: the merge refuses otherwise).  Macro-stage
archives only (upstream ids would need remapping).  Prints the per-input counts and the merged snapshot id.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heurbridge.archive.store import Archive, Candidate, load_layout  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--inputs", nargs="+", required=True)
    ap.add_argument("--min-fidelity", type=int, default=1)
    a = ap.parse_args()
    seen = {}
    rows = []
    for src in a.inputs:
        c = sqlite3.connect(Path(src) / "db" / "archive.sqlite")
        c.row_factory = sqlite3.Row
        rr = [dict(r) for r in c.execute("SELECT * FROM elites ORDER BY id")]
        c.close()
        for r in rr:
            if r["upstream"]:
                sys.exit("%s: row %d has upstream ids; only macro-stage archives can be merged" % (src, r["id"]))
            if seen.setdefault(r["design_id"], src) != src:
                sys.exit("design %s is in both %s and %s" % (r["design_id"], seen[r["design_id"]], src))
        rows.append((src, rr))
    out = Archive(a.out, min_fidelity=a.min_fidelity)
    if out.count():
        sys.exit("%s is not empty" % a.out)
    for src, rr in rows:
        admitted = 0
        for r in rr:
            ok, why = out.insert(Candidate(
                design_id=r["design_id"], stage=r["stage"], layout=load_layout(Path(src) / r["layout_path"]),
                fidelity=int(r["fidelity"]), J=float(r["J"]), admissible=True,
                metrics=json.loads(r["metrics_json"]), gates=json.loads(r["gates_json"]),
                provenance=dict(json.loads(r["provenance_json"]), merged_from=str(src), source_id=r["id"]),
                verified_at=r["verified_at"]))
            admitted += ok
        print(json.dumps({"input": str(src), "rows": len(rr), "admitted": admitted}), flush=True)
    print(json.dumps({"merged": a.out, "entries": out.count(), "snapshot": out.snapshot("merged")}))


if __name__ == "__main__":
    main()
