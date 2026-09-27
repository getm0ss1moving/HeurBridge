#!/usr/bin/env python3
"""Patches to the ORFS 8ae3ae36 checkout for an OpenROAD built without the GUI (metrics untouched).

  python patch_orfs.py <ORFS>/flow

final_report.tcl saves the final images when the `save_image` proc exists -- it does in a GUI-less build too --
but does it through `gui::show`, which such a build lacks: 6_report then fails after every metric is written.
The image step now also requires `gui::show`.  Idempotent; prints what it did.
"""
import sys
from pathlib import Path

f = Path(sys.argv[1]) / "scripts" / "final_report.tcl"
s = f.read_text()
old = "if {[expr [llength [info procs save_image]] > 0]} {"
new = "if {[llength [info procs save_image]] > 0 && [llength [info commands gui::show]] > 0} {"
if new in s:
    print("already patched", f)
elif old in s:
    f.write_text(s.replace(old, new, 1))
    print("patched", f)
else:
    sys.exit("pattern not found in %s" % f)
