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


def test_thread_count_reaches_the_placer(tmp_path, monkeypatch):
    """DreamplaceEvaluator.threads reaches DREAMPlace's num_threads (default 8, DREAMPlace's own); the CPU label
    job sets fewer per worker so that workers x threads stays within the cores."""
    from heurbridge.eval import dreamplace as DP
    from heurbridge.pipeline.evaluators import DreamplaceEvaluator
    assert DP.params("a.aux", "out")["num_threads"] == 8 and DreamplaceEvaluator().threads == 8
    seen = {}

    def fake_run_placer(p, work, timeout):
        seen.update(p)
        return 1, "stopped by the test", 0.0
    monkeypatch.setattr(DP, "run_placer", fake_run_placer)
    monkeypatch.setattr(DP, "write_oriented_bookshelf", lambda d, l, w, name: tmp_path / "x.aux")
    import types
    DP._run_f1(types.SimpleNamespace(id="d"), None, tmp_path, None, False, 10, 0, 60, threads=4)
    assert seen["num_threads"] == 4 and seen["gpu"] == 0
