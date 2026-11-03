# HeurBridge-PR

**Prompt-evolved placement heuristics, refined by a flow-matching "heuristic → elite" bridge.**

LLM-written heuristics are cheap to generate and expensive to evaluate. HeurBridge co-evolves them with a
learned *bridge* that transports a heuristic's macro layout toward the design's best known layouts, and then
scores the heuristic by **how refinable its output is** rather than by its raw cost — replacing the expensive
outer-loop evaluation with a cheap, learned inner signal.

> **Status: research prototype, stopped 2026-10-09 by the author.** The results below are pre-registered, and
> the negative ones are reported too. This repository is a public mirror: internal session logs, raw run
> artifacts, third-party checkouts and lab-cluster scripts are excluded.

---

## Headline results

Cost `J` is a weighted sum of ratios to a reference layout on Track A (wirelength 0.30, routing-congestion
overflow 0.15), measured after DREAMPlace places the standard cells around the fixed macros. The reference
layout scores `J = 0.45`; lower is better. Two designs/held-out families, **pre-registered confirmatory tests**:

| Comparison | Result | Protocol |
|---|---|---|
| ISPD2005 held-out family (7 designs, 405 cases) | `J` 0.5863 → **0.5579 (−4.8 %)**; 365 better / 40 unchanged / **0 worse** | confirmatory (gate passed) |
| same, against a *random-direction* control | random direction gives 0.5807 (−1.0 %), so the **learned direction adds −3.9 %** on its own | same |
| IBM held-out (ibm08, ibm12; 145 cases) | `J` 0.6375 → **0.6004 (−5.8 %)**; 66 better / 79 unchanged / **0 worse** | confirmatory (secondary) |
| Distance closed to the 0.45 reference | roughly **one fifth** of the gap (21 % / 20 %); no refined layout reaches 0.45 | descriptive |

**Guaranteed non-degradation.** The guard searches `α ∈ {0, 0.25, 0.5, 1}` along the learned direction and
keeps the best legal, tool-scored candidate. `α = 0` is the raw heuristic layout, so the bridge never returns
something worse than its input.

### What did not work (reported, not hidden)

| Attempt | Outcome |
|---|---|
| Bridge applied to DREAMPlace's *own* layouts | −0.0028 `J` (p = 0.040, ≈ −0.6 %) — **no better than simply running the tool twice** and keeping the better result (+0.0011, p = 0.609) at similar compute |
| Handing the bridge's standard-cell sketch to DREAMPlace as a start | **No effect**: 0.4828 vs 0.4822, 28 better / 36 worse (p = 0.972) |
| Re-targeting the training pairs at tool-level layouts (the planned fix) | Never run — the project was stopped first |

### Why it could not do more

- **Weak targets.** Only **38 %** of the 1,608 training pairs point at a layout at or below the tool's cost, so
  even a perfect bridge would stay above the tool.
- **Continuous, local moves only.** It never changes orientation, reorders groups or swaps distant macros.
- **Narrow data.** 1,608 pairs from a single design family (13 IBM designs); later rounds added none.
- **Never used in the real flow.** No bridge exists for Track B (the OpenROAD flow to signoff); all Track B
  results come from heuristic programs plus a flow-scored local search.

---

## How it works

1. **Heuristics are evolved as programs.** An LLM writes placement heuristics as code; a population is
   maintained with an evaluation-budget ledger (see `heurbridge/evolve/`).
2. **The bridge is trained** on pairs *(heuristic layout, nearest of the design's top-5 elites)* — 1,608 pairs
   from 13 IBM designs, pretrained for 200k steps on synthetic circuits.
3. **A heuristic is scored by refinability.** For each candidate layout `x^h`, the bridge integrates 20 Euler
   steps to `T(x^h)`; a guard tries `x^h + α(T(x^h) − x^h)` for four values of `α`, legalizes each, scores it
   with DREAMPlace `f1`, and keeps the best. Fitness = the score of what the bridge can make of the layout.

**Model.** ~1.1 M parameters: encoder MLP → `[GATv2 (4 heads), MLP, global self-attention] × L` → decoder,
predicting a velocity per node. Nodes are movable macros, fixed macros, IOs and standard-cell clusters;
orientation is an input feature and is never changed. Training uses a corrected stochastic-interpolant
flow-matching loss.

---

## Repository layout

| Path | Contents |
|---|---|
| `heurbridge/core/` | `Design`/`Layout` data model, bookshelf + LEF/DEF loaders/writers, orientation algebra, interface contract, synthetic designs |
| `heurbridge/eval/` | `f0` metrics (batched, differentiable), `f1`/`f2`/`f3` evaluators, final cost `J` and gates |
| `heurbridge/heuristics/` | macro / cell / route seed heuristics |
| `heurbridge/bridge/` | bridge data, model, training, guarded inference |
| `heurbridge/evolve/` | sandbox, LLM client + budget ledger, fitness, population, RLCE |
| `heurbridge/archive/` | elite archive (SQLite + npz) |
| `heurbridge/stats/` | paired tests, Holm correction, bootstrap, alpha-spending ledger |
| `configs/` | frozen cost weights, design families, run configs |
| `scripts/` | experiment entry points, audit and overlap scans |
| `tests/` | pytest suite |
| `reports/` | **curated** evidence reports — every headline number above cites one of them |
| `stats/alpha_ledger.jsonl` | the sequential alpha-budget ledger used by the pre-registered tests |

---

## Getting started

```bash
uv venv --python 3.11 .venv
VIRTUAL_ENV=.venv uv pip install numpy scipy scikit-learn pandas pyyaml networkx matplotlib hypothesis pytest torch torch_geometric
.venv/bin/python -m pytest -q tests
```

The bridge and the evaluators need the external HA-PR EDA harness (not vendored here) and a DREAMPlace
build for the cell-level evaluator. Point `HB_EDA_DIR` at the harness checkout:

```bash
export HB_EDA_DIR=/path/to/eda
```

## Evaluation protocol

- **Pre-registration.** Test protocols are written and committed *before* the runs
  (`reports/E0_preregistration.md`, `reports/trackB_preregistration.md`). Confirmatory and exploratory results
  are labelled separately and never mixed.
- **Paired tests.** Paired one-sided Wilcoxon with Holm correction across families; a sequential
  alpha-spending ledger (`stats/alpha_ledger.jsonl`) keeps the family-wise error budget honest.
- **Effect vs. control.** Every learned-direction claim is compared against the same guard moving in a
  **random direction** at equal budget, so the gain cannot be attributed to the guard alone.
- **No dropped failures.** Failures are counted as `+inf`, never discarded.

## What is not in this repository

Third-party code (`third_party/`: DREAMPlace, OpenROAD, ORFS, ...), benchmark data, run artifacts
(`runs/`, `checkpoints/`, `logs/`), internal session logs, and the manuscripts/plans for unpublished work.
Those are referenced by path in the reports but are not redistributed.

## Citation

If you use this code, please cite the repository:

```bibtex
@misc{heurbridge2026,
  title  = {HeurBridge-PR: prompt-evolved placement heuristics refined by a flow-matching heuristic-to-elite bridge},
  author = {Duan, Zeyu},
  year   = {2026},
  note   = {https://github.com/getm0ss1moving/HeurBridge}
}
```

## License

MIT — see [LICENSE](LICENSE). Third-party components keep their own licenses (DREAMPlace and OpenROAD are
BSD-3-Clause and are not redistributed here).

## Acknowledgements

Built on the HA-PR EDA harness; evaluation relies on DREAMPlace and OpenROAD/ORFS, with signoff metrics
produced by OpenSTA. Thanks to the maintainers of those open-source projects.
