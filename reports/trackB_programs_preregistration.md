# Track B, HeurBridge's programs without local search against DREAMPlace: pre-registration (confirmatory)

| Field | Value |
|---|---|
| Report | trackB_programs_preregistration |
| Date | 2026-10-04 |
| Status | **registered 4 Oct**, before any run of the program picks' shifts, under the owner's decisions of 4 Oct: D12 (c) (reports/next_phase_decisions.md:310-312) and D11 (b) for tests registered from now on (reports/next_phase_decisions.md:293-299) |
| Track | B (ORFS 2024-12-13 8ae3ae36, OpenROAD 676f8451, Nangate45; ENV_REPORT.md:138-139) |
| Cost | cost_v3's J normalized to the unmodified flow (configs/cost.yaml:3, :12-25); timing gates under D11 (b) (Section 4) |
| alpha-ledger | campaign `TP` (alpha = 0.05; HEURBRIDGE_TASKS.md:541): TP#1 bp_fe_top 0.025, TP#2 bp_be_top 0.0125, TP#3 ariane136 0.00625, TP#4 swerv_wrapper 0.003125, all reserved now |
| Code | scripts/run_seed_orfs.py (`--phase tbtest --tb-arms cand --tb-tag pg`, scripts/run_seed_orfs.py:444-461), scripts/programs_confirm.py, heurbridge/eval/cost.py:129-141 (`same_shift_reference`), as committed together with this document |

## 1 Question

Through the same OpenROAD flow, at signoff (f2), does HeurBridge's best heuristic-program layout, without any
local-search move (so without the search that scores layouts with the flow itself), beat DREAMPlace's macro placement?

## 2 What exists (descriptive)

- DREAMPlace's picks and their replicates at the six shifts (the three-way comparison, reports/trackB_threeway.md; jobs
  `tw_a`, `tw_b`, `tw_swerv`), the tool's replicates and HeurBridge's local-search candidates' replicates (the Track-B
  test, reports/trackB_confirmatory.md; jobs `tb_*`). They were measured before this registration.
- No program pick below has been run at the six shifts.

## 3 Arms

- **Programs:** per design the campaign's best program layout at f2, picked by the rule of DREAMPlace's pick
  (scripts/run_seed_orfs.py `ext_pick`): among the campaign's f2 rows of program layouts (neither the tool's replay nor
  a local-search move), the best admitted under D6, else the best J before the gates, else the best program by f1.
  Computed now from the stored rows (`programs_confirm.py pick`; local run files
  `runs/remote/seedB_orfs7_<design>/runs/seed_orfs/<design>/evals_f2.jsonl`):

| design | program layouts at f2 | pick | f2 J before the gates | rule |
|---|---|---|---|---|
| bp_fe_top | 6 | bp_fe_top.M3.v0.s2 | 0.9268 | the best admitted under D6 |
| bp_be_top | 12 | bp_be_top.M2.v1.s0 | 0.9500 | the best admitted under D6 |
| ariane136 | 1 | ariane136.M4.v2.s0 | 1.0295 | none admitted: the best before the gates |
| swerv_wrapper | 1 | swerv_wrapper.M4.v0.s0 | 1.0773 | none admitted: the best before the gates |

- **DREAMPlace:** the three-way comparison's replicates of its pick (rows `EXT_DP_TB`), re-scored here under Section 4;
  its recorded TW results stand.
- **Reported only:** the tool's replicates (rows `TB_REF`, J before the gates) and HeurBridge's local-search candidates
  (rows `TB_CAND`, gated as in Section 4).

## 4 Replicates and endpoint

- **Replicates (programs, new):** each pick at the Track-B test's six shifts (+2, 0), (-2, 0), (0, -1), (0, +2),
  (+1, +1), (-1, -1) sites and rows, with its fallback rule (common legal shifts with the tool's layout; fallbacks
  (+3, 0), (-3, 0), (0, -2); a slot with no legal shift left is dropped and named); f2, at most 8 OpenROAD runs at a time
  on 224, 7,200 s per step; one job per design (`tp_*`, rows `TB_PG_CAND` in `evals_tb_pg.jsonl`).
- **Endpoint, programs and DREAMPlace alike (decision D11 (b)):** f2 J with every gate enforced; the setup and hold gates
  compare with the tool's replicate at the same shift, with the 0.02-ns guard and without the sign rule; where the
  tool's run at that shift failed (bp_be_top's (0, +2) and (-1, -1)) or no tool replicate exists at a fallback shift,
  with the median of the tool's completed replicates in the Track-B test (heurbridge/eval/cost.py:129-141); a failed
  gate or flow is +inf.

## 5 Test and decision

- **Per design:** exact one-sided permutation test of the rank sum, programs lower than DREAMPlace (scripts/trackb_confirm.py
  `rank_sum_p`; p = 1/924 when the bands separate with six replicates per arm).
- **Pass:** p <= alpha_j. Claim per passing design: "HeurBridge's heuristic programs alone, without the flow-scored local
  search, beat DREAMPlace's macro placement through the OpenROAD flow at signoff, beyond the flow's shift sensitivity".
  Overall: k of n designs pass.
- **Fail:** a negative result for that design; that DREAMPlace is better is not tested.
- **Reported, not tested:** every replicate's J, J before the gates, gates and timing reference; the arms' medians
  before the gates; HeurBridge's local-search candidate against the programs under the same gates (what the
  flow-scored search adds).
- **Once:** `programs_confirm.py analyze --design <d>` records the design's result and refuses a second one.

## 6 Limits stated in advance

- **Selection budget, still unequal but without flow-scored search:** the programs' pick comes from 80 program layouts at
  f1 and the campaign's f2 stage (its 10 best f1 layouts and 10 more across its ranking, local-search layouts included,
  so only 1 program layout reached f2 on ariane136 and swerv_wrapper); DREAMPlace's from 12 layouts at f1 and 4 at f2.
- On ariane136 and swerv_wrapper the program pick was not admitted under D6 at f2 and its J before the gates (1.0295,
  1.0773) is above the tool's same-path replays there (reports/trackB_confirmatory.md); a pass is unlikely on those.
- DREAMPlace's replicates were measured before this registration; nothing of the program picks' replicates is known.
- The same flow, floorplan, legalizer (P_M), import path and shifts for every arm; f3 is not available.
