#!/usr/bin/env python3
"""T5 demo endpoint: post-bridge portfolio J of each arm's final portfolio on designs the evolution never saw.

An arm is an evolution run directory (scripts/run_evolution.py --out).  Its final portfolio is chosen from its last
population file by the population's own rule (greedy facility-location top-q over the D_evo post-bridge costs B,
island clones excluded; a +inf cost counts as 1e6 here, as in the fitness's standalone term); the seed portfolio is the
same rule applied to the first arm's population_g0.json.  Every program x design x seed: the program in the sandbox
(view without the design's identity) -> P_M -> the frozen bridge + guard (alphas 0, 0.25, 0.5, 1 scored by DREAMPlace
f1, J against the --runs seeding baseline, as E0) -> post-bridge J; any failure is +inf and named.  Portfolio J of a
(design, seed) unit = min over the portfolio's programs.  Paired one-sided Wilcoxon (heurbridge.stats.paired: +inf
kept) of each arm against the seed portfolio and against the control arm, Holm within each arm's two comparisons;
exploratory: nominal and Holm p are reported, no alpha-ledger entry.  Rows are cached per (program sha256, design,
seed) in <out>/rows.jsonl: the seed programs shared by every arm are evaluated once, and a rerun resumes.

  python scripts/eval_t5_portfolio.py --arms runs/evo/t5demo_hb,runs/evo/t5demo_ctrl --control t5demo_ctrl \
      --designs ibm04,ibm06 --seeds 3 --bridge checkpoints/algR_trackA_final/best.pt --runs runs/seed_trackA_dp \
      --out runs/evo/t5demo_V
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heurbridge.bridge.sample import refine  # noqa: E402
from heurbridge.bridge.train import load_bridge  # noqa: E402
from heurbridge.evolve.fitness import greedy_prune  # noqa: E402
from heurbridge.meta import write_meta  # noqa: E402
from heurbridge.stats.paired import holm, wilcoxon_less  # noqa: E402

BIG = 1e6


def population_files(arm: Path) -> list:
    return sorted(arm.glob("population_g*.json"), key=lambda p: int(p.stem.split("_g")[1]))


def portfolio(pop: dict, q: int) -> list:
    """[(id, sha256)] of the population's portfolio (Population.portfolio's rule, +inf as 1e6)."""
    progs = pop["programs"]
    ids = [i for i, r in progs.items() if r.get("B") and "@i" not in i]
    if not ids:
        return []
    B = np.array([progs[i]["B"] for i in ids], float)
    B = np.where(np.isfinite(B), B, BIG)
    return [(ids[k], progs[ids[k]]["sha256"]) for k in greedy_prune(B, B.max(0) + 1e-6, q)]


def unit_table(rows: dict, members: list, designs: list, seeds: int) -> np.ndarray:
    """Portfolio J per (design, seed) unit, in design-major order; +inf when every member failed."""
    out = []
    for d in designs:
        for s in range(seeds):
            vals = [rows[(sha, d, s)]["J_post"] for _, sha in members if (sha, d, s) in rows]
            out.append(min(vals) if vals else np.inf)
    return np.array(out, float)


def main():
    import run_evolution as RE
    from train_bridge import load_bundle
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", required=True, help="evolution run directories (comma separated)")
    ap.add_argument("--control", default="", help="name (directory basename) of the control arm")
    ap.add_argument("--designs", required=True)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--q", type=int, default=8, help="portfolio size (the population's q)")
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--runs", default="runs/seed_trackA_dp")
    ap.add_argument("--bridge", required=True)
    ap.add_argument("--K", type=int, default=20)
    ap.add_argument("--cpu-s", type=float, default=60.0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    arms = [Path(p) for p in a.arms.split(",")]
    designs = a.designs.split(",")
    write_meta(out, "t5_portfolio_eval", a.designs, config=vars(a), campaign="T5 demo endpoint")
    ports = {"seed": portfolio(json.loads((arms[0] / "population_g0.json").read_text()), a.q)}
    srcs = {}
    for arm in arms:
        last = population_files(arm)[-1]
        ports[arm.name] = portfolio(json.loads(last.read_text()), a.q)
        for p in (arm / "programs").glob("*.py"):
            srcs.setdefault(p.stem, p.read_text())
    (out / "portfolios.json").write_text(json.dumps(ports, indent=1))
    need = sorted({sha for m in ports.values() for _, sha in m})
    missing = [s for s in need if s not in srcs]
    if missing:
        sys.exit("program sources missing for %d portfolio members (first %s)" % (len(missing), missing[0]))
    rows_path = out / "rows.jsonl"
    rows = {}
    if rows_path.exists():
        for line in rows_path.read_text().splitlines():
            r = json.loads(line)
            rows[(r["sha256"], r["design"], r["seed"])] = r
    model = load_bridge(a.bridge)
    t0 = time.time()
    with open(rows_path, "a") as fh:
        for d in designs:
            b = load_bundle(a.suite, d, a.runs)
            b.view.misc.pop("design_id", None)
            guard = RE.guard_fn(b, "dp", a.runs, out / "dp_work")
            ev = RE.EvoEvaluator([b], [guard], model, a.seeds, a.K, a.cpu_s)
            for sha in need:
                for s in range(a.seeds):
                    if (sha, d, s) in rows:
                        continue
                    lay, why, cpu = ev.run(srcs[sha], b, s)
                    r = {"sha256": sha, "design": d, "seed": s, "cpu_s": cpu, "failure": why}
                    if lay is None:
                        r.update({"J_post": float("inf"), "J_raw": float("inf"), "alpha": None})
                    else:
                        res = refine(model, b.graph, b.design, [lay], guard, K=a.K)[0]
                        r.update({"J_post": float(min(res.scores)), "J_raw": float(res.scores[0]),
                                  "alpha": float(res.alpha) if res.alpha is not None else None})
                    rows[(sha, d, s)] = r
                    fh.write(json.dumps(r) + "\n")
                    fh.flush()
            print(json.dumps({"design": d, "rows": len(rows), "elapsed_s": round(time.time() - t0)}), flush=True)
    units = {name: unit_table(rows, m, designs, a.seeds) for name, m in ports.items()}
    res = {"designs": designs, "seeds": a.seeds, "q": a.q, "portfolio_size": {k: len(v) for k, v in ports.items()},
           "mean_J": {k: float(np.mean(np.where(np.isfinite(v), v, np.nan))) for k, v in units.items()},
           "failed_units": {k: int((~np.isfinite(v)).sum()) for k, v in units.items()},
           "per_design": {k: {d: [float(x) for x in v[i * a.seeds:(i + 1) * a.seeds]] for i, d in enumerate(designs)}
                          for k, v in units.items()},
           "tests": {}}
    for arm in arms:
        if arm.name == a.control:
            continue
        t = {"vs_seed": wilcoxon_less(units[arm.name], units["seed"])}
        if a.control and a.control in units:
            t["vs_control"] = wilcoxon_less(units[arm.name], units[a.control])
        t["holm"] = holm({k: v["p"] for k, v in t.items()})
        res["tests"][arm.name] = t
    if a.control and a.control in units:
        res["tests"][a.control] = {"vs_seed": wilcoxon_less(units[a.control], units["seed"])}
    (out / "summary.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({k: res[k] for k in ("mean_J", "failed_units", "tests")}, default=float), flush=True)


if __name__ == "__main__":
    main()
