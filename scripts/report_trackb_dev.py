#!/usr/bin/env python3
"""Track-B development seeding report (T2.7 on the local mini-flow): reports/T2_trackB_dev_<design>.md

  python scripts/report_trackb_dev.py --design bp_fe_top [--archive archive_dev_trackB]

Reads runs/seed_miniflow/<design>/{baseline.json, evals.jsonl}: baseline repeats and determinism, per
program: evaluations, failures by name, setup/hold gate pass rate, J before the gates (median, best) and
the best gated J; local-search trajectory; archive top-k.  Descriptive development evidence (old OpenROAD
build, f1 = placement-stage timing): no claim.
"""

import argparse
import collections
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heurbridge import reporting  # noqa: E402
from heurbridge.archive.store import Archive  # noqa: E402
from heurbridge.pipeline.seed_archive import distinct  # noqa: E402


def fmt(x, nd=4):
    return "-" if x is None or (isinstance(x, float) and not math.isfinite(x)) else ("%.*f" % (nd, x))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", default="bp_fe_top")
    ap.add_argument("--archive", default=str(ROOT / "archive_dev_trackB"))
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    rdir = ROOT / "runs" / "seed_miniflow" / a.design
    base = json.loads((rdir / "baseline.json").read_text())
    rows = [json.loads(l) for l in (rdir / "evals.jsonl").read_text().splitlines()]
    prog_rows = [r for r in rows if r.get("program") not in (None, "LS")]
    ls_rows = [r for r in rows if r.get("program") == "LS"]
    b0 = base["records"][0]
    J_base = 0.95                   # every term of the M1 baseline is 1 by construction (no via term at f1)
    # failures by name
    fails = collections.Counter()
    for r in rows:
        if r.get("status") != "ok":
            rec = r.get("record") or {}
            name = rec.get("failure") or r.get("error") or r.get("status")
            fails[str(name).split(":")[0] + (": " + str(name).split("]")[0].split("[")[-1] if "[" in str(name) else "")] += 1
    # per program
    by = collections.defaultdict(list)
    for r in prog_rows:
        by[r["program"]].append(r)
    lines = ["| program | evals | failed | gates passed | median J before gates | best J before gates | best gated J |",
             "|---|---|---|---|---|---|---|"]
    for pid in sorted(by):
        rr = by[pid]
        ok = [r for r in rr if r.get("status") == "ok"]
        raw = [r["J_raw"] for r in ok if r.get("J_raw") is not None and math.isfinite(r["J_raw"])]
        gated = [r["J"] for r in ok if math.isfinite(r["J"])]
        lines.append("| %s | %d | %d | %d | %s | %s | %s |" % (pid, len(rr), len(rr) - len(ok), len(gated),
                     fmt(float(np.median(raw))) if raw else "-", fmt(min(raw)) if raw else "-", fmt(min(gated)) if gated else "-"))
    ok_all = [r for r in prog_rows if r.get("status") == "ok"]
    gate_rate = np.mean([math.isfinite(r["J"]) for r in ok_all]) if ok_all else float("nan")
    setup_fail = sum(1 for r in ok_all if ((r.get("gates") or {}).get("setup") or {}).get("status") == "fail")
    hold_fail = sum(1 for r in ok_all if ((r.get("gates") or {}).get("hold") or {}).get("status") == "fail")
    beat = [r for r in ok_all if math.isfinite(r["J"]) and r["J"] < J_base]
    raw_beat = [r for r in ok_all if r.get("J_raw") is not None and r["J_raw"] < J_base]
    of_pos = [r for r in ok_all if ((r.get("record") or {}).get("gr_overflow_total") or 0) > 0]
    res = ["**Baseline (M1, rtl_macro_placer), %d runs, deterministic: %s** — GR WL %s um, GR overflow %s, setup WNS %s ns,"
           " TNS %s ns, hold WNS %s ns, power %s W (J = %.2f by construction)." % (
               len(base["records"]), base.get("deterministic"), fmt(b0.get("gr_wl"), 0), b0.get("gr_overflow_total"),
               fmt(b0.get("setup_wns_ns"), 3), fmt(b0.get("setup_tns_ns"), 1), fmt(b0.get("hold_wns_ns"), 3),
               fmt(b0.get("total_power_w"), 3), J_base),
           "", "**Program evaluations:** %d (%d completed, %d failed); setup/hold gates passed on %d of %d completed "
           "(%.0f%%; setup failures %d, hold failures %d); layouts with GR overflow > 0: %d." % (
               len(prog_rows), len(ok_all), len(prog_rows) - len(ok_all), sum(math.isfinite(r["J"]) for r in ok_all),
               len(ok_all), 100 * gate_rate, setup_fail, hold_fail, len(of_pos)),
           "Below the baseline J %.2f: %d layouts after the gates (%d distinct), %d before the gates (%d distinct); "
           "completed layouts: %d distinct of %d (seed-independent programs repeat their layout)." % (
               J_base, len(beat), len(distinct(beat)), len(raw_beat), len(distinct(raw_beat)), len(distinct(ok_all)), len(ok_all)),
           "", "\n".join(lines)]
    if ls_rows:
        traj = []
        best = None
        for r in ls_rows:
            if r.get("status") == "ok" and math.isfinite(r["J"]) and (best is None or r["J"] < best):
                best = r["J"]
            traj.append(best)
        res += ["", "**Local search** (T2.7, %d evaluations): best gated J after each step: %s." % (
            len(ls_rows), ", ".join(fmt(x) for x in traj[5::6]) or "-")]
    arch_txt = "no archive"
    if Path(a.archive).exists():
        top = Archive(a.archive, min_fidelity=1).topk(a.design, "M")
        arch_txt = "; ".join("%s J=%s (f%d)" % ((e.get("provenance") or {}).get("program") or (e.get("provenance") or {}).get("run_id"),
                                                 fmt(e["J"]), e["fidelity"]) for e in top)
    res += ["", "**Archive top-%s (fidelity 1, development):** %s." % ("k", arch_txt)]
    out = a.out or str(ROOT / "reports" / ("T2_trackB_dev_%s.md" % a.design))
    reporting.render({
        "title": "Track-B development seeding (T2.7) on %s — local mini-flow f1" % a.design,
        "report_id": "trackB_dev_%s" % a.design, "node": "local (macOS; OpenLane container, 6 vCPU)",
        "track": "B-dev (ORFS-aligned mini-flow, OpenROAD b16bda7e; f1 timing from placement parasitics)",
        "tools": "OpenROAD b16bda7e, Yosys 0.38 (efabless/openlane:master-arm64v8)",
        "gate": "T2 exit (archive A0) — development only; the pre-registered A0 is built at f2 on the server",
        "samples": "%d program evaluations (16 programs x seeds), %d local-search evaluations, baseline x %d" % (
            len(prog_rows), len(ls_rows), len(base["records"])),
        "failures": "\n".join("- %s: %d" % kv for kv in fails.most_common()) or "none",
        "commands": "python scripts/run_seed_miniflow.py --design nangate45/%s --seeds 5 --top 10 --ls 8\n"
                    "python scripts/report_trackb_dev.py --design %s" % (a.design, a.design),
        "results": "\n".join(res),
        "notes": "J before the gates ranks every completed layout; the gated J is +inf when the setup or hold WNS "
                 "is worse than the baseline by more than 0.02 ns (frozen rule B.3). Superseded rows of earlier flow "
                 "versions are kept under runs/seed_miniflow/%s/superseded_*." % a.design},
        gate_passed=None, out=out)
    print("REPORT_OK", out)


if __name__ == "__main__":
    main()
