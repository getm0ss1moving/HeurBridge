"""LLM evolution engine and baseline proposers (tasks T5.1-T5.5).

One engine, pluggable ``propose`` (how children are written) and ``fitness`` (how they are scored):

  proposer     prompt content                                                   paper
  heurbridge   parent + RLCE evidence (what the bridge cannot fix) + skill doc   this work
  eoh          5 operators: E1 new idea, E2 shared idea of parents, M1 modify, M2 parameters, M3 simplify
  reevo        short-term reflection (better vs worse parent) + long-term reflection memory
  funsearch    best-shot: two prior versions sorted by score, ask for the next version (islands)
  heuragenix   Algorithm 1: perturb ~10% of the parent's decisions, isolate the critical operation, ask
               the LLM to explain it and write the improved program (raw-cost fitness)

  fitness      refinability (post-bridge portfolio fitness, fitness.refinability_fitness) or raw
               (cost of P(x^h) without the bridge; ablation A1 / baselines)

Every child: strict parse (one retry) -> sandbox certificate (V0) -> evaluation on D_evo -> population.
Malformed responses, sandbox rejections and evaluation failures are logged by name, never silently dropped.
LLM calls go through evolve.llm.LLMClient (budget ledger with a 110% hard stop).
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import prompts as PR
from . import sandbox as SB
from .population import Individual, Population

EOH_OPS = {
    "E1": "Design a new heuristic that is substantially different from the given ones.",
    "E2": "Identify the common idea behind the given heuristics and design a new heuristic built on it.",
    "M1": "Modify the given heuristic to improve it (change its placement logic).",
    "M2": "Keep the logic of the given heuristic but change its parameters to improve it.",
    "M3": "Simplify the given heuristic: remove redundant parts that do not help the result.",
}


@dataclass
class EngineConfig:
    parents: int = 8
    children: int = 4
    generations: int = 10
    model: str = "deepseek-reasoner"
    budget_scope: str = "M/dev"
    max_tokens: int = 8192
    skill: str = "v0"
    seed: int = 0


class Proposer:
    name = "base"

    def __init__(self, llm, cfg: EngineConfig, log=print):
        self.llm, self.cfg, self.log = llm, cfg, log
        self.system = PR.system_prompt(PR.load_skill(cfg.skill))

    def ask(self, user: str, purpose: str, program_id: str) -> PR.Parsed:
        """One LLM call with one retry on malformed output."""
        msgs = [{"role": "system", "content": self.system}, {"role": "user", "content": user}]
        for attempt in (0, 1):
            rep = self.llm.chat(msgs, model=self.cfg.model, max_tokens=self.cfg.max_tokens, purpose=purpose,
                                program_id=program_id, budget_scope=self.cfg.budget_scope)
            p = PR.parse_response(rep.text)
            if p.ok:
                return p
            msgs += [{"role": "assistant", "content": rep.text},
                     {"role": "user", "content": "Your answer could not be parsed (%s). Reply again with the strategy "
                      "and exactly one ```python block containing the full EVOLVE block." % p.error}]
        return p

    def propose(self, parent: Individual, pop: Population, ctx: dict) -> tuple:
        raise NotImplementedError


class HeurBridgeProposer(Proposer):
    name = "heurbridge"

    def propose(self, parent, pop, ctx):
        evidence = ctx.get("evidence", {}).get(parent.id, "No diagnosis available for this parent.")
        pre, block, _ = PR.split_program(parent.source)
        p = self.ask(PR.user_prompt(block, evidence), "propose_rlce", parent.id)
        return (PR.assemble(parent.source, p.block), p.strategy) if p.ok else (None, p.error)


class EoHProposer(Proposer):
    name = "eoh"

    def propose(self, parent, pop, ctx):
        op = ctx["rng"].choice(sorted(EOH_OPS))
        others = [i for i in pop.all.values() if i.id != parent.id and "@i" not in i.id]
        mates = [parent] + ([others[int(ctx["rng"].integers(len(others)))]] if op in ("E1", "E2") and others else [])
        shown = "\n\n".join("Heuristic %d (idea: %s; fitness %.4f):\n```python\n%s```" % (
            k + 1, m.strategy or m.family, m.F, PR.split_program(m.source)[1]) for k, m in enumerate(mates))
        user = ("%s\n\n%s\n\nFirst describe the idea (<= 150 words), then return the full EVOLVE block of the new "
                "heuristic in one ```python block." % (EOH_OPS[op], shown))
        p = self.ask(user, "propose_eoh_" + op, parent.id)
        return (PR.assemble(parent.source, p.block), "[%s] %s" % (op, p.strategy)) if p.ok else (None, p.error)


class ReEvoProposer(Proposer):
    name = "reevo"

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.long_term = ""

    def propose(self, parent, pop, ctx):
        others = sorted([i for i in pop.all.values() if i.id != parent.id and "@i" not in i.id], key=lambda i: -i.F)
        worse = others[-1] if others else parent
        better, worse = (parent, worse) if parent.F >= worse.F else (worse, parent)
        refl_user = ("Compare the better and the worse heuristic and write a short reflection (<= 80 words) on what "
                     "makes the better one better.\nBetter (fitness %.4f):\n```python\n%s```\nWorse (fitness %.4f):\n"
                     "```python\n%s```\nReply with the reflection, then repeat the better heuristic's EVOLVE block unchanged "
                     "in one ```python block." % (better.F, PR.split_program(better.source)[1], worse.F,
                                                  PR.split_program(worse.source)[1]))
        r = self.ask(refl_user, "reevo_short_reflection", parent.id)
        short = r.strategy if r.ok else ""
        self.long_term = (self.long_term + "\n- " + short)[-1200:] if short else self.long_term
        user = ("Long-term reflections:%s\nShort-term reflection: %s\n\nUsing these reflections, improve this heuristic:\n"
                "```python\n%s```\nWrite the strategy (<= 150 words) then the full EVOLVE block in one ```python block."
                % (self.long_term or " none", short or "none", PR.split_program(parent.source)[1]))
        p = self.ask(user, "reevo_mutate", parent.id)
        return (PR.assemble(parent.source, p.block), p.strategy) if p.ok else (None, p.error)


class FunSearchProposer(Proposer):
    name = "funsearch"

    def propose(self, parent, pop, ctx):
        same = sorted([i for i in pop.all.values() if i.island == parent.island and "@i" not in i.id], key=lambda i: i.F)
        shots = (same[-2:] if len(same) >= 2 else [parent])
        body = "\n\n".join("Version %d (score %.4f):\n```python\n%s```" % (k, s.F, PR.split_program(s.source)[1])
                           for k, s in enumerate(shots))
        user = ("%s\n\nWrite version %d, improving on the previous versions. Give a one-paragraph idea, then the full "
                "EVOLVE block in one ```python block." % (body, len(shots)))
        p = self.ask(user, "funsearch_bestshot", parent.id)
        return (PR.assemble(parent.source, p.block), p.strategy) if p.ok else (None, p.error)


class HeurAgenixProposer(Proposer):
    """HeurAgenix Algorithm 1 adapted: the 'operations' are the parent's per-macro decisions; ~10% of macros
    are perturbed (moved to their best alternative among a few random slots), the perturbation with the
    largest raw-cost improvement is the critical operation, and the LLM explains it and rewrites the program."""
    name = "heuragenix"

    def propose(self, parent, pop, ctx):
        crit = ctx.get("critical", {}).get(parent.id, "no critical operation found")
        user = ("Heuristic:\n```python\n%s```\nPerturbation analysis: %s\nExplain why the better operation is better "
                "(<= 150 words), then write an improved heuristic that makes such decisions itself: the full EVOLVE "
                "block in one ```python block." % (PR.split_program(parent.source)[1], crit))
        p = self.ask(user, "heuragenix_critical_op", parent.id)
        return (PR.assemble(parent.source, p.block), p.strategy) if p.ok else (None, p.error)


PROPOSERS = {c.name: c for c in (HeurBridgeProposer, EoHProposer, ReEvoProposer, FunSearchProposer, HeurAgenixProposer)}


class Engine:
    """Generation loop.  ``evaluate(src) -> {"B": [...], "A": [...], "runtime_s": float, "decision": str}``."""

    def __init__(self, proposer: Proposer, pop: Population, evaluate, certify, cfg: EngineConfig, out_dir,
                 fitness: str = "refinability", context_fn=None, log=print):
        self.proposer, self.pop, self.evaluate, self.certify = proposer, pop, evaluate, certify
        self.cfg, self.fitness, self.log = cfg, fitness, log
        self.context_fn = context_fn or (lambda parents: {})
        self.out = Path(out_dir)
        self.out.mkdir(parents=True, exist_ok=True)
        self.events = open(self.out / "events.jsonl", "a")
        self.rng = np.random.default_rng(cfg.seed)

    def _event(self, **kw):
        kw["time"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.events.write(json.dumps(kw, default=str) + "\n")
        self.events.flush()

    def _score(self, ind: Individual):
        if self.fitness == "raw":
            ind.F = -float(np.mean(ind.A))
        else:
            self.pop.score(ind)

    def seed(self, programs: list):
        for k, p in enumerate(programs):
            src = PR.with_markers(p["source"]) if PR.START not in p["source"] else p["source"]
            ev = self.evaluate(src)
            ind = Individual(id=p["id"], source=src, sha256=hashlib.sha256(src.encode()).hexdigest(), family=p.get("family", "seed"),
                             decision=ev.get("decision", "none"), runtime_s=ev["runtime_s"], B=ev["B"], A=ev.get("A", []),
                             island=k % self.pop.n_islands, strategy=p.get("desc", ""))
            self._score(ind)
            self.pop.add(ind)
            self._event(kind="seed", id=ind.id, F=ind.F)

    def generation(self, g: int):
        parents = self.pop.select_parents(self.cfg.parents, self.rng)
        ctx = self.context_fn(parents)
        ctx["rng"] = self.rng
        n_ok = 0
        for p in parents:
            for c in range(self.cfg.children):
                cid = "g%d.%s.c%d" % (g, p.id.split("@")[0], c)
                try:
                    src, strategy = self.proposer.propose(p, self.pop, ctx)
                except Exception as e:                           # budget stop, API failure: logged, loop ends
                    self._event(kind="propose_error", id=cid, error="%s: %s" % (type(e).__name__, e))
                    if type(e).__name__ == "BudgetExceeded":
                        raise
                    continue
                if src is None:
                    self._event(kind="discarded_malformed", id=cid, error=strategy)
                    continue
                cert = self.certify(src)
                if not cert.ok:
                    self._event(kind="rejected_sandbox", id=cid, reasons=cert.reasons[:5])
                    continue
                ev = self.evaluate(src)
                ind = Individual(id=cid, source=src, sha256=cert.sha256, family=p.family, decision=ev.get("decision", "none"),
                                 runtime_s=ev["runtime_s"], B=ev["B"], A=ev.get("A", []), parent=p.id, generation=g,
                                 island=p.island, strategy=strategy)
                self._score(ind)
                added = self.pop.add(ind)
                n_ok += 1
                self._event(kind="child", id=cid, parent=p.id, F=ind.F, added=added, strategy=strategy[:300])
        self.pop.migrate(g)
        best = max(self.pop.all.values(), key=lambda i: i.F)
        self._event(kind="generation", g=g, evaluated=n_ok, best=best.id, best_F=best.F, portfolio=self.pop.portfolio())
        return n_ok
