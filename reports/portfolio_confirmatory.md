# Two densities vs two seeds for the tool: confirmatory result (Track A, ISPD2005)

| Field | Value |
|---|---|
| Report | portfolio_confirmatory |
| Date | 2026-10-03 09:47 |
| Pre-registration | reports/portfolio_preregistration.md |
| alpha-ledger | RL#3, alpha_3 = 0.00625, reserved 2026-10-03T05:27:51, result recorded 2026-10-03T09:47:08 |
| Status of the claim | **pre-registered confirmatory test: PASSED** |

## Primary test

Paired one-sided Wilcoxon signed-rank on 64 units: the better of the seed-s runs at 0.9 and 0.6 (by the selection seed) lower than the best of seeds s and s+1 at 0.9, +inf kept: p = 0.00586 against alpha_3 = 0.00625; median difference +0.0000; lower in 8 units, higher in 0. The pick was the run at 0.6 in 64 units.

| design | best of 2 seeds at 0.9 | two densities |
|---|---|---|
| adaptec1 | 0.4500 | 0.4500 |
| adaptec2 | 0.4503 | 0.4503 |
| adaptec3 | 0.4500 | 0.4500 |
| adaptec4 | 0.4499 | 0.4499 |
| bigblue1 | 0.4500 | 0.4500 |
| bigblue2 | 0.4500 | 0.4500 |
| bigblue3 | 0.4484 | 0.4414 |
| bigblue4 | 0.4502 | 0.4502 |
| **all** | 0.4498 | 0.4490 |

Failures (+inf, by name): none.

Sources: runs/remote/rtd_a12/runs/tool_runs_td0.6/adaptec1/rows.jsonl, runs/remote/rlc_a12b1/runs/relink/adaptec1/rows.jsonl, runs/remote/rlc_a12b1/runs/tool_runs/adaptec1/rows.jsonl, runs/remote/rtd_a12/runs/tool_runs_td0.6/adaptec2/rows.jsonl, runs/remote/rlc_a12b1/runs/relink/adaptec2/rows.jsonl, runs/remote/rlc_a12b1/runs/tool_runs/adaptec2/rows.jsonl, runs/remote/rtd_a34b1/runs/tool_runs_td0.6/adaptec3/rows.jsonl, runs/remote/rlc_a34/runs/relink/adaptec3/rows.jsonl, runs/remote/rlc_a34/runs/tool_runs/adaptec3/rows.jsonl, runs/remote/rtd_a34b1/runs/tool_runs_td0.6/adaptec4/rows.jsonl, runs/remote/rlc_a34/runs/relink/adaptec4/rows.jsonl, runs/remote/rlc_a34/runs/tool_runs/adaptec4/rows.jsonl, runs/remote/rtd_a34b1/runs/tool_runs_td0.6/bigblue1/rows.jsonl, runs/remote/rlc_a12b1/runs/relink/bigblue1/rows.jsonl, runs/remote/rlc_a12b1/runs/tool_runs/bigblue1/rows.jsonl, runs/remote/rtd_bb2/runs/tool_runs_td0.6/bigblue2/rows.jsonl, runs/remote/rlc_bb2/runs/relink/bigblue2/rows.jsonl, runs/remote/rlc_bb2/runs/tool_runs/bigblue2/rows.jsonl, runs/remote/rtd_bb3/runs/tool_runs_td0.6/bigblue3/rows.jsonl, runs/remote/rlc_bb3/runs/relink/bigblue3/rows.jsonl, runs/remote/rlc_bb3/runs/tool_runs/bigblue3/rows.jsonl, runs/remote/rtd_bb4/runs/tool_runs_td0.6/bigblue4/rows.jsonl, runs/remote/rlc_bb4/runs/relink/bigblue4/rows.jsonl, runs/remote/rlc_bb4/runs/tool_runs/bigblue4/rows.jsonl.

