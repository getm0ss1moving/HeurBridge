# Audit of the project's tests

| Field | Value |
|---|---|
| Report | test_audit |
| Date | 2026-10-03 23:51 |
| Why | the owner's request of 3 Oct: make a correct ISPD2005 test and check whether the other tests have problems like the ISPD2005 tool-input defect |
| Label | development / descriptive: an audit; no test is re-run or re-decided here |
| Code | scripts/audit_tests.py (`--report` writes this file; Sections 1-5 are recomputed from local run files) |

## Summary

**Problems found, and what each means for the results:**

1. **The tool's input froze ISPD2005's macros** (found 3 Oct): RL#1-RL#3 are not evidence for their claims (notes in
   Section 1; reports/defect_ispd_tool_runs.md). The corrected re-test RL#4 passed (Section 1;
   reports/portfolio_retest_confirmatory.md). The tool's runs now move the macros on every ISPD2005 design (Section 3),
   and a run that leaves a macro where it started is a named failure (heurbridge/eval/dreamplace.py, commit c9f0008).
2. **The Track-B test's hold gate:** TB#3 failed on a hold gate whose reference (the median of four unshifted replays,
   +0.015 ns) lies above the tool's own shifted replicates, which fail the same check on 5 of 6 shifts; TB#1 passed
   with one replicate exactly at its hold threshold (reports/trackB_confirmatory.md, Summary, notes 1 and 3). Stated in
   that report; no result is changed.
3. **bp_fe_top's same-path replay band was poorer for the tool than fresh runs:** the campaign's four replays of the
   tool's layout at f2 have J 1.03-1.40 and setup TNS -0.50 to -2.14 ns; the Track-B test's six reference replicates of
   the same layout have J 0.96-1.08 and TNS -0.15 to -0.68 ns (local run files
   `runs/remote/seedB_orfs7_bp_fe_top/runs/seed_orfs/bp_fe_top/evals_f2.jsonl:1-4`,
   `runs/remote/tb_bp_fe_top/runs/seed_orfs/bp_fe_top/evals_tb.jsonl`). The default flow path did not change between
   them (git log of heurbridge/eval/orfs.py, heurbridge/pipeline/evaluators.py and scripts/server/trackb.sh since 28 Sep:
   optional phases only; the warm start is off by default, heurbridge/pipeline/evaluators.py:145), so this is
   run-to-run timing variance. The campaign report's comparison with that band (reports/T2_trackB_orfs_bp_fe_top.md:47)
   flattered the candidate; the test's fresh references are the fair comparison, and TB#1 passed on them. On bp_be_top
   and ariane136 the replays and the references agree.
4. **The decision record said HeurBridge does not optimize the flow's score;** its Track-B local search scores every
   move with the flow at f1 (heurbridge/pipeline/seed_archive.py:269-296). Corrected in reports/next_phase_decisions.md
   (D9) and stated in the three-way comparison's pre-registration.
5. **E0's guard and its final cost share one f1 run (seed 0):** measured on rebuilt co-trained layouts, the optimism is
   negligible (Section 5) against the 0.026 gap between the co-trained and the memetic partner's mean J
   (reports/E0_partner_ablation.md:29, :31). G0' stands.
6. **The audit's own first run** excluded 16 of 46 units with a 1e-9 reproduction tolerance (float rounding, all within
   6e-8); the tolerance is 1e-6 now and the units were re-scored (Section 5).
7. **DREAMPlace on the Track-B designs (new code, found before any use):** its Abacus pass aborted 15 of 36 runs, and
   P_M's grid moved its packed macros by 2-6 % of the die on ariane136; both fixed (CHANGELOG.md, 3 Oct 23:15).

**Checks that found no problem:** f1 keeps the macros fixed (Section 2); the tool's runs move the macros on IBM and,
after the fix, on ISPD2005 (Section 3); E0's arms are distinct (Section 4: the co-trained partner equals another
partner only where both keep the raw layout); Track-B macro imports are honoured: 52,974 macro placements read back
from the flow's outputs on 224, x exact, y within 0.105 um, the tool's macro placer never ran (checked 3 Oct 11:00-12:00,
recorded in HANDOFF.md:99-101; the commands were not kept as a script and the flow's outputs are on 224 only).

**Not re-checked here:** the bridge-promotion tests (campaigns algR_dev, algR_trackA, E0_dev) beyond their ledger
entries (Section 1).

## 1 Every registered test (alpha-ledger)

| campaign | entry | alpha_j | what | p | outcome | notes |
|---|---|---|---|---|---|---|
| E0_dev | E0_dev#1 | 0.025 | best.pt | 0.99 | failed | - |
| E0_dev | E0_dev#2 | 0.0125 | best.pt@bc3d0d801e41c0f9 | 0.00524 | passed | - |
| E0_dev | E0_dev#3 | 0.00625 | best.pt@bc3d0d801e41c0f9 | 0.00524 | passed | - |
| E0_dev | E0_dev#4 | 0.003125 | best.pt@bc3d0d801e41c0f9 | 0.00608 | failed | - |
| algR_dev | algR_dev#1 | 0.025 | algR_dev#r0 | 0.000481 | passed | - |
| algR_dev | algR_dev#2 | 0.0125 | algR_dev#r1 | 0.389 | failed | - |
| algR_trackA | algR_trackA#1 | 0.025 | algR_trackA#r0 | 2.56e-09 | passed | - |
| algR_trackA | algR_trackA#2 | 0.0125 | algR_trackA#r1 | 0.000123 | passed | - |
| algR_trackA | algR_trackA#3 | 0.00625 | algR_trackA#r2 | 1 | failed | - |
| E0 | E0#1 | 0.025 | E0 primary @f95bdde848531634 | 2.41e-61 | passed | - |
| E0 | E0#2 | 0.0125 | E0 secondary_equal_guard @f95bdde848531634 | 3.25e-57 | passed | - |
| E0 | E0#3 | 0.00625 | E0 secondary_ibm_heldout @f95bdde848531634 | 4.32e-17 | passed | - |
| RL | RL#1 | 0.025 | relink two tool runs vs the tool's best of 4 @ISPD2005 | 0.882 | failed | Defect found after the analysis: the tool's input marked ISPD2005's macros as fixed termin |
| RL | RL#2 | 0.0125 | one tool run at target density 0.6 vs the tool's best of 4 at 0.9 @ISP | 0.00586 | passed | Defect found after the analysis: the tool's input marked ISPD2005's macros as fixed termin |
| RL | RL#3 | 0.00625 | two densities {0.9, 0.6} vs two seeds at 0.9, same seed s @ISPD2005 | 0.00586 | passed | Defect found after the analysis: the tool's input marked ISPD2005's macros as fixed termin |
| RL | RL#4 | 0.003125 | corrected re-test: two densities {0.9, 0.6} vs two seeds at 0.9 @ISPD2 | 0.000142 | passed | - |
| TB | TB#1 | 0.025 | bp_fe_top: bp_fe_top.ls0.n4.f2 vs the tool's macro placement at f2 | 0.00216 | passed | - |
| TB | TB#2 | 0.0125 | bp_be_top: bp_be_top.ls7.n1.f2 vs the tool's macro placement at f2 | 0.00108 | passed | - |
| TB | TB#3 | 0.00625 | ariane136: ariane136.ls7.n3.f2 vs the tool's macro placement at f2 | 0.53 | failed | - |
| TW | TW#1 | 0.025 | bp_fe_top: HeurBridge's macro layout vs DREAMPlace's at f2 | - | - | - |
| TW | TW#2 | 0.0125 | bp_be_top: HeurBridge's macro layout vs DREAMPlace's at f2 | - | - | - |
| TW | TW#3 | 0.00625 | ariane136: HeurBridge's macro layout vs DREAMPlace's at f2 | - | - | - |

Source: stats/alpha_ledger.jsonl (every line).

## 2 Track A: f1 keeps the macros fixed

Of 3145 rows of the Track-A seeding campaigns (25 files), 2890 carry an f1 record with the measured maximum macro shift; the largest is 0 (source units); 0 rows failed with `macros_moved`. The other 255 rows failed before f1 (sandbox, memory, P_M), each by name.

Sources: `runs/remote/seedA_*_combined/*/evals.jsonl` (field `record.macro_max_shift`); the guard: heurbridge/eval/dreamplace.py:258-264 (in place since v0.12.0, before these campaigns).

## 3 The tool's runs move the macros (J spread over seeds)

A run that leaves the macros where they start gives the same J for every seed (the ISPD2005 defect: 0.4499-0.4503 on seven designs for every seed and density, reports/density_confirmatory.md:19-24).

| family | design | runs | J min | J max | spread | source |
|---|---|---|---|---|---|---|
| IBM | ibm01 | 8 | 0.4492 | 0.4572 | 0.0080 | runs/remote/relinkall_a/runs/tool_runs/ibm01/rows.jsonl |
| IBM | ibm02 | 8 | 0.1553 | 0.4500 | 0.2947 | runs/remote/relinkall_a/runs/tool_runs/ibm02/rows.jsonl |
| IBM | ibm03 | 8 | 0.4493 | 0.4601 | 0.0108 | runs/remote/relinkall_a/runs/tool_runs/ibm03/rows.jsonl |
| IBM | ibm07 | 8 | 0.4469 | 0.4841 | 0.0372 | runs/remote/relinkall_a/runs/tool_runs/ibm07/rows.jsonl |
| IBM | ibm09 | 8 | 0.4323 | 0.5309 | 0.0986 | runs/remote/relinkall_b/runs/tool_runs/ibm09/rows.jsonl |
| IBM | ibm10 | 8 | 0.4498 | 0.5353 | 0.0855 | runs/remote/relinkall_b/runs/tool_runs/ibm10/rows.jsonl |
| IBM | ibm11 | 8 | 0.4428 | 0.4540 | 0.0112 | runs/remote/relinkall_b/runs/tool_runs/ibm11/rows.jsonl |
| IBM | ibm12 | 8 | 0.4459 | 0.4524 | 0.0064 | runs/remote/relinkall_b/runs/tool_runs/ibm12/rows.jsonl |
| IBM | ibm13 | 8 | 0.4449 | 0.4622 | 0.0173 | runs/remote/relinkall_c/runs/tool_runs/ibm13/rows.jsonl |
| IBM | ibm14 | 8 | 0.4483 | 0.4500 | 0.0017 | runs/remote/relinkall_c/runs/tool_runs/ibm14/rows.jsonl |
| IBM | ibm18 | 8 | 0.4461 | 0.4602 | 0.0141 | runs/remote/relinkall_c/runs/tool_runs/ibm18/rows.jsonl |
| IBM | ibm15 | 8 | 0.4483 | 0.4505 | 0.0022 | runs/remote/relinkall_d/runs/tool_runs/ibm15/rows.jsonl |
| IBM | ibm16 | 8 | 0.4476 | 0.4497 | 0.0020 | runs/remote/relinkall_d/runs/tool_runs/ibm16/rows.jsonl |
| IBM | ibm17 | 8 | 0.4506 | 0.4551 | 0.0045 | runs/remote/relinkall_d/runs/tool_runs/ibm17/rows.jsonl |
| ISPD2005 (RL#4, 0.9) | adaptec1 | 8 | 0.4121 | 0.4263 | 0.0142 | runs/remote/rc4_a1/runs/tool_runs_td0.9/adaptec1/rows.jsonl |
| ISPD2005 (RL#4, 0.9) | adaptec2 | 8 | 0.4142 | 0.4350 | 0.0208 | runs/remote/rc4_a2/runs/tool_runs_td0.9/adaptec2/rows.jsonl |
| ISPD2005 (RL#4, 0.9) | adaptec3 | 8 | 0.3818 | 0.3898 | 0.0081 | runs/remote/rc4_a3/runs/tool_runs_td0.9/adaptec3/rows.jsonl |
| ISPD2005 (RL#4, 0.9) | adaptec4 | 8 | 0.3869 | 0.3901 | 0.0032 | runs/remote/rc4_a4/runs/tool_runs_td0.9/adaptec4/rows.jsonl |
| ISPD2005 (RL#4, 0.9) | bigblue1 | 8 | 0.4405 | 0.4467 | 0.0062 | runs/remote/rc4_b1/runs/tool_runs_td0.9/bigblue1/rows.jsonl |
| ISPD2005 (RL#4, 0.9) | bigblue2 | 8 | 0.4145 | 0.4239 | 0.0094 | runs/remote/rc4_bb2/runs/tool_runs_td0.9/bigblue2/rows.jsonl |
| ISPD2005 (RL#4, 0.9) | bigblue4 | 8 | 0.4888 | 0.6875 | 0.1987 | runs/remote/rc4_bb4/runs/tool_runs_td0.9/bigblue4/rows.jsonl |

## 4 E0's arms are distinct

| protocol | units | co-trained = memetic | co-trained = repertoire | co-trained = raw layout |
|---|---|---|---|---|
| E0_1_spec | 405 | 8 | 0 | 40 |
| E0_2_eq | 405 | 22 | 24 | 40 |
| E0_3_ibm | 145 | 21 | 3 | 79 |

Source: `runs/e0_full/*/e0_rows.jsonl` (the combined rows of the full E0).

## 5 E0's same-seed selection (optimism of the co-trained J)

Units sampled: 46 (6 per design where available); scored: 46; still excluded: 0.

Optimism = median J over fresh f1 seeds 1-3 minus the recorded J (positive: the recorded J flattered the layout): median +0.00000, mean +0.00017, quartiles -0.00020 / +0.00020, range -0.00268 to +0.00562; positive in 24 of 46.

| design | units scored | median optimism |
|---|---|---|
| adaptec1 | 6 | +0.00003 |
| adaptec2 | 6 | +0.00007 |
| adaptec3 | 6 | -0.00011 |
| adaptec4 | 6 | -0.00010 |
| bigblue1 | 6 | -0.00001 |
| bigblue4 | 4 | +0.00011 |
| ibm08 | 6 | +0.00186 |
| ibm12 | 6 | -0.00002 |

Sources: `runs/remote/e0bias_a/runs/e0_bias/adaptec1/rows.jsonl`, `runs/remote/e0bias_a/runs/e0_bias/adaptec2/rows.jsonl`, `runs/remote/e0bias_a/runs/e0_bias/adaptec3/rows.jsonl`, `runs/remote/e0bias_a/runs/e0_bias/adaptec4/rows.jsonl`, `runs/remote/e0bias_a/runs/e0_bias/bigblue1/rows.jsonl`, `runs/remote/e0bias_a/runs/e0_bias/bigblue4/rows.jsonl`, `runs/remote/e0bias_a/runs/e0_bias/ibm08/rows.jsonl`, `runs/remote/e0bias_a/runs/e0_bias/ibm12/rows.jsonl`, `runs/remote/e0bias_b0/runs/e0_bias2/adaptec1/rows.jsonl`, `runs/remote/e0bias_b0/runs/e0_bias2/adaptec2/rows.jsonl`, `runs/remote/e0bias_b0/runs/e0_bias2/adaptec4/rows.jsonl`, `runs/remote/e0bias_b1/runs/e0_bias2/adaptec3/rows.jsonl`, `runs/remote/e0bias_b2/runs/e0_bias2/bigblue4/rows.jsonl`, `runs/remote/e0bias_b3/runs/e0_bias2/bigblue1/rows.jsonl`, `runs/remote/e0bias_b3/runs/e0_bias2/ibm12/rows.jsonl`.

