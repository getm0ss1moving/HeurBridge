"""Cooperative slot sharing on the EDA server: the cell chat's runs take the slots the macro chat does not use.

The server runs at most CAP = 8 OpenROAD processes at a time (a red line).  Jobs register the slots they hold as files
``<dir>/<owner>.<job>`` holding a number; owner is "macro" or "cs", job is the vault run name.  A registration counts
while its job runs (the vault's pid file ``<state dir>/<job>.pid`` names a live process).  A registration whose job
has not started yet counts for PENDING_S seconds after the file was written (a launch announced ahead), then lapses;
one whose job has ended counts no more.

The cell chat's gated evaluations (scripts/run_cell_stage.py --slot-gate) take one token each, a file
``<dir>/tokens/<pid>.<thread>.<n>``, removed when the evaluation ends or when its process is gone.  An evaluation
starts only while tokens + registrations < the cap, tokens < the cell chat's allowance, no gated waiter with a better
(lower) priority is waiting, and the server's live OpenROAD count is below the cap.  So the macro chat takes its slots
back by registering a job: no new gated evaluation starts, and the running ones end within one run.

The cap and the allowance follow the owner's decision D16 (8 Oct): while other users' jobs hold much of the server, our
total OpenROAD runs stay at most floor((cores - other users' cores) / 8), split between the chats by agreement.
load_aware_cap measures that bound (``ps``: the CPU share of every process that is not this account's); the
allowance file ``<dir>/cs.allowance`` holds the cell chat's agreed share, written by either chat, so the share can
change without restarting a run.  Without the file the allowance is the cap.
"""

from __future__ import annotations

import os
import re
import subprocess
import threading
import time
from pathlib import Path

CAP = 8
ALLOWANCE = "cs.allowance"                  # the cell chat's share (allowance()); not a job registration
PENDING_S = 6 * 3600
LOCK_STALE_S = 120
STATE_DIR = os.environ.get("HB_STATE_DIR", "/data/dzy/heura_repr/hb/state")


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:                     # exists, another account's
        return True
    return True


def job_alive(state_dir, job: str) -> bool | None:
    """True if the vault job runs, False if its pid file names no live process, None if it has no pid file."""
    p = Path(state_dir) / ("%s.pid" % job)
    try:
        pid = int(p.read_text().split()[0])
    except (OSError, ValueError, IndexError):
        return None
    return _pid_alive(pid)


def registered(slot_dir, state_dir=STATE_DIR, now: float | None = None) -> dict:
    """{owner: slots} over the registrations that count now, and the jobs behind them."""
    now = time.time() if now is None else now
    out = {"macro": 0, "cs": 0, "jobs": {}}
    for f in sorted(Path(slot_dir).glob("*.*")):
        m = re.match(r"^(macro|cs)\.([A-Za-z0-9_.-]+)$", f.name)
        if not m or f.name == ALLOWANCE:
            continue
        try:
            n = int(f.read_text().split()[0])
        except (OSError, ValueError, IndexError):
            continue
        a = job_alive(state_dir, m.group(2))
        if a is False:
            continue                            # the job has ended
        if a is None and now - f.stat().st_mtime > PENDING_S:
            continue                            # announced, never started
        out[m.group(1)] += n
        out["jobs"]["%s.%s" % m.groups()] = n
    return out


def foreign_cores() -> float:
    """Cores in use by processes of other accounts (ps's %CPU, each process's average over its life)."""
    import getpass
    me = getpass.getuser()
    p = subprocess.run(["ps", "-eo", "user:64,pcpu"], capture_output=True, text=True)
    if p.returncode != 0:                       # BSD ps: no width suffix
        p = subprocess.run(["ps", "-eo", "user,pcpu"], capture_output=True, text=True)
    total = 0.0
    for line in p.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[0] != me:
            try:
                total += float(parts[1])
            except ValueError:
                pass
    return total / 100.0


def load_aware_cap(cores: int | None = None, threads: int = 8) -> int:
    """D16: floor((cores - other accounts' cores) / threads), within [0, CAP]."""
    cores = os.cpu_count() if cores is None else cores
    return max(0, min(CAP, int((cores - foreign_cores()) // threads)))


def allowance(slot_dir, default: int) -> int:
    """The cell chat's agreed share (``<dir>/cs.allowance``), or ``default`` when there is no readable file."""
    try:
        return max(0, int((Path(slot_dir) / ALLOWANCE).read_text().split()[0]))
    except (OSError, ValueError, IndexError):
        return default


def live_openroad() -> int:
    """OpenROAD processes running on this machine (the processes named openroad, as the red line counts them)."""
    p = subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True)
    return sum(1 for line in p.stdout.splitlines() if re.match(r"^\S*openroad\s", line + " "))


class SlotGate:
    def __init__(self, slot_dir, state_dir=STATE_DIR, cap: int = CAP, poll: float = 30.0, live_fn=live_openroad,
                 log=print, cap_fn=None):
        self.dir, self.state_dir, self.cap, self.poll = Path(slot_dir), state_dir, cap, poll
        self.live_fn, self.log, self.cap_fn = live_fn, log, cap_fn
        for sub in ("tokens", "waiters"):
            (self.dir / sub).mkdir(parents=True, exist_ok=True)
        self._seq = 0
        self._mu = threading.Lock()

    # ---- a mutex shared by every process using this directory
    def _lock(self):
        lk = self.dir / ".lock"
        while True:
            try:
                lk.mkdir()
                return lk
            except FileExistsError:
                try:
                    if time.time() - lk.stat().st_mtime > LOCK_STALE_S:
                        lk.rmdir()              # a process died holding it
                        continue
                except OSError:
                    continue
                time.sleep(0.05)

    def _clean(self, sub: str) -> list:
        """Live entries of tokens/ or waiters/ (files whose leading pid is gone are removed)."""
        out = []
        for f in (self.dir / sub).iterdir():
            parts = f.name.split(".")
            try:
                pid = int(parts[1] if sub == "waiters" else parts[0])
            except (ValueError, IndexError):
                continue
            if _pid_alive(pid):
                out.append(f)
            else:
                f.unlink(missing_ok=True)
        return out

    def current_cap(self) -> int:
        return min(self.cap, self.cap_fn()) if self.cap_fn is not None else self.cap

    def state(self) -> dict:
        reg = registered(self.dir, self.state_dir)
        cap = self.current_cap()
        return {"tokens": len(self._clean("tokens")), "macro": reg["macro"], "cs": reg["cs"], "live": self.live_fn(),
                "cap": cap, "allowance": allowance(self.dir, cap)}

    def acquire(self, priority: int = 0, label: str = "") -> Path:
        """Wait for a slot; returns the token to release."""
        with self._mu:
            self._seq += 1
            seq = self._seq
        me = "%d.%d.%d" % (os.getpid(), threading.get_ident() % 10 ** 9, seq)
        waiter = self.dir / "waiters" / ("%d.%s" % (int(priority), me))
        waiter.write_text(label)
        said = False
        try:
            while True:
                lk = self._lock()
                try:
                    tokens = self._clean("tokens")
                    waiters = self._clean("waiters")
                    reg = registered(self.dir, self.state_dir)
                    better = any(int(w.name.split(".")[0]) < int(priority) for w in waiters if w != waiter)
                    used = len(tokens) + reg["macro"] + reg["cs"]
                    live = self.live_fn()
                    cap = self.current_cap()
                    share = allowance(self.dir, cap)
                    if used < cap and len(tokens) < share and not better and live < cap:
                        tok = self.dir / "tokens" / me
                        tok.write_text(label)
                        return tok
                finally:
                    lk.rmdir()
                if not said:
                    self.log("HB_SLOTS wait %s: tokens %d (allowance %d), macro %d, cs %d, live %d, cap %d%s" % (
                        label, len(tokens), share, reg["macro"], reg["cs"], live, cap,
                        ", a better priority waits" if better else ""))
                    said = True
                time.sleep(self.poll)
        finally:
            waiter.unlink(missing_ok=True)

    def release(self, token: Path):
        Path(token).unlink(missing_ok=True)
