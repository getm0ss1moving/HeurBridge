# Relinking two tool runs vs the tool's best of four: confirmatory result (Track A, ISPD2005)

| Field | Value |
|---|---|
| Report | relink_confirmatory |
| Date | 2026-10-03 09:46 |
| Pre-registration | reports/relink_preregistration.md |
| alpha-ledger | RL#1, alpha_1 = 0.025, reserved 2026-10-03T03:37:52, result recorded 2026-10-03T09:46:37 |
| Status of the claim | **pre-registered confirmatory test: FAILED; also degenerate (defect: see the last section)** |

## Primary test

Paired one-sided Wilcoxon signed-rank on 64 units (design, tool seed), relink lower than best of 4, +inf kept: p = 0.882 against alpha_1 = 0.025; median difference +0.0000; relink lower in 3 units, equal in 57, higher in 4.

## Per design (reported, not tested; mean of the fresh-seed medians over the 8 tool seeds)

| design | single tool run | best of 2 | best of 3 | best of 4 | relink | wall-clock s: relink / best of 4 |
|---|---|---|---|---|---|---|
| adaptec1 | 0.4500 | 0.4500 | 0.4500 | 0.4500 | 0.4500 | 183 / 201 |
| adaptec2 | 0.4503 | 0.4503 | 0.4503 | 0.4503 | 0.4503 | 205 / 230 |
| adaptec3 | 0.4500 | 0.4500 | 0.4500 | 0.4500 | 0.4500 | 262 / 277 |
| adaptec4 | 0.4499 | 0.4499 | 0.4499 | 0.4499 | 0.4499 | 319 / 315 |
| bigblue1 | 0.4500 | 0.4500 | 0.4500 | 0.4500 | 0.4500 | 217 / 234 |
| bigblue2 | 0.4500 | 0.4500 | 0.4500 | 0.4500 | 0.4500 | 1273 / 1130 |
| bigblue3 | 0.4488 | 0.4484 | 0.4479 | 0.4479 | 0.4484 | 809 / 793 |
| bigblue4 | 0.4502 | 0.4502 | 0.4502 | 0.4502 | 0.4502 | 2719 / 2581 |
| **all** | 0.4499 | 0.4498 | 0.4498 | 0.4498 | 0.4498 | 748 / 720 |

Mean J of the relink arm over its 64 finite units: 0.4498, bootstrap 95 % interval 0.4497-0.4500 (reported, not tested; 0.45 is the tool's own seed-0 layout by construction). Wall-clock = tool runs + selection f1 runs (+ the relink candidates' P_M and f1 runs); the fresh-seed endpoint runs are not part of either arm's cost.

Failures (+inf candidates, by name): none.

Sources: runs/remote/rlc_a12b1/runs/relink/adaptec1/rows.jsonl, runs/remote/rlc_a12b1/runs/tool_runs/adaptec1/rows.jsonl, runs/remote/rlc_a12b1/runs/relink/adaptec2/rows.jsonl, runs/remote/rlc_a12b1/runs/tool_runs/adaptec2/rows.jsonl, runs/remote/rlc_a34/runs/relink/adaptec3/rows.jsonl, runs/remote/rlc_a34/runs/tool_runs/adaptec3/rows.jsonl, runs/remote/rlc_a34/runs/relink/adaptec4/rows.jsonl, runs/remote/rlc_a34/runs/tool_runs/adaptec4/rows.jsonl, runs/remote/rlc_a12b1/runs/relink/bigblue1/rows.jsonl, runs/remote/rlc_a12b1/runs/tool_runs/bigblue1/rows.jsonl, runs/remote/rlc_bb2/runs/relink/bigblue2/rows.jsonl, runs/remote/rlc_bb2/runs/tool_runs/bigblue2/rows.jsonl, runs/remote/rlc_bb3/runs/relink/bigblue3/rows.jsonl, runs/remote/rlc_bb3/runs/tool_runs/bigblue3/rows.jsonl, runs/remote/rlc_bb4/runs/relink/bigblue4/rows.jsonl, runs/remote/rlc_bb4/runs/tool_runs/bigblue4/rows.jsonl.

## Defect found after the analysis (3 Oct 2026)

The procedure assumed that the tool places every ISPD2005 macro. It did not: the tool's input marked the macros as fixed terminals, so on adaptec1-4, bigblue1, bigblue2 and bigblue4 every tool run, at either density and with any seed, returned the benchmark's own macro placement, and every arm of this test is the same layout there (the ties above). The result above is as recorded under the registered code, but it rests on bigblue3's 8 units alone and **is not evidence for the registered claim**. Details, evidence and the fix: reports/defect_ispd_tool_runs.md.
