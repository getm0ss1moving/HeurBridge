# Timing-aware local search: trial (decision D13 (b), exploratory)

| Field | Value |
|---|---|
| Report | timing_aware_search_trial |
| Date | 2026-10-05 |
| Label | exploratory (no test; two designs; one run each) |
| Code | scripts/run_seed_orfs.py `--phase tls` (default tag tls; `tls_score`), jobs `tls_swerv`, `tls_ariane136`; smoke test `tlssmoke_bp_fe_top` |

**What ran.** From each design's Track-B candidate, HeurBridge's local search with the campaign's move set and budget
(8 steps of 6 neighbours at f1), but a step keeps its best neighbour only if it lowers J plus 0.04 x the share of its two
f1 timing checks (setup, hold) that do not clear the gate threshold by 0.03 ns; the final layout then at the Track-B
test's six shifts at f2 (48 f1 runs per design: local run files
`runs/remote/tls_<design>/runs/seed_orfs/<design>/evals_tls.jsonl`; six f2 runs: `.../evals_tls_f2.jsonl`).

**Results (J and the timing checks of decision D11 (b) at the six shifts; reports/trackB_timing_safety.md, test stage):**

| design | layout | median J | checks passed | J_safe | source |
|---|---|---|---|---|---|
| ariane136 | the Track-B candidate | 0.9761 | 12 of 12 | 0.9761 | reports/trackB_timing_safety.md:143 |
| ariane136 | after the timing-aware search | 0.9761 | 12 of 12 | 0.9761 | reports/trackB_timing_safety.md:147 |
| swerv_wrapper | the Track-B candidate | 0.9266 | 9 of 12 | 0.9366 | reports/trackB_timing_safety.md:186 |
| swerv_wrapper | after the timing-aware search | 0.9014 | 6 of 12 | 0.9214 | reports/trackB_timing_safety.md:190 |

- **ariane136:** no move was kept in 8 steps: the candidate already cleared both margins at f1 and no neighbour scored
  lower. Its six shift runs repeat the Track-B test's candidate replicates exactly (J and slacks, 6 of 6): the flow is
  deterministic across jobs and days.
- **swerv_wrapper:** one move was kept (step 1, score 0.8313 -> 0.8196). At signoff its median J is lower than the
  candidate's (0.9014 against 0.9266; the tool's replicates 0.9165), but it is not safer: two of its six shifts timed
  out in detailed placement (7,200 s) and two more fail setup, against one timeout and one setup failure for the
  candidate.
- **Reading:** a margin at f1 did not carry over to timing at f2 on swerv_wrapper; on ariane136 there was nothing to gain.
  As a way to pass the gates more often, this trial gives no support; on swerv_wrapper it found a lower-J layout.
  Exploratory: one run per design, not a test.
