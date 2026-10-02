#!/usr/bin/env python3
"""S2 look-ahead ranking check: does a cell-stage prediction order macro layouts the way DREAMPlace's f1 J does?

Diagnostic, no claim.  The S2 step of the sketch redesign has a distance bar (DA0 ratio <= 0.5, missed:
reports/sketch_predictor_s2.md) and a rank part that was never computed: Kendall tau between the predicted and the
actual f1 J of the labelled layouts.  This script computes it on given designs (the validation designs ibm04, ibm06).

Layouts: every labelled macro layout of the design (scripts/make_cell_labels.py: heuristic sources ``src``, bridge
endpoints at four alphas ``br``, the archive's elites ``el``), each placed by the Track-A f1 evaluator (DREAMPlace GP +
LG, macros fixed) with its actual J.

Predicted f1 J of a layout: every clustered standard cell is drawn from its cluster's Gaussian (centroid, second
moments; one fixed standard-normal draw per cell, shared by every predictor), then the f1 evaluator's own metrics
(eval.f1.trackA_metrics: exact HPWL and RUDY overflow) and its cost (Track-A weights, the design's seeding baseline).
Cluster predictors, from the macro layout alone:
  quad     clusters at their quadratic placement (sample.source_nodes; the S2 control), footprint spread
  s2       the S2 predictor (checkpoint): its centroids and its spreads
  s2_fp    the S2 centroids with the footprint spread (separates centroids from spreads)
  coarse   exploratory reference, not S2: the clustered netlist placed by HB-GP (eval.gp, clusters as soft cells,
           target density 0.9 as the f1 evaluator, no legalization), footprint spread
Oracle (not a predictor): placed  the placed centroids and second moments from the label.
Footprint spread: a cluster's area at the target density as a square, variance side^2 / 12 per axis.
Also ``f0``: the macro-stage surrogate (bundle scorer), the proxy the E3 calibration measured.

Per design and predictor: Kendall tau and Spearman rho with the actual J (all layouts and per kind), top-5 recall,
regret@k (actual J of the best of the k layouts the predictor ranks first minus the best actual J) against random
selection's expected regret@k, and the DA0 ratio of every cluster predictor as in train_lookahead.evaluate.
Sanity check: the actual placed cells through the same metric code reproduce the label's J.

  python scripts/eval_lookahead_rank.py --designs ibm04 --labels runs/cell_labels --runs runs/seed_trackA_dp \
      --s2 checkpoints/lookahead_s2/best.pt --device cuda --out runs/s2_rank/ibm04
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heurbridge.bridge.lookahead_net import LookaheadNet, spread_moments  # noqa: E402
from heurbridge.bridge.model import BridgeConfig  # noqa: E402
from heurbridge.bridge.sample import source_nodes  # noqa: E402
from heurbridge.eval import cost  # noqa: E402
from heurbridge.eval.f1 import trackA_metrics  # noqa: E402
from heurbridge.meta import write_meta  # noqa: E402
from heurbridge.pipeline.evaluators import DreamplaceEvaluator  # noqa: E402

KS = (1, 5, 10, 20)
PREDICTORS = ("quad", "s2", "s2_fp", "coarse", "placed", "f0")


def load_s2(path: str, device: str):
    z = torch.load(path, map_location=device, weights_only=False)
    m = LookaheadNet(BridgeConfig(**z["model_config"])).to(device)
    m.load_state_dict(z["ema"])
    m.eval()
    return m, int(z.get("step", -1))


def footprint_cov(graph, target: float) -> np.ndarray:
    """(C, 3) second moments of each cluster's area at the target density as a square (uniform: side^2 / 12)."""
    s = graph.size[graph.cluster_nodes] / math.sqrt(target)
    v = s ** 2 / 12.0
    return np.stack([v[:, 0], v[:, 1], np.zeros(len(v))], 1)


def cells_from_clusters(cid: np.ndarray, mu: np.ndarray, cov: np.ndarray, zdraw: np.ndarray) -> np.ndarray:
    """Positions of the clustered cells: cluster mean + Cholesky factor of the cluster covariance x a fixed draw."""
    vx, vy, cxy = np.maximum(cov[cid, 0], 0.0), np.maximum(cov[cid, 1], 0.0), cov[cid, 2]
    l11 = np.sqrt(vx)
    l21 = np.where(l11 > 0, cxy / np.maximum(l11, 1e-12), 0.0)
    l22 = np.sqrt(np.maximum(vy - l21 ** 2, 0.0))
    x = mu[cid, 0] + l11 * zdraw[:, 0]
    y = mu[cid, 1] + l21 * zdraw[:, 0] + l22 * zdraw[:, 1]
    return np.clip(np.stack([x, y], 1), 0.0, 1.0)


def da0(pred: np.ndarray, quad: np.ndarray, placed: np.ndarray, w: np.ndarray) -> float:
    """Area-weighted RMS distance of predicted centroids to the placed ones over the same for the quadratic placement."""
    r = math.sqrt(float((w * ((pred - placed) ** 2).sum(1)).sum() / w.sum()))
    q = math.sqrt(float((w * ((quad - placed) ** 2).sum(1)).sum() / w.sum()))
    return r / q if q > 0 else float("nan")


def rank_stats(pred, actual) -> dict:
    from scipy.stats import kendalltau, spearmanr
    pred, actual = np.asarray(pred, float), np.asarray(actual, float)
    n = len(actual)
    out = {"n": int(n)}
    if n < 3 or not np.isfinite(pred).all():
        return out
    out["kendall_tau"] = float(kendalltau(pred, actual)[0])
    out["spearman_rho"] = float(spearmanr(pred, actual)[0])
    k5 = min(5, n)
    out["top5_recall"] = len(set(np.argsort(actual, kind="stable")[:k5]) & set(np.argsort(pred, kind="stable")[:k5])) / k5
    best, srt = float(actual.min()), np.sort(actual)
    for k in KS:
        if k >= n:
            continue
        pick = np.argsort(pred, kind="stable")[:k]
        out["regret@%d" % k] = float(actual[pick].min() - best)
        p = np.array([math.comb(n - j, k - 1) for j in range(1, n + 1)], float) / math.comb(n, k)
        out["random_regret@%d" % k] = float((srt * p).sum() - best)        # E[min of k random picks] - best
    return out


def coarse_clusters(b, lay, device: str, target: float, iters: int):
    """Cluster positions from HB-GP on the clustered design (clusters = soft cells), macros held at ``lay``."""
    from heurbridge.eval.gp import GPConfig, place
    cd = b.scorer.cd
    lc = cd.to_layout(lay, np.full((cd.n_clusters, 2), 0.5))
    placed, info = place(cd.design, lc, GPConfig(iters=iters, target_density=target, overflow_stop=0.1, legalize=False,
                                                 device=device, seed=0), log=lambda *_: None)
    return np.asarray(placed.pos[cd.n_keep:], float), {k: info.get(k) for k in ("overflow", "iters") if k in info}


def run_design(name: str, a, model, s2_step: int, out: Path) -> dict:
    from train_bridge import load_bundle
    t0 = time.time()
    b = load_bundle(a.suite, name, a.runs)
    g, des = b.graph, b.design
    z = np.load(Path(a.labels) / (des.id + ".npz"), allow_pickle=False)
    rows = [r for r in json.loads(str(z["rows"])) if "k" in r]
    if a.limit:
        rows = rows[:a.limit]
    baseline = cost.Baseline.from_records(des.id, json.loads((Path(a.runs) / des.id / "baseline.json").read_text())["records"])
    ev = DreamplaceEvaluator(cluster_of=b.cluster_of)
    mm = des.is_macro & ~des.is_fixed
    cid_all = np.asarray(b.cluster_of)
    cell_idx = np.flatnonzero(cid_all >= 0)
    cid = cid_all[cell_idx]
    zdraw = np.random.default_rng(a.seed).standard_normal((len(cell_idx), 2))
    cl = g.cluster_nodes
    w = g.area_w[cl]
    fp = footprint_cov(g, a.target)
    gt = g.tensors(a.device) if model is not None else None
    per, da = [], {p: [] for p in ("s2", "coarse")}
    sanity = []
    for i, r in enumerate(rows):
        k = r["k"]
        lay = b.base.copy()
        lay.pos[mm] = z["macros"][k]
        lay.orient[mm] = z["macro_orient"][k]
        x = source_nodes(g, lay)
        quad = x[cl]
        placed_mu, placed_cov = z["cluster_pos"][k].astype(float), z["cluster_cov"][k].astype(float)
        mus = {"quad": (quad, fp), "placed": (placed_mu, placed_cov)}
        if model is not None:
            with torch.no_grad():
                pos, sp = model.predict(torch.as_tensor(x[None], dtype=torch.float32, device=a.device), gt)
            s2_mu = pos[0, cl].double().cpu().numpy()
            s2_cov = spread_moments(sp[0, cl].double()).cpu().numpy()
            mus["s2"], mus["s2_fp"] = (s2_mu, s2_cov), (s2_mu, fp)
            da["s2"].append(da0(s2_mu, quad, placed_mu, w))
        info = {}
        if a.coarse:
            c_mu, info = coarse_clusters(b, lay, a.device, a.target, a.coarse_iters)
            mus["coarse"] = (c_mu, fp)
            da["coarse"].append(da0(c_mu, quad, placed_mu, w))
        rec = {"k": int(k), "id": r["id"], "kind": r["kind"], "J": r["J"], "rwl_raw": (r.get("terms") or {}).get("rwl"),
               "of_raw": (r.get("terms") or {}).get("of"), "coarse_info": info}
        for p, (mu, cv) in mus.items():
            lp = lay.copy()
            lp.pos[cell_idx] = cells_from_clusters(cid, mu, cv, zdraw)
            assert np.isfinite(lp.pos).all(), (name, r["id"], p)
            m = trackA_metrics(des, lp, None, device=a.device)
            pr = {"hpwl_um": m["hpwl"], "rudy_of_pct": 100.0 * m["rudy_overflow_ratio"]}
            rec[p] = {"J": float(ev.score(pr, baseline).J), "hpwl_um": pr["hpwl_um"], "of_pct": pr["rudy_of_pct"]}
        rec["f0"] = {"J": float(b.scorer(lay))}
        if i < a.sanity:                                   # the label's own placed cells through the same code
            lp = lay.copy()
            lp.pos[z["cell_index"]] = z["cells"][k].astype(float)
            m = trackA_metrics(des, lp, None, device=a.device)
            j = float(ev.score({"hpwl_um": m["hpwl"], "rudy_of_pct": 100.0 * m["rudy_overflow_ratio"]}, baseline).J)
            sanity.append(abs(j - r["J"]) / max(abs(r["J"]), 1e-9))
        per.append(rec)
        if (i + 1) % 20 == 0 or i + 1 == len(rows):
            print(json.dumps({"design": name, "done": i + 1, "of": len(rows), "elapsed_s": round(time.time() - t0)}),
                  flush=True)
    with open(out / ("rows_%s.jsonl" % name), "w") as fh:
        for rec in per:
            fh.write(json.dumps(rec, default=float) + "\n")
    actual = np.array([p["J"] for p in per])
    kinds = np.array([p["kind"] for p in per])
    res = {"design": name, "n": len(per), "kinds": {k: int((kinds == k).sum()) for k in sorted(set(kinds))},
           "s2_checkpoint_step": s2_step, "sanity_rel_err_max": max(sanity) if sanity else None,
           "da0_median": {p: float(np.median(v)) for p, v in da.items() if v}, "rank": {}}
    for p in PREDICTORS:
        if not isinstance(per[0].get(p), dict) or "J" not in per[0][p]:
            continue
        pred = np.array([q[p]["J"] for q in per])
        res["rank"][p] = {"all": rank_stats(pred, actual)}
        for kd in ("src", "br"):
            m = kinds == kd
            if m.sum() >= 10:
                res["rank"][p][kd] = rank_stats(pred[m], actual[m])
        if p not in ("f0",):
            hp = np.array([q[p]["hpwl_um"] for q in per])
            of = np.array([q[p]["of_pct"] for q in per])
            rw = np.array([q["rwl_raw"] if q["rwl_raw"] is not None else np.nan for q in per])
            orw = np.array([q["of_raw"] if q["of_raw"] is not None else np.nan for q in per])
            if np.isfinite(rw).all():
                res["rank"][p]["hpwl_vs_actual_hpwl"] = rank_stats(hp, rw)
            if np.isfinite(orw).all():
                res["rank"][p]["of_vs_actual_of"] = rank_stats(of, orw)
    res["wall_s"] = round(time.time() - t0, 1)
    return res


def report(summaries: list, out_md: Path, title: str, note: str = "") -> None:
    """Markdown report of one or more summary.json files.  The bar is the one fixed before any S2 result
    (HEURBRIDGE_PLAN_downstream_aware.md, S2 row): DA0 ratio <= 0.5, Kendall tau >= 0.5 per design, top-1 regret
    <= 25 % of random."""
    from heurbridge.reporting import METRIC_CONVENTIONS
    res = [r for s in summaries for r in json.loads(Path(s).read_text())]
    names = {"quad": "quadratic placement (S2 control)", "s2": "S2 predictor", "s2_fp": "S2 centroids, footprint spread",
             "coarse": "HB-GP coarse placement (exploratory reference)", "placed": "placed clusters (oracle)",
             "f0": "f0 surrogate (macro stage)"}
    L = ["# %s" % title, "", "| Field | Value |", "|---|---|", "| Report | lookahead_rank |",
         "| Date | %s |" % time.strftime("%Y-%m-%d %H:%M"), "| Node | 225 (RTX 3090) |",
         "| Track | A (labels: DREAMPlace f1 placements, scripts/make_cell_labels.py) |",
         "| Metric conventions | %s |" % METRIC_CONVENTIONS, "| Feeds gate | none (S2 diagnostic) |",
         "| Pre-registered test | - (bar fixed before any S2 result: local plan, S2 row) |", "| alpha-ledger entry | - |",
         "| Status of the claim | no claim |", ""]
    L += ["**Bar (fixed before any S2 result):** DA0 ratio <= 0.5 against the quadratic placement; Kendall tau(predicted "
          "J, actual f1 J) >= 0.5 per design; top-1 regret <= 25 % of random's.", ""]
    if note:
        L += [note, ""]
    for r in res:
        L += ["## %s (%d layouts: %s; S2 checkpoint step %s)" % (r["design"], r["n"], ", ".join(
            "%s %d" % kv for kv in r["kinds"].items()), r["s2_checkpoint_step"]), "",
              "Sanity: the label's own placed cells through the same metric code reproduce its J within a relative %.1e."
              % (r["sanity_rel_err_max"] or float("nan")), "",
              "| predictor | DA0 ratio (median) | Kendall tau, all | tau, heuristic sources | tau, bridge endpoints | "
              "top-5 recall | regret@1 / random's | regret@5 / random's | tau of HPWL | tau of overflow |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for p, v in r["rank"].items():
            a = v["all"]
            da = r["da0_median"].get(p)

            def rr(k):
                x, y = a.get("regret@%d" % k), a.get("random_regret@%d" % k)
                return "%.4f / %.4f" % (x, y) if x is not None and y else "-"
            L.append("| %s | %s | %.3f | %s | %s | %.2f | %s | %s | %s | %s |" % (
                names.get(p, p), "%.3f" % da if da is not None else ("1 (by definition)" if p == "quad" else "-"),
                a.get("kendall_tau", float("nan")),
                "%.3f" % v["src"]["kendall_tau"] if "src" in v and "kendall_tau" in v["src"] else "-",
                "%.3f" % v["br"]["kendall_tau"] if "br" in v and "kendall_tau" in v["br"] else "-",
                a.get("top5_recall", float("nan")), rr(1), rr(5),
                "%.3f" % v["hpwl_vs_actual_hpwl"]["kendall_tau"] if "hpwl_vs_actual_hpwl" in v else "-",
                "%.3f" % v["of_vs_actual_of"]["kendall_tau"] if "of_vs_actual_of" in v else "-"))
        L.append("")
    Path(out_md).write_text("\n".join(L) + "\n")


def main():
    if "--report" in sys.argv:
        ap = argparse.ArgumentParser()
        ap.add_argument("--report", nargs="+", required=True)
        ap.add_argument("--title", default="Sketch redesign S2: ranking check")
        ap.add_argument("--note", default="")
        ap.add_argument("--out", required=True)
        a = ap.parse_args()
        report(a.report, Path(a.out), a.title, a.note)
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--designs", default="ibm04,ibm06")
    ap.add_argument("--labels", default="runs/cell_labels")
    ap.add_argument("--runs", default="runs/seed_trackA_dp")
    ap.add_argument("--s2", default="checkpoints/lookahead_s2/best.pt", help="S2 checkpoint ('' skips the S2 rows)")
    ap.add_argument("--coarse", type=int, default=1, help="1: also the HB-GP coarse placement reference")
    ap.add_argument("--coarse-iters", type=int, default=1000)
    ap.add_argument("--target", type=float, default=0.9, help="target density (the f1 evaluator's DREAMPlace value)")
    ap.add_argument("--sanity", type=int, default=10, help="layouts whose placed cells are re-scored (sanity check)")
    ap.add_argument("--limit", type=int, default=0, help="first N labelled layouts per design (0 = all; smoke runs)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    write_meta(out, "lookahead_rank", a.designs, config=vars(a), campaign="sketch redesign S2: ranking check")
    model, step = load_s2(a.s2, a.device) if a.s2 else (None, None)
    res = [run_design(n, a, model, step, out) for n in a.designs.split(",")]
    (out / "summary.json").write_text(json.dumps(res, indent=1, default=float))
    for r in res:
        print(json.dumps({"design": r["design"], "n": r["n"], "sanity": r["sanity_rel_err_max"], "da0": r["da0_median"],
                          "tau": {p: v["all"].get("kendall_tau") for p, v in r["rank"].items()}}), flush=True)


if __name__ == "__main__":
    main()
