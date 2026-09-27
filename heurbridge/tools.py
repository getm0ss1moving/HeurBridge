"""EDA tool binaries.  Locally OpenROAD and Yosys run in the OpenLane container; on the servers natively.

Environment:
  HB_OPENROAD, HB_YOSYS   binary or wrapper to run (e.g. scripts/server/openroad_deb.sh, which sets the library
                          path of the unpacked OpenROAD 2024-12 package).  Setting HB_OPENROAD selects native runs.
  HB_DOCKER_IMAGE         container image for local runs (default efabless/openlane:master-arm64v8; "" = native)
  EDA_THREADS             OpenROAD threads per job (red line A.2: 8 on the servers; default 6 = the local VM)
"""

from __future__ import annotations

import os

LOCAL_IMAGE = "efabless/openlane:master-arm64v8"


def binary(tool: str) -> str:
    """Command for 'openroad' or 'yosys'."""
    return os.environ.get("HB_" + tool.upper()) or tool


def docker_image() -> str | None:
    """Container image for tool runs, or None for native runs."""
    if os.environ.get("HB_OPENROAD"):
        return None
    return os.environ.get("HB_DOCKER_IMAGE", LOCAL_IMAGE) or None


def eda_threads(default: int = 6) -> int:
    return int(os.environ.get("EDA_THREADS") or default)


_DESCRIBED: str | None = None


def describe() -> str:
    """Tool versions for run metadata and reports (queried once per process)."""
    global _DESCRIBED
    if _DESCRIBED is None:
        img = docker_image()
        if img:
            _DESCRIBED = "container %s (OpenROAD b16bda7e, Yosys 0.38)" % img
        else:
            import subprocess

            def first(cmd):
                try:
                    out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    return ((out.stdout or out.stderr).strip().splitlines() or ["?"])[0][:60]
                except (OSError, subprocess.SubprocessError):
                    return "unavailable"
            _DESCRIBED = "native OpenROAD %s, %s" % (first([binary("openroad"), "-version"]),
                                                     first([binary("yosys"), "-V"]).split(" (")[0])
    return _DESCRIBED
