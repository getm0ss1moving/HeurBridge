#!/usr/bin/env python3
"""sha256 manifest of a benchmark suite (task T0.4).

  scripts/make_manifest.py <suite_dir> <out.sha256> [--source URL] [--archive-sha256 HEX]

Writes ``<sha256>  <relative path>`` lines (shasum -c compatible, sorted) and a JSON
sidecar with file count, total bytes, source and archive hash.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("suite_dir")
    ap.add_argument("out")
    ap.add_argument("--source", default="")
    ap.add_argument("--archive-sha256", default="")
    a = ap.parse_args()
    root = Path(a.suite_dir).resolve()
    files = sorted(p for p in root.rglob("*") if p.is_file() and not p.name.startswith("."))
    lines, total = [], 0
    for p in files:
        lines.append("%s  %s" % (sha256(p), p.relative_to(root)))
        total += p.stat().st_size
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    out.with_suffix(".json").write_text(json.dumps({
        "suite": root.name, "files": len(files), "bytes": total, "source": a.source,
        "archive_sha256": a.archive_sha256, "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "host": os.environ.get("HB_NODE_LABEL", "local" if sys.platform == "darwin" else "server")}, indent=1))
    print("MANIFEST_OK %s files=%d bytes=%d" % (out, len(files), total))


if __name__ == "__main__":
    main()
