#!/usr/bin/env python3
"""Experiment E0 / gate G0' (task T4): partner-type ablation on the seed population.

  python scripts/run_e0.py --suite ibm --designs ibm03 --bridge checkpoints/bridge_dev_r0/best.pt \
      [--frozen checkpoints/pretrain_small.pt] --final hbgp --out reports/e0_dev

Protocol: every seed program x --seeds seeds -> x^h -> each partner -> P_M -> final cost ("f2" on the
server via ORFS; "hbgp" = Track-A development stand-in).  Memetic and repertoire get the co-trained
bridge's median wall-clock per call (measured first, including its guard).  The alpha-ledger entry is
reserved before any result is read.  Primary test: paired one-sided Wilcoxon, co-trained < each other
partner, Holm over the comparisons; G0' passes iff co-trained beats memetic AND repertoire at p < 0.01.
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
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ledger = AlphaLedger(ROOT / "stats" / "alpha_ledger.jsonl", campaign=a.campaign)
    entry = ledger.reserve("partner_ablation", Path(a.bridge).name, "wilcoxon_less_holm4",
                           meta={"designs": a.designs, "final": a.final})
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
        cot = P.CotrainedPartner(bridge, b.graph, b.scorer, K=a.K)
        # measure the co-trained partner's median time per call (includes its guard)
        rng = np.random.default_rng(0)
        times = [cot(b.design, l, rng).wall_s for _, _, l in srcs[:5]]
        budget = float(np.median(times))
        partners = [P.NonePartner(), P.MemeticPartner(b.scorer), P.RepertoirePartner(b.scorer, b.view.macro_aff, b.view.macro_order), cot]
        if frozen is not None:
            partners.append(P.FrozenGenPartner(frozen, b.graph, b.scorer, K=a.K))
        for pid, s, lay in srcs:
            for part in partners:
                key = (b.design.id, pid, s, part.name)
                if key in done:
                    continue
                res = part(b.design, lay, np.random.default_rng(7 + s), budget_s=budget)
                lp, rep = project.legalize_macros(b.design, res.layout)
                if rep.ok:
                    rec = final.evaluate(b.design, lp, "%s.%s.s%d.%s" % key, out)
                    c = final.score(rec, baseline)
                    J, terms = c.J_inf, {t: v.get("raw") for t, v in c.terms.items()}
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
    res["gate_G0prime"] = {"pass": bool(pm < 0.01 and pr < 0.01), "p_memetic": pm, "p_repertoire": pr,
                           "note": "development run (Track-A stand-in final cost); not the pre-registered f2 test"
                           if a.final == "hbgp" else ""}
    ledger.record(entry, p_value=max(pm, pr), n=len(keys), extra={"gate": "G0prime", **res["gate_G0prime"]})
    (out / "e0_summary.json").write_text(json.dumps(res, indent=1, default=str))
    write_meta(out, "e0", a.designs, config=vars(a), alpha_ledger_id=entry["ledger_id"], summary=res)
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
