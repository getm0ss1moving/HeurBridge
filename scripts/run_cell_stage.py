#!/usr/bin/env python3
"""Cell-stage runs on Track B: imported macro layouts under cell-stage recipes (heurbridge/cellstage).

  python scripts/run_cell_stage.py --flow <ORFS>/flow --design nangate45/bp_fe_top --recipes configs/cellstage/c0_smoke.json \
      --layouts M1,bp_fe_top.ls0.n4.f2 --fidelity 1 --tag smoke [--shifts none|tb] [--workers 2] [--check-drift] \
      [--race K] [--slots 1,2] [--default-rows LEDGER[,LEDGER]] [--make-var KEY=VALUE ...] [--yosys ...]

Runs inside a campaign's resumed workspace (runs/seed_orfs/<design>/ of scripts/run_seed_orfs.py: its baselines, the
pre-macro floorplan, M1's macros, clusters.npy and the base variant's synthesis and floorplan).  It never runs or
changes a baseline, never touches the archive or another ledger, and writes only
runs/seed_orfs/<design>/evals_cs_<tag>.jsonl and runs/seed_orfs/<design>/cs_<tag>/ (meta.json, per-run files).

  --layouts   M1 (the tool's macro layout, imported like any candidate) or run ids of the campaign's ledgers
  --recipes   JSON: a list of recipes (CellRecipe.to_dict / from_dict) or {"recipes": [...]}
  --shifts    none: each layout as it is (slot 0); tb: the Track-B test's six whole-layout shifts with their
              fallbacks, common legal shifts with M1 (scripts/run_seed_orfs.py tb_pairs)
  --race K    with --fidelity 2: per layout, the default recipe plus the K best other recipes by this tag's f1 rows
              (J before the gates; heurbridge/cellstage/select.race); without it every recipe runs
  --check-drift  for recipes whose cells start at given positions: how far they moved after 3_1, 3_3 and 3_5
  --slots     with --shifts tb: only these slots (1-6), e.g. one run to compare with an earlier one
  --default-rows  ledgers with runs of the unmodified cell stage (the Track-B test's evals_tb.jsonl): a run of the
              default recipe whose fidelity and macro layout (positions to 1e-9 and orientations) match a row there
              is not run again; the row is copied into this tag's ledger with imported_from = <ledger>:<line> and
              scored like every other row.  Only rows of the plain ORFS evaluator (or of this default recipe) count
Rows: run id <design>.cs_<tag>.<layout>.s<slot>.<recipe id>.f<1|2>, program CS; every row carries the recipe, the
layout, the shift, and the record's cell_stage entry (effective make variables, the cell stage's own log lines,
drift).  J is scored like the campaign (cost_v3: J against the unmodified flow, timing gates against the same-path
replay band); a later test re-scores its replicates under its own registered rule.
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heurbridge import tools  # noqa: E402
from heurbridge.cellstage import select as S  # noqa: E402
from heurbridge.cellstage.recipe import CellRecipe, CellStage  # noqa: E402
from heurbridge.eval import cost, orfs  # noqa: E402
from heurbridge.heuristics.cell.cluster import cluster_cells  # noqa: E402
from heurbridge.meta import write_meta  # noqa: E402
from heurbridge.pipeline import seed_archive as SA  # noqa: E402
from heurbridge.pipeline.evaluators import OrfsEvaluator  # noqa: E402


def load_recipes(path) -> list:
    data = json.loads(Path(path).read_text())
    recipes = [CellRecipe.from_dict(d) for d in (data["recipes"] if isinstance(data, dict) else data)]
    ids, names = [r.id for r in recipes], [r.name for r in recipes]
    if len(set(ids)) != len(ids) or len(set(names)) != len(names):
        raise ValueError("%s: every recipe needs its own settings and its own name" % path)
    return recipes


def jl(path: Path) -> list:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


def find_layout(des, lay, m1, rdir: Path, lid: str):
    """(layout, where it came from): M1, or the row of that run id in one of the campaign's ledgers."""
    if lid == "M1":
        return m1, "m1_macros.tcl"
    for led in sorted(rdir.glob("evals*.jsonl")):
        if led.name.startswith("evals_cs_"):
            continue
        for r in jl(led):
            if r.get("run_id") == lid and "pos_macros" in r:
                return SA._layout_from_row(des, lay, r), "%s:%s" % (led.name, lid)
    raise SystemExit("layout %s is in none of the campaign's ledgers (%s)" % (lid, rdir))


PLAIN = "orfs"          # the evaluator of the unmodified cell stage in the campaigns and the Track-B tests


def import_default_rows(ledger, jobs, sources, default_id: str, fidelity: int, des) -> dict:
    """--default-rows: copy rows of the unmodified cell stage into this tag's ledger for the default recipe's jobs that
    have no row yet.  A source row counts if its evaluator is the plain ORFS one or this default recipe's, at this
    fidelity, completed or failed by a named deterministic failure, with no other recipe in its record.  Returns the
    run ids imported and those with no matching row (they run as usual)."""
    idx = {}
    for path in sources:
        for n, line in enumerate(Path(path).read_text().splitlines(), 1):
            if not line.strip():
                continue
            r = json.loads(line)
            cs = (r.get("record") or {}).get("cell_stage") or {}
            if r.get("evaluator") not in (PLAIN, "orfs_cs_%s" % default_id) or r.get("fidelity") != fidelity \
                    or (cs and cs.get("recipe_id") != default_id) or "pos_macros" not in r or r.get("reused_from") \
                    or not (r.get("status") == "ok" or SA.deterministic_failure(r)):
                continue
            idx.setdefault(SA.layout_key(r), ("%s:%d" % (path, n), r))
    mm = des.is_macro & ~des.is_fixed
    out = {"imported": [], "missing": []}
    for ev, L, rid, extra in jobs:
        if extra["cs_recipe"] != default_id or ledger.get(rid) is not None:
            continue
        probe = {"pos_macros": L.pos[mm].tolist(), "orient_macros": L.orient[mm].tolist()}
        hit = idx.get(SA.layout_key(probe))
        if hit is None:
            out["missing"].append(rid)
            continue
        where, src = hit
        if src.get("status") == "ok":
            row = {k: src[k] for k in SA.REUSE_KEYS if k in src}
        else:
            row = {k: src[k] for k in ("status", "fidelity", "J", "error") if k in src}
            row["record"] = {"failure": SA.deterministic_failure(src),
                             "returncode": (src.get("record") or {}).get("returncode")}
        row.update({"run_id": rid, "evaluator": ev.name, "imported_from": where, "imported_run_id": src.get("run_id"),
                    "wall_s": 0.0, **probe, **extra})
        ledger.add(row)
        out["imported"].append(rid)
    return out


def replay_records(rdir: Path, ledger: str) -> list:
    return [r["record"] for r in jl(rdir / ledger) if r.get("program") == "M1_replay" and r.get("status") == "ok"
            and isinstance(r.get("record"), dict)]


def main():
    import run_seed_orfs as RS
    ap = argparse.ArgumentParser()
    ap.add_argument("--flow", required=True)
    ap.add_argument("--design", required=True)
    ap.add_argument("--recipes", required=True)
    ap.add_argument("--layouts", required=True, help="comma-separated: M1 and/or campaign run ids")
    ap.add_argument("--fidelity", type=int, choices=[1, 2], default=1)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--shifts", choices=["none", "tb"], default="none")
    ap.add_argument("--race", type=int, default=0)
    ap.add_argument("--slots", default="", help="with --shifts tb: comma-separated slots to run (default all)")
    ap.add_argument("--default-rows", default="", help="comma-separated ledgers of unmodified-cell-stage runs")
    ap.add_argument("--workers", type=int, default=1, help="evaluations at a time (each runs one OpenROAD at a time)")
    ap.add_argument("--check-drift", action="store_true")
    ap.add_argument("--timeout", type=int, default=7200)
    ap.add_argument("--work-home", default=str(ROOT / "runs" / "orfs_work"))
    ap.add_argument("--yosys", default=None)
    ap.add_argument("--make-var", action="append", default=[], help="the campaign's KEY=VALUE overrides, as it ran")
    ap.add_argument("--campaign-dir", default="", help="default: runs/seed_orfs/<design name>")
    a = ap.parse_args()
    if a.race and a.fidelity != 2:
        raise SystemExit("--race picks f2 recipes from this tag's f1 rows: use it with --fidelity 2")
    if a.slots and a.shifts != "tb":
        raise SystemExit("--slots picks among the six shift slots: use it with --shifts tb")
    a.flow, a.work_home_abs = str(Path(a.flow).resolve()), str(Path(a.work_home).resolve())
    name, cfg = a.design.split("/")[-1], "./designs/%s/config.mk" % a.design
    rdir = Path(a.campaign_dir) if a.campaign_dir else ROOT / "runs" / "seed_orfs" / name
    bpath, b2path = rdir / "baseline.json", rdir / "baseline_f2.json"
    if not (bpath.exists() and b2path.exists()):
        raise SystemExit("no campaign baselines in %s: run inside a campaign's resumed workspace" % rdir)
    recs = {f: [r for r in json.loads(p.read_text())["records"] if r.get("returncode") == 0]
            for f, p in ((1, bpath), (2, b2path))}
    if not recs[1] or not recs[2]:
        raise SystemExit("the campaign's baseline failed; nothing to compare with")
    base_dirs = orfs.OrfsRun(flow_dir=a.flow, design_config=cfg, variant="base", work_home=a.work_home_abs,
                             yosys=a.yosys, make_vars_extra=tuple(a.make_var)).dirs()
    ns = SimpleNamespace(flow=a.flow, design=a.design, work_home_abs=a.work_home_abs, yosys=a.yosys, make_var=a.make_var)
    des, lay, m1, _ = RS.load_design(ns, name, rdir, base_dirs)
    base = cost.Baseline.from_records(des.id, recs[a.fidelity])
    reps = replay_records(rdir, "evals.jsonl" if a.fidelity == 1 else "evals_f2.jsonl")
    base = cost.with_gate_reference(base, reps)
    recipes = load_recipes(a.recipes)
    default = CellRecipe()
    if a.race and not any(r.is_default() for r in recipes):
        raise SystemExit("--race keeps the default recipe in every layout's set: add it to %s" % a.recipes)
    cl = None
    if any(r.start == "quadratic" for r in recipes):
        cpath = rdir / "clusters.npy"
        cl = np.load(cpath) if cpath.exists() else cluster_cells(des, seed=0)

    layouts = {}
    for lid in [x for x in a.layouts.split(",") if x]:
        L, src = find_layout(des, lay, m1, rdir, lid)
        slots = [(0, (0, 0), L)] if a.shifts == "none" else \
            [(k, sh, c) for k, sh, c, _ in RS.tb_pairs(des, L, m1) if sh is not None]
        if a.slots:
            slots = [s for s in slots if s[0] in {int(x) for x in a.slots.split(",") if x}]
        layouts[lid] = (src, slots)

    ledger = SA.Ledger(rdir / ("evals_cs_%s.jsonl" % a.tag))
    f1_rows = jl(rdir / ("evals_cs_%s.jsonl" % a.tag))
    plan = {}
    for lid in layouts:
        chosen = recipes
        if a.race:
            sc = {}
            for r in recipes:
                rows = [x for x in f1_rows if x.get("cs_layout") == lid and x.get("cs_recipe") == r.id
                        and x.get("fidelity") == 1 and x.get("cs_slot") == 0]
                sc[r.id] = rows[0].get("J_raw") if rows and rows[0].get("status") == "ok" else math.inf
            keep = set(S.race(sc, a.race, exclude=(default.id,))) | {default.id}
            chosen = [r for r in recipes if r.id in keep]
        plan[lid] = chosen

    evs = {}
    for r in recipes:
        evs[r.id] = OrfsEvaluator(fidelity=a.fidelity, flow_dir=a.flow, design_config=cfg, work_home=a.work_home_abs,
                                  base_variant="base", yosys=a.yosys, timeout_s=a.timeout,
                                  make_vars_extra=tuple(a.make_var), name="orfs_cs_%s" % r.id,
                                  cluster_of=cl if r.start == "quadratic" else None,
                                  cell_stage=CellStage(r, check_drift=a.check_drift))
    tdir = rdir / ("cs_%s" % a.tag)                       # never rdir itself: its meta.json is the campaign's
    work = tdir / "work"
    jobs = []
    for lid, (src, slots) in layouts.items():
        for slot, sh, L in slots:
            for r in plan[lid]:
                rid = "%s.cs_%s.%s.s%d.%s.f%d" % (name, a.tag, lid, slot, r.id, a.fidelity)
                extra = {"program": "CS", "cs_tag": a.tag, "cs_layout": lid, "cs_layout_source": src, "cs_slot": slot,
                         "cs_shift": list(sh), "cs_recipe": r.id, "cs_recipe_name": r.name}
                jobs.append((evs[r.id], L, rid, extra))
    write_meta(tdir, "cs_%s" % a.tag, des.id,
               config={k: v for k, v in vars(a).items() if k != "work_home_abs"},
               recipes=[r.to_dict() for r in recipes], plan={k: [r.id for r in v] for k, v in plan.items()},
               layouts={k: {"source": v[0], "slots": [[s, list(sh)] for s, sh, _ in v[1]]} for k, v in layouts.items()},
               baseline=base.to_dict(), gate_reference=base.sources.get("gate_reference"),
               eda_threads=tools.eda_threads(8), record_host=True)
    print(json.dumps({"cell_stage": a.tag, "design": name, "fidelity": a.fidelity, "runs": len(jobs),
                      "workers": a.workers}), flush=True)
    if a.default_rows:
        got = import_default_rows(ledger, jobs, [x for x in a.default_rows.split(",") if x], default.id, a.fidelity, des)
        print(json.dumps({"default_rows": a.default_rows, "imported": len(got["imported"]),
                          "not_found": got["missing"]}), flush=True)

    def one(job):
        ev, L, rid, extra = job
        row = SA._eval(ev, des, L, base, rid, work, ledger, extra)
        cs = (row.get("record") or {}).get("cell_stage") or {}
        print(json.dumps({"run": rid, "status": row.get("status"), "J_raw": row.get("J_raw"),
                          "failure": (row.get("record") or {}).get("failure") or row.get("error"),
                          "wall_s": row.get("wall_s"), "log_marks": cs.get("log_marks"), "drift": cs.get("drift"),
                          "inspect_error": cs.get("inspect_error")}, default=str), flush=True)
        return row
    SA._map(one, jobs, max(1, a.workers))


if __name__ == "__main__":
    main()
