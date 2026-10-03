#!/usr/bin/env python3
"""The Track-B confirmatory test of reports/trackB_preregistration.md (alpha-ledger campaign TB).

  python scripts/trackb_confirm.py reserve --design bp_fe_top     # before the design's test runs (TB#1, #2, ... in order)
  python scripts/trackb_confirm.py analyze --design bp_fe_top     # once, after the design's tbtest job is fetched
  python scripts/trackb_confirm.py describe --design bp_fe_top    # Section 5's reported-not-tested items (no ledger)
  python scripts/trackb_confirm.py candidate --design swerv_wrapper  # Section 3's candidate from the campaign's f2 rows

Per design: the tbtest rows (scripts/run_seed_orfs.py --phase tbtest: runs/seed_orfs/<d>/evals_tb.jsonl) and, for the
gate reference, the campaign's f2 baseline and same-path replays (runs/seed_orfs/<d>/baseline_f2.json, evals_f2.jsonl).
Candidate replicates: f2 J with every gate enforced, the timing gates against the replay band's median with the
0.02-ns guard and without the sign rule (decision D6); reference replicates: f2 J before the gates; a failed flow is
+inf.  Exact one-sided permutation test of the rank sum over all splits (candidate lower).
"""

import argparse
import glob
import itertools
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heurbridge.eval import cost  # noqa: E402
from heurbridge.stats.alpha_ledger import AlphaLedger  # noqa: E402

ORDER = ("bp_fe_top", "bp_be_top", "ariane136", "swerv_wrapper", "ariane133")      # TB#1, TB#2, ... in this order
CANDIDATES = {"bp_fe_top": "bp_fe_top.ls0.n4.f2", "bp_be_top": "bp_be_top.ls7.n1.f2", "ariane136": "ariane136.ls7.n3.f2",
              "swerv_wrapper": "swerv_wrapper.ls5.n4.f2"}       # fixed 4 Oct by `candidate` (pre-registration addendum)


def jl(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def one(pattern: str) -> Path:
    fs = sorted(glob.glob(pattern))
    if len(fs) != 1:
        sys.exit("expected one source for %s, found %s" % (pattern, fs))
    return Path(fs[0])


def rank_sum_p(cand: list, ref: list) -> float:
    """Exact one-sided p: the share of all splits of the pooled values whose candidate rank sum is <= the observed one
    (midranks for ties; +inf counts as larger than every finite value and ties with +inf)."""
    pool = np.array(cand + ref, float)
    big = 10.0 * (np.abs(pool[np.isfinite(pool)]).max() + 1.0) if np.isfinite(pool).any() else 1.0
    pool = np.where(np.isfinite(pool), pool, big)
    order = pool.argsort(kind="stable")
    ranks = np.empty(len(pool))
    ranks[order] = np.arange(1, len(pool) + 1)
    for v in np.unique(pool):                                         # midranks
        m = pool == v
        ranks[m] = ranks[m].mean()
    n = len(cand)
    obs = ranks[:n].sum()
    sums = [ranks[list(c)].sum() for c in itertools.combinations(range(len(pool)), n)]
    return float(np.mean([s <= obs + 1e-12 for s in sums]))


def endpoint(design: str, remote: Path, tb_prefix: str, camp_prefix: str) -> tuple:
    """(candidate values, reference values, rows, sources)."""
    tb = one(str(remote / (tb_prefix + "*") / "runs" / "seed_orfs" / design / "evals_tb.jsonl"))
    camp = one(str(remote / (camp_prefix + "*") / "runs" / "seed_orfs" / design / "evals_f2.jsonl"))
    recs2 = [r for r in json.loads((camp.parent / "baseline_f2.json").read_text())["records"] if r.get("returncode") == 0]
    base2 = cost.Baseline.from_records(design, recs2)
    rep = [r["record"] for r in jl(camp) if r.get("program") == "M1_replay" and r.get("status") == "ok"
           and isinstance(r.get("record"), dict)]
    ref_base = cost.with_gate_reference(base2, rep)
    rows = jl(tb)
    cand, refv, out = [], [], []
    for r in sorted(rows, key=lambda r: r["run_id"]):
        rec = r.get("record") if isinstance(r.get("record"), dict) else {}
        flow_ok = r.get("status") == "ok" and rec.get("returncode") in (0, None) and rec
        if r.get("program") == "TB_CAND":
            c = cost.evaluate(rec, ref_base, fidelity=2, timing_sign_rule=False) if flow_ok else None
            v = c.J_inf if c is not None else math.inf
            cand.append(v)
        elif r.get("program") == "TB_REF":
            c = cost.evaluate(rec, ref_base, fidelity=2) if flow_ok else None
            v = c.J if c is not None and math.isfinite(c.J) else math.inf
            refv.append(v)
        else:
            continue
        out.append({"run_id": r["run_id"], "arm": r["program"], "shift": r.get("tb_shift"), "J": v,
                    "J_before_gates": (c.J if c is not None else None),
                    "gates_failed": [k for k, g in (c.gates.items() if c is not None else []) if g.get("status") == "fail" and g.get("enforced")],
                    "wall_s": r.get("wall_s")})
    return cand, refv, out, [str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p) for p in (tb, camp)]


def candidate(design: str, remote: Path, camp_prefix: str) -> tuple:
    """Section 3's candidate: the campaign's best f2 layout admitted under Section 4's rule (every gate, the timing gates
    against the same-path replay band's median with the 0.02-ns guard and no sign rule).  Returns (run_id, J, n_admitted,
    n_rows, source)."""
    camp = one(str(remote / (camp_prefix + "*") / "runs" / "seed_orfs" / design / "evals_f2.jsonl"))
    recs2 = [r for r in json.loads((camp.parent / "baseline_f2.json").read_text())["records"] if r.get("returncode") == 0]
    rows = jl(camp)
    rep = [r["record"] for r in rows if r.get("program") == "M1_replay" and r.get("status") == "ok"
           and isinstance(r.get("record"), dict)]
    ref_base = cost.with_gate_reference(cost.Baseline.from_records(design, recs2), rep)
    scored = []
    for r in rows:
        rec = r.get("record") if isinstance(r.get("record"), dict) else {}
        if r.get("program") in ("M1_replay", "CAND_BAND") or r.get("status") != "ok" or rec.get("returncode") not in (0, None) \
                or not rec or r.get("pos_macros") is None:
            continue
        j = cost.evaluate(rec, ref_base, fidelity=2, timing_sign_rule=False).J_inf
        if math.isfinite(j):
            scored.append((j, r["run_id"]))
    n = sum(r.get("program") not in ("M1_replay", "CAND_BAND") for r in rows)
    if not scored:
        return None, math.inf, 0, n, str(camp)
    j, rid = min(scored)
    return rid, j, len(scored), n, str(camp)


def describe(design: str, remote: Path, tb_prefix: str, camp_prefix: str) -> list:
    """Section 5's "reported, not tested" items for one design (no ledger access): every replicate's J before the
    gates, slacks against the gate reference and wall-clock; the cost of finding the candidate against the tool's run."""
    tb = one(str(remote / (tb_prefix + "*") / "runs" / "seed_orfs" / design / "evals_tb.jsonl"))
    camp = one(str(remote / (camp_prefix + "*") / "runs" / "seed_orfs" / design / "evals_f2.jsonl"))
    recs2 = [r for r in json.loads((camp.parent / "baseline_f2.json").read_text())["records"] if r.get("returncode") == 0]
    base2 = cost.Baseline.from_records(design, recs2)
    rep = [r["record"] for r in jl(camp) if r.get("program") == "M1_replay" and r.get("status") == "ok"
           and isinstance(r.get("record"), dict)]
    ref_base = cost.with_gate_reference(base2, rep)
    fm = lambda v, f="%.4f": "-" if v is None else (f % v if math.isfinite(v) else "+inf")
    L = ["## %s: reported, not tested (pre-registration Section 5)" % design, "",
         "Gate reference: the campaign's %d same-path replays at f2, median setup WNS %s ns and hold WNS %s ns; a "
         "candidate replicate fails a timing gate below the reference minus 0.02 ns (hold WNS is reported in steps of "
         "0.01 ns). Gates failed: under the candidate's rule (D6) for both arms; for the reference arm they are shown for "
         "information only, its endpoint being J before the gates."
         % (len(rep), fm(ref_base.timing.get("setup_wns_ns"), "%.3f"), fm(ref_base.timing.get("hold_wns_ns"), "%.3f")), "",
         "| replicate | arm | shift | J before gates | setup WNS (ns) | hold WNS (ns) | hold violations | gates failed | flow wall (s) |",
         "|---|---|---|---|---|---|---|---|---|"]
    before = {"TB_CAND": [], "TB_REF": []}
    walls = {"TB_CAND": [], "TB_REF": []}
    for r in sorted(jl(tb), key=lambda r: (r.get("program", ""), r["run_id"])):
        if r.get("program") not in before:
            continue
        rec = r.get("record") if isinstance(r.get("record"), dict) else {}
        ok = r.get("status") == "ok" and rec.get("returncode") in (0, None) and rec
        c = cost.evaluate(rec, ref_base, fidelity=2, timing_sign_rule=False) if ok else None
        jb = c.J if c is not None and math.isfinite(c.J) else math.inf
        before[r["program"]].append(jb)
        if r.get("wall_s") is not None:
            walls[r["program"]].append(float(r["wall_s"]))
        failed = [k for k, g in c.gates.items() if g.get("status") == "fail" and g.get("enforced")] if c else []
        wns = {k: (c.gates[k].get("candidate") if c else cost._num(rec.get("%s_wns_ns" % k))) for k in ("setup", "hold")}
        why = "" if ok else " (flow failed: %s)" % str(r.get("error") or rec.get("failure") or r.get("status"))[:90]
        L.append("| %s | %s | %s | %s%s | %s | %s | %s | %s | %s |" % (
            r["run_id"], r["program"], r.get("tb_shift"), fm(jb), why, fm(wns["setup"], "%.3f"),
            fm(wns["hold"], "%.3f"), rec.get("hold_violation_count", "-"), ", ".join(failed) or "-",
            fm(r.get("wall_s"), "%.0f")))
    mc, mr = (float(np.median(before[k])) for k in ("TB_CAND", "TB_REF"))
    L += ["", "Median J before the gates: candidate %s, reference %s (difference %s)." % (fm(mc), fm(mr), fm(mc - mr)), ""]
    f1 = jl(camp.parent / "evals.jsonl")
    f2 = jl(camp)
    hrs = lambda rows: sum(float(r.get("wall_s") or 0.0) for r in rows) / 3600.0
    tool_s = float(np.median([float(r["duration_s"]) for r in recs2]))
    n_ok = sum(r.get("status") == "ok" for r in f1)
    L += ["Cost of finding the candidate: the campaign's %d flow runs to f1 (%d completed) and %d to f2, %.1f flow-run "
          "hours in all (the sum of the runs' wall-clock; the campaign ran up to 8 at a time; the four same-path replays "
          "are included), against one run of the unmodified flow with the tool's macro placement, %.2f h (the median of "
          "the campaign's %d f2 baseline runs): %.0fx. This test's replicates took a median of %.0f s (candidate) and "
          "%.0f s (reference) per run." % (len(f1), n_ok, len(f2), hrs(f1) + hrs(f2), tool_s / 3600.0, len(recs2),
                                           (hrs(f1) + hrs(f2)) * 3600.0 / tool_s, float(np.median(walls["TB_CAND"])),
                                           float(np.median(walls["TB_REF"]))), "",
          "Sources: %s, %s, %s, %s." % tuple(str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
                                              for p in (tb, camp.parent / "evals.jsonl", camp, camp.parent / "baseline_f2.json")), ""]
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["reserve", "analyze", "describe", "candidate"])
    ap.add_argument("--design", required=True, choices=ORDER)
    ap.add_argument("--ledger", default=str(ROOT / "stats" / "alpha_ledger.jsonl"))
    ap.add_argument("--remote", default=str(ROOT / "runs" / "remote"))
    ap.add_argument("--tb-prefix", default="tb_", help="job-name prefix of the test's runs")
    ap.add_argument("--campaign-prefix", default="seedB_orfs7_", help="job-name prefix of the seeding campaign")
    ap.add_argument("--out", default=str(ROOT / "reports" / "trackB_confirmatory.md"))
    a = ap.parse_args()
    if a.cmd == "candidate":                   # Section 3's rule applied to the campaign's stored f2 rows (no ledger)
        rid, j, k, n, src = candidate(a.design, Path(a.remote), a.campaign_prefix)
        print(json.dumps({"design": a.design, "candidate": rid, "f2_J": j, "admitted": k, "f2_rows": n, "source": src,
                          "registered": CANDIDATES.get(a.design)}))
        return
    if a.cmd == "describe":                    # descriptive only: no ledger access, may be rerun
        L = describe(a.design, Path(a.remote), a.tb_prefix, a.campaign_prefix)
        out = Path(a.out)
        text = out.read_text() if out.exists() else ""
        if ("## %s: reported, not tested" % a.design) in text:
            sys.exit("%s already has its descriptive section in %s" % (a.design, out))
        out.write_text(text + "\n".join(L) + "\n")
        print("\n".join(L))
        return
    led = AlphaLedger(a.ledger, campaign="TB")
    es = led._entries()
    want = "TB#%d" % (ORDER.index(a.design) + 1)
    if a.cmd == "reserve":
        if any(e.get("event") == "reserve" and e.get("meta", {}).get("design") == a.design for e in es):
            sys.exit("%s is already reserved" % a.design)
        e = led.reserve("trackb_vs_tool", "%s: %s vs the tool's macro placement at f2" % (a.design, CANDIDATES.get(a.design)),
                        "exact_rank_sum_permutation", meta={"design": a.design, "candidate": CANDIDATES.get(a.design),
                                                            "replicates": 6, "gate_rule": "0.02-ns guard, no sign rule (D6)",
                                                            "preregistration": "reports/trackB_preregistration.md"})
        if e["ledger_id"] != want:
            sys.exit("expected %s for %s, got %s: reserve the designs in order" % (want, a.design, e["ledger_id"]))
        print(json.dumps(e))
        return
    entry = next(e for e in es if e.get("event") == "reserve" and e.get("meta", {}).get("design") == a.design)
    if any(e.get("event") == "result" and e["ledger_id"] == entry["ledger_id"] for e in es):
        sys.exit("%s already has a recorded result; the test runs once" % entry["ledger_id"])
    cand, refv, rows, srcs = endpoint(a.design, Path(a.remote), a.tb_prefix, a.campaign_prefix)
    p = rank_sum_p(cand, refv) if cand and refv else 1.0
    res = led.record(entry, p_value=p, n=len(cand) + len(refv), extra={"candidate": cand, "reference": refv})
    fm = lambda v: "%.4f" % v if math.isfinite(v) else "+inf"
    sep = bool(cand and refv and max(cand) < min(refv))
    L = ["## %s (%s)" % (a.design, entry["ledger_id"]), "",
         "Candidate %s; recorded %s. **%s**: exact one-sided rank-sum permutation p = %.4g against alpha_j = %.4g; whole "
         "candidate band below the reference band: %s." % (CANDIDATES.get(a.design), res["time"],
                                                           "PASSED" if res["promoted"] else "FAILED", p, entry["alpha_j"],
                                                           "yes" if sep else "no"), "",
         "| replicate | arm | shift | J (candidate: gated; reference: before gates) | gates failed |", "|---|---|---|---|---|"]
    for r in rows:
        L.append("| %s | %s | %s | %s | %s |" % (r["run_id"], r["arm"], r["shift"], fm(r["J"]), ", ".join(r["gates_failed"]) or "-"))
    L += ["", "Sources: %s." % ", ".join(srcs), ""]
    out = Path(a.out)
    head = ("# Track B: confirmatory results\n\n| Field | Value |\n|---|---|\n| Report | trackB_confirmatory |\n"
            "| Pre-registration | reports/trackB_preregistration.md |\n| Status of the claim | per design below |\n\n")
    text = out.read_text() if out.exists() else head
    out.write_text(text + "\n".join(L) + "\n")
    print(json.dumps(res))


if __name__ == "__main__":
    main()
