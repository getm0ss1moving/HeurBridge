#!/usr/bin/env python3
"""Track-B development f2 (T1.5 / T2.7 verification / E3-lite f1 vs f2) with the local mini-flow.

  python scripts/run_f2_miniflow.py --design nangate45/bp_fe_top --top 10 --spread 10 [--base-runs 1]

Selection from the f1 campaign (runs/seed_miniflow/<design>/evals.jsonl, rows with a finite J before the
gates): the --top best by f1 J (T2.7: top 10 to f2) and --spread more rows evenly spaced in f1-J rank (for
the f1 -> f2 calibration).  The M1 baseline is evaluated --base-runs times at f2 (T1.7 median).  Every f2
evaluation is appended to evals_f2.jsonl (resumable); rows that pass every f2 gate are inserted into the
archive at fidelity 2.  Development flow (OpenLane OpenROAD b16bda7e): no claim follows from it.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heurbridge.archive.store import Archive, Candidate  # noqa: E402
from heurbridge.core import orient as O  # noqa: E402
from heurbridge.core.defio import load_def_design  # noqa: E402
from heurbridge.eval import cost, miniflow as MF  # noqa: E402
from heurbridge.eval.orfs import parse_macro_tcl  # noqa: E402
from heurbridge.meta import write_meta  # noqa: E402
from heurbridge.pipeline.evaluators import MiniflowF2Evaluator  # noqa: E402
from heurbridge.pipeline.seed_archive import Ledger, _eval, _layout_from_row, distinct  # noqa: E402

FLOW = ROOT / "third_party" / "OpenROAD-flow-scripts" / "flow"


def select(rows, top, spread):
    fin = distinct(sorted([r for r in rows if r.get("status") == "ok" and r.get("J_raw") is not None
                           and math.isfinite(r["J_raw"]) and r["run_id"].endswith(".f1")], key=lambda r: r["J_raw"]))
    pick = fin[:top]
    rest = fin[top:]
    if spread and rest:
        idx = np.unique(np.linspace(0, len(rest) - 1, min(spread, len(rest))).round().astype(int))
        pick += [rest[i] for i in idx]
    return pick


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", default="nangate45/bp_fe_top")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--spread", type=int, default=10)
    ap.add_argument("--base-runs", type=int, default=1)
    ap.add_argument("--archive", default=str(ROOT / "archive_dev_trackB"))
    ap.add_argument("--no-repair-timing", action="store_true")
    a = ap.parse_args()
    name = a.design.split("/")[-1]
    w = ROOT / "runs" / "miniflow" / name
    p, d = MF.Nangate45(str(FLOW)), MF.from_orfs(str(FLOW), a.design)
    des, lay = load_def_design(str(w / "fp.hb.def"), [str(p.tech_lef), str(p.sc_lef)] + d.macro_lefs,
                               family="orfs_cpu", tech="nangate45")
    m1 = lay.copy()
    idx = {n: i for i, n in enumerate(des.names)}
    for inst, (x, y, o) in parse_macro_tcl((w / "m1_macros.tcl").read_text()).items():
        i = idx[inst]
        m1.orient[i] = O.from_odb(o)
        eff = O.effective_size(des.size[i:i + 1], m1.orient[i:i + 1])[0]
        m1.pos[i] = des.to_norm(np.array([x, y]) + eff / 2)
    rdir = ROOT / "runs" / "seed_miniflow" / des.id
    ev = MiniflowF2Evaluator(flow_dir=str(FLOW), platform_design=a.design, fp_odb=str(w / "fp.odb"),
                             repair_timing=not a.no_repair_timing)
    bpath = rdir / "baseline_f2.json"
    if bpath.exists():
        recs = json.loads(bpath.read_text())["records"]
    else:
        recs = [ev.evaluate(des, m1, "baseline_m1_f2" + ("" if k == 0 else "_r%d" % k), rdir / "work_f2")
                for k in range(a.base_runs)]
        keys = ("detailed_wirelength_um", "vias", "drc_violations", "setup_wns_ns", "setup_tns_ns", "hold_wns_ns",
                "total_power_w")
        same = all(r.get(k) == recs[0].get(k) for r in recs for k in keys)
        bpath.write_text(json.dumps({"records": recs, "deterministic": same, "threads": ev.threads}, indent=1, default=str))
        print(json.dumps({"baseline_f2": [{k: r.get(k) for k in keys + ("failure", "wall_s")} for r in recs],
                          "deterministic": same}), flush=True)
    ok_base = [r for r in recs if r.get("returncode") == 0]
    if not ok_base:
        print(json.dumps({"error": "baseline f2 failed", "failures": [r.get("failure") for r in recs]}))
        sys.exit(1)
    baseline = cost.Baseline.from_records(des.id, ok_base)
    rows = [json.loads(l) for l in (rdir / "evals.jsonl").read_text().splitlines()]
    pick = select(rows, a.top, a.spread)
    ledger = Ledger(rdir / "evals_f2.jsonl")
    arch = Archive(a.archive, min_fidelity=1)
    out = []
    for r in pick:
        lay_r = _layout_from_row(des, lay, r)
        rid = r["run_id"][:-3] + ".f2"
        row = _eval(ev, des, lay_r, baseline, rid, rdir / "work_f2", ledger,
                    {"program": r.get("program"), "seed": r.get("seed"), "stage": "M", "f1_J": r["J"],
                     "f1_J_raw": r["J_raw"], "f1_run_id": r["run_id"]})
        out.append(row)
        if row.get("status") == "ok" and math.isfinite(row["J"]):
            arch.insert(Candidate(design_id=des.id, stage="M", layout=lay_r, fidelity=2, J=row["J"],
                                  admissible=row.get("admissible", False), metrics=row.get("record", {}),
                                  gates=row.get("gates", {}), provenance={"program": r.get("program"), "seed": r.get("seed"),
                                                                           "run_id": rid, "f1_run_id": r["run_id"]}))
        print(json.dumps({"run_id": rid, "status": row.get("status"), "f1_J_raw": r["J_raw"], "f2_J": row.get("J"),
                          "f2_J_raw": row.get("J_raw"), "failure": (row.get("record") or {}).get("failure")}), flush=True)
    write_meta(rdir / "f2_meta", "f2_miniflow_%s" % des.id, des.id, config=vars(a), baseline_f2=baseline.to_dict(),
               n_selected=len(pick), track="B-dev (local mini-flow f2, OpenLane OpenROAD b16bda7e)")
    print(json.dumps({"f2_done": len(out), "ok": sum(1 for r in out if r.get("status") == "ok")}), flush=True)


if __name__ == "__main__":
    main()
