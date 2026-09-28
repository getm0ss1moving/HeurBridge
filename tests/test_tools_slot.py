"""tools.slot: a host-wide cap on concurrent holders (flock), no-op without a limit."""

import fcntl
import os

import pytest

from heurbridge import tools


def _held(root, name, i):
    fd = os.open(os.path.join(root, "%s.%d" % (name, i)), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return True
    else:
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally:
        os.close(fd)


def test_slot_caps_holders(tmp_path, monkeypatch):
    monkeypatch.setenv("HB_SLOTS_DIR", str(tmp_path))
    with tools.slot("m", 2):
        assert _held(str(tmp_path), "m", 0) and not _held(str(tmp_path), "m", 1)
        with tools.slot("m", 2):                                 # the second holder takes the other slot
            assert _held(str(tmp_path), "m", 1)
    assert not _held(str(tmp_path), "m", 0) and not _held(str(tmp_path), "m", 1)   # released on exit


def test_slot_without_limit_is_a_noop(tmp_path, monkeypatch):
    monkeypatch.setenv("HB_SLOTS_DIR", str(tmp_path))
    with tools.slot("m", 0):
        pass
    assert os.listdir(tmp_path) == []


def test_slot_released_on_error(tmp_path, monkeypatch):
    monkeypatch.setenv("HB_SLOTS_DIR", str(tmp_path))
    with pytest.raises(RuntimeError):
        with tools.slot("m", 1):
            raise RuntimeError("x")
    assert not _held(str(tmp_path), "m", 0)
