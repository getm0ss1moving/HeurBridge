# Cell stage C1: headroom on fixed macro layouts (exploratory)

| Field | Value |
|---|---|
| Report | CS-C1 |
| Date | 6 Oct 2026 |
| Status | **exploratory, fixed before any C1 run**: nothing here is a claim; no alpha is reserved (the alpha-ledger's campaign CS starts with the confirmatory tests, C3) |
| Owner's decisions | CS-D1 to CS-D6, adopted 5 Oct (HANDOFF.md:146-151, :159-160) |
| Track | B (ORFS 2024-12-13 8ae3ae36, OpenROAD 676f8451, Nangate45; ENV_REPORT.md:138-139) |
| Cost | cost_v3's J normalized to the unmodified flow (configs/cost.yaml:3, :12-25) |
| Timing gates | decision D11 (b): each run against the tool's run at the same shift (heurbridge/eval/cost.py:129), 0.02-ns guard |
| Picks | decision D13 (a): lowest J_safe = J + 0.04 (1 - S) over equal positions (heurbridge/cellstage/select.py:40-64) |
| Code | heurbridge/cellstage/, scripts/run_cell_stage.py, configs/cellstage/c1_&lt;design&gt;.json, as committed with this document |
| Inputs | reports/cell_stage_c1_inputs.json, read from the campaigns' files and the fetched DREAMPlace jobs by scripts/cell_stage_inputs.py (local; runs no tool; `--dreamplace runs/remote/cs_c1_dpcells,runs/remote/cs_c1_dpladder`) |

## 1 Question

How much can the cell stage alone move the result of a fixed macro layout? The cell stage is how the flow places
the standard cells around the macros; the question is whether it moves the f2 result beyond the flow's spread over
the Track-B test's six shifts. A second question: does the best cell recipe depend on the macro layout? The go rule in
Section 6 turns the answers into the decision of CS-D4: whether method work beyond the best single recipe (hint
programs, method D) starts.

## 2 Layouts

Eight layouts: the tool's macro layout and HeurBridge's Track-B candidate for each of four designs.

| design | the tool's layout | HeurBridge's layout | campaign (local run files) | Track-B test of the candidate |
|---|---|---|---|---|
| bp_fe_top | M1 | bp_fe_top.ls0.n4.f2 | runs/remote/seedB_orfs7_bp_fe_top | TB#1 passed (reports/trackB_confirmatory.md:43) |
| bp_be_top | M1 | bp_be_top.ls7.n1.f2 | runs/remote/seedB_orfs7_bp_be_top | TB#2 passed (reports/trackB_confirmatory.md:64) |
| ariane136 | M1 | ariane136.ls7.n3.f2 | runs/remote/seedB_orfs7_ariane136 | TB#3 failed (reports/trackB_confirmatory.md:85) |
| swerv_wrapper | M1 | swerv_wrapper.ls5.n4.f2 | runs/remote/seedB_orfs7_swerv_wrapper | TB#4 failed (reports/trackB_confirmatory.md:181) |

- **M1:** the tool's own macro placement from the campaign's baseline, imported through the same path as every
  HeurBridge layout (m1_macros.tcl). No recipe reaches the tool's own macro placement: with an imported layout ORFS
  never runs its macro placer (heurbridge/cellstage/recipe.py:1-7).
- **ariane133:** its two layouts join after the macro chat fixes TB#5's candidate (its D2 (b) campaign is running).
  Its recipe file is written then by the same rules. That campaign already runs every layout with virtual resizing
  (reports/next_phase_decisions.md:196), so R5 equals R0 there.
- **Held out:** the confirmatory tests (C3) will use other macro layouts of these designs (CS-D1 (a); HANDOFF.md:159-160).

## 3 Recipes (12 per design)

Ids are hashes of the settings (heurbridge/cellstage/recipe.py:40-41). Where a recipe has one id for every design,
the settings are identical.

| recipe | what it sets | id | why, and what is expected |
|---|---|---|---|
| R0 default | nothing | 3b8b11b81c3f | the control: the Track-B campaigns and tests ran with it |
| R1 quad_restart | cells start at their cluster's quadratic position; 3_3 restarts from the core centre | f17371a3bb63 | the warm start of the earlier Track-B demos; it shapes only 3_1 and the IO pins (heurbridge/cellstage/recipe.py:23-30) |
| R1c quad_continue | the same start; 3_3 continues from 3_1 (`-skip_initial_place`) | a883991e2010 | the start reaches the main global placement (C0's finding, HANDOFF.md:157-158) |
| R2 density_down | addon 0.05 (bp_fe_top, bp_be_top, swerv_wrapper); PLACE_DENSITY 0.31 (ariane136) | 930f683d3f81; ariane136 772aa9371d43 | one step below the design's own density (below) |
| R3 density_up | addon 0.15; PLACE_DENSITY 0.39 (ariane136) | aa1d57809130; ariane136 30ee7cb5d507 | one step above |
| R4 pad1 | one site of padding each side in global placement (CELL_PAD_IN_SITES_GLOBAL_PLACEMENT=1) | 5c529846ec27 | spreads cells without moving the density target; on ariane136 (absolute density 0.35) the padded cells need about 0.33, an estimate from its baseline's 3_3 log (316,666 um^2 of cells in 171,508 instances: runs/remote/seedB_orfs7_ariane136/runs/orfs_work/logs/nangate45/ariane136/base/3_3_place_gp.log:11, :22; sites 0.19 um wide: third_party/ORFS-2024-12/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef:773); if they do not fit, global placement stops (GPL-0302) and R4 fails there by name |
| R5 virtual_resize | `-keep_resize_below_overflow 0.01` (default 0.3: third_party/OpenROAD-676f8451/src/gpl/include/gpl/Replace.h:200) | 9ee28617d708 | timing-driven iterations undo their resizing while the overflow is above the value (third_party/OpenROAD-676f8451/src/gpl/src/nesterovPlace.cpp:439-440), so almost always. The D2 (b) fix for ariane133's stalls; on its probes every layout completed, two with large setup violations (reports/next_phase_decisions.md:176-178) |
| R6 no_timing | GPL_TIMING_DRIVEN=0 | 147e823f033b | global placement without its timing-driven net weights and virtual resizing |
| R7 rc_target_low | `-routability_target_rc_metric 0.95` (default 1.01: third_party/OpenROAD-676f8451/src/gpl/include/gpl/Replace.h:186) | c7a13e7cde0f | the routability loop stops early once the RC metric is below the target (third_party/OpenROAD-676f8451/src/gpl/src/routeBase.cpp:561-577). **Prediction, recorded now:** R7's rows equal R0's on bp_fe_top and bp_be_top, whose loops never reached 1.01 in the campaigns (below); there they are a determinism check, not a result |
| R8 channel_caps | soft density caps of 50 % over every channel up to 60 um wide (heurbridge/cellstage/hints.py:86-120) | 8949980c97c7 | D's first hand-written family, not tuned. 60 um is three times the tool's own channel width (MACRO_PLACE_CHANNEL 20 um: third_party/ORFS-2024-12/flow/designs/nangate45/bp_fe_top/config.mk:31). Expected to act mainly on HeurBridge's layouts (below) |
| R9 dp_keep | cells start at DREAMPlace's placement around the fixed macros; 3_3 keeps it (`-skip_initial_place -skip_nesterov_place`) | bp_fe_top 7acb6c8ddee1, bp_be_top 6ad5ddb9bf59, ariane136 6bf058f98b56, swerv_wrapper 53ab314c3f20 | an external analytical placement (method F), kept until resizing and detailed placement |
| R9c dp_continue | the same start; 3_3 continues from it | bp_fe_top 6ec846270b8a, bp_be_top 71b60b559256, ariane136 c60aa76d335b, swerv_wrapper 264752bf77a9 | the flow's timing- and routability-driven placement from DREAMPlace's start |

Settings files: configs/cellstage/c1_bp_fe_top.json, c1_bp_be_top.json, c1_ariane136.json, c1_swerv_wrapper.json.

**Density steps (R2, R3).** ORFS sets the density from the lower bound gpl accepts: lower bound + (1 - lower bound) x
addon + 0.01 (third_party/ORFS-2024-12/flow/scripts/util.tcl:153-168). The step of 0.05 in the addon therefore moves
the density by 0.039 (bp_fe_top), 0.036 (bp_be_top) and 0.031 (swerv_wrapper):

| design | own density | lower bound | R2 | R3 | source |
|---|---|---|---|---|---|
| bp_fe_top | 0.310 | 0.222 | 0.271 | 0.349 | reports/cell_stage_c1_inputs.json:6-12 |
| bp_be_top | 0.360 | 0.277 | 0.323 | 0.396 | reports/cell_stage_c1_inputs.json:106-112 |
| ariane136 | 0.35 (fixed) | 0.253 | 0.31 | 0.39 | reports/cell_stage_c1_inputs.json:206-211 |
| swerv_wrapper | 0.456 | 0.385 | 0.425 | 0.487 | reports/cell_stage_c1_inputs.json:309-315 |

For ariane136 the lower bound is gpl's uniform density, the least it accepts (third_party/OpenROAD-676f8451/src/gpl/src/nesterovBase.cpp:1654-1667).

**The routability loop (R7).** Over every 3_3 log of the campaigns:

| design | logs | ended at the 1.01 target | ended after 3 iterations without improvement | lowest FinalRC when it did not reach the target | source |
|---|---|---|---|---|---|
| bp_fe_top | 116 | 0 | 116 | 1.027-1.237 | reports/cell_stage_c1_inputs.json:13-26 |
| bp_be_top | 117 | 0 | 117 | 1.075-1.254 | reports/cell_stage_c1_inputs.json:113-126 |
| ariane136 | 109 | 84 | 25 | 1.014-1.182 | reports/cell_stage_c1_inputs.json:212-229 |
| swerv_wrapper | 117 | 10 | 107 | 1.024-1.316 | reports/cell_stage_c1_inputs.json:316-333 |

The loop also stops after three iterations without improvement (third_party/OpenROAD-676f8451/src/gpl/src/routeBase.cpp:699-710).

**Channels (R8).** ORFS already blocks a band of 10 um around every macro for global placement:
max(halo, channel / 2) for these designs (third_party/ORFS-2024-12/flow/scripts/macro_place_util.tcl:22-24, :70-71).
Its soft blockages have density 0, so global placement uses none of their sites
(third_party/ORFS-2024-12/flow/scripts/placement_blockages.tcl:1-44; a blockage's density defaults to 0:
third_party/OpenROAD-676f8451/src/odb/src/db/dbBlockage.h:84).
A cap acts only beyond that band. The table gives shares of the core area not covered by macros:

| design | layout | caps (rectangles) | all channel area | beyond ORFS's band | source |
|---|---|---|---|---|---|
| bp_fe_top | M1 | 21 | 0.187 | 0.050 | reports/cell_stage_c1_inputs.json:61-65 |
| bp_fe_top | bp_fe_top.ls0.n4.f2 | 17 | 0.135 | 0.059 | reports/cell_stage_c1_inputs.json:91-95 |
| bp_be_top | M1 | 15 | 0.090 | 0.004 | reports/cell_stage_c1_inputs.json:161-165 |
| bp_be_top | bp_be_top.ls7.n1.f2 | 19 | 0.063 | 0.009 | reports/cell_stage_c1_inputs.json:191-195 |
| ariane136 | M1 | 256 | 0.174 | 0.007 | reports/cell_stage_c1_inputs.json:264-268 |
| ariane136 | ariane136.ls7.n3.f2 | 265 | 0.255 | 0.081 | reports/cell_stage_c1_inputs.json:294-298 |
| swerv_wrapper | M1 | 58 | 0.194 | 0.008 | reports/cell_stage_c1_inputs.json:368-372 |
| swerv_wrapper | swerv_wrapper.ls5.n4.f2 | 59 | 0.254 | 0.103 | reports/cell_stage_c1_inputs.json:398-402 |

**DREAMPlace's start (R9, R9c).** DREAMPlace 4.3.1 (ENV_REPORT.md:141; commit 6627f33, ENV_REPORT.md:68) places
every standard cell with the macros held fixed. It runs wirelength-driven with Abacus off, and a moved macro is an
error (heurbridge/cellstage/positions.py:128-159).

Its target density rule:
- The design's own density, where DREAMPlace stops at its overflow target 0.07 without reporting a divergence.
- Otherwise the lowest of 0.4, 0.5, 0.6, 0.7 and 0.8 at which it does so on both of the design's unshifted layouts.

Each start's row records DREAMPlace's iterations, final overflow and whether it converged. A start that did not
converge is used as it is and named in the report.

| design | at its own density (14 layouts) | higher densities (2 unshifted layouts) | DREAMPlace's density | source |
|---|---|---|---|---|
| bp_fe_top | 0.31: all at the 1,000-iteration cap, overflow 0.215-0.217 | 0.4, 0.5: diverged; 0.6: overflow 0.081-0.083; 0.7: converged | 0.7 | reports/cell_stage_c1_inputs.json:444-458, :551-610 |
| bp_be_top | 0.36: all diverged, overflow 0.152-0.156 | 0.4, 0.5: diverged; 0.6: converged | 0.6 | reports/cell_stage_c1_inputs.json:429-443, :476-520 |
| ariane136 | 0.35: all converged (569-607 iterations) | not needed | 0.35 | reports/cell_stage_c1_inputs.json:414-428 |
| swerv_wrapper | 0.46: all converged (511-535 iterations) | not needed | 0.46 | reports/cell_stage_c1_inputs.json:459-473 |

On the two bp designs the start is therefore 1.7 to 2.3 times as dense as the flow's own placement:
- R9 keeps that density into resizing and detailed placement.
- R9c lets the flow spread the cells again.

There is one start file per macro layout, keyed like the ledgers, for the eight layouts and their six shifts (56 in
all). They come from job cs_c1_dpcells2 on 225 and reach 224 as the job's data directory cellpos_c1/<design>.

## 4 Runs

At most 4 OpenROAD runs at a time on 224 (CS-D2 (a)); 7,200 s per step; a failed run is +inf and listed by name.

- **Stage 1 (f1):** every recipe on every layout, unshifted, 96 runs.
  - R9 and R9c run with --check-drift: their started cells' positions after 3_1, 3_3 and 3_5.
  - Cost from the campaigns' median f1 runs (316, 858, 1,885 and 2,677 s; reports/cell_stage_c1_inputs.json:28-33,
    :128-133, :231-236, :335-340): about 38 run-hours, about 10 hours at 4 slots.
- **Stage 2 (f2):** per layout, R0 and the 2 other recipes with the lowest stage-1 J before the gates (failures last,
  ties by id: heurbridge/cellstage/select.py:33-37; scripts/run_cell_stage.py:195-202).
  - They run at the Track-B test's six shifts with its fallbacks (scripts/run_seed_orfs.py:138-139, :180-194):
    96 new runs.
  - Cost from the campaigns' median f2 runs (576, 1,324, 3,419 and 4,011 s; reports/cell_stage_c1_inputs.json:34-39,
    :134-139, :237-242, :341-346): about 62 run-hours, about 16 hours at 4 slots.
  - **R0's 48 positions** are the Track-B test's rows of the same layouts and shifts. Its candidate arm ran R0 on the
    candidate and its reference arm ran R0 on M1, both imported and shifted (evals_tb.jsonl of the tb_<design> runs).
  - **Identity run first:** R0 at f2 on bp_fe_top.ls0.n4.f2 at shift (+2, 0) (`--slots 1`), compared with its
    Track-B row bp_fe_top.tb.cand.s1.f2. If every metric is equal, R0's rows are taken from the Track-B ledgers
    (`--default-rows`: matched by fidelity and exact macro layout, copied with the source ledger and line). If not, R0
    runs at all six shifts on every layout: 48 more runs, about 31 run-hours.
- **Order:** the two smaller designs first. Two designs at a time, 2 workers each, within this chat's free slots.

## 5 Outputs (all reported; nothing claimed)

- **Stage 1:**
  - J before the gates for every recipe and layout.
  - The caps R8 made per layout (count, area: `program_hints` in each row).
  - R9/R9c's drift.
  - R7's prediction checked.
- **Stage 2:**
  - Per layout and recipe, six positions: J before the gates, and the setup and hold checks under D11 (b) against
    the tool's same-shift run (the Track-B reference arm's row at that shift).
  - The summary J, S and J_safe per recipe (select.summarize).
  - The failures each recipe removes or adds.
- **The go rule's parts** (Section 6), whatever the decision.

## 6 Go rule (in code since commit 8f70c70: heurbridge/cellstage/select.py:72-97)

- **Go** if both hold:
  - **(a)** On at least 2 designs, some recipe's whole six-shift band lies below R0's band on a layout. Or some
    recipe completes every shift of a layout on which R0 has a flow failure.
  - **(b)** On at least one design, the J_safe pick differs between its two layouts.
- **Evaluated once,** when stage 2 is complete for the four designs. ariane133's layouts count if they are complete
  by then; otherwise they are reported apart and do not change the decision.
- **Go:** method D (hint programs conditioned on the macro layout) is built, with the best recipe per layout
  (method C) as its control at equal flow-run budget (CS-D3, CS-D4).
- **No go:** the cell stage becomes the best single recipe (engineering), and research effort stays on the macros.
- **Either way:** R1, R1c, R9 and R9c are the input to CS-D5 (whether future tests give imported layouts a warm
  start). The owner decides that after C1.

## 7 Before the first C1 run

- The C0 smoke on bp_fe_top at f1 passes (HANDOFF.md:164-173). It checks three things:
  - the default recipe reproduces the campaign's row of the same layout;
  - the caps' and the routing adjustments' log lines appear;
  - the started cells stay where a kept start puts them.
- 224 has free slots in this chat's share. The macro chat's jobs hold all 8 now. This chat gets 2 when `dpls_a`
  ends and 4 when `dpls_b` ends as well (HANDOFF.md:109-111).

## 8 ariane133 (added 7 Oct 2026, before any of its C1 runs)

The macro chat fixed TB#5's candidate on 7 Oct (commit a55a963), so ariane133's two layouts join C1 under the rules
above. Its inputs are in reports/cell_stage_c1_inputs_ariane133.json; its recipes are in
configs/cellstage/c1_ariane133.json.

- **Layouts:**
  - M1 of the D2 (b) campaign seedB_orfs9_ariane133.
  - TB#5's candidate ariane133.ls5.n5.f2 (runs/remote/seedB_orfs9_ariane133/runs/seed_orfs/ariane133/evals_f2.jsonl:15,
    a local run file).
- **Flow:** every run uses the campaign's make variables, RTLMP_MAX_LEVEL=1 and
  GLOBAL_PLACEMENT_ARGS=-keep_resize_below_overflow 0.01 (reports/cell_stage_c1_inputs_ariane133.json:6-9). The
  runner reads them from the campaign and refuses any other value, so J stays normalized to the same flow.
- **Recipe settings:**
  - R2/R3: PLACE_DENSITY 0.26 and 0.34. The design's own is 0.30 (the platform default), and the lowest gpl accepts
    is 0.245 (reports/cell_stage_c1_inputs_ariane133.json:10-15).
  - R5 equals R0: the campaign already sets the same value.
  - R7 acts here: the routability loop reached the 1.01 target in 83 of 107 logs
    (reports/cell_stage_c1_inputs_ariane133.json:16-33).
  - R8's caps reach 2.8 % of M1's free core area beyond ORFS's band and 7.6 % of the candidate's
    (reports/cell_stage_c1_inputs_ariane133.json:68-72, :98-102).
- **DREAMPlace's start (R9, R9c):** at the design's own density, 0.30, all 14 starts converged (624-645 iterations;
  reports/cell_stage_c1_inputs_ariane133.json:114-128). So R9 and R9c use 0.30 (job cs_c1_dp_a133, in 224's vault as
  cellpos_c1_ariane133).
- **Cost:** f1 and f2 runs take 3,845 s and 4,989 s at the median (reports/cell_stage_c1_inputs_ariane133.json:35-46).
  Stage 1 is about 26 run-hours; stage 2 is about 33.
- **Schedule:**
  - Stage 1 starts once ariane136's and swerv_wrapper's stage 2 have started.
  - Stage 2 needs TB#5's rows of R0, so it starts after TB#5's test ends.
  - As Section 6 says, ariane133 counts for the go rule only if its stage 2 is complete when the other four designs'
    is.
