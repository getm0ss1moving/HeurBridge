"""Filesystem locations, resolved the same way locally and on the servers.

Environment overrides:
  HB_EDA_DIR     HA-PR harness root (contains harness/metrics_schema.py)
  HB_DATA_ROOT   benchmark / dataset root
  HB_WORK_ROOT   run artifacts (runs/, archive/, logs/)
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_EDA_CANDIDATES = (
    os.environ.get("HB_EDA_DIR"),
    os.environ.get("HEURA_EDA_BASE"),
    str(REPO_ROOT.parent / "eda"),                       # server: /data/dzy/heura_repr/{eda,heurbridge}
    "/data/dzy/heura_repr/eda",
    str(Path.home() / "Desktop" / "heura_repro_en" / "eda"),  # local English copy
)


def eda_dir() -> Path | None:
    """HA-PR harness root, or None if it is not available on this machine."""
    for cand in _EDA_CANDIDATES:
        if cand and (Path(cand) / "harness" / "metrics_schema.py").exists():
            return Path(cand)
    return None


def data_root() -> Path:
    env = os.environ.get("HB_DATA_ROOT")
    if env:
        return Path(env)
    server = Path("/data/dzy/heura_repr/benchmarks")
    return server if server.exists() else REPO_ROOT / "benchmarks"


def work_root() -> Path:
    return Path(os.environ.get("HB_WORK_ROOT", str(REPO_ROOT)))


def logs_dir() -> Path:
    d = work_root() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d
