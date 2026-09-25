#!/usr/bin/env python3
"""Development calibration of the macro-stage proxy (E3-lite, task T6.2): f0 vs the f1 of a campaign.

  python scripts/calibrate_dev.py --suite ibm --designs ibm01,ibm02,ibm03 --runs runs/seed_dev \
      --out reports/E3_calibration_dev_ibm
  python scripts/calibrate_dev.py --miniflow nangate45/bp_fe_top --runs runs/seed_miniflow \
      --out reports/E3_calibration_dev_bp_fe_top

Proxy  = the f0 surrogate J0 on the clustered design, exactly the scorer the bridge guard uses
         (pipeline/bridge_data.make_bundle -> MacroStageScorer), computed on each row's macro layout.
Target = the stored f1 cost of the same row (no tool re-run): Track A rows are re-scored with the bounded
         overflow proxy (rudy_of_pct); Track B uses J before the gates (J_raw) for the rank study, and the
         gate pass rate is reported separately (a gated row has J = +inf).
Per design: Spearman, Kendall, top-5 recall, decision regret vs random (stats/calibration.per_design);
gate G0 rule (regret <= 25% of random and Kendall >= 0.5).  Development evidence: f1 stands in for
signoff, so this is not the pre-registered E3 study.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heurbridge import reporting  # noqa: E402
from heurbridge.eval import cost  # noqa: E402
from heurbridge.pipeline import bridge_data as BD  # noqa: E402
from heurbridge.pipeline.evaluators import HBGPEvaluator, MiniflowEvaluator  # noqa: E402
from heurbridge.stats import calibration as C  # noqa: E402


def with_pct(rec):
    rec = dict(rec)
    if "rudy_overflow_ratio" in rec and "rudy_of_pct" not in rec:
        rec["rudy_of_pct"] = 100.0 * float(rec["rudy_overflow_ratio"])
    return rec


def bundle_ibm(suite, name, runs):
    from train_bridge import load_bundle
    return load_bundle(suite, name, runs)


def bundle_miniflow(platform_design, runs):
    from heurbridge.core.defio import load_def_design
    from heurbridge.eval import miniflow as MF
    flow = ROOT / "third_party" / "OpenROAD-flow-scripts" / "flow"
    p, d = MF.Nangate45(str(flow)), MF.from_orfs(str(flow), platform_design)
    name = platform_design.split("/")[-1]
    des, lay = load_def_design(str(ROOT / "runs" / "miniflow" / name / "fp.hb.def"),
                               [str(p.tech_lef), str(p.sc_lef)] + d.macro_lefs, family="orfs_cpu", tech="nangate45")
    base = lay.copy()
    base.pos[~des.is_macro & ~des.is_io & ~des.is_fixed] = np.nan
    cl = np.load(Path(runs) / des.id / "clusters.npy")
    return BD.make_bundle(des, base, cl)


def rows_for(b, rdir, track):
    """(program, seed, proxy J0, target J, gated J, terms) for every ok f1 row of the campaign."""
    mm = b.design.is_macro & ~b.design.is_fixed
    out, failed = [], []
    if track == "A":
        recs = [with_pct(r) for r in json.loads((rdir / "baseline.json").read_text())["records"]]
        base = cost.Baseline.from_records(b.design.id, recs)
        ev = HBGPEvaluator()
    for line in (rdir / "evals.jsonl").read_text().splitlines():
        r = json.loads(line)
        if not r["run_id"].endswith(".f1"):
            continue
        if r.get("status") != "ok":
            failed.append((r["run_id"], r.get("status"), (r.get("record") or {}).get("failure") or r.get("error")))
            continue
        lay = b.base.copy()
        lay.pos[mm] = np.asarray(r["pos_macros"])
        lay.orient[mm] = np.asarray(r["orient_macros"], dtype=np.int8)
        if track == "A":
            c = ev.score(with_pct(r["record"]), base)
            target, gated, terms = c.J, c.J_inf, {k: v["norm"] for k, v in c.terms.items()}
        else:
            target, gated = r.get("J_raw"), r["J"]
            terms = {k: v["norm"] for k, v in (r.get("terms") or {}).items()}
        out.append({"design": b.design.id, "run_id": r["run_id"], "program": r.get("program"), "seed": r.get("seed"),
                    "J_proxy": b.scorer(lay), "J_signoff": target, "J_gated": gated, "terms": terms})
    return out, failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--designs", default="")
    ap.add_argument("--miniflow", default="", help="ORFS platform/design evaluated with the local mini-flow (Track B dev)")
    ap.add_argument("--runs", default=str(ROOT / "runs" / "seed_dev"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    track = "B" if a.miniflow else "A"
    bundles = [bundle_miniflow(a.miniflow, a.runs)] if a.miniflow else [bundle_ibm(a.suite, n, a.runs) for n in a.designs.split(",")]
    rows, failed = [], []
    for b in bundles:
        rr, ff = rows_for(b, Path(a.runs) / b.design.id, track)
        rows += rr
        failed += ff
        print(json.dumps({"design": b.design.id, "rows": len(rr), "failed": len(ff)}), flush=True)
    st = C.study(rows, ["J"])
    g0 = C.gate_g0(st["J"], "M", "f0->f1")
    extra = {}
    if track == "B":
        fin = [r for r in rows if r["J_signoff"] is not None]
        extra["gate_pass_rate"] = float(np.mean([math.isfinite(r["J_gated"]) for r in fin])) if fin else None
        # the same rank study on the gated cost (rows gated out are dropped by per_design)
        st_g = C.study([{**r, "J_signoff": r["J_gated"]} for r in rows], ["J"])
        extra["gated_study"] = st_g["J"]
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    res = {"track": track, "rows": rows, "failed": failed, "study": st["J"], "gate_G0": vars(g0), **extra}
    out.with_suffix(".json").write_text(json.dumps(res, indent=1, default=str))
    per = st["J"]["per_design"]
    lines = ["| design | n | Spearman | Kendall | top-5 recall | regret | random regret |", "|---|---|---|---|---|---|---|"]
    for d, v in per.items():
        if v.get("n", 0) >= 3:
            lines.append("| %s | %d | %.3f | %.3f | %.2f | %.4f | %.4f |" % (d, v["n"], v["spearman"], v["kendall"],
                                                                         v["top5_recall"], v["regret"], v["regret_random"]))
        else:
            lines.append("| %s | %d | - | - | - | - | - |" % (d, v.get("n", 0)))
    m = st["J"]["mean"]
    txt = "\n".join(lines)
    if m:
        txt += "\n\nMean over designs: Kendall %.3f, Spearman %.3f, top-5 recall %.2f, regret %.4f vs random %.4f." % (
            m["kendall"], m["spearman"], m["top5_recall"], m["regret"], m["regret_random"])
    txt += "\n\nGate G0 rule for (stage M, f0 -> f1): **%s** (regret <= 25%% of random and Kendall >= 0.5)." % (
        "met" if g0.admissible else "not met")
    if track == "B":
        txt += ("\n\nTrack B: J before the gates is ranked above; the setup/hold gate passes on %.0f%% of the rows."
                % (100 * (extra["gate_pass_rate"] or 0)))
        gm = extra["gated_study"]["mean"]
        if gm:
            txt += " On the gated rows only: Kendall %.3f, top-5 recall %.2f." % (gm["kendall"], gm["top5_recall"])
    cmd = "python scripts/calibrate_dev.py " + " ".join(sys.argv[1:])
    reporting.render({
        "title": "E3-lite macro-stage calibration, f0 proxy vs f1 (development, Track %s)" % track,
        "report_id": out.name, "node": "local (macOS, CPU)",
        "track": "A-dev (HB-GP stand-in f1)" if track == "A" else "B-dev (local mini-flow f1, OpenLane OpenROAD b16bda7e)",
        "tools": "HeurBridge f0 surrogate J0 (clustered design, bridge-guard scorer); f1 from the stored campaign records",
        "gate": "G0 (T6.2) for (M, f0) — development evidence only (f1 stands in for signoff)",
        "samples": "%d rows over %d design(s) (%s)" % (len(rows), len(bundles), ", ".join(b.design.id for b in bundles)),
        "failures": "\n".join("- %s: %s (%s)" % f for f in failed) or "none",
        "commands": cmd, "results": txt,
        "notes": "Proxy = MacroStageScorer (f0 J0 of the clustered design); per-design statistics from "
                 "heurbridge/stats/calibration.py. Supersedes reports/env/dev_calibration_f0_vs_hbgp.json, which "
                 "scored a single layout per design (a harness error) and computed the Track-A cost with the raw RUDY "
                 "overflow."}, gate_passed=None, out=out.with_suffix(".md"))
    print(json.dumps({"study_mean": m, "gate_G0": vars(g0), **{k: v for k, v in extra.items() if k != "gated_study"}}))


if __name__ == "__main__":
    main()
