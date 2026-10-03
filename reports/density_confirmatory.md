# One tool run at target density 0.6 vs the tool's best of four at 0.9: confirmatory result (Track A, ISPD2005)

| Field | Value |
|---|---|
| Report | density_confirmatory |
| Date | 2026-10-03 09:46 |
| Pre-registration | reports/density_preregistration.md |
| alpha-ledger | RL#2, alpha_2 = 0.0125, reserved 2026-10-03T05:02:00, result recorded 2026-10-03T09:46:53 |
| Status of the claim | **pre-registered confirmatory test: PASSED** |

## Primary test

Paired one-sided Wilcoxon signed-rank on 64 units (design, tool seed), one run at density 0.6 lower than the best of four at 0.9, +inf kept: p = 0.00586 against alpha_2 = 0.0125; median difference +0.0000; lower in 8 units, higher in 0.

## Per design (reported, not tested)

| design | density 0.9, one run | density 0.9, best of 4 | density 0.6, one run | wall-clock s: one run at 0.6 / best of 4 at 0.9 |
|---|---|---|---|---|
| adaptec1 | 0.4500 | 0.4500 | 0.4500 | 50 / 201 |
| adaptec2 | 0.4503 | 0.4503 | 0.4503 | 55 / 230 |
| adaptec3 | 0.4500 | 0.4500 | 0.4500 | 70 / 277 |
| adaptec4 | 0.4499 | 0.4499 | 0.4499 | 76 / 315 |
| bigblue1 | 0.4500 | 0.4500 | 0.4500 | 41 / 234 |
| bigblue2 | 0.4500 | 0.4500 | 0.4500 | 270 / 1130 |
| bigblue3 | 0.4488 | 0.4479 | 0.4414 | 199 / 793 |
| bigblue4 | 0.4502 | 0.4502 | 0.4502 | 648 / 2581 |
| **all** | 0.4499 | 0.4498 | 0.4490 | 176 / 720 |

Wall-clock = tool runs + selection f1 runs (one of each for the method, four of each for the comparator), measured while jobs shared GPUs; the fresh-seed endpoint runs belong to neither arm.

Failures (+inf, by name): none.

Sources: runs/remote/rtd_a12/runs/tool_runs_td0.6/adaptec1/rows.jsonl, runs/remote/rlc_a12b1/runs/relink/adaptec1/rows.jsonl, runs/remote/rlc_a12b1/runs/tool_runs/adaptec1/rows.jsonl, runs/remote/rtd_a12/runs/tool_runs_td0.6/adaptec2/rows.jsonl, runs/remote/rlc_a12b1/runs/relink/adaptec2/rows.jsonl, runs/remote/rlc_a12b1/runs/tool_runs/adaptec2/rows.jsonl, runs/remote/rtd_a34b1/runs/tool_runs_td0.6/adaptec3/rows.jsonl, runs/remote/rlc_a34/runs/relink/adaptec3/rows.jsonl, runs/remote/rlc_a34/runs/tool_runs/adaptec3/rows.jsonl, runs/remote/rtd_a34b1/runs/tool_runs_td0.6/adaptec4/rows.jsonl, runs/remote/rlc_a34/runs/relink/adaptec4/rows.jsonl, runs/remote/rlc_a34/runs/tool_runs/adaptec4/rows.jsonl, runs/remote/rtd_a34b1/runs/tool_runs_td0.6/bigblue1/rows.jsonl, runs/remote/rlc_a12b1/runs/relink/bigblue1/rows.jsonl, runs/remote/rlc_a12b1/runs/tool_runs/bigblue1/rows.jsonl, runs/remote/rtd_bb2/runs/tool_runs_td0.6/bigblue2/rows.jsonl, runs/remote/rlc_bb2/runs/relink/bigblue2/rows.jsonl, runs/remote/rlc_bb2/runs/tool_runs/bigblue2/rows.jsonl, runs/remote/rtd_bb3/runs/tool_runs_td0.6/bigblue3/rows.jsonl, runs/remote/rlc_bb3/runs/relink/bigblue3/rows.jsonl, runs/remote/rlc_bb3/runs/tool_runs/bigblue3/rows.jsonl, runs/remote/rtd_bb4/runs/tool_runs_td0.6/bigblue4/rows.jsonl, runs/remote/rlc_bb4/runs/relink/bigblue4/rows.jsonl, runs/remote/rlc_bb4/runs/tool_runs/bigblue4/rows.jsonl.

