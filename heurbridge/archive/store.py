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

Fidelities are ranked separately: J at f1 and J at f2 are normalized by different baselines over different
terms, so a candidate competes with the k-th best of its own fidelity, and the queries (``topk``,
``conditional``, ``best_J``) use the highest fidelity present for the key unless ``fidelity`` is given.
(Mixed ranking kept every f2-verified bp_fe_top layout, J ~0.96-0.99 at f2, out of a top-5 of f1 entries with
J ~0.86-0.88 at f1.)  A development archive holding only f1 entries behaves as a single-fidelity archive.
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
  UNIQUE(design_id, stage, upstream, layout_hash, fidelity)
);
CREATE INDEX IF NOT EXISTS elites_key ON elites(design_id, stage, upstream, fidelity, J);
CREATE TABLE IF NOT EXISTS rejections (
  id INTEGER PRIMARY KEY AUTOINCREMENT, design_id TEXT, stage TEXT, upstream TEXT, J REAL,
  fidelity INTEGER, reason TEXT, provenance_json TEXT, at REAL
);
"""


def _migrate_unique_fidelity(c) -> None:
    """Archives created before 0.10.7 made (design, stage, upstream, layout) unique, so a layout verified at a
    higher fidelity could not be stored in that fidelity's tier.  Rebuild the table with fidelity in the key
    (rows, ids and blobs unchanged)."""
    sql = c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='elites'").fetchone()[0]
    if "layout_hash, fidelity)" in sql.replace("\n", " "):
        return
    c.executescript("""
BEGIN IMMEDIATE;
ALTER TABLE elites RENAME TO elites_pre_0_10_7;
DROP INDEX IF EXISTS elites_key;
""" + _SCHEMA.split("CREATE TABLE IF NOT EXISTS rejections")[0] + """
INSERT INTO elites SELECT * FROM elites_pre_0_10_7;
DROP TABLE elites_pre_0_10_7;
COMMIT;
""")


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
    def __init__(self, root: str | Path, k: int = K_DEFAULT, min_fidelity: int = MIN_FIDELITY):
        """min_fidelity < 2 is for development archives only (Track-A stand-ins); such archives are labelled."""
        self.root = Path(root)
        self.min_fidelity = min_fidelity
        (self.root / "db").mkdir(parents=True, exist_ok=True)
        (self.root / "blobs").mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "db" / "archive.sqlite"
        self.k = k
        with self._db() as c:
            c.executescript(_SCHEMA)
            _migrate_unique_fidelity(c)
        if min_fidelity < MIN_FIDELITY:
            (self.root / ("DEV_ARCHIVE_MIN_FIDELITY_%d" % min_fidelity)).write_text(
                "Development archive: admits fidelity >= %d (task spec requires >= 2).\n" % min_fidelity)

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
        if cand.fidelity < self.min_fidelity:
            reason = "fidelity<%d" % self.min_fidelity
        elif not cand.admissible or cand.J is None or not math.isfinite(float(cand.J)):
            reason = "inadmissible"
        lh = layout_hash(cand.layout)
        c = self._conn()
        try:
            c.execute("BEGIN IMMEDIATE")
            if reason is None:
                dup = c.execute("SELECT 1 FROM elites WHERE design_id=? AND stage=? AND upstream=? AND layout_hash=? "
                                "AND fidelity=?", (cand.design_id, cand.stage, up, lh, int(cand.fidelity))).fetchone()
                if dup:
                    reason = "duplicate"
            if reason is None:
                row = c.execute("SELECT J FROM elites WHERE design_id=? AND stage=? AND upstream=? AND fidelity=? "
                                "ORDER BY J ASC, id ASC LIMIT 1 OFFSET ?",
                                (cand.design_id, cand.stage, up, int(cand.fidelity), self.k - 1)).fetchone()
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
    def _tier(self, c, design_id: str, stage: str, up: str, fidelity) -> int | None:
        """The fidelity to rank in: the one requested, else the highest present for the key."""
        if fidelity is not None:
            return int(fidelity)
        r = c.execute("SELECT MAX(fidelity) AS f FROM elites WHERE design_id=? AND stage=? AND upstream=?",
                      (design_id, stage, up)).fetchone()
        return None if r["f"] is None else int(r["f"])

    def topk(self, design_id: str, stage: str, k: int | None = None, upstream_ids=(), fidelity: int | None = None) -> list[dict]:
        up = upstream_key(upstream_ids)
        with self._db() as c:
            f = self._tier(c, design_id, stage, up, fidelity)
            rows = c.execute("SELECT * FROM elites WHERE design_id=? AND stage=? AND upstream=? AND fidelity=? "
                             "ORDER BY J ASC, id ASC LIMIT ?", (design_id, stage, up, f, k or self.k)).fetchall() if f is not None else []
        return [self._row(r) for r in rows]

    def conditional(self, design_id: str, stage: str, upstream_id: int, k: int | None = None,
                    fidelity: int | None = None) -> list[dict]:
        """Top-k elites of ``stage`` whose upstream set contains ``upstream_id`` (highest fidelity present)."""
        with self._db() as c:
            rows = c.execute("SELECT * FROM elites WHERE design_id=? AND stage=? ORDER BY J ASC, id ASC",
                             (design_id, stage)).fetchall()
        rows = [r for r in rows if str(int(upstream_id)) in r["upstream"].split(",")]
        f = fidelity if fidelity is not None else max((int(r["fidelity"]) for r in rows), default=None)
        out = [self._row(r) for r in rows if int(r["fidelity"]) == f]
        return out[: (k or self.k)]

    def best_J(self, design_id: str, stage: str, upstream_ids=(), fidelity: int | None = None) -> float:
        up = upstream_key(upstream_ids)
        with self._db() as c:
            f = self._tier(c, design_id, stage, up, fidelity)
            r = c.execute("SELECT MIN(J) AS j FROM elites WHERE design_id=? AND stage=? AND upstream=? AND fidelity=?",
                          (design_id, stage, up, f)).fetchone() if f is not None else None
        return math.inf if r is None or r["j"] is None else float(r["j"])

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
            keys = c.execute("SELECT DISTINCT design_id, stage, upstream, fidelity FROM elites ORDER BY 1, 2, 3, 4").fetchall()
            h = hashlib.sha256()
            for key in keys:
                rows = c.execute("SELECT id, J, layout_hash FROM elites WHERE design_id=? AND stage=? AND upstream=? "
                                 "AND fidelity=? ORDER BY J ASC, id ASC LIMIT ?", (*tuple(key), self.k)).fetchall()
                for r in rows:
                    h.update(("%s|%s|%s|f%d|%d|%.17g|%s\n" % (*tuple(key), r["id"], r["J"], r["layout_hash"])).encode())
            c.execute("PRAGMA wal_checkpoint(FULL)")
        sid = (label + "_" if label else "") + h.hexdigest()[:12]
        snap = self.root / "snapshots"
        snap.mkdir(exist_ok=True)
        shutil.copy2(self.db_path, snap / (sid + ".sqlite"))
        return sid
