#!/usr/bin/env python3
"""DREAMPlace Track-A f1 smoke test (T0.5 optional item / T1.4 Track A) on one IBM design.

  HB_DREAMPLACE=/tmp/.hbtools/dreamplace python scripts/server/dp_smoke.py --design ibm01
Runs f1 = DREAMPlace (macros FIXED) on the benchmark macro layout twice (determinism), once with every macro
rotated/flipped (orientation baking), and HB-GP on the same layout for reference.  Prints one JSON line per run
and DP_SMOKE_PASS / DP_SMOKE_FAIL.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heurbridge.core import bookshelf, project  # noqa: E402
from heurbridge.pipeline.evaluators import DreamplaceEvaluator, HBGPEvaluator  # noqa: E402
from run_seed_archive import SUITES, macro_stage_layout  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", default="ibm01")
    ap.add_argument("--out", default=str(ROOT / "runs" / "dp_smoke"))
    a = ap.parse_args()
    d, l = bookshelf.load_bookshelf(SUITES["ibm"] / a.design / (a.design + ".aux"), family="ibm")
    base, rep = project.legalize_macros(d, macro_stage_layout(d, l))
    out = Path(a.out) / a.design
    ev = DreamplaceEvaluator()
    recs = [ev.evaluate(d, base, "dp_r%d" % k, out) for k in range(2)]
    rot = base.copy()
    rng = np.random.default_rng(0)
    rot.orient[d.is_macro] = rng.integers(0, 8, int(d.is_macro.sum()))
    rot, rep_rot = project.legalize_macros(d, rot)
    recs.append(ev.evaluate(d, rot, "dp_rot", out))
    hb = HBGPEvaluator().evaluate(d, base, "hbgp", out)
    keys = ("returncode", "failure", "hpwl_um", "rudy_of_pct", "gp_overflow", "macro_max_shift", "runtime_s")
    for r in recs + [hb]:
        print(json.dumps({"run": r["run_id"], **{k: r.get(k) for k in keys}}), flush=True)
    ok = all(r.get("failure") is None and r.get("hpwl_um") for r in recs)
    det = recs[0].get("hpwl_um") == recs[1].get("hpwl_um")
    print(json.dumps({"deterministic": det, "pm_ok": rep.ok, "pm_rot_ok": rep_rot.ok,
                      "hpwl_ratio_dp_over_hbgp": (recs[0]["hpwl_um"] / hb["hpwl_um"]) if ok else None}))
    print("DP_SMOKE_PASS" if ok and det else "DP_SMOKE_FAIL")


if __name__ == "__main__":
    main()
