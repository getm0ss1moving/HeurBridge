# Beating the tool on Track A: feasibility, noise and equal-compute comparisons

| Field | Value |
|---|---|
| Report | beat_tool_track_a |
| Date | 2026-10-03 08:21 |
| Track | A (IBM; f1 = DREAMPlace GP + LG with macros fixed; J against the seeding M1 baseline, 0.45 by construction) |
| Status of the claim | **exploratory demo (no claim)**; any claim needs the pre-registered test drafted from it |
| Owner's aim (3 Oct) | macro layouts with mean J below 0.45 that beat the tool on output and on cost |
| Confirmatory tests drafted from it | RL#1 relinking vs best of 4 (reports/relink_preregistration.md); RL#2 the tool at target density 0.6 vs best of 4 at 0.9 (reports/density_preregistration.md); both on ISPD2005 |

## 1 Feasibility demo (f1 seed 0, the seed every arm also selected with)

| design | tool | tool, best of 4 seeds | frozen bridge on the tool's layout (alpha) | local search (f1 runs, minutes) | tool run s | f1 run s (median) |
|---|---|---|---|---|---|---|
| ibm01 | 0.4500 | 0.4500 | 0.4500 (0.0) | 0.4489 (77, 9.6) | 35.3 | 13.6 |
| ibm03 | 0.4500 | 0.4493 | 0.4500 (0.0) | 0.4417 (87, 10.1) | 40.1 | 12.4 |
| ibm04 | 0.4497 | 0.4326 | 0.4329 (0.25) | 0.4235 (84, 8.0) | 34.3 | 9.7 |
| ibm06 | 0.4499 | 0.4499 | 0.4499 (0.0) | 0.4428 (83, 8.0) | 46.2 | 10.2 |
| ibm07 | 0.4490 | 0.4471 | 0.4490 (0.0) | 0.4375 (83, 11.2) | 22.6 | 13.7 |
| ibm08 | 0.4507 | 0.4347 | 0.4507 (0.0) | 0.4480 (86, 10.5) | 28.9 | 11.9 |
| ibm09 | 0.4544 | 0.4323 | 0.4132 (0.25) | 0.4309 (81, 11.1) | 23.0 | 13.5 |
| ibm10 | 0.4498 | 0.4498 | 0.4498 (0.0) | 0.4492 (84, 15.8) | 23.2 | 14.7 |
| ibm12 | 0.4507 | 0.4501 | 0.4507 (0.0) | 0.4494 (82, 13.2) | 23.5 | 13.8 |
| ibm15 | 0.4500 | 0.4485 | 0.4500 (0.0) | 0.4484 (88, 26.3) | 32.3 | 31.3 |
| ibm16 | 0.4501 | 0.4473 | 0.4501 (0.0) | 0.4474 (79, 28.3) | 25.6 | 36.3 |
| ibm17 | 0.4500 | 0.4500 | 0.4500 (0.0) | 0.4496 (78, 28.4) | 25.0 | 33.3 |

The tool's routability mode failed on every design (dreamplace_rc_1): it builds a congestion map that needs routing capacities the IBM Bookshelf files lack (third_party/DREAMPlace/dreamplace/PlaceObj.py:250-257). Sources: runs/remote/beat_tool_231/runs/beat_tool/g231/summary.json, runs/remote/beat_tool_g0/runs/beat_tool/g0/summary.json, runs/remote/beat_tool_g1/runs/beat_tool/g1/summary.json, runs/remote/beat_tool_g2/runs/beat_tool/g2/summary.json, runs/remote/beat_tool_g3/runs/beat_tool/g3/summary.json.

## 2 Noise bands (f1 seeds 0-2; the tool's band = its baseline's three records)

| design | tool band (median) | local search band (median) | whole band below the tool's | bridge band (median) | whole band below |
|---|---|---|---|---|---|
| ibm01 | 0.4495-0.4507 (0.4500) | 0.4489-0.4508 (0.4504) | no | - (alpha 0) | - |
| ibm03 | 0.4485-0.4515 (0.4500) | 0.4417-0.4497 (0.4457) | no | - (alpha 0) | - |
| ibm04 | 0.4486-0.4508 (0.4497) | 0.4235-0.4361 (0.4314) | yes | 0.4303-0.4329 (0.4319) | yes |
| ibm06 | 0.4497-0.4511 (0.4499) | 0.4428-0.4475 (0.4458) | yes | - (alpha 0) | - |
| ibm07 | 0.4490-0.4511 (0.4497) | 0.4375-0.4398 (0.4393) | yes | - (alpha 0) | - |
| ibm08 | 0.4491-0.4518 (0.4498) | 0.4480-0.4507 (0.4482) | no | - (alpha 0) | - |
| ibm09 | 0.4408-0.4544 (0.4500) | 0.4309-0.4508 (0.4506) | no | 0.4132-0.4158 (0.4143) | yes |
| ibm10 | 0.4498-0.4507 (0.4498) | 0.4492-0.4506 (0.4500) | no | - (alpha 0) | - |
| ibm12 | 0.4499-0.4509 (0.4499) | 0.4487-0.4494 (0.4493) | yes | - (alpha 0) | - |
| ibm15 | 0.4500-0.4502 (0.4501) | 0.4484-0.4497 (0.4485) | yes | - (alpha 0) | - |
| ibm16 | 0.4492-0.4501 (0.4500) | 0.4474-0.4478 (0.4474) | yes | - (alpha 0) | - |
| ibm17 | 0.4499-0.4501 (0.4500) | 0.4496-0.4497 (0.4497) | yes | - (alpha 0) | - |

Sources: runs/remote/band_231/runs/beat_tool/g231/band.json, runs/remote/band_g0/runs/beat_tool/g0/band.json, runs/remote/band_g1/runs/beat_tool/g1/band.json, runs/remote/band_g2/runs/beat_tool/g2/band.json, runs/remote/band_g3/runs/beat_tool/g3/band.json.

## 3 Tool + frozen bridge vs the tool's best of two seeds (endpoint: median J over fresh f1 seeds 1-3)

| design | tool seeds | tool | tool + bridge (guarded) | best of 2 | mean cost s: tool / +bridge / best of 2 |
|---|---|---|---|---|---|
| ibm04 | 8 | 0.4411 | 0.4338 | 0.4316 | 21 / 49 / 54 |
| ibm06 | 8 | 0.4519 | 0.4481 | 0.4480 | 33 / 62 / 79 |
| ibm08 | 8 | 0.6108 | 0.6134 | 0.6124 | 20 / 59 / 55 |

All 24 cases: tool + bridge minus best of 2 = +0.0011 on average, one-sided Wilcoxon p = 0.609 (bridge lower); tool + bridge minus tool = -0.0028, p = 0.0402. Sources: runs/remote/toolref3_ibm04/runs/tool_refine3/ibm04/rows.jsonl, runs/remote/toolref3_ibm06/runs/tool_refine3/ibm06/rows.jsonl, runs/remote/toolref3_ibm08/runs/tool_refine3/ibm08/rows.jsonl.

## 4 Relinking two tool runs vs the tool's best of k (endpoint: median J over fresh f1 seeds 1-3)

Relink: the candidates P_M(T_s + a (T_p - T_s)), a in {0.25, 0.5, 0.75}, T_p another tool run with its interchangeable macros matched to T_s; the best of {T_s, T_p, candidates} by the selection seed (cost: two tool runs and five f1 runs, about the cost of best of 3: three tool runs and three f1 runs).

| design | tool seeds | tool | best of 2 | best of 3 | best of 4 | relink | relink below best of 3 (cases) |
|---|---|---|---|---|---|---|---|
| ibm01 | 8 | 0.4527 | 0.4516 | 0.4506 | 0.4501 | 0.4516 | 0 of 8 (3 above) |
| ibm02 | 8 | 0.2098 | 0.1565 | 0.1562 | 0.1559 | 0.1837 | 2 of 8 (3 above) |
| ibm03 | 8 | 0.4536 | 0.4511 | 0.4505 | 0.4504 | 0.4514 | 2 of 8 (1 above) |
| ibm04 | 8 | 0.4411 | 0.4345 | 0.4307 | 0.4290 | 0.4286 | 4 of 8 (1 above) |
| ibm06 | 8 | 0.4519 | 0.4484 | 0.4476 | 0.4472 | 0.4468 | 4 of 8 (2 above) |
| ibm07 | 8 | 0.4603 | 0.4490 | 0.4459 | 0.4458 | 0.4456 | 3 of 8 (1 above) |
| ibm08 | 8 | 0.6108 | 0.7753 | 0.9416 | 1.1066 | 0.4370 | 6 of 8 (1 above) |
| ibm09 | 8 | 0.4595 | 0.4446 | 0.4411 | 0.4402 | 0.4446 | 0 of 8 (2 above) |
| ibm10 | 8 | 0.4729 | 0.4533 | 0.4520 | 0.4507 | 0.4533 | 0 of 8 (1 above) |
| ibm11 | 8 | 0.4491 | 0.4463 | 0.4456 | 0.4451 | 0.4460 | 2 of 8 (3 above) |
| ibm12 | 8 | 0.4483 | 0.4473 | 0.4467 | 0.4462 | 0.4471 | 1 of 8 (3 above) |
| ibm13 | 8 | 0.4496 | 0.4477 | 0.4473 | 0.4469 | 0.4479 | 2 of 8 (4 above) |
| ibm14 | 8 | 0.4495 | 0.4489 | 0.4488 | 0.4487 | 0.4489 | 1 of 8 (3 above) |
| ibm15 | 8 | 0.4500 | 0.4500 | 0.4499 | 0.4497 | 0.4500 | 2 of 8 (3 above) |
| ibm16 | 8 | 0.4484 | 0.4481 | 0.4478 | 0.4477 | 0.4479 | 2 of 8 (3 above) |
| ibm17 | 8 | 0.4521 | 0.4513 | 0.4510 | 0.4509 | 0.4513 | 0 of 8 (4 above) |
| ibm18 | 8 | 0.4515 | 0.4510 | 0.4495 | 0.4489 | 0.4513 | 0 of 8 (4 above) |
| **all** | 136 | 0.4477 | 0.4503 | 0.4590 | 0.4682 | 0.4314 | 31 of 136 (42 above) |

Relink minus best of 3: -0.0276 on average (median +0.0000), one-sided Wilcoxon p = 0.765; relink minus best of 4 (more compute than relinking): -0.0369 on average (median +0.0000), p = 0.988 over 136 cases, relink lower in 29 and higher in 58. The means are dominated by ibm08, whose tool layouts blow up under some f1 seeds; the medians and the tests are not (exploratory, not registered tests). Sources: runs/remote/relink_ibm04/runs/relink/ibm04/rows.jsonl, runs/remote/relink_ibm06/runs/relink/ibm06/rows.jsonl, runs/remote/relink_ibm08/runs/relink/ibm08/rows.jsonl, runs/remote/relinkall_a/runs/relink/ibm01/rows.jsonl, runs/remote/relinkall_a/runs/relink/ibm02/rows.jsonl, runs/remote/relinkall_a/runs/relink/ibm03/rows.jsonl, runs/remote/relinkall_a/runs/relink/ibm07/rows.jsonl, runs/remote/relinkall_b/runs/relink/ibm09/rows.jsonl, runs/remote/relinkall_b/runs/relink/ibm10/rows.jsonl, runs/remote/relinkall_b/runs/relink/ibm11/rows.jsonl, runs/remote/relinkall_b/runs/relink/ibm12/rows.jsonl, runs/remote/relinkall_c/runs/relink/ibm13/rows.jsonl, runs/remote/relinkall_c/runs/relink/ibm14/rows.jsonl, runs/remote/relinkall_c/runs/relink/ibm18/rows.jsonl, runs/remote/relinkall_d/runs/relink/ibm15/rows.jsonl, runs/remote/relinkall_d/runs/relink/ibm16/rows.jsonl, runs/remote/relinkall_d/runs/relink/ibm17/rows.jsonl.

## 5 Consensus of k tool runs vs the tool's best of k (endpoint: median J over fresh f1 seeds 1-3)

Consensus: the average of k tool layouts with their interchangeable macros matched (a free-support barycenter), legalized by P_M; no f1 run picks it (cost: k tool runs). Best of k: k tool runs and k f1 runs. Guard: the best of the consensus and the k runs by the selection seed (k tool runs, k + 1 f1 runs).

| design | k | windows | tool | best of k | consensus | guard | consensus below best of k (cases) | failures |
|---|---|---|---|---|---|---|---|---|
| ibm04 | 2 | 8 | 0.4411 | 0.4345 | 0.4359 | 0.4317 | 5 of 8 (3 above) | 0 |
| ibm04 | 4 | 8 | 0.4411 | 0.4290 | 0.4421 | 0.4293 | 0 of 8 (8 above) | 0 |
| ibm06 | 2 | 8 | 0.4519 | 0.4484 | 0.4494 | 0.4470 | 4 of 8 (4 above) | 0 |
| ibm06 | 4 | 8 | 0.4519 | 0.4472 | 0.4484 | 0.4467 | 2 of 8 (6 above) | 0 |
| ibm08 | 2 | 8 | 0.6108 | 0.7753 | 0.5801 | 0.6031 | 6 of 8 (2 above) | 0 |
| ibm08 | 4 | 8 | 0.6108 | 1.1066 | 0.6389 | 0.6021 | 7 of 8 (1 above) | 0 |
| **all** | 2 | 24 | 0.5013 | 0.5527 | 0.4885 | 0.4940 | 15 of 24 (9 above) | |
| **all** | 4 | 24 | 0.5013 | 0.6609 | 0.5098 | 0.4927 | 9 of 24 (15 above) | |

k = 2: consensus minus best of k -0.0642 on average over the 24 finite cases, one-sided Wilcoxon p = 0.138 (+inf kept); guard minus best of k -0.0588, p = 0.0115. Windows overlap, so the cases are not independent (exploratory).
k = 4: consensus minus best of k -0.1511 on average over the 24 finite cases, one-sided Wilcoxon p = 0.561 (+inf kept); guard minus best of k -0.1682, p = 0.0178. Windows overlap, so the cases are not independent (exploratory).

Sources: runs/remote/cons_ibm04/runs/consensus/ibm04/rows.jsonl, runs/remote/cons_ibm06/runs/consensus/ibm06/rows.jsonl, runs/remote/cons_ibm08/runs/consensus/ibm08/rows.jsonl.

## 6 Macro orientation pass on the tool's layout (endpoint: median J over fresh f1 seeds 1-3)

The tool never flips a macro. The pass gives each movable macro the footprint-preserving orientation (N, S, FS, FN) that minimizes its nets' weighted HPWL with every other pin where f1 placed it (positions and legality unchanged; scripts/flip_eval.py). Flip: the pass alone (one more f1 run when computed on f1's placement). Guarded: the better of the two by the selection seed. Best of 2 + flip: the guarded pass on the best-of-2 pick (two tool runs, three f1 runs).

| design | cases | tool | flip | guarded | best of 2 | best of 2 + flip | best of 3 | best of 4 | flip below tool | HPWL change with the cells fixed |
|---|---|---|---|---|---|---|---|---|---|---|
| ibm04 | 8 | 0.4411 | 0.4401 | 0.4397 | 0.4345 | 0.4348 | 0.4307 | 0.4290 | 4 of 8 | -0.36 % |
| ibm06 | 8 | 0.4519 | 0.4503 | 0.4508 | 0.4484 | 0.4485 | 0.4476 | 0.4472 | 7 of 8 | -0.13 % |
| ibm07 | 8 | 0.4603 | 0.4577 | 0.4576 | 0.4490 | 0.4479 | 0.4459 | 0.4458 | 6 of 8 | -0.21 % |
| **all** | 24 | 0.4511 | 0.4494 | 0.4494 | 0.4440 | 0.4437 | 0.4414 | 0.4407 | 17 of 24 | |

Flip minus tool -0.0017 (one-sided Wilcoxon p = 0.0106); best of 2 + flip minus best of 2 -0.0003 (p = 0.197), minus best of 3 +0.0023 (p = 0.911). Exploratory. Sources: runs/remote/flip_ibm04/runs/flip/ibm04/rows.jsonl, runs/remote/flip_ibm06/runs/flip/ibm06/rows.jsonl, runs/remote/flip_ibm07/runs/flip/ibm07/rows.jsonl.

## 7 The tool's target density (endpoint: median J over fresh f1 seeds 1-3)

The tool's runs above use DREAMPlace's target density 0.9 (the seeding campaign's M1, which defines J = 0.45); DREAMPlace's own parameter default is 0.8 and its ISPD2005 and mixed-size benchmark configurations use 1.0 (third_party/DREAMPlace/dreamplace/params.json:39-42; third_party/DREAMPlace/test/mms/adaptec1.json). Here the same 8 tool seeds per design at lower densities (scripts/tool_runs.py --target-density); f1 is unchanged (0.9). Per cell: mean J of a single run / of the best of 4 by the selection seed; median tool run time.

| design | density 0.9 | density 0.8 | density 0.7 | density 0.6 | density 0.5 |
|---|---|---|---|---|---|
| ibm01 | 0.4527 / 0.4501 / 17 s | - | 0.4724 / 0.4664 / 34 s | 0.4610 / 0.4568 / 20 s | - |
| ibm02 | 0.2098 / 0.1559 / 22 s | - | 0.1538 / 0.1523 / 26 s | 0.1585 / 0.1558 / 23 s | - |
| ibm03 | 0.4536 / 0.4504 / 23 s | - | 0.4346 / 0.4331 / 30 s | 0.4293 / 0.4282 / 29 s | - |
| ibm04 | 0.4411 / 0.4290 / 20 s | 0.4253 / 0.4224 / 27 s | 0.4166 / 0.4154 / 24 s | 0.4156 / 0.4140 / 32 s | 0.4156 / 0.4140 / 31 s |
| ibm06 | 0.4519 / 0.4472 / 33 s | 0.4452 / 0.4406 / 52 s | 0.4221 / 0.4206 / 50 s | 0.4171 / 0.4154 / 35 s | 0.4171 / 0.4154 / 34 s |
| ibm07 | 0.4603 / 0.4458 / 16 s | - | 0.4371 / 0.4348 / 23 s | 0.4322 / 0.4297 / 24 s | - |
| ibm09 | 0.4595 / 0.4402 / 15 s | - | 0.6812 / 0.4084 / 22 s | 0.4201 / 0.4171 / 19 s | - |
| ibm10 | 0.4729 / 0.4507 / 18 s | 0.4868 / 0.4606 / 22 s | 0.4596 / 0.4294 / 24 s | 0.4493 / 0.4449 / 20 s | 0.4622 / 0.4515 / 24 s |
| ibm11 | 0.4491 / 0.4451 / 17 s | - | 0.4772 / 0.4723 / 21 s | 0.4882 / 0.4849 / 20 s | - |
| ibm12 | 0.4483 / 0.4462 / 17 s | 0.4249 / 0.4234 / 21 s | 0.4195 / 0.4190 / 23 s | 0.4172 / 0.4161 / 24 s | 0.4192 / 0.4179 / 23 s |
| ibm13 | 0.4496 / 0.4469 / 15 s | - | 0.4610 / 0.4551 / 23 s | 0.4729 / 0.4621 / 16 s | - |
| ibm14 | 0.4495 / 0.4487 / 17 s | - | 0.4486 / 0.4482 / 23 s | 0.4478 / 0.4468 / 23 s | - |
| ibm18 | 0.4515 / 0.4489 / 23 s | - | 0.4555 / 0.4545 / 29 s | 0.4552 / 0.4536 / 26 s | - |

- Density 0.8, single run vs density 0.9 single run (paired by tool seed): -0.0080 on average, lower in 24 of 32, one-sided Wilcoxon p = 0.00972; vs density 0.9 best of 4 (four times the runs): +0.0023, lower in 21 of 32, p = 0.287.
- Density 0.7, single run vs density 0.9 single run (paired by tool seed): +0.0069 on average, lower in 67 of 104, one-sided Wilcoxon p = 0.000364; vs density 0.9 best of 4 (four times the runs): +0.0180, lower in 62 of 104, p = 0.0763.
- Density 0.6, single run vs density 0.9 single run (paired by tool seed): -0.0143 on average, lower in 68 of 104, one-sided Wilcoxon p = 0.000134; vs density 0.9 best of 4 (four times the runs): -0.0031, lower in 61 of 104, p = 0.0327.
- Density 0.5, single run vs density 0.9 single run (paired by tool seed): -0.0250 on average, lower in 28 of 32, one-sided Wilcoxon p = 1.77e-07; vs density 0.9 best of 4 (four times the runs): -0.0147, lower in 25 of 32, p = 5.52e-05.
- Density 0.8 was run on 4 designs: ibm04, ibm06, ibm10, ibm12.
- Density 0.7 was run on 13 designs: ibm01, ibm02, ibm03, ibm04, ibm06, ibm07, ibm09, ibm10, ibm11, ibm12, ibm13, ibm14, ibm18.
- Density 0.6 was run on 13 designs: ibm01, ibm02, ibm03, ibm04, ibm06, ibm07, ibm09, ibm10, ibm11, ibm12, ibm13, ibm14, ibm18.
- Density 0.5 was run on 4 designs: ibm04, ibm06, ibm10, ibm12.
- The effect depends on the design (rows above); on the designs where 0.6 is worse than 0.9 (ibm01, ibm11, ibm13, ibm18), 0.7 is worse too.
- Two densities {0.9, 0.8} (the seed-s run at each, the better by the selection seed) vs two seeds at 0.9 (s and s+1), same number of runs: lower in 22 of 32, higher in 4, median 0.4354 vs 0.4473, one-sided Wilcoxon p = 0.00293.
- Two densities {0.9, 0.7} (the seed-s run at each, the better by the selection seed) vs two seeds at 0.9 (s and s+1), same number of runs: lower in 66 of 104, higher in 16, median 0.4365 vs 0.4485, one-sided Wilcoxon p = 3.33e-10.
- Two densities {0.9, 0.6} (the seed-s run at each, the better by the selection seed) vs two seeds at 0.9 (s and s+1), same number of runs: lower in 65 of 104, higher in 20, median 0.4320 vs 0.4485, one-sided Wilcoxon p = 3.11e-10.
- Two densities {0.9, 0.5} (the seed-s run at each, the better by the selection seed) vs two seeds at 0.9 (s and s+1), same number of runs: lower in 26 of 32, higher in 3, median 0.4184 vs 0.4473, one-sided Wilcoxon p = 5.4e-06.

J components where recorded (medians over seeds of the fresh-seed medians): ibm01 at 0.7: HPWL 2.649e+06 um, RUDY overflow 0.000 %; ibm01 at 0.6: HPWL 2.588e+06 um, RUDY overflow 0.000 %; ibm02 at 0.7: HPWL 5.248e+06 um, RUDY overflow 0.006 %; ibm02 at 0.6: HPWL 5.412e+06 um, RUDY overflow 0.011 %; ibm03 at 0.7: HPWL 6.75e+06 um, RUDY overflow 0.005 %; ibm03 at 0.6: HPWL 6.642e+06 um, RUDY overflow 0.002 %; ibm04 at 0.6: HPWL 7.684e+06 um, RUDY overflow 0.013 %; ibm04 at 0.5: HPWL 7.684e+06 um, RUDY overflow 0.013 %; ibm06 at 0.6: HPWL 6.115e+06 um, RUDY overflow 0.021 %; ibm06 at 0.5: HPWL 6.115e+06 um, RUDY overflow 0.021 %; ibm07 at 0.7: HPWL 9.984e+06 um, RUDY overflow 0.159 %; ibm07 at 0.6: HPWL 9.989e+06 um, RUDY overflow 0.108 %; ibm09 at 0.7: HPWL 1.23e+07 um, RUDY overflow 0.106 %; ibm09 at 0.6: HPWL 1.23e+07 um, RUDY overflow 0.204 %; ibm10 at 0.6: HPWL 2.856e+07 um, RUDY overflow 17.384 %; ibm10 at 0.5: HPWL 2.972e+07 um, RUDY overflow 17.518 %; ibm11 at 0.7: HPWL 1.847e+07 um, RUDY overflow 2.735 %; ibm11 at 0.6: HPWL 1.864e+07 um, RUDY overflow 2.931 %; ibm12 at 0.6: HPWL 3.228e+07 um, RUDY overflow 14.807 %; ibm12 at 0.5: HPWL 3.203e+07 um, RUDY overflow 15.361 %; ibm13 at 0.7: HPWL 2.305e+07 um, RUDY overflow 3.965 %; ibm13 at 0.6: HPWL 2.338e+07 um, RUDY overflow 4.245 %; ibm14 at 0.7: HPWL 3.508e+07 um, RUDY overflow 9.918 %; ibm14 at 0.6: HPWL 3.501e+07 um, RUDY overflow 9.864 %; ibm18 at 0.7: HPWL 4.158e+07 um, RUDY overflow 11.897 %; ibm18 at 0.6: HPWL 4.159e+07 um, RUDY overflow 11.849 %.

Exploratory; a tool parameter, not a HeurBridge method. Sources: runs/remote/dens6_a/runs/tool_runs_td0.6/ibm01/rows.jsonl, runs/remote/dens7_a/runs/tool_runs_td0.7/ibm01/rows.jsonl, runs/remote/dens6_a/runs/tool_runs_td0.6/ibm02/rows.jsonl, runs/remote/dens7_a/runs/tool_runs_td0.7/ibm02/rows.jsonl, runs/remote/dens6_a/runs/tool_runs_td0.6/ibm03/rows.jsonl, runs/remote/dens7_a/runs/tool_runs_td0.7/ibm03/rows.jsonl, runs/remote/dens6_b/runs/tool_runs_td0.6/ibm07/rows.jsonl, runs/remote/dens7_b/runs/tool_runs_td0.7/ibm07/rows.jsonl, runs/remote/dens6_b/runs/tool_runs_td0.6/ibm09/rows.jsonl, runs/remote/dens7_b/runs/tool_runs_td0.7/ibm09/rows.jsonl, runs/remote/dens6_c/runs/tool_runs_td0.6/ibm11/rows.jsonl, runs/remote/dens7_b/runs/tool_runs_td0.7/ibm11/rows.jsonl, runs/remote/dens6_c/runs/tool_runs_td0.6/ibm13/rows.jsonl, runs/remote/dens7_c/runs/tool_runs_td0.7/ibm13/rows.jsonl, runs/remote/dens6_d/runs/tool_runs_td0.6/ibm14/rows.jsonl, runs/remote/dens7_c/runs/tool_runs_td0.7/ibm14/rows.jsonl, runs/remote/dens6_d/runs/tool_runs_td0.6/ibm18/rows.jsonl, runs/remote/dens7_c/runs/tool_runs_td0.7/ibm18/rows.jsonl, runs/remote/densB_ibm04/runs/tool_runs_td0.5/ibm04/rows.jsonl, runs/remote/densB_ibm04/runs/tool_runs_td0.6/ibm04/rows.jsonl, runs/remote/dens_ibm04/runs/tool_runs_td0.7/ibm04/rows.jsonl, runs/remote/dens_ibm04/runs/tool_runs_td0.8/ibm04/rows.jsonl, runs/remote/densB_ibm06/runs/tool_runs_td0.5/ibm06/rows.jsonl, runs/remote/densB_ibm06/runs/tool_runs_td0.6/ibm06/rows.jsonl, runs/remote/dens_ibm06/runs/tool_runs_td0.7/ibm06/rows.jsonl, runs/remote/dens_ibm06/runs/tool_runs_td0.8/ibm06/rows.jsonl, runs/remote/densB_ibm10/runs/tool_runs_td0.5/ibm10/rows.jsonl, runs/remote/densB_ibm10/runs/tool_runs_td0.6/ibm10/rows.jsonl, runs/remote/dens_ibm10/runs/tool_runs_td0.7/ibm10/rows.jsonl, runs/remote/dens_ibm10/runs/tool_runs_td0.8/ibm10/rows.jsonl, runs/remote/densB_ibm12/runs/tool_runs_td0.5/ibm12/rows.jsonl, runs/remote/densB_ibm12/runs/tool_runs_td0.6/ibm12/rows.jsonl, runs/remote/dens_ibm12/runs/tool_runs_td0.7/ibm12/rows.jsonl, runs/remote/dens_ibm12/runs/tool_runs_td0.8/ibm12/rows.jsonl.

## 8 The tool started from a given macro layout (endpoint: median J over fresh f1 seeds 1-3)

DREAMPlace's mixed-size run normally starts every object near the die centre (random_center_init_flag = 1). Here it starts from a macro layout with the standard cells at their cluster's quadratic position (random_center_init_flag = 0; scripts/warm_tool_eval.py): heur = the seeding campaign's best layouts (heuristic programs and their local search), self = the tool's own layout T_s (a second pass), cons = the consensus of T_s and T_(s+1). Density as in the first pass unless stated. Per cell: mean J [min, max] over 8 starts; macro move = mean macro displacement from the start (normalized core units).

| design | random start (density 0.9) | heur | self | cons |
|---|---|---|---|---|
| ibm04 | 0.4411 [0.4247, 0.4502] | 0.4274 [0.4181, 0.4338], move 0.53 | 0.4171 [0.4076, 0.4320], move 0.49 | 0.4148 [0.4047, 0.4242], move 0.49 |
| ibm06 | 0.4519 [0.4447, 0.4602] | 0.4629 [0.4578, 0.4713], move 0.48 | 0.4538 [0.4384, 0.4944], move 0.15 | 0.4448 [0.4367, 0.4510], move 0.15 |
| ibm07 | 0.4603 [0.4457, 0.4830] | 0.4465 [0.4363, 0.4630], move 0.49 | 0.4357 [0.4300, 0.4393], move 0.38 | 0.4362 [0.4328, 0.4416], move 0.38 |

Second pass (self) minus the first pass, paired by tool seed: -0.0156 on average, lower in 20 of 24, one-sided Wilcoxon p = 0.000284 (exploratory). Cost: two tool runs, no f1 run to choose.

Sources: runs/remote/warm_ibm04/runs/warm_tool/ibm04/rows.jsonl, runs/remote/warm_ibm06/runs/warm_tool/ibm06/rows.jsonl, runs/remote/warm_ibm07/runs/warm_tool/ibm07/rows.jsonl.

## 9 On top of the tool at density 0.6 (endpoint: median J over fresh f1 seeds 1-3)

Second pass: the tool at 0.6 started from its own first-pass layout (two tool runs). Heuristic start: the tool at 0.6 started from the seeding campaign's best heuristic or local-search layouts instead of its random start (one tool run each). Flip: the orientation pass on the first-pass layout. Per cell: mean J over 8 cases; the reference columns are the first pass at 0.6 (one run) and its best of 2 and 4 by the selection seed.

| design | first pass | best of 2 | best of 4 | second pass | heuristic start | flip |
|---|---|---|---|---|---|---|
| ibm04 | 0.4156 | 0.4145 | 0.4140 | 0.4276 | 0.4252 | 0.4213 |
| ibm06 | 0.4171 | 0.4163 | 0.4154 | 0.4257 | 0.4415 | 0.4167 |
| ibm10 | 0.4493 | 0.4466 | 0.4449 | 0.4470 | 0.4442 | 0.4483 |
| ibm12 | 0.4172 | 0.4163 | 0.4161 | 0.9696 | 0.4321 | - |

- Second pass minus the first pass (paired by tool seed): +0.1427, lower in 11 of 32, one-sided Wilcoxon p = 1; minus the first pass's best of 2: +0.1440, p = 1.
- Heuristic start against the first pass (unpaired): mean +0.0110, one-sided Mann-Whitney p = 1; against its best of 2: mean +0.0123, p = 1.
- Flip minus the first pass (paired by tool seed): +0.0014, lower in 14 of 24, one-sided Wilcoxon p = 0.698; minus the first pass's best of 2: +0.0030, p = 0.999.

Exploratory. Sources: runs/remote/pass2_a/runs/warm_tool_td0.6/ibm04/rows.jsonl, runs/remote/heur06_a/runs/warm_tool_td0.6_heur/ibm04/rows.jsonl, runs/remote/flip06/runs/flip_td0.6/ibm04/rows.jsonl, runs/remote/pass2_a/runs/warm_tool_td0.6/ibm06/rows.jsonl, runs/remote/heur06_a/runs/warm_tool_td0.6_heur/ibm06/rows.jsonl, runs/remote/flip06/runs/flip_td0.6/ibm06/rows.jsonl, runs/remote/pass2_b/runs/warm_tool_td0.6/ibm10/rows.jsonl, runs/remote/heur06_a/runs/warm_tool_td0.6_heur/ibm10/rows.jsonl, runs/remote/flip06/runs/flip_td0.6/ibm10/rows.jsonl, runs/remote/pass2_c/runs/warm_tool_td0.6/ibm12/rows.jsonl, runs/remote/heur06_b/runs/warm_tool_td0.6_heur/ibm12/rows.jsonl.

## 10 Local search from the tool's layout (endpoint: median J over fresh f1 seeds 1-3)

Shift-only local search from the tool's layout at density 0.9 (scripts/tool_ls_pairs.py; 4 tool seeds per design), each step scored by f1 with the selection seed; the result is kept as a refiner pair only if its fresh-seed median is lower than the tool layout's. Per design: runs kept, mean change of the fresh-seed median [min, max].

| design | runs | kept | change |
|---|---|---|---|
| ibm01 | 4 | 3 | -0.0007 [-0.0015, +0.0002] |
| ibm02 | 4 | 4 | -0.0007 [-0.0015, -0.0002] |
| ibm03 | 4 | 2 | -0.0027 [-0.0091, +0.0009] |
| ibm07 | 4 | 2 | -0.0010 [-0.0046, +0.0013] |
| ibm09 | 4 | 3 | -0.0118 [-0.0371, +0.0019] |
| ibm10 | 4 | 4 | -0.0004 [-0.0008, -0.0000] |
| ibm11 | 4 | 4 | -0.0031 [-0.0070, -0.0013] |
| ibm13 | 4 | 3 | -0.0010 [-0.0030, +0.0006] |
| ibm14 | 4 | 1 | +0.0001 [-0.0002, +0.0003] |
| ibm15 | 4 | 3 | -0.0004 [-0.0013, +0.0006] |
| ibm18 | 4 | 2 | -0.0000 [-0.0006, +0.0007] |

All 44 runs: kept 31; change -0.0020 on average, median -0.0005; lower in 31, higher in 13. Cost: median 81 f1 runs and 843 s per search against 28 s for a tool run. Failures: none. Sources: runs/remote/lspairs_a/runs/tool_ls/a/rows.jsonl, runs/remote/lspairs_b/runs/tool_ls/b/rows.jsonl, runs/remote/lspairs_c/runs/tool_ls/c/rows.jsonl, runs/remote/lspairs_d/runs/tool_ls/d/rows.jsonl.

## Notes

- f1 is noisy: the same macro layout scored with another DREAMPlace seed changes J, and on some designs a run blows the overflow term up (ibm08: J 0.44 under one seed, 1.5-4.6 under another). Every comparison above therefore picks with one seed and judges with fresh seeds (median of three, as the tool's own baseline).
- The run files are local (`runs/remote/`, not in the public repository); the scripts that made them are named in each section's title.

