# Track B three-way comparison on ariane133 (TW#5): pre-registration (confirmatory: HeurBridge's macro layout against DREAMPlace's through the OpenROAD flow, next to the tool's)

| Field | Value |
|---|---|
| Report | trackB_threeway_ariane133_preregistration |
| Date | 2026-10-07 |
| Status | **registered 7 Oct**, before any DREAMPlace layout of ariane133 exists, under the owner's decision D15 of 7 Oct (reports/next_phase_decisions.md, D15); as a test registered after 4 Oct, with the gates of D11 (b) and the picks of D13 (a) |
| Track | B (ORFS 2024-12-13 8ae3ae36, OpenROAD 676f8451, Nangate45; ENV_REPORT.md:138-139); ariane133 under D2 (b): `RTLMP_MAX_LEVEL=1` and `GLOBAL_PLACEMENT_ARGS=-keep_resize_below_overflow 0.01` for every run, the baseline included |
| Cost | cost_v3's J normalized to the unmodified flow with D2 (b)'s variables (configs/cost.yaml:3, :12-25) |
| alpha-ledger | campaign `TW` (alpha = 0.05; HEURBRIDGE_TASKS.md:541): TW#5 ariane133, alpha_5 = 0.0015625, reserved now |
| Code | scripts/dreamplace_trackb.py (`export`, `place --inflate`), scripts/run_seed_orfs.py (`--phase extlayouts --ext-f2-top 4 --ext-tb --ext-pick jsafe`, `jsafe_pick`), scripts/threeway_confirm.py (`D11B`), scripts/equal_budget_confirm.py (`score_d11b`), heurbridge/eval/cost.py (`same_shift_reference`), as committed together with this document |

## 1 Question

As in the three-way comparison of the other four designs (reports/trackB_threeway_preregistration.md, Section 1):
through the same OpenROAD flow, at signoff (f2), does HeurBridge's macro layout (TB#5's candidate) beat DREAMPlace's on
ariane133? The tool's own macro placement (ORFS's rtl_macro_placer, Hier-RTLMP) is the third arm, reported.

## 2 What exists (descriptive)

- HeurBridge's candidate **ariane133.ls5.n5**, fixed by the Track-B rule and reserved as TB#5 before its test
  (reports/trackB_preregistration.md, addenda of 7 Oct). Under D13 (a) with one position (the unshifted f2 run, its
  setup and hold against the tool's unshifted replay with the 0.02-ns guard), its J_safe pick among the campaign's 20 f2
  layouts is the same layout: J_safe 0.9038, then ls7.n1 0.9090 and ls6.n5 0.9098 (J 0.8898, its hold fails), computed
  7 Oct from the local run file `runs/remote/seedB_orfs9_ariane133/runs/seed_orfs/ariane133/evals_f2.jsonl`.
- The replicates of HeurBridge and the tool are TB#5's re-run (job `tb10_ariane133`), not yet measured: this
  registration precedes them as well. TB#5's first attempt was voided by another user's load (D14).
- No DREAMPlace layout of ariane133 exists. The tool's four same-path replays at f2 vary J from 0.739 to 1.877 (the
  same file's lines 1-4), almost entirely through setup TNS.

## 3 Arms

- **HeurBridge:** TB#5's candidate replicates (rows `TB_CAND`, job `tb10_ariane133`).
- **DREAMPlace:** twelve runs as for TW#1-TW#4: target densities 0.6, 0.8 and 1.0 times seeds 0-3, DREAMPlace 4.3.1
  at 6627f33 on one of 227's RTX 3090 GPUs (TW#1-TW#4's model; GPU 0 is in use) with the parameters of
  heurbridge/eval/dreamplace.py (1,000 iterations), every macro
  movable and given as P_M's grid footprint (`--inflate`), its macro legalization and greedy cell legalization, the
  Abacus pass off; the macros read back and legalized by P_M with the campaign's spacing. The design is exported from
  the campaign's pre-macro floorplan (`fp.hb.def` of `seedB_orfs9_ariane133`). A run that leaves a macro unmoved or
  fails P_M is named and leaves the pool. Every completed layout to f1; the four best by f1 J before the gates to f2
  (unshifted); **the pick: the lowest one-position J_safe** against the tool's unshifted replay (D13 (a), D11 (b)), ties
  by J; if every f2 run failed, the best by f1 (scripts/run_seed_orfs.py `jsafe_pick`, `--ext-pick jsafe`).
- **Tool:** TB#5's reference replicates (rows `TB_REF`, job `tb10_ariane133`), reported only.

## 4 Replicates and endpoint

- **Replicates:** DREAMPlace's pick at the Track-B test's six shifts with their fallback rule (`tb_pairs`), at f2,
  with D2 (b)'s variables; at most 8 OpenROAD runs at a time on 224, 7,200 s per evaluation. One job `tw_ariane133`:
  up to twelve f1 runs, four f2 runs, six f2 replicates.
- **Endpoint, HeurBridge and DREAMPlace alike (D11 (b)):** f2 J with every gate enforced; setup and hold against the
  tool's replicate at the same shift with the 0.02-ns guard and no sign rule; where that run failed, the median of the
  tool's completed replicates; if none completed, the campaign's replay band (heurbridge/eval/cost.py
  `same_shift_reference`); a failed gate or flow is +inf.
- **Tool (reported):** f2 J before the gates.

## 5 Test and decision

- **Test:** exact one-sided permutation test of the rank sum, HeurBridge lower than DREAMPlace (scripts/trackb_confirm.py
  `rank_sum_p`). With six replicates per arm the smallest attainable p is 1/924 = 0.0011, below alpha_5; the next is
  2/924 = 0.0022, above it. TW#5 therefore passes only if all six HeurBridge replicates lie below all six DREAMPlace
  replicates; a dropped shift makes a pass unattainable.
- **Pass:** claim "through the OpenROAD flow at signoff, HeurBridge's macro layout beats DREAMPlace's on ariane133,
  beyond the flow's shift sensitivity". The three-way comparison overall: k of 5 designs.
- **Fail:** a negative result for ariane133; that DREAMPlace is better is not tested; it is reported.
- **Reported, not tested:** DREAMPlace against the tool (DREAMPlace gated, the tool before the gates); every replicate's
  J, J before the gates, gates and wall-clock; the arms' median J before the gates; each arm's J, S and J_safe over the
  six positions (D13 (a)); DREAMPlace's pick (run, density, seed, rule) and its flow runs.
- **Once:** `python scripts/threeway_confirm.py analyze --design ariane133 --tb-prefix tb10_ --campaign-prefix
  seedB_orfs9_` records the result and refuses a second one.

## 6 Fairness and limits stated in advance

- As for TW#1-TW#4 (reports/trackB_threeway_preregistration.md, Section 6): the same flow, floorplan, legalizer, import
  path, shifts and endpoint for both arms; HeurBridge searched with the flow as its score (80 program layouts at f1, a
  local search, 20 f2 layouts), DREAMPlace never sees the flow except in its pick (twelve f1 and four f2 runs), so a pass
  does not compare the two at equal flow budget; DREAMPlace keeps the floorplan's macro orientations; f3 is not
  available.
- **Differences from TW#1-TW#4:** the gate reference (the tool's replicate at the same shift instead of the replay band)
  and DREAMPlace's pick (one-position J_safe instead of admission under D6). TW#1-TW#4 keep their registered rules.
- Under D2 (b) ariane133's f2 J is dominated by timing noise (the tool's replays: J 0.739-1.877), so a complete
  separation of six by six is unlikely unless one arm's timing is consistently better.
- 224 is shared with another user's jobs (D14): the flow runs are launched only after checking that the free cores
  suffice; a run that still times out is +inf for either arm, as registered.
