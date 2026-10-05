# Track B, equal search budget: pre-registration (confirmatory: HeurBridge's programs vs DREAMPlace as the starts of the same flow-scored local search)

| Field | Value |
|---|---|
| Report | trackB_equal_budget_preregistration |
| Date | 2026-10-05 |
| Status | **registered 5 Oct**, before any run of DREAMPlace + local search, under the owner's decisions D12 (b) of 5 Oct (reports/next_phase_decisions.md, D12) and, for tests registered from 4 Oct on, D11 (b) and D13 (a) |
| Track | B (ORFS 2024-12-13 8ae3ae36, OpenROAD 676f8451, Nangate45; ENV_REPORT.md:138-139) |
| Cost | cost_v3's J normalized to the unmodified flow (configs/cost.yaml:3, :12-25); timing gates under D11 (b) (Section 4) |
| alpha-ledger | campaign `EB` (alpha = 0.05; HEURBRIDGE_TASKS.md:541): EB#1 bp_fe_top 0.025, EB#2 bp_be_top 0.0125, EB#3 ariane136 0.00625, EB#4 swerv_wrapper 0.003125, all reserved now |
| Code | scripts/run_seed_orfs.py `--phase tls --tls-tag dpls --tls-lambda 0 --tls-seed 0 --tls-verify-f2 --tls-pick jsafe --tls-start-ledger evals_ext_dp.jsonl --tls-pool-ledger evals_ext_dp.jsonl --tls-pool-programs EXT_DP_F2`; scripts/equal_budget_confirm.py; heurbridge/eval/cost.py `same_shift_reference`; scripts/timing_safety_report.py `position`, `summary`; as committed together with this document |

## 1 Question

At the same flow-scored local search (HeurBridge's campaign search: 8 steps of 6 neighbours at f1, J only), does
starting from HeurBridge's heuristic programs give a better layout at signoff (f2) than starting from DREAMPlace's
placement?

## 2 Arms

- **HeurBridge (programs + local search):** its Track-B candidate. Under D13 (a) with one position (the unshifted f2
  run, its setup and hold checked against the tool's unshifted replay, D11 (b)), its J_safe pick among the campaign's
  f2 layouts is that candidate on all four designs (computed 5 Oct from the local run files
  `runs/remote/seedB_orfs7_<design>/runs/seed_orfs/<design>/evals_f2.jsonl`): bp_fe_top.ls0.n4 (J_safe 0.8809),
  bp_be_top.ls7.n1 (0.9306), ariane136.ls7.n3 (0.9757), swerv_wrapper.ls5.n4 (0.8674). Replicates: the Track-B test's
  candidate replicates (rows `TB_CAND`, jobs `tb_*`, measured 3-4 Oct).
- **DREAMPlace + the same local search (new):** from DREAMPlace's pick of the three-way comparison (its f1 rows:
  bp_fe_top.ext_dp.td1.s2, bp_be_top.ext_dp.td0.8.s1, ariane136.ext_dp.td1.s1, swerv_wrapper.ext_dp.td1.s0; local run
  files `runs/remote/tw_*/runs/seed_orfs/<design>/evals_ext_dp.jsonl`), the campaign's local search: 8 steps of 6
  neighbours at f1 with the campaign's move set (heurbridge/pipeline/seed_archive.py `neighbours`) and random seed 0; a
  step keeps its best neighbour if that neighbour's f1 J before the gates (a failed flow +inf) is lower than the
  current one's; every kept move also runs at f2, unshifted. The pick: the lowest one-position J_safe (D13 (a), as for
  HeurBridge) among DREAMPlace's f2 layouts (3-4 per design) and the kept moves; the pick at the six shifts (rows
  `DPLS_TB`, jobs `dpls_*`).
- **Reported only:** DREAMPlace's pick without the search (rows `EXT_DP_TB`) and the tool (rows `TB_REF`).

## 3 Replicates and endpoint

- **Replicates:** the Track-B test's six shifts (+2, 0), (-2, 0), (0, -1), (0, +2), (+1, +1), (-1, -1) with its fallback
  rule; f2, at most 8 OpenROAD runs at a time on 224 in all, 7,200 s per step.
- **Endpoint, both arms (D11 (b)):** f2 J with every gate enforced; setup and hold against the tool's replicate at the
  same shift with the 0.02-ns guard and no sign rule; where that run failed, the median of the tool's completed
  replicates; a failed gate or flow is +inf.

## 4 Test and decision

- **Per design:** exact one-sided permutation test of the rank sum, HeurBridge lower than DREAMPlace + local search.
- **Pass:** p <= alpha_j. Claim per passing design: "at the same flow-scored search budget, starting from HeurBridge's
  heuristic programs gives a better layout at signoff than starting from DREAMPlace". Overall: k of n designs.
- **Fail:** a negative result for that design; that DREAMPlace + local search is better is not tested; it is reported.
- **Reported, not tested:** DREAMPlace + local search against DREAMPlace alone (what the search adds) and against the
  tool; every replicate's J, J before the gates and gates; the arms' medians; each arm's flow runs and hours.
- **Once:** `equal_budget_confirm.py analyze --design <d>` records the design's result and refuses a second one.

## 5 Limits stated in advance

- **Equal search, unequal starts:** the local search is the same (48 f1 moves); the start stages differ: HeurBridge's
  programs had 80 layouts at f1 and the campaign's f2 stage (20 layouts, local-search layouts included), DREAMPlace 12
  at f1 and 3-4 at f2.
- **Where the moves reach f2:** HeurBridge's campaign search kept moves at f1 and its layouts reached f2 through the f2
  stage (its 10 best f1 layouts and 10 more); DREAMPlace + local search runs every kept move at f2 instead (at most 8).
- **The start:** HeurBridge's search started from its best f1 layout; DREAMPlace's starts from DREAMPlace's pick, as the
  owner's decision says.
- HeurBridge's replicates and DREAMPlace's picks were measured before this registration; nothing of DREAMPlace + local
  search is known. On ariane136 and swerv_wrapper DREAMPlace's pick comes from the 3 of its 12 layouts that completed
  the flow at f1.
- f3 is not available.
