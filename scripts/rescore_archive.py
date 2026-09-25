#!/usr/bin/env python3
"""Rebuild a development archive from stored evaluation records after a cost-proxy change.

  python scripts/rescore_archive.py --runs runs/seed_dev --designs ibm01,ibm02,ibm03 --out archive_dev_v2

Every f1 row of <runs>/<design>/evals.jsonl is re-scored from its stored record (no tool re-run), the
baseline layout is admitted as an initial elite, and rows are inserted in their original order, so the
archive is exactly what the campaign would have produced under the new cost.  Development use only.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heurbridge.archive.store import Archive, Candidate  # noqa: E402
from heurbridge.core import bookshelf, project  # noqa: E402
from heurbridge.eval import cost  # noqa: E402
from heurbridge.pipeline.evaluators import HBGPEvaluator  # noqa: E402
from run_seed_archive import SUITES, insert_baseline_elite, macro_stage_layout  # noqa: E402


def with_pct(rec):
    rec = dict(rec)
    if "rudy_overflow_ratio" in rec and "rudy_of_pct" not in rec:
        rec["rudy_of_pct"] = 100.0 * float(rec["rudy_overflow_ratio"])
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--runs", default=str(ROOT / "runs" / "seed_dev"))
    ap.add_argument("--designs", required=True)
    ap.add_argument("--out", default=str(ROOT / "archive_dev_v2"))
    a = ap.parse_args()
    arch = Archive(a.out, min_fidelity=1)
    ev = HBGPEvaluator()
    for name in a.designs.split(","):
        d, l = bookshelf.load_bookshelf(SUITES[a.suite] / name / (name + ".aux"), family=a.suite)
        base = macro_stage_layout(d, l)
        bench, _ = project.legalize_macros(d, base)
        rdir = Path(a.runs) / d.id
        recs = [with_pct(r) for r in json.loads((rdir / "baseline.json").read_text())["records"]]
        baseline = cost.Baseline.from_records(d.id, recs)
        cl = np.load(rdir / "clusters.npy")
        if recs[0].get("cluster_pos") is None:
            recs[0]["cluster_pos"] = HBGPEvaluator(cluster_of=cl).evaluate(d, bench, "baseline.cp", rdir)["cluster_pos"]
        insert_baseline_elite(arch, d, bench, recs, baseline, ev)
        mm = d.is_macro & ~d.is_fixed
        n_ins = 0
        for line in (rdir / "evals.jsonl").read_text().splitlines():
            r = json.loads(line)
            if r.get("status") != "ok" or not r["run_id"].endswith(".f1"):
                continue
            rec = with_pct(r["record"])
            c = ev.score(rec, baseline)
            lay = base.copy()
            lay.pos[mm] = np.asarray(r["pos_macros"])
            lay.orient[mm] = np.asarray(r["orient_macros"], dtype=np.int8)
            if rec.get("cluster_pos") is not None:
                lay.routes = {"cluster_pos": np.asarray(rec["cluster_pos"])}
            ok, _ = arch.insert(Candidate(design_id=d.id, stage="M", layout=lay, fidelity=1, J=c.J_inf,
                                          admissible=c.admissible, metrics={k: v for k, v in rec.items() if k != "cluster_pos"},
                                          gates=c.gates, provenance={"program": r.get("program"), "seed": r.get("seed"),
                                                                     "run_id": r["run_id"], "rescored": True}))
            n_ins += ok
        print(json.dumps({"design": d.id, "baseline": baseline.values, "inserted": n_ins,
                          "top": [round(e["J"], 4) for e in arch.topk(d.id, "M")],
                          "top_programs": [e["provenance"].get("program") for e in arch.topk(d.id, "M")]}), flush=True)
    print(json.dumps({"snapshot": arch.snapshot("A0dev_v2")}))


if __name__ == "__main__":
    main()
