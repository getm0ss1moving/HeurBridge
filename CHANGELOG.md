# Changelog

Every change to the code is recorded here with its version, task and verification.
Versions: `0.<milestone>.<patch>`; a git tag `v<version>` marks each release.
(The task list's `_harness/CHANGELOG.md` does not exist in the current checkout; this file replaces it.)

## [0.6.0] — 2026-09-25 — T2.7 seeding driver, Track-B ORFS glue, E0 partners/driver, bridge training + pretraining scripts

### Added
- `heurbridge/eval/orfs.py` — Track B via OpenROAD-flow-scripts: our macro layout as `place_macro -exact`
  commands through `MACRO_PLACEMENT_TCL` (rtl_macro_placer then only places unplaced macros); stage `grt`
  = f1, `finish` + `make metadata` = f2; ORFS metric keys mapped to canonical fields with candidates and
  recorded sources; parser for ORFS' own `2_2_floorplan_macro.tcl` (tool-native M1 layouts).
- `heurbridge/pipeline/` — evaluator adapters (HB-GP Track-A stand-in, ORFS), T2.7 archive-seeding driver
  (seeds x programs -> P_M -> contract -> f1 -> top-10 -> f2 -> archive -> 8-step local search with the
  T2.7 move set; resumable JSONL; failures recorded by name with J = +inf), on-policy bridge data
  (sources, archive elites as graph nodes, symmetry-matched pairs).
- `heurbridge/core/cluster_design.py` — clustered design + macro-stage f0 scorer (cells unplaced).
- `heurbridge/partners.py` — E0 partners: none, memetic (T2.7 moves, f0, time-capped), repertoire (SpecAHD-
  style checked repair per macro-cluster region with rollback), frozen generator (partial noising), co-trained
  bridge (guarded).
- `heurbridge/meta.py` — meta.json with git_sha, config_hash, program/bridge/skill hashes, seed, archive
  snapshot, alpha-ledger id.
- `scripts/run_seed_archive.py`, `scripts/train_bridge.py`, `scripts/run_e0.py`, `scripts/pretrain_bridge.py`.
- `cost.evaluate(..., required_gates=...)`, `Archive(min_fidelity=...)` (development archives are labelled).
- Tests: 87 passing.

## [0.5.0] — 2026-09-25 — f1 evaluator backends, HB-GP development placer

### Added
- `heurbridge/eval/f1.py` — f1 (T1.4): OpenROAD Track-B script (macros FIRM, routability/timing-driven GP,
  DP, check_placement, estimate_parasitics -placement / -global_routing, global_route with 30 congestion
  iterations) and log parser (FastRoute final table: max H / max V / total overflow; GR wirelength);
  Track-A metrics from f0 (HPWL, RUDY overflow/peak, density overflow, channel shortage); DREAMPlace
  parameter builder; missing metrics listed as `unchecked`.
- `heurbridge/eval/gp.py` — HB-GP, an ePlace-style placer (quadratic init, WA wirelength, electrostatic
  density via an exact Neumann Poisson solve, Nesterov with Lipschitz step and pin/charge preconditioning,
  ePlace lambda schedule, Tetris row legalization). Development stand-in only (not DREAMPlace):
  ibm01 HPWL 2.51e6 after legalization (benchmark .pl 2.44e6), adaptec1 1.00e8 (benchmark .pl 1.05e8;
  DREAMPlace-class ~7.3e7); known limitation: does not converge on ibm18 (step collapse on high-degree nets).
- Tests: 81 passing.

## [0.4.0] — 2026-09-25 — T2.2 macro seed population, T0 scripts, ENV_REPORT draft

### Added
- `heurbridge/heuristics/macro/` — seed population (T2.2): M2 simulated annealing on Hier-RTLMP cost terms
  (+ pin-aware orientation pass), M3 boundary-biased mask sampling, M4 clustering + perimeter/block tiling,
  M5 recursive min-cut (Kernighan-Lin) bisection, M6 ordering policy + greedy placement, M7 random control;
  2-3 variants each (16 programs); M1 = tool-native placer via cached wrapper. Each program = shared helpers +
  PARAMS + body, content-addressed. All 16 certify under V0 (AST, run, validation, determinism, MR1).
- `DesignView` macro-level arrays (canonical macro order, effective sizes, affinity incl. 2-hop via cell
  clusters, anchor pulls, obstacles).
- Sandbox audit hook: allows only networkx's own argmap wrapper compilation; all other compile/exec blocked.
- `scripts/server/` — T0.1 inheritance, T0.2 read-only probe (JSON), T0.3 OpenROAD Tcl probe (reads
  `sta::cmd_args`) and isolated install (conda/micromamba, litex-hub), T0.5 env setup + GPU smoke test.
- `ENV_REPORT.md` (draft) and `reports/env/openroad_probe_local_openlane_b16bda7e.txt`: all T0.3 commands and
  flags present in the local OpenLane OpenROAD build.
- Tests: 78 passing.

## [0.3.0] — 2026-09-25 — T3 macro bridge core, T0.4 benchmarks (local), T0.6 client

### Added
- `heurbridge/bridge/graph.py` — macro-stage bridge graph: movable/fixed macros, IOs, soft cell-cluster
  nodes; star edges from each net's driver with rotated pin offsets (both directions, cluster-cluster
  edges merged); graph features; attention set = macros + 512 largest clusters (label-free tie-break);
  quadratic cluster seeding with macros/IOs fixed.
- `heurbridge/bridge/model.py` — BridgeNet: encoder -> [GATv2(4 heads) -> MLP -> global attention] x L ->
  decoder; sinusoidal tau + FiLM; raw + sinusoidal position encodings; zero-init decoder (identity at init);
  small ~1.14M / base ~6.0M parameters; output masked to movable nodes.
- `heurbridge/bridge/data.py` — pairs with Hungarian symmetry matching inside interchangeable-macro groups,
  nearest-elite selection, orientation-mismatch flags, pair weights exp(-(J*-Jmin)/0.02), sharded `.pt`
  storage, DAgger cap; joint dihedral (8) + aspect (+-5%) augmentation.
- `heurbridge/bridge/train.py` — corrected stochastic-interpolant loss + overlap penalty on the
  extrapolated endpoint; AdamW, cosine warm-up, grad clip, bf16 (CUDA), EMA; validation (residual,
  terminal error, evaluator criterion, alpha histogram), early stopping, checkpoints with sha256.
- `heurbridge/bridge/sample.py` — guarded partial transport (alpha in {0, .25, .5, 1}), batched ODE,
  deterministic inference, fixed nodes exactly unchanged.
- `heurbridge/heuristics/cell/cluster.py` — cell clustering (N_c rule of T2.3): spectral embedding +
  area-weighted k-means, METIS/KaHyPar hooks.
- `heurbridge/evolve/llm.py` — DeepSeek client: env-only keys with comma stripping and fallback, JSONL
  ledger (no key material), per-scope budget with 110% hard stop, 16-token self-test.
- `scripts/make_manifest.py`, `configs/manifests/*.sha256` — sha256 manifests: IBM-MSwPins bookshelf
  (108 files) and LEF/DEF (72), ISPD2005 (80 files, header statistics match the published suite).
- Tests: 61 passing, incl. all T3.10 bridge tests (overfit 1 pair; multimodal: bridge overlap < 1% vs
  regression > 40%; equivariance 1e-5; masking; determinism; guard monotonicity on 100 cases).

### Changed (deliberate deviation from the task spec, with evidence)
- The bridge velocity is **not conditioned on the source x^h** (T3.2 lists "x^h position" as a node
  feature). Conditioning on x^h turns each source into a point mass and the ODE follows the conditional-mean
  direction, i.e. the bridge degenerates into a regressor. Multimodal toy: 8.2% overlap with x^h
  conditioning vs 0.1% without (regression 61.5%; Bayes-optimal regression 59.5%). Kept as ablation
  `use_source=True`.
- Model widths 144 (small) / 240 (base) to hit the 1.2M / 6M parameter targets with this block design.

### Data notes
- ISPD2005: original hosts are offline (ispd.cc 404, archive.sigda.org no reply, UT mirror 403); copy taken
  from the Google Drive folder linked by lamda-bbo/BBOPlace-Bench (archive sha256 bd8d44cc...). Node, net,
  pin and terminal counts match the published statistics for 7 designs; bigblue3 matches nodes/nets/pins
  (terminal count 1,298 not independently confirmed).
- ChipDiffusion (vint-1/chipdiffusion @ 6973e90) has **no licence file**: used only for private evaluation,
  never copied into this repository. DREAMPlace is BSD-3.

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
