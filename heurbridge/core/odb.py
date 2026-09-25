"""ORFS ODB loader (task T1.1): OpenROAD writes the database as DEF, the tested DEF/LEF loader reads it.

  des, lay = load_odb("results/nangate45/ariane133/base/2_1_floorplan.odb",
                      lefs=[".../NangateOpenCellLibrary.tech.lef", ".../NangateOpenCellLibrary.macro.mod.lef",
                            ".../fakeram45_256x16.lef"], openroad="openroad")
Going through DEF keeps one parser for every Track-B design and inherits its round-trip and HPWL tests.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from .defio import load_def_design

TCL = "read_db {odb}\nwrite_def {out}\nexit\n"


def odb_to_def(odb: str | Path, out_def: str | Path, openroad: str = "openroad", timeout: int = 1800,
               docker_image: str | None = None) -> Path:
    out_def = Path(out_def)
    with tempfile.NamedTemporaryFile("w", suffix=".tcl", delete=False, dir=out_def.parent) as fh:
        fh.write(TCL.format(odb=Path(odb).resolve(), out=out_def.resolve()))
        tcl = fh.name
    cmd = [openroad, "-no_init", "-no_splash", "-exit", tcl]
    if docker_image:
        mounts = sorted({str(Path(odb).resolve().parent), str(out_def.resolve().parent)})
        cmd = ["docker", "run", "--rm"] + sum([["-v", "%s:%s" % (m, m)] for m in mounts], []) + \
              [docker_image, "bash", "-lc", "openroad -no_init -no_splash -exit %s" % tcl]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    Path(tcl).unlink(missing_ok=True)
    if p.returncode != 0 or not out_def.exists():
        raise RuntimeError("odb_to_def failed (rc=%s): %s" % (p.returncode, (p.stdout + p.stderr)[-800:]))
    return out_def


def load_odb(odb: str | Path, lefs: list, design_id: str | None = None, family: str = "", tech: str = "",
             workdir: str | Path | None = None, **kw):
    work = Path(workdir or Path(odb).parent)
    d = odb_to_def(odb, work / (Path(odb).stem + ".hb.def"), **kw)
    return load_def_design(d, lefs, design_id=design_id, family=family, tech=tech)
