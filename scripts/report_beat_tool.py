#!/usr/bin/env python3
"""Report of the beat-the-tool work on Track A (exploratory): reports/beat_tool_track_a.md.

Reads fetched job outputs under runs/remote/:
  beat_tool_*/runs/beat_tool/*/summary.json   feasibility demo (scripts/beat_tool_demo.py)
  band_*/runs/beat_tool/*/band.json           f1-seed bands of the demo's best layouts (scripts/beat_tool_band.py)
  toolref3_*/runs/tool_refine3/*/rows.jsonl   tool + frozen bridge vs best of two, fresh-seed medians
  relink*/runs/relink/*/rows.jsonl            relinking two tool runs vs best of k, fresh-seed medians
and writes every table from them, so each number traces to a run file listed in the report.

  python scripts/report_beat_tool.py --out reports/beat_tool_track_a.md
"""

import argparse
import glob
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def jl(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def wil(d):
    from scipy.stats import wilcoxon
    d = np.asarray(d, float)
    d = d[d != 0]
    return float(wilcoxon(d, alternative="less").pvalue) if len(d) else 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--remote", default=str(ROOT / "runs" / "remote"))
    ap.add_argument("--out", default=str(ROOT / "reports" / "beat_tool_track_a.md"))
    a = ap.parse_args()
    R = Path(a.remote)
    L = ["# Beating the tool on Track A: feasibility, noise and equal-compute comparisons", "",
         "| Field | Value |", "|---|---|", "| Report | beat_tool_track_a |", "| Date | %s |" % time.strftime("%Y-%m-%d %H:%M"),
         "| Track | A (IBM; f1 = DREAMPlace GP + LG with macros fixed; J against the seeding M1 baseline, 0.45 by construction) |",
         "| Status of the claim | **exploratory demo (no claim)**; any claim needs the pre-registered test drafted from it |",
         "| Owner's aim (3 Oct) | macro layouts with mean J below 0.45 that beat the tool on output and on cost |", ""]
    # 1 demo
    demo = []
    for f in sorted(glob.glob(str(R / "beat_tool_*" / "runs" / "beat_tool" / "*" / "summary.json"))):
        demo += [dict(r, _src=str(Path(f).relative_to(ROOT))) for r in json.loads(Path(f).read_text())]
    if demo:
        L += ["## 1 Feasibility demo (f1 seed 0, the seed every arm also selected with)", "",
              "| design | tool | tool, best of 4 seeds | frozen bridge on the tool's layout (alpha) | local search (f1 runs, minutes) | "
              "tool run s | f1 run s (median) |", "|---|---|---|---|---|---|---|"]
        for r in sorted(demo, key=lambda r: int(r["design"][3:])):
            seeds = [r["tool_J"]] + [v["J"] for v in r["tool_more"].values() if math.isfinite(v["J"])]
            L.append("| %s | %.4f | %.4f | %.4f (%s) | %.4f (%d, %.1f) | %s | %.1f |" % (
                r["design"], r["tool_J"], min(seeds), r["bridge_tool"]["J"], r["bridge_tool"]["alpha"], r["ls_tool"]["J"],
                r["ls_tool"]["evals"], r["ls_tool"]["wall_s"] / 60, r["tool_m1_s"], r["f1_s_median"]))
        L += ["", "The tool's routability mode failed on every design (dreamplace_rc_1): it builds a congestion map that needs "
              "routing capacities the IBM Bookshelf files lack (third_party/DREAMPlace/dreamplace/PlaceObj.py:250-257). "
              "Sources: %s." % ", ".join(sorted({r["_src"] for r in demo})), ""]
    # 2 bands
    bands = []
    for f in sorted(glob.glob(str(R / "band_*" / "runs" / "beat_tool" / "*" / "band.json"))):
        bands += [dict(r, _src=str(Path(f).relative_to(ROOT))) for r in json.loads(Path(f).read_text())]
    if bands:
        L += ["## 2 Noise bands (f1 seeds 0-2; the tool's band = its baseline's three records)", "",
              "| design | tool band (median) | local search band (median) | whole band below the tool's | bridge band (median) | "
              "whole band below |", "|---|---|---|---|---|---|"]
        fb = lambda b: "%.4f-%.4f" % (min(b), max(b))
        for r in sorted(bands, key=lambda r: int(r["design"][3:])):
            L.append("| %s | %s (%.4f) | %s (%.4f) | %s | %s | %s |" % (
                r["design"], fb(r["tool_band"]), r["tool_median"], fb(r["ls_band"]), r["ls_median"],
                "yes" if r["ls_band_below_tool_band"] else "no",
                "%s (%.4f)" % (fb(r["bridge_band"]), r["bridge_median"]) if "bridge_band" in r else "- (alpha 0)",
                ("yes" if r["bridge_band_below_tool_band"] else "no") if "bridge_band" in r else "-"))
        L += ["", "Sources: %s." % ", ".join(sorted({r["_src"] for r in bands})), ""]
    # 3 tool + bridge vs best of 2
    tr = {}
    for f in sorted(glob.glob(str(R / "toolref3_*" / "runs" / "tool_refine3" / "*" / "rows.jsonl"))):
        rows = [r for r in jl(f) if "J_eval" in r]
        if rows:
            tr[rows[0]["design"]] = (rows, str(Path(f).relative_to(ROOT)))
    if tr:
        L += ["## 3 Tool + frozen bridge vs the tool's best of two seeds (endpoint: median J over fresh f1 seeds 1-3)", "",
              "| design | tool seeds | tool | tool + bridge (guarded) | best of 2 | mean cost s: tool / +bridge / best of 2 |",
              "|---|---|---|---|---|---|"]
        allv = {"tool": [], "refine": [], "best2": []}
        for d, (rows, src) in sorted(tr.items()):
            E = {k: np.array([r["J_eval"][k] for r in rows]) for k in allv}
            for k in allv:
                allv[k] += list(E[k])
            C = {k: np.mean([r["cost_s"][k] for r in rows]) for k in allv}
            L.append("| %s | %d | %.4f | %.4f | %.4f | %.0f / %.0f / %.0f |" % (d, len(rows), E["tool"].mean(), E["refine"].mean(),
                                                                         E["best2"].mean(), C["tool"], C["refine"], C["best2"]))
        A = {k: np.array(v) for k, v in allv.items()}
        L += ["", "All %d cases: tool + bridge minus best of 2 = %+.4f on average, one-sided Wilcoxon p = %.3f (bridge lower); "
              "tool + bridge minus tool = %+.4f, p = %.3g. Sources: %s." % (
                  len(A["tool"]), (A["refine"] - A["best2"]).mean(), wil(A["refine"] - A["best2"]),
                  (A["refine"] - A["tool"]).mean(), wil(A["refine"] - A["tool"]), ", ".join(src for _, src in tr.values())), ""]
    # 4 relinking
    rl = {}
    for f in sorted(glob.glob(str(R / "relink*" / "runs" / "relink" / "*" / "rows.jsonl"))):
        rows = jl(f)
        if rows:
            rl[rows[0]["design"]] = (rows, str(Path(f).relative_to(ROOT)))
    # best of 4 seeds (more compute than relinking: four tool runs and four f1 runs), from the saved per-seed scores
    tool_rows = {}
    for f in sorted(glob.glob(str(R / "*" / "runs" / "tool_runs" / "*" / "rows.jsonl"))) + \
            sorted(glob.glob(str(R / "toolref3_*" / "runs" / "tool_refine3" / "*" / "rows.jsonl"))):
        rows = [r for r in jl(f) if "J_eval" in r]
        if rows:
            tool_rows[rows[0]["design"]] = rows
    for d, (rows, src) in rl.items():
        tr_ = tool_rows.get(d)
        if not tr_:
            continue
        S = len(tr_)
        sel = [r["J_select"]["tool"] for r in tr_]
        fr = [r["J_eval"]["tool"] for r in tr_]
        for r in rows:
            if "best4" in r["J_eval"]:                          # relink_eval.py computes it since the ISPD2005 protocol
                continue
            s = r["seed_index"]
            k4 = min([(s + i) % S for i in range(4)], key=lambda k: sel[k])
            r["J_eval"]["best4"] = fr[k4]
    if rl:
        L += ["## 4 Relinking two tool runs vs the tool's best of k (endpoint: median J over fresh f1 seeds 1-3)", "",
              "Relink: the candidates P_M(T_s + a (T_p - T_s)), a in {0.25, 0.5, 0.75}, T_p another tool run with its "
              "interchangeable macros matched to T_s; the best of {T_s, T_p, candidates} by the selection seed (cost: two "
              "tool runs and five f1 runs, about the cost of best of 3: three tool runs and three f1 runs).", "",
              "| design | tool seeds | tool | best of 2 | best of 3 | best of 4 | relink | relink below best of 3 (cases) |",
              "|---|---|---|---|---|---|---|---|"]
        allv = {"tool": [], "best2": [], "best3": [], "best4": [], "relink": []}
        for d, (rows, src) in sorted(rl.items(), key=lambda kv: int(kv[0][3:])):
            E = {k: np.array([r["J_eval"].get(k, np.nan) for r in rows]) for k in allv}
            for k in allv:
                allv[k] += list(E[k])
            L.append("| %s | %d | %.4f | %.4f | %.4f | %.4f | %.4f | %d of %d (%d above) |" % (
                d, len(rows), E["tool"].mean(), E["best2"].mean(), E["best3"].mean(), E["best4"].mean(), E["relink"].mean(),
                int((E["relink"] < E["best3"]).sum()), len(rows), int((E["relink"] > E["best3"]).sum())))
        A = {k: np.array(v) for k, v in allv.items()}
        ok4 = np.isfinite(A["best4"])
        L += ["| **all** | %d | %.4f | %.4f | %.4f | %.4f | %.4f | %d of %d (%d above) |" % (
            len(A["tool"]), A["tool"].mean(), A["best2"].mean(), A["best3"].mean(), np.nanmean(A["best4"]), A["relink"].mean(),
            int((A["relink"] < A["best3"]).sum()), len(A["tool"]), int((A["relink"] > A["best3"]).sum())), "",
              "Relink minus best of 3: %+.4f on average (median %+.4f), one-sided Wilcoxon p = %.3g; relink minus best of 4 "
              "(more compute than relinking): %+.4f on average (median %+.4f), p = %.3g over %d cases, relink lower in %d and "
              "higher in %d. The means are dominated by ibm08, whose tool layouts blow up under some f1 seeds; the medians "
              "and the tests are not (exploratory, not registered tests). Sources: %s." % (
                  (A["relink"] - A["best3"]).mean(), np.median(A["relink"] - A["best3"]), wil(A["relink"] - A["best3"]),
                  (A["relink"][ok4] - A["best4"][ok4]).mean() if ok4.any() else float("nan"),
                  np.median(A["relink"][ok4] - A["best4"][ok4]) if ok4.any() else float("nan"),
                  wil(A["relink"][ok4] - A["best4"][ok4]) if ok4.any() else float("nan"), int(ok4.sum()),
                  int((A["relink"][ok4] < A["best4"][ok4]).sum()), int((A["relink"][ok4] > A["best4"][ok4]).sum()),
                  ", ".join(src for _, src in sorted(rl.values(), key=lambda v: v[1]))), ""]
    # 5 consensus of k tool runs
    cs = {}
    for f in sorted(glob.glob(str(R / "cons*" / "runs" / "consensus" / "*" / "rows.jsonl"))):
        rows = jl(f)
        if rows:
            cs[rows[0]["design"]] = (rows, str(Path(f).relative_to(ROOT)))
    if cs:
        L += ["## 5 Consensus of k tool runs vs the tool's best of k (endpoint: median J over fresh f1 seeds 1-3)", "",
              "Consensus: the average of k tool layouts with their interchangeable macros matched (a free-support "
              "barycenter), legalized by P_M; no f1 run picks it (cost: k tool runs). Best of k: k tool runs and k f1 "
              "runs. Guard: the best of the consensus and the k runs by the selection seed (k tool runs, k + 1 f1 runs).", "",
              "| design | k | windows | tool | best of k | consensus | guard | consensus below best of k (cases) | failures |",
              "|---|---|---|---|---|---|---|---|---|"]
        allv = {}
        for d, (rows, src) in sorted(cs.items(), key=lambda kv: int(kv[0][3:])):
            for k in sorted({r["k"] for r in rows}):
                rk = [r for r in rows if r["k"] == k]
                E = {c: np.array([r["J_eval"][c] for r in rk]) for c in ("tool", "best", "consensus", "guard")}
                for c in E:
                    allv.setdefault(k, {}).setdefault(c, []).extend(E[c])
                nf = sum(len(r["failures"]) for r in rk)
                fm = lambda v: "%.4f" % v.mean() if np.isfinite(v).all() else "+inf (%d)" % (~np.isfinite(v)).sum()
                L.append("| %s | %d | %d | %s | %s | %s | %s | %d of %d (%d above) | %d |" % (
                    d, k, len(rk), fm(E["tool"]), fm(E["best"]), fm(E["consensus"]), fm(E["guard"]),
                    int((E["consensus"] < E["best"]).sum()), len(rk), int((E["consensus"] > E["best"]).sum()), nf))
        from heurbridge.stats.paired import wilcoxon_less
        fm = lambda v: "%.4f" % v.mean() if np.isfinite(v).all() else "+inf (%d)" % (~np.isfinite(v)).sum()
        notes = []
        for k, A in sorted(allv.items()):
            A = {c: np.array(v, float) for c, v in A.items()}
            L.append("| **all** | %d | %d | %s | %s | %s | %s | %d of %d (%d above) | |" % (
                k, len(A["tool"]), fm(A["tool"]), fm(A["best"]), fm(A["consensus"]), fm(A["guard"]),
                int((A["consensus"] < A["best"]).sum()), len(A["tool"]), int((A["consensus"] > A["best"]).sum())))
            ok = np.isfinite(A["consensus"]) & np.isfinite(A["best"])
            notes.append("k = %d: consensus minus best of k %+.4f on average over the %d finite cases, one-sided Wilcoxon "
                         "p = %.3g (+inf kept); guard minus best of k %+.4f, p = %.3g. Windows overlap, so the cases are "
                         "not independent (exploratory)." % (
                             k, (A["consensus"][ok] - A["best"][ok]).mean() if ok.any() else float("nan"), int(ok.sum()),
                             wilcoxon_less(A["consensus"], A["best"])["p"], (A["guard"] - A["best"]).mean(),
                             wilcoxon_less(A["guard"], A["best"])["p"]))
        L += [""] + notes + ["", "Sources: %s." % ", ".join(src for _, src in sorted(cs.values(), key=lambda v: v[1])), ""]
    # 6 macro orientation pass
    fl = {}
    for f in sorted(glob.glob(str(R / "flip_*" / "runs" / "flip" / "*" / "rows.jsonl"))):
        rows = jl(f)
        if rows:
            fl[rows[0]["design"]] = (rows, str(Path(f).relative_to(ROOT)))
    if fl:
        from heurbridge.stats.paired import wilcoxon_less
        L += ["## 6 Macro orientation pass on the tool's layout (endpoint: median J over fresh f1 seeds 1-3)", "",
              "The tool never flips a macro. The pass gives each movable macro the footprint-preserving orientation (N, S, "
              "FS, FN) that minimizes its nets' weighted HPWL with every other pin where f1 placed it (positions and "
              "legality unchanged; scripts/flip_eval.py). Flip: the pass alone (one more f1 run when computed on f1's "
              "placement). Guarded: the better of the two by the selection seed. Best of 2 + flip: the guarded pass on "
              "the best-of-2 pick (two tool runs, three f1 runs).", "",
              "| design | cases | tool | flip | guarded | best of 2 | best of 2 + flip | best of 3 | best of 4 | flip below tool | "
              "HPWL change with the cells fixed |", "|---|---|---|---|---|---|---|---|---|---|---|"]
        allv = {k: [] for k in ("tool", "flip", "flip_guard", "best2", "b2f", "best3", "best4")}
        for d, (rows, src) in sorted(fl.items(), key=lambda kv: int(kv[0][3:])):
            byi = {r["seed_index"]: r for r in rows}
            E = {k: np.array([r["J_eval"][k] for r in rows]) for k in ("tool", "flip", "flip_guard", "best2", "best3", "best4")}
            E["b2f"] = np.array([byi[r["best2_pick"]]["J_eval"]["flip_guard"] for r in rows])
            for k in allv:
                allv[k] += list(E[k])
            hp = [r["hpwl_placed"]["after_cells_fixed"] / r["hpwl_placed"]["before"] - 1 for r in rows if "hpwl_placed" in r]
            L.append("| %s | %d | %s | %d of %d | %+.2f %% |" % (
                d, len(rows), " | ".join("%.4f" % E[k].mean() for k in ("tool", "flip", "flip_guard", "best2", "b2f", "best3",
                                                                          "best4")),
                int((E["flip"] < E["tool"]).sum()), len(rows), 100 * np.mean(hp) if hp else float("nan")))
        A = {k: np.array(v, float) for k, v in allv.items()}
        L += ["| **all** | %d | %s | %d of %d | |" % (len(A["tool"]), " | ".join("%.4f" % A[k].mean() for k in (
            "tool", "flip", "flip_guard", "best2", "b2f", "best3", "best4")), int((A["flip"] < A["tool"]).sum()), len(A["tool"])), "",
              "Flip minus tool %+.4f (one-sided Wilcoxon p = %.3g); best of 2 + flip minus best of 2 %+.4f (p = %.3g), minus "
              "best of 3 %+.4f (p = %.3g). Exploratory. Sources: %s." % (
                  (A["flip"] - A["tool"]).mean(), wilcoxon_less(A["flip"], A["tool"])["p"],
                  (A["b2f"] - A["best2"]).mean(), wilcoxon_less(A["b2f"], A["best2"])["p"],
                  (A["b2f"] - A["best3"]).mean(), wilcoxon_less(A["b2f"], A["best3"])["p"],
                  ", ".join(src for _, src in sorted(fl.values(), key=lambda v: v[1]))), ""]
    L += ["## Notes", "",
          "- f1 is noisy: the same macro layout scored with another DREAMPlace seed changes J, and on some designs a run blows "
          "the overflow term up (ibm08: J 0.44 under one seed, 1.5-4.6 under another). Every comparison above therefore "
          "picks with one seed and judges with fresh seeds (median of three, as the tool's own baseline).",
          "- The run files are local (`runs/remote/`, not in the public repository); the scripts that made them are named in "
          "each section's title.", ""]
    Path(a.out).write_text("\n".join(L) + "\n")
    print("REPORT_OK", a.out)


if __name__ == "__main__":
    main()
