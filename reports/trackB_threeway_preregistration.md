# Track B three-way comparison: pre-registration (confirmatory: HeurBridge's macro layout against DREAMPlace's through the OpenROAD flow, next to the tool's)

| Field | Value |
|---|---|
| Report | trackB_threeway_preregistration |
| Date | 2026-10-03 |
| Status | **registered 3 Oct**, before any DREAMPlace layout has run through the flow, under the owner's decision of 3 Oct (D9: when Track B's seeding has finished, compare DREAMPlace's and HeurBridge's macro placements through the OpenROAD flow, next to the tool's own; reports/next_phase_decisions.md:125-127). The flow runs start when swerv_wrapper's seeding campaign has finished |
| Track | B (ORFS 2024-12-13 8ae3ae36, OpenROAD 676f8451, Nangate45; ENV_REPORT.md:138-139) |
| Cost | cost_v3's J normalized to the unmodified flow (configs/cost.yaml:3, :12-25), with the Track-B test's timing-gate rule (decision D6, reports/next_phase_decisions.md:258-262) |
| alpha-ledger | campaign `TW` (alpha = 0.05; HEURBRIDGE_TASKS.md:541): TW#1 bp_fe_top 0.025, TW#2 bp_be_top 0.0125, TW#3 ariane136 0.00625 reserved now; TW#4 swerv_wrapper 0.003125 reserved after its Track-B candidate is fixed (TB#4), before its DREAMPlace flow runs. ariane133 only under decision D2 |
| Code | scripts/dreamplace_trackb.py (`place`), scripts/run_seed_orfs.py (`--phase extlayouts --ext-f2-top 4 --ext-tb`, `ext_pick`), scripts/threeway_confirm.py, as committed together with this document |

## 1 Question

Through the same OpenROAD flow, at signoff (f2), does HeurBridge's macro layout (the Track-B test's candidate) beat
DREAMPlace's (its mixed-size placement with every macro movable, the best of twelve runs picked the way HeurBridge's
candidate was picked)? The tool's own macro placement (ORFS's rtl_macro_placer, Hier-RTLMP) is the third arm,
reported.

## 2 What exists (descriptive)

- HeurBridge's and the tool's replicates at the six shifts were measured by the Track-B test before this registration:
  TB#1 and TB#2 passed, TB#3 failed on the hold gate (reports/trackB_confirmatory.md:13-15). No DREAMPlace layout has
  been through the flow.
- DREAMPlace's layouts (job `dptb_place3` on 227): per design twelve runs, target densities 0.6, 0.8 and 1.0 times
  seeds 0-3, DREAMPlace 4.3.1 at 6627f33 (ENV_REPORT.md:68, :141) on a GPU with the parameters of
  heurbridge/eval/dreamplace.py:174-185 (1,000 iterations), every macro movable and given to DREAMPlace as P_M's grid
  footprint (its size rounded up to P_M's cells plus the halo cells; scripts/dreamplace_trackb.py:57-68), DREAMPlace's
  macro legalization and greedy cell legalization, its Abacus pass off (it aborts on these designs;
  scripts/dreamplace_trackb.py:81); the macros read back and legalized by P_M with the campaign's spacing. Only the
  macro positions are used: the flow places the standard cells for every arm. Before the footprints, P_M's grid moved
  DREAMPlace's packed macros by 2-6 % of the die on ariane136 (job `dptb_place2`, not used); with them the area-weighted
  mean displacement is at most 0.002 of the die on bp_fe_top, bp_be_top and ariane136 and 0.02 on swerv_wrapper, where
  HeurBridge's own program layouts move by a median of 0.02 (local run files `runs/remote/dptb_place3/runs/dptb3/<design>/rows.jsonl`,
  `runs/remote/seedB_orfs7_swerv_wrapper/runs/seed_orfs/swerv_wrapper/evals.jsonl`).

- The flow path for external layouts was checked without DREAMPlace's layouts (job `extsmoke_bp_fe_top`): two
  campaign layouts of bp_fe_top given in reversed macro order reproduced their campaign f1 J exactly (0.9000776798887087,
  0.9160923196962636), and the better one its f2 J (0.8808680861952332), picked as admitted under D6 (local run files
  `runs/remote/extsmoke_bp_fe_top/runs/seed_orfs/bp_fe_top/evals_ext_smoke.jsonl:1-3`).

## 3 Arms

- **HeurBridge:** the Track-B test's candidate replicates (rows `TB_CAND`, jobs `tb_<design>`).
- **DREAMPlace:** the pick among its completed runs (a failed run is named and leaves the pool), chosen like
  HeurBridge's candidate: every layout to f1; the four best by f1 J before the gates to f2 (unshifted); the pick is the
  best f2 layout admitted under Section 4's rule, else the best f2 J before the gates, else (every f2 run failed) the
  best by f1, each named (scripts/run_seed_orfs.py:154-163, `ext_pick`).
- **Tool:** the Track-B test's reference replicates (rows `TB_REF`), reported only.

## 4 Replicates and endpoint

- **Replicates:** DREAMPlace's pick at the Track-B test's six shifts (+2, 0), (-2, 0), (0, -1), (0, +2), (+1, +1),
  (-1, -1) sites and rows, with its fallback rule (scripts/run_seed_orfs.py:138-139, `tb_pairs`: a shift illegal for
  the pick or the tool's layout is replaced by the next of (+3, 0), (-3, 0), (0, -2); a slot with no legal shift left
  is dropped and named). At f2 (6_report), at most 8 OpenROAD runs at a time on 224, 7,200 s per step. Per design one
  job `tw_<design>`: twelve f1 runs, four f2 runs, six f2 replicates.
- **Endpoint, HeurBridge and DREAMPlace alike:** f2 J with every gate enforced; the setup and hold gates compare with
  the campaign's same-path replay band's median at f2 with the 0.02-ns guard and without the sign rule
  (heurbridge/eval/cost.py:129-138, `timing_sign_rule=False`); a failed gate or flow is +inf.
- **Tool (reported):** f2 J before the gates.

## 5 Test and decision

- **Per design:** exact one-sided permutation test of the rank sum, HeurBridge lower than DREAMPlace, over all splits
  of the pooled replicates (scripts/trackb_confirm.py `rank_sum_p`; C(12, 6) = 924 splits with six per arm, p = 1/924
  when the bands separate).
- **Pass:** p <= alpha_j of the design's entry. Claim per passing design: "through the OpenROAD flow at signoff,
  HeurBridge's macro layout beats DREAMPlace's, beyond the flow's shift sensitivity". Overall: k of n designs pass.
- **Fail:** reported as a negative result for that design. That DREAMPlace is better is not tested; it is reported.
- **Reported, not tested:** the same statistic for DREAMPlace against the tool (DREAMPlace gated, the tool before the
  gates); every replicate's J, J before the gates, gates and wall-clock; the three arms' median J before the gates;
  DREAMPlace's pick (run, density, seed, rule) and its flow runs, against HeurBridge's campaign and the tool's one run.
- **Once:** `threeway_confirm.py analyze --design <d>` records the design's result and refuses a second one.

## 6 Fairness and limits stated in advance

- **The same for every arm:** flow, pre-macro floorplan, macro legalizer (P_M with the campaign's spacing), import path
  (a place_macro script; the tool's macro placer does not run), shifts, gate reference and endpoint.
- **Search with the flow in the loop (not the same):** HeurBridge's candidates come from 80 heuristic-program layouts
  and 45-48 local-search moves scored by the flow itself at f1, the improving moves verified at f2, and were picked at
  f2 (heurbridge/pipeline/seed_archive.py:269-296; local run files
  `runs/remote/seedB_orfs7_<design>/runs/seed_orfs/<design>/evals.jsonl`): 29-86 flow-run hours per design
  (reports/trackB_confirmatory.md:125, :150, :175), and all three registered candidates are local-search layouts.
  DREAMPlace optimizes wirelength and density without timing and never sees the flow's score; the flow enters only its
  pick (twelve f1 and four f2 runs). So a pass says that HeurBridge's search with the flow as its score reaches better
  layouts than DREAMPlace with light selection; it does not compare the two at equal flow budget.
- HeurBridge's and the tool's replicates were measured before this registration; nothing of DREAMPlace's flow results
  is known. All four designs enter in the Track-B order.
- DREAMPlace keeps every macro's orientation as in the floorplan; HeurBridge's programs and the tool choose
  orientations.
- A dropped shift lowers the attainable p (the minimum is 1/C(6 + n, 6) with n DREAMPlace replicates): n = 5 gives
  1/462 = 0.0022, still below every alpha_j; n = 4 gives 1/210 = 0.0048, above alpha_4; n = 3 gives 1/84 = 0.0119,
  above alpha_3.
- The hold gate with this reference rejected the tool's own shifted layouts on 5 of 6 shifts of ariane136
  (reports/trackB_confirmatory.md:31-37); it applies to HeurBridge and DREAMPlace alike.
- f3 (DRC and LVS by KLayout, Magic, Netgen) is not available (reports/signoff_anchor_readiness.md): passing f2's
  gates is not production signoff.
