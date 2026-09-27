"""Import shim for the HA-PR harness (``eda/harness/*``): imported, never copied."""

from __future__ import annotations

import importlib
import sys
from types import ModuleType

from .paths import eda_dir


class EdaHarnessMissing(ImportError):
    pass


def harness(name: str) -> ModuleType:
    """Import ``eda/harness/<name>.py`` (e.g. ``harness("lef_def")``)."""
    root = eda_dir()
    if root is None:
        raise EdaHarnessMissing("HA-PR eda/ harness not found; set HB_EDA_DIR")
    hdir = str(root / "harness")
    if hdir not in sys.path:
        sys.path.insert(0, hdir)
    # the harness tree belongs to HA-PR (on the servers: another project's directory): never leave
    # __pycache__/*.pyc in it
    saved, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        return importlib.import_module(name)
    finally:
        sys.dont_write_bytecode = saved
