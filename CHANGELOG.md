# Changelog

Every change to the code is recorded here with its version, task and verification.
Versions: `0.<milestone>.<patch>`; a git tag `v<version>` marks each release.
(The task list's `_harness/CHANGELOG.md` does not exist in the current checkout; this file replaces it.)

## [0.2.0] — 2026-09-25 — T2 infrastructure + statistics (local)

### Added
- `heurbridge/core/project.py` — certified macro projection P_M (T2.5): largest-first greedy grid
  legalization, exact nearest-free-slot search over a prefix-sum occupancy map, halo as whole grid cells,
  site-aligned lower-left corners, fixed-macro obstacles; `check_macros` exact checker. Test: 3 designs x
  1,000 random layouts (incl. out-of-core targets, orientations, halos) -> 100% legal.
- `heurbridge/archive/store.py` — elite archive (T2.6): SQLite (WAL) + content-addressed `.npz`; atomic
  admission (f>=2, admissible, beats k-th best, not duplicate), every rejection logged; `topk`,
  `conditional`, `snapshot`. Property test (hypothesis): best J per key never increases (Lemma 3).
- `heurbridge/evolve/sandbox.py` — program contract and sandbox (T2.1/V0): AST allow-list, separate
  interpreter with CPU/memory limits and a PEP 578 audit hook, read-only `DesignView`, output validation,
  determinism and MR1 permutation-equivariance checks, content-addressed program store.
- `heurbridge/stats/paired.py` — one-sided paired Wilcoxon with +inf failures kept, Holm, stratified
  bootstrap geometric-mean ratio with the +-0.5% effect floor, Clopper-Pearson, Page's L (T7.2).
- `heurbridge/stats/alpha_ledger.py` — alpha-spending ledger, alpha_j = alpha 2^-j per campaign (T7.3).
- Tests: 53 passing.

## [0.1.0] — 2026-09-25 — T1 foundations (local)

### Added
- `heurbridge/core/orient.py` — orientation enum (R0…MY90 ↔ DEF N…FE) with OpenDB transform matrices;
  `lef_def_v1_offset` reproduces the HA-PR `lef_def._transform` for regression.
- `heurbridge/core/design.py` — `Design`/`Layout` data model (T1.1): centre-relative pin offsets,
  CSR nets, core-normalized float64 positions, schema hash, exact HPWL (numpy).
- `heurbridge/core/bookshelf.py` — bookshelf loader and `.pl` writer (round-trip exact).
- `heurbridge/core/defio.py` — LEF/DEF loader (pins/sizes via `eda/harness/lef_def.lef_info`, plus CLASS,
  SITE, routing layers, placement status, ROW, GCELLGRID) and DEF COMPONENTS writer.
- `heurbridge/core/contract.py` — interface contract checker I1 (T1.2): schema, shape, orientation, finite,
  range, fixed, keep-out-of-scope; raises, never repairs.
- `heurbridge/core/synth.py` — synthetic designs (tests, pretraining data).
- `heurbridge/eval/f0.py` — f0 metrics in PyTorch (T1.3): exact/WA/LSE HPWL, macro overlap, outside area,
  density overflow, RUDY H/V overflow, macro-channel shortage, differentiable surrogate `J0`.
- `heurbridge/eval/cost.py` — final cost `J` and gates (T1.6); timing through `metrics_schema`.
- `configs/cost.yaml` (frozen weights), `configs/families.yaml` (draft families and LOFO splits).
- `scripts/ssh_run.sh`, `scripts/sync_to_server.sh` — key-only SSH (BatchMode; no passwords), non-destructive sync.
- Tests: 27 passing (`tests/test_core_design.py`, `test_f0.py`, `test_cost.py`, `test_configs.py`).

### Findings (not yet changed in `eda/`)
- `eda/harness/lef_def.py` pin transform omits the bounding-box shift for non-N orientations and swaps
  FE/FW relative to OpenDB. On the OpenLane `spm` DEFs (S/FS/FN cells present) the canonical
  `hpwl_um` is 5.0–5.6% higher than the geometric value. HeurBridge reports the geometric value
  (`convention="centre"`) and can reproduce `lef_def` exactly (`convention="lef_def_v1"`, ≤1e-7 relative).
  To be confirmed against OpenROAD pin coordinates on server 224 before any HA-PR number is revised.
