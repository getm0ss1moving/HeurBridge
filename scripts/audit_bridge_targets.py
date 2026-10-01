#!/usr/bin/env python3
"""Audit of the bridge's training targets (diagnostic, no claim): which elites the pairs point at, and their cost.

The bridge learns to carry a heuristic layout to the nearest of its design's top-5 archive elites (bridge/data.py).
If those targets cost more than the tool's own macro placement (Track-A J 0.45 by construction), even perfect
transport cannot reach the tool.  For every design's round-0 pair shard: pairs, target J (min / median / max), the
share of pairs whose target costs at most the tool (J <= 0.45 + tol), the share whose target is the tool's own layout
(archive provenance program M1*), and the targets' programs.

  python scripts/audit_bridge_targets.py --pairs <round0 pairs dir> --archive <merged archive> --out reports/bridge_target_audit.md
"""

import argparse
import collections
import glob
import json
import sqlite3
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def provenance(archive: Path) -> dict:
    """elite id -> (program, J) from the archive's SQLite index."""
    dbs = list(Path(archive).glob("**/*.sqlite")) + list(Path(archive).glob("**/*.db"))
    out = {}
    for db in dbs:
        con = sqlite3.connect(str(db))
        try:
            for i, j, p in con.execute("SELECT id, J, provenance_json FROM elites"):
                out[int(i)] = ((json.loads(p) or {}).get("program"), float(j))
        except sqlite3.OperationalError:
            pass
        con.close()
    return out


def main():
    import torch
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", required=True, help="directory of <design>.pt pair shards (bridge.data.PairSet.save)")
    ap.add_argument("--archive", required=True, help="the archive the pairs were drawn from")
    ap.add_argument("--tool-J", type=float, default=0.45)
    ap.add_argument("--tol", type=float, default=5e-4, help="M1's J is the median of 3 runs: its seeds differ by ~1e-4")
    ap.add_argument("--val", default="ibm04,ibm06", help="validation designs: listed, not in the training totals")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    val = set(a.val.split(",")) if a.val else set()
    prov = provenance(Path(a.archive))
    L = ["# Bridge training targets: audit", "",
         "| Field | Value |", "|---|---|", "| Report | bridge_target_audit |",
         "| Data | round-0 pair shards of Algorithm R on Track A (%s); archive %s |" % (a.pairs, a.archive),
         "| Status of the claim | development / descriptive (no claim) |", "",
         "Tool = DREAMPlace's own mixed-size macro placement, J = %.2f by construction. A target at or below the tool: "
         "J <= %.4f." % (a.tool_J, a.tool_J + a.tol), "",
         "| design | pairs | target J min | median | max | share of pairs with target <= tool | share whose target is "
         "the tool's layout | target programs (pairs) |", "|---|---|---|---|---|---|---|---|"]
    tot = collections.Counter()
    for f in sorted(glob.glob(str(Path(a.pairs) / "*.pt"))):
        z = torch.load(f, weights_only=False)
        meta = z["meta"]
        J = np.array([m["J"] for m in meta], float)
        progs = collections.Counter(str((prov.get(int(m["elite"])) or ("?",))[0]) for m in meta)
        tool = sum(n for p, n in progs.items() if p == "BASELINE" or p.startswith("M1"))
        le = int((J <= a.tool_J + a.tol).sum())
        L.append("| %s%s | %d | %.4f | %.4f | %.4f | %.2f | %.2f | %s |" % (
            z["design_id"], " (validation)" if z["design_id"] in val else "", len(J), J.min(), np.median(J), J.max(), le / len(J), tool / len(J),
            ", ".join("%s (%d)" % kv for kv in progs.most_common(4))))
        if z["design_id"] in val:
            continue
        tot["pairs"] += len(J)
        tot["le"] += le
        tot["tool"] += tool
        tot["designs"] += 1
    L += ["", "Training designs (%d): %d pairs; target at or below the tool %d (%.2f); target is the tool's layout %d (%.2f)."
          % (tot["designs"], tot["pairs"], tot["le"], tot["le"] / max(tot["pairs"], 1), tot["tool"],
             tot["tool"] / max(tot["pairs"], 1)), ""]
    Path(a.out).write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
