# Changelog

Every change to the code is recorded here with its version, task and verification.
Versions: `0.<milestone>.<patch>`; a git tag `v<version>` marks each release.
(The task list's `_harness/CHANGELOG.md` does not exist in the current checkout; this file replaces it.)

## [Unreleased]

### Added (T3.9 interface; owner's decision 29 Sep: bridge-to-bridge parts now, tool hand-off after G0')
- **Stage hand-off** `heurbridge/bridge/handoff.py`. The macro-stage graph already carries the standard cells as
  clusters that the bridge moves together with the macros, but only the macros were kept. The hand-off keeps the
  clusters' guarded positions (the clusters of `src + alpha (end - src)` at the guard's alpha; alpha = 0 gives the
  quadratic placement) as a sketch for the next bridge stage:
  - `Handoff` (.npz, format `heurbridge.handoff.v1`): the sketch, the legal macro positions it belongs to and the
    graph hash; `check` refuses another design, another clustering, another layout's macros and values outside
    [0, 1];
  - `next_stage_source(graph, layout, handoff=None)`: without a hand-off exactly `source_nodes`;
  - `transfer_sketch` (onto another clustering; exact for nested ones) and `member_positions`;
  - `anchored_clusters` (quadratic placement pulled toward the sketch; mu = 0 is `quadratic_clusters`);
  - `sketch_fidelity` (area-weighted RMS distance to reference cluster centres).
  `solve_macro(keep_handoff=True)` attaches a hand-off to each beam candidate; the default output and every
  decision are unchanged (tested). Nothing on the evaluation path (partners, `run_e0.py`, evaluators, f0,
  DREAMPlace) uses it, and a test enforces that: G0' is unaffected. Handing the sketch to DREAMPlace or OpenROAD
  waits for G0'. Tests: `tests/test_handoff.py` (12); full suite 166 passed.

### Fixed
- `report_trackb_dev.py` `tools_line` dropped the closing parenthesis of the new-format Yosys path; it now strips
  only an unbalanced one.

### Reports
- `reports/T2_trackB_orfs_bp_fe_top.md` regenerated from `seedB_band_bp_fe_top` (the finished band job; the same
  129 f1 and 24 f2 rows plus 9 band rows). The candidate noise bands are descriptive: the 3 best candidates stay
  at 0.874-0.949 under every one-site or one-row shift. The tool's own layout through the same path spans
  1.033-1.405.

### Docs / housekeeping (29 Sep 15:30)
- `.gitignore`: local proposal documents (`HEURBRIDGE_PLAN_*.md`) are unpublished research documents and stay out
  of the public repository, like the task list and the proposal.
- `reports/PROGRESS.md` 15:30: full E0 12 of 16 parts complete (bigblue3 equal guard: 300 rows, one budget over its
  4 slices, rc 0, no duplicate case); bigblue4 measured at ~4.75 h per case (ETA 30 Sep 22:00 - 1 Oct 01:00); the
  afternoon's decisions recorded (all bigblue4 slices kept, B.3 frozen, Track-B plan under way).

### Added (Track B, user decisions 2026-09-29: B.3 stays frozen; apply the Track-B plan)
- **Candidate noise bands** (`run_seed_orfs.py --phase band --band-top K`): the K best f2-admitted candidates are
  shifted as a whole by one site (+x, -x) or one row (+y) and re-run through f2, exactly like M1's same-path
  replays (rows `<run>.p1-3.f2`, program CAND_BAND). `report_trackb_dev.py` adds a "Candidate noise bands" table
  and counts a candidate as better than the tool only if its whole band lies below the tool's same-path band;
  CAND_BAND rows stay out of the signoff statistics.
- **Standard-cell warm start for imported macro layouts** (`OrfsEvaluator(warm_start="quadratic", cluster_of=...)`,
  `orfs.cell_locations_tcl`; demo `run_seed_orfs.py --phase warmstart`). In OpenROAD 676f8451 the first global
  placement (ORFS 3_1, -skip_io, no initial placement) keeps already placed cells only when every cell is placed
  (mpl2's warm start in the unmodified flow) and starts all others at the core centre -- which is what every
  imported layout got. Now each standard cell can start at its cluster's position from a quadratic placement of
  the clustered netlist with the layout's macros and the IOs fixed; every cell is placed (placed cells are locked
  otherwise) and a name that does not resolve stops the flow (HB-WARM-START). The demo re-runs M1's replay, its
  shifts and the best candidates at f1/f2 with the warm start (evals_ws*.jsonl); the report compares both starts.

### Changed
- **cost_v3 (user decision 2026-09-29): Track B's timing gates compare with the same-path replay.** The setup and
  hold WNS gates (frozen rule B.3, guard 0.02 ns) now refer to the tool-native macro layout run through the
  candidates' path -- median over the replay and its one-site shifts, per fidelity (`cost.with_gate_reference`,
  `run_seed_orfs.py --gate-reference replay`, the default) -- instead of the unmodified flow, whose standard cells
  start from Hier-RTLMP's placement. J is still normalized to the unmodified flow (task list T1.6); Track A has no
  timing and is unchanged, so the running E0 is not affected. `configs/cost.yaml` version cost_v3_2026-09-29.
  Effect (reports re-scored): bp_fe_top 16 of 20 signoff layouts pass every gate (was 15); bp_be_top 9 (was 13):
  its same-path replay has more hold slack (+0.055 ns vs +0.010 ns), so candidates with small positive hold slack
  now fail the "no more than 0.02 ns worse" part of B.3. The three Track-B jobs still running on 224 score with the
  old reference at run time; their rows are re-scored in the reports and their archives are rebuilt before use.
  Test: `test_cost.py::test_gate_reference_same_path_replay`.

### Added
- **Track-B ORFS report** (`report_trackb_dev.py --label orfs`, first: `reports/T2_trackB_orfs_bp_fe_top.md`).
  Every stored row is re-scored from its record under the current cost rule (the campaign resumed rows written
  under cost_v1, which enforced the timing gates at f1); 'timing gates passed' counts setup/hold within the B.3
  guard; a signoff (f2) section: completed/admitted layouts, failing gates, J before the gates, Kendall tau of
  f1 vs f2, admitted layouts below the f2 noise band and below the same-path replay; the run's real command line;
  f2-admitted archive top-k. `tools.describe(yosys=...)` and `run_seed_orfs.py` now record the Yosys the flow runs
  (`--yosys`/HB_YOSYS); earlier runs recorded the one on PATH (0.38+92) although ORFS ran Yosys 0.48 -- the report
  names the configured binary.

- **RUDY without the 18 GB temporary, and a host-wide cap on memory-heavy steps.** On 231 the kernel's OOM killer
  ended one E0 slice (bigblue3 spec 2/4) at 22:46 on 28 Sep: 21 GB resident. Cause: `F0Context.rudy` sums each
  net's demand over the GCells with a three-operand `torch.einsum`, and without `opt_einsum` (not installed on the
  servers) torch materializes a nets x ngx x ngy float32 temporary -- 18 GB on bigblue3, 36 GB on bigblue4, 9 GB
  on adaptec4 (measured on 225: 1.60 GB above baseline for 100k nets x 64 x 64, as predicted). Now
  `f0._gcell_sum`: `HB_RUDY_IMPL=einsum` (default, the reference implementation every stored result used) or
  `bmm` (one batched matrix product, no temporary, equal to ~1e-6 relative -- a run must use one implementation
  throughout). `tools.slot(name, n)` caps concurrent holders per host (flock files in HB_SLOTS_DIR, default
  /dev/shm/.hb_slots); DREAMPlace f1 takes a "metrics" slot around its RUDY/HPWL step when `HB_METRIC_SLOTS` is
  set (timing only; results unchanged). Tests: `test_f0.py::test_rudy_bmm_equals_einsum`, `test_tools_slot.py`.

- **DREAMPlace GPU out-of-memory is rerun, not scored** (`eval/dreamplace.run_placer`). With several E0 slices
  sharing a GPU, a placer run can die because the GPU is momentarily full; that says nothing about the layout, and
  recording it as a failed case (J = +inf) would add noise to the paired tests. Such a run is rerun after 30, 90,
  270 s (DREAMPlace is deterministic, so the rerun gives the result the first run would have); any other failure is
  returned as before; the log records the reruns. A placer run SIGKILLed by the host's OOM killer (rc -9) is
  rerun the same way (2026-09-29: bigblue4's placer reaches 10 GB of host memory; a killed run would otherwise
  be recorded as a failed case). Test: `tests/test_dreamplace_retry.py`.

- **E0 components split over processes** (`run_e0.py --slice K/N --sources-cache DIR --budget-s S --prepare-only`).
  The full E0 is CPU-bound (memetic and repertoire each spend the bridge's whole budget per case; measured 10-27 min
  per case on ISPD2005, adaptec4 ~27 h per component), so one component can now run as N contiguous slices of its
  source list. The protocol is unchanged: every slice uses the component's one budget and random-control scale
  (`<cache>/budget_<design>.json`, written once by `--prepare-only`, which measures it with the timed probe as
  before, or takes `--budget-s`, the value the component's first run measured, and recomputes the scale from the
  bridge's unguarded endpoints -- `CotrainedPartner.displacement`, the same batch-of-one integration, equal to the
  call's `disp` by test); every row records the host load (`load1`). `e0_combine.py` now refuses duplicate cases
  and a design whose rows carry different budgets. Tests: `tests/test_e0_slices.py`, partner displacement.

- **Track-B noise band** (`run_seed_orfs.py --noise-replays 3`, default): besides the same-path replay of M1, the
  whole M1 layout shifted by exactly one site (+x, -x) or one row (+y) goes through the candidates' path at f1 and
  f2 (rows `<design>.M1replay.p1-3`). ORFS is deterministic, so this is the task list's "3 seeds" of the baseline:
  the spread of J over base, replay and shifts is the band a candidate's improvement must exceed.
  `report_trackb_dev.py` prints the band. (A shift is checked at zero halo -- M1 itself does not meet P_M's 20 um
  spacing rule, smallest gap 19.88 um -- and never re-legalized: P_M would move macros by hundreds of um.)

- **Pre-registered, pooled E0** (T4). `scripts/e0_preregister.py` reserves campaign E0's ledger entries before any
  data exist -- E0#1 primary (task-list protocol, held-out family ISPD2005), E0#2 equal guard, E0#3 the training
  family's held-out designs -- with the protocol in each entry's meta, and writes `reports/E0_preregistration.md`.
  Per-design runs are `run_e0.py --component <id>` (no ledger entry of their own, so they do not spend alpha);
  `e0_combine.py --ledger-entry E0#1` records the pooled result after checking that the entry is open and that
  designs, guard, equal guard, final cost, seeds and the bridge checkpoint (sha256, now in every run's meta) match.
  Checked with a scratch ledger: registration, refusal of a second registration, of a protocol mismatch and of a
  closed entry, and a matching record.

- `scripts/e0_combine.py`: one analysis over several `run_e0.py` runs (e.g. one per design) for `report_e0.py`;
  statistics from the new side-effect-free `run_e0.summarize` (the alpha-ledger record stays in `run_e0.analyse`);
  the runs must share the protocol. Checked: a two-design run split by design and recombined gives identical
  p-values and mean J. `report_e0.py --demo` labels an exploratory demo.

### Operations (2026-09-28 19:52, user-approved)
- The running full-E0 jobs were stopped and restarted as slices (`e0x_*`; cases done before the restart kept via
  `--resume-from`, sources reused from encrypted saves, budgets carried over with `--budget-s`). Checked on the
  restarted components: the recomputed random-control scale equals the original probe's exactly. bigblue4 moves
  whole to 225 (no rows had been computed on 231).

### Observed (Track B, bp_fe_top campaign complete, 2026-09-29)
- Signoff (f2) on 20 layouts: 15 pass every gate, 14 of them below the unmodified flow (J 1.00); best 0.881 (local
  search around the best heuristic layouts). The tool's own macro layout through the same path scores 1.323 and
  fails the setup gate; its one-site shifts span 1.03-1.40. f1 and f2 agree only moderately (Kendall tau 0.51 over
  20 layouts). Descriptive: each candidate is one run, and a candidate's own one-site shifts could move it as much
  as M1's do, so no improvement is claimed before candidates get their own noise band.
- bp_be_top (complete 11:39): 13 of 20 f2 layouts pass every gate, 9 below the unmodified flow, best 0.931 (local
  search); the same-path replay is 1.103 and its shifts span 1.02-1.16 (band width 0.16); f1/f2 Kendall tau 0.78.
  34 of 80 program runs fail at f1, all with GRT-0116 (global-routing congestion). Same caveat as bp_fe_top.
  `reports/T2_trackB_orfs_bp_be_top.md`; the report now merges a tool message's variants into one failure line.

### Observed (T3.7 training data, 2026-09-28)
- Algorithm R's rounds 1-2 trained on exactly round 0's pairs (checked on the fetched shards: x0, x1, weights and
  struct_err identical): the seed programs do not change before T5 and the archive is not updated with the
  bridge's outputs, so the DAgger aggregation duplicated the 1,608 round-0 pairs (2x, 3x). The on-policy part of
  Algorithm R only adds information once the population changes (T5) or refined layouts enter the archive.
  Recorded in `reports/T3_algorithmR_trackA.md`.

### Observed (Track B, 2026-09-28)
- **The same-path replay of M1 scores worse than base M1**: f1 J 0.959 (bp_fe_top), 1.024 (bp_be_top), 0.958
  (ariane136) vs 0.95 by construction; at f2 bp_fe_top's replay has J 1.323 before the gates vs 1.00 and fails the
  setup gate. Almost all of it is timing: setup TNS -1.756 ns vs -0.336 ns (the (1 - TNS) term doubles because the
  base TNS is close to 0), WNS -0.122 vs -0.077 ns; wirelength +0.7 %, vias +2.3 %, power +0.5 %. The only
  difference between the two runs is global placement's starting point (Hier-RTLMP leaves the standard cells
  placed). Candidate comparisons must be paired with the replay, and the noise band above decides what counts as
  an improvement.
- **Why candidate layouts fail placement** (`probe_ariane133_place`): the SA layout M2.v0.s0 fails with ORFS's
  default timing-driven global placement (5,000 iterations, overflow 0.30, then DPL-0036) but converges with
  `GPL_TIMING_DRIVEN=0` (730 iterations, overflow 0.0999; detailed placement passes); M1's replay converges either
  way. So the failures come from the 2024-12 timing-driven placement diverging on scattered layouts. The default
  flow stays the evaluation (the M1 baseline uses it); a run of base and candidates with timing-driven placement
  off would be a robustness check.

### T3.7 done (2026-09-28; `reports/T3_algorithmR_trackA.md`)
- Algorithm R on Track A (13 IBM training designs, validation ibm04/ibm06, DREAMPlace f1 guard and final cost):
  round 0 promoted (T3 exit gate; J 0.4815 vs raw 0.8870, p = 2.6e-9, `algR_trackA#1`), round 1 promoted (0.4756 vs
  0.4815, p = 1.2e-4, `#2`), round 2 not promoted (0.4864 vs 0.4756, p ~ 1, `#3`) -> stop. **Final checkpoint:
  round 1** (sha256 f95bdde8...; the one the E0 demo used). Every round's best validation checkpoint was at step
  4,000 of 20,000 (training overfits early). The job's six ledger lines are merged into `stats/alpha_ledger.jsonl`.
  `report_algr.py`: `--node`, `--track`, per-round training table.

### E0 demo results (exploratory, 2026-09-28; `reports/E0_demo_spec.md`, `reports/E0_demo_eq.md`)
- ibm04 + ibm06 (T3.7's validation designs: optimistic for the bridge), 16 programs x 2 seeds = 64 paired cases,
  T3.7 round-1 bridge, final cost DREAMPlace f1. **The co-trained bridge has the lowest final J under both
  protocols** (mean J 0.482; task-list protocol: memetic 0.701, repertoire 0.749, frozen generator 0.746, raw 0.897;
  equal guard: memetic 0.697, repertoire 0.699, frozen 0.503). Holm-adjusted one-sided p: task-list protocol <= 2.4e-10
  against every partner; equal guard 4.2e-9 (memetic), 5.4e-9 (repertoire), 2.1e-6 (frozen). Learned direction vs
  the random-direction control (same guard): p = 2.3e-9, mean J 0.482 vs 0.508. With the equal guard the bridge
  improves the raw layout in 54 of 64 cases, never worsens it (geometric-mean J ratio 0.845; frozen 0.882, random
  0.889, memetic 0.936, repertoire 0.936). Caveats: much of the gain over memetic/repertoire comes from the guard's
  access to f1 (random direction + guard: 0.508); ibm06's raw layouts are poor (mean J 1.25), which inflates gains;
  at the portfolio level (best program per design) the bridge's 0.437 is close to raw's 0.443. Go decision: the
  demo points the right way; the full, pre-registered E0 follows with the final T3.7 checkpoint.

### Fixed
- The new E0 Holm family named the frozen partner `frozen`; the partner is `frozen_gen`, so it had been left out of
  the four comparisons (found in the demo analysis; `run_e0.SPEC_PARTNERS`, `e0_preregister.py`).
- **E0 Holm family** (task list T4: "Holm over 4 comparisons"): Holm now runs over none / memetic / repertoire /
  frozen only; controls (the random-direction partner) are tested on their own (`controls`), and the G0' gate uses
  the Holm-adjusted p of memetic and repertoire (it used the unadjusted ones).

## [0.14.0] — 2026-09-28 — T4 starts: E0 demo on 225; cost_v2 gate rule; LLM = deepseek-flash

### Changed
- **Gate enforcement by fidelity (cost_v2, the user's decision 2026-09-28).** At f0/f1 only a failed flow sets
  J_inf = +inf; the timing and DRC gates are computed and reported (`"enforced": false`) but do not remove a layout,
  because f1 timing predicts f2 badly (10 of 12 f1-passing bp_fe_top layouts failed at f2, and the best gated f2
  layout was gated out at f1). At f2/f3 every gate is enforced. `cost.ENFORCED_GATES`, `configs/cost.yaml`
  (`gate_enforcement`, version cost_v2_2026-09-28; weights unchanged), reports show "cost cost_v2_2026-09-28".
  Stored ledger rows are re-scored under the current rule when a campaign resumes (`seed_archive.rescore`; the
  ledger keeps the values as written). Tests: f1 reports/f2 enforces, a failed flow is always enforced, a cost_v1
  row is re-scored (140 tests pass).
- **LLM for T5 and any later LLM use: `deepseek-flash`** (the user's decision 2026-09-28): `llm.DEFAULT_MODEL`,
  the self-test, `EngineConfig.model` and `run_evolution.py --model` default to it.
- Experiment workflow (the user's decision 2026-09-28): each experiment first runs as a demo on 225 (direction check,
  results reported), then at full capacity if the effect is good.

### Running
- **E0 demo** (T4 direction check; exploratory, not the pre-registered G0′ test) on 225 GPUs 1-3:
  `e0demo_{spec,eq}_{ibm04,ibm06}`: ibm04 and ibm06 (T3.7's validation designs, kept out of the confirmatory set so
  that the go/no-go decision does not use the held-out designs; the bridge was selected on them, so the demo is
  optimistic for it), 16 programs x 2 seeds, partners none / memetic / repertoire / frozen generator / co-trained
  bridge (T3.7 round-1 checkpoint, sha256 f95bdde8...) / random-direction control; final cost DREAMPlace f1.
  `spec` = the task list's protocol (only the bridge is guarded at f1), `eq` = every partner guarded at f1
  (`--equal-guard`). Ledger campaigns `E0_demo_spec` / `E0_demo_eq` (exploratory).

### Added
- **Same-path control for Track B** (`run_seed_orfs.py`, red line "pairing"): M1's own layout is evaluated through
  the candidates' path at f1 and f2 (rows `<design>.M1replay.f1/.f2`, program `M1_replay`), and
  `report_trackb_dev.py` shows it as the control candidate deltas are paired with. Why: the validity probe on
  ariane133 (`probe_ariane133_place`) replayed ORFS's own macro placement through our import. It converges like
  the base run (global placement 700 iterations, final overflow 0.099; detailed placement succeeds), so the
  import is sound and the non-converging candidates are a property of their layouts. After macro placement the
  macro records of both databases are identical (132 LOCKED macros, same locations and orientations, no halos),
  and synthesis, SDC, floorplan and IO placement are byte-identical. **But Hier-RTLMP leaves all 167,923 standard
  cells PLACED at their cluster positions, while an imported layout leaves them unplaced**: global placement
  starts warm for M1 only (610 vs 700 iterations here). The base run stays the spec's M1 baseline; deltas are
  also reported against the same-path replay.
- **Deterministic failures are reused for identical layouts** (`seed_archive.deterministic_failure`): a named tool
  error of the deterministic ORFS flow (`GRT-0116`, `DPL-0036`, ...) or a timeout is copied with `reused_from`, like a
  successful evaluation already was; crashes and unnamed failures are still evaluated again. Found on ariane133:
  two SA program versions give byte-identical layouts for the same seed (M2.v0.s0 = M2.v1.s0), and the second
  evaluation repeated the same ~1 h DPL-0036 failure. Test with a failing fake evaluator (138 tests pass).
- **`hbv.py run --resume-from RUN`**: continue a stopped run under a new name. Its final archive (else its partial)
  is restored and those files stay in the new run's archives (`hbv stop` writes the final and deletes the partial,
  so `--resume` cannot continue a stopped run, and `--after` inputs are not re-archived). Verified on 224.
- **ISPD2005 Track-A campaign on the spec's tools** (`reports/T2_trackA_ispd_dreamplace.md`; 225 GPU 1, two
  streams, 11.9 h): 8 designs (MMS convention: macros movable), M1 = DREAMPlace mixed-size, f1 = DREAMPlace with the
  macros fixed; 640 program and 336 local-search evaluations. As on IBM, DREAMPlace's M1 is the best layout on every
  design (the best program, M6 on all seven designs with program results, is 6.8-33% worse in J). The program API
  hits memory limits: bigblue2's dense 23,084 x 23,084 macro affinity (4.3 GB) exceeds the 4 GB sandbox, so all 80
  runs crash (M1-only archive); on bigblue4 (8,170 macros) 40 runs fail allocating further M x M arrays.
- **E3 calibration on ISPD2005** (`reports/E3_calibration_trackA_ispd.{md,json}`, 7 designs): Kendall 0.54,
  Spearman 0.72, top-5 recall 0.09, regret 0.026 vs random 0.049 (54 %): **G0 not met** (regret must be <= 25 % of
  random); f0 ranks better than on IBM (Kendall 0.34) but still picks badly on adaptec1 and bigblue1. The f1 guard
  stands.

### Fixed
- `report_trackA.py` repeated every stream's design list once per design in "Exact commands" (each design's
  meta.json holds its stream's whole list); now the designs are joined once. Crashes are named by their exception
  line (`program_crash (rc=1 MemoryError)`) instead of the whole traceback. The committed
  `reports/T2_trackA_ibm_dreamplace.md` had the repeated list; its command lines are corrected (nothing else changes).
- **Algorithm R regenerated the heuristic sources every round** (~4 h of CPU on 225 for 15 IBM designs): each
  round's `train_bridge.py` cached them in its own round directory. The sources do not change between rounds
  (T3.7 step 2: "cached"), so `algorithm_r.py` now passes one cache (`--cache-dir <out>/cache`, the one its promotion
  test already used; both use 8 seeds). In the running `algR_trackA2` (round 1 had already regenerated them), the
  cache directories of rounds 2 and 3 were linked to round 0's before round 2 started (manual, 2026-09-28 11:19;
  visible as ~100 s preparation per design in their train.log).

## [0.13.4] — 2026-09-28 — ORFS failures recorded by name

### Fixed
- **ORFS failures had no name in the records** (red line: every failure recorded by name): the Track-B report fell
  back to "tool returncode 2 (no reason parsed)". `orfs.failure_reason` names the last tool error
  (`GRT-0116 Global routing finished with congestion. ...`) or the step a timeout stopped (`timeout in 5_1_grt`);
  `orfs.run` records it as `failure`, and `report_trackb_dev.py` derives it from the stored log tail for earlier
  records (the running `seedB_orfs5_*` jobs). Tested on the bp_be_top snapshot.

### Observed (Track-B campaign, first hours)
- The 0.13.2 timeout fix worked in production: bp_fe_top's M2.v0.s1 was stopped at 7,200 s in 5_1_grt (log tail
  ends with `do-5_1_grt] Terminated`), recorded as a timeout, and the job's session held one OpenROAD afterwards.
- **T0.3 complete**: ariane133 through detailed routing on ORFS 2024-12 + OpenROAD 676f8451 (`RTLMP_MAX_LEVEL=1`),
  twice, bit-identical at 8 threads: routed WL 7,656,562 um, DRC 0, setup WNS -0.015 ns, hold +0.01 ns, 0.345 W.
- bp_be_top's first three SA layouts fail ORFS's default global route with GRT-0116 (overflow 13, 2,194 and 389,781
  after the extra iterations; the base flow routes cleanly): unroutable at f1, counted as +inf.

## [0.13.3] — 2026-09-28 — bridge inference runs on the model's device (T3.7 on the GPU)

### Fixed
- **T3.7 stopped at its first validation on the GPU** (`algR_trackA`, 225, after 4.5 h of CPU data preparation;
  no training step was lost). `bridge.sample.refine` and `bridge_endpoints` defaulted to `device="cpu"`: the
  training validation, and also Algorithm R's promotion test, RLCE and the evolution driver (none of which pass a
  device), put the graph on the CPU while the model was on CUDA. Local runs were CPU-only, so this path had never
  run on a GPU. Inference now runs on the model's device by default. New test `test_refine_follows_model_device`
  (Mac GPU backend MPS, CUDA on the servers): fails before the fix, passes after (136 tests pass). The rerun
  (`algR_trackA2`) restores the cached sources and pairs with `--after algR_trackA`.

## [0.13.2] — 2026-09-28 — ORFS timeouts kill the whole flow; hbv stop/resume fixes; Track-B campaign restarted

### Fixed
- **An ORFS timeout left the flow running (red line A.2).** `orfs.run` killed only the top `make` on a timeout, but
  ORFS runs every step in a recursive sub-make (make -> sh -> time -> openroad | tee). The step would have kept
  running as an orphan while the driver started the next candidate on the same 8-thread budget; plain
  `subprocess.run` returns at once and leaves the grandchild alive. Caught before any candidate timed out:
  bp_fe_top's and bp_be_top's M2.v0.s1 (SA seed 1, macros scattered through the core) spent > 1.5 h in FastRoute's
  "Extra Run for hard benchmark" at 5_1_grt (base: 1:46 / 4:44). New `heurbridge.tools.run_group`: the child runs
  in its own process group, and a timeout or any exception kills the whole group (SIGTERM, 10 s, SIGKILL); the
  output so far is kept (an ORFS timeout record now carries its log tail). Used for the ORFS runs, signoff and M1
  extraction, the mini-flow, the dev f1 and DREAMPlace. `tests/test_tools.py` (135 tests pass).
- **`hbv.py stop`** signals the job's whole session in a single pass, so tool process groups inside it are
  reached too, and the job's final archiving, which starts afterwards, is not. Verified on 224: nothing left in
  the session, final archive written, workspace wiped.
- **`hbv.py run --resume` lost the restored files.** They keep their mtimes (make needs them), so they predated
  the workspace marker and were never archived again; the resumed job's finish then deleted the partial that
  held them. The restored members are now listed and archived with the job's own files. Verified on 224 with a
  simulated crash (SIGKILL: partial kept) and a resume: the final archive holds the restored and the new files.
- ORFS's `final_report.tcl` saves images through `gui::show` whenever the `save_image` proc exists; our OpenROAD
  build has no GUI, so 6_report failed after every metric was written (bp_fe_top on 676f8451: metrics identical to
  the package's -- routed WL 2,376,571 um, setup WNS -0.077 ns). `scripts/server/patch_orfs.py` also requires
  `gui::show` there (applied to the checkout on 224); the metrics are untouched. bp_fe_top / bp_be_top restarted
  (`seedB_orfs3_*`).
- **ariane133's tool-native macro placement does not converge at 8 threads** -- with the package (a008522d8) and with
  the ORFS pin built from source (676f8451) alike: `MPL-0040 Failed on cluster (i_cache_subsystem/i_nbdcache)
  _glue_logic` after 14-15 minutes. Hier-RTLMP's annealing depends on the thread count (ORFS runs with all cores;
  red line A.2 caps us at 8), and upstream ORFS later changed ariane133's settings repeatedly for MPL convergence
  ("workaround on nangate45/ariane due to mpl issues" 2025-12, "decrease macros halos to ease MPL convergence"
  2026-01, "Use bigger macro clusters" 2026-04). **Deviation, ariane133 only:** M1 is still ORFS's own
  rtl_macro_placer, with those later upstream settings (max level 1, 10-30 macros and 8k-80k instances per
  cluster, halo 8 x 8) on the 2024-12 flow and floorplan; `run_seed_orfs.py --make-var KEY=VALUE` passes such
  overrides to every run of a design (recorded in meta.json; P_M's spacing follows the halo).
- **ariane133's deviation narrowed to one setting, `RTLMP_MAX_LEVEL=1`.** With halo 8 x 8 its M1 converged (4:51)
  but the 2024-12 power grid failed (`PDN-0179 Unable to repair all channels`: two VDD channels on metal4, 6 um tall,
  between the core's bottom edge and macros placed 6 um from it); upstream's smaller halo (fa3401136d) came with a
  utilization-based floorplan (355cd0439d) that the 2024-12 configuration does not have. The job
  (`seedB_orfs3_ariane133`) was stopped in its second base run (same deterministic failure); logs fetched. Probe
  (`scripts/orfs_probe.py`, 224, 8 threads, 2024-12 halo 10 x 10), both variants converge and pass the PDN:
  max level 1 with upstream's 2026-04 clusters (10-30 macros, 8k-80k instances) in 4:48, and **max level 1 alone**
  (the 2024-12 clusters, 4-16 macros, 5k-30k instances) in 6:03; both leave the 132 macros >= 9.3 um from the core
  edge with gaps >= 19.9 um (the PDN-0110 via warnings also occur in unmodified bp_fe_top). The smaller deviation is
  kept: only `RTLMP_MAX_LEVEL=1`, the level limit of upstream's MPL workaround for this design (98b961bb3c,
  2025-12-05); clusters, halo, channel and floorplan are the 2024-12 values. Restarted as `seedB_orfs4_ariane133`.

### Added
- `scripts/orfs_probe.py`: runs ORFS up to one stage (default the floorplan, which ends with the PDN) for several
  design-config overrides. The first variant synthesizes; the others reuse its synthesis. Output: one JSON line per
  variant with the return code, step times, MPL/PDN/PPL/GPL messages and the macro geometry (distance to the core
  edge, smallest facing gap).

### Running
- ISPD2005 Track-A campaign (T1.7/T2.7 on the spec tools) on 225 GPU 1: `seedA_ispd_s1` (adaptec1, bigblue1,
  bigblue4) and `seedA_ispd_s2` (adaptec2-4, bigblue2, bigblue3); M1 = DREAMPlace mixed-size, f1 = DREAMPlace with the
  macros fixed, MMS convention (macros movable).
- ORFS Track-B campaign restarted with this code as `seedB_orfs5_{bp_fe_top,bp_be_top,swerv_wrapper,ariane133,
  ariane136}` (`seedB_orfs3_*`, `seedB_orfs2_*`, `seedB_orfs4_ariane133` stopped: the three in their base runs lost
  1-5 h). The vault now keeps the base variant's synthesis and pre-macro floorplan (exclude pattern in
  `docs/SERVER_RUNBOOK.md`): a resumed job seeds candidates without re-synthesis, and later f2 / E0 jobs can start
  from them with `--after`.

## [0.13.1] — 2026-09-27 — OpenROAD 676f8451 from source (ORFS pin); Track-A campaign and E3 on the spec tools

### Added
- **Track-A campaign on the spec's tools** (`reports/T2_trackA_ibm_dreamplace.md`; 225 GPU 1, two streams): 17 IBM
  designs, M1 = DREAMPlace mixed-size, f1 = DREAMPlace with the macros fixed; 1,360 program and 809 local-search
  evaluations. Against this strong M1 the programs win on two designs only -- ibm02 (J 0.164; its M1 is anomalous:
  HPWL 12.2 M, RUDY OF 5.4 %) and ibm06 (J 0.4251, 9 distinct layouts); elsewhere M1 stays the best elite. 55 M2
  timeouts on designs with >= 614 macros. `report_trackA.py --note`.
- **E3 calibration on the spec's f1** (`reports/E3_calibration_trackA_dreamplace.md`, one row per distinct layout,
  17 designs): f0 (the bridge guard's surrogate J0) vs DREAMPlace f1 -- mean Spearman 0.44, Kendall 0.34, top-5
  recall 0.01, decision regret 1.53 vs 0.18 for a random pick; good on some designs (ibm01 Kendall 0.75, ibm12 0.71),
  anti-correlated on others (ibm13 -0.34, ibm06 -0.13), with catastrophic picks on ibm06 and ibm09. **G0 not met**:
  f0 must not make macro-stage decisions; the f1 guard and fitness stand (as in the development study).
- The HB-GP development campaign and the DREAMPlace campaign disagree on which programs help (HB-GP's baseline was
  the benchmark placement, not a placer's): the spec baseline is the stronger reference.

### Changed
- **Track B runs OpenROAD 676f8451 built from source** (`scripts/server/build_openroad.sh`, launcher
  `scripts/server/openroad_676.sh`; version string `676f8451bb-src`): the commit ORFS 8ae3ae36 pins. The package
  (a008522d8) is 8 commits older and lacks mpl2 PR #6335 ("cluster placement for stdcell-only levels"): ORFS's
  own macro placement of ariane133 failed there after 15 minutes with `MPL-0040 Failed on cluster
  (i_cache_subsystem/i_nbdcache)_glue_logic`, so the T0.3 Track-B condition (ariane133 to detailed routing) could
  not be met with it. Built without root against conda-forge CMake 3.29 / gcc 11.4 / Boost 1.86 / SWIG 4.2.1 /
  spdlog 1.15.3 / Tcl 8.6.13 + tclreadline 2.3.8 / OR-Tools 9.6 (the installer's 9.11 is a GitHub binary: not
  downloaded without asking) / LEMON 1.3.1 / Eigen 3.4, CUDD 3.0.0 from source; GUI and tests off. Every required
  command is present (probe), the Python API works. Build fixes on the way: tclreadline is needed for Main.cc,
  readline must be linked explicitly, and a stale CMake cache hides OR-Tools' pkg-config targets (fresh configure).
  The ORFS campaign restarted on it (`seedB_orfs2_*`); the `seedB_orfs_*` runs on the package are superseded.

### Running
- T3.7 Algorithm R on 225 GPU 0 (`algR_trackA`): the two stream archives merged (139 entries); train 13 IBM designs,
  validate ibm04 / ibm06 (ibm08 / ibm12 held back for E0), pretrained warm start, f1 guard and promotion test with
  DREAMPlace.

## [0.13.0] — 2026-09-27 — Track B on the real ORFS flow (2024-12), T3.4 done

### Changed — Track B runs the real ORFS flow
- The mini-flow could not reproduce ORFS's result on this OpenROAD build: every alignment step fixed one gap and
  exposed the next (floorplan areas, RTLMP arguments, synthesis order, buffer removal, density), and ORFS's
  timing-driven placement with kept resizer changes diverged in the mini-flow even after `remove_buffers`
  (bp_fe_top: +19,505 um^2 of buffers, HPWL 2.4e9 -> 3e10, detailed placement failed). Its baselines were also far
  from ORFS's (bp_fe_top setup WNS -1.9 ns vs ORFS's CI bound -0.22 ns).
- **ORFS at 2024-12-13 (8ae3ae36)** pins OpenROAD 676f8451 (our package a008522d8 is from 2024-12-11) and
  **Yosys 0.48** (installed from conda-forge on 224, the same commit aaa53474); a sparse checkout
  (`third_party/ORFS-2024-12`: scripts, util, platforms/nangate45 + common, the five designs) is on 224. The full
  flow on bp_fe_top (M1 = ORFS's own rtl_macro_placer) runs to 6_report in 15 minutes: setup WNS -0.077 ns, TNS
  -0.34 ns, hold WNS -0.05 ns (462 hold-violating endpoints), power 0.165 W, 2,376,571 um routed, 326,997 vias,
  DRC 0, 0 antenna diodes, instance area 235,187 um^2 (within ORFS's CI bounds for WNS, area and antennas).
- `eval/orfs.py`: ORFS reports its own directories (`make print-%`; directories follow DESIGN_NICKNAME, e.g.
  bp_fe_top -> bp_fe); `WORK_HOME` keeps every output in the job's encrypted workspace; OPENROAD_EXE / YOSYS_EXE;
  f2 stops at `6_report.log` (the GDS needs KLayout, which the servers lack and the metrics do not need); a
  candidate variant starts from the base variant's synthesis chain and pre-macro floorplan (timestamps kept, so
  make begins at 2_3); metrics are merged only up to the requested stage (an f1 record never reads finish keys);
  hold WNS comes from the stage report (`report_checks -path_delay min`, 0.01 ns resolution: ORFS 2024-12 has no
  hold-slack metric); global-route power (`globalroute__power__total`); M1 extracted from 2_3_floorplan_macro.odb.
  `place_macro -exact` is no longer written by default (this build has no such flag).
- `scripts/run_seed_orfs.py`: T1.7 baselines (the unmodified flow, repeated), T2.7 seeding at f1 (5_1_grt) and f2
  verification (6_report) with `OrfsEvaluator`; variant databases are deleted after each evaluation (logs and
  reports, which hold every metric, stay).
- The mini-flow (`eval/miniflow.py`, `run_seed_miniflow.py`) remains for local development and as the fallback.
- **Driver test on bp_fe_top** (`orfs_drv_test`): base flow 825 s; two programs at f1 as seeded variants (each
  starts at 2_3: no synthesis or floorplan rerun; 6-7 minutes); M5.v0 fails the f1 setup gate (WNS -0.071 ns vs
  M1's -0.005 ns), M2.v0 passes (J 0.916) and at f2 beats ORFS's own M1 with every gate passed: J 0.937 (setup WNS
  -0.040 vs -0.077 ns, TNS -0.23 vs -0.34 ns, hold +0.01 vs -0.05 ns, routed WL 2,097,257 vs 2,376,571 um, DRC 0).
- **Layout reuse in seeding** (`pipeline/seed_archive._eval`): a layout the same evaluator already evaluated
  successfully is not evaluated again (seed-independent programs repeat their layout for every seed; all
  evaluators are deterministic) -- the row is copied with `reused_from`; failures are always repeated.

### Running
- ORFS Track-B campaign on 224: `seedB_orfs_{bp_fe_top,bp_be_top,swerv_wrapper,ariane133,ariane136}` (base x2, 16
  programs x 5 seeds + local search at f1, top 10 + spread 10 at f2).

## [0.12.4] — 2026-09-27 — Track-B placement steps as ORFS 3_3-3_5; T3.4 pretraining done

### Fixed
- **Track-B placement steps now follow ORFS 3_3-3_5** (`eval/miniflow._place_steps`): `remove_buffers` before
  timing-driven global placement (GPL_TIMING_DRIVEN=1) and `buffer_ports` before it (DONT_BUFFER_PORTS=0; the
  mini-flow buffered after placement), `repair_design` only at 3_4 (ENABLE_PLACE_REPAIR_TIMING=0), and after
  detailed placement `improve_placement` (ENABLE_DPO=1) and `optimize_mirroring`, each only when the build has it
  (logged). `repair_tie_fanout` moved to the floorplan (ORFS 2_1). ariane133's f1 had stopped with GPL-0302: its
  cells kept the synthesis buffers (31.65 % of the free core against the platform density 0.30).
- Track-B design ids are the ORFS design names: ariane133 and ariane136 share the top module `ariane` and would
  have collided in run directories and merged archives. Hier-RTLMP reports go to the run's `rtlmp/` directory.
- Baselines on the aligned flow (`tb5_*`, superseded by `tb6_*` for the placement change): bp_fe_top, bp_be_top and
  swerv_wrapper completed f1 and two bit-identical f2 runs with DRC 0 (setup WNS -1.89 / -2.02 / -0.94 ns);
  ariane136's M1 (no RTLMP limits in its config) exceeded the 7,200 s step limit — retried once in `tb6_*`; if it
  times out again it cannot run within red line A.2 on this build and is excluded by name.

### Added
- **T3.4 pretraining done** (`reports/T3_pretrain_small.md`): 200k steps, batch 64, 3.47 h on 225 GPU 0 (0.048 s/step
  on ~200-object circuits, 0.106 on ~1,000); final loss 0.089 (flow term 0.077, overlap 0.127); checkpoint sha256
  6a5ee4b8...; `scripts/report_pretrain.py`.
- ORFS's CI reference bounds for the five designs (upstream rules-base.json before 2026-09-22) show ORFS's timing
  closure is far better than the mini-flow's (signoff setup WNS about -0.2 to -0.6 ns vs -0.9 to -2.0 ns here): the
  mini-flow repairs timing only in its f2 `rt` stage, not at floorplan / placement / CTS / global routing as ORFS
  does. Recorded as a deviation; J is relative to the same flow's baseline.

## [0.12.3] — 2026-09-27 — ORFS floorplan areas and RTLMP arguments for Track B

### Fixed
- **Track-B floorplan and M1 were not ORFS's for three designs** (`eval/miniflow.py`): ariane136, bp_be_top and
  swerv_wrapper give `DIE_AREA`/`CORE_AREA`, which ORFS uses (floorplan.tcl); the mini-flow always used
  `-utilization` (bp_be_top: core 498,584 um^2 instead of 529,418 um^2). And ORFS calls `rtl_macro_placer` with the
  design's `RTLMP_*` arguments (ariane133: max level 1, 10-30 macros and 8k-80k instances per cluster) and always
  `-target_util <placement density>` (macro_place_util.tcl); the M1 passed only the halo — for ariane133 that also
  meant a much deeper search (M1 still running after 40 minutes). Now the floorplan method follows the design
  (both methods given is an error, as in ORFS), and M1 passes the RTLMP arguments and `-target_util` (the density of
  `place_density_with_lb_addon`, shared with global placement); flags the build lacks are dropped and logged.
  All five Track-B baselines are recomputed (`tb5_*`); the `tb4_*` and `seedB_bp_fe_top` runs are superseded.

### Known deviations from ORFS (kept, documented)
- No floorplan-stage timing repair (ORFS 2026: `repair_timing_helper -setup` at floorplan unless
  `REMOVE_ABC_BUFFERS`), `repair_tie_fanout` after global placement (ORFS: at floorplan), and swerv_wrapper's
  `SWAP_ARITH_OPERATORS` (hierarchical arithmetic swapping) is not applied. The spec defines f1/f2 by their steps
  (T1.4/T1.5); these ORFS-version-specific optimizations are outside them. The ORFS checkout is 2026-09 while the
  OpenROAD build is 2024-12, so "ORFS behaviour" means the 2026 scripts' logic applied to the 2024 tools.

## [0.12.2] — 2026-09-27 — ORFS synthesis order, Track-A tools for T3.7/T4, HB-GP campaign report

### Fixed
- **Track-B synthesis order** (`eval/miniflow.synth_script`): `hilomap` ran before `setundef -zero`, so the
  constants that `setundef` creates never became tie cells. bp_be_top's netlist kept wide constant buses (128'b0,
  64'b0, 6'b0); OpenROAD links them through a GROUND-typed `zero_` net that detailed routing refuses
  (DRT-0305 in both f2 runs, while f1 passed). Now ORFS synth.tcl's order after mapping: `opt`, `setundef -zero`,
  `abc`, `splitnets`, `opt_clean -purge`, `hilomap`, `insbuf -buf BUF_X1 A Z` (SYNTH_INSBUF=1): no constants and no
  port assigns remain (checked on bp_be_top and bp_fe_top). Every netlist changes, so the five Track-B baselines
  are recomputed from synthesis (`tb4_*`); the `tb3_*` results (bp_fe_top f1/f2, bp_be_top f1) are superseded.

### Added
- `--final dreamplace` for `algorithm_r.py` (T3.7 guard and promotion test) and `run_e0.py` (T4): the spec's
  Track-A f1, scored against the M1 baseline of the seeding campaign given by `--runs` (the archive's J scale);
  `hbgp` stays the development default. `evaluators.track_a_final` selects the evaluator.
- `scripts/report_trackA.py`: Track-A campaign report (per design: M1 time and P_M displacement, baseline of 3
  seeds, program evaluations and failures by name, layouts below the baseline, local search, archive best);
  `--node` / `--code` for runs made before the host and code-version records.
- `scripts/merge_archives.py`: merges the archives of parallel streams (disjoint designs) by replaying each
  input's rows in id order through `Archive.insert` (checked: the 17-design HB-GP archive replays to an identical
  top-k on every design, 155/155 rows).
- `reports/T2_trackA_ibm_hbgp_dev.md` — the HB-GP development campaign on 224 (17 IBM designs, 1,360 program and
  809 local-search evaluations; baseline = the benchmark macro positions): programs beat that baseline on 8
  designs, mostly where its placement is congested (ibm18: RUDY OF 76 %, best J 0.12 vs 0.45); 68 program
  timeouts (the sandbox's 60 s CPU limit) on the larger designs. Development only: the spec's Track-A campaign
  (DREAMPlace, M1 baseline) is running.

### Verified
- M1 is thread-count invariant on bp_fe_top: the 8-thread Hier-RTLMP placement is identical to the single-threaded
  one (all 11 macros) and f1 on it is identical (GR WL 1,762,903 um, setup WNS -2.234 ns, TNS -81.1 ns); the
  0.12.1 thread change aligns M1 with ORFS and speeds it up, and the earlier bp_fe_top results stand.

## [0.12.1] — 2026-09-27 — Track-A seeding with DREAMPlace, ORFS-faithful M1 and synthesis

### Fixed
- **M1 (Hier-RTLMP) ran single-threaded** (`eval/miniflow.m1_script` had no `set_thread_count`): ORFS runs every
  stage as `openroad -threads $(NUM_CORES)`, and Hier-RTLMP anneals in parallel with the thread count, so the M1
  layouts of today (bp_fe_top, bp_be_top) were not ORFS's configuration, and ariane133's M1 had run for over an
  hour. M1 now uses EDA_THREADS (8); the Track-B baselines are recomputed from M1 on (`tb3_*`). bp_fe_top's f2
  pair on the single-threaded M1 was bit-identical across runs and across the thread cap (DRC 0, setup WNS
  -1.905 ns, TNS -54.9 ns, hold +0.096 ns, 590 s each) — kept as a record of determinism, superseded as baseline.
- **swerv_wrapper did not synthesize**: its RTL instantiates `OPENROAD_CLKGATE`, which ORFS resolves with the
  platform's `CLKGATE_MAP_FILE`. The synthesis script now reads it (and the standard cells as black boxes) for RTL
  that uses the clock gate, and maps latches with the platform's `LATCH_MAP_FILE` (as ORFS). Reading the
  standard-cell library for every design would change other netlists (bp_fe_top: 362 lines, output ports driven
  through assigns), so it is conditional; bp_fe_top's netlist is bit-identical with and without the latch map and
  clock-gate file (checked on 224).
- Synthesis, floorplan and M1 failures were noticed only at the next step: each step must now produce its file,
  or `run_seed_miniflow.py` stops with the step's first errors.
- DREAMPlace's parameter file was passed as a relative path while Placer.py runs in its install directory.

### Added
- Track A per spec: `run_seed_archive.py --evaluator dreamplace` — M1 = DREAMPlace mixed-size placement (macro
  placement and macro legalization switch on for movable macros; cached per design as `m1.npz`; P_M checks
  legality and its displacement is recorded), baseline = f1 on M1 with DREAMPlace seeds 0-2 (median), every
  program evaluated with DREAMPlace (macros FIXED). A design whose M1 or baseline fails is reported by name and
  the campaign continues; the job still exits non-zero. On 225 (ibm01, 2 programs, 88 s): M1 26.5 s, P_M mean
  displacement 0.0107 of the core; baseline HPWL 2,484,943 / 2,490,825 / 2,481,027 (-3 % vs the benchmark
  macro positions); M2.v0 J 0.525, M5.v0 J 0.533 against the baseline's 0.45 — the programs start far behind
  DREAMPlace's own macro placement.
- The HA-PR harness (`metrics_schema.py` sha256 4356a854..., identical on 224 and the Mac) reaches 225 as an
  encrypted data bundle (`--data eda_harness:eda`, `HB_EDA_DIR`): the NAS copy there predates `metrics_schema.py`.
- DREAMPlace evaluations delete their bookshelf copy and output after reading (workspaces are in RAM).

### Running
- Track A (spec f1) on 225 GPU 1: `seedA_dp_s1` / `seedA_dp_s2` — 17 IBM designs (ibm05 has no macros).
- Track B on 224: `tb3_{ariane133,bp_fe_top,bp_be_top,swerv_wrapper}` — M1 (8 threads) -> f1 -> f2 x 2.

## [0.12.0] — 2026-09-27 — DREAMPlace Track-A f1 on 225, Track B through detailed routing on 224

### Fixed
- **Red line A.2 exceeded on 224 (OpenROAD threads).** `set_thread_count 8` does not bound OpenMP in the 2024-12
  build: one f2 run (bp_fe_top, second determinism repeat) was seen with 73 threads and ~59 cores busy; the
  earlier Track-B runs of today with this build (bp_fe_top f1 twice, f2 once; together about 25 minutes of run
  time) were launched the same way and may have exceeded 8 cores in their OpenMP phases. The job was stopped
  on sight; `openroad_deb.sh`, `trackb.sh` and native `run_tool` calls now set `OMP_NUM_THREADS=EDA_THREADS` (8),
  and the f2 baseline pair is rerun under the cap (results depend on the thread count).
- A truncated `m1_macros.tcl` would have produced a partial M1 baseline silently: both Track-B drivers now
  require it to place every macro of the design.
- **Placement density for bp_be_top / swerv_wrapper** (`eval/miniflow.py`): their ORFS configs set
  `PLACE_DENSITY_LB_ADDON`, for which ORFS computes the density (`place_density_with_lb_addon`: uniform lower bound
  + addon x remainder + 0.01); the mini-flow used the platform's 0.30, below bp_be_top's 31 % utilization
  (GPL-0302). Now the ORFS rule, computed in the run and logged (`HB_PLACE_DENSITY`); ariane133 / bp_fe_top (0.30)
  and ariane136 (0.35) are unchanged.
- The local ORFS checkout is sparse and lacked `designs/nangate45/swerv/` (swerv_wrapper's `macros.v`): added to
  the sparse set and to the copy on 224; `from_orfs` now fails when a `VERILOG_FILES` entry is missing.
- `run_seed_miniflow.py` carried on after a failed f1 baseline (all metrics null): it now stops with the named
  failure, like the f2 driver.
- **Track-B global placement diverged on OpenROAD 2024-12** (`eval/miniflow.py`): builds with
  `-keep_resize_below_overflow` (default 0.3) keep the resizer's buffers inside timing-driven global placement;
  on bp_fe_top (M1) that step added 21,726 um^2 of buffers (+49 % cell area) at iteration 336, HPWL went from
  2.4e9 to 3e10, the overflow never fell below 0.28 in 5,000 iterations and detailed placement failed (DPL-0036).
  The flow now passes `-keep_resize_below_overflow 0` when the build has the flag (every timing-driven repair
  virtual, the only behaviour of the local build b16bda7e; electrical repair stays in the explicit ORFS 3_4
  step) and logs the arguments (`HB_GPL_ARGS`). bp_fe_top M1 at f1 on 224 then converges at iteration 420:
  GR WL 1,762,903 um, overflow 0, setup WNS -2.234 ns, TNS -81.1 ns, hold +0.093 ns, power 0.158 W
  (local b16bda7e, 6 threads: 1,832,439 / 0 / -2.336 / -113.5 / +0.096 / 0.151).

### Added
- `heurbridge/eval/dreamplace.py` — the Track-A f1 of the spec (T1.4: DREAMPlace GP + LG with the macros FIXED,
  then f0 RUDY / HPWL). DREAMPlace's bookshelf reader ignores orientations, and our programs rotate and flip
  macros, so each layout is written as a bookshelf copy with orientations baked in (swapped footprints,
  transformed pin offsets, all N; macros `/FIXED`); `test_dreamplace_io` checks identical absolute pin
  positions for all eight orientations on ibm01. A run whose macros moved is a named failure (`macros_moved`).
- `scripts/server/build_dreamplace.sh` — DREAMPlace 4.3.1 with CUDA on 225 without root (conda CMake 3.26, gcc 11,
  CUDA 11.8 nvcc, Boost, tclsh; torch's C++ ABI; sm_86; the driver stub found via `CMAKE_LIBRARY_PATH`). The public
  source with submodules is copied from the Mac (225 cannot reach GitHub). Installed copy: `np.string_` ->
  `np.bytes_` (NumPy 2; the only NumPy-1-only name, 6 uses in PlaceDB.py).
- `DreamplaceEvaluator` (Track-A f1, same record fields as HB-GP) and `scripts/server/dp_smoke.py`: **DP_SMOKE_PASS**
  on ibm01 (225 GPU 1): benchmark macro layout HPWL 2,568,480 (HB-GP 2,655,909: -3.3 %), GP overflow 0.071, macros
  unmoved, 10.4 s per run, bit-identical in two runs; all-orientations layout runs as well (HPWL 2,812,144).
  The ICCAD04 `.wts` holds node weights that DREAMPlace would read as net weights (assertion): the copy writes
  net weights from the design instead.

## [0.11.1] — 2026-09-27 — OpenROAD 2024-12 on 224, GPU env on 225, T3.4 pretraining started

### Fixed
- **bf16 autocast crash in the bridge model** (`bridge/model.py`): the attention output (bf16 under autocast) was
  `index_add`-ed into the fp32 residual stream — every CUDA training run (T3.4 pretraining, T3.7) would have
  stopped at the first step. Never exercised before: all earlier training ran on CPUs with autocast off. Found by
  the GPU smoke test on 225; `test_bf16_autocast_step` runs the same mixed-dtype path under CPU autocast (fails
  without the fix).
- **Unintended write into the HA-PR tree on 224**: importing `eda/harness/metrics_schema.py` with Python 3.11 left
  `eda/harness/__pycache__/metrics_schema.cpython-311.pyc` (12 KB; the only file of ours in that tree — nothing
  else in it changed). The harness shim now imports with `sys.dont_write_bytecode`, and hbv jobs export
  `PYTHONDONTWRITEBYTECODE=1`. The stray file is to be removed once the job that is still importing it ends.
- **Server runs recorded `git_sha: unknown`** (workspaces are shipped without `.git`): `hbv.py push-code` adds a
  `CODE_VERSION` stamp (commit, dirty flag, archive name) and `meta.git_sha()` falls back to it; `meta.json` also
  records `code_archive`.
- `run_seed_miniflow.py` assumed `runs/miniflow/<design>/` existed (true only on the Mac); `run_tool` creates the
  script's directory. `run_f2_miniflow.py` accepts a baseline-only campaign (no `evals.jsonl`).

### Added
- **OpenROAD 2024-12 on 224 without root** (T0.3; download approved by the user): `scripts/server/install_openroad_deb.sh`
  unpacks the Precision Innovations package `openroad_2.0-17598-ga008522d8_amd64-ubuntu-20.04.deb`
  (sha256 `c24ca8ff…0535dfdb`, checked) and its two missing dependencies; `ldd` finds every library. Probe: every
  required command and flag, including `rtl_macro_placer`, `place_macro`, `global_route -allow_congestion` and the
  Python API (`reports/env/openroad_probe_224_deb_2024-12_a008522d8.txt`). `scripts/server/openroad_deb.sh` sets
  the package's library path for the binary only.
- `heurbridge/tools.py`: one place resolving the EDA binaries — `HB_OPENROAD` / `HB_YOSYS` select native runs (the
  servers), otherwise the local OpenLane container; `EDA_THREADS` sets the evaluators' thread count; run metadata
  records the actual tool versions (`tools.describe()`) instead of a hard-coded build. Native runs call the binary
  directly (no login shell: the shared account's profile cannot choose the tool).
- `scripts/server/trackb.sh`: Track-B jobs on 224 (native OpenROAD 2024-12, Yosys 0.38+92, ORFS platform files
  linked read only, `EDA_THREADS=8`).
- **225 set up for GPU work** (approved by the user): env `/tmp/.hbenv/hb` (torch 2.6.0+cu118 — Ubuntu 18.04's glibc
  2.27 excludes later wheels —, PyG 2.8.0.post1), GPU smoke test PASS on GPU 0 (0.119 s/step, `reports/env/gpu_smoke_225.txt`).
  `setup_env.sh` bootstraps micromamba itself (`HB_TOOLS`), `TORCH_SPEC` pins a torch version; `t0_server.sh t05`
  takes `HB_ENV` / `SMOKE_GPU` / `HOST_TAG`, `t03deb` probes the package.
- `pretrain_bridge.py --resume`: continues from the checkpoint (model, EMA, optimizer, step; the data streams are
  reseeded from the step — valid, not bit-identical to an uninterrupted run); checkpoints are written atomically;
  `meta.json` records the configuration and code version. Tested on a 4 + 2-step CPU run.

### Running
- T3.4 pretraining on 225 GPU 0 (`pretrain_small`, 200k steps, batch 64): 0.047 s/step in stage 1, loss 0.249 ->
  0.130 over the first 4k steps.
- Track B on 224: `ariane133` and `bp_fe_top` baselines (synthesis -> floorplan -> M1 `rtl_macro_placer` -> f1) with
  the 2024-12 OpenROAD; f2 (detailed route) follows — the remaining T0.3 condition for Track B.
- Track-A seeding `seedA_ibm`: 16 of 17 designs done (ibm18 running).

## [0.11.0] — 2026-09-27 — server access, encrypted workflow on the shared lab account, T0 on 224

### Added
- `scripts/hbv.py` — encrypted workspace for the shared lab login: the server holds ciphertext only
  (`vault/{code,data,runs}/*.tgz.enc`, AES-256-CBC + PBKDF2-SHA256, same format on OpenSSL 3 and 1.1.1 — tested
  both ways); the key stays on the Mac and reaches a job only through its SSH session's stdin (never a server
  file, command line or environment variable; with `ptrace_scope=1` other logins cannot read job memory); jobs run
  detached in a RAM workspace, encrypt what they created back into the vault at exit (and every `--snapshot`
  seconds) and wipe the workspace. Code pushes contain tracked / non-ignored files only. Verified on 224: no key
  in any readable `/proc/*/cmdline` or `/proc/*/environ` during a job; vault ciphertext only; workspace wiped.
- `scripts/server/t0_server.sh` — T0.1 (on a temporary copy of `eda/`, never written), T0.3, T0.5, T0.6 as jobs.
- LLM client: `DEEPSEEK_API_KEY_FILE` (a KEY=VALUE key file read by the client; `API_KEY` accepted), so the key
  never enters a process environment on the shared account.
- `ENV_REPORT.md` s.6: T0 on 224 — T0.1 PASS (same numbers as locally), benchmarks uploaded and all 260 files
  verified, DeepSeek self-test PASS (models `deepseek-flash`, `deepseek-v4-pro`), env `hb` built (torch 2.7.1+cu118,
  PyG 2.8.0); CUDA cannot initialize on 224 or 227 (faulty GPU 0 breaks the driver), 225 works (needs approval);
  conda OpenROAD builds lack `rtl_macro_placer` / `place_macro`.

### Changed
- Removed `scripts/sync_to_server.sh` (plaintext copies on a shared account; it also did not exclude every
  unpublished document). `docs/SERVER_RUNBOOK.md` rewritten for the encrypted workflow.
- `.gitignore`: local lab notes (`LAB_*`: host, account, ports, people) are never published.
- `setup_env.sh`: the CUDA version is read per device (plain `nvidia-smi` aborts on the faulty GPU 0 and the
  script silently chose CPU PyTorch); driver CUDA 11.4-11.8 maps to the cu118 wheels.
- `install_openroad.sh`: `OPENROAD_SPEC`, `CHANNELS`, `EXTRA_SPECS` (the unpinned solve picks litex-hub's 2022 build;
  the 2024 build needs Anaconda `main` before conda-forge with strict priority).
- hbv jobs put tool caches (conda, pip, XDG, matplotlib, torch) on a local disk: the account's home is on a NAS
  whose quota is exhausted (the first install failed with EDQUOT).
- Lemma-3 property test checks monotonicity within each fidelity (the default query follows the highest fidelity
  present); it failed on a generated sequence after the tiered archive of 0.10.7.

## [0.10.7] — 2026-09-26 — fidelity-tiered archive, Track-B f2 verification, deterministic E0

### Fixed
- **Elite archive ranked J across fidelities** (`archive/store.py`): J at f1 and at f2 have different baselines
  and terms, so the f2-verified bp_fe_top layouts (J 0.96-0.99 at f2) were rejected against a top-5 of f1
  entries (J 0.86-0.88 at f1), and the same layout could not be stored at two fidelities (unique key without
  fidelity). Admission now compares within the candidate's fidelity; `topk` / `conditional` / `best_J` use the
  highest fidelity present unless `fidelity=` is given; the snapshot hashes each fidelity's top-k; the unique
  key includes fidelity, and existing archives are migrated in place on open (rows, ids and blobs unchanged;
  checked on both dev archives). Test for separate tiers and cross-fidelity duplicates.

### Added
- **Track-B dev f2 verification** (`reports/E3_calibration_dev_bp_fe_top_f1f2.md`): M1 at f2 twice
  (bit-identical at 6 threads: setup WNS -1.794 ns, TNS -62.0 ns, hold +0.095 ns, DRC 0, 1,618,921 um,
  264,712 vias) and 14 layouts (the f1 top 8 by J before the gates + 6 spread): 14/14 completed, DRC 0 on all.
  f1 -> f2 rank agreement: Kendall 0.50, Spearman 0.60, top-5 recall 0.6. Gate agreement is poor: of 12
  layouts passing the f1 gates, 10 fail at f2 (8 setup, 2 hold); of 2 failing at f1, one passes at f2. Two
  layouts pass every f2 gate and beat M1: M4.v2 (J 0.959; gated out at f1) and M3.v0 (0.989). The best f2 J
  before the gates (M3.v2, 0.9445, better setup WNS than M1) fails only on hold: +0.074 ns against M1's
  +0.095 ns (met, but more than 0.02 ns below the baseline — the frozen HA-PR rule, METRIC_CONVENTIONS s.2).
  The f2-verified layouts and M1 at f2 form the f2 tier of the dev archive.
- `reports/E0_partner_ablation_dev_deterministic.md` (ledger E0_dev#4) — the dev E0 with every control and the
  reproducible evaluator (single-threaded HB-GP, all partners in one process, 64 paired cases on held-out ibm04 /
  ibm06, bridge guard at f1, equal f1 guard): G0' criterion met (co-trained vs memetic p = 8.6e-5, vs repertoire
  p = 0.0061; not "promoted" in the ledger because the 4th dev test's alpha_j is 0.0031). Learned-transport check
  inconclusive: co-trained vs the random-direction control p = 0.056 — the learned direction wins 22 : 1 on
  ibm06 (geometric-mean J ratio vs raw 0.965 vs 0.987) but loses 6 : 11 on ibm04 (0.897 vs 0.883). Without
  evaluator noise the random control improves on raw in 24 cases (50 in the noisy run).
- `scripts/calibrate_f1_f2.py` — E3-lite f1 -> f2 on a Track-B design (rank agreement, gate agreement, per-term).
- `verify_pin_geometry.py --tech-lef`: the pin-geometry check repeated with the real sky130 technology LEF and
  the unmodified DEFs (vias and routes kept; only the fill cells without a LEF dropped): identical result
  (`reports/V3_pin_geometry_vs_openroad_full_tech.json`).
- Tests: 128 passing.

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
