#!/usr/bin/env python3
"""Track-B development seeding report (T2.7 on the local mini-flow): reports/T2_trackB_dev_<design>.md

  python scripts/report_trackb_dev.py --design bp_fe_top [--archive archive_dev_trackB]
  python scripts/report_trackb_dev.py --design bp_fe_top --runs runs/remote/seedB_bp_fe_top/runs/seed_miniflow \
      --archive runs/remote/seedB_bp_fe_top/archive_B0_bp_fe_top --label server     (a server campaign)

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
from heurbridge.eval import cost, orfs  # noqa: E402
from heurbridge.pipeline.seed_archive import distinct  # noqa: E402
from heurbridge.stats import paired as ST  # noqa: E402


def fmt(x, nd=4):
    return "-" if x is None or (isinstance(x, float) and not math.isfinite(x)) else ("%.*f" % (nd, x))


def timing_ok(r) -> bool:
    """Setup and hold gates pass (recorded gates; at f1 they are reported, not enforced, under cost_v2)."""
    g = r.get("gates") or {}
    return all((g.get(k) or {}).get("status") != "fail" for k in ("setup", "hold"))


def cost_version() -> str:
    import yaml
    try:
        return str(yaml.safe_load((ROOT / "configs" / "cost.yaml").read_text()).get("version", "cost_v2"))
    except Exception:           # noqa: BLE001
        return "cost_v2"


def tools_line(meta: dict) -> str:
    """Tool versions of an ORFS campaign.  Runs before 2026-09-29 recorded the Yosys on PATH; the flow ran the
    binary in config['yosys'] (ORFS YOSYS_EXE)."""
    tr = (meta.get("track") or "?").split("; ", 1)[-1].rstrip(")")
    y = (meta.get("config") or {}).get("yosys")
    if y and y not in tr:
        tr = tr.split(", Yosys")[0] + "; the flow's Yosys: %s (the Yosys version in the run's metadata is the one on PATH, not used)" % y
    return tr


def orfs_command(cfg: dict) -> str:
    parts = ["python scripts/run_seed_orfs.py --flow %s --design %s" % (cfg.get("flow", "<ORFS>/flow"), cfg.get("design", "?"))]
    for k in ("seeds", "top", "spread", "ls", "base_runs", "timeout", "base_timeout", "noise_replays", "phase", "yosys"):
        if cfg.get(k) not in (None, "", False):
            parts.append("--%s %s" % (k.replace("_", "-"), cfg[k]))
    for mv in cfg.get("make_var") or []:
        parts.append("--make-var %s" % mv)
    return " ".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", default="bp_fe_top")
    ap.add_argument("--archive", default=str(ROOT / "archive_dev_trackB"))
    ap.add_argument("--out", default="")
    ap.add_argument("--runs", default=str(ROOT / "runs" / "seed_miniflow"))
    ap.add_argument("--label", default="dev", help="report name suffix; 'dev' = the local development campaign")
    a = ap.parse_args()
    rdir = Path(a.runs) / a.design
    meta = json.loads((rdir / "meta.json").read_text()) if (rdir / "meta.json").exists() else {}
    dev = a.label == "dev"
    base = json.loads((rdir / "baseline.json").read_text())
    cfg = meta.get("config") or {}
    # ORFS campaigns resume rows written under earlier cost versions: every row is re-scored from its record under
    # the current rule (cost_v2: at f1 only a failed flow is enforced, the timing gates are reported)
    bases = {} if dev else {1: cost.Baseline.from_records(a.design, base["records"])}
    if not dev and (rdir / "baseline_f2.json").exists():
        bases[2] = cost.Baseline.from_records(a.design, json.loads((rdir / "baseline_f2.json").read_text())["records"])

    def rescored(r, fid):
        if fid not in bases or r.get("status") != "ok" or not isinstance(r.get("record"), dict):
            return r
        c = cost.evaluate(r["record"], bases[fid], fidelity=fid)
        return {**r, "J": c.J_inf, "J_raw": c.J, "gates": c.gates}

    rows = [rescored(json.loads(l), 1) for l in (rdir / "evals.jsonl").read_text().splitlines()]
    prog_rows = [r for r in rows if r.get("program") not in (None, "LS", "M1_replay")]
    replay = {1: [r for r in rows if r.get("program") == "M1_replay"]}
    f2_path = rdir / "evals_f2.jsonl"
    rows2 = [rescored(json.loads(l), 2) for l in f2_path.read_text().splitlines()] if f2_path.exists() else []
    replay[2] = [r for r in rows2 if r.get("program") == "M1_replay"]
    ls_rows = [r for r in rows if r.get("program") == "LS"]
    b0 = base["records"][0]
    J_base = 0.95                   # every term of the M1 baseline is 1 by construction (no via term at f1)
    # failures by name
    fails = collections.Counter()
    for r in rows:
        if r.get("status") != "ok":
            rec = r.get("record") or {}
            name = rec.get("failure") or r.get("error") or r.get("status")
            if "design_config" in rec:                  # ORFS: the tool error or the step a timeout stopped
                name = rec.get("failure") or orfs.failure_reason(rec.get("log_tail", ""), rec.get("returncode")) or name
                fails[str(name).split(". ")[0].rstrip(".")] += 1         # one line per tool message
                continue
            fails[(str(name).split(":")[0] + (": " + str(name).split("]")[0].split("[")[-1] if "[" in str(name) else "")
                   ).split(". ")[0].rstrip(".")] += 1                    # one line per tool message
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
        gated = [r["J_raw"] for r in ok if timing_ok(r) and r.get("J_raw") is not None]
        lines.append("| %s | %d | %d | %d | %s | %s | %s |" % (pid, len(rr), len(rr) - len(ok), len(gated),
                     fmt(float(np.median(raw))) if raw else "-", fmt(min(raw)) if raw else "-", fmt(min(gated)) if gated else "-"))
    ok_all = [r for r in prog_rows if r.get("status") == "ok"]
    gate_rate = np.mean([timing_ok(r) for r in ok_all]) if ok_all else float("nan")
    setup_fail = sum(1 for r in ok_all if ((r.get("gates") or {}).get("setup") or {}).get("status") == "fail")
    hold_fail = sum(1 for r in ok_all if ((r.get("gates") or {}).get("hold") or {}).get("status") == "fail")
    beat = [r for r in ok_all if timing_ok(r) and r["J_raw"] < J_base]
    raw_beat = [r for r in ok_all if r.get("J_raw") is not None and r["J_raw"] < J_base]
    of_pos = [r for r in ok_all if ((r.get("record") or {}).get("gr_overflow_total") or 0) > 0]
    res = ["**Baseline (M1, rtl_macro_placer), %d runs, deterministic: %s** — GR WL %s um, GR overflow %s, setup WNS %s ns,"
           " TNS %s ns, hold WNS %s ns, power %s W (J = %.2f by construction)." % (
               len(base["records"]), base.get("deterministic"), fmt(b0.get("gr_wl"), 0), b0.get("gr_overflow_total"),
               fmt(b0.get("setup_wns_ns"), 3), fmt(b0.get("setup_tns_ns"), 1), fmt(b0.get("hold_wns_ns"), 3),
               fmt(b0.get("total_power_w"), 3), J_base),
           "", "**Program evaluations:** %d (%d completed, %d failed); setup/hold gates passed on %d of %d completed "
           "(%.0f%%; setup failures %d, hold failures %d); layouts with GR overflow > 0: %d." % (
               len(prog_rows), len(ok_all), len(prog_rows) - len(ok_all), sum(timing_ok(r) for r in ok_all),
               len(ok_all), 100 * gate_rate, setup_fail, hold_fail, len(of_pos)),
           "Below the baseline J %.2f: %d layouts after the gates (%d distinct), %d before the gates (%d distinct); "
           "completed layouts: %d distinct of %d (seed-independent programs repeat their layout)." % (
               J_base, len(beat), len(distinct(beat)), len(raw_beat), len(distinct(raw_beat)), len(distinct(ok_all)), len(ok_all)),
           "", "\n".join(lines)]
    if replay[1] or replay[2]:                  # same-path control and noise band (M1 imported like a candidate)
        txt = []
        for fid, jb in ((1, J_base), (2, 1.0)):
            rr = sorted(replay[fid], key=lambda r: r.get("seed") or 0)
            if not rr:
                continue
            vals = [r.get("J_raw") for r in rr if r.get("status") == "ok" and r.get("J_raw") is not None]
            band = [jb] + vals                    # base (by construction) + replay + shifted replays
            txt.append("f%d: replay J %s%s; shifted by one site/row: %s; band over base and replays %s-%s (width %s)" % (
                fid, fmt(rr[0].get("J_raw")), "" if rr[0].get("status") == "ok" else " (" + str(rr[0].get("status")) + ")",
                ", ".join(fmt(r.get("J_raw")) if r.get("status") == "ok" else str(r.get("status")) for r in rr[1:]) or "-",
                fmt(min(band)), fmt(max(band)), fmt(max(band) - min(band))))
        res += ["", "**Same-path control and noise band** (M1's layout imported like every candidate -- standard "
                "cells not pre-placed by Hier-RTLMP -- and the same layout shifted as a whole by one site or row; J "
                "before the gates, the baseline is %.2f at f1 and 1.00 at f2 by construction): " % J_base
                + "; ".join(txt) + ". Candidate deltas are paired with the replay; differences inside the band are "
                "not distinguishable from the flow's sensitivity to its starting point."]
    if ls_rows:
        traj = []
        best = None
        for r in ls_rows:
            if r.get("status") == "ok" and timing_ok(r) and r.get("J_raw") is not None and (best is None or r["J_raw"] < best):
                best = r["J_raw"]
            traj.append(best)
        res += ["", "**Local search** (T2.7, %d evaluations): best J among layouts passing the timing gates, after each step: %s." % (
            len(ls_rows), ", ".join(fmt(x) for x in traj[5::6]) or "-")]
    cand2 = [r for r in rows2 if r.get("program") != "M1_replay"]
    if cand2:
        ok2 = [r for r in cand2 if r.get("status") == "ok"]
        adm = sorted([r for r in ok2 if math.isfinite(r["J"])], key=lambda r: r["J"])
        raw2 = [r["J_raw"] for r in ok2 if r.get("J_raw") is not None]
        pairs = [(r["f1_J_raw"], r["J_raw"]) for r in ok2 if r.get("f1_J_raw") is not None and r.get("J_raw") is not None]
        tau = ST.kendall_tau([x for x, _ in pairs], [y for _, y in pairs]) if len(pairs) > 2 else float("nan")
        failing = collections.Counter(g for r in ok2 for g, v in (r.get("gates") or {}).items()
                                      if isinstance(v, dict) and v.get("status") == "fail")
        rp = [r for r in replay[2] if r.get("status") == "ok" and r.get("J_raw") is not None]
        lo = min([1.0] + [r["J_raw"] for r in rp])
        rj = rp[0]["J_raw"] if rp and (rp[0].get("seed") or 0) == 0 else None
        res += ["", "**Signoff (f2, 6_report; every gate enforced):** %d layouts (the top %s of f1 and %s more across "
                "its ranking): %d completed, %d failed; all gates pass on %d (failing gates: %s); J before the gates "
                "median %s, best %s; best admitted J %s. Rank agreement of f1 and f2 (Kendall tau of J before the "
                "gates) %s over %d layouts. Admitted layouts below the f2 band's lower edge (%s): %d; below the "
                "same-path replay (%s): %d." % (
                    len(cand2), cfg.get("top", "?"), cfg.get("spread", "?"), len(ok2), len(cand2) - len(ok2), len(adm),
                    ", ".join("%s %d" % kv for kv in failing.most_common()) or "none",
                    fmt(float(np.median(raw2))) if raw2 else "-", fmt(min(raw2)) if raw2 else "-",
                    fmt(adm[0]["J"]) if adm else "-", fmt(tau), len(pairs), fmt(lo),
                    sum(r["J"] < lo for r in adm), fmt(rj) if rj is not None else "-",
                    sum(r["J"] < rj for r in adm) if rj is not None else 0)]
        if adm:
            res += ["", "| admitted at f2 | program | seed | f1 J | f2 J |", "|---|---|---|---|---|"] + [
                "| %s | %s | %s | %s | %s |" % (r["run_id"], r.get("program"), r.get("seed"), fmt(r.get("f1_J_raw")),
                                              fmt(r["J"])) for r in adm[:8]]
    arch_txt = "no archive"
    if Path(a.archive).exists():
        top = Archive(a.archive, min_fidelity=1 if dev else 2).topk(a.design, "M")
        arch_txt = "; ".join("%s J=%s (f%d)" % ((e.get("provenance") or {}).get("program") or (e.get("provenance") or {}).get("run_id"),
                                                 fmt(e["J"]), e["fidelity"]) for e in top)
    res += ["", "**Archive top-k (%s):** %s." % ("fidelity 1, development" if dev else "f2-admitted", arch_txt)]
    out = a.out or str(ROOT / "reports" / ("T2_trackB_%s_%s.md" % (a.label, a.design)))
    reporting.render({
        "title": ("Track-B seeding (T2.7) on %s — mini-flow f1 (%s)" % (a.design, a.label)) if dev else
                 "Track-B seeding (T2.7) on %s — ORFS flow, f1 = 5_1_grt, f2 = 6_report (%s)" % (a.design, a.label),
        "report_id": "trackB_%s_%s" % (a.label, a.design),
        "node": "local (macOS; OpenLane container, 6 vCPU)" if dev else (meta.get("host") or "?"),
        "track": "B-dev (ORFS-aligned mini-flow, OpenROAD b16bda7e; f1 timing from placement parasitics)" if dev
                 else "B (ORFS 2024-12-13 8ae3ae36); %s threads" % meta.get("eda_threads", "?"),
        "tools": "OpenROAD b16bda7e, Yosys 0.38 (efabless/openlane:master-arm64v8)" if dev else tools_line(meta),
        "version": meta.get("heurbridge_version", "?"),
        "git_sha": (meta.get("git_sha") or "unknown") + (" (%s)" % meta["code_archive"] if meta.get("code_archive") else ""),
        "gate": "T2 exit (archive A0) — development only; the pre-registered A0 is built at f2 on the server" if dev
                else "T2 exit (archive A0, Track B; f2 verification in the f2 campaign) — descriptive",
        "samples": "%d program evaluations (16 programs x seeds), %d local-search evaluations, baseline x %d" % (
            len(prog_rows), len(ls_rows), len(base["records"])),
        "failures": "\n".join("- %s: %d" % kv for kv in fails.most_common()) or "none",
        "commands": ("python scripts/run_seed_miniflow.py --design nangate45/%s --seeds 5 --top 10 --ls 8\n"
                     "python scripts/report_trackb_dev.py --design %s" % (a.design, a.design)) if dev else
                    orfs_command(cfg) + "\npython scripts/report_trackb_dev.py --design %s --runs %s --archive %s "
                    "--label %s" % (a.design, a.runs, a.archive, a.label),
        "results": "\n".join(res),
        "notes": ("J before the gates ranks every completed layout; the gated J is +inf when the setup or hold WNS "
                  "is worse than the baseline by more than 0.02 ns (frozen rule B.3). Superseded rows of earlier flow "
                  "versions are kept under runs/seed_miniflow/%s/superseded_*." % a.design) if dev else
                 ("J before the gates ranks every completed layout. Every row is re-scored from its record under %s "
                  "(the campaign resumed rows written under the earlier rule): at f1 only a failed flow is enforced "
                  "and 'timing gates passed' counts rows whose setup and hold WNS are within 0.02 ns of the baseline "
                  "(frozen rule B.3); at f2 every gate is enforced (J = +inf on a failed gate)." % cost_version())},
        gate_passed=None, out=out)
    print("REPORT_OK", out)


if __name__ == "__main__":
    main()
