"""The slot gate shared with the macro chat (heurbridge/cellstage/slots.py)."""

import os
import subprocess
import threading
import time

from heurbridge.cellstage import slots as SL


def _dead_pid() -> int:
    p = subprocess.Popen(["true"])
    p.wait()
    return p.pid


def _job(state, name, pid):
    (state / ("%s.pid" % name)).write_text("%d\n" % pid)


def test_registrations_count_while_their_job_runs(tmp_path):
    slots, state = tmp_path / "slots", tmp_path / "state"
    slots.mkdir(), state.mkdir()
    _job(state, "tb9", os.getpid())                 # running
    _job(state, "old", _dead_pid())                 # ended
    (slots / "macro.tb9").write_text("2\n")
    (slots / "macro.old").write_text("4\n")
    (slots / "macro.next").write_text("2\n")        # announced, not started
    (slots / "cs.s1").write_text("2\n")
    _job(state, "s1", os.getpid())
    (slots / "junk").write_text("9\n")
    got = SL.registered(slots, state)
    assert (got["macro"], got["cs"]) == (4, 2) and set(got["jobs"]) == {"macro.tb9", "macro.next", "cs.s1"}
    old = time.time() - SL.PENDING_S - 10
    os.utime(slots / "macro.next", (old, old))      # an announcement that lapsed
    assert SL.registered(slots, state)["macro"] == 2


def _gate(tmp_path, live=0):
    slots, state = tmp_path / "slots", tmp_path / "state"
    state.mkdir(exist_ok=True)
    return SL.SlotGate(slots, state, cap=3, poll=0.02, live_fn=lambda: live, log=lambda m: None), slots, state


def test_tokens_fill_the_free_slots_and_wait_when_full(tmp_path):
    g, slots, state = _gate(tmp_path)
    (slots / "macro.dpls_c").write_text("1\n")
    _job(state, "dpls_c", os.getpid())
    t1, t2 = g.acquire(0, "a"), g.acquire(0, "b")      # 1 registered + 2 tokens = cap 3
    got = {}

    def third():
        got["t"] = g.acquire(0, "c")
    th = threading.Thread(target=third)
    th.start()
    time.sleep(0.2)
    assert "t" not in got                           # full: waits
    g.release(t1)
    th.join(2)
    assert "t" in got and g.state()["tokens"] == 2
    g.release(t2), g.release(got["t"])
    assert g.state()["tokens"] == 0


def test_stale_tokens_are_reclaimed_and_the_live_count_is_a_hard_cap(tmp_path):
    g, slots, state = _gate(tmp_path)
    for i in range(3):
        (slots / "tokens" / ("%d.1.%d" % (_dead_pid(), i))).write_text("gone")
    tok = g.acquire(0, "x")                          # the dead processes' tokens do not count
    g.release(tok)
    g2, _, _ = _gate(tmp_path, live=3)
    got = {}
    th = threading.Thread(target=lambda: got.setdefault("t", g2.acquire(0, "y")))
    th.daemon = True
    th.start()
    time.sleep(0.2)
    assert "t" not in got                            # 3 OpenROAD processes already run: wait
    assert len(list((slots / "waiters").iterdir())) == 1


def test_a_better_priority_goes_first(tmp_path):
    g, slots, state = _gate(tmp_path)
    toks = [g.acquire(0, "run%d" % i) for i in range(3)]
    order = []

    def want(prio, name):
        t = g.acquire(prio, name)
        order.append(name)
        time.sleep(0.1)
        g.release(t)
    low = threading.Thread(target=want, args=(1, "stage1"))
    low.start()
    time.sleep(0.1)
    high = threading.Thread(target=want, args=(0, "stage2"))
    high.start()
    time.sleep(0.1)
    g.release(toks[0])                               # one slot frees while both wait
    low.join(3), high.join(3)
    for t in toks[1:]:
        g.release(t)
    assert order[0] == "stage2"
