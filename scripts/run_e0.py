#!/usr/bin/env python3
"""Experiment E0 / gate G0' (task T4): partner-type ablation on the seed population.

  python scripts/run_e0.py --suite ibm --designs ibm03 --bridge checkpoints/bridge_dev_r0/best.pt \
      [--frozen checkpoints/pretrain_small.pt] --final hbgp --out reports/e0_dev

Protocol: every seed program x --seeds seeds -> x^h -> each partner -> P_M -> final cost ("f2" on the
server via ORFS; "hbgp" = Track-A development stand-in).  Memetic and repertoire get the co-trained
bridge's median wall-clock per call (measured first, including its guard).  The alpha-ledger entry is
reserved before any result is read.  Primary test: paired one-sided Wilcoxon, co-trained < each other
partner, Holm over the comparisons; G0' passes iff co-trained beats memetic AND repertoire at p < 0.01.

Guard options (recorded in the ledger entry and the summary):
  --guard-fidelity f1   the co-trained bridge's guard scores its alpha candidates with the final evaluator
                        (T3.8 default); f0 = the macro-stage surrogate (all partners then decide on f0 only)
  --equal-guard         every other partner's output is also guarded at the same fidelity: kept only if it
                        beats the raw layout, else the raw layout is returned.  Without it, a win of the
                        f1-guarded bridge over f0-driven partners can come from the guard's access to f1
                        alone, not from the learned transport.
"""

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heurbridge import partners as P  # noqa: E402
from heurbridge.bridge.train import load_bridge  # noqa: E402
from heurbridge.core import project  # noqa: E402
from heurbridge.eval import cost  # noqa: E402
from heurbridge.heuristics.macro.registry import all_programs  # noqa: E402
from heurbridge.meta import write_meta  # noqa: E402
from heurbridge.pipeline import bridge_data as BD  # noqa: E402
from heurbridge.pipeline.evaluators import HBGPEvaluator  # noqa: E402
from heurbridge.stats import paired as ST  # noqa: E402
from heurbridge.stats.alpha_ledger import AlphaLedger  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
from train_bridge import load_bundle  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--designs", required=True)
    ap.add_argument("--runs", default=str(ROOT / "runs" / "seed_dev"))
    ap.add_argument("--bridge", required=True)
    ap.add_argument("--frozen", default="")
    ap.add_argument("--final", default="hbgp", choices=["hbgp"])
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--K", type=int, default=20)
    ap.add_argument("--out", default=str(ROOT / "reports" / "e0_dev"))
    ap.add_argument("--campaign", default="E0_dev")
    ap.add_argument("--programs", default="")
    ap.add_argument("--guard-fidelity", default="f1", choices=["f0", "f1"])
    ap.add_argument("--equal-guard", action="store_true")
    ap.add_argument("--random-control", action="store_true",
                    help="add the random-direction control partner (the bridge's guard along a random displacement)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ledger = AlphaLedger(ROOT / "stats" / "alpha_ledger.jsonl", campaign=a.campaign)
    ck = hashlib.sha256(Path(a.bridge).read_bytes()).hexdigest()[:16]
    entry = ledger.reserve("partner_ablation", "%s@%s" % (Path(a.bridge).name, ck), "wilcoxon_less_holm4",
                           meta={"designs": a.designs, "final": a.final, "bridge": str(a.bridge), "bridge_sha256_16": ck,
                                 "guard_fidelity": a.guard_fidelity, "equal_guard": a.equal_guard})
    progs = all_programs()
    if a.programs:
        progs = [p for p in progs if p["id"] in set(a.programs.split(","))]
    bridge = load_bridge(a.bridge)
    frozen = load_bridge(a.frozen) if a.frozen else None
    rows_path = out / "e0_rows.jsonl"
    rows = [json.loads(l) for l in rows_path.read_text().splitlines()] if rows_path.exists() else []
    done = {(r["design"], r["program"], r["seed"], r["partner"]) for r in rows}
    fh = open(rows_path, "a")
    for name in a.designs.split(","):
        b = load_bundle(a.suite, name, a.runs)
        srcs = BD.run_sources(b, progs, a.seeds, cache=out / "cache")
        final = HBGPEvaluator(cluster_of=b.cluster_of)
        bench = project.legalize_macros(b.design, b.base)[0]
        base_recs = [final.evaluate(b.design, bench, "base%d" % s, out) for s in range(3)]
        baseline = cost.Baseline.from_records(b.design.id, base_recs)
        cache = {}

        def final_J(lay, key, _b=b, _final=final, _baseline=baseline, _cache=cache):
            """Final cost of a projected layout (cached by macro positions/orientations)."""
            mm = _b.design.is_macro & ~_b.design.is_fixed
            h = hashlib.sha256(lay.pos[mm].tobytes() + lay.orient[mm].tobytes()).hexdigest()
            if h not in _cache:
                rec = _final.evaluate(_b.design, lay, key, out)
                c = _final.score(rec, _baseline)
                _cache[h] = (c.J_inf, {t: v.get("raw") for t, v in c.terms.items()})
            return _cache[h]
        guard = b.scorer if a.guard_fidelity == "f0" else (lambda lay: final_J(lay, "guard")[0])
        cot = P.CotrainedPartner(bridge, b.graph, guard, K=a.K)
        # measure the co-trained partner's median time per call (includes its guard)
        rng = np.random.default_rng(0)
        probe = [cot(b.design, l, rng) for _, _, l in srcs[:5]]
        budget = float(np.median([r.wall_s for r in probe]))
        scale = float(np.median([r.info["disp"] for r in probe]))   # the bridge's typical displacement
        partners = [P.NonePartner(), P.MemeticPartner(b.scorer), P.RepertoirePartner(b.scorer, b.view.macro_aff, b.view.macro_order), cot]
        if frozen is not None:
            partners.append(P.FrozenGenPartner(frozen, b.graph, b.scorer, K=a.K))
        if a.random_control:
            partners.append(P.RandomGuardPartner(b.graph, guard, scale))
        for pid, s, lay in srcs:
            for part in partners:
                key = (b.design.id, pid, s, part.name)
                if key in done:
                    continue
                res = part(b.design, lay, np.random.default_rng(7 + s), budget_s=budget)
                lp, rep = project.legalize_macros(b.design, res.layout)
                ok = rep.ok
                if a.equal_guard and part.name not in ("none", "cotrained", "random_guard"):
                    raw_p, raw_rep = project.legalize_macros(b.design, lay)
                    keep = ok and guard(lp) < guard(raw_p)       # ties keep the raw layout
                    res.info["equal_guard"] = "kept_output" if keep else "kept_raw"
                    if not keep:
                        lp, ok = raw_p, raw_rep.ok
                if ok:
                    J, terms = final_J(lp, "%s.%s.s%d.%s" % key)
                else:
                    J, terms = math.inf, {}
                row = {"design": b.design.id, "program": pid, "seed": s, "partner": part.name, "J": J, "terms": terms,
                       "wall_s": round(res.wall_s, 3), "budget_s": round(budget, 3), "info": {k: v for k, v in res.info.items() if k != "scores"}}
                fh.write(json.dumps(row, default=str) + "\n")
                fh.flush()
                rows.append(row)
    fh.close()
    analyse(rows, entry, ledger, out, a)


def analyse(rows, entry, ledger, out, a):
    import collections
    by = collections.defaultdict(dict)
    for r in rows:
        by[(r["design"], r["program"], r["seed"])][r["partner"]] = r["J"]
    keys = [k for k, v in by.items() if "cotrained" in v]
    partners = sorted({r["partner"] for r in rows})
    res = {"n_cases": len(keys), "partners": partners, "mean_J": {}, "vs_cotrained": {}, "portfolio": {}, "kendall_vs_raw": {}}
    for p in partners:
        v = [by[k][p] for k in keys if p in by[k]]
        res["mean_J"][p] = float(np.mean([x for x in v if math.isfinite(x)])) if v else None
    pvals = {}
    for p in partners:
        if p == "cotrained":
            continue
        ks = [k for k in keys if p in by[k]]
        t = ST.wilcoxon_less([by[k]["cotrained"] for k in ks], [by[k][p] for k in ks])
        res["vs_cotrained"][p] = t
        pvals[p] = t["p"]
    res["holm"] = ST.holm(pvals, alpha=0.05) if pvals else {}
    designs = sorted({k[0] for k in keys})
    for p in partners:
        res["portfolio"][p] = float(np.mean([min(by[k][p] for k in keys if k[0] == d and p in by[k]) for d in designs]))
        taus = []
        for d in designs:
            progs = sorted({k[1] for k in keys if k[0] == d})
            raw = [np.mean([by[k]["none"] for k in keys if k[0] == d and k[1] == g and "none" in by[k]]) for g in progs]
            pv = [np.mean([by[k][p] for k in keys if k[0] == d and k[1] == g and p in by[k]]) for g in progs]
            if len(progs) > 2:
                taus.append(ST.kendall_tau(raw, pv))
        res["kendall_vs_raw"][p] = float(np.nanmean(taus)) if taus else None
    pm = res["vs_cotrained"].get("memetic", {}).get("p", 1.0)
    pr = res["vs_cotrained"].get("repertoire", {}).get("p", 1.0)
    res["guard"] = {"fidelity": a.guard_fidelity, "equal_guard": a.equal_guard, "random_control": a.random_control}
    res["gate_G0prime"] = {"pass": bool(pm < 0.01 and pr < 0.01), "p_memetic": pm, "p_repertoire": pr,
                           "note": "development run (Track-A stand-in final cost); not the pre-registered f2 test"
                           if a.final == "hbgp" else ""}
    ledger.record(entry, p_value=max(pm, pr), n=len(keys), extra={"gate": "G0prime", **res["gate_G0prime"]})
    (out / "e0_summary.json").write_text(json.dumps(res, indent=1, default=str))
    write_meta(out, "e0", a.designs, config=vars(a), alpha_ledger_id=entry["ledger_id"], summary=res)
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
