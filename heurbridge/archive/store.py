"""Elite archive (task T2.6): SQLite index + content-addressed .npz layout blobs.

Admission (Lemma 3 / proposal s.3.5): a candidate enters only if
  * it was verified at fidelity >= 2 (f2 or f3),
  * its cost is admissible (all required gates checked and passed, J complete),
  * its J beats the current k-th best J of its key (design, stage, upstream), k = 5,
    or the key has fewer than k entries, and
  * the same layout is not already stored under that key.
Entries are never deleted, so the best J of every key is non-increasing over any
insertion sequence.  ``snapshot()`` returns a content hash of the active top-k
sets and copies the index to ``snapshots/<id>.sqlite``.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import shutil
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..core.design import Layout

K_DEFAULT = 5
MIN_FIDELITY = 2

_SCHEMA = """
CREATE TABLE IF NOT EXISTS elites (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  design_id TEXT NOT NULL,
  stage TEXT NOT NULL,
  upstream TEXT NOT NULL,            -- canonical key of upstream elite ids ('' for the macro stage)
  layout_hash TEXT NOT NULL,
  layout_path TEXT NOT NULL,
  fidelity INTEGER NOT NULL,
  J REAL NOT NULL,
  metrics_json TEXT NOT NULL,
  gates_json TEXT NOT NULL,
  provenance_json TEXT NOT NULL,
  verified_at TEXT NOT NULL,
  inserted_at REAL NOT NULL,
  UNIQUE(design_id, stage, upstream, layout_hash)
);
CREATE INDEX IF NOT EXISTS elites_key ON elites(design_id, stage, upstream, J);
CREATE TABLE IF NOT EXISTS rejections (
  id INTEGER PRIMARY KEY AUTOINCREMENT, design_id TEXT, stage TEXT, upstream TEXT, J REAL,
  fidelity INTEGER, reason TEXT, provenance_json TEXT, at REAL
);
"""


@dataclass
class Candidate:
    design_id: str
    stage: str                      # "M" | "C" | "R" | "full"
    layout: Layout
    fidelity: int
    J: float
    admissible: bool
    metrics: dict = field(default_factory=dict)
    gates: dict = field(default_factory=dict)
    provenance: dict = field(default_factory=dict)   # program_hash, bridge_ckpt, alpha, seed, run_id, ...
    upstream_ids: tuple = ()
    verified_at: str = ""


def upstream_key(ids) -> str:
    return ",".join(str(int(i)) for i in sorted(ids)) if ids else ""


def layout_bytes(layout: Layout) -> bytes:
    buf = io.BytesIO()
    extra = {}
    if layout.routes:
        extra = {"routes_" + k: np.asarray(v) for k, v in layout.routes.items() if isinstance(v, np.ndarray)}
    np.savez(buf, pos=layout.pos, orient=layout.orient, schema=np.array(layout.schema), **extra)
    return buf.getvalue()


def layout_hash(layout: Layout) -> str:
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(layout.pos).tobytes())
    h.update(np.ascontiguousarray(layout.orient).tobytes())
    h.update(layout.schema.encode())
    return h.hexdigest()


def load_layout(path: str | Path) -> Layout:
    with np.load(path) as z:
        routes = {k[len("routes_"):]: z[k] for k in z.files if k.startswith("routes_")} or None
        return Layout(pos=z["pos"].copy(), orient=z["orient"].copy(), schema=str(z["schema"]), routes=routes)


class Archive:
    def __init__(self, root: str | Path, k: int = K_DEFAULT):
        self.root = Path(root)
        (self.root / "db").mkdir(parents=True, exist_ok=True)
        (self.root / "blobs").mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "db" / "archive.sqlite"
        self.k = k
        with self._db() as c:
            c.executescript(_SCHEMA)

    @contextmanager
    def _db(self):
        c = self._conn()
        try:
            yield c
        finally:
            c.close()

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path, timeout=60, isolation_level=None)
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA busy_timeout=60000")
        c.row_factory = sqlite3.Row
        return c

    # ------------------------------------------------------------------ writes
    def insert(self, cand: Candidate) -> tuple[bool, str]:
        """Atomic admission test + insert.  Returns (admitted, reason); every rejection is logged."""
        up = upstream_key(cand.upstream_ids)
        reason = None
        if cand.fidelity < MIN_FIDELITY:
            reason = "fidelity<%d" % MIN_FIDELITY
        elif not cand.admissible or cand.J is None or not math.isfinite(float(cand.J)):
            reason = "inadmissible"
        lh = layout_hash(cand.layout)
        c = self._conn()
        try:
            c.execute("BEGIN IMMEDIATE")
            if reason is None:
                dup = c.execute("SELECT 1 FROM elites WHERE design_id=? AND stage=? AND upstream=? AND layout_hash=?",
                                (cand.design_id, cand.stage, up, lh)).fetchone()
                if dup:
                    reason = "duplicate"
            if reason is None:
                row = c.execute("SELECT J FROM elites WHERE design_id=? AND stage=? AND upstream=? ORDER BY J ASC, id ASC "
                                "LIMIT 1 OFFSET ?", (cand.design_id, cand.stage, up, self.k - 1)).fetchone()
                if row is not None and not float(cand.J) < float(row["J"]):
                    reason = "not_better_than_kth(%.6g)" % float(row["J"])
            if reason is not None:
                c.execute("INSERT INTO rejections(design_id, stage, upstream, J, fidelity, reason, provenance_json, at) "
                          "VALUES (?,?,?,?,?,?,?,?)", (cand.design_id, cand.stage, up,
                                                       None if cand.J is None or not math.isfinite(float(cand.J)) else float(cand.J),
                                                       cand.fidelity, reason, json.dumps(cand.provenance, default=str), time.time()))
                c.execute("COMMIT")
                return False, reason
            rel = Path("blobs") / cand.design_id / cand.stage / (lh[:24] + ".npz")
            dst = self.root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                tmp = dst.with_suffix(".tmp")
                tmp.write_bytes(layout_bytes(cand.layout))
                tmp.replace(dst)
            c.execute("INSERT INTO elites(design_id, stage, upstream, layout_hash, layout_path, fidelity, J, metrics_json, "
                      "gates_json, provenance_json, verified_at, inserted_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                      (cand.design_id, cand.stage, up, lh, str(rel), int(cand.fidelity), float(cand.J),
                       json.dumps(cand.metrics, default=str), json.dumps(cand.gates, default=str),
                       json.dumps(cand.provenance, default=str), cand.verified_at or time.strftime("%Y-%m-%dT%H:%M:%S"),
                       time.time()))
            c.execute("COMMIT")
            return True, "admitted"
        except Exception:
            c.execute("ROLLBACK")
            raise
        finally:
            c.close()

    # ------------------------------------------------------------------ reads
    def topk(self, design_id: str, stage: str, k: int | None = None, upstream_ids=()) -> list[dict]:
        with self._db() as c:
            rows = c.execute("SELECT * FROM elites WHERE design_id=? AND stage=? AND upstream=? ORDER BY J ASC, id ASC LIMIT ?",
                             (design_id, stage, upstream_key(upstream_ids), k or self.k)).fetchall()
        return [self._row(r) for r in rows]

    def conditional(self, design_id: str, stage: str, upstream_id: int, k: int | None = None) -> list[dict]:
        """Top-k elites of ``stage`` whose upstream set contains ``upstream_id``."""
        with self._db() as c:
            rows = c.execute("SELECT * FROM elites WHERE design_id=? AND stage=? ORDER BY J ASC, id ASC",
                             (design_id, stage)).fetchall()
        out = [self._row(r) for r in rows if str(int(upstream_id)) in r["upstream"].split(",")]
        return out[: (k or self.k)]

    def best_J(self, design_id: str, stage: str, upstream_ids=()) -> float:
        with self._db() as c:
            r = c.execute("SELECT MIN(J) AS j FROM elites WHERE design_id=? AND stage=? AND upstream=?",
                          (design_id, stage, upstream_key(upstream_ids))).fetchone()
        return math.inf if r["j"] is None else float(r["j"])

    def count(self, design_id: str | None = None) -> int:
        with self._db() as c:
            if design_id is None:
                return int(c.execute("SELECT COUNT(*) FROM elites").fetchone()[0])
            return int(c.execute("SELECT COUNT(*) FROM elites WHERE design_id=?", (design_id,)).fetchone()[0])

    def layout(self, entry: dict) -> Layout:
        return load_layout(self.root / entry["layout_path"])

    def _row(self, r: sqlite3.Row) -> dict:
        d = dict(r)
        for k in ("metrics_json", "gates_json", "provenance_json"):
            d[k[:-5]] = json.loads(d.pop(k))
        d["upstream_ids"] = tuple(int(x) for x in d["upstream"].split(",")) if d["upstream"] else ()
        return d

    # ------------------------------------------------------------------ snapshots
    def snapshot(self, label: str = "") -> str:
        with self._db() as c:
            keys = c.execute("SELECT DISTINCT design_id, stage, upstream FROM elites ORDER BY 1, 2, 3").fetchall()
            h = hashlib.sha256()
            for key in keys:
                rows = c.execute("SELECT id, J, layout_hash FROM elites WHERE design_id=? AND stage=? AND upstream=? "
                                 "ORDER BY J ASC, id ASC LIMIT ?", (*tuple(key), self.k)).fetchall()
                for r in rows:
                    h.update(("%s|%s|%s|%d|%.17g|%s\n" % (*tuple(key), r["id"], r["J"], r["layout_hash"])).encode())
            c.execute("PRAGMA wal_checkpoint(FULL)")
        sid = (label + "_" if label else "") + h.hexdigest()[:12]
        snap = self.root / "snapshots"
        snap.mkdir(exist_ok=True)
        shutil.copy2(self.db_path, snap / (sid + ".sqlite"))
        return sid
