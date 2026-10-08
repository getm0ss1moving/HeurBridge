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
  --void RUN_IDS --void-reason TEXT  move these rows of this tag's ledger to evals_cs_<tag>.void.jsonl (each with
              the reason and the time) before anything runs, so they run again; for runs voided by an outside cause,
              e.g. timeouts under another user's load (decision D14).  A voided row is kept and reported, never dropped
  --slot-gate DIR  share the server's slots with the macro chat: every evaluation first takes a token from DIR
              (heurbridge/cellstage/slots.py; --slot-priority, lower first)
  --make-var  the campaign's own KEY=VALUE overrides; by default read from its meta.json (config.make_var), and any
              other value is refused, since J is normalized to the flow the campaign ran (ariane133's D2 (b) runs)
  --slots     with --shifts tb: only these slots (1-6), e.g. one run to compare with an earlier one
  --default-rows  ledgers with runs of the unmodified cell stage (the Track-B test's evals_tb.jsonl): a run of the
              default recipe whose fidelity and macro layout (positions to 1e-9 and orientations) match a row there
              is not run again; the row is copied into this tag's ledger with imported_from = <ledger>:<line> and
              scored like every other row.  Only rows of the plain ORFS evaluator (or of this default recipe) count
  --verify-default N  with --default-rows: first run the first N default-recipe jobs that have such a row and compare
              each with it (status and every numeric metric of the record but the run time); rows are imported only if
              all N are identical, else every default job runs
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


def default_sources(sources, default_id: str, fidelity: int) -> dict:
    """--default-rows: {layout key: ("<ledger>:<line>", row)} of rows of the unmodified cell stage.  A row counts if its
    evaluator is the plain ORFS one or this default recipe's, at this fidelity, completed or failed by a named
    deterministic failure, with no other recipe in its record."""
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
    return idx


def _probe(des, L) -> dict:
    mm = des.is_macro & ~des.is_fixed
    return {"pos_macros": L.pos[mm].tolist(), "orient_macros": L.orient[mm].tolist()}


def same_run(row: dict, src: dict) -> tuple:
    """(identical, differences): status, the failure's name, and every numeric metric of the record but the run
    time."""
    a, b = row.get("record") or {}, src.get("record") or {}
    diff = {}
    if row.get("status") != src.get("status"):
        diff["status"] = (row.get("status"), src.get("status"))
    if row.get("status") != "ok" and a.get("failure") != b.get("failure"):
        diff["failure"] = (a.get("failure"), b.get("failure"))
    for k in sorted(set(a) | set(b)):
        if k == "duration_s":
            continue
        x, y = a.get(k), b.get(k)
        if isinstance(x, (int, float)) or isinstance(y, (int, float)):
            if x != y:
                diff[k] = (x, y)
    return not diff, diff


def import_default_rows(ledger, jobs, idx: dict, default_id: str, des) -> dict:
    """Copy the matching rows of ``idx`` (default_sources) into this tag's ledger for the default recipe's jobs that
    have no row yet.  Returns the run ids imported and those with no matching row (they run as usual)."""
    out = {"imported": [], "missing": []}
    for ev, L, rid, extra in jobs:
        if extra["cs_recipe"] != default_id or ledger.get(rid) is not None:
            continue
        probe = _probe(des, L)
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


def void_rows(path: Path, run_ids, reason: str) -> list:
    """Move the rows of ``run_ids`` from the ledger ``path`` to <ledger>.void.jsonl (with the reason and the time);
    every named run id must be in the ledger.  Returns the run ids moved."""
    import time as _time
    want = set(run_ids)
    rows = jl(path)
    have = {r.get("run_id") for r in rows}
    missing = sorted(want - have)
    if missing:
        raise SystemExit("--void: %s not in %s" % (missing, path))
    if not reason:
        raise SystemExit("--void needs --void-reason")
    keep, moved = [r for r in rows if r.get("run_id") not in want], [r for r in rows if r.get("run_id") in want]
    stamp = _time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(path.with_name(path.stem + ".void.jsonl"), "a") as fh:
        for r in moved:
            fh.write(json.dumps({**r, "voided": reason, "voided_at": stamp}, default=str) + "\n")
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text("".join(json.dumps(r, default=str) + "\n" for r in keep))
    tmp.replace(path)
    return [r["run_id"] for r in moved]


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
    ap.add_argument("--verify-default", type=int, default=0, help="with --default-rows: default jobs run and compared first")
    ap.add_argument("--slot-gate", default="", help="slot registry directory shared with the macro chat (slots.py)")
    ap.add_argument("--void", default="", help="comma-separated run ids of this tag's ledger to void and run again")
    ap.add_argument("--void-reason", default="")
    ap.add_argument("--slot-priority", type=int, default=0)
    ap.add_argument("--workers", type=int, default=1, help="evaluations at a time (each runs one OpenROAD at a time)")
    ap.add_argument("--check-drift", action="store_true")
    ap.add_argument("--timeout", type=int, default=7200)
    ap.add_argument("--work-home", default=str(ROOT / "runs" / "orfs_work"))
    ap.add_argument("--yosys", default=None)
    ap.add_argument("--make-var", action="append", default=[],
                    help="the campaign's KEY=VALUE overrides, as it ran (default: its meta.json)")
    ap.add_argument("--campaign-dir", default="", help="default: runs/seed_orfs/<design name>")
    a = ap.parse_args()
    if a.race and a.fidelity != 2:
        raise SystemExit("--race picks f2 recipes from this tag's f1 rows: use it with --fidelity 2")
    if a.slots and a.shifts != "tb":
        raise SystemExit("--slots picks among the six shift slots: use it with --shifts tb")
    if a.verify_default and not a.default_rows:
        raise SystemExit("--verify-default compares runs with --default-rows: give both")
    a.flow, a.work_home_abs = str(Path(a.flow).resolve()), str(Path(a.work_home).resolve())
    name, cfg = a.design.split("/")[-1], "./designs/%s/config.mk" % a.design
    rdir = Path(a.campaign_dir) if a.campaign_dir else ROOT / "runs" / "seed_orfs" / name
    bpath, b2path = rdir / "baseline.json", rdir / "baseline_f2.json"
    if not (bpath.exists() and b2path.exists()):
        raise SystemExit("no campaign baselines in %s: run inside a campaign's resumed workspace" % rdir)
    camp_mv = []
    if (rdir / "meta.json").exists():
        camp_mv = list((json.loads((rdir / "meta.json").read_text()).get("config") or {}).get("make_var") or [])
    if a.make_var and list(a.make_var) != camp_mv:
        raise SystemExit("--make-var %s differs from the campaign's own %s (%s): J is normalized to the flow the "
                         "campaign ran" % (a.make_var, camp_mv, rdir / "meta.json"))
    a.make_var = camp_mv
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

    if a.void:
        moved = void_rows(rdir / ("evals_cs_%s.jsonl" % a.tag), [x for x in a.void.split(",") if x], a.void_reason)
        print(json.dumps({"voided": moved, "reason": a.void_reason}), flush=True)
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

    gate = None
    if a.slot_gate:
        from heurbridge.cellstage.slots import SlotGate
        gate = SlotGate(a.slot_gate, log=lambda m: print(m, flush=True))
        print(json.dumps({"slot_gate": a.slot_gate, "priority": a.slot_priority, **gate.state()}), flush=True)

    def one(job):
        ev, L, rid, extra = job
        tok = gate.acquire(a.slot_priority, rid) if gate is not None and ledger.get(rid) is None else None
        try:
            row = SA._eval(ev, des, L, base, rid, work, ledger, extra)
        finally:
            if tok is not None:
                gate.release(tok)
        cs = (row.get("record") or {}).get("cell_stage") or {}
        print(json.dumps({"run": rid, "status": row.get("status"), "J_raw": row.get("J_raw"),
                          "failure": (row.get("record") or {}).get("failure") or row.get("error"),
                          "wall_s": row.get("wall_s"), "log_marks": cs.get("log_marks"), "drift": cs.get("drift"),
                          "inspect_error": cs.get("inspect_error")}, default=str), flush=True)
        return row

    if a.default_rows:
        idx = default_sources([x for x in a.default_rows.split(",") if x], default.id, a.fidelity)
        identical = True
        if a.verify_default:
            vjobs = [j for j in jobs if j[3]["cs_recipe"] == default.id
                     and SA.layout_key(_probe(des, j[1])) in idx][:a.verify_default]
            for j in vjobs:
                where, src = idx[SA.layout_key(_probe(des, j[1]))]
                same, diff = same_run(one(j), src)
                identical = identical and same
                print(json.dumps({"verify_default": j[2], "source": where, "identical": same, "differing": diff},
                                 default=str), flush=True)
            if not vjobs:
                identical = False
                print(json.dumps({"verify_default": "no default job has a source row: nothing imported"}), flush=True)
        if identical:
            got = import_default_rows(ledger, jobs, idx, default.id, des)
            print(json.dumps({"default_rows": a.default_rows, "imported": len(got["imported"]),
                              "not_found": got["missing"]}), flush=True)
        else:
            print(json.dumps({"default_rows": a.default_rows, "imported": 0,
                              "reason": "a verification run differs from its source row: every default job runs"}),
                  flush=True)
    SA._map(one, jobs, max(1, a.workers))


if __name__ == "__main__":
    main()
