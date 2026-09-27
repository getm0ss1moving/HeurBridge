#!/usr/bin/env python3
"""Track-A seeding campaign report (T1.7 baselines + T2.7 seeding): reports/T2_trackA_<label>.md

  python scripts/report_trackA.py --label ibm_dreamplace \
      --runs runs/remote/seedA_dp_s1/runs/seed_trackA_dp runs/remote/seedA_dp_s2/runs/seed_trackA_dp \
      --archives runs/remote/seedA_dp_s1/archive_A0_trackA_s1 runs/remote/seedA_dp_s2/archive_A0_trackA_s2

Reads each <runs>/<design>/{baseline.json, evals.jsonl, meta.json}: per design the M1 / baseline record (3 seeds,
median), program evaluations (failures by name, best J, how many layouts beat the baseline), local search and the
archive's best entry.  Descriptive: no claim follows from a seeding campaign.
"""

import argparse
import collections
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heurbridge import reporting  # noqa: E402
from heurbridge.archive.store import Archive  # noqa: E402
from heurbridge.pipeline.seed_archive import distinct  # noqa: E402

J_BASE = 0.45                 # Track A: rWL (0.30) + OF (0.15) terms, each 1 for the baseline by construction


def fmt(x, nd=4):
    return "-" if x is None or (isinstance(x, float) and not math.isfinite(x)) else ("%.*f" % (nd, x))


def failure_name(r):
    """status (e.g. program_timeout = the sandbox's 60 s CPU limit, SIGXCPU) or the evaluator's named failure."""
    rec = r.get("record") or {}
    if rec.get("failure"):
        return str(rec["failure"]).split(":")[0]
    err = str(r.get("error") or "").strip()
    return "%s%s" % (r.get("status"), " (%s)" % err if err else "")


def design_rows(rdir: Path):
    base = json.loads((rdir / "baseline.json").read_text())
    ev = rdir / "evals.jsonl"
    rows = [json.loads(l) for l in ev.read_text().splitlines()] if ev.exists() else []
    meta = json.loads((rdir / "meta.json").read_text()) if (rdir / "meta.json").exists() else {}
    return base, rows, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--archives", nargs="*", default=[])
    ap.add_argument("--node", default="")
    ap.add_argument("--code", default="", help="commit / code archive for runs made before the CODE_VERSION stamp")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    designs = {}
    for r in a.runs:
        for d in sorted(Path(r).iterdir()):
            if (d / "baseline.json").exists():
                designs[d.name] = d
    arch = [Archive(p, min_fidelity=1) for p in a.archives if Path(p).exists()]
    fails = collections.Counter()
    table = ["| design | M1 s / P_M disp | baseline HPWL (median of 3) | RUDY OF % | f1 s | program evals (failed) "
             "| best program J | layouts < baseline (distinct) | LS best J | archive best J |", "|---|---|---|---|---|---|---|---|---|---|"]
    metas, n_eval, n_ls, n_beat = [], 0, 0, 0
    for name in sorted(designs, key=lambda s: (len(s), s)):
        base, rows, meta = design_rows(designs[name])
        metas.append(meta)
        recs = base["records"]
        hp = [r.get("hpwl_um") for r in recs if r.get("hpwl_um") is not None]
        m1 = base.get("m1") or {}
        prog = [r for r in rows if r.get("program") not in (None, "LS")]
        ls = [r for r in rows if r.get("program") == "LS"]
        n_eval += len(prog)
        n_ls += len(ls)
        for r in rows:
            if r.get("status") != "ok":
                fails[failure_name(r)] += 1
        ok = [r for r in prog if r.get("status") == "ok" and math.isfinite(r.get("J", math.inf))]
        best = min(ok, key=lambda r: r["J"]) if ok else None
        beat = [r for r in ok if r["J"] < J_BASE]
        n_beat += len(distinct(beat)) if beat else 0
        ls_ok = [r["J"] for r in ls if r.get("status") == "ok" and math.isfinite(r.get("J", math.inf))]
        top = None
        for ar in arch:
            t = ar.topk(name, "M")
            if t and (top is None or t[0]["J"] < top["J"]):
                top = t[0]
        table.append("| %s | %s | %s | %s | %s | %d (%d) | %s | %d (%d) | %s | %s |" % (
            name, ("%s / %s" % (fmt(m1.get("wall_s"), 1), fmt(m1.get("pm_mean_disp"), 4))) if m1 else "-",
            fmt(statistics.median(hp), 0) if hp else "-",
            fmt(statistics.median([r.get("rudy_of_pct") or 0.0 for r in recs]), 4),
            fmt(statistics.median([r.get("runtime_s") or 0.0 for r in recs]), 1),
            len(prog), len(prog) - len([r for r in prog if r.get("status") == "ok"]),
            ("%s %s" % (best["program"], fmt(best["J"]))) if best else "-", len(beat), len(distinct(beat)) if beat else 0,
            fmt(min(ls_ok)) if ls_ok else "-", fmt(top["J"]) if top else "-"))
    tools = sorted({m.get("track") or "" for m in metas} - {""})
    evs = sorted({m.get("evaluator") or "" for m in metas} - {""})
    tool_txt = "; ".join({"dreamplace_f1": "DREAMPlace 4.3.1 (GPU; CUDA 11.8, torch 2.6.0) + f0 RUDY/HPWL",
                          "hbgp_f1": "HB-GP (heurbridge.eval.gp, 1 thread) + f0 RUDY/HPWL"}.get(e, e) for e in evs) or "-"
    shas = [a.code] if a.code else sorted({(m.get("git_sha") or "unknown") + (
        " (%s)" % m["code_archive"] if m.get("code_archive") else "") for m in metas})
    cmds = collections.defaultdict(list)                  # one command per configuration, designs joined
    for m in metas:
        cfg = dict(m.get("config") or {})
        des = cfg.pop("designs", "")
        cmds[json.dumps(cfg, sort_keys=True)].append(des)
    out = a.out or str(ROOT / "reports" / ("T2_trackA_%s.md" % a.label))
    reporting.render({
        "title": "Track-A seeding campaign (T1.7 / T2.7): %s" % a.label,
        "report_id": "trackA_%s" % a.label, "node": a.node or ", ".join(sorted({m.get("host") or "?" for m in metas})),
        "track": "; ".join(tools) or "-", "tools": tool_txt,
        "version": "; ".join(sorted({m.get("heurbridge_version") or "?" for m in metas})), "git_sha": "; ".join(shas),
        "gate": "T2 exit (archive A0, Track A) — descriptive",
        "samples": "%d designs; %d program evaluations; %d local-search evaluations; baseline 3 seeds per design" % (
            len(designs), n_eval, n_ls),
        "failures": "\n".join("- %s: %d" % kv for kv in fails.most_common()) or "none",
        "commands": "\n".join("python scripts/run_seed_archive.py --designs %s " % ",".join(sorted(ds, key=lambda x: (len(x), x)))
                               + " ".join("--%s %s" % (k.replace("_", "-"), v) for k, v in json.loads(c).items()
                                          if v is not None and v != "" and v is not False)
                               for c, ds in cmds.items()),
        "results": "\n".join(["J is relative to the baseline (J = %.2f for the baseline by construction; lower is "
                              "better); a layout 'beats' the baseline when J < %.2f." % (J_BASE, J_BASE), "",
                              "\n".join(table), "",
                              "Distinct layouts below the baseline, all designs: %d." % n_beat]),
        "notes": "M1 = the tool-native macro placement (DREAMPlace mixed-size for the dreamplace evaluator; the benchmark "
                 "macro positions for the HB-GP development runs); P_M disp = mean macro displacement of the legality "
                 "check, core-normalized. Failures are counted as +inf and listed by name."},
        gate_passed=None, out=out)
    print("REPORT_OK", out)


if __name__ == "__main__":
    main()
