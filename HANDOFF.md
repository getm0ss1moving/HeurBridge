# HeurBridge — session handoff log

Newest entry first.  Each entry: what was done, commands, artifacts, open issues.

---

## 2026-10-07 — Macro chat: EB#1-EB#3 recorded (EB#3 passed); D2 (b) campaign done; TB#5 and EB#4 running

- **Gap:** this chat was paused from 6 Oct about 07:15 until 7 Oct 15:30. `dpls_b` ended 6 Oct 16:09 and
  `seedB_orfs9_ariane133` 17:12 (both rc 0), so my 4 slots on 224 sat idle for about 22 h; the cell chat took its full
  share of 4 at 7 Oct 15:26 as agreed.
- **D12 (b), equal search budget (`reports/trackB_equal_budget.md`; campaign EB):** EB#1 bp_fe_top failed (p = 0.128),
  EB#2 bp_be_top failed (p = 0.79), **EB#3 ariane136 passed** (7 Oct 15:34; p = 0.0011 against alpha_j 0.00625):
  HeurBridge's candidate J 0.975-0.976 on all six shifts inside the gates; DREAMPlace + local search (4 moves kept, f1
  0.983 -> 0.981; pick `ariane136.dpls.s4.f2`) 1.036-1.038 before the gates, with setup failing on four of its six
  shifts (D11 (b), against the tool's replicate at the same shift). Reported only: the search adds little to DREAMPlace
  on ariane136 (p = 0.35 against DREAMPlace alone); it cost 34.5 flow-run hours. EB#4 (swerv_wrapper) is running.
- **D2 (b) campaign done** (`seedB_orfs9_ariane133`): 80 program layouts at f1 (36 distinct, all completed), local
  search, 20 f2 layouts (one stopped at the 7,200-s cap), 12 admitted under the TB rule (D6). **TB#5's candidate
  `ariane133.ls5.n5`** (f2 J 0.904) fixed by `scripts/trackb_confirm.py candidate --design ariane133 --campaign-prefix
  seedB_orfs9_` and reserved (alpha_5 = 0.0015625) before its test: addendum in `reports/trackB_preregistration.md`
  (commit a55a963). Only complete separation can pass (p = 1/924). The tool's f2 replays vary J 0.74-1.88 (setup TNS).
- **Running on 224 since 15:37 (my 4 slots; the cell chat has the other 4):** `tb9_ariane133` (TB#5: `--phase tbtest
  --tb-candidate ariane133.ls5.n5.f2 --tb-workers 2` with the campaign's make variables, resumed from
  `seedB_orfs9_ariane133`; 12 f2 runs, about 9-10 h) and `dpls_c` (EB#4: the scratchpad's `launch_dpls.sh c`; about a
  day). Afterwards, once each: `python scripts/trackb_confirm.py analyze --design ariane133 --tb-prefix tb9_
  --campaign-prefix seedB_orfs9_` (then `describe` with the same prefixes) and `python scripts/equal_budget_confirm.py
  analyze --design swerv_wrapper`. The cell chat has ariane133's candidate run id for its C1 layouts.
- **Citation re-map:** the scratchpad's `remap_citations.py` was lost to the temp-folder cleanup and rebuilt; it now
  also re-maps `, :L` continuations (a second range after a cited file's first), which were left unmapped before.

## 2026-10-07 — Cell-placement chat: C1 stage 1 done on bp_fe_top and bp_be_top; ariane136 and swerv_wrapper running

- **Stage 1 (f1, single runs, exploratory):** bp_fe_top (`cs_c1_bp_fe_top`, 6 Oct 03:48-05:31) and bp_be_top
  (`cs_c1_bp_be_top`, 05:32-09:48). Local run files: `runs/remote/cs_c1_<design>/runs/seed_orfs/<design>/evals_cs_c1.jsonl`.
  - R0 reproduces the campaign's f1 rows of all four layouts exactly (14 metrics each).
  - R7 equals R0 on all four, as predicted.
  - R9 (DREAMPlace's start kept): no cell moves in 3_1 or 3_3, which closes the smoke's open check. Global routing
    then fails (GRT-0116) on all four layouts; R9c fails on three of four.
  - bp_be_top is sensitive to congestion: 9 of its 24 runs fail global routing (GRT-0116), among them R1c on both
    layouts and R2, R4 and R8 on M1. On its HeurBridge layout no recipe beats R0 at f1 (R0 0.918, next R3 0.966).
  - bp_fe_top, J before the gates, R0 against the best recipe: M1 0.959 against 0.922 (R6, no timing-driven global
    placement); HeurBridge's layout 0.900 against 0.887 (R5 and R3).
  - Stage 2's race (the fixed rule):
    - bp_fe_top: R6 and R1 on M1; R5 and R3 on HeurBridge's layout.
    - bp_be_top: R5 and R7 on M1; R7 and R3 on HeurBridge's layout.
    - R7 enters on both bp_be_top layouts because its f1 rows tie R0's. It runs as the rule says, and its f2 rows
      double as a determinism check.
- **224:** nothing of this chat ran between 6 Oct 09:48 and 7 Oct 15:25, because the session was not re-invoked when
  bp_be_top's job ended. At 15:25 the macro chat's jobs had all ended and 224 was idle. `cs_c1_ariane136` and
  `cs_c1_swerv_wrapper` started at 15:26 with 2 workers each, this chat's 4 slots. The macro chat was told that its
  4 slots are free for TB#5 and `dpls_c`.
- **Stage 2 for bp_fe_top and bp_be_top queued on 224** (`cs_c1s2_bp`, scratchpad `c1/launch_c1_stage2_bp_queued.sh`).
  - The job waits until `cs_c1_ariane136` or `cs_c1_swerv_wrapper` ends, so this chat stays within its 4 slots. It
    then runs `--fidelity 2 --shifts tb --race 2 --default-rows runs/seed_orfs/<design>/evals_tb.jsonl --verify-default 1`
    for each design.
  - Each design's first R0 run (HeurBridge's layout, shift slot 1) is compared with its Track-B row before the rows
    are imported. This is the record's identity run (reports/cell_stage_c1.md, Section 4), done for every design
    instead of bp_fe_top only.
  - All 12 shifted layouts of each design have a Track-B row (local check). The failed ones are named failures
    (GRT-0116; one timeout), which are imported as such.
- **ariane133 joins C1** (`reports/cell_stage_c1.md` Section 8; `configs/cellstage/c1_ariane133.json`).
  - Layouts: TB#5's candidate ariane133.ls5.n5.f2 (the macro chat's message, 7 Oct) and M1 of `seedB_orfs9_ariane133`.
  - Every run uses that campaign's D2 (b) make variables; the runner now reads them from the campaign's meta.json.
  - DREAMPlace starts: all 14 converged at its own density, 0.30 (`cs_c1_dp_a133` on 225).
- **C1 queue on 224:** `cs_c1_queue` runs `scripts/server/cs_c1_queue.sh` with the entries `s2:ariane136`,
  `s2:swerv_wrapper`, `s1:ariane133`.
  - Stage 2 of ariane136 and swerv_wrapper starts when their stage-1 jobs end and a pair of this chat's slots is free.
    It needs no launch by hand, since the queue copies their stage-1 ledgers while those jobs run.
  - Then ariane133's stage 1 runs.
  - ariane133's stage 2 needs TB#5's rows (`tb9_ariane133`, running), so it is launched after that test ends.

---

## 2026-10-06 — Cell-placement chat: C1 prepared (fixed before any run); C0 smoke done; C1 stage 1 running

- **224:** the macro chat agreed (6 Oct 01:20) that `dpls_a`'s 2 slots go to this chat, and that its next jobs (`dpls_c`,
  the TB#5 test) start only when its reserved slots are 2 or fewer. Its notice at 03:34: `dpls_a` ended, its jobs reserve
  6 (`seedB_orfs9_ariane133` x4, `dpls_b` x2), so this chat has 2, and 4 once `dpls_b` ends (about 14:00).
- **C0 smoke done** (`cs_c0smoke_bp_fe_top`, 03:35-03:47, bp_fe_top.ls0.n4.f2 at f1, 2 at a time; local run file
  `runs/remote/cs_c0smoke_bp_fe_top/runs/seed_orfs/bp_fe_top/evals_cs_c0smoke.jsonl`, lines 1-5):
  - default: J 0.9000776798887087 and all 15 numeric metrics equal to the campaign's f1 row of the layout, so the hook
    leaves the flow unchanged.
  - caps_routes: HB_DENSITY_CAPS in the 2_3 log, HB_ROUTE_ADJUST in the 3_3 and 5_1 logs; completes.
  - hbgp_keep: HB-GP's 33,279 cells do not move in 3_1 or 3_3 (at most 0.0003 um, database rounding). Detailed
    placement moves 78 % of them (median 1.4 um).
  - quad_continue: completes.
  - dp_keep failed by name before the flow (no start file): C0's DREAMPlace job had placed only the six shifted layouts.
    C1's start files include this layout under the key the server computed. C1's R9 runs the same path and carries
    the drift check.
- **C1 stage 1 running:** `cs_c1_bp_fe_top` since 03:48 (24 runs, 2 at a time; scratchpad
  `c1/launch_c1_stage1.sh <design> <macro reservation>`). bp_be_top follows. ariane136 and swerv_wrapper start once 4
  slots are free.
- **C1 prepared (exploratory, no claims):** `reports/cell_stage_c1.md` fixes the eight layouts (the tool's M1 and
  HeurBridge's Track-B candidate of bp_fe_top, bp_be_top, ariane136 and swerv_wrapper; ariane133's two later), 12
  recipes per design (`configs/cellstage/c1_<design>.json`), the two stages and the go rule (`select.go_rule`, in code
  since 8f70c70), before any C1 run. Inputs read from the campaigns' files: `reports/cell_stage_c1_inputs.json`
  (`scripts/cell_stage_inputs.py`, local, runs no tool).
- **New code:** `heurbridge/cellstage/hints.py` (hint programs run on each run's macro layout; `channel_caps`: soft
  density caps over the macro channels, as disjoint rectangles), `CellRecipe.programs` (ids of recipes without
  programs unchanged), npz starts recorded by file name and sha256.
- **225 (approved), DREAMPlace starts for R9/R9c:** `cs_c1_dpcells` placed the eight C1 layouts and their six test
  shifts at each design's own density, but did not converge on bp_fe_top or bp_be_top. `cs_c1_dpladder` tried 0.4-0.8
  on their unshifted layouts: they converge from 0.7 and 0.6. `cs_c1_dpcells2` makes the 56 starts C1 uses (0.7,
  0.6, 0.35, 0.46).
- **Next:** stage 1 for the other designs as slots allow. Check R9's drift and R7's prediction on bp_fe_top's rows. Before
  stage 2: one identity run (`--slots 1`); then `--default-rows` takes the default recipe's f2 rows from the Track-B
  test ledgers.

---

## 2026-10-05 — Cell-placement chat (a fork of this session): C0 started

- **Scope:** this chat works on standard-cell placement for HeurBridge's macro layouts; the macro chat keeps every
  macro job and analysis. Plan: the local, unpublished `HEURBRIDGE_PLAN_cell_stage.md`; the owner adopted every
  recommendation (CS-D1 to CS-D6) on 5 Oct and asked to start C0.
- **224 slots (CS-D2 (a)):** at most 4 of the 8 OpenROAD slots for this chat, counted live before every launch. The
  macro chat keeps its own jobs at 4 or fewer once the running ones allow; at 17:50 they held all 8
  (`seedB_orfs9_ariane133` x4, `dpls_a` x2, `dpls_b` x2), and it will say when `dpls_a` ends.
- **Built (C0; infrastructure, no claims):** `heurbridge/cellstage/` (recipes, start positions, selection rules, the
  go rule), `OrfsEvaluator.cell_stage` (default off), `scripts/run_cell_stage.py`, `scripts/cell_positions.py`,
  `configs/cellstage/c0_smoke.json`, the originality tools (`scripts/code_overlap_scan.py`,
  `scripts/originality_scan.py`, `scripts/overlap_scan.py`), `reports/templates/cell_stage_preregistration.md`.
  Details in CHANGELOG.
- **Finding:** in ORFS 2024-12 a cell warm start reaches the main global placement (3_3) only through 3_2's IO pin
  placement, since 3_3 restarts from the core centre; a recipe's `hold` can now continue 3_3 from 3_1 or keep a start.
- **CS-D1:** 224's pinned ORFS tree has no Nangate45 macro design beyond our five (black_parrot and bp_multi_top
  are only in the newer local checkout), so held-out macro layouts (option (a)) for now.
- **225 (approved):** `cs_c0_dpcells` (DREAMPlace start positions for bp_fe_top's Track-B candidate and M1 at the six
  test shifts: 33,279 cells, about 9 s per layout); the full test suite `cs_c0_tests3` (eda harness mounted): 262 passed,
  5 skipped for local-only data (`tests/test_core_design.py`, `tests/test_orfs.py`: both pass locally).
- **Next, when 224 has free slots:** the C0 smoke on bp_fe_top at f1, 5 runs at 2 at a time, with the Track-B launch
  recipe below (`--resume-from` the latest final holding `seedB_orfs7_bp_fe_top`'s campaign, plus
  `--data cellpos_dp_bp_fe_top:cellpos/bp_fe_top`, DREAMPlace's positions pushed to 224's vault), command
  `bash scripts/server/trackb.sh python scripts/run_cell_stage.py --flow /data/dzy/heura_repr/third_party/ORFS-2024-12/flow
  --design nangate45/bp_fe_top --recipes configs/cellstage/c0_smoke.json --layouts bp_fe_top.ls0.n4.f2 --fidelity 1
  --tag c0smoke --workers 2 --check-drift --yosys /data/dzy/heura_repr/tools/yosys_048/bin/yosys`. Checks: the default
  recipe reproduces the campaign's f1 row of that layout (J 0.9000776798887087, local run file
  `runs/remote/seedB_orfs7_bp_fe_top/runs/seed_orfs/bp_fe_top/evals.jsonl`); HB_DENSITY_CAPS / HB_ROUTE_ADJUST lines
  in the 2_3, 3_3 and 5_1 logs; the cells of hbgp_keep and dp_keep (DREAMPlace's positions, source `npzdir:`) do not
  move in 3_1 or 3_3. Then C1's recipe list and registration.

---

## 2026-10-04 — Session 4 (19:30): D13 (a) and (b), D2 running

- **Owner (4 Oct evening):** D13 (a) for new tests, combining J and timing safety with a full output of J and gates;
  D13 (b) run; D2 run.
- **D13 (a):** `scripts/timing_safety_report.py` -> `reports/trackB_timing_safety.md` (every layout's J, setup/hold
  marks per position, checks passed, margin, J_safe = J + 0.04 (1 - S)); for new tests each arm's pick is the lowest
  J_safe among layouts with equal positions (the best few by J run at the band's shifts).
- **D2 (a):** `seedB_orfs8_ariane133` on 224 since 19:19 (PLACE_DENSITY 0.35 for every run incl. the baseline,
  RTLMP_MAX_LEVEL 1, `--workers 4`): about 1.5 days. If its baseline fails: D2 (c). When it completes: TB#5's candidate
  by the TB rule (`trackb_confirm.py candidate --design ariane133` needs ariane133 added to ORDER/CANDIDATES), reserve,
  tbtest.
- **D13 (b):** `--phase tls` smoke test `tlssmoke_bp_fe_top` (1 step x 2 neighbours, then six shifts) running; then
  `tls_swerv`, `tls_ariane136` from swerv_wrapper.ls5.n4.f2 and ariane136.ls7.n3.f2, 2 at a time each (about 18 h).
- **Watch:** Monitor with the scratchpad's `monitor_jobs.sh` (pid files) or `monitor_log.sh` (log lines).
- **D2 update (5 Oct 00:45):** (a)'s baseline failed in the tool's macro placer (PLACE_DENSITY is also its target
  utilization; MPL-0040); the owner chose (b): `seedB_orfs9_ariane133` (virtual resizing for every run) running. The
  smoke test of `--phase tls` passed (search step and six shifts); `tls_swerv`, `tls_ariane136` running.
- **D2 (b) progress (5 Oct 08:00):** both baseline runs complete and identical (f2: setup WNS -0.059 ns, TNS -12.9 ns,
  DRC 0). Warning for TB#5: the tool's own layout replayed at f2 swings J from 0.74 to 1.88 with one-site shifts, all
  from setup TNS (-0.7 to -53.6 ns; wirelength, vias and power nearly equal): ariane133's f2 J is dominated by timing
  noise under virtual resizing. `tls_ariane136`: no move kept in 8 steps (its start already clears both margins), so
  its six shifts re-run TB#3's candidate (a determinism check); `tls_swerv`: one move kept (step 1), step 5 running.
- **`tls_ariane136` done (5 Oct 10:30):** no move kept in 8 steps; its six shift runs are identical to TB#3's candidate
  replicates (J and setup/hold slack, 6 of 6; local run files `runs/remote/tls_ariane136/.../evals_tls_f2.jsonl`,
  `runs/remote/tb_ariane136/.../evals_tb.jsonl`): the flow is deterministic across jobs and days. On ariane136 the
  timing-aware search leaves the candidate as it is (it passes the D11 (b) gates on all six shifts).
- **D12 (b) registered 14:35 and running** (`reports/trackB_equal_budget_preregistration.md`, campaign EB, EB#1-EB#4
  reserved): DREAMPlace's pick + the campaign's local search (`--phase tls --tls-tag dpls --tls-lambda 0 --tls-seed 0
  --tls-verify-f2 --tls-pick jsafe ...`) vs HeurBridge's candidate (its one-position J_safe pick on all four designs).
  `dpls_a` (bp_fe_top then bp_be_top) since 14:37; `dpls_b` (ariane136) when `tls_swerv` frees its slots; `dpls_c`
  (swerv_wrapper) after `dpls_a` (the scratchpad's `launch_dpls.sh a|b|c`). After each: fetch,
  `python scripts/equal_budget_confirm.py analyze --design <d>` once.
- **D13 (b) trial done (17:00):** `reports/timing_aware_search_trial.md`: ariane136 unchanged; swerv_wrapper lower J
  (0.901 vs 0.927) but not safer at signoff (6 vs 9 of 12 checks). `dpls_b` (ariane136) launched 16:55.
- **State at 17:50 (interim, no result):** `seedB_orfs9_ariane133` 28 of 80 program layouts at f1, all completed, best f1 J
  0.940 (below the tool's replays 0.949-0.956); `dpls_a` bp_fe_top 3 of 8 steps (f1 J 0.951 -> 0.935; kept moves at f2
  0.958 and 0.941, inside the D11 (b) gates against the tool's unshifted replay); `dpls_b` ariane136 step 0. 7 OpenROAD
  runs on 224. Next: `dpls_c` (swerv_wrapper) when `dpls_a` finishes.
- **EB#1 (bp_fe_top) recorded 6 Oct 01:10: failed** (`reports/trackB_equal_budget.md`; p = 0.128 against alpha_j
  0.025). `dpls_a`'s bp_fe_top part was complete (fetched as a partial snapshot: 45 f1 runs, 4 kept moves at f2, the
  pick `bp_fe_top.dpls.s2.f2` (kept move of step 2) at the six shifts). Medians before the gates: HeurBridge 0.905,
  DREAMPlace + local search 0.943; each arm fails hold on one shift. Reported only: the search lifts DREAMPlace's pick
  from 0 to 5 of 6 shifts inside the gates (p = 0.0076 against DREAMPlace alone). At 01:08 `dpls_a` was at bp_be_top
  step 6 of 8 (no move kept), `dpls_b` at ariane136 step 3, `seedB_orfs9_ariane133` in local search (step 2).
- **`dpls_a` done (6 Oct 03:30, rc 0); EB#2 (bp_be_top) recorded 03:35: failed** (`reports/trackB_equal_budget.md`;
  p = 0.79 against alpha_j 0.0125). One move kept (step 6, f1 J 0.832); the pick `bp_be_top.dpls.s6.f2` (J 0.870 at the
  unshifted check, inside both gates). At the six shifts DREAMPlace + local search is lower before the gates (median
  0.956 against HeurBridge's 1.017) but loses two shifts: the flow fails at (-2, 0) (PDN-0179, unable to repair all
  channels; DREAMPlace's own pick fails there too) and hold fails at (0, +2); HeurBridge's candidate passes every gate
  on all six. Reported only: against DREAMPlace alone (one shift inside the gates) p = 0.053.
- **224 slot split (CS-D2 (a), relayed by the cell-placement chat; replaces "`dpls_c` when `dpls_a` finishes" above):**
  macro jobs at most 4 of the 8 OpenROAD slots once running jobs allow. After `dpls_a` the macro jobs reserve 6
  (`seedB_orfs9_ariane133` 4, `dpls_b` 2); `dpls_a`'s 2 slots went to the cell chat's C0 smoke (notice sent 03:35). No
  new macro job until the reserved count is 2 or fewer: `dpls_c` and the TB#5 test start together, within 4 slots,
  after `seedB_orfs9_ariane133` ends (estimate 7 Oct 01:00); `dpls_b` about 14:00 today.

---

## 2026-10-04 — Session 4 (05:00): TB#4 failed; TW#1 passed; DREAMPlace on ariane136 fails the flow so far

- **TB#4 swerv_wrapper failed** (analysed once, 04:51; p = 0.98): before the gates the candidate is not better than the
  tool's layout (median 0.9266 vs 0.9165); setup gate failed on 3 of 6 shifts, one detailed-placement timeout. Track B:
  2 of 4 designs pass. Summary update at the end of `reports/trackB_confirmatory.md`.
- **TW#1 bp_fe_top passed** (analysed once, 02:18, from `tw_a`'s snapshot holding all 22 of bp_fe_top's rows):
  HeurBridge lower than DREAMPlace (p = 0.0022); DREAMPlace's f2 layouts all failed the setup gate, so its pick is the
  best before the gates (density 1.0, seed 2); DREAMPlace vs the tool, reported: p = 0.98.
- **ariane136 (`tw_b`):** DREAMPlace's first four layouts failed the flow's detailed placement at f1 (DPL-0036, 4,540
  instances not placed; one 7,200-s timeout). If no layout completes f1, there is no DREAMPlace replicate and the
  registered analysis records p = 1 for TW#3 (`threeway_confirm.py`: an empty arm gives p = 1); report it as such and
  say why.
- **Running on 224:** `tw_a` (bp_be_top's six shifts), `tw_b` (ariane136 f1), `tw_swerv` (since 04:55, 4 at a time).
  Watch: Monitor with the scratchpad's `monitor_jobs.sh 224 /data/dzy/heura_repr/hb tw_a tw_b tw_swerv`.
- **Next:** for each finished `tw_*` job: fetch, `python scripts/threeway_confirm.py analyze --design <d>` once.
- **05:23 TW#2 bp_be_top** (`tw_a` done 05:20, fetched; TW#1's final rows identical to the snapshot it used): passed
  under the registered rule (p = 0.0011), but before the gates DREAMPlace's layout is the best of the three; its
  replicates fail only the relative hold gate with positive hold slack (notes at the end of `reports/trackB_threeway.md`;
  new D11 evidence). Still running: `tw_b`, `tw_swerv`.
- **13:38 TW#3 ariane136** (`tw_b` done 13:35): failed (p = 0.16); before the gates HeurBridge is the best of the three
  on every replicate; relative gates reject 3 HeurBridge (hold) and 3 DREAMPlace (setup, positive slack) replicates; 9 of
  DREAMPlace's 12 layouts failed the flow at f1. Still running: `tw_swerv`.
- **Owner's decision D11 (4 Oct): option (b) for future Track-B tests**: each replicate's timing gates refer to the
  tool's replicate at the same shift (`heurbridge/eval/cost.same_shift_reference`; fallback when the tool's run there
  failed: the median of its completed replicates in the test). TB#1-TB#4 and TW#1-TW#4 keep D6 as registered.
- **Owner's decision D12 (c) (4 Oct), registered 15:00** (`reports/trackB_programs_preregistration.md`, campaign TP,
  TP#1-TP#4 reserved): HeurBridge's best program layout without local search vs DREAMPlace's pick, gates under D11 (b)
  for both arms. Running on 224: `tp_a` (bp_fe_top then bp_be_top, 2 at a time), `tp_b` (ariane136, 3), `tp_c`
  (swerv_wrapper, 2); after each: fetch, `python scripts/programs_confirm.py analyze --design <d>` once.
- **15:50 TW#4 swerv_wrapper failed** (p = 0.23): the three-way comparison is complete (overall section of
  `reports/trackB_threeway.md`): recorded 2 of 4, only TW#1 a better layout.
- **19:01 D12 (c) complete** (TP#1-TP#4, each analysed once; TP#1 from `tp_a`'s snapshot, final rows identical): TP#1
  bp_fe_top passed (p = 0.0076), TP#2-TP#4 failed; overall section of `reports/trackB_programs_vs_dreamplace.md`. 224 is
  idle. Open for the owner: D13 (a) margin-aware selection for new tests, D13 (b) timing-aware search demo, D2.
- **Timing gates (owner's question):** `reports/timing_margin_explore.md` (exploratory) and D13 in the decision sheet
  (margin-aware selection; timing-aware search demo; DREAMPlace's timing mode).

---

## 2026-10-04 — Session 4 (00:20): Track B's seeding finished; TB#4 and the three-way comparison running

- **swerv_wrapper's campaign finished** (4 Oct 00:15; 132 f1 and 24 f2 runs, fetched). TB#4's candidate fixed by the
  registered rule (`trackb_confirm.py candidate`): swerv_wrapper.ls5.n4 (f2 J 0.8674); addendum in
  `reports/trackB_preregistration.md`. Unlike the other designs it lies above the tool's same-path replays (0.8407-0.8611):
  TB#4 is likely to fail and runs as registered. TB#4 and TW#4 reserved (0.003125 each).
- **Running on 224 (8 OpenROAD runs):** `tb_swerv_wrapper` (TB#4, 12 f2 runs, 4 at a time, about 3.5 h);
  `tw_a` (DREAMPlace through the flow: bp_fe_top then bp_be_top, 2 at a time, about 5 h); `tw_b` (ariane136, 2 at a
  time, about 8 h). Launch commands: the scratchpad's `launch_after_swerv.sh` (tb, tw_a, tw_b, tw_swerv).
- **Next:** when `tb_swerv_wrapper` finishes: fetch, `python scripts/trackb_confirm.py analyze --design swerv_wrapper`
  then `describe`; launch `tw_swerv` (4 at a time). When each `tw_*` job finishes: fetch, then
  `python scripts/threeway_confirm.py analyze --design <d>` once per design (TW#1-TW#4).

---

## 2026-10-03 — Session 4 (23:15): Track-B test results; RL#4 passed; DREAMPlace for Track B; three-way comparison prepared

- **Results (each analysed once):** TB#1 bp_fe_top passed (p = 0.0022), TB#2 bp_be_top passed (p = 0.0011), TB#3
  ariane136 failed (p = 0.53, hold gate on 3 of 6 shifts; before the gates every candidate replicate is below every
  reference replicate); `reports/trackB_confirmatory.md` (summary, then the recorded tables, then the reported-not-tested
  sections from `trackb_confirm.py describe`). TB#1 rests on one replicate exactly at its hold threshold. RL#4 passed
  (p = 0.00014; `reports/portfolio_retest_confirmatory.md`, notes at the end).
- **Local housekeeping:** the Sep-27 development runs `runs/remote/tb_*` (same job names as the test's) were renamed
  `runs/remote/sep27_tb_*` before fetching (nothing cited them).
- **DREAMPlace for Track B:** its standard-cell Abacus pass aborted 15 of 36 runs (an assertion after greedy
  legalization); off by default now (only the macros are used). P_M's grid made the effective spacing 22.8-25.2 um
  instead of 20 um and moved DREAMPlace's packed macros by 2-6 % of the die on ariane136; `--inflate` now gives
  DREAMPlace each macro as P_M's footprint (displacement now <= 0.001 on bp_fe_top). Jobs: `dptb_place2` (old
  inflation, all 48 runs complete), `dptb_place3` (footprints, 227 GPU 0, running).
- **Three-way comparison (owner's D9) registered 23:24** (commit a2c4de7; TW#1-TW#3 reserved, commit 1b6e918):
  `reports/trackB_threeway_preregistration.md`, `scripts/threeway_confirm.py`. HeurBridge's TB candidate vs
  DREAMPlace's pick (`dptb_place3`'s twelve layouts per design; f1 for all, f2 for the best four, the best admitted under
  D6, then the six shifts), the tool reported. The external-layout path was checked first on two campaign layouts
  (`extsmoke_bp_fe_top`: f1 and f2 reproduced exactly). DREAMPlace's layouts are in 224's vault (`dptb3_layouts`).
  Correction recorded in D9: HeurBridge's candidates come from local search scored by the flow itself.
- **Audit done:** `reports/test_audit.md` (`scripts/audit_tests.py --report`): all 46 E0 units scored (median optimism
  +0.00000 J, mean +0.00017); the problems found are listed first. Proposals D11 (same-shift gate reference for future
  Track-B tests) and D12 (equal-budget DREAMPlace comparison) added to the decision sheet.
- **Running:** 224 `seedB_orfs7_swerv_wrapper` (its last f2 run).
- **Next, when swerv's campaign has finished:** fetch it; `python scripts/trackb_confirm.py candidate --design
  swerv_wrapper`, add the result to `CANDIDATES` and to the pre-registration, `reserve` (TB#4), launch
  `tb_swerv_wrapper` (tbtest, 4 workers); `python scripts/threeway_confirm.py reserve --design swerv_wrapper` (TW#4);
  launch `tw_a` (bp_fe_top then bp_be_top, `--after` both campaigns, 2 workers) and `tw_b` (ariane136, 2 workers):
  `--phase extlayouts --ext-dir ext/<d> --ext-tag dp --ext-f2-top 4 --ext-tb`, data `dptb3_layouts:ext`; `tw_swerv`
  (4 workers) when TB#4 has finished. At most 8 OpenROAD runs at a time on 224.

---

## 2026-10-03 — Session 4 (12:00): owner's decisions; Track-B test and RL#4 running; audit of earlier tests

- **Owner (3 Oct):** more effort on Track B; after Track B's seeding, compare DREAMPlace and HeurBridge through the
  OpenROAD flow; D6 (0.02-ns guard, no sign rule); D10 (corrected ISPD2005 re-test).
- **Track-B test (TB#1-TB#3)** registered (commit 2ab085a) and launched 11:52 on 224: `tb_bp_fe_top`,
  `tb_bp_be_top`, `tb_ariane136` (`--resume-from seedB_orfs7_<d> --phase tbtest`, 2 OpenROAD runs each; with
  swerv_wrapper's one, 7 at a time). After each job is fetched: `python scripts/trackb_confirm.py analyze --design <d>`
  once. TB#4 (swerv_wrapper): fix its candidate from its f2 rows under the D6 rule, `reserve`, then run.
- **RL#4** registered (commit 4e2b673); bigblue3 check passed (every macro moves; J about 0.38 there); seven `rc4_*`
  jobs since 11:30. After all are fetched: `python scripts/portfolio_retest_confirm.py analyze` once.
- **Audit of earlier tests** (to be written up in `reports/test_audit.md`): f1 always kept the macros fixed (2,965
  records); IBM tool runs genuine; Track-B imports honoured (52,974 macro placements, y within 0.105 um); E0 not
  degenerate, but its guard and final cost share one f1 run: `e0bias_a` (225 GPU 3) measures the optimism on 48
  rebuilt co-trained layouts. New guard: a tool run that leaves a macro unmoved is a named failure (commit c9f0008).

---

## 2026-10-03 — Session 4 (10:00): ISPD2005 results; the tool never placed ISPD2005's macros (defect, fixed)

- **Analyses (each once, 09:46-09:47):** RL#1 failed (p = 0.88); RL#2 and RL#3 passed their alpha
  (`reports/relink_confirmatory.md`, `density_confirmatory.md`, `portfolio_confirmatory.md`).
- **Defect:** `write_oriented_bookshelf` wrote source terminals as terminal and /FIXED, so DREAMPlace's mixed-size runs
  never moved ISPD2005's macros: on 7 of 8 designs the tool's layout is identical for every seed and density (the
  benchmark's own macro placement after P_M); only bigblue3's source-movable macros were placed. The three tests'
  passes rest on bigblue3 alone and are not evidence. Report: `reports/defect_ispd_tool_runs.md`; fix: commit 157bf21
  (tool inputs free the macros the design keeps movable; f1 unchanged); notes in the ledger and in the ISPD2005
  seeding and E0 reports (J = 0.45 on ISPD2005 is the benchmark's placement).
- **Also done:** density 0.6 on all 13 IBM designs (`dens6_*`): one run at 0.6 vs best of four at 0.9 is borderline
  (61 of 104 lower, p = 0.033); two densities vs two seeds hold (65 lower, 20 higher). Refiner pairs finished
  (`lspairs_*`): local search from the tool's layout, kept 31 of 44, median change -0.0005 (report Section 10).
- **Owner's decisions needed:** D9 (direction), D10 (a corrected ISPD2005 test; recommendation: RL#4, two densities vs
  two seeds on the 7 designs not seen, alpha 0.003125), D6 (hold gate), D8 (staged deletions).

---

## 2026-10-03 — Session 4 (05:45): density effect is design-dependent; nothing helps on top of 0.6; RL#3 registered

- **Density 0.7 on 13 IBM designs** (`dens7_*`, fetched): lower than 0.9 in 67 of 104 cases, losses on ibm01, ibm11,
  ibm13, ibm18. RL#2 (0.6) rests on four favourable designs; it runs as registered.
- **On top of 0.6** (`pass2_*`, `flip06`, `heur06_*`, fetched): second pass, heuristic starts, flip: none helps.
- **RL#3 registered 05:35** (`reports/portfolio_preregistration.md`, alpha 0.00625): two densities {0.9, 0.6} vs two
  seeds at 0.9, computed from RL#1's and RL#2's runs: after all `rlc_*` and `rtd_*` jobs are fetched, run
  `python scripts/relink_confirm.py analyze`, then `python scripts/density_confirm.py analyze` and `... analyze3`, each
  once.
- **Owner's decision needed:** D9 (direction after the Track-A evidence), D6 (hold-gate rule), D8 (staged deletions).

---

## 2026-10-03 — Session 4 (05:10): relinking does not generalize; the tool's target density; RL#2 registered

- **IBM relinking complete** (`relinkall_a`-`_d` fetched): on all 17 designs relinking ties the tool's best of four
  (29 lower, 44 higher of 136). `reports/beat_tool_track_a.md` regenerated (Sections 4-8).
- **New exploratory scripts:** `consensus_eval.py` (matched barycenter of k tool runs: no), `flip_eval.py` (macro
  orientation pass: -0.0017), `warm_tool_eval.py` (the tool started from a layout: a second pass -0.0156),
  `tool_runs.py --target-density` (0.6: -0.0288 against 0.9, beats 0.9's best of four in 29 of 32).
- **RL#2 registered and launched 05:02** (code 7c316f9): `reports/density_preregistration.md`, alpha 0.0125, jobs
  `rtd_bb4` (231 GPU 4), `rtd_bb3`, `rtd_bb2`, `rtd_a34b1` (227 GPUs 0-2), `rtd_a12` (225 GPU 1). Its comparator is
  RL#1's best of four, so `density_confirm.py analyze` runs after both RL#1 and RL#2 jobs are fetched.
- **Running (exploratory):** `pass2_a`-`_c`, `flip06` (second pass and flip on top of density 0.6), `dens7_a`-`_c`
  (density 0.7 on nine more IBM designs). Fetch with `python scripts/hbv.py fetch --port <port> --run <job>`, then
  regenerate the report (`scripts/report_beat_tool.py`).
- **Track B:** `--phase tbtest` added (not launched); D6 is blocked by the hold-gate rule (owner's decision, recorded
  in `reports/next_phase_decisions.md`, D6).
- **Pitfall:** in this zsh, an unquoted variable holding several words is not split: pass multi-job `--after` lists
  and loop specs as separate arguments (two launches printed nothing this session; relaunched).

---

## 2026-10-03 — Session 4 (03:45): confirmatory relinking test registered (RL#1) and launched on ISPD2005

- **Registered before any ISPD2005 run:** `reports/relink_preregistration.md` (commit 5dded6e, pushed); alpha-ledger
  `RL#1` (alpha_1 = 0.025) reserved 03:37 by `python scripts/relink_confirm.py reserve`. Relinking two tool runs
  against the tool's best of four (more compute: four tool runs and four f1 runs against two and five), 8 designs x
  tool seeds 0-7 = 64 units, pick by f1 seed 0, judge by the median of fresh seeds 1-3, one-sided Wilcoxon.
- **Code:** `scripts/relink_eval.py` keeps failed tool runs by seed (+inf candidates, named per row) and writes best
  of 2/3/4 and the method's extra cost; `bridge.data.match_symmetric(block=...)` matches very large interchangeable
  groups blockwise (bigblue2: 14,321 identical macros; bigblue4: 6,150); the default stays exact, and every IBM group
  (at most 362) and every other ISPD2005 group (at most 731) is matched exactly as before.
- **Launched 03:40** (code 5dded6e): `rlc_bb4` (231 GPU 4), `rlc_bb3`, `rlc_bb2`, `rlc_a34` (adaptec3-4) on 227 GPUs
  0-2 next to `relinkall_a`-`_c`, `rlc_a12b1` (adaptec1-2, bigblue1) on 225 GPU 0 next to `lspairs_a`. About 1.5-3.5 h.
- **When every `rlc_*` job is done:** `python scripts/hbv.py fetch --port <port> --run rlc_<tag>` for all five, then
  `python scripts/relink_confirm.py analyze` **once** (it records RL#1's result and refuses a second one) ->
  `reports/relink_confirmatory.md`. Wall-clock is measured while jobs share GPUs; the run counts carry the cost claim.
- **Note:** 227's clock runs about 55 minutes ahead of this Mac's; times in these notes are the Mac's (CST).

---

## 2026-10-03 — Session 4 (03:30): owner's aim "mean J below 0.45, better than the tool on output and cost"

- **Owner (3 Oct):** the first aim is a macro placer with mean J below 0.45, proven better than the tool on output and
  on cost; I decide priorities (recorded in `reports/next_phase_decisions.md`, "Re-prioritization"). Also: use free GPUs
  on other ports.
- **GPU survey:** 227 has 3 idle RTX 3090s (set up from 225's environment, no downloads; encrypted inputs copied with
  matching sha256; smoke test identical to 231's); 231 GPU 4 used (GPUs 0-3 are other users' per the earlier rule);
  224 and 234 have no usable GPU; other ports refuse connections.
- **Results (exploratory):** `reports/beat_tool_track_a.md` (`scripts/report_beat_tool.py` regenerates it from
  `runs/remote/`). Relinking two tool runs is the lead; the frozen bridge on the tool's layout ties with the tool's best
  of two; local-search gains are small but robust on 7 of 12 designs.
- **Running:** `relinkall_a`-`_c` (227 GPUs 0-2), `relinkall_d` (231 GPU 4): tool runs and relinking on 14 designs;
  `lspairs_a`-`_d` (225): refiner pairs. Fetch with `python scripts/hbv.py fetch --port <port> --run <job>`, then
  regenerate the report.
- **Not to forget:** a confirmatory test must use a family untouched by this exploration (ISPD2005), with the f1
  noise handled by fresh-seed medians, and pre-registered before its run.

---

## 2026-10-03 — Session 4 (01:00): ariane133 diagnosed, ariane136 bands, S2 augmentation; progress report updated

- **Owner (3 Oct):** "keep on with the task and update your progress report".
- **ariane133** (`probe133_pd35`, `probe133_virt`, both rc 0; fetched): `reports/trackB_ariane133_diagnosis.md`,
  Sections 3-4. PLACE_DENSITY 0.35 makes 4 of 5 failed layouts evaluable at f1 (the fifth fails with GPL-0307);
  virtual resizing completes all 5 but leaves setup TNS down to -50.7 ns. Recommendation: PLACE_DENSITY 0.35 for every
  ariane133 run including the baseline, then re-run the campaign (decision D2).
- **ariane136 bands** (`seedB_band_ariane136`, rc 0; fetched): report regenerated with `report_trackb_dev.py`; the top
  three candidates' bands, 0.9753-0.9766, lie below the tool's same-path band (from 1.0011). Descriptive.
- **S2:** `s2_aug_225` (augmentation, one change) misses the distance bar (0.777 / 0.611) and the ranking bar (tau
  0.114 / 0.401) (`reports/sketch_predictor_s2_aug.md`); the ranking step first crashed on a bug of mine (the coarse
  placement's info stored under a predictor's key) and was re-run as `s2rank_aug_225`. `s2rank_train2`
  (supplementary, training designs) is in `reports/sketch_predictor_s2_ranking.md`.
- **swerv_wrapper:** still running on 224; its partial snapshot (fetched with `--partial`) shows 101 f1 rows, 32
  completed, and 36 failures that stall like ariane133's.
- **Running now:** only `seedB_orfs7_swerv_wrapper` (224). Every other job of this session is done and fetched.
- **Next:** the owner's decisions D1-D8 in `reports/next_phase_decisions.md` (T5 demo, ariane133, T3.9 endpoint,
  S2, gap experiment, Track-B test, f3 tools, housekeeping).

---

## 2026-10-02 — Session 4 (03:00): next-phase preparation (owner's task brief); English only from now on

- **Owner's requests (2 Oct):** a plan that keeps the LLM step from doing harm; check ariane133; explain the S2
  numbers and either show S2 improving placement or improve S2; then the next-phase brief (P0-P3, English only,
  every number sourced, prepare-only where the owner has not decided).
- **Done (details in each report; the open decisions in `reports/next_phase_decisions.md`):**
  - T5 readiness: `--guard dp`, `--llm perturb` (control arm), identity-free programs, kept sources, held-out endpoint
    and decision script; draft `reports/t5_demo_preregistration.md`; mock smoke test `t5_smoke_mock` on 225 GPU 2,
    rc 0. Nothing ran with the real LLM.
  - Track B: `reports/trackB_ariane133_diagnosis.md` (global placement stalls at overflow about 0.3; the tool's own
    layout shifted by one site stalls too); probes `probe133_pd35`, `probe133_virt` on 224;
    draft `reports/trackB_preregistration.md`.
  - S2: ranking check `reports/sketch_predictor_s2_ranking.md` (fails on ibm04: tau 0.152; holds on ibm06: 0.523);
    one change (augmentation) running as `s2_aug_225`.
  - Gap to the tool: `reports/bridge_target_audit.md` (38 % of training pairs target an elite at or below the tool's
    J), `reports/gap_to_tool_plan.md`.
  - `reports/signoff_anchor_readiness.md` (no f3; ORFS's reference metrics as the external anchor),
    `reports/l1b_handoff_design.md`, failure taxonomy (`reports/PROGRESS.md` Section 8), label-job thread fix.
- **Running (fetch when the watcher reports DONE):**
  - 224 `probe133_pd35`, `probe133_virt`: `python scripts/hbv.py fetch --port 224 --run probe133_pd35` (and `_virt`);
    rows in `runs/remote/<job>/runs/seed_orfs/ariane133/evals_probe_<tag>.jsonl`; then finish the diagnosis report.
  - 224 `seedB_band_ariane136`: fetch, then `python scripts/report_trackb_dev.py --design ariane136 --runs
    runs/remote/seedB_band_ariane136/runs/seed_orfs --archive runs/remote/seedB_band_ariane136/archive_B0_orfs_ariane136
    --label orfs`.
  - 224 `seedB_orfs7_swerv_wrapper`: unchanged.
  - 225 `s2_aug_225`: fetch, then `.venv/bin/python scripts/train_lookahead.py --report
    runs/remote/s2_aug_225/checkpoints/lookahead_s2_aug --out reports/sketch_predictor_s2_aug.md`; its ranking check is
    `runs/remote/s2_aug_225/runs/s2_rank_val_aug/summary.json` (`scripts/eval_lookahead_rank.py --report`).
  - 225 `s2rank_train2` (supplementary ranking on the 13 training designs): fetch and add its summary to the ranking
    report (`--report <val summary> <train summary>`).
- **Housekeeping (owner):** staged folders 68 GB (224), 31 GB (225), 7.1 GB (231); `nvidia-smi` fails on 224 and 227
  (one faulty GPU each); back up the vault key offline. Details: `reports/next_phase_decisions.md` D8.

### T5 demo runbook (protocol: `reports/t5_demo_preregistration.md`; run only after the owner approves it)

Prerequisites: `python scripts/hbv.py push-code --port 225` from the approved commit; GPUs 0-2 free on 225; the server
path of the LLM key file in `$HB_LLM_KEYFILE` (set in `~/.config/heurbridge/servers.sh`, never in the repo).

```bash
# 1. mock smoke test (no LLM; done 2 Oct: rc 0)
python scripts/hbv.py run --port 225 --run t5_smoke_mock --gpu 2 --after seedA_dp_s1 seedA_dp_s2 --data eda_harness:eda bridge_v1_e0_frozen:checkpoints/algR_trackA_final --exclude '(^\./eda/|/dp_work/|^\./checkpoints/)' -- "bash scripts/server/t5_demo.sh smoke"
# 2. real-LLM preflight (at most 2 calls)
python scripts/hbv.py run --port 225 --run t5_preflight --gpu 2 --api-key-file "$HB_LLM_KEYFILE" --after seedA_dp_s1 seedA_dp_s2 --data eda_harness:eda bridge_v1_e0_frozen:checkpoints/algR_trackA_final --exclude '(^\./eda/|/dp_work/|^\./checkpoints/)' -- "bash scripts/server/t5_demo.sh preflight"
# 3. the two arms, in parallel
python scripts/hbv.py run --port 225 --run t5demo_hb --gpu 0 --api-key-file "$HB_LLM_KEYFILE" --after seedA_dp_s1 seedA_dp_s2 --data eda_harness:eda bridge_v1_e0_frozen:checkpoints/algR_trackA_final --exclude '(^\./eda/|/dp_work/|^\./checkpoints/)' -- "bash scripts/server/t5_demo.sh hb"
python scripts/hbv.py run --port 225 --run t5demo_ctrl --gpu 1 --after seedA_dp_s1 seedA_dp_s2 --data eda_harness:eda bridge_v1_e0_frozen:checkpoints/algR_trackA_final --exclude '(^\./eda/|/dp_work/|^\./checkpoints/)' -- "bash scripts/server/t5_demo.sh ctrl"
# 4. after both arms: the endpoint on V (decides) and T (report only)
python scripts/hbv.py run --port 225 --run t5demo_V --gpu 0 --after seedA_dp_s1 seedA_dp_s2 t5demo_hb t5demo_ctrl --data eda_harness:eda bridge_v1_e0_frozen:checkpoints/algR_trackA_final --exclude '(^\./eda/|/dp_work/|^\./checkpoints/)' -- "bash scripts/server/t5_demo.sh eval_V"
python scripts/hbv.py run --port 225 --run t5demo_T --gpu 1 --after seedA_dp_s1 seedA_dp_s2 t5demo_hb t5demo_ctrl --data eda_harness:eda bridge_v1_e0_frozen:checkpoints/algR_trackA_final --exclude '(^\./eda/|/dp_work/|^\./checkpoints/)' -- "bash scripts/server/t5_demo.sh eval_T"
# 5. fetch and apply the pre-registered decision rule
for r in t5demo_hb t5demo_ctrl t5demo_V t5demo_T; do python scripts/hbv.py fetch --port 225 --run $r; done
.venv/bin/python scripts/t5_demo_decision.py --hb runs/remote/t5demo_hb/runs/evo/t5demo_hb --ctrl runs/remote/t5demo_ctrl/runs/evo/t5demo_ctrl --val runs/remote/t5demo_V/runs/evo/t5demo_V --ledger runs/remote/t5demo_hb/logs/llm_ledger.jsonl --out runs/remote/t5demo_decision.json
```

---

## 2026-10-01 — Session 4 (19:30): ariane136 Track-B campaign complete

- **`seedB_orfs7_ariane136` done 19:13 (rc 0).** Report: `reports/T2_trackB_orfs_ariane136.md` (descriptive).
  - 80 program evaluations: 40 completed, 40 failed (3_5_place_dp timeout 18, DPL-0036 17, GPL-0307 5); gates passed
    on 5 of 40.
  - Local search: 48 evaluations.
  - **Signoff (f2), 20 layouts:** all completed, 10 pass every gate. Best admitted J 0.9757 (local search) against
    the unmodified flow's 1.00. The tool's same-path band is 1.0000-1.0089, so 10 admitted layouts sit below it.
  - f1-f2 Kendall 0.937.
  - Candidate noise bands not measured yet. **Launched 19:20: `seedB_band_ariane136`** (224, code 335863a,
    `--resume-from seedB_orfs7_ariane136`, the documented Track-B recipe with `--phase band`): the top 3 admitted
    layouts shifted by one site or row and re-run through f2.
- **Track B status:** bp_fe_top, bp_be_top and ariane136 complete; swerv_wrapper running; ariane133 waiting for the
  owner's decision.

---

## 2026-10-01 — Session 4 (07:30): S2 predictor trained; misses its bar

- **`s2_lookahead_225` (225 GPU 0, code 9366ae1):**
  - Checks: the frozen bridge's sha was checked before and after; core tests 14 passed.
  - Input preparation took 854 s; 20,000 steps; rc 0. Fetched to `runs/remote/s2_lookahead_225`.
- **Report:** `reports/sketch_predictor_s2.md`.
  - Best step 4,000: DA0 ratio ibm04 0.747, ibm06 0.642; closer than quadratic in 239 / 252 of 261.
  - Bar <= 0.5 not met; it overfits after 4k steps.
- **Options, not started (owner's call):**
  - Dihedral and aspect augmentation, as the bridge uses (the S2 training has none).
  - Regularization or a smaller model.
  - Using the predictor where ranking matters rather than precision: the S2 look-ahead check (Kendall of
    predicted vs actual f1 J) is not computed yet.

---

## 2026-10-01 — Session 4 (05:40): S2 labels complete on 234

- **`cell_labels_234` done 05:13**, final archive 2.88 GB. Summarized on 234 by `labels_summary_234`, which
  restores it and reads the shards; the Mac only fetched the summary.
  - **Scale:** 3,838 DREAMPlace placements (CPU, `num_threads` 8) on 15 IBM designs, **0 failures**.
  - **Per design:** 128 bridge endpoints (32 sources x alpha 0.25/0.5/0.75/1), 5 elites, and 104-128 heuristic
    sources.
  - **Clusters:** 512 on ibm01-07, 2,048 on ibm09-18.
- **J tails:** a few placements are extreme (J_max 12.4-13.1 on ibm03/06/07/09; 7.7 on ibm11; 6.0 on ibm15). They are
  heavily congested layouts. They are valid labels, but any J-based loss needs a robust form (rank or log).
- **Wall time:** 23-81 min per design, ~13.5 h in total. The ciphertext is copied to 224's disk vault (sha256 fdbf1ee5..., identical).

---

## 2026-09-30 — Session 4 (23:30): full E0 complete — gate G0′ PASSED

- **Last components:** `e0x_spec_bigblue4_w7` (22:36) and `e0x_eq_bigblue4_w67` (23:18). Checked by counts before
  combining: 24 rows per slice, no duplicates, rc 0. Totals task list 2,430 rows (405 cases), equal guard 2,430,
  IBM held-out 870 (145 cases).
- **Combined** with `e0_combine.py --ledger-entry` (commands in the session scratchpad, `e0_final_combine.sh`).
  - Excluded by design: the wave jobs' empty prepare dirs, and the dead bigblue3 spec slice 2 of the original job
    (11 rows, no meta; re-run as `e0x_spec_bigblue3_r2`).
  - Ledger E0#1-#3 are recorded (`stats/alpha_ledger.jsonl`:22-24).
- **Results (reports/E0_partner_ablation*.md):**
  - E0#1 primary (ISPD2005): bridge 0.5579; memetic 0.5843, repertoire 0.6137, frozen_gen 0.5874, raw 0.5863,
    random_guard 0.5807. Holm p vs memetic 3.3e-65, vs repertoire 2.4e-61: **G0′ PASS**.
  - E0#2 equal guard: p 3.5e-63 / 3.2e-57. E0#3 ibm08/ibm12: p 4.3e-17 / 1.6e-21.
  - Learned direction beats the random-direction control: p 1.3e-59 on ISPD2005.
  - No failed rows.
- **Context for any statement:**
  - Per design the bridge lowers mean J by 1.9-6.9 % against the raw heuristic.
  - Every partner's mean J, and every bridge-refined layout on these designs, stays above 0.45, DREAMPlace's own
    macro placement.
  - The reports' header shows cost_v3 (the reporting code's version); the rows were scored under cost_v2. Track-A J
    is identical under both (`configs/cost.yaml`:3-4).
- **Decision per the pre-registration:** continue to T5 (LLM evolution, deepseek-flash). Per the workflow, a demo
  comes first; waiting for the owner's go.
- `scripts/run_e0.py`'s gate note no longer says the protocol awaits pre-registration. It was a stale string,
  also recorded in the ledger entries' `extra`.

---

## 2026-09-30 — Session 4 (14:45): sketch fine-tune (S1) fails its pass rule; S2 next

- `ft_sketch_ibm2` done 14:09 (rc 0), fetched to `runs/remote/ft_sketch_ibm2`. The ciphertext was also copied to
  224's disk vault (sha256 09840de3..., identical).
- **Report:** `reports/sketch_finetune_s1.md`. The pass rule fails on ibm04 for every model; see CHANGELOG. S2 (the
  dedicated predictor) goes ahead.
- **S2 infrastructure:**
  - `heurbridge/bridge/lookahead.py` (labels) and `DreamplaceEvaluator.evaluate_placed` are committed (b671f21).
  - The label server is 234 (CPU-only, idle, 64 cores). 231's Python env and DREAMPlace are copied to 234 at the
    same paths (`/dev/shm/.hbenv/hb`, `/dev/shm/.hbtools/dreamplace`; env checked: torch 2.6.0, no CUDA).
  - 234 is set up: IBM benchmarks in `/dev/shm/.hbdata/benchmarks`, and the encrypted inputs copied from 231 with
    identical sha256 (`bridge_v1_e0_frozen`, `eda_harness`, the finals of `seedA_dp_s1/s2` and `algR_trackA2`). hbv's
    default root there is `/tmp/.hbv`.
  - `scripts/make_cell_labels.py` (2d210ab): trial `labels_smoke_234` passed. Three ibm01 placements on the CPU took
    25-28 s each, with labels of the expected shapes.
  - **Running on 234 since 15:46: `cell_labels_234`.** 15 designs (13 training and ibm04/ibm06), about 260 layouts
    each, 14 placements at a time. ETA roughly 6-8 h.
  - DREAMPlace's `num_threads` defaults to 8 (not `OMP_NUM_THREADS`), so 14 x 8 threads oversubscribe the 64
    cores (load ~90). That is slower but consistent, and 234 is otherwise idle. Next time use 8 workers or 4
    threads per placement.
  - The watcher now checks 234 too (`J234`).

---

## 2026-09-30 — Session 4 (13:50): bigblue4 spec slice 6 done; ariane133 Track-B campaign yields nothing

- **E0:** `e0x_spec_bigblue4_w6` done 13:45 and checked (counts only): `spec_bigblue4_s6` has 24 rows = 4 cases x 6
  partners, no duplicates, rc 0 (plus the wave's empty prepare dir, excluded as planned). Still running on 225:
  `e0x_spec_bigblue4_w7` (slice 7) and `e0x_eq_bigblue4_w67` (slices 6-7).
- **Track B, ariane133 (`seedB_orfs7_ariane133`, done 10:44, rc 0): no heuristic layout could be evaluated.**
  - f1 ok 0 of 80. Failures: DPL-0036 detailed placement 37, timeout in `3_5_place_dp` 25, no parsed reason 14,
    GPL-0307 divergence 5, PDN-0179 1. The archive holds only the tool's layout (M1 replay f1 J 0.948).
  - That layout's f2 failed a gate (J_raw 5.17), and its one-site-shift replays failed.
  - Our P_M already keeps macros 2 x the flow's halo apart (MACRO_PLACE_HALO 10 10 -> 20 um), so the halo is
    not the cause. Unlike ariane136, ariane133's config sets no PLACE_DENSITY: a lead, not a finding.
  - The other two designs are usable: ariane136 72 of 112 f1 ok, swerv_wrapper 16 of 49 (mostly detailed-placement
    timeouts at 7200 s).
  - Needs the owner's decision: diagnose ariane133 (a flow deviation may be needed), or drop it from Track B as a
    documented deviation.

---

## 2026-09-30 — Session 4 (09:30): demo 2 stopped; bridge backed up; fine-tune running; sketch redesign

- **Demo 2 stopped** (owner: "is the current demo useful now, if not stop it"), 09:14, once ibm04 was complete.
  - Report: `reports/demo_sketch_cells.md`.
  - Result: no start and no cell widening from the sketch helps DREAMPlace, and the sketch is barely closer than a
    quadratic placement (0.235 against 0.253).
  - The inflation arms' first attempt failed on a bug of mine (fractional widths; fixed in 159ee95). The re-run
    `demo_sketch2_infl` was stopped at 22 of 32 ibm04 cases.
- **Bridge backup** (owner: keep a checkpoint before any fine-tune): `bridge_v1_e0_frozen`, sha256
  f95bdde8485316349a1a47b8b1e8115018085f518419f46c903c65f773a525a5, the E0 bridge.
  - Mac: `checkpoints/bridge_v1_e0_frozen/` (read-only, with MANIFEST.json).
  - Vaults: `vault/data/bridge_v1_e0_frozen.tgz.enc` on 224 (disk), 225 and 231. The plaintext was checked by
    decrypting the 225 and 231 copies; 224's ciphertext is identical to 231's.
- **Running on 231 GPU 4: `ft_sketch_ibm2`** (code 1c42f8d, launched 09:35; job file in the session scratchpad, `ft_job2.cmd`).
  The first launch, `ft_sketch_ibm` (88ca4a9), stopped at its DA0 smoke step (exit 11, before any training). With a
  cache, `run_sources` returns every cached source (128 per design) whatever `--seeds` says, and the evaluation sent
  them to the GPU in one batch (out of memory). Fixed: batches of 16, and DA0 places a fixed 32 per design.
  Its full test suite had one failure (the timing local-search test, which relied on a random path that differs
  with the METIS version); the test is now scripted (d586701).
  - Steps: sha guard; tests (core blocking, full suite logged); merge + snapshot check 2ebe74fadcf0; a DA0 smoke run;
    `m1_cluster_pos` (15 designs); fine-tunes `ft_ctrl`, `ft_targets` and `ft_both` (8,000 steps each, a checkpoint
    at every validation); the sha guard again; then `runs/sketch_quality.json` (DA0 with DREAMPlace, f1 J) and
    `runs/sketch_quality_steps.json`.
  - ETA about 13:30-14:00. It is on the watcher's 231 list.
- **Recomputed baseline cell targets** (`m1_cluster_pos`, 14 designs; ibm02 has no baseline in its top 5). J now
  against the archive's (the median of three runs):
  - ibm01, ibm03, ibm04 and ibm07 reproduce the first archived run exactly; ibm10, 11, 13-17 are within 0.2 %.
  - ibm09 (0.4596 against 0.45) and ibm18 (0.4596 against 0.4503) are about 2 % worse. They are ordinary
    placement variation: ibm09's congestion 0.58 % against 0.39-0.52 % on a nearly uncongested design; ibm18's
    wirelength +1 % and congestion 12.2 % against 11.6-11.7 %. Equal J to four decimals is a coincidence: the
    terms differ. The targets are DREAMPlace's placements of those macros either way.
- **Sketch redesign** (owner's question): written in the local plan (unpublished) and the meeting brief.
- **The fine-tune's pass rule, fixed before any result:** on both ibm04 and ibm06, median DA0 ≤ 0.7 × the quadratic
  control's (today 0.93×), and median f1 J no more than 0.5 % above the frozen bridge's.

---

## 2026-09-30 — Session 4 (08:40): bigblue4 slices 0-5 done overnight; watcher failure; last slices launched

- **Watcher failure (my error).** Appending slice 6's job to `watch_extra_225.txt` at 23:10 put a newline into the
  job list, which broke the remote `for` loop of the 225 check; its stderr was discarded, so 225 went unwatched from
  23:15 until 08:20 (224 and 231 were still watched). Every slice 0-5 finished in that window (by ~05:00), so slices
  spec 7 and eq 6/7 were not launched overnight. That cost about 3-7 h on E0's critical path.
  Fixed: the list is flattened to one line, and every server check now ends with a heartbeat; a missing heartbeat
  is reported once as `WATCHER_CHECK_FAILED <host>`.
- **Launched 08:25:** `e0x_spec_bigblue4_w7` (slice 7, GPU 3) and `e0x_eq_bigblue4_w67` (slices 6-7, GPU 2/3; eq
  budget 2230.7). Both are pinned to code 5e1c009 through their plan files. With slice 6 (spec, 14 of 24 rows at
  08:20) that makes 4 slices on 225; 114 GB were free.
- **Checked (counts only):** slices 0-5 of both protocols are complete: 22 cases = 132 rows per protocol, no
  duplicates, one budget per protocol, rc 0. The code-version deviation had no effect: no placer failure and no
  host OOM kill in any slice; the one rerun note (eq slice 3) is a GPU-OOM rerun, which both code versions do.
- **E0 bigblue4 components for the combine:**
  - spec = `e0x_spec_bigblue4` {spec_bigblue4, _s1, _s2, _s3} + `e0x_spec_bigblue4_w45` {_s4, _s5} +
    `e0x_spec_bigblue4_w6` {_s6} + `e0x_spec_bigblue4_w7` {_s7};
  - eq = `e0x_eq_bigblue4` {eq_bigblue4, _s1, _s2, _s3} + `e0x_eq_bigblue4_w45` {_s4, _s5} +
    `e0x_eq_bigblue4_w67` {_s6, _s7};
  - exclude every wave job's empty prepare dir (`spec_bigblue4` / `eq_bigblue4` inside `_w*`).

---

## 2026-09-29 — Session 4 (22:00): new session; ibm12 done; bp_be_top report; watcher moved

- **New session:** the scratchpad moved to `.../2d703b2c-f6de-4a89-b03d-30c5f7b1c57c/scratchpad`. The watcher
  (`watch_events.sh`, its SEEN file), `e0_progress.py`, `e0_timing.py`, `e0split/` and the brief's source were
  copied there. The brief artifact is updated by URL from now on.
- **E0:** `e0x_eq_bigblue1_spec_ibm12` fetched and checked (ibm12 390 rows, rc 0). 14 of 16 parts are complete.
  E0#3 = spec ibm08 (in `e0x_spec_bigblue1_ibm08`) + spec ibm12 (in `e0x_eq_bigblue1_spec_ibm12`).
- **bigblue4 (22:00):** spec slices at 16 rows each (s2 needs 18), eq at 14-15, w45 at 13-14.
- **23:08: spec slice 2 finished** (18 rows, meta). Slice 6 of the task-list protocol was launched in its place,
  one for one, so the load stays at the 12 slices the machine has carried since 11:22; 56 GB were free. Job
  `e0x_spec_bigblue4_w6` (GPU 2, code `5e1c009-20260929112219` verified in its CODE_VERSION; plan and cmd in this
  session's `e0split/`). The next finished slices are replaced the same way: spec 7, then eq 6 and eq 7
  (`make_bigblue4.py wave <spec|eq> <k> <budget>` + `relaunch.py 225 plan_<run>.json`; budgets spec 2259.007,
  eq 2230.7). Add each new job to `watch_extra_225.txt`.
- **Track B:** the bp_be_top report was regenerated (bands, and a warm start that hurts: see CHANGELOG). The
  orfs7 seeding for swerv_wrapper, ariane136 and ariane133 continues (f1 rows 26/82/77).

---

## 2026-09-29 — Session 3 (17:15): timing probes; DREAMPlace sketch demo on 231

- **Timing probes** (224, `--phase timingprobe`; finals `seedB_tprobe2_bp_fe_top`, `seedB_tprobe_bp_be_top`;
  the first `seedB_tprobe_bp_fe_top` failed on `3_place.sdc`, fixed in c1447c2). No macro pin is near-critical
  (see CHANGELOG), so no weighted campaign was run.
- **Launch recipe for Track-B jobs** (band, warm start and probes all used it): `hbv.py run --port 224 --run <job>
  --resume-from <latest final of the design> --snapshot 1800 --exclude "$X" -- "export
  HB_OPENROAD=\$PWD/scripts/server/openroad_676.sh; bash scripts/server/trackb.sh python scripts/run_seed_orfs.py
  --flow /data/dzy/heura_repr/third_party/ORFS-2024-12/flow --design nangate45/<d> --seeds 5 --top 10 --spread 10
  --ls 8 --base-runs 2 --yosys /data/dzy/heura_repr/tools/yosys_048/bin/yosys --archive archive_B0_orfs_<d>
  --phase <phase>"`, with
  `X='(/(objects|results)/[^/]+/[^/]+/([^/]*[.][^/]*|base_r[0-9]+)/|/results/[^/]+/[^/]+/base/([3-6]_|2_[3-9]|2_floorplan)|\.png$)'`
  (it keeps the base run's synthesis and floorplan and drops every candidate variant's databases). The band and
  warm-start finals of a design branch from the same orfs7 final: merge their ledgers locally for one report
  (`runs/remote/seedB_bandws_bp_fe_top`).
- **DREAMPlace sketch demo** (owner's request; 231 GPU 4 by the owner's choice): job `demo_sketch_ibm`,
  `scripts/demo_sketch_start.py`. Inputs are the new small data bundle `sketch_demo_inputs` (IBM seeding baselines
  and clusters, the E0 demo's rows and source caches for ibm04/ibm06), plus `bridge_final` (= the round-1
  checkpoint the E0 demo used, same sha256) and `eda_harness`. Arms: centre / sketch / quadratic. The first case
  reproduces the E0 demo's J to 1e-8. Fetch `hbv.py fetch --port 231 --run demo_sketch_ibm` (231's vault is in
  RAM), summary at `runs/demo_sketch/summary.json`.

---

## 2026-09-29 — Session 3 (16:30): spec bigblue3 done; stage hand-off written; code versions of bigblue4

- **Done and checked:** `e0x_spec_bigblue3_r2` (231, 15:50). The task-list bigblue3 component is `e0x_spec_bigblue3`
  {spec_bigblue3, _s1, _s3} + `e0x_spec_bigblue3_r2` {_s2, _s2b}: 300 rows = 50 x 6, no duplicate, one budget
  845.246 s. **Exclude** the dead `spec_bigblue3_s2` inside `e0x_spec_bigblue3` (11 rows, no meta). 13 of 16 parts
  complete; 231 is idle.
- **Code versions of bigblue4 (for the E0 report's deviations):** slices 0-3 run `9b3c8e8`, slices 4-5 `5e1c009`.
  The only change on the E0 path is that `run_placer` reruns a placer SIGKILLed by the host OOM killer instead of
  scoring the case as failed. Results are identical unless such a kill happens. At combine time, check that no
  placer failure appears in slices 0-3 and no `killed (host out of memory)` note in slices 4-7. Slices 6-7 are
  pinned to `5e1c009-20260929112219` (plan key `code`, passed by `relaunch.py` as `hbv run --code`). **Do not
  push code to 225 before bigblue4 ends** (pinning also guards it).
- **T3.9 extension adopted** (owner, 16:00). Bridge-to-bridge parts go ahead now; anything handed to DREAMPlace or
  OpenROAD waits for G0'. `heurbridge/bridge/handoff.py` + `tests/test_handoff.py` (bc19c89); nothing on the
  evaluation path uses it (tested). The plan is kept local (gitignored).
- **Track B:** `seedB_band_bp_fe_top` done (15:56); `reports/T2_trackB_orfs_bp_fe_top.md` regenerated from it.

---

## 2026-09-29 — Session 3 (15:30): bigblue3 equal guard done; bigblue4 timing; slices 6-7 launch rule

- **Done and checked:** `e0x_eq_bigblue3` (231, 14:44): fetched (`hbv.py fetch --port 231`; 231's vault is in RAM,
  fetch promptly), 4 slice dirs `eq_bigblue3{,_s1,_s2,_s3}` = 300 rows = 50 cases x 6 partners, rc 0, no duplicate,
  one budget 846.566 s (`cache:measured`). With ibm08, adaptec1-4 and bigblue1 x 2: 12 of 16 parts complete.
- **bigblue4 timing (rows' wall_s and file times only):** per case ~4.75 h = placer ~10 min per row, memetic ~44 min,
  repertoire ~58 min, bridge-type partners ~43 min + scoring. Slice sizes (30 sources / 8): 4,4,3,4 | 4,3 | 4,4.
  The 3-case slices (s2, s5) end ~01:00-03:00 on 30 Sep, the others ~06:00-07:30.
- **Launch rule for slices 6-7** (keeps at most 12 bigblue4 slices on 225): after two slices have finished (the
  watcher prints `225 SLICE_DONE <run> <dir>`), `e0split/make_bigblue4.py wave spec 6,7 2259.007` then
  `e0split/relaunch.py 225 plan_e0x_spec_bigblue4_w67.json`; after the next two, the same with `eq 6,7 2230.7`.
  Check `free -g` first (available >= ~40 GB). Add the new job names to `watch_extra_225.txt`.
- **Watcher:** also reports finished bigblue4 slices; a wave job's empty prepare dir is no longer flagged stale.
- **Owner's question (downstream-aware bridges):** answered with a gated plan extending T3.9, in the meeting brief
  (version 9) and in a local proposal document (`HEURBRIDGE_PLAN_*.md`, gitignored: unpublished). Open decision.

---

## 2026-09-28 — Session 3 (20:00): full E0 restarted as slices (user-approved); meeting brief

- **Why:** the full E0 is CPU-bound -- memetic and repertoire each spend the bridge's whole budget per case, and
  every output is scored with DREAMPlace: 10-27 min per case on adaptec1-4/bigblue1, ~77 min on bigblue3. As
  launched, G0' would have come ~5 Oct (bigblue4 ~7 days per protocol).
- **What:** `run_e0.py --slice K/N` (commit 9f38847) splits a component's source list over processes; the budget and
  the random-control scale are fixed once per component (`<cache>/budget_<design>.json`; `--budget-s` carries the
  first measurement over a restart, the scale is recomputed from the bridge's unguarded endpoints). Verified: smoke
  test on ibm04 (`e0smoke_slices`: slices share the budget; recomputed displacements identical, diff 0.0; combine
  OK) and on the restarted components (recomputed scale == the original probe's, bigblue1 0.07522169482228229,
  adaptec2 0.08942288385014388). `e0_combine.py` refuses duplicate cases and mixed budgets. DREAMPlace GPU OOM is
  rerun, not scored (4330c96).
- **Restart (user: "yes, restart the E0 jobs as slices"):** the 8 jobs on 225 and `e0_bigblue3` on 231 were
  stopped (each archived its rows: `e0_*` finals), sources saved encrypted (`save_src_{adaptec4,adaptec3,bigblue1,
  adaptec2,bigblue3,bigblue4}`, identical spec/eq copies by sha256), and relaunched as `e0x_*` jobs with
  `--resume-from` + `--after save_src_*` (scratchpad `e0split/relaunch.py`, command files `e0split/*.cmd`). 225: 16
  processes; 231: bigblue3 spec (budget 845.246 s, carried over) and eq (measures its own), 4 slices each.
  `e0_{spec,eq}_bigblue4` stopped on 231 before any row; bigblue4 runs whole on 225 once its designs finish
  (the encrypted source archive was copied to 225's vault).
- **When everything ends:** fetch the `e0x_*` jobs; E0#1 = `e0_combine.py --runs` all spec slices of the 7 ISPD
  designs `--ledger-entry E0#1` (combine checks duplicates and one budget per design); E0#2 the eq slices; E0#3
  spec ibm08 + ibm12.
  **Which directories (29 Sep):** spec bigblue3 = `e0x_spec_bigblue3` {spec_bigblue3, _s1, _s3} (37 cases; its
  slice 2 was OOM-killed at 22:46 on 28 Sep -- its dir there holds 11 rows and no meta: do NOT include it) +
  `e0x_spec_bigblue3_r2` {spec_bigblue3_s2 (restored 11 rows + the rest of sources 25-31), spec_bigblue3_s2b
  (31-38)}. bigblue4 (30 sources) = `e0x_{spec,eq}_bigblue4` {_bigblue4, _s1, _s2, _s3} + `e0x_{spec,eq}_bigblue4_w45`
  {_s4, _s5} + the later wave for slices 6 and 7 (not the w45 jobs' empty prepare dir). Budgets: spec bigblue4
  2259.007 s, eq 2230.7 s (HB_RUDY_IMPL=bmm for every bigblue4 process). Then `report_e0.py` per entry; commit ledger + reports; T5 only if G0' passes.
- **Track-B noise band** (live, `seedB_orfs7_*`): f2 J over replay + 3 one-site shifts 1.03-1.40 (bp_fe_top),
  1.02-1.16 (bp_be_top), 1.001-1.009 (ariane136); the same-path replay fails the f2 timing gate on 4 of 5 designs
  -> proposal (open, user): reference the f2 gates to the same-path replay.
- **Meeting brief** (private artifact, refreshed 19:00): https://claude.ai/artifact/WEwo1A2vGXnV5a55BrYJAr
- **29 Sep afternoon (user decisions):** cost_v3 -- Track-B timing gates vs the same-path replay (median of replay
  + shifts); 225's reproduction monitors stopped. **225's tmux sessions `agent1`, `agent2`, `tmp` belong to another
  project (`/mnt/nas-new/home/<user>/taorui/auto_project`): never stop them.** Reproduction folders staged in
  `/data/dzy/heura_repr/_to_delete_20260929/` on 224 (68 GB), 225 (31 GB), 231 (7 GB); the user runs the final rm.

---

## 2026-09-28 — Session 3 (16:10): T3.7 done; E0 demo positive; full E0 pre-registered and running

- **T3.7** finished: rounds 0 and 1 promoted, round 2 not -> final checkpoint round 1 (`reports/T3_algorithmR_trackA.md`).
- **E0 demo** (ibm04/ibm06, exploratory): the co-trained bridge has the lowest J under both protocols (spec and equal
  guard), p <= 5e-9 vs memetic/repertoire; the random-direction control is close (0.508 vs 0.482) but beaten
  (p = 2.3e-9) -> much of the gain is the f1 guard, the learned direction adds on top. Reports
  `reports/E0_demo_{spec,eq}.md`.
- **Full E0 pre-registered** (commit d186667, 16:06, `reports/E0_preregistration.md`; ledger E0#1 primary ISPD2005
  task-list protocol, E0#2 equal guard, E0#3 IBM held-out) and **running since 16:08**: 225 GPUs 0-3 (8 slots: the
  five smaller ISPD designs x both protocols, ibm08/ibm12) and 231 GPU 4 (bigblue4 x2, bigblue3 x2); inputs from the
  encrypted bundles `e0_inputs`, `bridge_final`, `eda_harness`; vault excludes the source caches.
- **When the runs end**: fetch all 11 jobs; `e0_combine.py --runs <the 7 ISPD spec runs> --ledger-entry E0#1`, the eq
  runs into E0#2, ibm08/ibm12 into E0#3; `report_e0.py` for each; commit ledger + reports. Then T5 if G0' passes.

---

## 2026-09-28 — Session 3 (13:40): user decisions; T4 E0 demo started (0.14.0)

**User decisions:** LLM = deepseek-flash (code default now); f1 timing gates reported, enforced at f2/f3 (cost_v2);
every experiment first as a demo on 225, then at full capacity if the effect is good (possibly on another server in
parallel -- 231 still needs explicit approval).

**E0 demo** on 225 GPUs 1-3 (`e0demo_{spec,eq}_{ibm04,ibm06}`, CHANGELOG 0.14.0): ibm04/ibm06 are outside the
confirmatory set (held-out ibm08/ibm12 + ISPD2005), so the go/no-go does not peek at the test designs. Results
~18:00-18:30: fetch the four runs, `report_e0.py` per variant, compare spec vs equal guard and the random control.
Then, with the final T3.7 checkpoint: pre-register and launch the full E0 (5 seeds) if the demo points the right way.

**231 approved (user, 2026-09-28) for the full E0.** Only GPU 4 is free; root disk full, so everything lives in RAM
(`/dev/shm`: vault `.hbv`, env `.hbenv/hb` pinned to 225's versions, DREAMPlace for sm_89 in `.hbtools`, benchmarks
`.hbdata`). `setup_231` job builds and smoke-tests it (`scripts/server/setup_231.sh`). A reboot of 231 wipes all of
it: fetch results promptly. Designs are assigned whole to one server (3090 vs 4090 results are not bit-identical).

**Track B** (14:00): continued as `seedB_orfs7_*` on 9546dd4 (cost_v2, noise band). Findings (CHANGELOG "Observed"):
the same-path M1 replay is worse than base M1 (bp_fe_top f2 J 1.32, nearly all TNS) -> pair candidates with the
replay and use the noise band; candidate placement failures come from timing-driven GPL (probe: fine with it off).

**E0 tooling ready** for the full run: `e0_preregister.py` (reserve E0#1-3, write reports/E0_preregistration.md,
commit), per-design `run_e0.py --component E0`, pooled `e0_combine.py --ledger-entry E0#1` (and #2, #3).

---

## 2026-09-28 — Session 3 (11:30): ISPD2005 campaign and E3 done; T3 exit gate passed; T0.3 complete

- **ISPD2005 Track A done** (`reports/T2_trackA_ispd_dreamplace.md`): DREAMPlace's M1 best on all 8 designs;
  bigblue2's programs cannot run (dense macro affinity > 4 GB sandbox; see CHANGELOG). **E3 on ISPD2005**
  (`reports/E3_calibration_trackA_ispd.md`): Kendall 0.54, regret 54 % of random, G0 not met.
- **T3.7 round 0 promoted** (T3 exit gate): on ibm04/ibm06 the f1-guarded bridge's final J 0.4815 vs the raw
  heuristics' 0.8870, paired one-sided Wilcoxon p = 2.6e-9 at alpha_j 0.025 (ledger `algR_trackA#1`). Caveat for the
  report and E0: the guard picks alpha with the same f1 that scores the final cost (alpha = 0 is the raw layout).
  Rounds 1-3 continue (round 1 regenerated the heuristic sources, ~4 h; rounds 2-3 reuse round 0's cache, CHANGELOG).
- **T0.3 complete**: ariane133 through detailed routing on ORFS 2024-12 (ENV_REPORT).
- Track B: failures now named (GRT-0116 congestion on several bp_be_top SA layouts; 2-h timeouts in 5_1_grt).

**Running**: 224 `seedB_orfs6_*` (5 jobs, continuing `seedB_orfs5_*` with `--resume-from`: deterministic-failure
reuse and the same-path M1 control, CHANGELOG); 225 GPU 0 `algR_trackA2` (round 2 of 0-3); 225 GPU 1 free.
Progress against the task list: `reports/PROGRESS.md`.

**Next**: T3.7 report (`report_algr.py`) and the job's new alpha-ledger lines into `stats/alpha_ledger.jsonl`; then
T4 E0 — needs the user's protocol decision (open issue 8: the co-trained bridge's f1 guard vs f0-only partners;
proposal `--equal-guard` + `--random-control` as pre-registered secondary analyses) and the design set (held-out
ibm08/ibm12; ISPD2005 as the held-out family is ~10x the evaluation cost).

---

## 2026-09-28 — Session 3 (00:40): ORFS timeout fix (0.13.2); Track-B campaign restarted

Some candidate layouts (e.g. SA seeds that scatter macros through the core) keep FastRoute in its overflow
"extra run" for hours; the 7,200 s candidate timeout then fires. It would have killed only the top `make` and left
the sub-make and OpenROAD running beside the next candidate (red line A.2). Fixed before any timeout occurred:
`tools.run_group` kills the whole process group; `hbv.py stop` kills the job's session; `hbv.py run --resume` now
keeps the restored files in later archives (both verified on 224). All five ORFS jobs restarted as
`seedB_orfs5_*` (same arguments; ariane133 with `--make-var RTLMP_MAX_LEVEL=1`; new vault exclude pattern that
keeps the base synthesis/floorplan, see SERVER_RUNBOOK).

Expect a slow Track-B campaign: a normal bp_fe_top candidate takes ~10 min to f1, a route-hostile one 2 h
(timeout, recorded as a failure). If the throughput is a problem: split a design's programs across two jobs
(`--programs`; up to 8 parallel jobs are allowed, 5 in use).

**T3.7 rerun** (0.13.3): `algR_trackA` stopped at its first validation on the GPU (bridge inference defaulted to
the CPU while the model was on CUDA; no training step lost). Fixed; `algR_trackA2` restores the cached sources
and pairs (`--after algR_trackA`; preparation ~100 s per design instead of 1,000-2,000 s) and trains on GPU 0.

**Running**: 224 `seedB_orfs5_*` (5 jobs); 225 GPU 0 `algR_trackA2`; 225 GPU 1 `seedA_ispd_s1`, `seedA_ispd_s2`
(adaptec1-4, bigblue1 done: DREAMPlace's M1 is the best layout on each, next best +6.5-17% J).

**Open (for the ISPD2005 report and T5):** on bigblue2 (23,084 movable macros, MMS convention) all 80 program runs
crash with MemoryError in the sandbox: the program view's dense macro affinity `macro_aff` (M x M float64) is
4.3 GB, above the 4 GB sandbox address-space limit (bigblue4: 8,170 macros, 0.53 GB, fine). Recorded by name;
bigblue2's archive holds M1 only. A sparse affinity for very large M would change the program API (T2.1/T5 template).
Track B: SA layouts often fail ORFS's default global route (GRT-0116) or hit the 2-h timeout; failures are named
since 0.13.4.

---

## 2026-09-27 — Session 3 (late night): ariane133 deviation narrowed; ISPD2005 Track-A campaign started

**ariane133**: the halo-8 settings made its M1 converge but failed the 2024-12 PDN (PDN-0179, 6-um channels at the
core edge). `scripts/orfs_probe.py` (floorplan-only probe on 224) shows `RTLMP_MAX_LEVEL=1` alone converges (6 min)
and passes the PDN with every other value from 2024-12; that single setting (upstream 98b961bb3c) is now the
deviation. `seedB_orfs3_ariane133` stopped (logs in `runs/remote/`), `seedB_orfs4_ariane133` running (CHANGELOG).

**ISPD2005 Track A** (T1.7/T2.7, spec tools) on 225 GPU 1, which the IBM campaign freed (so no third GPU is
needed): `seedA_ispd_s1` (adaptec1, bigblue1, bigblue4) and `seedA_ispd_s2` (adaptec2-4, bigblue2, bigblue3), MMS
convention (all 543-23,084 macros movable), `--out runs/seed_trackA_ispd --archive archive_A0_ispd_s{1,2}`.
Estimate ~12 h (IBM18: 23 s per f1; bigblue4 is 10x larger). bigblue2's 23k macros will hit program time caps
(recorded as failures).

**Running**
- 225 GPU 0: `algR_trackA` (T3.7; data preparation at ibm16 of 13 training + 2 validation designs, CPU; then
  3 rounds x 20k steps on the GPU).
- 225 GPU 1: `seedA_ispd_s1`, `seedA_ispd_s2`.
- 224: `seedB_orfs3_{bp_fe_top,bp_be_top}`, `seedB_orfs2_{swerv_wrapper,ariane136}`, `seedB_orfs4_ariane133`.

**Next**: as in the entry below, plus the ISPD2005 report (`report_trackA.py --label ispd_dreamplace`) and merge of
`archive_A0_ispd_s{1,2}`. Open user decisions: T5 LLM model, E0 protocol (open issue 8), timing gates at f1 (9).

---

## 2026-09-27 — Session 3 (night): OpenROAD built from source; Track-A campaign, E3, T3.7 running

**Track A (spec tools) done**: `reports/T2_trackA_ibm_dreamplace.md` (DREAMPlace M1 is strong: programs win only on
ibm02 -- anomalous M1 -- and ibm06) and `reports/E3_calibration_trackA_dreamplace.md` (G0 not met; f1 guard stands).

**Track B tools**: OpenROAD 676f8451 (the ORFS 8ae3ae36 pin) built from source on 224
(`scripts/server/build_openroad.sh`, launcher `openroad_676.sh`, version `676f8451bb-src`); ORFS checkout patched for a
GUI-less build (`patch_orfs.py`). ariane133's tool-native Hier-RTLMP does not converge at 8 threads (MPL-0040 with
both builds): its runs use upstream's later MPL settings via `--make-var` (documented deviation; user may prefer to
exclude it or allow more threads for M1).

**Running**
- 225 GPU 0: `algR_trackA` (T3.7; data preparation, then 20k steps per round, V5 test with DREAMPlace f1).
- 224: `seedB_orfs3_{bp_fe_top,bp_be_top,ariane133}`, `seedB_orfs2_{swerv_wrapper,ariane136}` (ORFS T1.7/T2.7).

**Next**: fetch and report T3.7 (merge the job's new alpha-ledger lines into `stats/alpha_ledger.jsonl`); Track-B
reports per design (`report_trackb_dev.py --runs runs/remote/<job>/runs/seed_orfs --label orfs`) and the f1->f2
calibration; merge the per-design Track-B archives; then T4 (E0, protocol pending the user) and T5 (model pending).

---

## 2026-09-27 — Session 3 (evening): Track B moves to the real ORFS flow; T3.4 done

**Track B = ORFS 2024-12-13 (8ae3ae36) + OpenROAD a008522d8 + Yosys 0.48** (0.13.0). The mini-flow could not be made
ORFS-equivalent on this build (each alignment exposed the next gap; ORFS's kept-resize placement diverges there).
The real flow works: bp_fe_top M1 to 6_report in 15 minutes (setup WNS -0.077 ns, DRC 0). `run_seed_orfs.py` does
the T1.7 baselines and the T2.7 seeding; candidates reuse the base synthesis/floorplan; identical layouts are
evaluated once. In the driver test M2.v0 beat ORFS's own M1 at f2 with every gate passed (J 0.937).

**T3.4 done**: `reports/T3_pretrain_small.md` (checkpoint in the 225 vault as `pretrain_small`).

**Running**
- 224: `seedB_orfs_{bp_fe_top,bp_be_top,swerv_wrapper,ariane133,ariane136}` (hours to days; ariane136's M1 has no
  RTLMP limits and ran > 2 h in the mini-flow — watch it).
- 225 GPU 1: `seedA_dp_s1/_s2` (Track-A spec campaign; ibm17/ibm18 left at 20:10).

**Next**
1. When `seedA_dp_*` end: fetch; `report_trackA.py --label ibm_dreamplace ...`; E3 calibration
   (`calibrate_dev.py`, combined runs dir); launch T3.7 on 225 GPU 0 (command: scratch `algr_cmd.txt`, i.e.
   `--after seedA_dp_s1 seedA_dp_s2 pretrain_small --data eda_harness:eda`, merge the two archives, then
   `algorithm_r.py ... --val ibm04,ibm06 --final dreamplace --pretrained checkpoints/pretrain_small/pretrain_small.pt`;
   ibm08/ibm12 are held back for E0). Merge the job's new alpha-ledger lines into `stats/alpha_ledger.jsonl`.
2. When the ORFS jobs end: fetch; merge `archive_B0_orfs_*`; Track-B report.
3. User decisions still open: T5 LLM model, E0 protocol, a third 225 GPU (ISPD2005).

---

## 2026-09-27 — Session 3 (continued): OpenROAD 2024-12, 225 GPU work, Track B on the servers, DREAMPlace

**User decisions received:** 225's GPUs may be used; the prebuilt OpenROAD 2024-12 package may be downloaded.
(c) — the faulty GPUs on 224/227 — still needs the admin.

**Done (0.11.1 - 0.12.1, CHANGELOG):**
- T0.3: OpenROAD 2.0-17598-ga008522d8 unpacked without root on 224; every required command incl. Hier-RTLMP.
  Flow fixes for this build: virtual timing-driven GPL (it diverged), ORFS density rule (LB_ADDON designs), OpenMP
  capped at 8 threads (**one run exceeded the red line before the cap — disclosed in CHANGELOG 0.12.0**), M1 with 8
  threads as ORFS (bp_fe_top's M1 is identical either way), clock-gate map for swerv_wrapper, fail-fast steps.
- Track B on 224: bp_fe_top M1 at f2 twice, bit-identical, DRC 0 (setup WNS -1.905 ns, TNS -54.9 ns, hold +0.096).
- 225: env `/tmp/.hbenv/hb` (torch 2.6.0+cu118), GPU smoke PASS; a bf16 bug that would have stopped all GPU
  training fixed. **DREAMPlace 4.3.1 built on 225** (`/tmp/.hbtools/dreamplace`); Track-A f1 per spec
  (`DreamplaceEvaluator`, orientations baked, macros FIXED) and M1 = DREAMPlace mixed-size; smoke PASS on ibm01.
- `--final dreamplace` in `algorithm_r.py` / `run_e0.py`; `scripts/report_trackA.py`.
- Unintended write found and fixed: one `.pyc` in the HA-PR harness tree on 224 (remove after `seedA_ibm`).

**Update 16:15:** Track-B flow now follows ORFS for floorplan areas, RTLMP arguments + `-target_util`, synthesis
order and density (CHANGELOG); bp_fe_top's M1 changes with `-target_util`, so all five baselines rerun as `tb5_*` on
224 (fetch: `python scripts/hbv.py fetch --port 224 --run tb5_<design>`); then restart the Track-B seeding
(`seedB_*`). Superseded: `tb3_*`, `tb4_*`, `seedB_bp_fe_top`.

**Running:** 225 GPU 0 `pretrain_small` (T3.4, 200k steps, ~0.048 s/step); 225 GPU 1 `seedA_dp_s1`/`_s2` (Track-A
T1.7/T2.7 with DREAMPlace, 17 IBM designs, ~12 h); 224 `tb3_{ariane133,bp_fe_top,bp_be_top,swerv_wrapper}` (M1 ->
f1 -> f2 x2; ariane133 through detailed routing = the T0.3 Track-B condition); 224 `seedA_ibm` (HB-GP dev
campaign, ibm18 left).

**Next:** ariane136 Track-B baseline; Track-A reports (`report_trackA.py`) when the campaigns end; T3.7 Algorithm R
on 225 with `--final dreamplace --pretrained checkpoints/pretrain_small/pretrain_small.pt` (validation designs to be
fixed in the run's config, e.g. ibm03/ibm06); ISPD2005 Track-A campaign (upload the benchmarks to 225; bigblue4 is
2.2M objects); T2.7 Track-B seeding (programs x seeds at f1, top-10 at f2) once the five baselines exist.

**Decisions for the user:** (1) T5 LLM: `deepseek-v4-pro` (flagship, ~4x the price) or `deepseek-flash` — both think by
default; the old `deepseek-reasoner` name silently maps to flash. (2) The E0 protocol (open issue 8 below) before
T4 is pre-registered. (3) A third 225 GPU for the ISPD2005 campaign (only GPUs 0 and 1 are in use now).

---

## 2026-09-27 — Session 3: server access, encrypted workflow, T0 on 224

**Access.** Key-only SSH works on ports 224, 225, 227, 231, 232, 234 (the lab note `LAB_PORTS_AND_API_KEY.md`
is local-only). The login is shared by several people: everything of ours on the servers goes through
`scripts/hbv.py` (encrypted vault, key on the Mac, RAM workspaces wiped at job end) — see `docs/SERVER_RUNBOOK.md`.
Back up `~/.config/heurbridge/vault.key`: without it the vault cannot be decrypted.

**T0 on 224** (details in ENV_REPORT s.6): T0.1 PASS; T0.4 benchmarks uploaded and verified; T0.6 DeepSeek PASS;
T0.5 env built but **CUDA fails on 224 and 227** (faulty GPU 0 breaks the driver: report to the admin);
**225's four RTX 3090 work but need the user's approval** (A.2); T0.3: conda OpenROAD builds lack Hier-RTLMP and
`place_macro` — a prebuilt 2024-12 package (.deb, unpacked without root) awaits approval to download.

**Running:** `seedA_ibm` on 224 — T1.7/T2.7 Track-A seeding of 17 IBM designs with the deterministic HB-GP f1
(outputs in the vault; `python scripts/hbv.py fetch --port 224 --run seedA_ibm` when done).

**Decisions for the user:** (a) GPU 225 for T3.4 pretraining / T3.7 training; (b) download the prebuilt OpenROAD
package for Track B; (c) ask the admin to reset the faulty GPUs on 224/227.

---

## 2026-09-26 — Session 2: audit of the work so far, Track-B flow fixed and aligned with ORFS, T5 driver

**Server access still blocked** (key-only SSH to 224/227/234: publickey denied), so all work is local.

**Audit findings (each fixed, tested, and in CHANGELOG 0.10.0 / Unreleased)**
- Track-B mini-flow was not ORFS-faithful: placement density 0.6 (ORFS platform default 0.30), core margin 2,
  generic tracks, no tapcells / power grid / port buffers / dont-use. Now layered ORFS config + the ORFS stage
  order (macros -> tapcell -> pdngen -> GP -> resize -> DP -> GRT).
- f1 lost 7 of 18 evaluations: `estimate_parasitics -global_routing` is broken in the local OpenROAD
  (bad_alloc exit, segfault, OOM kill) -> timing/power from placement parasitics for every layout; GR timing
  opt-in. `report_power` segfaulted once the grid existed -> bisected to pdngen's VDD/VSS block pins.
  Every failure is named; the baseline is evaluated 3x (bit-identical at 6 threads; thread count matters).
- FastRoute stopped with GRT-0119 on congested layouts, so OF could never be measured -> `-allow_congestion`.
- P_M: (a) largest-first greedy failed on 0.5% of dense layouts -> fallback orders incl. bottom-left
  packing (1,000/1,000 legal); (b) Track-B spacing must be 2 x MACRO_PLACE_HALO (per-side halo in
  rtl_macro_placer); with 1 x the edge channels broke pdngen on 6 of 16 layouts (PDN-0179).
- V0 certificate rejected every program on real designs (NaN != NaN for unplaced cells) — found by the first
  end-to-end evolution dry run. RLCE groups were unbounded (one 246-macro "group") -> bounded to 8.
- The earlier f0-vs-f1 calibration JSON scored one layout per design -> redone (`scripts/calibrate_dev.py`).
- Run metadata recorded the end-of-run commit with the start-of-run code version -> commit at start.
- Local absolute paths removed from tracked docs; reports relativize paths; dev archives untracked.

**Development results (no claims; stand-ins for the server experiments)**
- T1.1: bookshelf load -> write -> load identity on all 26 designs (`reports/T1_roundtrip_bookshelf.json`).
- E3-lite (one row per distinct layout): f0 J0 (the guard's scorer) vs f1 — Track A (HB-GP,
  `reports/E3_calibration_dev_ibm.md`) Kendall 0.70 / 0.51 / 0.16 on ibm01 / 02 / 03; Track B (mini-flow,
  `reports/E3_calibration_dev_bp_fe_top.md`) Kendall 0.35, top-5 recall 0, f0's pick worse than random. G0 rule
  not met on either track: f0 must not make macro-stage decisions (the spec's f1 guard / fitness stand).
- T3 dev bridge (`reports/T3_bridge_macro_dev.md`): f0 criterion 2.0125 vs raw 2.0411 on ibm03 (91% of sources
  improved) while the validation residual and terminal error rose.
- E0 dev on held-out ibm04 / ibm06 (`reports/E0_partner_ablation_dev.md`; 16 programs x 5 seeds, every partner
  decides on f0, final J = HB-GP f1): G0' dev **FAIL** (co-trained vs memetic p = 0.99, vs repertoire p = 0.68;
  ledger E0_dev#1). The bridge's mean J is lower (0.509 vs raw 0.587) only because it rescues catastrophic
  sources (M5.v1: J 3.45 -> 0.76); paired vs raw it wins 71 / loses 89 (median +0.0004; ibm06: 15 / 40): the
  f0 guard accepts moves that f1 rejects. Portfolio J (best program per design) is the same for all partners
  (0.429-0.432). With the bridge's guard at f1 and the equal f1 guard for the others (E0_dev#2), G0' passes
  (p = 2.1e-5 / 0.0052) — but a random displacement of matched length with the same guard does as well as the
  bridge (geometric-mean J ratio vs raw 0.933 vs 0.931, bridge vs control p = 0.071; E0_dev#3), and HB-GP was
  not reproducible in these runs (winner's curse on noise). **Deterministic rerun with all controls**
  (`reports/E0_partner_ablation_dev_deterministic.md`, E0_dev#4): G0' criterion met (p = 8.6e-5 / 0.0061), the
  learned-transport check inconclusive (bridge vs random direction p = 0.056: 22 : 1 for the bridge on ibm06,
  6 : 11 on ibm04). With a CPU-trained 2-design bridge this is suggestive only; the server E0 decides.
- Track-B dev seeding on bp_fe_top with the corrected flow (`reports/T2_trackB_dev_bp_fe_top.md`): 80/80
  evaluations completed, gates passed on 62% (all failures setup WNS), 15 distinct gated layouts beat the M1
  baseline (J 0.95); best M5.v0 0.8559; dev archive top-5 0.856-0.879 (fidelity 1).
- Track-B f2 verification (`reports/E3_calibration_dev_bp_fe_top_f1f2.md`; ORFS-style staged f2: CTS,
  repair_timing, DRT, OpenRCX): 14/14 layouts routed with DRC 0. f1 -> f2 Kendall 0.50; the f1 gates predict
  the f2 gates badly (10 of 12 f1-passing layouts fail at f2; one f1-failing layout passes). Two layouts beat
  M1 with every f2 gate passed: M4.v2 J 0.959 (gated out at f1) and M3.v0 0.989. The best f2 J (M3.v2 0.9445,
  better setup WNS than M1) fails only because its met hold slack (+0.074 ns) is > 0.02 ns below M1's (+0.095).

**New tools**: `scripts/run_evolution.py` (T5 driver; `--llm mock` dry runs, all five proposers work end to
end), `scripts/run_f2_miniflow.py` + `MiniflowF2Evaluator` (Track-B dev f2: CTS, repair_timing, GRT, DRT,
fill, OpenRCX, STA — untested on the tool yet), `scripts/calibrate_dev.py`, `run_e0.py --guard-fidelity
--equal-guard`.

**Open issues / decisions for the user (additions)**
8. E0 protocol (T4, before it is pre-registered) — supported by the dev runs above: the co-trained bridge's guard sees f1, memetic and
   repertoire decide on f0 only. With a weakly calibrated f0 (Kendall 0.03-0.65 above) the bridge can win
   through the guard's access to f1 alone. Proposal: run E0 with `--equal-guard` (every partner's output
   kept only if it beats the raw layout at the same fidelity) and `--random-control` (the bridge's guard along
   a random displacement of matched length); both are implemented. Also required: reproducible evaluators
   (fixed thread counts; HB-GP was not) and a final cost evaluated independently of the guard's evaluations
   (on the server the f1 guard and the f2 final cost are separate runs, which already satisfies this).
9. Timing gates at f1 — now with f2 evidence: at f1 (pre-CTS, no timing repair) 38% of bp_fe_top layouts fail
   the 0.02 ns setup-WNS gate against M1, but the f1 gates predict the f2 gates badly (10 of 12 f1-passing
   layouts fail at f2, and the best gated f2 layout, M4.v2, was gated out at f1). Proposal: at f1 report the
   gates but rank by J before the gates; enforce the gates at f2/f3 (needs your decision: frozen rule B.3).
   Related: the frozen guard also fails a *met* check whose slack shrinks by > 0.02 ns (hold +0.095 -> +0.074
   ns keeps the best f2 layout out). If that is not intended, a "met stays met" rule for positive baselines is
   the alternative — your call; nothing was changed.
10. The (1+OF) term (open issue 6) is confirmed on Track B: GR overflow 8 against a zero-overflow baseline
    raises J from ~0.95 to 2.14.

---

## 2026-09-25 — Session 1 (later): local Track-B flow, dev bridge training, overflow-proxy fix

**Local Track B (development).** `heurbridge/eval/miniflow.py` runs a minimal Nangate45 flow in the local
OpenLane container (OpenROAD b16bda7e, Yosys 0.38; current ORFS does not run there). On `nangate45/bp_fe_top`:
hierarchical synthesis 15 s, floorplan 4 s, tool-native `rtl_macro_placer` (M1) 285 s, f1 126 s (GR WL 1.758e6 um,
overflow 0, setup WNS -2.20 ns / TNS -310.9 ns pre-CTS, hold +0.086 ns, 0.128 W). Placement/GR results are
deterministic across repeats; the old build segfaults intermittently after GR (evaluator retries once and
records the crash). `place_macro -exact` is not available in this build (made optional).
*[2026-09-26: these are flow-v1 values (density 0.6, no tapcells/power grid, GR-stage timing); superseded —
see the 2026-09-26 entry.]*
```bash
nohup .venv/bin/python scripts/run_seed_miniflow.py --design nangate45/bp_fe_top --seeds 2 > logs/seed_miniflow_bp_fe_top.log 2>&1 &
```
The first attempt failed on every candidate because of `-exact` (a harness bug, recorded as eval_failed);
its records are kept in `runs/seed_miniflow/bp_fe_top/failed_attempt_1/`.

**Track-A overflow proxy fixed.** Raw RUDY overflow in microns made (1+OF)~ explode against zero-overflow
baselines (ibm02 J up to 2e4; an artificial 25% "gain" on ibm03). Proxy is now `rudy_of_pct`; the development
archive was rebuilt from stored records: `archive_dev_v2` (`scripts/rescore_archive.py`). With it the benchmark
macro positions are the best layout on ibm01-03 and the seed heuristics are 1.8-9.5% worse.

**Dev bridge (round 0).** `scripts/train_bridge.py --train ibm01,ibm02 --val ibm03 --archive archive_dev_v2`
(CPU, 1.13M params, 256 pairs). Guarded post-projection f0 on held-out ibm03: 2.0393 / 2.0389 / 2.0322 vs raw
2.0411 at steps 400 / 800 / 1200 (up to 0.44% better; the guard picks alpha > 0 for 40-53% of sources).
Development evidence only (two training designs, f0 criterion); not the T3 exit gate.

**Also added:** ODB loader (verified on nangate45 gcd), V5 promotion gate + H8 null injection, ORFS signoff
stage (f3), MMD^2, Algorithm R driver, report generators, `docs/SERVER_RUNBOOK.md`, T1 baseline table (dev).

**Open issues (additions)**
6. The (1+OF)~ normalization also makes the Track-B J very sensitive when the baseline GR overflow is ~0
   (decision for the user: keep frozen weights, or use e.g. log(1+OF) / an absolute cap).
7. The bridge is not conditioned on x^h (deviation from T3.2, evidence in CHANGELOG 0.3.0).

---

## 2026-09-25 — Session 1 (continued): T0.4 local, T1-T7 software, first development campaign

**Server access is still blocked** (key not authorized), so everything below ran on the Mac. Versions v0.2.0 ..
v0.8.x are on GitHub (`getm0ss1moving/HeurBridge`, tags `v*`); CHANGELOG.md lists every change.

**Done (local, tested; 100+ tests)**
- T0.4 benchmarks on the Mac with sha256 manifests (`configs/manifests/`): IBM-MSwPins bookshelf + LEF/DEF,
  ISPD2005 (originals offline; Drive copy, header statistics match), ORFS Nangate45 macro designs (sparse clone).
- T0.3 probe on the local OpenLane OpenROAD (b16bda7e): every required command and flag present
  (`reports/env/openroad_probe_local_openlane_b16bda7e.txt`). `ENV_REPORT.md` is a draft.
- T1.4 f1 (OpenROAD Track-B script + parser; Track-A metrics; HB-GP dev placer), Track-B ORFS glue
  (`eval/orfs.py`: MACRO_PLACEMENT_TCL injection, stage grt = f1, finish = f2).
- T2.2 seed population (16 programs, V0-certified), T2.5 P_M, T2.6 archive, T2.7 driver (resumable).
- T3 bridge (graph, model, pairs + symmetry matching, loss, trainer, guarded inference); all T3.10 unit tests
  pass. Deviation: no x^h conditioning (evidence in CHANGELOG 0.3.0).
- T4 partners + E0 driver; T5 prompts/skill v0, RLCE, fitness, MAP-Elites, engine with 5 proposers;
  T6.1 online solve (macro stage); T6.2 calibration + gate G0; T7.1 V1 metamorphic tests; T7.2/7.3 stats and
  alpha ledger; T7.5 originality check.

**Development campaign (Track-A stand-in, NOT a pre-registered experiment)**
```bash
.venv/bin/python scripts/run_seed_archive.py --suite ibm --designs ibm01,ibm02,ibm03 --evaluator hbgp \
    --out runs/seed_dev --archive archive_dev --min-fidelity 1
```
Archive `archive_dev/` (labelled DEV, fidelity 1). ibm01 top J: baseline 0.450, best heuristic 0.493;
ibm02: 0.450 / 0.458 (Track-A partial J = 0.30 rWL~ + 0.15 (1+OF)~ with HPWL and RUDY proxies).

**Open issues / decisions for the user**
1. SSH key authorization (blocks T0.1-server, T0.2, T0.3 install, T0.5, and every real f1/f2 run).
2. DeepSeek key: put `DEEPSEEK_LAB_API_KEY` in the server environment (not in chat).
3. Track-A cost: bookshelf designs have no timing/power; J uses rWL (HPWL proxy) + OF (RUDY proxy) only,
   and Track-A archives would admit fidelity-1 elites. Needs your confirmation.
4. HB-GP is a stand-in (not DREAMPlace) and does not converge on ibm18; DREAMPlace must be built on the server.
5. `eda/harness/lef_def.py` orientation handling (CHANGELOG 0.1.0 findings) -- **confirmed 2026-09-26 with
   OpenROAD's pin geometry** (`reports/V3_pin_geometry_vs_openroad.json`: OpenROAD = HeurBridge exactly;
   lef_def +5.25..5.96% on spm). Decision for the user: revise the HA-PR `hpwl_um` numbers or not.

---

## 2026-09-25 — Session 1: T0.1 (local), T1 foundations

**Environment.** Local clone of `github.com/getm0ss1moving/HeurBridge` (git `main`). HA-PR harness: the
English copy `heura_repro_en/eda` next to the repo on the Mac, exported as `$HEURA_EDA_BASE` (the task list's
`papers/heura_repro` no longer exists). Local venv: Python 3.11, torch 2.14 (CPU), PyG 2.8.

**T0.1 inherit state (local): PASS.**
```bash
cd "$HEURA_EDA_BASE"    # the HA-PR harness (English copy)
python3 harness/smoke_test.py            # SMOKE_TEST_PASS
python3 harness/session_status.py        # v2=222, control coverage 46/46
python3 harness/validate_replay_v2.py    # VALIDATE_REPLAY_V2_PASS
python3 harness/build_checkpoint_dataset.py --strict   # 46 decisions / 176 samples / 0 errors
```
Server side (224) pending: SSH key not yet authorized (see open issues).

**T1.1–T1.3, T1.6 (local).** See CHANGELOG 0.1.0. Tests: `.venv/bin/python -m pytest -q tests` → 27 passed.

**Open issues**
1. **Server access blocked.** Password login is not used by the agent. A dedicated key
   `~/.ssh/id_ed25519_heurbridge` was created; the owner must authorize it once:
   `for p in 224 225 226 227 228 229 230 231 232 233 234; do ssh-copy-id -i ~/.ssh/id_ed25519_heurbridge.pub -p $p <user>@<host>; done`.
   Port 223 closed the connection during probing.
2. `lef_def.py` orientation handling (CHANGELOG findings) — verify with OpenROAD `odb` pin coordinates.
3. `DEEPSEEK_LAB_API_KEY` is not set locally; needed for T0.6 and T5.
