"""T5 engine with a mock LLM: proposals parsed, certified, evaluated, logged; malformed and unsafe children rejected."""

import json
from dataclasses import dataclass

import numpy as np

from heurbridge.core import synth
from heurbridge.evolve import engine as EN, prompts as PR, sandbox as SB
from heurbridge.evolve.population import Population
from heurbridge.heuristics.macro.registry import all_programs


@dataclass
class Rep:
    text: str


class MockLLM:
    """Returns: a valid tweak of the parent, a malformed reply, or an unsafe program (cycling)."""

    def __init__(self):
        self.n = 0
        self.parent_block = None

    def chat(self, messages, **kw):
        self.n += 1
        user = messages[-1]["content"]
        blk = user[user.find(PR.START): user.find(PR.END) + len(PR.END)] if PR.START in user else None
        mode = self.n % 3
        if mode == 1 and blk:
            return Rep("Strategy: shift the boundary weight.\n```python\n%s\n```" % blk.replace('"beta": 0.5', '"beta": 0.8'))
        if mode == 2:
            return Rep("I think the heuristic is fine.")
        return Rep("Strategy: read a file.\n```python\n%s\nimport os\ndef heuristic(d, u, r):\n    return d.init_pos\n%s\n```"
                   % (PR.START, PR.END))


def test_engine_generation(tmp_path):
    des, ref = synth.make_design(seed=80, n_macros=6, n_cells=40, n_io=6)
    scope = des.is_macro & ~des.is_fixed
    rng = np.random.default_rng(0)

    def evaluate(src):
        return {"B": list(rng.uniform(0.5, 1.5, 3)), "A": list(rng.uniform(0.5, 1.5, 3)), "runtime_s": 0.5}

    def certify(src):
        return SB.certify(src, des, ref, scope, check_mr1=False)

    cfg = EN.EngineConfig(parents=2, children=3, budget_scope="M/test")
    prop = EN.HeurBridgeProposer(MockLLM(), cfg, log=lambda s: None)
    pop = Population(n_islands=2, q=3)
    eng = EN.Engine(prop, pop, evaluate, certify, cfg, tmp_path, log=lambda s: None)
    eng.seed([p for p in all_programs() if p["id"] in ("M6.v0", "M6.v1")])
    n = eng.generation(1)
    events = [json.loads(l) for l in (tmp_path / "events.jsonl").read_text().splitlines()]
    kinds = [e["kind"] for e in events]
    assert "child" in kinds and "generation" in kinds
    assert "discarded_malformed" in kinds or "rejected_sandbox" in kinds
    rej = [e for e in events if e["kind"] == "rejected_sandbox"]
    assert all(any("import os" in r for r in e["reasons"]) for e in rej)
    assert n >= 1 and len(pop.all) >= 3
