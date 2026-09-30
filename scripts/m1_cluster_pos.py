#!/usr/bin/env python3
"""Post-placement cluster targets for the seeding baselines (bridge training data fix, 30 Sep).

Every Track-A archive elite carries the cluster centroids DREAMPlace produced when it was scored
(``routes['cluster_pos']``), which the bridge learns as its sketch of the cell stage -- except the seeding baseline
(provenance program BASELINE: DREAMPlace's own macro placement, M1), whose records were scored without the clustering.
For it ``archive_elites`` fell back to a quadratic placement, and it is the lowest-J elite on most designs, so it
carries most of the pair weight.  This scores each baseline layout once more with the same Track-A f1 (DREAMPlace GP +
LG, macros fixed) and the clustering, and stores the centroids with the elite id; J is recorded next to the archive's.

  python scripts/m1_cluster_pos.py --designs ibm01,ibm02,... --runs runs/seed_trackA_dp --archive archive_A0_trackA \
      --out runs/m1_cluster_pos
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heurbridge.archive.store import Archive  # noqa: E402
from heurbridge.eval import cost  # noqa: E402
from heurbridge.pipeline.evaluators import track_a_final  # noqa: E402


def main():
    from train_bridge import load_bundle
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--designs", required=True)
    ap.add_argument("--runs", default="runs/seed_trackA_dp")
    ap.add_argument("--archive", default="archive_A0_trackA")
    ap.add_argument("--out", default="runs/m1_cluster_pos")
    ap.add_argument("--k", type=int, default=5, help="elites per design considered (as in training)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    arch = Archive(a.archive, min_fidelity=1)
    for name in a.designs.split(","):
        b = load_bundle(a.suite, name, a.runs)
        final = track_a_final("dreamplace", cluster_of=b.cluster_of)
        baseline = cost.Baseline.from_records(b.design.id, json.loads((Path(a.runs) / b.design.id / "baseline.json").read_text())["records"])
        ids, cps, Js, Ja = [], [], [], []
        for e in arch.topk(b.design.id, "M", a.k):
            lay = arch.layout(e)
            if (lay.routes or {}).get("cluster_pos") is not None:
                continue
            rec = final.evaluate(b.design, lay, "%s.elite%d" % (name, int(e["id"])), out / "work")
            if rec.get("cluster_pos") is None:
                print(json.dumps({"design": name, "elite": int(e["id"]), "failure": rec.get("failure")}), flush=True)
                continue
            c = final.score(rec, baseline)
            ids.append(int(e["id"]))
            cps.append(np.asarray(rec["cluster_pos"], np.float64))
            Js.append(float(c.J_inf))
            Ja.append(float(e["J"]))
            print(json.dumps({"design": name, "elite": int(e["id"]), "program": (e.get("provenance") or {}).get("program"),
                              "J_now": round(float(c.J_inf), 6), "J_archive": round(float(e["J"]), 6)}), flush=True)
        if ids:
            np.savez(out / (b.design.id + ".npz"), elite_ids=np.asarray(ids), cluster_pos=np.stack(cps),
                     J=np.asarray(Js), J_archive=np.asarray(Ja))


if __name__ == "__main__":
    main()
