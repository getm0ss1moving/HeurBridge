"""scripts/server/cs_c1_queue.sh with fake jobs: ledgers copied from running stage-1 jobs, a stage-2 entry started when its
stage-1 job has ended, an incomplete copy skipped by name, a stage-1 entry started at once (the slot gate inside the
runner orders and caps the evaluations: tests/test_cellstage_slots.py)."""

import json
import subprocess
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "scripts" / "server" / "cs_c1_queue.sh"
ROW = {"run_id": "x", "status": "ok", "fidelity": 1, "evaluator": "orfs_cs_0"}


def _job(state: Path, name: str, seconds: float, wd: Path | None = None):
    """A fake vault job: a sleeping process with the pid (and workspace) files hbv writes; reaped when it ends."""
    p = subprocess.Popen(["sleep", str(seconds)])
    (state / ("%s.pid" % name)).write_text("%d\n" % p.pid)
    if wd is not None:
        (state / ("%s.wd" % name)).write_text("%s\n" % wd)
    threading.Thread(target=p.wait, daemon=True).start()
    return p


def test_queue_starts_each_step_when_ready_and_skips_incomplete_ledgers(tmp_path):
    state, repo = tmp_path / "state", tmp_path / "repo"
    state.mkdir()
    (repo / "logs").mkdir(parents=True)
    (repo / "configs" / "cellstage").mkdir(parents=True)
    for d in "ABC":
        (repo / "configs" / "cellstage" / ("c1_%s.json" % d)).write_text(json.dumps({"recipes": [{"id": "r0"}]}, indent=1))
        (repo / "runs" / "seed_orfs" / d).mkdir(parents=True)
    for d, rows in (("A", 2), ("B", 1)):           # A's stage 1 completes (2 layouts x 1 recipe), B's misses a row
        w = tmp_path / ("ws_%s" % d)
        led = w / "repo" / "runs" / "seed_orfs" / d / "evals_cs_c1.jsonl"
        led.parent.mkdir(parents=True)
        led.write_text("".join(json.dumps(ROW) + "\n" for _ in range(rows)))
        _job(state, "cs_c1_%s" % d, 1.0, w)
    events = tmp_path / "events"
    fake = tmp_path / "fake_run.sh"
    fake.write_text('#!/bin/bash\necho "start $1 $2 $(python3 -c "import time; print(time.time())")" >> %s\n'
                    'sleep 0.5\n' % events)
    fake.chmod(0o755)
    t0 = time.time()
    p = subprocess.run(["bash", str(QUEUE), "s2:A:a.f2", "s2:B:b.f2", "s1:C:c.f2"], cwd=repo,
                       env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HB_STATE_DIR": str(state),
                            "HB_SLOT_DIR": str(tmp_path / "slots"), "HB_QUEUE_POLL": "0.1", "HB_QUEUE_RUN": str(fake)},
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "s2:B:b.f2 skipped: the stage-1 ledger has 1 of 2 f1 rows" in p.stdout
    assert "all entries done" in p.stdout
    assert (repo / "runs" / "seed_orfs" / "A" / "evals_cs_c1.jsonl").read_text().count('"fidelity": 1,') == 2
    ev = {}
    for line in events.read_text().splitlines():
        what, kind, d, ts = line.split()
        ev[(kind, d)] = float(ts) - t0
    assert ("s2", "B") not in ev
    assert ev[("s1", "C")] < 1.0                         # at once: the runner's slot gate orders the evaluations
    assert ev[("s2", "A")] >= 1.0                         # after A's stage-1 job ended
