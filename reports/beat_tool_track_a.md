# Beating the tool on Track A: feasibility, noise and equal-compute comparisons

| Field | Value |
|---|---|
| Report | beat_tool_track_a |
| Date | 2026-10-03 03:18 |
| Track | A (IBM; f1 = DREAMPlace GP + LG with macros fixed; J against the seeding M1 baseline, 0.45 by construction) |
| Status of the claim | **exploratory demo (no claim)**; any claim needs the pre-registered test drafted from it |
| Owner's aim (3 Oct) | macro layouts with mean J below 0.45 that beat the tool on output and on cost |

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

| design | tool seeds | tool | best of 2 | best of 3 | relink | relink below best of 3 (cases) |
|---|---|---|---|---|---|---|
| ibm04 | 8 | 0.4411 | 0.4345 | 0.4307 | 0.4286 | 4 of 8 (1 above) |
| ibm06 | 8 | 0.4519 | 0.4484 | 0.4476 | 0.4468 | 4 of 8 (2 above) |
| ibm08 | 8 | 0.6108 | 0.7753 | 0.9416 | 0.4370 | 6 of 8 (1 above) |
| **all** | 24 | 0.5013 | 0.5527 | 0.6067 | 0.4375 | 14 of 24 (4 above) |

Relink minus best of 3: -0.1692 on average, one-sided Wilcoxon p = 0.00448 (exploratory, not a registered test). Sources: runs/remote/relink_ibm04/runs/relink/ibm04/rows.jsonl, runs/remote/relink_ibm06/runs/relink/ibm06/rows.jsonl, runs/remote/relink_ibm08/runs/relink/ibm08/rows.jsonl.

## Notes

- f1 is noisy: the same macro layout scored with another DREAMPlace seed changes J, and on some designs a run blows the overflow term up (ibm08: J 0.44 under one seed, 1.5-4.6 under another). Every comparison above therefore picks with one seed and judges with fresh seeds (median of three, as the tool's own baseline).
- The run files are local (`runs/remote/`, not in the public repository); the scripts that made them are named in each section's title.

