"""Originality hygiene (task T7.5): similarity of evolved programs to public placer/router code.

Two measures, both reported; a program is labelled "rediscovery" when either exceeds 0.8 against any
reference file:
  ast      (Python references) containment of the program's AST node-type 5-grams (identifiers and
           literals abstracted away) in the reference file's AST 5-grams
  tokens   (any language: DREAMPlace, ChipDiffusion, RePlAce/gpl, mpl2, FastRoute, CUGR2) containment of
           winnowed fingerprints of normalized token 8-grams (identifiers -> ID, numbers -> NUM,
           strings -> STR, comments removed)
Containment = |F(program) & F(reference)| / |F(program)|: how much of the program appears in the reference.
"""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

KEYWORDS = set("""and as assert break class continue def del elif else except False finally for from global if import
in is lambda None nonlocal not or pass raise return True try while with yield auto bool case catch char const
double enum extern float goto inline int long namespace new private protected public return short signed sizeof
static struct switch template this throw typedef typename union unsigned using virtual void volatile proc set
foreach puts expr""".split())
_TOKEN = re.compile(r"[A-Za-z_]\w*|\d+\.?\d*(?:[eE][-+]?\d+)?|==|!=|<=|>=|->|::|\*\*|//|[^\s\w]")


def _strip_comments(text: str, lang: str) -> str:
    if lang == "py":
        text = re.sub(r"#.*", "", text)
        text = re.sub(r'("""|\'\'\')(?:.|\n)*?\1', "STR", text)
    else:
        text = re.sub(r"//.*|/\*(?:.|\n)*?\*/", "", text)
        text = re.sub(r"#(?!include|define).*", "", text) if lang == "tcl" else text
    return re.sub(r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'", "STR", text)


def normalized_tokens(text: str, lang: str = "py") -> list:
    out = []
    for t in _TOKEN.findall(_strip_comments(text, lang)):
        if t == "STR" or t in KEYWORDS:
            out.append(t)
        elif re.match(r"^\d", t):
            out.append("NUM")
        elif re.match(r"^[A-Za-z_]", t):
            out.append("ID")
        else:
            out.append(t)
    return out


def winnow(tokens: list, k: int = 8, w: int = 4) -> set:
    hs = [int(hashlib.blake2b(" ".join(tokens[i:i + k]).encode(), digest_size=8).hexdigest(), 16)
          for i in range(max(0, len(tokens) - k + 1))]
    if len(hs) <= w:
        return set(hs)
    return {min(hs[i:i + w]) for i in range(len(hs) - w + 1)}


def ast_ngrams(src: str, n: int = 5) -> set:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()
    seq = [type(node).__name__ for node in ast.walk(tree)]
    return {tuple(seq[i:i + n]) for i in range(max(0, len(seq) - n + 1))}


def containment(a: set, b: set) -> float:
    return len(a & b) / len(a) if a else 0.0


def lang_of(path: Path) -> str:
    return {".py": "py", ".tcl": "tcl"}.get(path.suffix, "c")


def build_corpus(roots: dict, exts=(".py", ".cpp", ".cc", ".h", ".hpp", ".cu", ".tcl"), max_files: int = 20000) -> dict:
    """{name: [(path, token fingerprints, ast n-grams or None)]} for each reference code base."""
    corpus = {}
    for name, root in roots.items():
        items = []
        for p in sorted(Path(root).rglob("*")):
            if p.suffix in exts and p.is_file() and len(items) < max_files:
                try:
                    text = p.read_text(errors="replace")
                except OSError:
                    continue
                lang = lang_of(p)
                items.append((str(p), winnow(normalized_tokens(text, lang)), ast_ngrams(text) if lang == "py" else None))
        corpus[name] = items
    return corpus


def rediscovery_report(program_src: str, corpus: dict, threshold: float = 0.8) -> dict:
    fp = winnow(normalized_tokens(program_src, "py"))
    ag = ast_ngrams(program_src)
    out = {"threshold": threshold, "references": {}, "rediscovery": False}
    for name, items in corpus.items():
        best = {"tokens": 0.0, "ast": 0.0, "file": None}
        for path, rfp, rag in items:
            t = containment(fp, rfp)
            a = containment(ag, rag) if rag is not None else 0.0
            if max(t, a) > max(best["tokens"], best["ast"]):
                best = {"tokens": t, "ast": a, "file": path}
        out["references"][name] = best
        if max(best["tokens"], best["ast"]) > threshold:
            out["rediscovery"] = True
    return out
