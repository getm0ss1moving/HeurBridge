#!/usr/bin/env python3
"""Can a macro layout beat the tool on Track A (J < 0.45), and at what cost?  Feasibility demo (exploratory, no claim).

Every arm is scored by the registered Track-A f1 (DREAMPlace GP + LG with the macros fixed; J against the seeding
campaign's M1 baseline, 0.45 by construction) and records its wall-clock, so output and cost are reported together:

  tool         the tool's own macro layout (the seeding campaign's M1: DREAMPlace mixed-size, seed 0, then P_M), re-scored
  tool_seed<k> the tool spending more compute: DREAMPlace mixed-size with seed k, P_M, scored
  tool_rout    the tool's congestion-aware setting: mixed-size with its routability mode on, P_M, scored
  bridge_tool  the frozen bridge applied to the tool's layout, guarded by f1 (alpha 0 = the tool's layout)
  ls_tool      local search from the tool's layout: each step scores n moves (shift by a fraction of the macro's size,
               swap of two identical macros, orientation flip; each legalized by P_M) and keeps the best if it lowers J

  python scripts/beat_tool_demo.py --designs ibm01,ibm16 --runs runs/seed_trackA_dp \
      --bridge checkpoints/algR_trackA_final/best.pt --steps 12 --moves 8 --par 2 --out runs/beat_tool/demo
"""

import argparse
import contextlib
import hashlib
import json
import math
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heurbridge.core import orient as O, project  # noqa: E402
from heurbridge.eval import cost  # noqa: E402
from heurbridge.meta import write_meta  # noqa: E402
from heurbridge.pipeline.evaluators import DreamplaceEvaluator  # noqa: E402


@contextlib.contextmanager
def dreamplace_params(**over):
    """Override DREAMPlace parameters inside this process only (as scripts/demo_sketch_cells.py)."""
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


class Scorer:
    """f1 J of macro layouts (cached by macro positions and orientations), with the wall-clock of every run."""

    def __init__(self, b, baseline, work: Path, log):
        self.b, self.base, self.work, self.log = b, baseline, work, log
        self.ev = DreamplaceEvaluator(cluster_of=b.cluster_of)
        self.mm = b.design.is_macro & ~b.design.is_fixed
        self.cache, self.lock = {}, threading.Lock()
        self.f1_s = []

    def key(self, lay) -> str:
        return hashlib.sha256(lay.pos[self.mm].tobytes() + lay.orient[self.mm].tobytes()).hexdigest()

    def __call__(self, lay, tag: str) -> dict:
        k = self.key(lay)
        with self.lock:
            if k in self.cache:
                return dict(self.cache[k], cached=True)
        t0 = time.time()
        rec = self.ev.evaluate(self.b.design, lay, "%s.%s" % (tag, k[:12]), self.work)
        c = self.ev.score(rec, self.base)
        out = {"J": float(c.J_inf), "hpwl": rec.get("hpwl_um"), "of_pct": rec.get("rudy_of_pct"),
               "failure": rec.get("failure"), "f1_s": round(time.time() - t0, 2)}
        with self.lock:
            self.cache[k] = out
            self.f1_s.append(out["f1_s"])
        return dict(out, cached=False)


def moves(design, layout, rng, n: int) -> list:
    """n candidate moves from ``layout``: shift one macro by a fraction of its size (70 %), swap two identical macros
    (20 %), flip one macro (10 %)."""
    mm = np.flatnonzero(design.is_macro & ~design.is_fixed)
    eff = O.effective_size(design.size, layout.orient) / design.core_wh
    masters = design.masters or ["%.6g_%.6g" % tuple(v) for v in design.size]
    out = []
    while len(out) < n:
        lay = layout.copy()
        u = rng.random()
        i = int(rng.choice(mm))
        if u < 0.7:
            ax = int(rng.integers(2))
            k = float(rng.choice([-1.0, -0.5, -0.25, 0.25, 0.5, 1.0]))
            lay.pos[i, ax] = float(np.clip(lay.pos[i, ax] + k * eff[i, ax], eff[i, ax] / 2, 1 - eff[i, ax] / 2))
            what = "shift %+.2f" % k
        elif u < 0.9:
            same = [j for j in mm if j != i and masters[j] == masters[i] and np.allclose(design.size[j], design.size[i])]
            if not same:
                continue
            j = int(rng.choice(same))
            lay.pos[[i, j]] = lay.pos[[j, i]]
            what = "swap"
        else:
            lay.orient[i] = int(rng.choice([o for o in (O.R0, O.MX, O.MY, O.R180) if o != lay.orient[i]]))
            what = "flip"
        out.append((what, lay))
    return out


def run_design(name: str, a, model, out: Path, log) -> dict:
    from heurbridge.bridge.sample import refine
    from heurbridge.eval.dreamplace import run_dreamplace_m1
    from heurbridge.core import bookshelf
    from train_bridge import SUITES, load_bundle
    t_design = time.time()
    b = load_bundle(a.suite, name, a.runs)
    des = b.design
    rdir = Path(a.runs) / des.id
    baseline = cost.Baseline.from_records(des.id, json.loads((rdir / "baseline.json").read_text())["records"])
    work = out / "work" / des.id
    work.mkdir(parents=True, exist_ok=True)
    score = Scorer(b, baseline, work, log)
    rows = []

    def row(arm, lay_score, **kw):
        r = {"design": des.id, "arm": arm, **lay_score, **kw}
        rows.append(r)
        log(json.dumps(r))
        return r

    # the tool's layout, exactly as the seeding campaign made it (m1.npz, then P_M)
    z = np.load(rdir / "m1.npz", allow_pickle=False)
    m1 = b.base.copy()
    m1.pos, m1.orient = z["pos"], z["orient"]
    tool, rep = project.legalize_macros(des, m1)
    m1_rec = json.loads(str(z["record"]))
    res = {"design": des.id, "tool_m1_s": m1_rec.get("wall_s")}
    t0 = row("tool", score(tool, "tool"), m1_s=m1_rec.get("wall_s"))
    res["tool_J"] = t0["J"]

    # the tool with more compute: other seeds, and its routability mode
    d, l = bookshelf.load_bookshelf(SUITES[a.suite] / name / (name + ".aux"), family=a.suite)
    tool_runs = []
    for arm, seed, over in [("tool_seed%d" % s, s, {}) for s in range(1, a.tool_seeds + 1)] + \
                           ([("tool_rout", 0, {"routability_opt_flag": 1})] if a.tool_rout else []):
        with dreamplace_params(**over):
            rec, lay = run_dreamplace_m1(d, l, work / arm, seed=seed)
        if lay is None:
            row(arm, {"J": math.inf, "failure": rec.get("failure")}, m1_s=rec.get("wall_s"))
            continue
        lay_b = b.base.copy()
        lay_b.pos, lay_b.orient = lay.pos, lay.orient
        lp, rep = project.legalize_macros(des, lay_b)
        sc = score(lp, arm) if rep.ok else {"J": math.inf, "failure": "P_M failed"}
        tool_runs.append(row(arm, sc, m1_s=rec.get("wall_s")))
    res["tool_more"] = {r["arm"]: {"J": r["J"], "m1_s": r.get("m1_s")} for r in tool_runs}

    # the frozen bridge on the tool's layout, guarded by f1
    if model is not None:
        tb = time.time()
        rr = refine(model, b.graph, des, [tool], lambda lay: score(lay, "bridge")["J"], K=a.K)[0]
        res["bridge_tool"] = {"J": float(min(rr.scores)), "alpha": rr.alpha, "scores": rr.scores,
                              "wall_s": round(time.time() - tb, 1)}
        row("bridge_tool", {"J": float(min(rr.scores))}, alpha=rr.alpha, scores=rr.scores)

    # local search from the tool's layout
    rng = np.random.default_rng(a.seed)
    cur, cur_J = tool, t0["J"]
    traj, n_eval, t_ls = [{"step": 0, "evals": 0, "J": cur_J}], 0, time.time()
    with ThreadPoolExecutor(max_workers=max(1, a.par)) as pool:
        for step in range(1, a.steps + 1):
            cands = []
            for what, lay in moves(des, cur, rng, a.moves):
                lp, rep = project.legalize_macros(des, lay)
                if rep.ok:
                    cands.append((what, lp))
            scored = list(pool.map(lambda c: (c[0], c[1], score(c[1], "ls%d" % step)), cands))
            n_eval += sum(1 for s in scored if not s[2].get("cached"))
            best = min(scored, key=lambda s: s[2]["J"]) if scored else None
            if best is not None and best[2]["J"] < cur_J:
                cur, cur_J = best[1], best[2]["J"]
            traj.append({"step": step, "evals": n_eval, "J": cur_J, "move": best[0] if best else None,
                         "best_candidate_J": best[2]["J"] if best else None, "elapsed_s": round(time.time() - t_ls, 1)})
            log(json.dumps({"design": des.id, "ls": traj[-1]}))
    mm = des.is_macro & ~des.is_fixed
    res["ls_tool"] = {"J": cur_J, "evals": n_eval, "wall_s": round(time.time() - t_ls, 1), "trajectory": traj}
    np.savez(out / ("ls_best_%s.npz" % des.id), pos=cur.pos[mm], orient=cur.orient[mm], J=cur_J)
    res["f1_s_median"] = float(np.median(score.f1_s)) if score.f1_s else None
    res["wall_s"] = round(time.time() - t_design, 1)
    with open(out / ("rows_%s.jsonl" % des.id), "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, default=float) + "\n")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--designs", required=True)
    ap.add_argument("--runs", default="runs/seed_trackA_dp")
    ap.add_argument("--bridge", default="checkpoints/algR_trackA_final/best.pt", help="'' skips the bridge arm")
    ap.add_argument("--K", type=int, default=20)
    ap.add_argument("--tool-seeds", type=int, default=3, help="extra DREAMPlace mixed-size seeds (1..k)")
    ap.add_argument("--tool-rout", type=int, default=1, help="1: also the tool's routability mode")
    ap.add_argument("--steps", type=int, default=12)
    ap.add_argument("--moves", type=int, default=8)
    ap.add_argument("--par", type=int, default=2, help="f1 runs at a time (DREAMPlace processes on the GPU)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    write_meta(out, "beat_tool_demo", a.designs, config=vars(a), campaign="beat-the-tool feasibility demo (Track A)")
    log_f = open(out / "log.jsonl", "a")

    def log(s):
        print(s, flush=True)
        log_f.write(s + "\n")
        log_f.flush()
    model = None
    if a.bridge:
        from heurbridge.bridge.train import load_bridge
        model = load_bridge(a.bridge)
    res = []
    for name in a.designs.split(","):
        res.append(run_design(name, a, model, out, log))
        (out / "summary.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps([{k: r[k] for k in ("design", "tool_J") if k in r} | {"ls": r["ls_tool"]["J"]} for r in res]),
          flush=True)


if __name__ == "__main__":
    main()
