# Sketch redesign S2: cell-stage predictor

| Field | Value |
|---|---|
| Report | lookahead_s2 |
| Date | 2026-10-01 07:16 |
| Node | 225 (RTX 3090, GPU 0) |
| Track | A (labels: DREAMPlace f1 placements on the CPU, 234) |
| HeurBridge version / git | 0.14.0 / 9366ae1bc0f5c901de58f13a9730491d00bb672b |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v3_2026-09-29 |
| Feeds gate | none (diagnostic step S2 of the sketch redesign) |
| Pre-registered test | - (bar fixed before any result: local plan, S2) |
| alpha-ledger entry | - |
| Status of the claim | no claim |

## Setup

Predictor: the bridge's encoder (initialized from checkpoints/algR_trackA_final/best.pt) with a centroid-shift and a spread head, one forward pass from the committed macros with the clusters at their quadratic placement. Training designs ibm01,ibm02,ibm03,ibm07,ibm09,ibm10,ibm11,ibm13,ibm14,ibm15,ibm16,ibm17,ibm18; validation ibm04,ibm06; 20000 steps, batch 16, lr 0.0001, spread weight 0.1. Labels: `scripts/make_cell_labels.py` on 234 (3,838 DREAMPlace placements, 0 failures). Measure: per sample, the area-weighted RMS distance of the predicted cluster centroids to the placed ones, divided by the same distance for the quadratic placement; median per design. **Bar: <= 0.5 on every validation design.**

## Result

| step | ibm04 ratio | ibm06 ratio | mean | train ratio |
|---|---|---|---|---|
| 0 (initialization) | 0.860 | 0.843 | 0.851 | - |
| 2000 | 0.758 | 0.691 | 0.725 | 0.775 |
| 4000 | 0.747 | 0.642 | 0.695 | 0.686 |
| 6000 | 0.780 | 0.661 | 0.720 | 0.646 |
| 8000 | 0.779 | 0.658 | 0.718 | 0.611 |
| 10000 | 0.778 | 0.671 | 0.724 | 0.585 |
| 12000 | 0.768 | 0.645 | 0.706 | 0.569 |
| 14000 | 0.775 | 0.657 | 0.716 | 0.550 |
| 16000 | 0.788 | 0.669 | 0.728 | 0.537 |
| 18000 | 0.796 | 0.678 | 0.737 | 0.537 |
| 20000 | 0.799 | 0.673 | 0.736 | 0.536 |

**Best checkpoint (step 4000):** ibm04 median distance 0.236 against 0.299 for the quadratic placement (ratio 0.747; closer in 239 of 261; by kind br 0.779, el 0.546, src 0.720); ibm06 median distance 0.180 against 0.303 for the quadratic placement (ratio 0.642; closer in 252 of 261; by kind br 0.632, el 0.693, src 0.681).

**Outcome:** does not reach the bar of 0.5; the training ratio keeps falling while validation rises after the best step (fitting the training designs, not generalizing).

## Reproduce

`python scripts/train_lookahead.py --suite ibm --train ibm01,ibm02,ibm03,ibm07,ibm09,ibm10,ibm11,ibm13,ibm14,ibm15,ibm16,ibm17,ibm18 --val ibm04,ibm06 --labels runs/cell_labels --runs runs/seed_trackA_dp --init checkpoints/algR_trackA_final/best.pt --steps 20000 --batch 16 --lr 0.0001 --wd 0.01 --warmup 1000 --lam-cov 0.1 --val-every 2000 --seed 0 --device cuda --out checkpoints/lookahead_s2`; `python scripts/train_lookahead.py --report runs/remote/s2_lookahead_225/checkpoints/lookahead_s2 --out reports/sketch_predictor_s2.md`.
