"""Originality tooling (task T7.5): code-overlap scan, rediscovery driver, text-overlap scan."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import code_overlap_scan as C  # noqa: E402
import originality_scan as OS  # noqa: E402
import overlap_scan as T  # noqa: E402

SRC = '''
def spread(points, alpha, rng):
    """docstrings never count"""
    out = []
    for i in range(len(points)):
        x, y = points[i]
        out.append((x * alpha + rng.normal(), y * alpha - rng.normal()))  # comments never count
    total = sum(p[0] for p in out) / max(1, len(out))
    return [(p[0] - total, p[1]) for p in out]
'''
RENAMED = SRC.replace("points", "pts").replace("alpha", "a").replace("spread", "jitter").replace("total", "mean_x")
OTHER = '''
class Ledger:
    def __init__(self, path):
        self.path = path
        self.rows = {}

    def add(self, key, value):
        if key in self.rows:
            raise KeyError(key)
        self.rows[key] = value
'''


def test_tokens_drop_docstrings_comments_and_names():
    toks = [t for t, _ in C.tokens(SRC)]
    assert "STR" not in toks[:12] and "docstrings" not in " ".join(toks) and "ID" in toks
    assert [t for t, _ in C.tokens(SRC)] == [t for t, _ in C.tokens(RENAMED)]


def test_scan_finds_a_renamed_copy_and_not_an_unrelated_file(tmp_path):
    (tmp_path / "ours").mkdir()
    (tmp_path / "theirs").mkdir()
    (tmp_path / "ours" / "copy.py").write_text(RENAMED)
    (tmp_path / "ours" / "other.py").write_text(OTHER)
    (tmp_path / "theirs" / "orig.py").write_text(SRC)
    res = C.scan(C.py_files(tmp_path / "ours"), {"lib": C.py_files(tmp_path / "theirs")}, k=12)
    by = {Path(r["file"]).name: r for r in res["rows"]}
    n = len(C.tokens(SRC))
    assert by["copy.py"]["share"] == 1.0 and by["copy.py"]["run"] == n and by["copy.py"]["match_tree"] == "lib"
    assert by["other.py"]["share"] == 0.0 and by["other.py"]["match"] is None
    assert res["share_ge_010"] == 1 and res["longest_run"] == n


def test_longest_run_is_exact_and_reports_positions():
    a = C.tokens("x = 1\n" + OTHER)
    b = C.tokens(OTHER + "\ny = 2\n")
    L, i, j = C.longest_run(a, b, 5)
    assert L == len(C.tokens(OTHER)) and a[i][1] == 3 and b[j][1] == 2
    assert C.longest_run(C.tokens("a = 1\n"), b, 5) == (0, -1, -1)


def test_originality_driver_flags_a_copy(tmp_path):
    ref = tmp_path / "ref"
    ref.mkdir()
    (ref / "orig.py").write_text(SRC * 3)
    (tmp_path / "copy.py").write_text(RENAMED * 3)
    (tmp_path / "other.py").write_text(OTHER * 3)
    res = OS.scan(OS.targets_of([str(tmp_path / "copy.py"), str(tmp_path / "other.py")]), {"lib": ref})
    flags = {Path(r["file"]).name: r["rediscovery"] for r in res["rows"]}
    assert flags == {"copy.py": True, "other.py": False} and res["rediscoveries"] == 1
    assert OS.main([str(tmp_path / "other.py"), "--ref", "lib=%s" % ref, "nothere=%s" % (tmp_path / "missing")]) == 0
    assert OS.main([str(tmp_path / "copy.py"), "--ref", "lib=%s" % ref]) == 1


def test_text_overlap_reports_shared_sentences(tmp_path):
    shared = ("the guard tries none a quarter a half and all of the move scores each candidate "
              "and keeps the best so the result is never worse than the raw program")
    ms = "# Title\n\nIntro line here.\n\n" + shared + "\n\nOur own closing words follow here.\n"
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.md").write_text("Some other text.\n" + shared.upper() + "\n")
    (tmp_path / "src" / "b.txt").write_text("completely different words about routing capacity and vias in metal layers\n")
    (tmp_path / "src" / "c.pdf").write_bytes(b"%PDF-1.4")
    files, skipped = T.read_sources([tmp_path / "src"])
    assert len(files) == 2 and len(skipped) == 1 and "c.pdf" in skipped[0]
    res = {Path(r["source"]).name: r for r in T.scan(ms, files, n=8, min_run=12)}
    assert res["a.md"]["share"] > 0.5 and res["a.md"]["runs"][0]["words"] == len(shared.split())
    assert res["a.md"]["runs"][0]["manuscript_lines"] == [5, 5]
    assert res["b.txt"]["share"] == 0.0 and res["b.txt"]["runs"] == []


def test_tiny_files_are_listed_not_scored(tmp_path):
    (tmp_path / "ours").mkdir()
    (tmp_path / "ref").mkdir()
    (tmp_path / "ours" / "__init__.py").write_text('"""Package."""\n\nfrom .a import b, c, d\n')
    (tmp_path / "ref" / "x.py").write_text("from .a import b, c, d\n" + OTHER)
    res = C.scan(C.py_files(tmp_path / "ours"), {"lib": C.py_files(tmp_path / "ref")}, k=12)
    assert res["rows"] == [] and len(res["too_small"]) == 1
    r2 = OS.scan(OS.targets_of([str(tmp_path / "ours")]), {"lib": tmp_path / "ref"})
    assert r2["rows"] == [] and len(r2["too_small"]) == 1 and r2["rediscoveries"] == 0
