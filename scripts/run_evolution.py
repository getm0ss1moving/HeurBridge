#!/usr/bin/env python3
"""T5 macro-stage evolution campaign (tasks T5.1-T5.5): one proposer x one fitness on D_evo.

  python scripts/run_evolution.py --proposer heurbridge --fitness refinability --suite ibm \
      --evo ibm01,ibm02 --seeds 3 --bridge checkpoints/<promoted>.pt --guard f1 --archive <A0> \
      --generations 10 --parents 8 --children 4 --llm deepseek --budget 2000 --split S1 --out runs/evo/hb_S1

Per child: strict parse (one retry) -> V0 certificate (AST, run, output contract, determinism, MR1 on a
probe design) -> evaluation on D_evo: program x seeds -> x^h -> bridge + guard (T3.8) -> B (post-bridge
cost, mean over seeds per design; a failure is +inf) and A (the raw alpha=0 cost) -> refinability fitness
(or raw fitness for the FunSearch / HeurAgenix baselines and ablation A1) -> MAP-Elites population.
Context for the proposers: RLCE evidence packs (heurbridge; T5.4) and critical-operation analysis
(heuragenix).  Every event is in <out>/events.jsonl; the LLM budget ledger is logs/llm_ledger.jsonl.

--llm mock is a deterministic offline stand-in (rescales numeric constants of the parent's EVOLVE block)
for dry runs of the whole loop before any LLM budget is spent.  It never produces results: runs with it
are labelled dry_run in meta.json and summary.json.
Not done here (server campaign): promotion of the top 20% per generation to f2 (T5.2 step 5) and fitness
re-anchoring after a bridge promotion (population.reanchor), which need the f2 evaluator and Algorithm R.
"""

import argparse
import hashlib
import json
import math
import re
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heurbridge.archive.store import Archive  # noqa: E402
from heurbridge.bridge.data import match_symmetric  # noqa: E402
from heurbridge.bridge.graph import KIND_MOV  # noqa: E402
from heurbridge.bridge.sample import refine, source_nodes  # noqa: E402
from heurbridge.bridge.train import load_bridge  # noqa: E402
from heurbridge.core import project, synth  # noqa: E402
from heurbridge.evolve import prompts as PR, rlce, sandbox as SB  # noqa: E402
from heurbridge.evolve.engine import PROPOSERS, Engine, EngineConfig  # noqa: E402
from heurbridge.evolve.llm import LLMClient, Reply  # noqa: E402
from heurbridge.evolve.population import Population  # noqa: E402
from heurbridge.heuristics.macro.registry import all_programs  # noqa: E402
from heurbridge.meta import write_meta  # noqa: E402
from heurbridge.paths import logs_dir  # noqa: E402
from train_bridge import load_bundle  # noqa: E402

NUM = re.compile(r"(?<![\w.])(\d+\.\d+)(?![\w.])")


class MockLLM:
    """Offline stand-in for dry runs; same interface as LLMClient.chat.  Takes the first python block of the
    latest user message that has one and rescales its decimal constants by a factor in [0.7, 1.3] drawn
    from the prompt hash (deterministic)."""

    def __init__(self, ledger_path: Path):
        self.ledger = ledger_path
        self.ledger.parent.mkdir(parents=True, exist_ok=True)

    def chat(self, messages, model="mock", max_tokens=0, purpose="", program_id="", budget_scope=None, **_):
        user = [m["content"] for m in messages if m["role"] == "user"]
        block = None
        for u in reversed(user):
            b = re.findall(r"```(?:python|py)?\s*\n(.*?)```", u, re.S)
            if b:
                block = b[0]
                break
        seed = int(hashlib.sha256("\n".join(user).encode()).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        if block is None:
            text = "No program found in the prompt."
        else:
            if PR.START not in block:
                block = PR.START + "\n" + block.rstrip() + "\n" + PR.END + "\n"
            new = NUM.sub(lambda m: "%.6g" % (float(m.group(1)) * rng.uniform(0.7, 1.3)), block)
            text = "Dry-run strategy: rescale the numeric parameters of the parent by factors in [0.7, 1.3].\n" \
                   "```python\n%s```" % new
        with open(self.ledger, "a") as fh:
            fh.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": "mock", "purpose": purpose,
                                 "program_id": program_id, "budget_scope": budget_scope, "status": "mock"}) + "\n")
        return Reply(text=text, reasoning="", model="mock", tokens_in=sum(len(u) for u in user) // 4,
                     tokens_out=len(text) // 4, reasoning_tokens=0, latency_s=0.0)


def guard_fn(b, kind):
    """The guard's cost function for a bundle: f0 = the macro-stage surrogate; f1 = HB-GP J (Track-A dev)."""
    if kind == "f0":
        return b.scorer
    from heurbridge.eval import cost
    from heurbridge.pipeline.evaluators import HBGPEvaluator
    ev = HBGPEvaluator(cluster_of=b.cluster_of)
    bench = project.legalize_macros(b.design, b.base)[0]
    base = cost.Baseline.from_records(b.design.id, [ev.evaluate(b.design, bench, "evo.base", None)])
    return lambda lay: ev.score(ev.evaluate(b.design, lay, "evo.guard", None), base).J_inf


class EvoEvaluator:
    def __init__(self, bundles, guards, model, seeds, K, cpu_s):
        self.bundles, self.guards, self.model = bundles, guards, model
        self.seeds, self.K, self.cpu_s = seeds, K, cpu_s

    def run(self, src, b, s):
        """x^h of a program on one design and seed (None on any failure, reason in the second value)."""
        r = SB.run_program(src, b.view, None, s, cpu_s=self.cpu_s)
        if r.status != "ok":
            return None, "run_%s" % r.status, 0.0
        bad = SB.validate_output(b.design, b.base, r, b.design.is_macro & ~b.design.is_fixed)
        if bad:
            return None, "contract: %s" % bad[:2], r.cpu_s
        return SB.to_layout(b.design, b.base, r), None, r.cpu_s

    def __call__(self, src):
        B, A, rts, fails = [], [], [], []
        for b, g in zip(self.bundles, self.guards):
            Bd, Ad = [], []
            for s in range(self.seeds):
                lay, why, cpu = self.run(src, b, s)
                rts.append(cpu)
                if lay is None:
                    Bd.append(math.inf)
                    Ad.append(math.inf)
                    fails.append("%s.s%d: %s" % (b.design.id, s, why))
                    continue
                res = refine(self.model, b.graph, b.design, [lay], g, K=self.K)[0] if self.model else None
                if res is None:                              # raw fitness without a bridge (ablation A1 setting)
                    lp, rep = project.legalize_macros(b.design, lay)
                    c = g(lp) if rep.ok else math.inf
                    Bd.append(c)
                    Ad.append(c)
                else:
                    Bd.append(min(res.scores))
                    Ad.append(res.scores[0])
            B.append(float(np.mean(Bd)))                     # any +inf seed makes the design +inf
            A.append(float(np.mean(Ad)))
        return {"B": B, "A": A, "runtime_s": float(np.mean(rts)) if rts else 0.0, "decision": "none", "failures": fails}


def matched(graph, lay, el):
    """The elite with its interchangeable macros permuted (Hungarian, T3.2) to best match x^h, as a Layout."""
    _, perm = match_symmetric(graph, source_nodes(graph, lay), source_nodes(graph, el))
    out = el.copy()
    k = np.flatnonzero(graph.obj >= 0)
    out.pos[graph.obj[k]] = el.pos[graph.obj[perm[k]]]
    out.orient[graph.obj[k]] = el.orient[graph.obj[perm[k]]]
    return out


def elite_for(arch, b, lay):
    """Nearest archive elite for x^h (area-weighted distance after symmetric matching); None without elites."""
    top = arch.topk(b.design.id, "M") if arch else []
    best, bd = None, math.inf
    mm = b.design.is_macro & ~b.design.is_fixed
    for e in top:
        m = matched(b.graph, lay, arch.layout(e))
        d = float(np.sum((m.pos[mm] - lay.pos[mm]) ** 2 * b.design.area[mm, None]))
        if d < bd:
            best, bd = m, d
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proposer", default="heurbridge", choices=sorted(PROPOSERS))
    ap.add_argument("--fitness", default="refinability", choices=["refinability", "raw"])
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--evo", required=True, help="D_evo designs (comma separated)")
    ap.add_argument("--runs", default=str(ROOT / "runs" / "seed_dev"))
    ap.add_argument("--archive", default=str(ROOT / "archive_dev_v2"))
    ap.add_argument("--bridge", default="")
    ap.add_argument("--guard", default="f1", choices=["f0", "f1"])
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--programs", default="", help="seed programs (default: the whole T2.2 population)")
    ap.add_argument("--generations", type=int, default=10)
    ap.add_argument("--parents", type=int, default=8)
    ap.add_argument("--children", type=int, default=4)
    ap.add_argument("--islands", type=int, default=4)
    ap.add_argument("--llm", default="deepseek", choices=["deepseek", "mock"])
    ap.add_argument("--model", default="deepseek-reasoner")
    ap.add_argument("--budget", type=int, default=2000, help="LLM calls per stage per family split (B.3)")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--K", type=int, default=20)
    ap.add_argument("--cpu-s", type=float, default=60.0)
    ap.add_argument("--rlce-design", type=int, default=0, help="index in --evo of the design used for RLCE evidence")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dry = a.llm == "mock"
    bundles = [load_bundle(a.suite, n, a.runs) for n in a.evo.split(",")]
    guards = [guard_fn(b, a.guard) for b in bundles]
    model = load_bridge(a.bridge) if a.bridge and a.fitness == "refinability" else None
    if a.fitness == "refinability" and model is None:
        sys.exit("refinability fitness needs --bridge")
    arch = Archive(a.archive, min_fidelity=1) if a.archive and Path(a.archive).exists() else None
    evaluate = EvoEvaluator(bundles, guards, model, a.seeds, a.K, a.cpu_s)
    b0 = bundles[0]
    probe = synth.make_design(seed=0, n_macros=8, n_cells=60, n_io=8)

    def certify(src):
        return SB.certify(src, b0.design, b0.base, b0.design.is_macro & ~b0.design.is_fixed, seeds=(0,), probe=probe,
                          cpu_s=a.cpu_s, cluster=b0.cluster_of)

    br = bundles[a.rlce_design]
    rho = None
    gen = [0]

    def context(parents):
        nonlocal rho
        gen[0] += 1
        ctx = {}
        if a.proposer == "heurbridge" and model is not None:
            if rho is None:                           # reachability radius from the seed population's sources
                trip = []
                for q in list(pop.all.values())[:6]:
                    lay, _, _ = evaluate.run(q.source, br, 0)
                    e = elite_for(arch, br, lay) if lay is not None else None
                    if e is not None:                 # (x^h, bridge endpoint, matched elite) on movable macro nodes
                        rb = refine(model, br.graph, br.design, [lay], guards[a.rlce_design], K=a.K, alphas=(1.0,))[0]
                        mv = br.graph.kind == KIND_MOV
                        trip.append((source_nodes(br.graph, lay)[mv], rb.x_bridge[mv], source_nodes(br.graph, e)[mv]))
                site = (br.design.site[0] / br.design.core_wh[0]) if br.design.site else 0.01
                rho = rlce.calibrate_rho(trip, site) if trip else 0.05
            ev = {}
            for p in parents:
                lay, why, _ = evaluate.run(p.source, br, 0)
                e = elite_for(arch, br, lay) if lay is not None else None
                if lay is None or e is None:
                    ev[p.id] = "No diagnosis: %s." % (why or "no elite for the RLCE design")
                    continue
                dg = rlce.diagnose(br.design, br.view, br.graph, model, br.scorer, lay, e, rho, K=a.K,
                                   evaluate=guards[a.rlce_design])
                ev[p.id] = dg.evidence
            ctx["evidence"] = ev
        if a.proposer == "heuragenix":
            crit, rng = {}, np.random.default_rng(a.seed)
            for p in parents:
                lay, why, _ = evaluate.run(p.source, br, 0)
                if lay is None:
                    crit[p.id] = "the parent failed on the analysis design (%s)" % why
                    continue
                crit[p.id] = critical_operation(br, lay, guards[a.rlce_design], rng)
            ctx["critical"] = crit
        # the LLM's inputs are part of the record (the prompts are rebuilt from these + the parents' code)
        (out / ("context_g%d.json" % gen[0])).write_text(json.dumps(
            {"parents": [p.id for p in parents], "rho": rho, **{k: v for k, v in ctx.items()}}, indent=1, default=str))
        return ctx

    if not dry:
        from heurbridge.evolve.llm import load_keys
        if not load_keys():
            sys.exit("no DeepSeek key in the environment (DEEPSEEK_LAB_API_KEY); use --llm mock for a dry run")
    llm = MockLLM(out / "llm_mock_ledger.jsonl") if dry else LLMClient(
        budgets={"M/%s" % a.split: a.budget}, ledger_path=logs_dir() / "llm_ledger.jsonl")
    cfg = EngineConfig(parents=a.parents, children=a.children, generations=a.generations, model=a.model,
                       budget_scope="M/%s" % a.split, seed=a.seed)
    proposer = PROPOSERS[a.proposer](llm, cfg)
    pop = Population(n_islands=a.islands)
    eng = Engine(proposer, pop, evaluate, certify, cfg, out, fitness=a.fitness, context_fn=context)
    progs = all_programs()
    if a.programs:
        progs = [q for q in progs if q["id"] in set(a.programs.split(","))]
    t0 = time.time()
    eng.seed(progs)
    (out / "population_g0.json").write_text(pop.to_json())
    hist = []
    for g in range(1, a.generations + 1):
        n = eng.generation(g)
        best = max(pop.all.values(), key=lambda i: i.F)
        hist.append({"generation": g, "evaluated": n, "best": best.id, "best_F": best.F, "portfolio": pop.portfolio(),
                     "elapsed_s": round(time.time() - t0, 1)})
        print(json.dumps(hist[-1]), flush=True)
        (out / ("population_g%d.json" % g)).write_text(pop.to_json())
    ev_rows = [json.loads(l) for l in (out / "events.jsonl").read_text().splitlines()]
    kinds = {}
    for r in ev_rows:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    summary = {"dry_run": dry, "proposer": a.proposer, "fitness": a.fitness, "guard": a.guard, "evo": a.evo,
               "seeds": a.seeds, "history": hist, "events": kinds, "rho": rho}
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    write_meta(out, "evo_%s_%s" % (a.proposer, a.split), a.evo, config=vars(a), dry_run=dry,
               bridge_ckpt_hash=hashlib.sha256(Path(a.bridge).read_bytes()).hexdigest() if a.bridge else None,
               llm_model="mock" if dry else a.model, skill_hash=hashlib.sha256(PR.load_skill("v0").encode()).hexdigest()[:16])
    print(json.dumps({k: v for k, v in summary.items() if k != "history"}), flush=True)


def critical_operation(b, lay, guard, rng, frac=0.1, tries=3):
    """HeurAgenix Algorithm 1 (adapted): perturb ~10% of the parent's macro decisions (each moved to the best
    of a few random slots), report the single perturbation with the largest raw-cost improvement."""
    mo = b.view.macro_order
    base_p, rep = project.legalize_macros(b.design, lay)
    c0 = guard(base_p) if rep.ok else math.inf
    picks = rng.choice(len(mo), size=max(1, int(round(frac * len(mo)))), replace=False)
    best = (0.0, None)
    for k in picks:
        i = mo[k]
        for _ in range(tries):
            c = lay.copy()
            c.pos[i] = rng.uniform(0.05, 0.95, 2)
            cp, r2 = project.legalize_macros(b.design, c)
            if not r2.ok:
                continue
            gain = c0 - guard(cp)
            if gain > best[0]:
                best = (gain, (k, lay.pos[i].copy(), cp.pos[i].copy()))
    if best[1] is None:
        return "no single-macro perturbation improved the raw cost %.4f (%d macros tried)" % (c0, len(picks))
    k, f, t = best[1]
    return ("moving macro #%d (size %.3f x %.3f, group %d) from (%.3f, %.3f) to (%.3f, %.3f) lowers the raw cost "
            "from %.4f by %.4f (best of %d perturbed macros)" % (k, *b.view.macro_size[k], b.view.macro_group[k],
                                                                 f[0], f[1], t[0], t[1], c0, best[0], len(picks)))


if __name__ == "__main__":
    main()
