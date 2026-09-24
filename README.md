# HeurBridge-PR

Implementation of HeurBridge-PR: LLM-written placement/routing heuristics co-evolved with a learned
**heuristic-to-elite bridge** (flow matching whose source is a heuristic's output), scored by what the
bridge makes of them ("refinability fitness"), on real netlists with signoff-verified elites.

This repository follows the implementation task list `HEURBRIDGE_TASKS.md` (v1.0, 2026-09-24; kept local
until publication is approved) and builds on the HA-PR EDA harness (`eda/`, imported, never copied).

## Layout

| Path | Content | Task |
|---|---|---|
| `heurbridge/core/` | `Design`/`Layout` data model, bookshelf + LEF/DEF loaders/writers, orientation algebra, interface contract, synthetic designs | T1.1, T1.2 |
| `heurbridge/eval/` | f0 metrics (PyTorch, batched, differentiable), f1/f2/f3 evaluators, final cost `J` and gates | T1.3–T1.6 |
| `heurbridge/heuristics/` | macro / cell / route seed heuristics | T2.2–T2.4 |
| `heurbridge/bridge/` | bridge data, model, training, guarded inference | T3 |
| `heurbridge/evolve/` | sandbox, LLM client + budget ledger, fitness, population, RLCE | T0.6, T2.1, T5 |
| `heurbridge/archive/` | elite archive (SQLite + npz) | T2.6 |
| `heurbridge/stats/` | paired tests, Holm, bootstrap, alpha-spending ledger | T7.2, T7.3 |
| `configs/` | frozen cost weights, design families, run configs | — |
| `scripts/` | server access (key-only SSH), sync, probes | T0 |
| `tests/` | pytest suite (`.venv/bin/python -m pytest -q tests`) | every task |
| `reports/` | experiment reports | T7.4 |
| `HANDOFF.md`, `CHANGELOG.md`, `ENV_REPORT.md` | session log, versioned change record, environment report | every task |

On the servers the repository lives at `/data/dzy/heura_repr/heurbridge`, next to the HA-PR harness
`/data/dzy/heura_repr/eda`; paths in the task list (`heurbridge/configs/...`) are relative to this root.

## Setup

```bash
uv venv --python 3.11 .venv
VIRTUAL_ENV=.venv uv pip install numpy scipy scikit-learn pandas pyyaml networkx matplotlib hypothesis pytest torch torch_geometric
.venv/bin/python -m pytest -q tests
```

The HA-PR harness is found through `HB_EDA_DIR` (or `HEURA_EDA_BASE`), else `../eda`,
`/data/dzy/heura_repr/eda`, `~/Desktop/heura_repro_en/eda`.

## Conventions

- Positions are object centres normalized to the core box; pin offsets are measured from the object
  centre in the master frame and rotated per OpenDB orientation semantics.
- Metrics follow `eda/docs/METRIC_CONVENTIONS.md`; timing always goes through
  `metrics_schema.canonicalize_record`. Missing fields are *unchecked*, never passed.
- No credentials in the repository: SSH is key-only (`scripts/ssh_run.sh`), API keys come from the environment.
