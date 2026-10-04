#!/usr/bin/env python3
"""How much J does a timing margin cost? (exploratory, the owner's question of 4 Oct)

For each Track-B campaign's f2 layouts (the replays excluded): the timing margin of a layout = the smaller of its setup
and hold slack minus the gate threshold (the campaign's same-path replay median minus 0.02 ns, decision D6's
reference).  Prints the best J before the gates among the layouts whose margin is at least m, for m = 0 (D6's
admission), 0.01, 0.02, 0.03, 0.05 ns, and for the candidates with a shifted band (the `band` phase: the best three
re-run at three one-site / one-row shifts), how often each passes the gates on its band against the tool's replay at the
same shift (decision D11 (b)).

  python scripts/explore_timing_margin.py
"""

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heurbridge.eval import cost  # noqa: E402

DESIGNS = ("bp_fe_top", "bp_be_top", "ariane136", "swerv_wrapper")
MARGINS = (0.0, 0.01, 0.02, 0.03, 0.05)


def jl(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def main():
    print("| design | layouts at f2 | " + " | ".join("best J, margin >= %.2f ns (n)" % m for m in MARGINS) + " |")
    print("|---|---|" + "---|" * len(MARGINS))
    bands = []
    for d in DESIGNS:
        camp = ROOT / ("runs/remote/seedB_orfs7_%s/runs/seed_orfs/%s" % (d, d))
        recs2 = [r for r in json.loads((camp / "baseline_f2.json").read_text())["records"] if r.get("returncode") == 0]
        rows = jl(camp / "evals_f2.jsonl")
        reps = {r["run_id"]: r["record"] for r in rows if r.get("program") == "M1_replay" and r.get("status") == "ok"}
        ref = cost.with_gate_reference(cost.Baseline.from_records(d, recs2), list(reps.values()))
        th = {k: ref.timing[k + "_wns_ns"] - 0.02 for k in ("setup", "hold")}
        pts = []
        for r in rows:
            rec = r.get("record") if isinstance(r.get("record"), dict) else {}
            if r.get("program") == "M1_replay" or r.get("status") != "ok" or not rec:
                continue
            c = cost.evaluate(rec, ref, fidelity=2, timing_sign_rule=False)
            s, h = cost._num(rec.get("setup_wns_ns")), cost._num(rec.get("hold_wns_ns"))
            other_ok = all(g.get("status") != "fail" for k, g in c.gates.items() if k not in ("setup", "hold"))
            if s is None or h is None or not math.isfinite(c.J) or not other_ok:
                continue
            pts.append((c.J, min(s - th["setup"], h - th["hold"]), r["run_id"]))
        cells = []
        for m in MARGINS:
            ok = sorted(p for p in pts if p[1] >= m - 1e-12)
            cells.append("%.4f (%d)" % (ok[0][0], len(ok)) if ok else "- (0)")
        print("| %s | %d | %s |" % (d, len(pts), " | ".join(cells)))
        band_p = ROOT / ("runs/remote/seedB_band_%s/runs/seed_orfs/%s/evals_f2.jsonl" % (d, d))
        if band_p.exists():
            brows = jl(band_p)
            rep_by_k = {int(k[-4]) if k.endswith(".f2") and k[-5] == "p" else 0: v for k, v in reps.items()}
            unshifted = {r["run_id"]: r for r in rows}
            for cid in sorted({r["band_of"] for r in brows if r.get("program") == "CAND_BAND"}):
                pos = [(0, unshifted.get(cid))] + [(int(r["seed"]), r) for r in brows
                                                   if r.get("program") == "CAND_BAND" and r.get("band_of") == cid]
                passed, js = 0, []
                for k, r in pos:
                    rec = (r or {}).get("record") if isinstance((r or {}).get("record"), dict) else {}
                    if not rec or (r or {}).get("status") != "ok":
                        js.append(math.inf)
                        continue
                    g = cost.same_shift_reference(ref, rep_by_k.get(k), list(reps.values()))
                    c = cost.evaluate(rec, g, fidelity=2, timing_sign_rule=False)
                    js.append(c.J if math.isfinite(c.J) else math.inf)
                    passed += math.isfinite(c.J_inf)
                bands.append((d, cid, passed, len(pos), min(js), max(js)))
    print()
    print("| design | candidate | positions passing the gates (same-shift tool replay) | J before the gates, min-max |")
    print("|---|---|---|---|")
    for d, cid, p, n, lo, hi in bands:
        print("| %s | %s | %d of %d | %.4f-%.4f |" % (d, cid, p, n, lo, hi))


if __name__ == "__main__":
    main()
