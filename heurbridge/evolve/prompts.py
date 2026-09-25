"""Prompts and strict response parsing for LLM program evolution (task T5.1).

A program's editable region is delimited by ``# EVOLVE-BLOCK-START`` / ``# EVOLVE-BLOCK-END``
(AlphaEvolve convention); everything outside it (shared helpers, the contract) is kept from the parent.
The model must return a short strategy E (<= 150 words) and then exactly one ```python block holding
the full new EVOLVE block.  Parsing is strict; the caller gets one retry, then the candidate is
discarded and logged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
START, END = "# EVOLVE-BLOCK-START", "# EVOLVE-BLOCK-END"

CONTRACT = """Program contract (checked automatically; violations are rejected):
- define `def heuristic(design, upstream, rng)` returning `pos` (N x 2 float, normalized core coordinates)
  or `(pos, orient)` with orient (N,) ints 0..7 (R0,R90,R180,R270,MX,MY,MX90,MY90)
- only change movable macros (`design.macro_idx`); every other row must equal `design.init_pos`
- imports only from numpy, scipy, networkx, math, heapq, itertools, collections; no files, network,
  subprocess, os/sys, threads, eval/exec, getattr, dunder attributes
- deterministic given `rng` (the only randomness); iterate in `design.macro_order` /
  `design.canonical_order`; relabelling objects must relabel the output (permutation equivariance)
- CPU time limit 60 s, memory 4 GB"""

DESIGN_API = """DesignView (read-only numpy; coordinates normalized to the core box [0,1]^2):
  n, size (N,2), is_macro, is_fixed, is_io, movable, init_pos (N,2; NaN for unplaced cells), orient (N,)
  pin_obj, pin_off (P,2), net_ptr, pin_idx, net_weight, net_pins(k), n_nets
  macro_order (M,) movable macros in canonical order -- all macro_* arrays follow this order
  macro_size (M,2) effective sizes, macro_group (M,) interchangeable groups, macro_aff (M,M) affinity
  io_pull (M,2) mean position of connected fixed objects, io_w (M,) its weight
  obstacles (F,4) fixed-macro rectangles, cluster (N,) cell cluster ids, cluster_area
  misc: {"row_h", "site_w", "halo", "aspect", "design_id"}"""

INVARIANTS = """EDA invariants: macros must lie inside the core, must not overlap each other or fixed obstacles
(minimum spacing = halo), fixed objects never move, orientation is chosen by your program (the bridge
never changes it)."""

SYSTEM = """You design macro-placement heuristics for chip layout. Your program's output is refined by a
learned bridge and a certified legalizer, and it is scored on the final layout.

{contract}

{api}

{invariants}

Skill document:
{skill}"""

USER = """Parent program (edit only the EVOLVE block):
```python
{parent}
```

Evidence from the evaluation of the parent (what the bridge could not fix):
{evidence}

Task: first write a strategy E of at most 150 words that names the structural error you will fix and
how. Then return the complete new EVOLVE block (from `{start}` to `{end}` inclusive) in exactly one
```python code block. Keep the function name `heuristic` and the contract."""


def load_skill(version: str = "v0") -> str:
    return (HERE / "prompts" / ("skill_%s.md" % version)).read_text()


def system_prompt(skill: str) -> str:
    return SYSTEM.format(contract=CONTRACT, api=DESIGN_API, invariants=INVARIANTS, skill=skill)


def user_prompt(parent_block: str, evidence: str) -> str:
    return USER.format(parent=parent_block, evidence=evidence, start=START, end=END)


def split_program(src: str) -> tuple[str, str, str]:
    """(prefix, evolve block incl. markers, suffix).  A program without markers is one evolve block."""
    i, j = src.find(START), src.find(END)
    if i < 0 or j < 0 or j < i:
        return "", START + "\n" + src.rstrip() + "\n" + END + "\n", ""
    j += len(END)
    return src[:i], src[i:j] + "\n", src[j:].lstrip("\n")


def with_markers(src: str, body_start_token: str = "def heuristic") -> str:
    """Wrap everything from the heuristic definition on (and PARAMS) in EVOLVE markers."""
    k = src.find("PARAMS =")
    k = k if k >= 0 else src.find(body_start_token)
    return src[:k] + START + "\n" + src[k:].rstrip() + "\n" + END + "\n"


@dataclass
class Parsed:
    ok: bool
    strategy: str = ""
    block: str = ""
    error: str = ""


def parse_response(text: str) -> Parsed:
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, re.S)
    if len(blocks) != 1:
        return Parsed(False, error="expected exactly one python block, got %d" % len(blocks))
    block = blocks[0]
    if START not in block or END not in block:
        return Parsed(False, error="EVOLVE markers missing")
    i, j = block.find(START), block.find(END) + len(END)
    block = block[i:j] + "\n"
    if "def heuristic" not in block:
        return Parsed(False, error="no heuristic() in the block")
    strategy = text.split("```")[0].strip()
    words = len(strategy.split())
    if words == 0:
        return Parsed(False, error="missing strategy")
    if words > 180:                                        # 150 requested; small tolerance
        return Parsed(False, error="strategy too long (%d words)" % words)
    return Parsed(True, strategy=strategy, block=block)


def assemble(parent_src: str, new_block: str) -> str:
    pre, _, post = split_program(parent_src)
    return pre + new_block + ("\n" + post if post else "")
