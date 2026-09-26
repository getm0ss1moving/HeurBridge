#!/usr/bin/env python3
"""E3-lite, f1 -> f2 on a Track-B development design (T6.2; open decision 9 on timing gates at f1).

  python scripts/calibrate_f1_f2.py --design bp_fe_top

Pairs every f2 row of runs/seed_miniflow/<design>/evals_f2.jsonl (written by run_f2_miniflow.py) with its f1
row: rank agreement of J before the gates (Spearman / Kendall, top-k recall), the gate agreement (does passing the
f1 setup/hold gates predict passing the f2 gates?), and per-term f1 -> f2 changes.  Development evidence only.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heurbridge import reporting  # noqa: E402
from heurbridge.stats import calibration as C  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", default="bp_fe_top")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    rdir = ROOT / "runs" / "seed_miniflow" / a.design
    f1 = {json.loads(l)["run_id"]: json.loads(l) for l in (rdir / "evals.jsonl").read_text().splitlines()}
    f2 = [json.loads(l) for l in (rdir / "evals_f2.jsonl").read_text().splitlines()]
    base2 = json.loads((rdir / "baseline_f2.json").read_text())["records"][0]
    base1 = json.loads((rdir / "baseline.json").read_text())["records"][0]
    pairs, failed = [], []
    for r in f2:
        r1 = f1.get(r.get("f1_run_id"))
        if r.get("status") != "ok" or r1 is None:
            failed.append((r["run_id"], (r.get("record") or {}).get("failure") or r.get("error")))
            continue
        g1 = all((r1.get("gates") or {}).get(k, {}).get("status") == "pass" for k in ("setup", "hold"))
        g2 = all((r.get("gates") or {}).get(k, {}).get("status") == "pass" for k in ("setup", "hold", "drc"))
        rec1, rec2 = r1.get("record") or {}, r.get("record") or {}
        pairs.append({"run_id": r["run_id"], "program": r.get("program"), "J1": r1["J_raw"], "J2": r["J_raw"],
                      "gate1": g1, "gate2": g2, "wns1": rec1.get("setup_wns_ns"), "wns2": rec2.get("setup_wns_ns"),
                      "tns1": rec1.get("setup_tns_ns"), "tns2": rec2.get("setup_tns_ns"), "drc2": rec2.get("drc_violations")})
    J1 = np.array([p["J1"] for p in pairs])
    J2 = np.array([p["J2"] for p in pairs])
    st = C.per_design(J1, J2, k=5) if len(pairs) >= 3 else {"n": len(pairs)}
    agree = [(p["gate1"], p["gate2"]) for p in pairs]
    tab = ["| layout | program | f1 J | f2 J | f1 gates | f2 gates | setup WNS f1 -> f2 (ns) | TNS f1 -> f2 (ns) | DRC |",
           "|---|---|---|---|---|---|---|---|---|"]
    for p in sorted(pairs, key=lambda p: p["J1"]):
        tab.append("| %s | %s | %.4f | %.4f | %s | %s | %.3f -> %.3f | %.1f -> %.1f | %s |" % (
            p["run_id"].replace(".f2", ""), p["program"], p["J1"], p["J2"], "pass" if p["gate1"] else "fail",
            "pass" if p["gate2"] else "fail", p["wns1"], p["wns2"], p["tns1"], p["tns2"], p["drc2"]))
    n11 = sum(1 for a1, a2 in agree if a1 and a2)
    n10 = sum(1 for a1, a2 in agree if a1 and not a2)
    n01 = sum(1 for a1, a2 in agree if not a1 and a2)
    n00 = sum(1 for a1, a2 in agree if not a1 and not a2)
    res = ["**Baselines (M1):** f1 setup WNS %.3f ns / TNS %.1f ns; f2 setup WNS %.3f ns / TNS %.1f ns, DRC %s, detailed WL "
           "%.0f um, %s vias." % (base1["setup_wns_ns"], base1["setup_tns_ns"], base2["setup_wns_ns"], base2["setup_tns_ns"],
                                  base2.get("drc_violations"), base2.get("detailed_wirelength_um"), base2.get("vias")), "",
           "\n".join(tab), "",
           "**Rank agreement of J before the gates (f1 vs f2, %d layouts):** Spearman %s, Kendall %s, top-5 recall %s." % (
               len(pairs), *("%.3f" % st[k] if k in st else "-" for k in ("spearman", "kendall", "top5_recall"))),
           "**Gate agreement (setup/hold at f1 vs setup/hold/DRC at f2):** pass->pass %d, pass->fail %d, fail->pass %d, "
           "fail->fail %d." % (n11, n10, n01, n00)]
    out = a.out or str(ROOT / "reports" / ("E3_calibration_dev_%s_f1f2.md" % a.design))
    reporting.render({
        "title": "E3-lite f1 -> f2 calibration on %s (development, Track B)" % a.design,
        "report_id": "f1f2_%s" % a.design, "node": "local (macOS; OpenLane container, 6 vCPU)",
        "track": "B-dev (mini-flow f1: placement-stage timing; f2: CTS + repair_timing + DRT + OpenRCX)",
        "tools": "OpenROAD b16bda7e (efabless/openlane:master-arm64v8)",
        "gate": "G0 (T6.2) for (M, f1 -> f2) — development evidence; decision 9 (timing gates at f1)",
        "samples": "%d layouts with f1 and f2 (f1 top by J before the gates + an even spread over the f1 range); "
                   "M1 baseline at f2 x %d" % (len(pairs), len(json.loads((rdir / "baseline_f2.json").read_text())["records"])),
        "failures": "\n".join("- %s: %s" % f for f in failed) or "none",
        "commands": "python scripts/run_f2_miniflow.py --design nangate45/%s --top 8 --spread 6 --base-runs 2\n"
                    "python scripts/calibrate_f1_f2.py --design %s" % (a.design, a.design),
        "results": "\n".join(res),
        "notes": "J before the gates is normalized per fidelity by that fidelity's M1 baseline (f1: 4 terms, M1 = 0.95; f2: "
                 "5 terms, M1 = 1.00). f2 gates: setup/hold WNS within 0.02 ns of M1 at f2 and DRC = 0 (frozen rule B.3)."},
        gate_passed=None, out=out)
    print("REPORT_OK", out)


if __name__ == "__main__":
    main()
