# Sketch redesign S2: cell-stage predictor with the bridge's augmentation (one change)

| Field | Value |
|---|---|
| Report | lookahead_s2 |
| Date | 2026-10-03 00:47 |
| Node | 225 (RTX 3090, GPU 0) |
| Track | A (labels: DREAMPlace f1 placements on the CPU, 234) |
| HeurBridge version / git | 0.14.0 / 75b424c83b373a91dd82caa7dc83284d37b1d1d7+dirty |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v3_2026-09-29 |
| Feeds gate | none (diagnostic step S2 of the sketch redesign) |
| Pre-registered test | - (bar fixed before any result: local plan, S2) |
| alpha-ledger entry | - |
| Status of the claim | no claim |

## Setup

Predictor: the bridge's encoder (initialized from checkpoints/algR_trackA_final/best.pt) with a centroid-shift and a spread head, one forward pass from the committed macros with the clusters at their quadratic placement. Training designs ibm01,ibm02,ibm03,ibm07,ibm09,ibm10,ibm11,ibm13,ibm14,ibm15,ibm16,ibm17,ibm18; validation ibm04,ibm06; 20000 steps, batch 16, lr 0.0001, spread weight 0.1, augmentation dihedral + aspect (as the bridge). Labels: `scripts/make_cell_labels.py` on 234 (3,838 DREAMPlace placements, 0 failures). Measure: per sample, the area-weighted RMS distance of the predicted cluster centroids to the placed ones, divided by the same distance for the quadratic placement; median per design. **Bar: <= 0.5 on every validation design.**

## Result

| step | ibm04 ratio | ibm06 ratio | mean | train ratio |
|---|---|---|---|---|
| 0 (initialization) | 0.860 | 0.843 | 0.851 | - |
| 2000 | 0.738 | 0.689 | 0.714 | 0.800 |
| 4000 | 0.741 | 0.682 | 0.712 | 0.738 |
| 6000 | 0.771 | 0.632 | 0.702 | 0.716 |
| 8000 | 0.777 | 0.611 | 0.694 | 0.697 |
| 10000 | 0.794 | 0.598 | 0.696 | 0.694 |
| 12000 | 0.802 | 0.606 | 0.704 | 0.677 |
| 14000 | 0.805 | 0.613 | 0.709 | 0.671 |
| 16000 | 0.812 | 0.610 | 0.711 | 0.671 |
| 18000 | 0.823 | 0.616 | 0.720 | 0.669 |
| 20000 | 0.828 | 0.615 | 0.721 | 0.671 |

**Best checkpoint (step 8000):** ibm04 median distance 0.228 against 0.299 for the quadratic placement (ratio 0.777; closer in 238 of 261; by kind br 0.791, el 0.529, src 0.743); ibm06 median distance 0.169 against 0.303 for the quadratic placement (ratio 0.611; closer in 251 of 261; by kind br 0.605, el 0.663, src 0.620).

**Outcome:** does not reach the bar of 0.5. After the best step the training ratio goes from 0.697 to 0.671 and the validation ratios end at ibm04 0.828, ibm06 0.615.

## Reproduce

`python scripts/train_lookahead.py --suite ibm --train ibm01,ibm02,ibm03,ibm07,ibm09,ibm10,ibm11,ibm13,ibm14,ibm15,ibm16,ibm17,ibm18 --val ibm04,ibm06 --labels runs/cell_labels --runs runs/seed_trackA_dp --init checkpoints/algR_trackA_final/best.pt --steps 20000 --batch 16 --lr 0.0001 --wd 0.01 --warmup 1000 --lam-cov 0.1 --val-every 2000 --augment True --seed 0 --device cuda --out checkpoints/lookahead_s2_aug`; `python scripts/train_lookahead.py --report runs/remote/s2_aug_225/checkpoints/lookahead_s2_aug --out reports/sketch_predictor_s2_aug.md`.

## Ranking check (look-ahead part of the same bar)

Bar, fixed before any S2 result: Kendall tau(predicted J, actual f1 J) >= 0.5 per validation design and top-1 regret <= 25 % of random's (scripts/eval_lookahead_rank.py on the best checkpoint, step 8000; job `s2rank_aug_225`).

**Outcome:** ibm04 tau 0.114, top-1 regret 0.0418 = 0.44 of random's: fails; ibm06 tau 0.401: fails (its first pick is the best layout, regret 0, top-5 recall 0.60). Without augmentation the taus were 0.152 and 0.523 (reports/sketch_predictor_s2_ranking.md): augmentation brings the centroids closer on ibm06 but orders the layouts worse on both designs. **S2 with augmentation misses both parts of the bar.**

### ibm04 (261 layouts: br 128, el 5, src 128; S2 checkpoint step 8000)

Sanity: the label's own placed cells through the same metric code reproduce its J within a relative 1.9e-04.

| predictor | DA0 ratio (median) | Kendall tau, all | tau, heuristic sources | tau, bridge endpoints | top-5 recall | regret@1 / random's | regret@5 / random's | tau of HPWL | tau of overflow |
|---|---|---|---|---|---|---|---|---|---|
| quadratic placement (S2 control) | 1 (by definition) | 0.039 | 0.021 | 0.109 | 0.00 | 0.0528 / 0.0947 | 0.0105 / 0.0308 | 0.325 | 0.147 |
| S2 predictor | 0.777 | 0.114 | 0.259 | -0.003 | 0.00 | 0.0418 / 0.0947 | 0.0305 / 0.0308 | 0.172 | 0.196 |
| S2 centroids, footprint spread | - | 0.136 | 0.361 | -0.034 | 0.20 | 0.0418 / 0.0947 | 0.0000 / 0.0308 | 0.417 | 0.208 |
| placed clusters (oracle) | - | 0.441 | 0.425 | 0.484 | 0.00 | 0.0190 / 0.0947 | 0.0190 / 0.0308 | 0.374 | 0.469 |
| f0 surrogate (macro stage) | - | 0.252 | 0.224 | 0.295 | 0.00 | 0.0396 / 0.0947 | 0.0390 / 0.0308 | - | - |

### ibm06 (261 layouts: br 128, el 5, src 128; S2 checkpoint step 8000)

Sanity: the label's own placed cells through the same metric code reproduce its J within a relative 1.8e-04.

| predictor | DA0 ratio (median) | Kendall tau, all | tau, heuristic sources | tau, bridge endpoints | top-5 recall | regret@1 / random's | regret@5 / random's | tau of HPWL | tau of overflow |
|---|---|---|---|---|---|---|---|---|---|
| quadratic placement (S2 control) | 1 (by definition) | 0.523 | 0.598 | 0.394 | 0.40 | 0.0211 / 0.4283 | 0.0004 / 0.0133 | -0.426 | 0.491 |
| S2 predictor | 0.611 | 0.401 | 0.344 | 0.390 | 0.60 | 0.0000 / 0.4283 | 0.0000 / 0.0133 | 0.299 | 0.220 |
| S2 centroids, footprint spread | - | 0.343 | 0.333 | 0.358 | 0.00 | 12.1986 / 0.4283 | 12.1986 / 0.0133 | -0.056 | 0.184 |
| placed clusters (oracle) | - | 0.746 | 0.763 | 0.712 | 0.00 | 0.0081 / 0.4283 | 0.0042 / 0.0133 | 0.737 | 0.635 |
| f0 surrogate (macro stage) | - | -0.381 | -0.490 | -0.279 | 0.00 | 0.0525 / 0.4283 | 0.0525 / 0.0133 | - | - |

