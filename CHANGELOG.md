# Changelog

Every change to the code is recorded here with its version, task and verification.
Versions: `0.<milestone>.<patch>`; a git tag `v<version>` marks each release.
(The task list's `_harness/CHANGELOG.md` does not exist in the current checkout; this file replaces it.)

## [0.10.6] — 2026-09-26 — Algorithm R end to end: DAgger fix, ledger reservation order, MMD fix

### Fixed
- **Algorithm R never trained on the DAgger aggregate** (`scripts/algorithm_r.py`, T3.7 step 4): it aggregated
  earlier rounds' pairs *after* each round into a directory that `train_bridge.py` never read, so every round
  trained on its own pairs only. Now the aggregate of rounds 0..r-1 is built before round r and passed as
  `train_bridge.py --prior-pairs` (merged before the round's pairs, cap 4,000 newest per design).
- Promotion tests reserve their alpha-ledger entry before any cost is computed (`verify.gates.promote(entry=)`;
  Algorithm R reserves at the start of each round's test).
- `stats.paired.mmd2`: with fewer than two samples on a side the unbiased statistic is undefined; the missing
  within-sample term was silently set to 0, which biased it downward (Algorithm R, 2 training vs 1 validation
  design: -0.26). It now returns NaN there and always reports the biased V-statistic (`mmd2_biased`).

### Added
- `algorithm_r.py --round0-dir` (reuse an existing round-0 run), `--guard f0|f1` (the promotion test's guard,
  default f1 as in T3.8; cached deterministic HB-GP), `--val-every` passed to training.
- `reports/T3_algorithmR_dev.md`, `scripts/report_algr.py` — first end-to-end Algorithm R run (dev: ibm01+02 ->
  ibm03, 16 validation sources, f1 guard, deterministic HB-GP): round 0 (the T3 exit test, bridge + guard vs raw)
  mean J 0.558 vs 0.601, p = 0.0005, promoted (algR_dev#1) — <= raw by construction of the guard, so it does not
  isolate the learned transport; round 1 (DAgger 256 pairs per design, 400 steps) vs round 0: p = 0.39, not
  promoted, stop (algR_dev#2).
- Tests: 127 passing.

## [0.10.5] — 2026-09-26 — Track-B dev seeding results, distinct top-k, calibration on distinct layouts

### Fixed
- T2.7 driver: the top-k for verification / archive admission were the top-k *rows*; seed-independent programs
  repeat their layout, so on bp_fe_top the top 10 held 3 distinct layouts (M5.v0 x5, M4.v0 x4) and the archive
  got 3 elites. Top-k are now distinct layouts (`seed_archive.distinct`, also in `run_f2_miniflow.select`);
  re-running the driver (all evaluations from the ledger) completed the dev archive to 5 elites.
- E3-lite calibration counts one row per distinct layout (duplicates overweighted repeated layouts).

### Added
- `reports/T2_trackB_dev_bp_fe_top.md` — Track-B dev seeding with the corrected flow: 80/80 program evaluations
  completed (no tool failure), setup/hold gates passed on 62% (all failures setup WNS), 15 distinct gated
  layouts below the M1 baseline J = 0.95; best M5.v0 0.8559; local search (45 evaluations) did not improve it;
  archive top-5 (fidelity 1): 0.8559 / 0.8673 / 0.8737 / 0.8745 / 0.8790.
- `reports/E3_calibration_dev_bp_fe_top.md` — Track B, f0 vs mini-flow f1 on 87 distinct layouts: Kendall 0.35,
  top-5 recall 0, f0's pick worse than a random pick (regret 0.116 vs 0.107). Track A redone on distinct
  layouts: Kendall 0.70 / 0.51 / 0.16 on ibm01 / 02 / 03. The G0 rule is not met on either track: f0 must not
  make macro-stage decisions (guard, fitness) — the spec's f1 defaults stand.
- Tests: 126 passing.

## [0.10.4] — 2026-09-26 — reproducible HB-GP f1, E0 fairness and control results

### Fixed
- **HB-GP (Track-A dev f1) was not reproducible** (T1.4 requires determinism): torch's multi-threaded CPU
  reductions changed the result between runs (ibm01, same layout: HPWL 2,646,210 vs 2,651,174 at 3 threads;
  2,649,741.5 twice at 1 thread; E0: same-layout J differs by a median of 7e-4, max 3.4e-3, across
  processes). `run_hbgp_f1` / `HBGPEvaluator` now run on one thread by default (recorded as `gp.threads`;
  the caller's setting is restored); regression test. Past dev data (ibm01-03 archive, dev bridge labels,
  E0 dev runs) were computed multi-threaded: gaps of 2-10% between heuristics and the baseline are far above
  this noise, near-ties are not.

### Added
- E0 dev with the fairness options (`reports/E0_partner_ablation_dev_f1guard_equal*.md`, ledger E0_dev#2,
  #3): with the bridge's guard at f1 and the equal f1 guard for memetic / repertoire, G0' passes (p = 2.1e-5
  and 0.0052), but the random-direction control with the same guard does as well as the bridge (geometric-mean
  J ratio vs raw 0.933 vs 0.931; bridge vs control p = 0.071), and these runs used the non-reproducible
  HB-GP, so the guarded partners' wins include selection on noise (winner's curse: the guard's evaluations are
  the reported final cost in the dev setup). Rerun with the deterministic evaluator: ledger E0_dev#4.
- `scripts/report_e0.py --caveat`; the learned-transport check (co-trained vs random-direction control) in the
  report.
- Tests: 125 passing.

## [0.10.3] — 2026-09-26 — E0 random-direction control, deterministic overfit test

### Added
- `partners.RandomGuardPartner` + `run_e0.py --random-control` — E0 control for open issue 8: the co-trained
  bridge's guard (same alpha grid, P_M and evaluator) along a random displacement whose mean length matches the
  bridge's (median over the budget sources). `bridge/sample.guarded` is the shared guard (refine unchanged).

### Fixed
- `tests/test_bridge.py::test_overfit_single_pair` was flaky under CPU load (default thread count: parallel
  reductions change the 2,000-step trajectory; the spec's 1e-3 threshold leaves little room). It now runs on
  one thread with a fixed seed: terminal error 5.9e-4 on every run.
- Tests: 124 passing.

## [0.10.2] — 2026-09-26 — staged f2 (ORFS-style), LEF/DEF round trip, OpenROAD pin-geometry check, dev E0 report

### Changed
- Track-B dev f2 runs as ORFS does: one OpenROAD process per stage (cts, rt = repair_timing, route = GRT +
  DRT + fill, final = OpenRCX + STA), each reading the previous stage's database. In one process,
  `repair_timing` after CTS segfaulted in the STA arrival search of the local build (smoke test on M1).
  A failed stage fails the candidate by name (one retry for crashes); no stage is skipped silently.
  Smoke test on the M1 layout (2 threads): all four stages pass in 782 s; DRC 0, detailed WL 1,618,701 um,
  264,348 vias, setup WNS -1.979 ns / TNS -57.8 ns (extracted, propagated clocks), hold +0.096 ns, 0.169 W.
- Verified end to end on CPU (server jobs, never run before): T3.4 pretraining (`pretrain_bridge.py`, 40
  steps over both data stages, checkpoint + hash) and E0's frozen-generator partner with that checkpoint on
  ibm01.

### Added
- `scripts/roundtrip_all.py --lefdef`, `reports/T1_roundtrip_lefdef.json` — T1.1 round trip on the 18 IBM
  LEF/DEF designs through the DEF writer: 18/18 identical (HPWL compared NaN-aware: the IBM DEFs leave
  383-2,463 objects unplaced). With the bookshelf sweep, all 44 local bookshelf / LEF/DEF designs pass.
- `scripts/verify_pin_geometry.py`, `reports/V3_pin_geometry_vs_openroad.json` — **confirms the 0.1.0 finding
  on `eda/harness/lef_def.py` with OpenROAD's own pin geometry** (OpenDB `getBBox` of every ITerm/BTerm, local
  OpenROAD b16bda7e; minimal sky130 technology LEF, connectivity-only DEF copies): on the HA-PR spm placement /
  cts / routing DEFs OpenROAD's HPWL equals HeurBridge's geometric value exactly (5104.355 / 5519.0625 /
  5920.3575 um) and `lef_def`'s canonical `hpwl_um` is 5.25% / 5.83% / 5.96% too high. `eda/` is not changed
  (inherited harness); revising HA-PR numbers is the user's decision.
- `scripts/report_trackb_dev.py` — Track-B development seeding report (baseline determinism, per-program gate
  pass rate and J before / after the gates, failures by name, local search, archive top-k).
- `reports/E0_partner_ablation_dev.md` — dev E0 on held-out ibm04 / ibm06 (160 paired cases, every partner
  deciding on f0, final J = HB-GP f1): G0' dev FAIL (co-trained vs memetic p = 0.99, vs repertoire p = 0.68;
  ledger E0_dev#1). `scripts/report_e0.py` adds wins / losses / median dJ / geometric-mean ratio vs the raw
  layout and the guard configuration.
- Tests: 123 passing.

## [0.10.1] — 2026-09-26 — audit fixes: V0 NaN bug, P_M spacing + packing, -allow_congestion, T5 driver, E0 guard options

### Changed
- Mini-flow f1: `global_route -allow_congestion` (in the local build). Without it FastRoute stops with
  GRT-0119 when overflow remains, so every routable layout reports OF = 0 and the (1+OF) term of J is never
  measured; the congested layout (bp_fe_top M2.v0 seed 1) is re-evaluated, its failed row kept in
  `superseded_no_allow_congestion.jsonl`. f2 keeps the ORFS default (a congested layout fails there).
- `scripts/run_e0.py`: `--guard-fidelity f0|f1` (the co-trained bridge's guard; T3.8 default f1) and
  `--equal-guard` (every other partner's output is kept only if it beats the raw layout at the same
  fidelity), both recorded in the ledger entry and the summary; final costs cached per layout.

- **Track-B P_M spacing = 2 x MACRO_PLACE_HALO** (`scripts/run_seed_miniflow.py`). The platform halo is
  per side in `rtl_macro_placer` (inflated macros do not overlap: M1 keeps 20 um between RAMs and >= 10 um
  to the core edge for halo 10); P_M's halo is the macro-to-macro spacing and used the platform value, so
  macros sat 5 um from the core edge and pdngen failed on 6 of 16 layouts (PDN-0179: 3.5 um metal4 channel
  at the core edge). 16 rows superseded (`superseded_halo_spacing_10/`); the M1 baseline is unaffected.
- P_M: bottom-left packing as the last fallback order (targets only order the macros). At spacing 20 the
  target-driven orders failed on 0.8-2% of random bp_fe_top layouts; with it 1,000/1,000 are legal.

### Fixed
- **V0 certificate rejected every program on real designs** (`evolve/sandbox.certify`): the determinism
  check compared two runs with `np.array_equal`, and unplaced cells are NaN rows in every output (NaN != NaN;
  ibm01: 12,260 rows). The seed programs had only been certified on synthetic designs without NaN, so the
  bug was invisible until the first end-to-end evolution dry run. Now `equal_nan=True`; regression test.
- RLCE (`evolve/rlce.py`): structural groups are bounded (`max_group` = 8, grown from the highest-attribution
  member) — with a weak bridge (rho = 0) every macro is structural and the whole design formed one "group"
  (ibm01: 246 of 246 macros); the evidence pack no longer names a "decisive group" when no group has a
  positive counterfactual gain.

### Added
- `scripts/run_evolution.py` — T5 campaign driver: proposer (heurbridge / eoh / reevo / funsearch /
  heuragenix) x fitness (refinability / raw) on D_evo; V0 certificate with an MR1 probe design; RLCE evidence
  (rho calibrated from the population's sources) and HeurAgenix critical-operation analysis; the LLM's inputs
  saved per generation (`context_g<g>.json`); LLM budget scope per split (B.3). `--llm mock` is a
  deterministic offline stand-in for dry runs (labelled `dry_run`); all five proposers dry-run end to end on
  ibm01. Not in the driver yet: promotion of the top 20% to f2 and re-anchoring after bridge promotions.
- Tests: 123 passing (NaN-cell certification, bounded RLCE groups, evidence without a positive
  counterfactual, dense RAM core at spacing 20, `-allow_congestion`, f2 script and parser).

## [0.10.0] — 2026-09-26 — Track-B development flow aligned with ORFS, robust f1, P_M fallback, dev calibration

Covers the two commits after v0.9.1 that had no entry (55531ee, 12b29e1) and the changes of 2026-09-26.

### Added (55531ee, 12b29e1 — 2026-09-25)
- `heurbridge/eval/miniflow.py` — minimal Nangate45 flow for the local OpenLane OpenROAD (b16bda7e), which
  cannot run current ORFS: hierarchical Yosys synthesis, floorplan, tool-native `rtl_macro_placer` (M1), f1.
- `heurbridge/core/odb.py` — ODB -> DEF -> `Design` loader (verified on nangate45 gcd: 304 objects, 54 IO).
- `heurbridge/pipeline/evaluators.py::MiniflowEvaluator` (one retry on a tool crash, crashes recorded);
  `place_macro -exact` made optional (absent in the local build; its use failed the whole first campaign,
  recorded in `runs/seed_miniflow/bp_fe_top/failed_attempt_1/`).
- `scripts/run_seed_miniflow.py` (Track-B development seeding), `scripts/algorithm_r.py` (T3.7 driver),
  `docs/SERVER_RUNBOOK.md` (exact command sequence for T0-T4 once SSH works).

### Changed (2026-09-26)
- **Mini-flow aligned with ORFS** (all earlier Track-B development rows superseded, kept under
  `runs/seed_miniflow/bp_fe_top/superseded_*`): configuration read with ORFS/Make semantics (design
  `config.mk`, then the platform's; `?=` fills gaps) — global placement density is now the platform default
  0.30 (was a hard-coded fallback of 0.6), core margin 1.0 (was 2), platform `make_tracks.tcl`, dont-use cells
  in synthesis (`abc`) and sizing, the design's `fastroute.tcl`; f1 now inserts tapcells and the power grid
  after the macros are placed (ORFS 2_3/2_4) and buffers the ports (ORFS 3_4).
- **Mini-flow f1 robustness** (the first campaign lost 7 of 18 evaluations): timing and power come from
  placement-stage parasitics, for the baseline and every candidate alike. In the local build,
  `estimate_parasitics -global_routing` fails at random (bad_alloc "out of memory" and process exit, segfault,
  or an OOM kill), so GR-stage timing is opt-in (`gr_timing`). `report_power` segfaulted once the power grid
  existed: bisected to the VDD/VSS block terminals `pdngen -pins` creates (vertex-less ports corrupt
  OpenSTA's power seeding during placement); they are removed right after `pdngen` (nets and straps stay).
  Every failure is named (`classify_failure`: tool_oom, tool_assertion, segfault, timeout, tool_error); one
  retry for crashes and bad_alloc; a failed row keeps its tool record. A deterministic gpl assertion
  (`std::vector<gpl::Bin>` index out of range, macro layout M4.v1) is recorded as a tool failure.
- M1 baseline flow evaluated 3 times (T1.7 median; the repeats test determinism, T1.4). Finding: f1 is
  identical across repeats at a fixed thread count but not across thread counts (setup TNS -113.5 ns with 6
  threads, -86.9 ns with 3 on the M1 layout), so a campaign fixes the count.
- **P_M fallback orders** (`core/project.py`): largest-first greedy legalization can fragment a dense core
  (bp_fe_top: nine 153 x 113 um RAMs, at most 15 halo footprints in a perfect packing) and failed on 0.5% of
  random layouts and on one heuristic output. Only when the primary order fails, sweeps by target y, target x
  and centre-out are tried and the legal result with the least displacement is kept; the primary result is
  unchanged whenever it is legal. 1,000/1,000 random bp_fe_top layouts legal (was 995).
- `heurbridge/meta.py`: `git_sha` is the commit at process start (the code the run imported);
  `git_sha_at_write` and `process_started` are added. (The dev bridge run's meta shows 0.8.1 code with the
  end-of-run commit — the inconsistency that motivated this.)
- `heurbridge/reporting.py`: reports go to a public repository — the repo root becomes `.`, the home
  directory `~`. Local absolute paths removed from ENV_REPORT, HANDOFF, docs/SERVER_RUNBOOK.
- `scripts/report_bridge.py`: pairs per design, parameter count, run-vs-report versions, and a caveat when the
  validation residual rises while the guarded criterion improves.
- `.gitignore`: `archive_dev*/`; the development archive SQLite files are no longer tracked.
- Removed `reports/env/dev_calibration_f0_vs_hbgp.json`: it scored one layout per design (a harness error)
  and used the raw RUDY overflow; superseded by `reports/E3_calibration_dev_ibm.md`.

### Added (2026-09-26)
- `scripts/roundtrip_all.py`, `reports/T1_roundtrip_bookshelf.json` — T1.1 load -> write -> load identity on
  all 26 bookshelf designs (ibm01-18, adaptec1-4, bigblue1-4): 26/26.
- `scripts/calibrate_dev.py`, `reports/E3_calibration_dev_ibm.md` — E3-lite: f0 proxy (the bridge-guard
  scorer) vs HB-GP f1 on the stored campaign rows. Kendall 0.65 / 0.50 / 0.03 on ibm01 / 02 / 03, top-5
  recall 0 on all three, regret 55% of random: the G0 rule is not met for (M, f0).
- `reports/T3_bridge_macro_dev.md` — dev bridge round 0 (ibm01+02 -> ibm03, 2,000 CPU steps): guarded f0
  2.0125 vs raw 2.0411 (-1.4%), 91% of held-out sources improved; validation residual and terminal error
  rose over training (reported as a caveat). Development evidence, no gate claim.
- `scripts/run_f2_miniflow.py`, `MiniflowF2Evaluator`, `miniflow.f2_script` — Track-B development f2 (T1.5) on
  the ORFS stage sequence: f1 placement, CTS + setup/hold `repair_timing` (design hold margin), GRT, detailed
  route, fill, OpenRCX extraction + STA; DRC count, wirelength and vias from TritonRoute. Selects the f1 top-k
  (T2.7) and an even spread over the f1 range (f1 -> f2 calibration); fidelity-2 archive insertion.
- M1 baseline at f1 evaluated 3 times: bit-identical (GR WL 1,832,439 um, setup WNS -2.336 ns, TNS -113.48 ns,
  hold +0.096 ns, 0.151 W; 109 s).
- `scripts/run_e0.py` records the bridge checkpoint's sha256 in the alpha-ledger entry.
- Tests: `tests/test_miniflow.py` (8), dense-RAM-core P_M tests (2); 119 passing.

## [0.9.1] — 2026-09-25 — V3/V5 gates, H8 null injection, ORFS signoff (f3), MMD, report generators

### Added
- `heurbridge/verify/gates.py` — V5 promotion gate (alpha reserved before the data are read; paired
  one-sided Wilcoxon with failures as +inf), H8 null injection (placebo promotion rate with Clopper-Pearson
  bound), V3 recompute consistency.
- `heurbridge/eval/orfs.py` — f3 `signoff` stage: ORFS `drc` / `lvs` targets (KLayout decks), canonical DRC
  (signoff count when available, else detailed-route count; METRIC_CONVENTIONS s.8).
- `heurbridge/stats/paired.py::mmd2` — unbiased MMD^2 with the median heuristic (Algorithm R monitoring).
- `scripts/report_bridge.py`, `scripts/report_e0.py` — T3 exit and E0 reports through the T7.4 template.
- `reports/T1_baselines_dev.md` — development baseline table (T1 exit format), f1 runtime per design.

## [0.9.0] — 2026-09-25 — T2.3 cell seeds, T2.4 pattern router, T7.4 reporting, Track-A OF proxy fix

### Added
- `heurbridge/heuristics/cell/seeds.py` — cell-stage seeds on cluster centroids (T2.3): quadratic with macros
  fixed, rank-based spreading (alpha 0.3 / 0.6), dataflow region assignment.
- `heurbridge/heuristics/route/pattern.py` — vectorized congestion-aware pattern router (T2.4): MST 2-pin
  decomposition, L/Z candidates costed in O(1) with prefix sums, batched usage updates with difference
  arrays, net orders (HPWL, criticality) and edge-cost functions (linear, quadratic, exp); demand tensors.
  Tests: exact H/V demand conservation; batch-1 routing spreads usage over both L-shapes.
- `heurbridge/reporting.py`, `reports/templates/experiment_report.md` — T7.4 mandatory report fields; a
  report can claim an improvement only if its gate passed.
- `scripts/rescore_archive.py` — rebuild a development archive from stored records after a proxy change.

### Changed
- **Track-A overflow proxy**: `rudy_of_pct` = 100 x (RUDY overflow / RUDY demand) replaces the raw RUDY
  overflow in microns. With the raw value, (1+OF)/(1+OF_base) exploded (J up to 2e4 on ibm02 because the
  baseline overflow was 0) and produced an artificial 25% "gain" on ibm03. Rescored development archive:
  `archive_dev_v2` (baseline best on ibm01/02/03; seed heuristics 1.8-9.5% worse on the Track-A J).
- Finding for Track B (decision for the user, weights are frozen): (1+OF)~ normalized by a baseline with
  near-zero GR overflow makes J extremely sensitive to a few overflows (OF 0 -> 20 adds 3.0 to J).
- Tests: 107 passing.

## [0.8.1] — 2026-09-25 — T6.1 online solve, T7.5 originality hygiene, handoff

### Added
- `heurbridge/online/solve.py` — online macro-stage solve (T6.1): state card, top-k portfolio programs x seeds,
  bridge + guard at f1, best b to f2, deploy argmin{baseline, verified candidates} (Lemma 3); zero LLM calls.
- `heurbridge/verify/originality.py` — rediscovery check (T7.5): AST 5-gram containment for Python
  references and winnowed normalized-token 8-gram containment for any language; > 0.8 = rediscovery.
- HANDOFF.md session entry (work done, commands, artifacts, open decisions).
- CHANGELOG 0.8.0 test count: 103 (not 104).

## [0.8.0] — 2026-09-25 — E3 calibration + gate G0, V1 metamorphic tests, baseline elites

### Added
- `heurbridge/stats/calibration.py` — E3 analysis (T6.2): per-design Spearman/Kendall, top-5 recall, decision
  regret vs random; isotonic maps with split-conformal 90% intervals (coverage checked); gate G0 per
  (stage, fidelity); writer for `configs/fidelity_admissible.yaml`.
- `heurbridge/verify/metamorphic.py` + `tests/test_metamorphic.py` — V1 relations MR1-MR6 as hypothesis
  property tests (50 cases each): relabel, mirror (orientation composed with MY), translate, zero-weight
  dummy net, tightened GCell capacity, side-by-side duplicate.
- `scripts/run_seed_archive.py` admits the baseline layout as an initial elite (proposal s.3.5).

### Fixed
- f0 grid counts (density bins, GCells) now tolerate round-off in the core size (found by MR3: a translated
  core of height 1000.0000000000001 produced 21 instead of 20 GCells).
- P_M breaks equal-area ties with a label-free key (MR1 equivariance of the projection).
- CHANGELOG 0.7.0 test count: 94 (not 95).
- Tests: 104 passing.

## [0.7.0] — 2026-09-25 — T5 evolution machinery (prompts, RLCE, fitness, population, engine + baselines)

### Added
- `heurbridge/evolve/prompts.py` + `prompts/skill_v0.md` — EVOLVE-BLOCK template (AlphaEvolve convention),
  system prompt (contract, DesignView API, EDA invariants, skill doc S v0 written from reply_Q1_Q3 s.1.4 and
  the pilot lessons), user prompt with the RLCE evidence, strict parser (one retry, then discard + log).
- `heurbridge/evolve/rlce.py` — RLCE diagnosis: integrated gradients of J0 along x*->x_hat (completeness gap
  reported; measured O(1/steps) convergence because J0 has ReLU kinks), reachability split with rho_M
  calibration, structural groups (netlist affinity + proximity), counterfactual splices through bridge +
  guard, evidence pack (text for the LLM, PNG/JSON for humans).
- `heurbridge/evolve/fitness.py` — refinability fitness F(h|H) (portfolio gain - 0.2 standalone - 0.01/s over
  30 s), facility-location portfolio value with greedy (1-1/e) pruning (checked against brute force),
  leave-one-design-out ridge predictability probe pi(h).
- `heurbridge/evolve/population.py` — MAP-Elites over (family, decision type, runtime class), 4 islands,
  ring migration, portfolio, fitness re-anchoring.
- `heurbridge/evolve/engine.py` — generation loop with pluggable proposers (HeurBridge/RLCE, EoH 5 operators,
  ReEvo reflections, FunSearch best-shot, HeurAgenix Algorithm 1) and fitness (refinability or raw);
  every discard/rejection/failure logged by name; LLM budget ledger enforced.
- Tests: 95 passing.

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
