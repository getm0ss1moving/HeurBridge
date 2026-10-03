# Two densities vs two seeds for the tool, corrected re-test: confirmatory result (Track A, ISPD2005)

| Field | Value |
|---|---|
| Report | portfolio_retest_confirmatory |
| Date | 2026-10-03 22:37 |
| Pre-registration | reports/portfolio_retest_preregistration.md |
| alpha-ledger | RL#4, alpha_4 = 0.003125, reserved 2026-10-03T11:19:05, result recorded 2026-10-03T22:37:47 |
| Status of the claim | **pre-registered confirmatory test: PASSED** |

## Primary test

Paired one-sided Wilcoxon signed-rank on 56 units (design, tool seed): the better of the seed-s runs at 0.9 and 0.6 lower than the better of seeds s and s+1 at 0.9, +inf kept: p = 0.000142 against alpha_4 = 0.003125; median difference -0.0060; lower in 33 units, equal in 12, higher in 11. The pick was the run at 0.6 in 37 units.

## Per design (reported, not tested; J against the benchmark's macro placement, 0.45)

| design | one run at 0.9 | one run at 0.6 | two seeds at 0.9 | two densities |
|---|---|---|---|---|
| adaptec1 | 0.4206 | 0.4184 | 0.4162 | 0.4175 |
| adaptec2 | 0.4241 | 0.4207 | 0.4194 | 0.4174 |
| adaptec3 | 0.3848 | 0.3708 | 0.3838 | 0.3708 |
| adaptec4 | 0.3890 | 0.3929 | 0.3884 | 0.3890 |
| bigblue1 | 0.4432 | 0.4352 | 0.4418 | 0.4352 |
| bigblue2 | 0.4187 | 0.3977 | 0.4169 | 0.3977 |
| bigblue4 | 0.5422 | 0.5478 | 0.5051 | 0.5130 |
| **all** | 0.4318 | 0.4262 | 0.4245 | 0.4201 |

Failures (+inf, by name): none.

Sources: runs/remote/rc4_a1/runs/tool_runs_td0.9/adaptec1/rows.jsonl, runs/remote/rc4_a1/runs/tool_runs_td0.6/adaptec1/rows.jsonl, runs/remote/rc4_a2/runs/tool_runs_td0.9/adaptec2/rows.jsonl, runs/remote/rc4_a2/runs/tool_runs_td0.6/adaptec2/rows.jsonl, runs/remote/rc4_a3/runs/tool_runs_td0.9/adaptec3/rows.jsonl, runs/remote/rc4_a3/runs/tool_runs_td0.6/adaptec3/rows.jsonl, runs/remote/rc4_a4/runs/tool_runs_td0.9/adaptec4/rows.jsonl, runs/remote/rc4_a4/runs/tool_runs_td0.6/adaptec4/rows.jsonl, runs/remote/rc4_b1/runs/tool_runs_td0.9/bigblue1/rows.jsonl, runs/remote/rc4_b1/runs/tool_runs_td0.6/bigblue1/rows.jsonl, runs/remote/rc4_bb2/runs/tool_runs_td0.9/bigblue2/rows.jsonl, runs/remote/rc4_bb2/runs/tool_runs_td0.6/bigblue2/rows.jsonl, runs/remote/rc4_bb4/runs/tool_runs_td0.9/bigblue4/rows.jsonl, runs/remote/rc4_bb4/runs/tool_runs_td0.6/bigblue4/rows.jsonl.


## Notes (reported, not tested; written 2026-10-03 22:47)

- **Claim (pre-registered confirmatory, passed):** on the held-out ISPD2005 designs (bigblue3 excluded), with the tool
  placing every macro, two tool runs at target densities 0.9 and 0.6 with the better kept give a lower Track-A J than
  two runs at 0.9 with the better kept, at the same number of runs (reports/portfolio_retest_preregistration.md:46-48;
  p in stats/alpha_ledger.jsonl:41). It is a claim about how to spend the tool's runs, not about a HeurBridge method
  (reports/portfolio_retest_preregistration.md:20).
- **Size of the effect:** small. Median difference -0.0060 J, lower in 33 of 56 units, equal in 12, higher in 11
  (reports/portfolio_retest_confirmatory.md:13); the per-design means of the two arms differ by -0.0044 J overall
  (reports/portfolio_retest_confirmatory.md:26).
- **The tool against the benchmark's macro placement (J 0.45):** one tool run at 0.9 gives a lower J on six designs
  (0.385-0.443) and a higher one on bigblue4 (0.542) (reports/portfolio_retest_confirmatory.md:19-25).
- **Tool input:** the seven jobs ran code with the input fix (commit 157bf21, 09:53) and started at 11:30
  (reports/next_phase_decisions.md:145), before the movement guard was committed (c9f0008, 11:40), so their rows carry no
  count of unmoved macros. Every design's J differs from the frozen-macro values of the defective runs (0.4499-0.4503,
  reports/density_confirmatory.md:19-24, reports/density_confirmatory.md:26) and changes with the seed (the source rows
  below); a direct check of movement was made on bigblue3 only (reports/next_phase_decisions.md:145).
- **Wall-clock (mean seconds per run, measured while jobs shared GPUs; source rows below):**

| design | tool run at 0.9 | tool run at 0.6 | f1 run | method / comparator (two tool runs + two f1 runs) |
|---|---|---|---|---|
| adaptec1 | 38 | 38 | 23 | 123 / 122 |
| adaptec2 | 52 | 53 | 26 | 157 / 156 |
| adaptec3 | 50 | 53 | 31 | 165 / 161 |
| adaptec4 | 72 | 71 | 42 | 227 / 230 |
| bigblue1 | 27 | 28 | 20 | 95 / 94 |
| bigblue2 | 301 | 303 | 36 | 676 / 676 |
| bigblue4 | 484 | 604 | 212 | 1511 / 1389 |

Wall-clock source: the `cost_s` field of every row in the source files listed above.
