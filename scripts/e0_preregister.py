#!/usr/bin/env python3
"""Pre-register the confirmatory E0 (task T4, gate G0') before any of its data exist.

  python scripts/e0_preregister.py --bridge checkpoints/algR_trackA_final/best.pt --demo-report reports/E0_demo_spec.md

Reserves, in this order (alpha_j = 0.05 * 2^-j), the alpha-ledger entries of campaign E0:
  E0#1  primary    task-list protocol (only the co-trained bridge is guarded, at f1), held-out family ISPD2005
  E0#2  secondary  every partner guarded at f1 (--equal-guard), same designs
  E0#3  secondary  task-list protocol on the held-out designs of the training family (ibm08, ibm12)
and writes the protocol to reports/E0_preregistration.md (commit it before launching the runs).  Each entry's meta
holds the protocol that e0_combine.py --ledger-entry checks before recording the pooled result.
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heurbridge.stats.alpha_ledger import AlphaLedger  # noqa: E402

ISPD = "adaptec1,adaptec2,adaptec3,adaptec4,bigblue1,bigblue3,bigblue4"   # bigblue2: no program can run (sandbox memory)
IBM = "ibm08,ibm12"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bridge", required=True, help="the final promoted T3.7 checkpoint (local copy)")
    ap.add_argument("--frozen", default="checkpoints/pretrain_small/pretrain_small.pt")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--primary", default=ISPD)
    ap.add_argument("--ibm", default=IBM)
    ap.add_argument("--campaign", default="E0")
    ap.add_argument("--ledger", default=str(ROOT / "stats" / "alpha_ledger.jsonl"))
    ap.add_argument("--demo-report", default="", help="the demo report the go decision was based on")
    ap.add_argument("--out", default=str(ROOT / "reports" / "E0_preregistration.md"))
    a = ap.parse_args()
    sha = hashlib.sha256(Path(a.bridge).read_bytes()).hexdigest()
    led = AlphaLedger(a.ledger, campaign=a.campaign)
    if led._entries():
        sys.exit("campaign %s already has ledger entries: pre-registration must come first" % a.campaign)
    common = {"final": "dreamplace", "seeds": a.seeds, "bridge_sha256_16": sha[:16], "frozen": a.frozen,
              "partners": ["none", "memetic", "repertoire", "frozen_gen", "cotrained"], "control": "random_guard",
              "test": "paired one-sided Wilcoxon, co-trained < partner; Holm over none/memetic/repertoire/frozen_gen",
              "gate": "G0' passes iff Holm-adjusted p < 0.01 for memetic AND repertoire"}
    plan = [("primary", a.primary, "f1", False), ("secondary_equal_guard", a.primary, "f1", True),
            ("secondary_ibm_heldout", a.ibm, "f1", False)]
    entries = []
    for role, designs, gf, eq in plan:
        meta = dict(common, role=role, designs=sorted(designs.split(",")), guard_fidelity=gf, equal_guard=eq)
        entries.append(led.reserve("partner_ablation", "E0 %s @%s" % (role, sha[:16]), "wilcoxon_less_holm4", meta=meta))
    rows = "\n".join("| %s | %s | %s | %s | %.5f |" % (e["ledger_id"], e["meta"]["role"], ", ".join(e["meta"]["designs"]),
                                                      "all partners" if e["meta"]["equal_guard"] else "bridge only",
                                                      e["alpha_j"]) for e in entries)
    text = """# E0 pre-registration (task T4, gate G0')

Registered {time} before any confirmatory E0 data exist. Bridge checkpoint sha256 `{sha}`
(the final promoted T3.7 Algorithm R checkpoint); frozen generator `{frozen}` (T3.4 pretraining).
{demo}
## Question

Does the co-trained bridge, as the evaluation partner of a heuristic's macro layout, give a lower final cost than
the partners that do not learn from the heuristics (memetic search, repertoire repair, the frozen generator, no
partner), at the same wall-clock per call?

## Protocol (task list T4)

- Sources: the 16 seed programs (T2.2) x seeds 0-{s_last} on every design; a source is kept when the program runs and
  its layout projects legally (P_M).
- Partners: none (the raw layout), memetic (SA on f0), repertoire (checked repair on f0), frozen generator (partial
  noising, best by f0), co-trained bridge (K = 20 Euler steps, guard over alpha in 0 / 0.25 / 0.5 / 1). Memetic and
  repertoire get the bridge's median wall-clock per call (measured first, including its guard). Control:
  random_guard = the bridge's guard along a random displacement of the bridge's typical length.
- Every partner's output -> P_M -> final cost J (Track A: DREAMPlace f1 with the macros fixed, J relative to the
  M1 baseline of the Track-A seeding campaign; a failure counts as +inf).
- Each design runs whole on one server (225: RTX 3090; 231: RTX 4090): pairs never cross GPU types.

## Tests

{rows}

Test: {test}. Gate: {gate}; the ledger's alpha_j of E0#1 (0.025) is above 0.01, so the gate threshold binds.
Also reported, not tested: portfolio J (best program per design), Kendall tau of each partner's program ranking vs
raw, per-metric deltas, the random-direction control (co-trained vs random_guard, one-sided Wilcoxon).

## Decision

- G0' passes (E0#1): continue to T5 (LLM evolution, deepseek-flash).
- G0' fails: stop and report; the N1-N2 novelty claims are withdrawn and the user decides the repositioning
  (task list T4). The secondary tests do not change this decision; they qualify it (whether a win survives an equal
  guard, whether it comes from the learned direction, whether it holds on the training family's held-out designs).
""".format(time=time.strftime("%Y-%m-%d %H:%M"), sha=sha, frozen=a.frozen, s_last=a.seeds - 1, rows=
               "| ledger entry | role | designs | guarded partners | alpha_j |\n|---|---|---|---|---|\n" + rows,
               test=common["test"], gate=common["gate"],
               demo=("\nGo decision based on the demo `%s` (designs outside this confirmatory set).\n" % a.demo_report)
               if a.demo_report else "")
    Path(a.out).write_text(text)
    print(json.dumps({"registered": [e["ledger_id"] for e in entries], "out": a.out, "bridge_sha256_16": sha[:16]}))


if __name__ == "__main__":
    main()
