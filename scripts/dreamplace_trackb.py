#!/usr/bin/env python3
"""DREAMPlace's macro placement for a Track-B design, to be run through the OpenROAD flow like HeurBridge's layouts
(the owner's request of 3 Oct: compare DREAMPlace and HeurBridge through the OpenROAD flow, next to the tool's own
macro placement).

  export (local, parsing only): the design as run_seed_orfs.load_design builds it (the campaign's pre-macro floorplan
          fp.hb.def + the platform and macro LEFs) and the P_M spacing the campaign uses (2 x MACRO_PLACE_HALO), pickled
  place  (GPU server): per target density and seed, DREAMPlace's mixed-size run with every macro movable
          (write_bookshelf_from_design), the macros read back and legalized by P_M with the campaign's spacing;
          a run that leaves a macro unmoved or fails P_M is a named failure.  Writes rows.jsonl and layouts.npz
          (key "macros": (runs, M, 3) x, y, orientation of the movable macros, normalized as the Design's layouts)

  python scripts/dreamplace_trackb.py export --design nangate45/bp_fe_top --flow third_party/ORFS-2024-12/flow \
      --fp-def runs/remote/seedB_orfs7_bp_fe_top/runs/seed_orfs/bp_fe_top/fp.hb.def --out data_dptb
  python scripts/dreamplace_trackb.py place --pkl data_dptb/bp_fe_top.pkl --densities 0.8 --seeds 0 --out runs/dptb/bp_fe_top
"""

import argparse
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def export(a):
    from heurbridge.core.defio import load_def_design
    from heurbridge.eval import miniflow as MF
    name = a.design.split("/")[-1]
    p, d = MF.Nangate45(a.flow), MF.from_orfs(a.flow, a.design)
    des, lay = load_def_design(a.fp_def, [str(p.tech_lef), str(p.sc_lef)] + d.macro_lefs, design_id=name,
                               family="orfs_cpu", tech="nangate45")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    halo = 2 * max(d.halo)                     # P_M spacing = 2 x the per-side platform halo (run_seed_orfs.py)
    with open(out / ("%s.pkl" % name), "wb") as fh:
        pickle.dump({"design": des, "layout": lay, "halo": halo, "platform_design": a.design}, fh)
    mm = des.is_macro & ~des.is_fixed
    print(json.dumps({"design": name, "objects": int(des.n_objects), "macros": int(mm.sum()), "nets": int(des.n_nets),
                      "halo_spacing": halo, "pickle": str(out / ("%s.pkl" % name))}))


def place(a):
    from heurbridge.core import project
    from heurbridge.eval.dreamplace import params, read_bookshelf_layout, run_placer, write_bookshelf_from_design
    with open(a.pkl, "rb") as fh:
        z = pickle.load(fh)
    des, lay, halo = z["design"], z["layout"], z["halo"]
    name = des.id
    placer_des = des
    if a.inflate:                              # DREAMPlace sees every macro grown by its halo on each side (halo / 2:
        import copy                            # P_M's spacing is twice the per-side halo), so it leaves the spacing
        placer_des = copy.copy(des)            # itself; centres and pin offsets are unchanged
        placer_des.size = des.size.copy()
        mmi = des.is_macro & ~des.is_fixed
        placer_des.size[mmi] = des.size[mmi] + halo
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    mm = des.is_macro & ~des.is_fixed
    saved, rows = [], []
    with open(out / "rows.jsonl", "w") as fh:
        for td in (float(x) for x in a.densities.split(",")):
            for seed in (int(x) for x in a.seeds.split(",")):
                work = out / "work" / ("td%g_s%d" % (td, seed))
                aux = write_bookshelf_from_design(placer_des, lay, work / "in", name=name, scale=a.scale)
                t0 = time.time()
                rc, log, wall = run_placer(params(str(aux.resolve()), str((work / "out").resolve()), gpu=not a.cpu,
                                                  iters=a.iters, seed=seed, target_density=td), work, a.timeout)
                row = {"design": name, "target_density": td, "seed": seed, "inflated_by_halo": bool(a.inflate),
                       "dreamplace_rc": rc, "dreamplace_s": round(wall, 1)}
                pl = work / "out" / name / ("%s.gp.pl" % name)
                if rc != 0 or not pl.exists():
                    row["failure"] = "dreamplace_rc_%s" % rc if rc != 0 else "dreamplace_no_output"
                else:
                    placed = read_bookshelf_layout(placer_des, lay, pl, scale=a.scale)
                    shift = np.abs(des.to_abs(placed.pos[mm]) - des.to_abs(lay.pos[mm]))
                    unmoved = int((np.nan_to_num(shift, nan=1.0).max(axis=1) <= 1e-9).sum())
                    m1 = lay.copy()
                    m1.pos[mm] = placed.pos[mm]
                    lp, rep = project.legalize_macros(des, m1, halo=halo)
                    row.update({"macros_unmoved": unmoved, "pm_ok": bool(rep.ok), "pm_mean_disp": float(rep.mean_disp)})
                    if unmoved:
                        row["failure"] = "tool_left_%d_macros_unmoved" % unmoved
                    elif not rep.ok:
                        row["failure"] = "P_M failed"
                    else:
                        row["index"] = len(saved)
                        saved.append(np.c_[lp.pos[mm], lp.orient[mm]])
                row["wall_s"] = round(time.time() - t0, 1)
                fh.write(json.dumps(row) + "\n")
                fh.flush()
                print(json.dumps(row), flush=True)
                if not a.keep_work:
                    import shutil
                    shutil.rmtree(work, ignore_errors=True)
    if saved:
        np.savez(out / "layouts.npz", macros=np.stack(saved))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--design", required=True, help="e.g. nangate45/bp_fe_top")
    e.add_argument("--flow", default="third_party/ORFS-2024-12/flow")
    e.add_argument("--fp-def", required=True)
    e.add_argument("--out", required=True)
    p = sub.add_parser("place")
    p.add_argument("--pkl", required=True)
    p.add_argument("--densities", default="0.8")
    p.add_argument("--seeds", default="0")
    p.add_argument("--iters", type=int, default=1000)
    p.add_argument("--scale", type=float, default=1000.0)
    p.add_argument("--timeout", type=int, default=3600)
    p.add_argument("--cpu", action="store_true")
    p.add_argument("--keep-work", action="store_true")
    p.add_argument("--inflate", action="store_true", help="grow the macros by the halo in DREAMPlace's input")
    p.add_argument("--out", required=True)
    a = ap.parse_args()
    export(a) if a.cmd == "export" else place(a)


if __name__ == "__main__":
    main()
