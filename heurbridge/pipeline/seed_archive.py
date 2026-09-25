"""Archive-seeding campaign (task T2.7).

Per design: all seed programs x ``seeds`` -> sandbox run -> P_M -> contract -> f1; the top
``top_f2`` by f1 J go to f2 and into the archive; then ``ls_steps`` steps of local search from the
best (moves: shift one macro by +-1..3 macro pitches, swap two same-size macros, flip orientation),
each neighbour checked at f1 and the best verified at f2.  Resumable: every evaluation is appended
to <out>/<design>/evals.jsonl under a run_id and skipped when present.  Every failure (sandbox
error, projection failure, contract violation, tool failure) is recorded by name with J = +inf.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..archive.store import Archive, Candidate
from ..core import contract, orient as O, project
from ..core.design import Design, Layout
from ..eval import cost
from ..evolve import sandbox as SB
from .evaluators import Evaluator


@dataclass
class SeedConfig:
    seeds: int = 5
    top_f2: int = 10
    ls_steps: int = 8
    ls_neighbours: int = 6
    halo: float = 0.0
    cpu_s: float = 60.0
    seed: int = 0


class Ledger:
    """Append-only JSONL of evaluations (resume support)."""

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.rows = {}
        if path.exists():
            for line in path.read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    self.rows[r["run_id"]] = r

    def get(self, run_id):
        return self.rows.get(run_id)

    def add(self, row: dict):
        self.rows[row["run_id"]] = row
        with open(self.path, "a") as fh:
            fh.write(json.dumps(row, default=str) + "\n")


def _eval(ev: Evaluator, design, layout, base, run_id, work, ledger: Ledger, extra: dict) -> dict:
    row = ledger.get(run_id)
    if row is not None:
        return row
    t0 = time.time()
    rec = None
    try:
        rec = ev.evaluate(design, layout, run_id, work / run_id)
        rc = rec.get("returncode", 0)
        if rc not in (0, None):
            raise RuntimeError("tool returncode %s (%s)" % (rc, rec.get("failure") or "no reason parsed"))
        res = ev.score(rec, base)
        row = {"run_id": run_id, "status": "ok", "fidelity": ev.fidelity, "evaluator": ev.name, "J": res.J_inf,
               "J_raw": res.J, "admissible": res.admissible, "partial": res.partial, "terms": res.terms,
               "gates": res.gates, "unchecked": res.unchecked, "record": rec}
    except Exception as e:
        row = {"run_id": run_id, "status": "eval_failed", "fidelity": ev.fidelity, "evaluator": ev.name,
               "J": math.inf, "error": "%s: %s" % (type(e).__name__, str(e)[:300])}
        if rec is not None:                     # keep the tool record (partial metrics, failure reason)
            row["record"] = rec
    row.update(extra)
    row["wall_s"] = round(time.time() - t0, 2)
    row["pos_macros"] = layout.pos[design.is_macro & ~design.is_fixed].tolist()
    row["orient_macros"] = layout.orient[design.is_macro & ~design.is_fixed].tolist()
    ledger.add(row)
    return row


def _layout_from_row(design: Design, base: Layout, row: dict) -> Layout:
    l = base.copy()
    mm = design.is_macro & ~design.is_fixed
    l.pos[mm] = np.asarray(row["pos_macros"])
    l.orient[mm] = np.asarray(row["orient_macros"], dtype=np.int8)
    return l


def neighbours(design: Design, layout: Layout, rng: np.random.Generator, n: int) -> list:
    """T2.7 local-search moves on movable macros."""
    mm = np.flatnonzero(design.is_macro & ~design.is_fixed)
    eff = O.effective_size(design.size, layout.orient) / design.core_wh
    masters = design.masters or ["%.6g_%.6g" % tuple(v) for v in design.size]
    out = []
    for _ in range(n):
        l = layout.copy()
        u = rng.random()
        if u < 0.6 or len(mm) < 2:
            i = int(rng.choice(mm))
            ax = int(rng.integers(2))
            k = int(rng.choice([-3, -2, -1, 1, 2, 3]))
            l.pos[i, ax] = float(np.clip(l.pos[i, ax] + k * eff[i, ax], eff[i, ax] / 2, 1 - eff[i, ax] / 2))
            move = "shift"
        elif u < 0.85:
            i = int(rng.choice(mm))
            same = [j for j in mm if j != i and masters[j] == masters[i] and np.allclose(design.size[j], design.size[i])]
            if not same:
                continue
            j = int(rng.choice(same))
            l.pos[[i, j]] = l.pos[[j, i]]
            move = "swap"
        else:
            i = int(rng.choice(mm))
            l.orient[i] = int(rng.choice([o for o in (O.R0, O.MX, O.MY, O.R180) if o != l.orient[i]]))
            move = "flip"
        out.append((move, l))
    return out


def seed_design(design: Design, base_layout: Layout, programs: list, f1: Evaluator, f2: Evaluator | None,
                archive: Archive, baseline: cost.Baseline, out_dir: str | Path, cfg: SeedConfig | None = None,
                cluster=None, log=print) -> dict:
    cfg = cfg or SeedConfig()
    out = Path(out_dir) / design.id
    work = out / "work"
    ledger = Ledger(out / "evals.jsonl")
    scope = design.is_macro & ~design.is_fixed
    view = SB.make_view(design, base_layout, cluster, halo=cfg.halo)
    rows = []
    for prog in programs:
        for s in range(cfg.seeds):
            rid = "%s.%s.s%d.f1" % (design.id, prog["id"], s)
            if ledger.get(rid):
                rows.append(ledger.get(rid))
                continue
            r = SB.run_program(prog["source"], view, None, s, cpu_s=cfg.cpu_s)
            extra = {"program": prog["id"], "program_hash": prog["sha256"], "seed": s, "stage": "M"}
            if r.status != "ok":
                row = {"run_id": rid, "status": "program_" + r.status, "J": math.inf, "error": r.error[:300], **extra}
                ledger.add(row)
                rows.append(row)
                continue
            lay = SB.to_layout(design, base_layout, r)
            bad = SB.validate_output(design, base_layout, r, scope)
            lay_p, rep = project.legalize_macros(design, lay, halo=cfg.halo)
            try:
                if bad:
                    raise contract.ContractViolation("M", bad)
                contract.check(design, lay_p, base_layout, stage="M", scope=scope)
                if not rep.ok:
                    raise contract.ContractViolation("M", ["P_M failed: %s" % rep.failed[:5]])
            except contract.ContractViolation as e:
                row = {"run_id": rid, "status": "contract_violation", "J": math.inf, "error": str(e)[:300], **extra}
                ledger.add(row)
                rows.append(row)
                continue
            extra["pm_disp"] = rep.mean_disp
            rows.append(_eval(f1, design, lay_p, baseline, rid, work, ledger, extra))
    ok = sorted([r for r in rows if r.get("status") == "ok" and math.isfinite(r["J"])], key=lambda r: r["J"])
    log(json.dumps({"design": design.id, "f1_ok": len(ok), "f1_total": len(rows),
                    "f1_failed": {r["run_id"]: r["status"] for r in rows if r.get("status") != "ok"}}))
    top = ok[: cfg.top_f2]
    verified = []
    top_ev = f2 or f1
    for r in top:
        lay = _layout_from_row(design, base_layout, r)
        rid = r["run_id"][:-3] + (".f2" if f2 else ".f1")
        vr = r if f2 is None else _eval(f2, design, lay, baseline, rid, work, ledger,
                                        {k: r.get(k) for k in ("program", "program_hash", "seed", "stage")})
        verified.append((vr, lay))
        _insert(archive, design, lay, vr, top_ev)
    # local search from the best verified layout
    rng = np.random.default_rng(cfg.seed)
    if verified:
        best_row, best_lay = min(verified, key=lambda t: t[0]["J"])
        cur_J = best_row["J"]
        for step in range(cfg.ls_steps):
            cands = []
            for n, (move, l) in enumerate(neighbours(design, best_lay, rng, cfg.ls_neighbours)):
                lp, rep = project.legalize_macros(design, l, halo=cfg.halo)
                if not rep.ok:
                    continue
                rid = "%s.ls%d.n%d.f1" % (design.id, step, n)
                row = _eval(f1, design, lp, baseline, rid, work, ledger, {"program": "LS", "move": move, "stage": "M"})
                cands.append((row["J"], row, lp))
            if not cands:
                continue
            j, row, lp = min(cands, key=lambda t: t[0])
            if j < cur_J:
                cur_J, best_lay = j, lp
                if f2 is not None:
                    rid = "%s.ls%d.f2" % (design.id, step)
                    vr = _eval(f2, design, lp, baseline, rid, work, ledger, {"program": "LS", "stage": "M"})
                    _insert(archive, design, lp, vr, f2)
                else:
                    _insert(archive, design, lp, row, f1)
    snap = archive.snapshot("A0_" + design.id)
    summary = {"design": design.id, "evaluated": len(ledger.rows), "archive_top": [e["J"] for e in archive.topk(design.id, "M")],
               "snapshot": snap}
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    return summary


def _insert(archive: Archive, design: Design, lay: Layout, row: dict, ev: Evaluator):
    if row.get("status") != "ok":
        return
    rec = row.get("record", {})
    if rec.get("cluster_pos") is not None:              # downstream cluster centroids travel with the elite
        lay = lay.copy()
        lay.routes = dict(lay.routes or {}, cluster_pos=np.asarray(rec["cluster_pos"], dtype=np.float64))
    archive.insert(Candidate(design_id=design.id, stage="M", layout=lay, fidelity=ev.fidelity, J=row["J"],
                             admissible=bool(row.get("admissible")),
                             metrics={k: v for k, v in rec.items() if k != "cluster_pos"},
                             gates=row.get("gates", {}),
                             provenance={"program_hash": row.get("program_hash"), "program": row.get("program"),
                                         "seed": row.get("seed"), "run_id": row["run_id"], "evaluator": ev.name}))
