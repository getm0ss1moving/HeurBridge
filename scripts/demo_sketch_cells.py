#!/usr/bin/env python3
"""Demo 2 (owner's request, 30 Sep; exploratory, no claim): a reinforced cell-level sketch, and the DREAMPlace inputs
that can carry it.

Demo 1 (`demo_sketch_start.py`): starting DREAMPlace from the bridge's cluster sketch changes nothing, because
DREAMPlace starts with a density weight ~1e-4 of the wirelength's (params.density_weight = 8e-5 times the gradient
ratio, PlaceObj.initialize_density_weight): the first few hundred iterations pull every cell to a wirelength-optimal
clump, which erases any start, before the density penalty spreads them again.

Reinforced sketch ("cell instructions").  Each cluster's cells are spread over the cluster's own area (total cell
area / target density, a square around the cluster's sketch position) instead of being stacked on one point, and
within that square each cell sits where its outside connections pull it (macros and IOs at their positions, cells of
other clusters at their clusters' positions; cells assigned to grid slots by column-then-row order of their pull).
The quadratic control gets the same construction around its own cluster positions.

Arms (the same 64 bridge-refined layouts and the same J as demo 1 / E0):
  centre        cells start at the die centre (today's f1)
  cells_sketch  cells start at the reinforced sketch, default schedule
  cells_quad    cells start at the reinforced quadratic sketch (control)
  keep_centre   centre start, initial density weight x KEEP (control for the next two)
  keep_sketch   reinforced sketch start, density weight x KEEP: DREAMPlace keeps the start instead of collapsing it
  keep_quad     reinforced quadratic start, density weight x KEEP (control)
  infl_sketch   centre start; cells inflated where the reinforced sketch predicts routing congestion (RUDY), via
                the cell sizes DREAMPlace reads (.nodes); J is measured with the real cell sizes
  infl_quad     the same with the quadratic sketch's prediction (control)

Only this process changes DREAMPlace's parameters or cell sizes; the evaluation code on G0''s path is unchanged.

  python scripts/demo_sketch_cells.py --designs ibm04,ibm06 --runs runs/seed_trackA_dp --e0-demo runs/e0_demo \
      --bridge checkpoints/algR_trackA_final/best.pt --out runs/demo_sketch2 [--keep 80] [--pilot 2]
  python scripts/demo_sketch_cells.py --report runs/demo_sketch2 --out reports/demo_sketch_cells.md
"""

import argparse
import contextlib
import copy
import json
import math
import re
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
from heurbridge.pipeline.evaluators import cluster_centroids, track_a_final  # noqa: E402

ARMS = ("centre", "cells_sketch", "cells_quad", "keep_centre", "keep_sketch", "keep_quad", "infl_sketch", "infl_quad")
DENSITY = 0.9                       # DREAMPlace target_density of our f1


@contextlib.contextmanager
def dreamplace_params(**over):
    """Override DREAMPlace parameters (``eval.dreamplace.params``) inside this process only."""
    from heurbridge.eval import dreamplace as DP
    orig = DP.params

    def params(*a, **kw):
        p = orig(*a, **kw)
        p.update(over)
        return p
    DP.params = params
    try:
        yield
    finally:
        DP.params = orig


def cell_sketch(design, layout, cluster_of, cluster_pos, density=DENSITY):
    """(N_obj,2) normalized centres for every clustered cell: each cluster's cells spread over a square of the
    cluster's area / density around its position, placed by the direction of their outside connections."""
    d = design
    wh = d.core_wh
    cl = np.asarray(cluster_of)
    cpos = np.asarray(cluster_pos, np.float64)
    pos = np.array(layout.pos, np.float64)
    m = cl >= 0
    obj_pos = pos.copy()
    obj_pos[m] = cpos[cl[m]]                              # cells at their cluster's position
    # outside pull: for each pin of a clustered cell, the mean position of its net's pins outside its cluster
    net_of = d.net_of_pin()
    pin_obj = d.pin_obj
    pin_cl = np.where(m[pin_obj], cl[pin_obj], -1)
    npin = len(pin_obj)
    pull_sum = np.zeros((d.n_objects, 2))
    pull_cnt = np.zeros(d.n_objects)
    ok_pin = np.isfinite(obj_pos[pin_obj]).all(1) & (net_of >= 0)
    for k in range(d.n_nets):
        pins = d.pin_idx[d.net_ptr[k]:d.net_ptr[k + 1]]
        pins = pins[ok_pin[pins]]
        if len(pins) < 2:
            continue
        pc = pin_cl[pins]
        for c in np.unique(pc[pc >= 0]):
            inside, outside = pins[pc == c], pins[pc != c]
            if len(outside) == 0:
                continue
            tgt = obj_pos[pin_obj[outside]].mean(0)
            objs = pin_obj[inside]
            np.add.at(pull_sum, objs, tgt)
            np.add.at(pull_cnt, objs, 1.0)
    out = np.full((d.n_objects, 2), np.nan)
    for c in range(len(cpos)):
        cells = np.flatnonzero(cl == c)
        if len(cells) == 0:
            continue
        side = math.sqrt(float(d.area[cells].sum()) / density)            # absolute units
        half = np.array([side / wh[0], side / wh[1]]) / 2.0               # normalized half-extent
        centre = cpos[c]
        pull = np.where(pull_cnt[cells, None] > 0, pull_sum[cells] / np.maximum(pull_cnt[cells, None], 1), centre)
        tgt = centre + np.clip(pull - centre, -half, half)
        k = int(math.ceil(math.sqrt(len(cells))))
        gx = (np.arange(k) + 0.5) / k * 2 * half[0] - half[0]
        gy = (np.arange(k) + 0.5) / k * 2 * half[1] - half[1]
        order = np.lexsort((cells, tgt[:, 0]))                           # by pull x (ties: object index)
        for col in range(k):
            chunk = order[col * k:(col + 1) * k]
            if len(chunk) == 0:
                break
            chunk = chunk[np.lexsort((cells[chunk], tgt[chunk, 1]))]      # within the column by pull y
            out[cells[chunk], 0] = centre[0] + gx[col]
            out[cells[chunk], 1] = centre[1] + gy[:len(chunk)]
    return np.clip(out, 0.0, 1.0)


def with_positions(layout, pos):
    out = layout.copy()
    ok = np.isfinite(pos).all(1)
    out.pos[ok] = pos[ok]
    return out


def inflation(design, layout, cell_pos, q=0.9, cap=1.3, budget=0.10):
    """(N_obj,) width factors from the sketch's routing hot spots, relative to the sketch itself: a cell whose GCell
    RUDY utilization u exceeds the q-quantile u_q over all cells gets 1 + (u / u_q - 1), at most ``cap``; the added
    area is scaled down to at most ``budget`` of the cell area.  (A bunched sketch predicts congestion almost
    everywhere in absolute terms, so the rule ranks cells instead.)"""
    import torch
    from heurbridge.eval import f0
    lay = with_positions(layout, cell_pos)
    ctx = f0.F0Context(design, lay.orient)
    p = torch.as_tensor(lay.pos, dtype=torch.float32)
    r = ctx.rudy(p)
    u = torch.maximum(r["dem_h"] / r["cap_h"].clamp_min(1e-12), r["dem_v"] / r["cap_v"].clamp_min(1e-12))[0].numpy()
    nx, ny = u.shape
    cells = np.flatnonzero(np.isfinite(cell_pos).all(1))
    ix = np.clip((cell_pos[cells, 0] * nx).astype(int), 0, nx - 1)
    iy = np.clip((cell_pos[cells, 1] * ny).astype(int), 0, ny - 1)
    uc = u[ix, iy]
    thr = float(np.quantile(uc, q))
    f = np.ones(design.n_objects)
    if thr > 0:
        f[cells] = np.clip(np.where(uc > thr, uc / thr, 1.0), 1.0, cap)
    area = design.area[cells].sum()
    added = float(((f - 1) * design.area).sum() / max(area, 1e-12))
    if added > budget:
        f = 1.0 + (f - 1.0) * budget / added
    return f, {"cells_inflated": int((f > 1.0).sum()), "threshold_u": thr,
               "area_added_frac": float(((f - 1) * design.area).sum() / max(area, 1e-12))}


def inflated_run(final, design, layout, factors, run_id, workdir, cluster_of):
    """DREAMPlace with cells widened by ``factors`` (the sizes it reads), metrics with the real cell sizes."""
    from heurbridge.eval.dreamplace import run_dreamplace_f1
    from heurbridge.eval.f1 import trackA_metrics
    di = copy.copy(design)
    di.size = design.size.copy()
    di.size[:, 0] *= factors
    work = Path(workdir) / run_id
    work.mkdir(parents=True, exist_ok=True)
    out, placed = run_dreamplace_f1(di, layout, work, None, gpu=final.gpu, iters=final.iters, seed=final.seed,
                                    timeout=final.timeout_s)
    rec = {"run_id": run_id, "backend": "dreamplace", "returncode": out["returncode"], "failure": out.get("failure"),
           "runtime_s": out["wall_s"], "unchecked": out["unchecked"], "gp_overflow": out.get("gp_overflow"),
           "macro_max_shift": out.get("macro_max_shift")}
    if placed is not None and out.get("failure") is None:
        m = trackA_metrics(design, placed, None)                 # the real cell sizes at the placed centres
        rec.update({"hpwl_um": m["hpwl"], "rudy_overflow": m["rudy_overflow"], "rudy_overflow_ratio": m["rudy_overflow_ratio"],
                    "rudy_peak": m["rudy_peak"], "density_overflow": m["density_overflow"],
                    "rudy_of_pct": 100.0 * m["rudy_overflow_ratio"],
                    "cluster_pos": cluster_centroids(design, placed, cluster_of).tolist()})
    (work / "record.json").write_text(json.dumps(rec, indent=1, default=str))
    return rec


def gp_iterations(workdir: Path, run_id: str):
    f = workdir / run_id / "dreamplace.log"
    if not f.exists():
        return None
    it = re.findall(r"DREAMPlace - iteration\s+(\d+),", f.read_text(errors="replace"))
    return int(it[-1]) if it else None


def main():
    from demo_sketch_start import e0_alphas
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--designs", default="ibm04,ibm06")
    ap.add_argument("--runs", default="runs/seed_trackA_dp")
    ap.add_argument("--e0-demo", default="runs/e0_demo")
    ap.add_argument("--bridge", default="checkpoints/algR_trackA_final/best.pt")
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--K", type=int, default=20)
    ap.add_argument("--keep", type=float, default=100.0, help="density-weight multiplier of the keep_* arms")
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--out", default="runs/demo_sketch2")
    ap.add_argument("--limit", type=int, default=0, help="first N cases per design (0 = all)")
    a = ap.parse_args()
    from train_bridge import load_bundle
    from heurbridge.eval.dreamplace import params as dp_params
    base_dw = dp_params("x", "y")["density_weight"]
    arms = [x for x in a.arms.split(",") if x]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    write_meta(out, "demo_sketch_cells", a.designs, config=vars(a), campaign="demo_sketch_cells (exploratory)",
               base_density_weight=base_dw)
    rows_path = out / "rows.jsonl"
    rows = [json.loads(l) for l in rows_path.read_text().splitlines()] if rows_path.exists() else []
    done = {(r["design"], r["program"], r["seed"], r["arm"]) for r in rows}
    model = load_bridge(a.bridge)
    fh = open(rows_path, "a")
    for name in a.designs.split(","):
        b = load_bundle(a.suite, name, a.runs)
        g, des = b.graph, b.design
        e0 = Path(a.e0_demo)
        srcs = BD.run_sources(b, all_programs(), a.seeds, cache=e0 / ("spec_%s" % name) / "cache")
        alphas = e0_alphas(e0, name)
        final = track_a_final("dreamplace", cluster_of=b.cluster_of)
        baseline = cost.Baseline.from_records(des.id, json.loads((Path(a.runs) / des.id / "baseline.json").read_text())["records"])
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
                continue
            sk = H.guarded_sketch(g, src, end, alpha)
            qd = source_nodes(g, dep)[g.cluster_nodes]
            cells = {"sketch": cell_sketch(des, dep, b.cluster_of, sk), "quad": cell_sketch(des, dep, b.cluster_of, qd)}
            for arm in arms:
                key = (des.id, pid, s, arm)
                if key in done:
                    continue
                rid = "%s.%s.s%d.%s" % (name, pid, s, arm)
                t0 = time.time()
                extra = {}
                if arm == "centre":
                    rec = final.evaluate(des, dep, rid, out / "work")
                elif arm.startswith("cells_") or arm in ("keep_sketch", "keep_quad"):
                    which = arm.split("_")[1]
                    over = {"random_center_init_flag": 0}
                    if arm.startswith("keep_"):
                        over["density_weight"] = base_dw * a.keep
                    with dreamplace_params(**over):
                        rec = final.evaluate(des, with_positions(dep, cells[which]), rid, out / "work")
                elif arm == "keep_centre":
                    with dreamplace_params(density_weight=base_dw * a.keep):
                        rec = final.evaluate(des, dep, rid, out / "work")
                elif arm.startswith("infl_"):
                    f, extra = inflation(des, dep, cells[arm.split("_")[1]])
                    rec = inflated_run(final, des, dep, f, rid, out / "work", b.cluster_of)
                else:
                    raise ValueError(arm)
                c = final.score(rec, baseline)
                row = {"design": des.id, "program": pid, "seed": s, "arm": arm, "alpha": alpha, "J": c.J_inf, "J_raw": c.J,
                       "terms": {t: v.get("raw") for t, v in c.terms.items()}, "failure": rec.get("failure"),
                       "gp_overflow": rec.get("gp_overflow"), "gp_iterations": gp_iterations(out / "work", rid),
                       "wall_s": round(time.time() - t0, 1), **({"inflation": extra} if extra else {})}
                if rec.get("cluster_pos") is not None:
                    cp = np.asarray(rec["cluster_pos"])
                    row["fidelity"] = {"sketch": H.sketch_fidelity(g, sk, cp), "quad": H.sketch_fidelity(g, qd, cp)}
                fh.write(json.dumps(row, default=str) + "\n")
                fh.flush()
                rows.append(row)
                print(json.dumps({k: row[k] for k in ("design", "program", "seed", "arm", "J", "gp_iterations", "wall_s")}),
                      flush=True)
    fh.close()
    s = summarize(rows, arms)
    (out / "summary.json").write_text(json.dumps(s, indent=1, default=str))
    print(json.dumps(s, default=str), flush=True)


PAIRS = (("cells_sketch", "centre"), ("cells_quad", "centre"), ("cells_sketch", "cells_quad"),
         ("keep_sketch", "keep_centre"), ("keep_quad", "keep_centre"), ("keep_sketch", "keep_quad"),
         ("keep_sketch", "centre"), ("infl_sketch", "centre"), ("infl_quad", "centre"), ("infl_sketch", "infl_quad"))


def summarize(rows, arms=ARMS):
    from scipy.stats import wilcoxon
    by = {}
    for r in rows:
        by.setdefault((r["design"], r["program"], r["seed"]), {})[r["arm"]] = r
    out = {"cases": len(by)}
    for arm in arms:
        v = [c[arm] for c in by.values() if arm in c]
        J = [r["J"] for r in v if math.isfinite(r["J"])]
        it = [r["gp_iterations"] for r in v if r.get("gp_iterations") is not None]
        out[arm] = {"n": len(v), "finite": len(J), "mean_J": float(np.mean(J)) if J else None,
                    "median_iterations": float(np.median(it)) if it else None,
                    "mean_rwl": float(np.mean([r["terms"].get("rwl") for r in v if r["terms"].get("rwl")])) if v else None,
                    "mean_of": float(np.mean([r["terms"].get("of") for r in v if r["terms"].get("of") is not None])) if v else None}
    for x, y in PAIRS:
        if x not in arms or y not in arms:
            continue
        cs = [c for c in by.values() if x in c and y in c and math.isfinite(c[x]["J"]) and math.isfinite(c[y]["J"])]
        d = np.array([c[x]["J"] - c[y]["J"] for c in cs])
        if len(d) == 0:
            continue
        nz = d[np.abs(d) > 1e-12]
        out["%s-%s" % (x, y)] = {"n": len(d), "median_delta": float(np.median(d)), "mean_delta": float(d.mean()),
                                 "wins": int((d < -1e-12).sum()), "losses": int((d > 1e-12).sum()),
                                 "p_less": float(wilcoxon(nz, alternative="less").pvalue) if len(nz) >= 5 else None}
    return out


def report(run_dir: Path, out_md: Path) -> None:
    from heurbridge.reporting import METRIC_CONVENTIONS
    rows = [json.loads(l) for l in (run_dir / "rows.jsonl").read_text().splitlines() if l.strip()]
    meta = json.loads((run_dir / "meta.json").read_text())
    arms = [x for x in (meta.get("config") or {}).get("arms", ",".join(ARMS)).split(",") if x]
    sm = summarize(rows, arms)
    keep = (meta.get("config") or {}).get("keep")
    L = ["# Demo 2: a reinforced cell-level sketch, and the DREAMPlace inputs that can carry it", "",
         "| Field | Value |", "|---|---|", "| Report | demo_sketch_cells |", "| Date | %s |" % time.strftime("%Y-%m-%d %H:%M"),
         "| Node | 231 (RTX 4090, GPU 4) |",
         "| Track | A (DREAMPlace f1: GP + LG with the macros fixed, f0 metrics; J on the seeding campaign's M1 scale) |",
         "| HeurBridge version / git | %s / %s |" % (meta.get("heurbridge_version"), meta.get("git_sha")),
         "| Metric conventions | %s |" % METRIC_CONVENTIONS, "| Feeds gate | none (owner's request, 30 Sep; exploratory) |",
         "| Pre-registered test | - |", "| alpha-ledger entry | - |", "| Status of the claim | no claim (exploratory demo) |", "",
         "## Setup", "",
         "The E0 demo's 64 bridge-refined macro layouts (ibm04, ibm06), as in demo 1 (`reports/demo_sketch_start.md`). "
         "Each is placed by DREAMPlace in every arm below; J is the E0 cost. The reinforced sketch spreads each cluster's "
         "cells over the cluster's own area (total cell area / 0.9, a square around the cluster's sketch position) and "
         "orders them inside it by where their outside connections pull them. keep_* arms multiply DREAMPlace's initial "
         "density weight (8e-5 x the wirelength/density gradient ratio) by %s, so the density penalty is felt from the "
         "first iteration and the start is not first collapsed into a wirelength-optimal clump. infl_* arms widen cells "
         "where the sketch's RUDY utilization exceeds 1 (factor 1 + (u - 1), at most 1.5), through the cell sizes "
         "DREAMPlace reads; J is measured with the real sizes." % keep, "",
         "## Results", "", "| arm | n | mean J | mean rWL term | mean OF term | median GP iterations |", "|---|---|---|---|---|---|"]
    for arm in arms:
        v = sm.get(arm) or {}
        L.append("| %s | %s | %s | %s | %s | %s |" % (arm, v.get("n"), "%.4f" % v["mean_J"] if v.get("mean_J") is not None else "-",
                                                    "%.4g" % v["mean_rwl"] if v.get("mean_rwl") else "-",
                                                    "%.4f" % v["mean_of"] if v.get("mean_of") is not None else "-",
                                                    "%.0f" % v["median_iterations"] if v.get("median_iterations") else "-"))
    L += ["", "| comparison (paired J difference; negative = first is better) | n | median | mean | wins | losses | "
          "one-sided p (first < second) |", "|---|---|---|---|---|---|---|"]
    for x, y in PAIRS:
        k = "%s-%s" % (x, y)
        if k in sm:
            v = sm[k]
            L.append("| %s | %d | %+.4f | %+.4f | %d | %d | %s |" % (k, v["n"], v["median_delta"], v["mean_delta"], v["wins"],
                                                                v["losses"], "%.3g" % v["p_less"] if v["p_less"] is not None else "-"))
    L += ["", "## Reproduce", "", "```",
          "python scripts/demo_sketch_cells.py --designs ibm04,ibm06 --runs runs/seed_trackA_dp --e0-demo runs/e0_demo "
          "--bridge checkpoints/algR_trackA_final/best.pt --out runs/demo_sketch2 --keep %s" % keep,
          "python scripts/demo_sketch_cells.py --report runs/demo_sketch2 --out reports/demo_sketch_cells.md", "```", ""]
    out_md.write_text("\n".join(L))
    print("REPORT_OK", out_md)


if __name__ == "__main__":
    if "--report" in sys.argv:
        i = sys.argv.index("--report")
        report(Path(sys.argv[i + 1]), Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv
               else Path("reports/demo_sketch_cells.md"))
    else:
        main()
