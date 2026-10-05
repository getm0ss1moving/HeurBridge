#!/usr/bin/env python3
"""Standard-cell start positions per macro layout, for cell-stage recipes with source "npzdir:<dir>".

  # 1. local: the campaign's design and the macro layouts (M1 or campaign run ids; --shifts tb adds the Track-B
  #    test's shifted copies), pickled
  python scripts/cell_positions.py export --flow third_party/ORFS-2024-12/flow --design nangate45/bp_fe_top \
      --campaign-dir runs/remote/seedB_orfs7_bp_fe_top/runs/seed_orfs/bp_fe_top --layouts M1,bp_fe_top.ls0.n4.f2 \
      [--shifts none|tb] --out data_cellpos/bp_fe_top.pkl
  # 2. a GPU server (HB_DREAMPLACE set) or any server for HB-GP: one <layout key>.npz per layout, plus rows.jsonl
  python scripts/cell_positions.py dreamplace --pkl data_cellpos/bp_fe_top.pkl --out cellpos/bp_fe_top [--density 0.8]
  python scripts/cell_positions.py hbgp --pkl data_cellpos/bp_fe_top.pkl --out cellpos/bp_fe_top_hbgp

The key is the macro layout's identity as the campaign ledgers compute it (heurbridge/cellstage/positions.layout_key),
so the 224 job finds the file for whichever (shifted) layout it evaluates.  The export reads the campaign's
fp.hb.def and m1_macros.tcl and runs no tool.
"""

import argparse
import json
import pickle
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heurbridge.cellstage import positions as P  # noqa: E402


def export(a):
    import run_seed_orfs as RS
    from run_cell_stage import find_layout
    rdir = Path(a.campaign_dir)
    for f in ("fp.hb.def", "m1_macros.tcl"):
        if not (rdir / f).exists():
            raise SystemExit("%s has no %s (export runs no tool: use a fetched campaign)" % (rdir, f))
    ns = SimpleNamespace(flow=str(Path(a.flow).resolve()), design=a.design, work_home_abs="", yosys=None, make_var=[])
    des, lay, m1, _ = RS.load_design(ns, a.design.split("/")[-1], rdir, None)
    entries = []
    for lid in [x for x in a.layouts.split(",") if x]:
        L, src = find_layout(des, lay, m1, rdir, lid)
        slots = [(0, (0, 0), L)] if a.shifts == "none" else \
            [(k, sh, c) for k, sh, c, _ in RS.tb_pairs(des, L, m1) if sh is not None]
        for slot, sh, c in slots:
            entries.append({"key": P.layout_key(des, c), "layout_id": lid, "source": src, "slot": slot,
                            "shift": list(sh), "layout": c})
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as fh:
        pickle.dump({"design": des, "entries": entries}, fh)
    print(json.dumps({"export": str(out), "design": des.id, "layouts": len(entries),
                      "keys": [e["key"][:12] for e in entries]}))


def place(a, which: str):
    with open(a.pkl, "rb") as fh:
        z = pickle.load(fh)
    des, out = z["design"], Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "rows.jsonl", "a") as fh:
        for e in z["entries"]:
            row = {k: e[k] for k in ("key", "layout_id", "source", "slot", "shift")}
            row["placer"] = which
            t0 = time.time()
            try:
                if which == "dreamplace":
                    cells, ll, info = P.dreamplace(des, e["layout"], out / "work" / e["key"][:16], a.density, a.seed,
                                                   gpu=not a.cpu, iters=a.iters, timeout=a.timeout)
                else:
                    cells, ll, info = P.hbgp()(des, e["layout"])
                    info = {k: v for k, v in info.items() if isinstance(v, (int, float, str))}
                P.write_npz(out / ("%s.npz" % e["key"]), des, cells, ll)
                row.update({"status": "ok", "cells": int(len(cells)), "info": info})
            except Exception as ex:                  # noqa: BLE001 - recorded by name, never dropped
                row.update({"status": "failed", "error": "%s: %s" % (type(ex).__name__, str(ex)[:400])})
            row["wall_s"] = round(time.time() - t0, 1)
            fh.write(json.dumps(row, default=str) + "\n")
            fh.flush()
            print(json.dumps(row, default=str), flush=True)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--flow", default=str(ROOT / "third_party" / "ORFS-2024-12" / "flow"))
    e.add_argument("--design", required=True)
    e.add_argument("--campaign-dir", required=True)
    e.add_argument("--layouts", required=True)
    e.add_argument("--shifts", choices=["none", "tb"], default="none")
    e.add_argument("--out", required=True)
    for name in ("dreamplace", "hbgp"):
        p = sub.add_parser(name)
        p.add_argument("--pkl", required=True)
        p.add_argument("--out", required=True)
        if name == "dreamplace":
            p.add_argument("--density", type=float, default=0.8)
            p.add_argument("--seed", type=int, default=0)
            p.add_argument("--iters", type=int, default=1000)
            p.add_argument("--timeout", type=int, default=3600)
            p.add_argument("--cpu", action="store_true")
    a = ap.parse_args()
    if a.cmd == "export":
        export(a)
    else:
        place(a, a.cmd)


if __name__ == "__main__":
    main()
