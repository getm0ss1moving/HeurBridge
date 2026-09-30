# Sketch fine-tune (redesign step S1): corrected cell targets

| Field | Value |
|---|---|
| Report | sketch_quality |
| Date | 2026-09-30 15:09 |
| Node | 231 (RTX 4090, GPU 4) |
| Track | A (DREAMPlace f1 with the macros fixed; J on the seeding campaign's M1 scale) |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v3_2026-09-29 |
| Feeds gate | none (diagnostic step of the sketch redesign) |
| Pre-registered test | - (pass rule fixed before any result: HANDOFF 30 Sep 09:30) |
| alpha-ledger entry | - |
| Status of the claim | no claim |

## Setup

Three fine-tunes of the E0 bridge (`bridge_v1_e0_frozen`, sha256 f95bdde8...; 8,000 steps at lr 1e-4 on the 13 IBM training designs, best checkpoint by the usual validation criterion): `ft_ctrl` on unchanged data, `ft_targets` with the baselines' cell targets corrected (DREAMPlace's centroids, `m1_cluster_pos.py`), `ft_both` with the corrected targets and 10x the loss weight on the cell clusters. Validation designs ibm04,ibm06.

- **Offline error:** each of the 128 sources' bridge endpoint (alpha 1) against its paired elite (the training target, with the corrected cell targets); area-weighted RMS in core units, for the cell clusters and the macros.
- **DA0:** 32 sources per design; each model's endpoint is legalized and placed by DREAMPlace (cells from the centre, as always); its sketch and the quadratic placement of the same macros are compared with the placed cluster centroids. The same placements give the endpoint's f1 J.

## Result

| model | offline cluster error | offline macro error | DA0 sketch | DA0 quadratic | ratio | sketch closer | f1 J (median) |
|---|---|---|---|---|---|---|---|
| source (quadratic) | 0.299 | 0.463 | - | - | - | - | - |
| final | 0.317 | 0.483 | 0.217 | 0.257 | 0.84 | 47 / 64 | 0.4786 |
| ft_ctrl | 0.317 | 0.476 | 0.215 | 0.262 | 0.82 | 56 / 64 | 0.4854 |
| ft_targets | 0.343 | 0.489 | 0.211 | 0.253 | 0.83 | 47 / 64 | 0.4797 |
| ft_both | 0.345 | 0.498 | 0.213 | 0.260 | 0.82 | 49 / 64 | 0.4737 |

**Pass rule, per design** (fixed before any result): DA0 ratio <= 0.70 and f1 J at most 0.5 % above `final`.

| design | model | DA0 sketch | DA0 quadratic | ratio | f1 J (median) | vs final | passes |
|---|---|---|---|---|---|---|---|
| ibm04 | final | 0.225 | 0.244 | 0.92 | 0.5376 | +0.0 % | no |
| ibm04 | ft_ctrl | 0.219 | 0.242 | 0.90 | 0.5427 | +0.9 % | no |
| ibm04 | ft_targets | 0.229 | 0.240 | 0.95 | 0.5287 | -1.7 % | no |
| ibm04 | ft_both | 0.231 | 0.260 | 0.89 | 0.5422 | +0.9 % | no |
| ibm06 | final | 0.214 | 0.264 | 0.81 | 0.4538 | +0.0 % | no |
| ibm06 | ft_ctrl | 0.211 | 0.272 | 0.77 | 0.4597 | +1.3 % | no |
| ibm06 | ft_targets | 0.195 | 0.263 | 0.74 | 0.4531 | -0.1 % | no |
| ibm06 | ft_both | 0.175 | 0.252 | 0.70 | 0.4509 | -0.6 % | yes |

**Outcome:** no fine-tuned model passes on every design; correcting the targets alone does not make the transport's cluster output a good predictor of the placement.

## Offline error by training step (cluster / macro)

| model | step 1600 | step 3200 | step 4800 | step 6400 | step 8000 |
|---|---|---|---|---|---|
| ft_ctrl | 0.316 / 0.480 | 0.317 / 0.476 | 0.327 / 0.480 | 0.326 / 0.478 | 0.330 / 0.481 |
| ft_targets | 0.343 / 0.489 | 0.363 / 0.487 | 0.367 / 0.484 | 0.369 / 0.480 | 0.368 / 0.483 |
| ft_both | 0.345 / 0.498 | 0.357 / 0.488 | 0.362 / 0.491 | 0.363 / 0.491 | 0.367 / 0.494 |

The quadratic source's offline error is 0.299 / 0.463.

## Reproduce

The job file `ft_job2.cmd` (HANDOFF 30 Sep): `m1_cluster_pos.py`, three `train_bridge.py` fine-tunes, then `eval_sketch_quality.py --placer` and the per-step evaluation;
`python scripts/eval_sketch_quality.py --report runs/sketch_quality.json --steps runs/sketch_quality_steps.json --out reports/sketch_finetune_s1.md`.
