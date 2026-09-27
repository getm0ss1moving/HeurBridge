"""heurbridge.tools.run_group: a timeout kills the child's whole process group (ORFS sub-makes, red line A.2)."""

import os
import subprocess
import time

import pytest

from heurbridge import tools


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    st = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    return bool(st) and not st.startswith("Z")


def test_run_group_output_and_returncode():
    p = tools.run_group(["sh", "-c", "echo out; echo err >&2; exit 3"], timeout=30)
    assert (p.returncode, p.stdout, p.stderr) == (3, "out\n", "err\n")


def test_run_group_timeout_kills_grandchildren(tmp_path):
    pidf = tmp_path / "grandchild.pid"
    # a make-like chain: sh starts a long-running grandchild and waits for it
    cmd = ["sh", "-c", "sleep 60 & echo $! > %s; echo started; wait" % pidf]
    t0 = time.time()
    with pytest.raises(subprocess.TimeoutExpired) as e:
        tools.run_group(cmd, timeout=1)
    assert time.time() - t0 < 30
    assert "started" in (e.value.output or "")
    gpid = int(pidf.read_text())
    deadline = time.time() + 10
    while _alive(gpid) and time.time() < deadline:
        time.sleep(0.1)
    assert not _alive(gpid)


def test_run_group_env_and_cwd(tmp_path):
    p = tools.run_group(["sh", "-c", "echo $HB_T; pwd"], timeout=30, env=dict(os.environ, HB_T="x"), cwd=tmp_path)
    assert p.stdout.split()[0] == "x"
    assert os.path.realpath(p.stdout.split()[1]) == os.path.realpath(tmp_path)
