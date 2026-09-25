"""Run metadata (task spec A.3): every run writes meta.json in the HA-PR schema, extended with
git_sha, config_hash, program_hash, bridge_ckpt_hash, skill_hash, llm_model, seed, archive_snapshot,
alpha_ledger_id."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path

from . import __version__
from .paths import REPO_ROOT

EXTENDED = ("git_sha", "config_hash", "program_hash", "bridge_ckpt_hash", "skill_hash", "llm_model", "seed",
            "archive_snapshot", "alpha_ledger_id")


def git_sha(short: bool = False) -> str:
    try:
        out = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "--short" if short else "HEAD"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(REPO_ROOT), "status", "--porcelain", "--untracked-files=no"],
                               capture_output=True, text=True, timeout=10).stdout.strip()
        return out + ("+dirty" if dirty else "") if out else "unknown"
    except Exception:
        return "unknown"


def stable_hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def write_meta(run_dir: str | Path, run_id: str, design: str, **fields) -> dict:
    """Write run_dir/meta.json; unknown extended fields are recorded as None (never guessed)."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    meta = {"run_id": run_id, "design": design, "heurbridge_version": __version__, "git_sha": git_sha(),
            "host": platform.node() if fields.pop("record_host", False) else None,
            "created": time.strftime("%Y-%m-%dT%H:%M:%S")}
    for k in EXTENDED:
        meta.setdefault(k, None)
    meta.update(fields)
    if "config" in meta and meta.get("config_hash") is None:
        meta["config_hash"] = stable_hash(meta["config"])
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2, default=str))
    return meta
