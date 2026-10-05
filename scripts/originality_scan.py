#!/usr/bin/env python3
"""Rediscovery check of task T7.5 over code we wrote or evolved (heurbridge/verify/originality.py).

  python scripts/originality_scan.py [TARGET ...] [--ref NAME=PATH ...] [--threshold 0.8] [--json OUT]

Each target file (a .py file, or every .py file under a directory) is compared with every reference file: the
containment of its winnowed normalized-token 8-grams (any language) and of its AST node-type 5-grams (Python
references), as heurbridge/verify/originality.py defines them.  A target above the threshold by either measure is a
"rediscovery" (HEURBRIDGE_TASKS.md T7.5).  Default targets: the macro, cell and route heuristics, the cell stage,
HB-GP, the bridge, orientation and timing weights; pass the directory of evolved programs too before any write-up.
Default references: DREAMPlace, ChipDiffusion, and OpenROAD's RePlAce (gpl), mpl2, mpl, FastRoute (grt) and dpl;
CUGR2 when present.  A reference tree that is not present is named, never skipped silently.  A target with fewer
than --min-tokens normalized tokens (an __init__.py that only imports) is too small to judge: it is listed, not
scored, because one generic import line is contained in almost any reference.  Exit status 1 if any target is a
rediscovery.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heurbridge.verify import originality as O  # noqa: E402

DEFAULT_TARGETS = ("heurbridge/heuristics", "heurbridge/cellstage", "heurbridge/eval/gp.py", "heurbridge/bridge",
                   "heurbridge/core/orient.py", "heurbridge/core/timing_weights.py")
DEFAULT_REFS = (("DREAMPlace", "third_party/DREAMPlace/dreamplace"), ("ChipDiffusion", "third_party/chipdiffusion"),
                ("RePlAce/gpl", "third_party/OpenROAD-676f8451/src/gpl"), ("mpl2", "third_party/OpenROAD-676f8451/src/mpl2"),
                ("mpl", "third_party/OpenROAD-676f8451/src/mpl"), ("FastRoute/grt", "third_party/OpenROAD-676f8451/src/grt"),
                ("dpl", "third_party/OpenROAD-676f8451/src/dpl"), ("CUGR2", "third_party/CUGR2"))


def targets_of(paths) -> list:
    out = []
    for t in paths:
        p = Path(t) if Path(t).is_absolute() else ROOT / t
        out += sorted(p.rglob("*.py")) if p.is_dir() else ([p] if p.exists() else [])
    return out


def scan(targets: list, refs: dict, threshold: float = 0.8, min_tokens: int = 100) -> dict:
    corpus = O.build_corpus({k: str(v) for k, v in refs.items()})
    rows, small = [], []
    for p in targets:
        src = p.read_text(errors="replace")
        if len(O.normalized_tokens(src, "py")) < min_tokens:
            small.append(str(p))
            continue
        r = O.rediscovery_report(src, corpus, threshold)
        tok = max(r["references"].items(), key=lambda kv: kv[1]["tokens"])
        ast_ = max(r["references"].items(), key=lambda kv: kv[1]["ast"])
        rows.append({"file": str(p), "tokens": tok[1]["tokens"], "tokens_ref": tok[0], "tokens_file": tok[1]["file"],
                     "ast": ast_[1]["ast"], "ast_ref": ast_[0], "ast_file": ast_[1]["file"],
                     "rediscovery": r["rediscovery"]})
    rows.sort(key=lambda r: -max(r["tokens"], r["ast"]))
    return {"threshold": threshold, "corpus": {k: len(v) for k, v in corpus.items()}, "rows": rows,
            "too_small": small, "min_tokens": min_tokens, "rediscoveries": sum(r["rediscovery"] for r in rows)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="*", default=list(DEFAULT_TARGETS))
    ap.add_argument("--ref", nargs="*", default=None, help="NAME=PATH (default: the third_party trees)")
    ap.add_argument("--threshold", type=float, default=0.8)
    ap.add_argument("--min-tokens", type=int, default=100)
    ap.add_argument("--json", default="")
    a = ap.parse_args(argv)
    pairs = [x.split("=", 1) for x in a.ref] if a.ref is not None else DEFAULT_REFS
    refs, absent = {}, []
    for name, path in pairs:
        p = Path(path) if Path(path).is_absolute() else ROOT / path
        (refs.__setitem__(name, p) if p.exists() else absent.append("%s (%s)" % (name, path)))
    res = scan(targets_of(a.targets), refs, a.threshold, a.min_tokens)
    res["absent_references"] = absent
    rel = lambda s: str(Path(s).relative_to(ROOT)) if s and Path(s).is_relative_to(ROOT) else s
    print("reference files: %s" % res["corpus"])
    if absent:
        print("not present, not scanned: %s" % ", ".join(absent))
    print("file | best token containment (reference) | best AST containment (reference) | rediscovery (> %.2f)"
          % a.threshold)
    for r in res["rows"]:
        print("%s | %.3f (%s) | %.3f (%s) | %s" % (rel(r["file"]), r["tokens"], r["tokens_ref"], r["ast"], r["ast_ref"],
                                                  r["rediscovery"]))
    if res["too_small"]:
        print("too small to judge (< %d tokens): %s" % (a.min_tokens, ", ".join(rel(x) for x in res["too_small"])))
    print("targets: %d, rediscoveries: %d" % (len(res["rows"]), res["rediscoveries"]))
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1))
    return 1 if res["rediscoveries"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
