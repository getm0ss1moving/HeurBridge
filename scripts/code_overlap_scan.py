#!/usr/bin/env python3
"""Code-overlap scan: our Python against third-party Python (originality hygiene, task T7.5).

  python scripts/code_overlap_scan.py [--ours heurbridge scripts tests] [--theirs NAME=PATH ...] [--k 12] [--top 25]
                                      [--json OUT]

Tokens come from Python's tokenizer with comments and docstring-like strings removed; identifiers become ID and
literals NUM / STR, so renamed copies still match.  Fingerprints are k-token shingles.  For each of our files: the
third-party file sharing the most fingerprints, the share of our file's fingerprints found there, and the longest
common token run with its line ranges in both files.  Generic Python shares a little everywhere: report the
unrelated-file background next to any number.  Default third-party trees: DREAMPlace, ChipDiffusion, ORFS 2024-12,
OpenROAD 676f8451 (third_party/).  Flags a file at --flag-share or a run of --flag-run tokens or more.  Files
with fewer than --min-tokens tokens (an __init__.py that only imports) are listed as too small, not scored: a
single generic import line matches almost anything.
"""

from __future__ import annotations

import argparse
import io
import json
import keyword
import sys
import tokenize
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_THEIRS = (("DREAMPlace", "third_party/DREAMPlace"), ("ChipDiffusion", "third_party/chipdiffusion"),
                  ("ORFS", "third_party/ORFS-2024-12"), ("OpenROAD", "third_party/OpenROAD-676f8451"))
SKIP = {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING,
        tokenize.ENDMARKER}


def tokens(text: str) -> list:
    """[(normalized token, line)]; [] for text the tokenizer rejects."""
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return []
    out, prev = [], None
    for t in toks:
        if t.type in SKIP:
            if t.type in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT):
                prev = t.type
            continue
        if t.type == tokenize.STRING and prev in (None, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT):
            prev = t.type
            continue                                    # a docstring-like statement
        if t.type == tokenize.NAME:
            s = t.string if keyword.iskeyword(t.string) else "ID"
        elif t.type == tokenize.NUMBER:
            s = "NUM"
        elif t.type == tokenize.STRING:
            s = "STR"
        else:
            s = t.string
        out.append((s, t.start[0]))
        prev = t.type
    return out


def shingles(toks: list, k: int) -> set:
    s = [t for t, _ in toks]
    return {hash(tuple(s[i:i + k])) for i in range(len(s) - k + 1)}


def longest_run(a: list, b: list, k: int) -> tuple:
    """(length, start in a, start in b) of the longest common contiguous token run of length >= k; (0, -1, -1) if
    none.  Exact: every k-gram match is extended as far as it goes."""
    sa, sb = [t for t, _ in a], [t for t, _ in b]
    idx = defaultdict(list)
    for j in range(len(sb) - k + 1):
        idx[tuple(sb[j:j + k])].append(j)
    best = (0, -1, -1)
    for i in range(len(sa) - k + 1):
        for j in idx.get(tuple(sa[i:i + k]), ()):
            if i and j and sa[i - 1] == sb[j - 1]:
                continue                                # inside a longer run already counted from its start
            n = k
            while i + n < len(sa) and j + n < len(sb) and sa[i + n] == sb[j + n]:
                n += 1
            if n > best[0]:
                best = (n, i, j)
    return best


def py_files(root: Path) -> list:
    return sorted(p for p in Path(root).rglob("*.py") if p.is_file())


def scan(ours: list, theirs: dict, k: int = 12, min_tokens: int = 50) -> dict:
    """``ours``: [Path]; ``theirs``: {name: [Path]}.  Rows sorted by share, then run length."""
    ttok, index = {}, defaultdict(set)
    for name, files in theirs.items():
        for p in files:
            t = tokens(p.read_text(errors="replace"))
            if len(t) >= k:
                ttok[p] = (name, t)
                for h in shingles(t, k):
                    index[h].add(p)
    rows, small = [], []
    for p in ours:
        t = tokens(p.read_text(errors="replace"))
        if len(t) < max(k, min_tokens):
            small.append(str(p))
            continue
        sh = shingles(t, k)
        hit = defaultdict(int)
        for h in sh:
            for q in index.get(h, ()):
                hit[q] += 1
        if not hit:
            rows.append({"file": str(p), "share": 0.0, "run": 0, "match": None})
            continue
        q, n = max(hit.items(), key=lambda kv: (kv[1], str(kv[0])))
        L, i, j = longest_run(t, ttok[q][1], k)
        tq = ttok[q][1]
        rows.append({"file": str(p), "share": n / len(sh), "run": L, "match": str(q), "match_tree": ttok[q][0],
                     "ours_lines": [t[i][1], t[i + L - 1][1]] if L else None,
                     "theirs_lines": [tq[j][1], tq[j + L - 1][1]] if L else None})
    rows.sort(key=lambda r: (-r["share"], -r["run"], r["file"]))
    shares = [r["share"] for r in rows]
    return {"k": k, "ours_files": len(ours), "scanned": len(rows), "too_small": small, "min_tokens": min_tokens,
            "theirs_files": len(ttok), "rows": rows,
            "mean_share": float(np.mean(shares)) if shares else 0.0,
            "share_ge_005": sum(s >= 0.05 for s in shares), "share_ge_010": sum(s >= 0.10 for s in shares),
            "longest_run": max((r["run"] for r in rows), default=0)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ours", nargs="+", default=["heurbridge", "scripts", "tests"])
    ap.add_argument("--theirs", nargs="*", default=None, help="NAME=PATH (default: the third_party trees)")
    ap.add_argument("--k", type=int, default=12)
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--flag-share", type=float, default=0.10)
    ap.add_argument("--flag-run", type=int, default=60)
    ap.add_argument("--min-tokens", type=int, default=50)
    ap.add_argument("--json", default="")
    a = ap.parse_args(argv)
    ours = [p for d in a.ours for p in (py_files(ROOT / d) if (ROOT / d).is_dir() else [ROOT / d])]
    pairs = [x.split("=", 1) for x in a.theirs] if a.theirs is not None else DEFAULT_THEIRS
    theirs = {}
    for name, path in pairs:
        root = Path(path) if Path(path).is_absolute() else ROOT / path
        if not root.exists():
            print("third-party tree %s not present: %s (not scanned)" % (name, root))
            continue
        theirs[name] = py_files(root)
    res = scan(ours, theirs, a.k, a.min_tokens)
    rel = lambda s: str(Path(s).relative_to(ROOT)) if s and Path(s).is_relative_to(ROOT) else s
    print("ours %d files (%d scanned, %d too small: < %d tokens), third-party %d files, k = %d tokens"
          % (res["ours_files"], res["scanned"], len(res["too_small"]), a.min_tokens, res["theirs_files"], a.k))
    print("mean share %.3f; files at >= 0.05: %d; at >= 0.10: %d; longest common run %d tokens"
          % (res["mean_share"], res["share_ge_005"], res["share_ge_010"], res["longest_run"]))
    print("our file | share | longest run (tokens) | our lines | their file | their lines")
    for r in res["rows"][:a.top]:
        print("%s | %.3f | %d | %s | %s | %s" % (rel(r["file"]), r["share"], r["run"], r.get("ours_lines"),
                                                 rel(r["match"]), r.get("theirs_lines")))
    flagged = [r for r in res["rows"] if r["share"] >= a.flag_share or r["run"] >= a.flag_run]
    print("flagged (share >= %.2f or run >= %d tokens): %d of %d" % (a.flag_share, a.flag_run, len(flagged),
                                                                     res["scanned"]))
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    main(sys.argv[1:])
