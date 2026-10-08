# HeurBridge-PR — progress against the task list (T0–T7)

Status as of **2026-10-08 10:15 CST**, code: see `git log` (v0.14.0 + unreleased). Measured against
`HEURBRIDGE_TASKS.md` (Part C tasks, Part D gates). Session history: `HANDOFF.md`; every code change: `CHANGELOG.md`.

## 1. Summary

- **Cell stage (5-6 Oct, a separate chat):** the owner approved the cell-stage plan (local, unpublished); C0 is built
  (`heurbridge/cellstage/`, `scripts/run_cell_stage.py`, originality tools; CHANGELOG, HANDOFF) and its smoke test shows
  the hook leaves the flow unchanged. The headroom demo C1 (exploratory, fixed before any run: `reports/cell_stage_c1.md`)
  runs since 6 Oct 03:48 on 2 of 224's 8 OpenROAD slots, 4 once the macro chat's `dpls_b` ends.
- **Position on the critical path:** T0 ✅ → T1 ✅ → T2 (Track-B seeding: all 5 designs complete, ariane133 under D2 (b)) → T3 ✅ (exit
  gate passed) → **T4 = full E0: gate G0′ PASSED (30 Sep 23:18, all three pre-registered tests; `reports/E0_partner_ablation.md`)**
  → T5 (next, per the pre-registered decision) → T6.
- **Roughly 44 % of the planned effort is done** (weighted by the task list's own duration estimates, §5). The done
  part is the infrastructure: toolchains on the servers, data, evaluators f0/f1/f2, the 7 heuristic families,
  archive, the bridge and its training. The remaining part is mostly the **experiments** (E0, LLM evolution,
  E1/E2, H1–H9): compute-bound and gated. G0′, the gate that could stop the project, has passed.
- **Remaining time if every later gate passes:** about 5–8 weeks (T5 ≈ 2 weeks, T6 ≈ 3–5 weeks).

## 1b. The owner's aim (3 Oct): mean Track-A J below 0.45, better than the tool on output and cost

- **Where it stands (exploratory, `reports/beat_tool_track_a.md`):** none of the HeurBridge-side ideas beats the
  tool's best of k at equal compute on IBM. Relinking two tool runs, the lead on three designs, does not generalize:
  on all 17 designs it is lower than best of four in 29 of 136 cases and higher in 44 (Section 4). Consensus of tool
  runs: no (Section 5). Macro flipping: J -0.0017 against one run, nothing on top of best of two (Section 6).
- **What moves J is how the tool is run:** at target density 0.6 instead of 0.9 one run lowers J by 0.0288 on four
  designs (32 of 32 cases), but at 0.7 on 13 designs the effect depends on the design (lower in 67 of 104, losses on
  four designs); two densities beat two seeds at the same number of runs in 66 of 104 cases (16 worse) (Section 7). On
  top of the tool at 0.6, a second pass, heuristic starts and the flip pass do not help (Section 9). J = 0.45 is the
  tool at 0.9, so "better than the tool" must from now on mean better than the tool at its best configuration.
- **ISPD2005 tests (RL#1-RL#3) ran, but a defect makes them uninformative:** RL#1 failed (p = 0.88), RL#2 and RL#3
  passed their alpha, all on bigblue3's 8 units alone: the tool's input froze ISPD2005's macros as fixed terminals, so
  on 7 of 8 designs every arm is the benchmark's own macro placement (`reports/defect_ispd_tool_runs.md`). None of
  the three is evidence for its claim. Fixed in code; the reports and the ledger carry notes.
- **Corrected re-test RL#4 passed (pre-registered confirmatory, 3 Oct 22:37):** on the seven ISPD2005 designs not seen
  placing macros, two tool runs at densities 0.9 and 0.6 beat two seeds at 0.9 (p = 0.00014 against 0.003125; median
  -0.0060 J, lower in 33 of 56 units, higher in 11; `reports/portfolio_retest_confirmatory.md`). It confirms a way to
  spend the tool's runs, not a HeurBridge method.
- **7 Oct 19:00: another user's jobs on 224** (Gaussian, about 40 of 64 cores since the afternoon) make our runs
  time out: TB#5's first two runs hit the 7,200-s cap, EB#4's first f1 runs failed. Decision D14 asks how to proceed
  (`reports/next_phase_decisions.md`). **Decided (c):** both jobs stopped; TB#5 re-runs alone (`tb10_ariane133`),
  then EB#4 from the start and TW#5, the three-way comparison on ariane133 (D15).
- **7 Oct 15:45:** equal search budget (D12 (b), `reports/trackB_equal_budget.md`): EB#1 bp_fe_top and EB#2
  bp_be_top failed, **EB#3 ariane136 passed** (p = 0.0011): from DREAMPlace's start the same flow-scored search does
  not reach HeurBridge's layout there; EB#4 running. ariane133's campaign under D2 (b) is done; TB#5's candidate is
  fixed and reserved, its test running. This chat was paused for about 22 h (6 Oct 07:15 - 7 Oct 15:30).
- **Owner's decisions (4 Oct evening):** D13 (a) for new tests: J and timing safety combined (J, S, J_safe; every
  layout's J and gates in `reports/trackB_timing_safety.md`); D13 (b) timing-aware search: running; D2: (a) failed at its
  baseline (the tool's macro placer), (b) virtual resizing chosen and running.
- **Owner's decisions (4 Oct):** D11 (b): future Track-B tests gate each replicate against the tool's replicate at the
  same shift (registered tests unchanged); D12 (c): HeurBridge's programs without local search vs DREAMPlace (campaign
  TP): **1 of 4 designs pass** (bp_fe_top); before the gates the programs beat DREAMPlace on bp_fe_top and ariane136,
  lose on bp_be_top; the flow-scored local search improves on the programs on three designs, so HeurBridge's Track-B
  results rest mostly on it (`reports/trackB_programs_vs_dreamplace.md`). Timing-gate plan proposed (D13;
  `reports/timing_margin_explore.md`).
- **Owner's decisions (3 Oct):** more effort on Track B (D9); after Track B's seeding, DREAMPlace's and HeurBridge's
  macro placements through the OpenROAD flow next to the tool's own; the Track-B test with the 0.02-ns guard and no
  sign rule (D6); the corrected ISPD2005 re-test (D10). An audit of every earlier test is under way (E0's same-seed
  selection: 30 of 46 sampled units give a median optimism of +0.00001 J; 16 more being re-scored).
- **Track-B test (pre-registered confirmatory, 3 Oct 22:36):** HeurBridge's layout beats the tool's macro placement at
  signoff beyond the flow's shift sensitivity on 2 of 3 designs: TB#1 bp_fe_top passed (p = 0.0022; it rests on one
  replicate exactly at its hold threshold), TB#2 bp_be_top passed (p = 0.0011), TB#3 ariane136 failed on the hold gate
  (p = 0.53) although before the gates every candidate replicate is below every reference replicate
  (`reports/trackB_confirmatory.md`). Finding the candidates took 47-133 times the tool's one flow run.
- **TB#4 failed (4 Oct 04:51):** on swerv_wrapper the candidate is not better than the tool's layout even before the
  gates (median J 0.9266 against 0.9165), as its campaign data had shown. Track B: 2 of 4 designs pass.
- **Three-way comparison (`reports/trackB_threeway.md`): TW#1 bp_fe_top passed** (p = 0.0022; median J before the
  gates HeurBridge 0.905, the tool 1.001, DREAMPlace 1.073; DREAMPlace also worse on setup timing). **TW#2 bp_be_top
  passed under the registered rule** (p = 0.0011), but before the gates DREAMPlace's layout is the best of the three
  (0.961 against 1.017 and 1.108) and fails only the relative hold gate with positive hold slack: not evidence that
  HeurBridge's layout is better there (notes in the report; D11). **TW#3 ariane136 failed** (p = 0.16): before the gates
  HeurBridge is the best of the three (0.976 against DREAMPlace 1.039 and the tool 1.005), but relative gates reject
  replicates of both arms; DREAMPlace's layouts failed the flow's detailed placement on 9 of 12 f1 runs. **TW#4
  swerv_wrapper failed** (p = 0.23; every DREAMPlace replicate failed the flow or the setup gate). Complete: recorded 2 of
  4, only TW#1 a better layout (overall section of `reports/trackB_threeway.md`).
- **Next:** the three-way comparison on Track B (running) (HeurBridge, DREAMPlace, the tool's
  own placement through the same flow; `reports/trackB_threeway_preregistration.md`, registered 3 Oct 23:24, TW#1-TW#3),
  with the asymmetry stated: HeurBridge's candidates were searched with the flow as the score, DREAMPlace never sees it.
  The audit of the earlier tests is done (`reports/test_audit.md`).
- **New capacity:** 227 (3 x RTX 3090) set up from 225's environment (no downloads), smoke test identical to 231's.

## 2. What is running right now

| Server | Job | Task | State | Expected |
|---|---|---|---|---|
| 225 GPUs 0–3 | — | **full E0 done** (bigblue4 whole on 225: 30 legal sources of 80, budgets 2259 / 2231 s, memory-lean RUDY `HB_RUDY_IMPL=bmm`) | all components complete 30 Sep 23:18 (task list 405 + equal guard 405 + IBM 145 cases) | done: G0′ passed |
| 231 GPU 4 | `ft_sketch_ibm2` | cell-sketch fine-tune (S1 of the sketch redesign) | **done 14:09: fails its pass rule** (`reports/sketch_finetune_s1.md`); the dedicated predictor (S2) is next | done |
| 234 (CPU only) → 225 GPU 0 | `cell_labels_234`, `s2_lookahead_225` | sketch redesign S2: 3,838 DREAMPlace labels (0 failures), then the cell-stage predictor | **done 1 Oct 07:14: misses its bar** (DA0 ratio 0.747 / 0.642 vs ≤ 0.5; `reports/sketch_predictor_s2.md`) | done |
| 224 (2 OpenROAD runs) | `tb9_ariane133` (after `seedB_orfs9_ariane133`) | **D2 (b)**: ariane133's campaign with virtual resizing for every run incl. the baseline; then **TB#5** | campaign **done 6 Oct 17:12** (80 program layouts at f1, 36 distinct; 20 at f2, 12 admitted); TB#5 candidate `ariane133.ls5.n5` (f2 J 0.904) fixed and reserved 7 Oct 15:36 (`reports/trackB_preregistration.md`, addendum); its test `tb9_ariane133` running since 15:37 (12 f2 runs, 2 at a time); **at 19:00 its first two runs timed out at the 7,200-s cap under another user's load; stopped 18:56 (D14 (c)), re-run as `tb10_ariane133`**, running since 8 Oct 10:10 (alone on our side of 224) | about 9-10 h, to about 20:00 |
| 224 (2 OpenROAD runs) | `dpls_a`, `dpls_b`, `dpls_c` | **D12 (b)** equal search budget (`reports/trackB_equal_budget_preregistration.md`, EB#1-EB#4): DREAMPlace's pick + HeurBridge's local search vs HeurBridge's candidate | **EB#1 bp_fe_top failed** (p = 0.128), **EB#2 bp_be_top failed** (p = 0.79), **EB#3 ariane136 passed** (p = 0.0011; HeurBridge 0.976 inside every gate, DREAMPlace + local search 1.037 with setup failing on 4 of 6 shifts); `reports/trackB_equal_budget.md`. `dpls_c` (swerv_wrapper, EB#4) running since 7 Oct 15:37; its first two f1 runs failed (one at the cap, one GRT-0116) under the same load; stopped 18:56 (D14 (c)), restarts as `dpls_c2` after TB#5 | about a day after TB#5 |
| 224 | `tls_swerv`, `tls_ariane136` | **D13 (b)** timing-aware local search (exploratory) | **done 5 Oct 17:00** (`reports/timing_aware_search_trial.md`: ariane136 unchanged; swerv_wrapper lower J, not safer) | done |
| 224 | `tp_a`, `tp_b`, `tp_c` | **D12 (c)** (`reports/trackB_programs_preregistration.md`): HeurBridge's program picks at the six shifts | **done; TP#1-TP#4 analysed** (last 4 Oct 19:01; `reports/trackB_programs_vs_dreamplace.md`) | done |
| 224 | `tw_a`, `tw_b`, `tw_swerv` | **three-way comparison** (`reports/trackB_threeway_preregistration.md`): DREAMPlace's layouts through the flow on all four designs | **done** (TW#1-TW#4 analysed, last 4 Oct 15:50; `reports/trackB_threeway.md`) | done |
| 224 (4 OpenROAD runs) | `tb_swerv_wrapper` | **Track-B test TB#4** (12 f2 runs) | **done; analysed 4 Oct 04:51: failed** (p = 0.98; `reports/trackB_confirmatory.md`) | done |
| 224 | `seedB_orfs7_swerv_wrapper` | T2.7 Track-B seeding of the last design | **done 4 Oct 00:15** (Track B's seeding complete) | done |
| 224 (6 OpenROAD runs) | `tb_bp_fe_top`, `tb_bp_be_top`, `tb_ariane136` | **Track-B confirmatory test TB#1-TB#3**: 12 f2 runs per design | **done; analysed 3 Oct 22:36** (`reports/trackB_confirmatory.md`): TB#1, TB#2 passed, TB#3 failed | done |
| 231 GPU 4, 227 GPUs 0-2, 225 GPUs 0-2 | `rc4_*` | **corrected ISPD2005 re-test RL#4**: the tool at 0.9 and 0.6, 8 seeds, 7 designs | **done; analysed 3 Oct 22:37: passed** (`reports/portfolio_retest_confirmatory.md`) | done |
| 225 GPUs 0-3, 227 GPU 0, 224 | `e0bias_a`, `e0bias_b0`-`b3`, `dptb_place`, `dptb_diag`, `dptb_place2`, `dptb_place3`, `extsmoke_bp_fe_top` | E0 same-seed audit (all 46 units; `reports/test_audit.md`); DREAMPlace's Track-B layouts (48 runs, macros as P_M's footprints); the external-layout flow path checked on two campaign layouts | done | done |
| 225, 227, 231 | `rlc_*`, `rtd_*`, `dens6_*`, `lspairs_*` | RL#1-RL#3 runs (ISPD2005); density 0.6 on 13 IBM designs; refiner pairs | **done 3 Oct**; RL#1-RL#3 analysed once, invalid for their claims (`reports/defect_ispd_tool_runs.md`) | done |
| 227, 231 | `pass2_*`, `flip06`, `heur06_*`, `dens7_*` | exploratory: on top of density 0.6; density 0.7 on nine more IBM designs | **done 3 Oct** (`reports/beat_tool_track_a.md`, Sections 7 and 9) | done |
| 227, 231 | `relinkall_a`-`_d`, `cons_*`, `flip_*`, `warm_*`, `dens_*`, `densB_*` | relinking on 14 IBM designs; consensus, flip, warm start, target density (IBM) | **done 3 Oct** (`reports/beat_tool_track_a.md`, Sections 4-8) | done |
| 225, 227, 231 | `beat_tool_*`, `band_*`, `toolref3_*`, `relink_*` | feasibility demo, bands, tool + bridge vs best of two, relinking on 3 designs | **done 3 Oct** (`reports/beat_tool_track_a.md`) | done |
| 224, 225 | `probe133_*`, `s2_aug_225`, `s2rank_*`, `seedB_band_ariane136`, `t5_smoke_mock` | earlier this session | done (reports listed in Section 3) | done |
| 224 | — | Track-B plan: noise bands and warm-start demos done for bp_fe_top and bp_be_top (reports regenerated) | done | done |

**Overnight (my error):** the watcher stopped seeing 225 at 23:15 (a newline in its job list), so the last three bigblue4 slices started at 08:25 instead of ~01:00–05:00, 3–7 h later. Fixed, and the watcher now reports a failed check instead of going quiet.

**Done in the full E0 (checked for completeness only):** adaptec1, adaptec2, adaptec3, adaptec4, bigblue1 in both
protocols (390 rows = 65 cases × 6 partners each), ibm08 (480 rows), bigblue3 in both protocols (300 rows = 50 × 6
each; one budget per protocol: 846.6 s equal guard, 845.2 s task list; the task-list component is
`e0x_spec_bigblue3` {spec_bigblue3, _s1, _s3} + `e0x_spec_bigblue3_r2` {_s2, _s2b}); every one exit code 0, no
duplicate case.

**What I did this afternoon (29 Sep 13:00 – 15:30):**
- cost_v3 (your decision): Track-B timing gates referenced to the same-path replay; both Track-B reports re-scored.
- Track-B plan started on 224: candidate noise bands (`--phase band`) and the standard-cell warm start for imported
  macro layouts (`--phase warmstart`, cells from cluster quadratic positions).
- Fetched and checked bigblue3 (equal guard). Measured bigblue4's per-case time (≈ 4.75 h, was estimated at 4 h)
  and taught the watcher to report finished bigblue4 slices, so slices 6–7 start as soon as memory frees.
- Your question on downstream-aware bridges: a proposal extending T3.9 is in the meeting brief (kept local, not in
  this public repository); it waits for your decision (§6).

**Earlier (28 Sep 19:50 – 29 Sep 13:00):**
- **Restarted the full E0 as slices** (your approval, 19:52): every component keeps its sources, partners and first
  measured time budget; the recomputed random-control scale matched the original probe's exactly on all five
  restarted designs.
- **Found and fixed an out-of-memory kill** (bigblue3 spec slice 2 at 22:46, 21 GB): RUDY's three-operand einsum
  builds an 18 GB temporary without `opt_einsum`. Fix: a memory-lean equivalent (`HB_RUDY_IMPL=bmm`, used for
  bigblue4 only, so every design stays internally consistent) and a per-host slot cap; the killed slice was re-run
  from its 11 finished rows (bit-identical settings). The watcher now reports kernel OOM kills, stalled slices and
  low memory. A placer run killed by the host OOM killer is now re-run instead of being scored as a failure.
- **Moved bigblue4 whole to 225** (sources saved encrypted on 231 and copied as ciphertext; identical sha256).
- **Track B:** bp_fe_top and bp_be_top finished; reports re-score every row under cost_v2 and add the signoff (f2)
  results (§3, T2.7). The report generator now records the Yosys the flow actually runs (0.48).
- **Cleanup survey** of the HeurAgenix reproduction folders (your request, §6).

## 3. Status per task

Legend: ✅ done · 🔄 running · ⚠️ done with a limitation · ⏸ waiting for your decision · ⬜ not started

### T0 — Environment and feasibility ✅

| Sub-task | Status | Evidence / note |
|---|---|---|
| T0.1 inherit state | ✅ | `ENV_REPORT.md` |
| T0.2 probe servers | ✅ | `ENV_REPORT.md` (224, 225, 227; 225 approved by you) |
| T0.3 recent OpenROAD / ORFS | ✅ | OpenROAD 676f8451 built from source (the ORFS 2024-12 pin); **ariane133 through detailed routing: DRC 0, bit-identical repeats** (`ENV_REPORT.md`) |
| T0.4 benchmarks | ✅ | IBM (ICCAD04), ISPD2005, ORFS Nangate45 designs with sha256 manifests (`configs/manifests/`) |
| T0.5 Python env, GPU | ⚠️ | 225: env + GPU smoke PASS (`reports/env/gpu_smoke_225.txt`); 224/227 CUDA broken by a faulty GPU (admin); ChipDiffusion cloned but not reproduced (no licence; checkpoints on Google Drive) — the bridge uses our own backbone (spec fallback) |
| T0.6 LLM client + budget ledger | ✅ | DeepSeek self-test PASS |

### T1 — Data model, contract, fidelity ladder ✅

| Sub-task | Status | Evidence / note |
|---|---|---|
| T1.1 design object, loaders | ✅ | round trips on 26 bookshelf + 18 LEF/DEF designs (`reports/T1_roundtrip_*.json`) |
| T1.2 contract checker | ✅ | `heurbridge/core/contract.py`, tests |
| T1.3 f0 (GPU-batched) | ✅ | `heurbridge/eval/f0.py` |
| T1.4 f1 | ✅ | Track A: DREAMPlace 4.3.1 (macros fixed); Track B: ORFS to global routing |
| T1.5 f2 / f3 | ⚠️ | f2 = ORFS to 6_report (Track B). f3 signoff (KLayout DRC/LVS) not possible on the servers (no KLayout) — only via local OpenLane on a sample |
| T1.6 cost J and gates | ✅ | `heurbridge/eval/cost.py`, weights frozen (`configs/cost.yaml`) |
| T1.7 seed baselines | ✅ | Track A: 25 designs; Track B: 5 ORFS designs × 2 deterministic runs |

### T2 — Heuristic population, projections, archive 🔄 (T2.7 Track B)

| Sub-task | Status | Evidence / note |
|---|---|---|
| T2.1 program contract + sandbox | ✅ | `heurbridge/evolve/sandbox.py` (V0) |
| T2.2 macro seeds (≥ 7 families) | ✅ | M1 (tool-native) + M2–M7, 16 program versions |
| T2.3 / T2.4 cell and route seeds | ✅ | `heuristics/cell`, `heuristics/route` |
| T2.5 projections P_M / P_C / P_R | ✅ | `heurbridge/core/project.py` |
| T2.6 elite archive | ✅ | `heurbridge/archive/` |
| T2.7 seeding, Track A | ✅ | IBM 17 designs `reports/T2_trackA_ibm_dreamplace.md`; ISPD2005 8 designs `reports/T2_trackA_ispd_dreamplace.md` |
| T2.7 seeding, Track B | ✅ | **All five designs complete** (swerv_wrapper 4 Oct, ariane133 under D2 (b) 6 Oct; candidates: `reports/trackB_preregistration.md`, addenda). Earlier notes: **bp_fe_top and bp_be_top complete** (`reports/T2_trackB_orfs_bp_fe_top.md`, `…_bp_be_top.md`; cost_v3: gates vs the same-path replay): at signoff 16 / 9 of 20 layouts pass every gate, 14 / 7 of them below the unmodified flow (best 0.881 / 0.931, local search); the same-path replay of the tool's own layout scores 1.323 / 1.103 (band of one-site shifts 1.03–1.40 / 1.02–1.16); f1–f2 Kendall tau 0.51 / 0.78. Descriptive: candidates need their own noise band before any claim. ariane136 complete (`reports/T2_trackB_orfs_ariane136.md`: best admitted 0.976 at signoff, 10 of 20 layouts below the tool's same-path band 1.000–1.009; **the top three candidates' own bands, 0.9753–0.9766, lie below the tool's same-path band**, descriptive); swerv_wrapper then still running; ariane133's first campaign finished with 0 of 80 heuristic layouts evaluable. **Diagnosis 2 Oct** (`reports/trackB_ariane133_diagnosis.md`): global placement stalls (overflow ≈ 0.3 at the 5,000-iteration cap), the resizer then adds ≈ 110,000 buffers and detailed placement fails; the tool's own layout shifted by one site stalls too. PLACE_DENSITY 0.35 (ariane136's value) makes 4 of 5 probed layouts evaluable; decision D2 in `reports/next_phase_decisions.md`. Draft Track-B pre-registration: `reports/trackB_preregistration.md`. Many heuristic layouts fail ORFS (GRT-0116 congestion, DPL-0036, 2-h timeouts; identical failing layouts are no longer re-run). **Findings:** (1) the failures come from ORFS 2024-12's timing-driven global placement diverging on scattered layouts (the same layout places fine with it off); (2) M1's own layout imported like a candidate scores worse than base M1 (bp_fe_top f2: J 1.32 vs 1.00, nearly all TNS) because Hier-RTLMP pre-places the standard cells — so candidates are paired with this same-path replay, and a per-design noise band (M1 shifted by one site/row) decides what counts as an improvement. Estimate: several more days |

### T3 — The bridge ✅ (T3.9 after G0′)

| Sub-task | Status | Evidence / note |
|---|---|---|
| T3.1–T3.3 data, model | ✅ | `heurbridge/bridge/` |
| T3.4 pretraining (warm start) | ✅ | `reports/T3_pretrain_small.md` |
| T3.5–T3.6 loss, training, validation | ✅ | `heurbridge/bridge/train.py` |
| T3.7 Algorithm R | ✅ | round 0 promoted (T3 exit gate: J 0.4815 vs raw 0.8870, p = 2.6e-9), round 1 promoted (0.4756, p = 1.2e-4), round 2 not promoted → final checkpoint round 1 (`reports/T3_algorithmR_trackA.md`) |
| T3.8 guarded inference | ✅ | `heurbridge/bridge/sample.py` |
| T3.9 cell / route bridges | ⬜ | only after G0′ passes (task list). Extension adopted 29 Sep (kept local); its first package, the bridge-to-bridge stage hand-off, is written and tested (`heurbridge/bridge/handoff.py`, off the evaluation path); anything handed to DREAMPlace or OpenROAD waits for G0′ **Sketch redesign (2 Oct):** the S2 cell-stage predictor misses its bar in both parts: distance (DA0 0.747 / 0.642; with the bridge's augmentation 0.777 / 0.611) and ranking (Kendall tau 0.152 on ibm04; with augmentation 0.114 and 0.401) (`reports/sketch_predictor_s2.md`, `…_s2_aug.md`, `…_s2_ranking.md`). The cell bridge's endpoint is decision D3 (`reports/next_phase_decisions.md`). |
| T3.10 unit tests 1–6 | ✅ | `tests/test_bridge.py`; the whole suite: 197 tests pass (3 Oct, `.venv/bin/python -m pytest -q tests`, 150 s) |

### T4 — E0 partner ablation, gate G0′ ✅

| Sub-task | Status | Evidence / note |
|---|---|---|
| partners + E0 driver | ✅ | `heurbridge/partners.py`, `scripts/run_e0.py` |
| development E0 (local, CPU) | ✅ | `reports/E0_partner_ablation_dev*.md` (suggestive only) |
| E0 demo (225) | ✅ | positive direction: the co-trained bridge has the lowest J under both protocols (`reports/E0_demo_spec.md`, `reports/E0_demo_eq.md`); much of the gain comes from the f1 guard (random direction + guard is close), the learned direction still beats it (p = 2.3e-9) |
| **full E0 (confirmatory, G0′)** | ✅ | **G0′ PASSED** (30 Sep 23:18). E0#1 (primary; ISPD2005, 7 designs, 405 cases): co-trained bridge mean J 0.5579 vs memetic 0.5843, repertoire 0.6137, raw 0.5863; Holm p 3.3e-65 / 2.4e-61 (`reports/E0_partner_ablation.md`). E0#2 (equal guard): p 3.5e-63 / 3.2e-57 (`…_eq.md`). E0#3 (ibm08/ibm12, 145 cases): p 4.3e-17 / 1.6e-21 (`…_ibm_heldout.md`). Learned direction vs random direction p = 1.3e-59. No failed rows. Every partner's mean J (and every bridge-refined layout) stays above DREAMPlace's own macro placement, J 0.45: the bridge improves the heuristics by 1.9–6.9 % per design, it does not reach the tool |

### T5 — LLM evolution ⏸ (after G0′)

| Sub-task | Status | Evidence / note |
|---|---|---|
| T5.1–T5.4 prompts, fitness, population, RLCE | ✅ | `heurbridge/evolve/`; end-to-end with a mock LLM (`scripts/run_evolution.py --llm mock`) |
| T5.5 baseline engines | ✅ | five proposers implemented |
| T5.6 knowledge loop | ⬜ | later (after H1) |
| real evolution runs | ⬜ | **prepared, awaiting your approval:** draft pre-registration `reports/t5_demo_preregistration.md`, runbook (HANDOFF, "T5 demo runbook"), mock smoke test passed on 225 (2 Oct); nothing ran with the real LLM |

### T6 — Online solving and main experiments ⬜ (mostly)

| Sub-task | Status | Evidence / note |
|---|---|---|
| T6.1 online pipeline | ✅ | `heurbridge/online/solve.py` |
| T6.2 E3 calibration, gate G0 | 🔄 | Track A done: IBM `reports/E3_calibration_trackA_dreamplace.md`, ISPD2005 `reports/E3_calibration_trackA_ispd.md` — **G0 not met** on both (f0 is not an admissible proxy for f1; the f1 guard stays). Track B pending the campaign |
| T6.3 E1, T6.4 E2, T6.5 H1–H9 / A1–A11 | ⬜ | weeks of compute after T4/T5 |

### T7 — Verification, statistics, reporting (continuous) ✅ so far

V0 sandbox, V1 metamorphic tests, V2 contract/legality, V5 promotion gate: implemented (`heurbridge/verify/`); V3
pin-geometry check (`reports/V3_*.json`); V4 signoff limited (no KLayout on the servers). Statistics
(`heurbridge/stats/`), α-ledger (`stats/alpha_ledger.jsonl`; the two T3.7 entries are merged when the job ends),
report template (`reports/templates/`), originality tool (`heurbridge/verify/originality.py`).

## 4. Gates (Part D)

| Gate | Status |
|---|---|
| T0 exit (a track available) | ✅ both tracks |
| T3 exit (bridge beats raw on validation, paired) | ✅ passed (p = 2.6e-9); caveat: its guard uses the same f1 as the final cost |
| **G0′** (bridge beats memetic and repertoire, p < 0.01) | ✅ passed 30 Sep 23:18 (E0#1 Holm p 3.3e-65 / 2.4e-61; E0#2, E0#3 also pass) |
| G0 (proxy admissible) | ❌ not met on Track A (IBM, ISPD2005); Track B pending → fitness stays at f1 |
| G1, G2, G3, G4 | ⬜ later (T5, T3.9, T6) |

## 5. How far from completion

Effort weights are the midpoints of the task list's own estimates; completion fractions are my assessment.

| Task | Planned effort | Done | Done (days) |
|---|---|---|---|
| T0 | 1.5 d | 95 % | 1.4 |
| T1 | 5 d | 95 % | 4.8 |
| T2 | 6 d | 90 % | 5.4 |
| T3 | 8.5 d | 80 % | 6.8 |
| T4 | 3.5 d | 100 % | 3.5 |
| T5 | 12 d | 30 % | 3.6 |
| T6 | 28 d | 10 % | 2.8 |
| **Total** | **64.5 d** | **≈ 44 %** | **28.3** |

T7 runs alongside and is not weighted separately. The estimate assumes every gate passes; a G0′ failure ends the
planned path at T4 ("stop and report", with a repositioning decision for you).

## 6. Decisions

Open decisions with options, evidence and recommendations (2 Oct): `reports/next_phase_decisions.md`.

Received 2026-09-28: LLM = **deepseek-flash** for every LLM call; timing gates **reported at f1, enforced at f2/f3**
(cost_v2); each experiment runs as a **demo on 225 first**, then at full capacity if the effect is good.

Received 2026-09-28: 231 approved for the full E0 (GPU 4 only); restart of the full E0 as slices approved (19:52).
Received 2026-09-29: clean the HeurAgenix reproduction folders HeurBridge does not need. Staged (moved, reversible)
into `/data/dzy/heura_repr/_to_delete_20260929/` on 224 (68 GB: eda/runs*, models, envs/heura, envs/miniconda3,
repo, datasets, output, logs, results, evidence) and 231 (7 GB: envs, models, repo, datasets, output, logs; its
results/ kept). The final delete is yours to run (I cannot delete files permanently). Kept on 224: hb, envs/hb,
tools, cache, third_party, benchmarks, eda/{harness,flow,tools,pdk,...}, src, build.

Received 2026-09-29 (afternoon): **Track-B timing gates referenced to the same-path replay** (cost_v3, done: code,
tests, both Track-B reports re-scored); **225's reproduction monitors stopped** (`b_monitor`, `b_reason_monitor`;
the other tmux sessions there, `agent1`, `agent2`, `tmp`, belong to another project -- `taorui/auto_project` -- and
were left alone) and 225's reproduction folders staged for deletion (31 GB; result tables and docs kept).

Received 2026-09-29 (15:00): **keep all bigblue4 slices running**; **B.3 stays frozen** (hold no more than 0.02 ns
worse than the reference); **go ahead with the Track-B improvement plan** (candidate bands and the warm-start demo
are running; next: timing-aware macro cost, f1 timing-aware local search, the Track-B bridge after G0′).

Received 2026-09-29 (16:00): **the T3.9 extension is adopted**. Parts used only among bridges go ahead now, since
they leave G0′ unchanged. Anything that hands a bridge's sketch to another tool's standard-cell placement or global
routing waits for G0′. The first package, the bridge-to-bridge hand-off, is written; nothing on the evaluation path
uses it.

**Track-B demos, bp_be_top (22:00; `reports/T2_trackB_orfs_bp_be_top.md`).**
- Only the best candidate's noise band (0.931-1.000) lies wholly below the tool's same-path band (1.024-1.162).
- The quadratic warm start hurts on bp_be_top: the candidates go from 0.93-0.95 to 1.07-1.11, two of seven runs
  fail global routing (congestion), and the tool's layout does not improve. On bp_fe_top it had helped the tool's
  layout. My recommendation, needing no change since the protocol does not use it: do not adopt the quadratic
  warm start for Track B.

**DREAMPlace sketch demo (done 17:34, `reports/demo_sketch_start.md`): no effect.**
- Mean J 0.4822 with cells starting at the die centre, 0.4828 from the bridge's sketch, 0.4948 from a quadratic
  placement; sketch vs centre: 28 better, 36 worse.
- DREAMPlace reaches nearly the same placement from any start, and the sketch is far from it (0.24 of the core,
  against 0.02 between placements).
- Consequence for the adopted extension: the sketch must first get much better (its first check, DA0), and
  start positions are not the port for DREAMPlace.

Received 2026-09-29 (17:00): **run the DREAMPlace sketch demo now, on 231's GPU 4** (not on 225, where E0's
wall-clock-budgeted partners run).

Track-B timing plan, 17:10:
- The timing probe (the unmodified flow to 3_place, then slack at every macro pin) finds no near-critical macro
  pin. bp_fe_top's worst is +0.457 ns at a 1.8 ns clock, bp_be_top's +0.465 ns at 2.6 ns; no macro pin has
  negative hold slack.
- The timing-aware local search, replayed on both campaigns, would not have changed an accepted move.
- So neither mechanism has leverage on these two designs, and no weighted campaign is run. Both stay available,
  off by default, for designs whose macros are on critical paths.

**Demo 2 (30 Sep, `reports/demo_sketch_cells.md`), stopped at your request at 09:14 once ibm04 was complete.**
- Nothing built from the sketch improves DREAMPlace.
  - Sketch start: +0.4 % J (5 better, 18 worse).
  - Held sketch start: +1.4 % (2 / 21).
  - Cell widening from the sketch's congestion: +0.6 % (1 / 15).
- The sketch is barely closer than a quadratic placement to where DREAMPlace puts the cells (0.235 against 0.253).
- Causes and a redesign of the sketch are in the meeting brief (the plan itself stays local). The fine-tune above is its first stage.

Received 2026-09-30 (09:10): **stop the demo if it is not useful** (done); **keep a checkpoint of the bridge before fine-tuning** (done: `bridge_v1_e0_frozen`, sha256 f95bdde8…, on the Mac and in all three vaults); **no heavy compute on the Mac**; CPU-only servers for CPU work.

Open:
0. ariane133 (Track B): diagnose, possibly with another flow deviation, or drop it as a documented deviation (HANDOFF 30 Sep 13:50).
1. Endpoints of the extension's tests (proposed: signoff J on the ORFS designs; placer J on ISPD2005) -- fixed in
   its pre-registration after G0′.
2. Housekeeping: back up `~/.config/heurbridge/vault.key` (without it the server vault cannot be decrypted); ask
   the admin about the faulty GPUs on 224 / 227; run the final delete of the staged reproduction folders.

## 7. Deviations and known limitations

- Full E0: bigblue4 has 30 legal sources (only 30 of its 80 program runs project legally) and uses the memory-lean
  RUDY (`HB_RUDY_IMPL=bmm`, equal to the reference to ~1e-6); bigblue3 spec's slice 2 was OOM-killed and re-run
  from its 11 finished rows as two sub-slices (same settings, bit-identical scale). Neither changes the registered
  protocol; both are listed for the report.
- ariane133 runs with `RTLMP_MAX_LEVEL=1` (upstream's MPL workaround); ORFS's own macro placer does not converge
  otherwise at the 8-thread cap. Everything else is the 2024-12 configuration.
- Track A has no f2 (bookshelf benchmarks have no timing): its final cost is f1 (DREAMPlace).
- bigblue2 (23,084 macros) cannot run the heuristic programs: the dense macro affinity exceeds the sandbox's 4 GB.
- On every Track-A design the seeding's M1 is the best layout found by seeding (on ISPD2005 M1 is the benchmark's own
  macro placement, not DREAMPlace's: `reports/defect_ispd_tool_runs.md`); the
  heuristics beat it on 2 of 25 designs only. **Corrected 2 Oct:** the bridge's targets are M1-like in position,
  not in cost: on the 13 training designs only 38 % of the 1,608 pairs target an elite at or below the tool's J
  0.45 (30 % the tool's own layout); the rest target local-search or heuristic elites that cost more
  (`reports/bridge_target_audit.md`:29). This caps what the bridge can reach (`reports/gap_to_tool_plan.md`).

## 8. Failure taxonomy (2 Oct 2026)

Every failure enters the statistics as +inf and is listed by name in its report. Counts are evaluations, per
design; "disposition" is the existing mitigation or the proposed fix.

| Class | Where (count) | Disposition | Sources |
|---|---|---|---|
| Routing congestion (GRT-0116) | bp_fe_top 8, bp_be_top 41 | a property of the layout: kept as a named failure (+inf); identical failing layouts are not re-run | `reports/T2_trackB_orfs_bp_fe_top.md`:88, `reports/T2_trackB_orfs_bp_be_top.md`:88 |
| Global placement does not converge | named divergence GPL-0307: bp_fe_top 7, ariane136 5, ariane133 5; GPL-0305: bp_fe_top 1. Silent: every other failing ariane133 layout stops at the 5,000-iteration cap with overflow 0.28-0.43 instead of 0.10, after which the resizer adds about 110,000 buffers (utilization 39 % to 74 %) and detailed placement fails or times out; the failing ariane136 layouts show the same pattern (overflow 0.335, about 121,000 buffers), and so do 36 of swerv_wrapper's failures so far (overflow 0.416, about 114,000 buffers; partial snapshot 2 Oct) | diagnosis 2 Oct (`reports/trackB_ariane133_diagnosis.md`, five probed layouts): PLACE_DENSITY 0.35 (as ariane136 sets) makes 4 of 5 evaluable with setup TNS no worse than -0.15 ns (the fifth: GPL-0307); virtual timing-driven resizing (`-keep_resize_below_overflow 0.01`) makes 5 of 5 complete but leaves setup TNS down to -50.7 ns. Proposed fix: PLACE_DENSITY 0.35 for every ariane133 run, baseline included (a flow deviation for the owner, decision D2) | `reports/T2_trackB_orfs_bp_fe_top.md`:89-92, `reports/T2_trackB_orfs_ariane136.md`:78, HANDOFF.md:610 |
| Detailed placement failed (DPL-0036) | bp_fe_top 2, ariane136 17, ariane133 37 | on ariane133 and ariane136 a consequence of the class above (diagnosis); otherwise kept as named failures | `reports/T2_trackB_orfs_bp_fe_top.md`:91, `reports/T2_trackB_orfs_ariane136.md`:77, HANDOFF.md:610 |
| Step timeout (7,200 s per step) | bp_fe_top 5_1_grt 7; ariane136 3_5_place_dp 18; ariane133 3_5_place_dp 25; swerv_wrapper 3_5_place_dp 52 and 5_1_grt 1 of 101 f1 rows so far | the red-line cap; on the ariane designs the timeouts follow non-converged placement (diagnosis) | `reports/T2_trackB_orfs_bp_fe_top.md`:89, `reports/T2_trackB_orfs_ariane136.md`:76, HANDOFF.md:610, :615-616 |
| Unparsed ORFS failure | ariane133 14 | explained by the diagnosis (non-converged placement, then detailed placement); the parser found no [ERROR] line in the 4,000-character tail | HANDOFF.md:610, `heurbridge/eval/orfs.py`:307 |
| Power-grid repair (PDN-0179) | ariane133 1 (the tool's layout shifted by one row) | named failure; not a heuristic's | HANDOFF.md:610, `runs/diag_trackb` (local) |
| Program timeout (sandbox, 60 s CPU) | IBM 55 (ibm10 15, ibm12 15, ibm14 5, ibm16 5, ibm17 15); ISPD2005 80 | +inf; the limit is part of the program contract | `reports/T2_trackA_ibm_dreamplace.md`:35-42, :49, `reports/T2_trackA_ispd_dreamplace.md`:42 |
| Sandbox memory (4 GB) | ISPD2005: 80 crashes + 40 errors; bigblue2 cannot run any program | +inf; bigblue2 stays out of E0 as a documented deviation (§7) | `reports/T2_trackA_ispd_dreamplace.md`:34, :41-43, §7 |
| Too few legal sources | bigblue4: 30 of 80 program runs project legally | registered as is for E0 (§7) | §7 |
| Host out-of-memory kill | 1 (bigblue3 E0 slice, 21 GB) | fixed: memory-lean RUDY (`HB_RUDY_IMPL=bmm`), per-host slot cap, a SIGKILLed placer run is re-run, the watcher reports OOM kills | §2 (28-29 Sep) |
| GPU out of memory | 1 (S1 evaluation, all cached sources in one batch) | fixed: batches of `--chunk` sources | CHANGELOG.md:327-328 |
| Label-job CPU oversubscription (not a failure) | 14 workers x 8 DREAMPlace threads on 64 cores | fixed 2 Oct: `make_cell_labels.py --workers 8 --threads 4` | HANDOFF.md:597-599 |
| Pipeline defect: the tool's input froze ISPD2005's macros (source terminals) | every ISPD2005 tool run since 28 Sep (seeding M1, RL#1-RL#3) | fixed 3 Oct (commit 157bf21); RL#1-RL#3 not evidence for their claims; re-test: D10 | `reports/defect_ispd_tool_runs.md` |

