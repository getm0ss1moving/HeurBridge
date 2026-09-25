#!/usr/bin/env python3
"""E0 / G0' report from run_e0.py outputs (e0_rows.jsonl, e0_summary.json, meta.json).

  python scripts/report_e0.py --run reports/e0_dev --out reports/E0_partner_ablation_dev.md --dev
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heurbridge import reporting  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dev", action="store_true")
    ap.add_argument("--node", default="local (macOS, CPU)")
    ap.add_argument("--track", default="A-dev (HB-GP stand-in final cost; f0 guard)")
    a = ap.parse_args()
    run = Path(a.run)
    s = json.loads((run / "e0_summary.json").read_text())
    meta = json.loads((run / "meta.json").read_text())
    rows = [json.loads(l) for l in (run / "e0_rows.jsonl").read_text().splitlines()]
    fails = [r for r in rows if r["J"] in (float("inf"), "Infinity") or str(r["J"]) == "inf"]
    tab = ["| partner | mean J | portfolio J | Kendall tau vs raw | co-trained better: frac | one-sided p | Holm p_adj |",
           "|---|---|---|---|---|---|---|"]
    for p in s["partners"]:
        v = s["vs_cotrained"].get(p, {})
        hp = s.get("holm", {}).get(p, {})
        tab.append("| %s | %.4f | %.4f | %s | %s | %s | %s |" % (
            p, s["mean_J"][p] or float("nan"), s["portfolio"][p], s["kendall_vs_raw"].get(p),
            "%.2f" % v["frac_better"] if v else "-", "%.3g" % v["p"] if v else "-", "%.3g" % hp["p_adj"] if hp else "-"))
    g = s["gate_G0prime"]
    # paired view against the raw layout (partner "none"): where the gains are, not only the means
    import collections
    import math
    import numpy as np
    by = collections.defaultdict(dict)
    for r in rows:
        by[(r["design"], r["program"], r["seed"])][r["partner"]] = float(r["J"])
    vs = ["| partner | wins vs raw | losses | ties | median dJ vs raw | geometric-mean J ratio vs raw |", "|---|---|---|---|---|---|"]
    for p in s["partners"]:
        if p == "none":
            continue
        d = [(v[p], v["none"]) for v in by.values() if p in v and "none" in v and math.isfinite(v[p]) and math.isfinite(v["none"])]
        if not d:
            continue
        x = np.array(d)
        dj = x[:, 0] - x[:, 1]
        vs.append("| %s | %d | %d | %d | %+.4f | %.4f |" % (p, (dj < -1e-9).sum(), (dj > 1e-9).sum(), (abs(dj) <= 1e-9).sum(),
                                                         float(np.median(dj)), float(np.exp(np.mean(np.log(x[:, 0] / x[:, 1]))))))
    guard = s.get("guard") or {"fidelity": "f0 (fixed before v0.10.1)", "equal_guard": False}
    res = "\n".join(tab) + "\n\n" + "\n".join(vs) + (
        "\n\nGuard: the co-trained bridge's guard scores its alpha candidates at **%s**; equal guard for the other "
        "partners: **%s**." % (guard["fidelity"], guard["equal_guard"])) + \
        "\n\n**G0' decision (%s):** co-trained vs memetic p = %.3g, vs repertoire p = %.3g -> %s." % (
        "development, not the pre-registered test" if a.dev else "pre-registered", g["p_memetic"], g["p_repertoire"],
        "PASS" if g["pass"] else "FAIL")
    cfg = meta.get("config", {})
    text = reporting.render({
        "title": "E0 partner-type ablation%s" % (" (development)" if a.dev else ""),
        "report_id": run.name, "node": a.node, "track": a.track, "tools": "HeurBridge %s" % meta.get("heurbridge_version"),
        "gate": "G0' (co-trained beats memetic AND repertoire at p < 0.01 on the held-out family)",
        "test": "paired one-sided Wilcoxon, co-trained < each partner, Holm over the comparisons",
        "samples": "%d paired cases (design x program x seed); designs %s" % (s["n_cases"], cfg.get("designs")),
        "failures": ("%d rows with J = +inf: %s" % (len(fails), [(r["design"], r["program"], r["seed"], r["partner"]) for r in fails[:30]]))
        if fails else "none",
        "commands": "python scripts/run_e0.py " + " ".join("--%s %s" % (k.replace("_", "-"), v) for k, v in cfg.items() if v not in ("", None)),
        "results": res, "alpha_ledger_id": meta.get("alpha_ledger_id") or "-",
        "notes": "raw rows: %s. Wins / losses count paired cases where the partner's final J is below / above the "
                 "raw layout's; the geometric-mean ratio < 1 means lower J on average in log terms." % (run / "e0_rows.jsonl")},
        gate_passed=None if a.dev else g["pass"], out=a.out)
    print("REPORT_OK", a.out)


if __name__ == "__main__":
    main()
