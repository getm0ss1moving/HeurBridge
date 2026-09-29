#!/usr/bin/env python3
"""Demo (owner's request, 29 Sep; exploratory, no claim): does DREAMPlace place the standard cells better when
they start from the macro bridge's cell sketch?

The same bridge-refined macro layouts as the E0 demo (ibm04, ibm06: the bridge's validation designs, not G0''s
test designs).  The guard's alpha per case is read from the E0 demo's rows, so no guard run is repeated; the
bridge endpoint is recomputed (deterministic).  Each layout is placed three times by DREAMPlace (Track-A f1:
GP + LG with the macros fixed, f0 metrics, J on the seeding campaign's M1 scale, as in E0):

  A centre     every cell starts at the die centre (random_center_init_flag = 1: today's f1)
  B sketch     every cell starts at its cluster's position in the bridge's guarded output (handoff.guarded_sketch)
  C quadratic  every cell starts at its cluster's quadratic position around the same macros (control)

B and C switch DREAMPlace's random_center_init_flag to 0 (global placement then starts from the .pl) inside this
process only: the evaluation code on G0''s path is not changed.  Cases the guard left at alpha = 0 give B and C
the same start: a determinism check.  DA0 diagnostic: area-weighted RMS distance (normalized core units) of the
sketch and of the quadratic start to the cluster centroids of arm A's placement.

  python scripts/demo_sketch_start.py --designs ibm04,ibm06 --runs runs/seed_trackA_dp \
      --e0-demo runs/e0_demo --bridge checkpoints/algR_trackA_round1/best.pt --out runs/demo_sketch
"""

import argparse
import contextlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heurbridge.bridge import handoff as H  # noqa: E402
from heurbridge.bridge.sample import bridge_endpoints, source_nodes  # noqa: E402
from heurbridge.bridge.train import load_bridge  # noqa: E402
from heurbridge.core import project  # noqa: E402
from heurbridge.eval import cost  # noqa: E402
from heurbridge.heuristics.macro.registry import all_programs  # noqa: E402
from heurbridge.meta import write_meta  # noqa: E402
from heurbridge.pipeline import bridge_data as BD  # noqa: E402
from heurbridge.pipeline.evaluators import track_a_final  # noqa: E402

ARMS = ("centre", "sketch", "quadratic")


@contextlib.contextmanager
def start_from_pl():
    """DREAMPlace starts global placement from the .pl positions (random_center_init_flag = 0), this process only."""
    from heurbridge.eval import dreamplace as DP
    orig = DP.params

    def params(*a, **kw):
        p = orig(*a, **kw)
        p["random_center_init_flag"] = 0
        return p
    DP.params = params
    try:
        yield
    finally:
        DP.params = orig


def with_cells(design, layout, cell_pos, cluster_of):
    """Copy of ``layout`` with every clustered cell at ``cell_pos`` of its cluster (normalized centres)."""
    out = layout.copy()
    p = H.member_positions(cell_pos, cluster_of)
    m = np.isfinite(p).all(1)
    out.pos[m] = p[m]
    return out


def e0_alphas(e0_dir: Path, design: str) -> dict:
    """{(program, seed): alpha} of the co-trained partner in the E0 demo (task-list protocol run)."""
    f = e0_dir / ("spec_%s" % design) / "e0_rows.jsonl"
    rows = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    return {(r["program"], r["seed"]): float(r["info"]["alpha"]) for r in rows if r["partner"] == "cotrained"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--designs", default="ibm04,ibm06")
    ap.add_argument("--runs", default="runs/seed_trackA_dp", help="seeding campaign (baseline.json, clusters.npy)")
    ap.add_argument("--e0-demo", default="runs/e0_demo", help="E0 demo output (rows with the guard's alpha, sources)")
    ap.add_argument("--bridge", default="checkpoints/algR_trackA_round1/best.pt")
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--K", type=int, default=20)
    ap.add_argument("--out", default="runs/demo_sketch")
    ap.add_argument("--limit", type=int, default=0, help="first N cases per design (0 = all)")
    a = ap.parse_args()
    from train_bridge import load_bundle
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    write_meta(out, "demo_sketch_start", a.designs, config=vars(a), campaign="demo_sketch_start (exploratory)")
    rows_path = out / "rows.jsonl"
    rows = [json.loads(l) for l in rows_path.read_text().splitlines()] if rows_path.exists() else []
    done = {(r["design"], r["program"], r["seed"], r["arm"]) for r in rows}
    model = load_bridge(a.bridge)
    progs = all_programs()
    fh = open(rows_path, "a")
    for name in a.designs.split(","):
        b = load_bundle(a.suite, name, a.runs)
        g, des = b.graph, b.design
        e0 = Path(a.e0_demo)
        srcs = BD.run_sources(b, progs, a.seeds, cache=e0 / ("spec_%s" % name) / "cache")
        alphas = e0_alphas(e0, name)
        final = track_a_final("dreamplace", cluster_of=b.cluster_of)
        base_recs = json.loads((Path(a.runs) / des.id / "baseline.json").read_text())["records"]
        baseline = cost.Baseline.from_records(des.id, base_recs)
        n = 0
        for pid, s, lay in srcs:
            if (pid, s) not in alphas:
                continue
            n += 1
            if a.limit and n > a.limit:
                break
            alpha = alphas[(pid, s)]
            src = source_nodes(g, lay)
            end = bridge_endpoints(model, g, src[None], K=a.K)[0]
            dep, rep = project.legalize_macros(des, g.to_layout(src + alpha * (end - src), lay))
            if not rep.ok:
                print(json.dumps({"design": name, "program": pid, "seed": s, "skip": "P_M failed"}), flush=True)
                continue
            h = H.make_handoff(g, dep, src, end, alpha, {"program": pid, "seed": s})
            quad = source_nodes(g, dep)[g.cluster_nodes]
            starts = {"centre": None, "sketch": h.sketch, "quadratic": quad}
            placed_centroids = None
            for arm in ARMS:
                key = (des.id, pid, s, arm)
                if key in done:
                    continue
                t0 = time.time()
                if starts[arm] is None:
                    rec = final.evaluate(des, dep, "%s.%s.s%d.%s" % (name, pid, s, arm), out / "work")
                else:
                    with start_from_pl():
                        rec = final.evaluate(des, with_cells(des, dep, starts[arm], b.cluster_of),
                                             "%s.%s.s%d.%s" % (name, pid, s, arm), out / "work")
                c = final.score(rec, baseline)
                row = {"design": des.id, "program": pid, "seed": s, "arm": arm, "alpha": alpha, "J": c.J_inf,
                       "J_raw": c.J, "terms": {t: v.get("raw") for t, v in c.terms.items()},
                       "failure": rec.get("failure"), "gp_overflow": rec.get("gp_overflow"),
                       "wall_s": round(time.time() - t0, 1), "same_start_as_quadratic": bool(alpha == 0.0)}
                if arm == "centre" and rec.get("cluster_pos") is not None:
                    placed_centroids = np.asarray(rec["cluster_pos"])
                    row["fidelity"] = {"sketch": H.sketch_fidelity(g, h.sketch, placed_centroids),
                                       "quadratic": H.sketch_fidelity(g, quad, placed_centroids)}
                fh.write(json.dumps(row, default=str) + "\n")
                fh.flush()
                rows.append(row)
                print(json.dumps({k: row[k] for k in ("design", "program", "seed", "arm", "alpha", "J", "wall_s")}),
                      flush=True)
    fh.close()
    summary = summarize(rows)
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps(summary, default=str), flush=True)


def summarize(rows: list) -> dict:
    """Paired comparisons of the arms (exploratory: medians, wins, one-sided Wilcoxon), DA0 and the check."""
    from scipy.stats import wilcoxon
    by = {}
    for r in rows:
        by.setdefault((r["design"], r["program"], r["seed"]), {})[r["arm"]] = r
    full = [v for v in by.values() if all(k in v and math.isfinite(v[k]["J"]) for k in ARMS)]
    out = {"cases": len(full), "cases_alpha_gt_0": sum(v["centre"]["alpha"] > 0 for v in full)}
    for x, y in (("sketch", "centre"), ("quadratic", "centre"), ("sketch", "quadratic")):
        for subset, cases in (("all", full), ("alpha>0", [v for v in full if v["centre"]["alpha"] > 0])):
            d = np.array([v[x]["J"] - v[y]["J"] for v in cases])
            if len(d) == 0:
                continue
            nz = d[np.abs(d) > 1e-12]
            p = float(wilcoxon(nz, alternative="less").pvalue) if len(nz) >= 5 else None
            out["%s-%s (%s)" % (x, y, subset)] = {"n": len(d), "median_delta": float(np.median(d)),
                                                    "mean_delta": float(d.mean()), "wins": int((d < -1e-12).sum()),
                                                    "losses": int((d > 1e-12).sum()), "p_less": p}
    same = [v for v in full if v["centre"]["alpha"] == 0.0]
    out["determinism_alpha0"] = {"n": len(same), "identical": sum(v["sketch"]["J"] == v["quadratic"]["J"] for v in same)}
    fid = [v["centre"].get("fidelity") for v in full if v["centre"].get("fidelity")]
    if fid:
        fs, fq = np.array([f["sketch"] for f in fid]), np.array([f["quadratic"] for f in fid])
        out["DA0_fidelity"] = {"n": len(fid), "sketch_median": float(np.median(fs)), "quadratic_median": float(np.median(fq)),
                               "sketch_closer": int((fs < fq).sum())}
    for arm in ARMS:
        out["mean_J_" + arm] = float(np.mean([v[arm]["J"] for v in full])) if full else None
    return out


if __name__ == "__main__":
    main()
