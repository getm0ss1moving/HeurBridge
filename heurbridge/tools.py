"""EDA tool binaries.  Locally OpenROAD and Yosys run in the OpenLane container; on the servers natively.

Environment:
  HB_OPENROAD, HB_YOSYS   binary or wrapper to run (e.g. scripts/server/openroad_deb.sh, which sets the library
                          path of the unpacked OpenROAD 2024-12 package).  Setting HB_OPENROAD selects native runs.
  HB_DOCKER_IMAGE         container image for local runs (default efabless/openlane:master-arm64v8; "" = native)
  EDA_THREADS             OpenROAD threads per job (red line A.2: 8 on the servers; default 6 = the local VM)
"""

from __future__ import annotations

import os
import signal
import subprocess
import tempfile
import time
from contextlib import contextmanager

LOCAL_IMAGE = "efabless/openlane:master-arm64v8"


def run_group(cmd, timeout: float | None = None, env: dict | None = None, cwd=None) -> subprocess.CompletedProcess:
    """``subprocess.run(cmd, capture_output=True, text=True)`` with the child in its own process group; on a timeout
    (or any exception, e.g. KeyboardInterrupt) the whole group is killed before TimeoutExpired is re-raised.

    ORFS runs every step in a recursive sub-make (make -> sh -> time -> openroad | tee); killing only the top make
    leaves the rest running, and the next evaluation then shares the job's 8 threads with it (red line A.2).  The
    group stays in the job's session, which ``hbv.py stop`` kills as a whole."""
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, cwd=cwd,
                         process_group=0)
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_group(p)
        out, err = p.communicate()
        raise subprocess.TimeoutExpired(cmd, timeout, output=out, stderr=err) from None
    except BaseException:
        kill_group(p)
        raise
    return subprocess.CompletedProcess(cmd, p.returncode, out, err)


def kill_group(p: subprocess.Popen, grace: float = 10.0) -> None:
    """SIGTERM to the process group led by ``p``, then SIGKILL to whatever is left of it."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(p.pid, sig)
        except (ProcessLookupError, PermissionError):
            break                                       # group empty
        if sig == signal.SIGTERM:
            try:
                p.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                pass
    try:
        p.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        pass


@contextmanager
def slot(name: str, n: int | None, poll_s: float = 1.0):
    """At most ``n`` concurrent holders of ``name`` on this host, across processes and jobs (flock on n files in
    HB_SLOTS_DIR, default /dev/shm/.hb_slots); ``n`` falsy = no limit.  Used to keep memory-heavy steps of
    parallel jobs from coinciding.  Waiting changes only the timing, never a result."""
    if not n:
        yield
        return
    import fcntl
    root = os.environ.get("HB_SLOTS_DIR") or ("/dev/shm/.hb_slots" if os.path.isdir("/dev/shm") else
                                              os.path.join(tempfile.gettempdir(), ".hb_slots"))
    os.makedirs(root, mode=0o700, exist_ok=True)
    while True:
        for i in range(int(n)):
            fd = os.open(os.path.join(root, "%s.%d" % (name, i)), os.O_CREAT | os.O_RDWR, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                os.close(fd)
                continue
            try:
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
            return
        time.sleep(poll_s)


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


def describe(yosys: str | None = None) -> str:
    """Tool versions for run metadata and reports (queried once per process).  ``yosys``: the Yosys binary the
    flow actually runs (e.g. ORFS's YOSYS_EXE, run_seed_orfs.py --yosys) when it is not the one on PATH."""
    global _DESCRIBED
    if yosys:
        try:
            out = subprocess.run([yosys, "-V"], capture_output=True, text=True, timeout=60)
            yv = ((out.stdout or out.stderr).strip().splitlines() or ["?"])[0][:60].split(" (")[0]
        except (OSError, subprocess.SubprocessError):
            yv = "Yosys unavailable"
        return "%s; flow Yosys: %s (%s)" % (describe().split(", Yosys")[0], yv, yosys)
    if _DESCRIBED is None:
        img = docker_image()
        if img:
            _DESCRIBED = "container %s (OpenROAD b16bda7e, Yosys 0.38)" % img
        else:
            def first(cmd):
                try:
                    out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    return ((out.stdout or out.stderr).strip().splitlines() or ["?"])[0][:60]
                except (OSError, subprocess.SubprocessError):
                    return "unavailable"
            _DESCRIBED = "native OpenROAD %s, %s" % (first([binary("openroad"), "-version"]),
                                                     first([binary("yosys"), "-V"]).split(" (")[0])
    return _DESCRIBED
