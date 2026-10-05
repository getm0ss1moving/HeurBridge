# L1b hand-off, second mechanism: design note (design and dry-run plan only)

| Field | Value |
|---|---|
| Report | l1b_handoff_design |
| Date | 2026-10-02 |
| Status | design only. Nothing has run. A dry run on one design needs the owner's approval and the entry gate of Section 3. |
| Evaluation path | untouched: everything here is an opt-in variant with its own run ids and ledger, never part of E0, T5 or the Track-B campaigns |

## 1 Why a second mechanism

The first port, initial positions, is disproven for DREAMPlace. In demo 1 the sketch start was better in 28 cases
and worse in 36 (p = 0.972, reports/demo_sketch_start.md:34). In demo 2, holding the sketch start made J worse by
+1.4 % (2 better, 21 worse) and cell widening +0.6 % (reports/PROGRESS.md:294-296). DREAMPlace reaches nearly the
same placement from any start (reports/demo_sketch_start.md:41). *Negative results.* A sketch that only predicts the
tool's own result cannot improve it; a hint must prescribe something the tool lacks
(HEURBRIDGE_PLAN_downstream_aware.md:73-86).

## 2 Candidate mechanisms (ports the installed tools honour)

| Mechanism | Port | Needs a tool change? | Source |
|---|---|---|---|
| Routing-capacity reservation where the predicted congestion map exceeds capacity (cell stage, Track B) | OpenROAD `set_global_routing_region_adjustment`, delivered through a variant of the design's `FASTROUTE_TCL` file (ORFS sources it in global routing; bp_fe_top's own file already sets layer adjustments: third_party/ORFS-2024-12/flow/designs/nangate45/bp_fe_top/fastroute.tcl:1-2) | no: a design-config file only | HEURBRIDGE_PLAN_downstream_aware.md:21 |
| Placement padding where the predicted density map shows crowding (Track B) | OpenROAD `set_placement_padding -instances` before global placement | yes: ORFS 2024-12 has a global pad (`CELL_PAD_IN_SITES_GLOBAL_PLACEMENT`) but no per-instance hook in global_place.tcl (third_party/ORFS-2024-12/flow/scripts/global_place.tcl); a hook is a documented flow deviation | HEURBRIDGE_PLAN_downstream_aware.md:20 |
| Route guides (route stage) | OpenROAD `read_guides` | no | HEURBRIDGE_PLAN_downstream_aware.md:22 |
| Net weights or cell sizes (Track A) | DREAMPlace has no external-map port; its routability mode inflates cells from its own map | yes: a code hook in DREAMPlace (a modified tool, reported as such) | HEURBRIDGE_PLAN_downstream_aware.md:17 |
| Density or region hints (Track A) | DREAMPlace fence regions take LEF/DEF input only, not Bookshelf | yes | HEURBRIDGE_PLAN_downstream_aware.md:18 |

**Choice for the first dry run: routing-capacity reservation on Track B.** It is the only mechanism that needs no
tool change, it acts on routing congestion (a term of Track-B J; GRT-0116 congestion is a named failure mode,
reports/T2_trackB_orfs_bp_fe_top.md:88), and Track B is where the plan puts tool hints first
(HEURBRIDGE_PLAN_downstream_aware.md:106).

## 3 Entry gate (fixed now, before anything runs)

A hint derived from a prediction is only worth testing if the prediction is faithful. The dry run starts only when a
cell-stage predictor meets the S2 bar fixed before any S2 result (HEURBRIDGE_PLAN_downstream_aware.md:104):
median DA0 ratio <= 0.5 against the quadratic placement on both validation designs, and Kendall tau(predicted,
actual f1 J) >= 0.5 per design with top-1 regret <= 25 % of random. Today the S2 predictor's DA0 ratios are 0.747
and 0.642 (reports/sketch_predictor_s2.md:38), so the gate is closed. The ranking part is being computed now
(scripts/eval_lookahead_rank.py). A Track-B predictor would need its own labels (ORFS placements); none exist yet.

## 4 Dry run (if the gate opens and the owner approves)

- **Design:** bp_fe_top (complete campaign, measured bands: reports/T2_trackB_orfs_bp_fe_top.md:47, :78-82).
- **Layouts:** the tool's same-path replay and the campaign's best admitted candidate, each with its one-site and
  one-row shifts (the band rule of cost_v3).
- **Arms:** (a) no hint; (b) hint: capacity reserved where the predicted RUDY map exceeds a quantile fixed before the
  run; (c) placebo: the same amount of reserved capacity at randomly permuted map locations.
- **Endpoint:** f2 J (6_report, every gate enforced, failures +inf).
- **Success:** for both layouts, the hint arm's whole band lies below both the no-hint band and the placebo band.
- **Failure:** any overlap: "indistinguishable from noise"; or the hint band lies above: harmful.
- **Compute:** 2 layouts x 4 band members x 3 arms = 24 f2 runs on 224 (at most 8 at a time, 7,200 s per step; the
  f2 run time per layout is not documented in the repo).

Any result is an exploratory demo; it changes no registered protocol.
