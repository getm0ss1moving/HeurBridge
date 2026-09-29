"""DREAMPlace runner: a momentary GPU out-of-memory is rerun, nothing else (eval/dreamplace.run_placer)."""


def test_placer_reruns_only_on_gpu_oom(tmp_path, monkeypatch):
    """A momentary GPU out-of-memory is rerun (it says nothing about the layout); any other failure is returned."""
    import subprocess as sp
    from heurbridge.eval import dreamplace as DP
    monkeypatch.setenv("HB_DREAMPLACE", str(tmp_path))
    monkeypatch.setattr(DP, "OOM_WAITS_S", (0, 0))
    monkeypatch.setattr(DP.time, "sleep", lambda s: None)
    calls = []

    def fake(results):
        def run_group(cmd, timeout=None, env=None, cwd=None):
            calls.append(cmd)
            rc, err = results[min(len(calls) - 1, len(results) - 1)]
            return sp.CompletedProcess(cmd, rc, stdout="", stderr=err)
        return run_group

    monkeypatch.setattr(DP.tools, "run_group", fake([(1, "RuntimeError: CUDA out of memory. Tried"), (0, "ok")]))
    rc, log, _ = DP.run_placer({}, tmp_path)
    assert rc == 0 and len(calls) == 2 and "rerun" in (tmp_path / "dreamplace.log").read_text()
    calls.clear()
    monkeypatch.setattr(DP.tools, "run_group", fake([(1, "Segmentation fault")]))
    rc, _, _ = DP.run_placer({}, tmp_path)
    assert rc == 1 and len(calls) == 1                         # not an OOM: returned as it is
    calls.clear()
    monkeypatch.setattr(DP.tools, "run_group", fake([(1, "CUDA error: out of memory")]))
    rc, _, _ = DP.run_placer({}, tmp_path)
    assert rc == 1 and len(calls) == 3                         # persistent OOM: two reruns, then the failure


def test_placer_reruns_after_sigkill(tmp_path, monkeypatch):
    """SIGKILL (the host OOM killer) is a resource failure: rerun; a timeout is not."""
    import subprocess as sp
    from heurbridge.eval import dreamplace as DP
    monkeypatch.setenv("HB_DREAMPLACE", str(tmp_path))
    monkeypatch.setattr(DP, "OOM_WAITS_S", (0, 0))
    monkeypatch.setattr(DP.time, "sleep", lambda s: None)
    calls = []
    results = [(-9, ""), (0, "ok")]

    def run_group(cmd, timeout=None, env=None, cwd=None):
        calls.append(cmd)
        rc, err = results[min(len(calls) - 1, len(results) - 1)]
        return sp.CompletedProcess(cmd, rc, stdout="", stderr=err)

    monkeypatch.setattr(DP.tools, "run_group", run_group)
    rc, _, _ = DP.run_placer({}, tmp_path)
    assert rc == 0 and len(calls) == 2 and "host out of memory" in (tmp_path / "dreamplace.log").read_text()

    def timed_out(cmd, timeout=None, env=None, cwd=None):
        calls.append(cmd)
        raise sp.TimeoutExpired(cmd, timeout, output="")

    calls.clear()
    monkeypatch.setattr(DP.tools, "run_group", timed_out)
    rc, _, _ = DP.run_placer({}, tmp_path)
    assert rc == "timeout" and len(calls) == 1
