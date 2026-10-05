#!/usr/bin/env python3
"""Text-overlap scan of a manuscript against source texts (task T7.5's overlap_scan.py).

  python scripts/overlap_scan.py MANUSCRIPT --sources PATH [PATH ...] [--n 8] [--min-run 12] [--json OUT]

Words are runs of letters and digits, lower-cased; markdown and LaTeX markup falls away with the punctuation.  For
each source: the share of the manuscript's word n-grams found in it, and every common word run of at least
--min-run words with the manuscript's line numbers, longest first.  Sources are text files (.txt, .md, .tex, ...)
or directories of them; a PDF or binary file is named and skipped (extract its text first).  This is a screen
before submission, not a replacement for iThenticate/Turnitin, which the owner runs (HEURBRIDGE_TASKS.md T7.5).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

WORD = re.compile(r"[A-Za-z0-9]+")
TEXT_EXT = {".txt", ".md", ".tex", ".rst", ".html", ".htm", ".csv", ""}


def words(text: str) -> list:
    """[(word, line)]."""
    out = []
    for ln, line in enumerate(text.splitlines(), 1):
        out += [(w.lower(), ln) for w in WORD.findall(line)]
    return out


def runs(a: list, b: list, n: int, min_run: int) -> list:
    """Maximal common word runs of at least ``min_run`` words: [(length, start in a, start in b)], longest first."""
    sa, sb = [w for w, _ in a], [w for w, _ in b]
    idx = defaultdict(list)
    for j in range(len(sb) - n + 1):
        idx[tuple(sb[j:j + n])].append(j)
    out = []
    for i in range(len(sa) - n + 1):
        for j in idx.get(tuple(sa[i:i + n]), ()):
            if i and j and sa[i - 1] == sb[j - 1]:
                continue                                # not the start of a maximal run
            L = n
            while i + L < len(sa) and j + L < len(sb) and sa[i + L] == sb[j + L]:
                L += 1
            if L >= min_run:
                out.append((L, i, j))
    return sorted(out, key=lambda r: (-r[0], r[1]))


def read_sources(paths) -> tuple:
    files, skipped = [], []
    for p in paths:
        p = Path(p)
        for f in (sorted(x for x in p.rglob("*") if x.is_file()) if p.is_dir() else [p]):
            if f.suffix.lower() not in TEXT_EXT:
                skipped.append("%s (%s file)" % (f, f.suffix or "no extension"))
                continue
            data = f.read_bytes()
            if b"\x00" in data[:4096]:
                skipped.append("%s (binary)" % f)
                continue
            files.append((f, data.decode("utf-8", errors="replace")))
    return files, skipped


def scan(manuscript: str, sources: list, n: int = 8, min_run: int = 12) -> list:
    m = words(manuscript)
    grams = {tuple(w for w, _ in m[i:i + n]) for i in range(len(m) - n + 1)}
    out = []
    for name, text in sources:
        s = words(text)
        sg = {tuple(w for w, _ in s[i:i + n]) for i in range(len(s) - n + 1)}
        rr = runs(m, s, n, min_run)
        out.append({"source": str(name), "share": len(grams & sg) / len(grams) if grams else 0.0,
                    "runs": [{"words": L, "manuscript_lines": [m[i][1], m[i + L - 1][1]],
                              "source_lines": [s[j][1], s[j + L - 1][1]]} for L, i, j in rr]})
    return sorted(out, key=lambda r: -r["share"])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("manuscript")
    ap.add_argument("--sources", nargs="+", required=True)
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--min-run", type=int, default=12)
    ap.add_argument("--json", default="")
    a = ap.parse_args(argv)
    files, skipped = read_sources(a.sources)
    res = scan(Path(a.manuscript).read_text(errors="replace"), files, a.n, a.min_run)
    for s in skipped:
        print("skipped: %s" % s)
    print("source | share of the manuscript's %d-grams | common runs of >= %d words (longest)" % (a.n, a.min_run))
    for r in res:
        top = r["runs"][0] if r["runs"] else None
        print("%s | %.3f | %d%s" % (r["source"], r["share"], len(r["runs"]),
                                    " (%d words, manuscript lines %s)" % (top["words"], top["manuscript_lines"]) if top else ""))
    if a.json:
        Path(a.json).write_text(json.dumps({"results": res, "skipped": skipped}, indent=1))
    return res


if __name__ == "__main__":
    main(sys.argv[1:])
