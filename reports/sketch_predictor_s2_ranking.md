# Sketch redesign S2: ranking check (look-ahead part of the S2 bar)

| Field | Value |
|---|---|
| Report | lookahead_rank |
| Date | 2026-10-03 00:47 |
| Node | 225 (RTX 3090) |
| Track | A (labels: DREAMPlace f1 placements, scripts/make_cell_labels.py) |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v3_2026-09-29 |
| Feeds gate | none (S2 diagnostic) |
| Pre-registered test | - (bar fixed before any S2 result: local plan, S2 row) |
| alpha-ledger entry | - |
| Status of the claim | no claim |

**Bar (fixed before any S2 result):** DA0 ratio <= 0.5 against the quadratic placement; Kendall tau(predicted J, actual f1 J) >= 0.5 per design; top-1 regret <= 25 % of random's.

**Outcome against the bar (the bar above is unchanged):** ibm04: S2 Kendall tau 0.152, top-1 regret 0.0394 = 0.42 of random's: **fails**. ibm06: tau 0.523, top-1 regret 0.0072 = 0.017 of random's: passes. The bar requires every validation design, so **S2 fails its look-ahead part as well as its distance part** (DA0 0.747 / 0.642, unchanged from reports/sketch_predictor_s2.md). Two observations, not bar changes: (1) on ibm04 even the placed clusters themselves, scored the same way, reach only tau 0.441, so no cluster-level prediction scored this way can reach 0.5 there; (2) on ibm06 S2 ranks no better than the quadratic placement (tau 0.523 both) but picks better (top-1 regret 0.0072 against 0.0211). As a selector among the 261 labelled layouts, the S2 first pick is 0.0394 (ibm04) and 0.0072 (ibm06) above the best layout's J; f0's first pick 0.0396 and 0.0525; random selection's expectation 0.0947 and 0.4283. Exploratory reference, not S2: the HB-GP coarse placement of the clustered netlist is closer to the placed clusters than S2 (DA0 0.593 and 0.490) but ranks worse on ibm06, and with the footprint spread its first pick on ibm06 is a congested layout 12.2 above the best (so is the S2 centroids' with the footprint spread): the predicted spread matters for the overflow term. Supplementary: the 13 training designs follow the two validation designs; S2 was trained on them (in-sample), the other predictors were not. Across them the median Kendall tau is 0.476 for S2, 0.507 for the coarse placement, 0.637 for the placed clusters, 0.411 for f0 and 0.222 for the quadratic placement; f0's first pick is the best layout on 10 of the 13 (its regret@1 is 0 there).

## ibm04 (261 layouts: br 128, el 5, src 128; S2 checkpoint step 4000)

Sanity: the label's own placed cells through the same metric code reproduce its J within a relative 2.6e-04.

| predictor | DA0 ratio (median) | Kendall tau, all | tau, heuristic sources | tau, bridge endpoints | top-5 recall | regret@1 / random's | regret@5 / random's | tau of HPWL | tau of overflow |
|---|---|---|---|---|---|---|---|---|---|
| quadratic placement (S2 control) | 1 (by definition) | 0.039 | 0.021 | 0.109 | 0.00 | 0.0528 / 0.0947 | 0.0105 / 0.0308 | 0.325 | 0.147 |
| S2 predictor | 0.747 | 0.152 | 0.177 | 0.205 | 0.00 | 0.0394 / 0.0947 | 0.0102 / 0.0308 | 0.167 | 0.227 |
| S2 centroids, footprint spread | - | 0.172 | 0.251 | 0.162 | 0.00 | 0.0394 / 0.0947 | 0.0394 / 0.0308 | 0.366 | 0.226 |
| HB-GP coarse placement (exploratory reference) | 0.593 | 0.238 | 0.200 | 0.293 | 0.00 | 0.0190 / 0.0947 | 0.0106 / 0.0308 | 0.393 | 0.262 |
| placed clusters (oracle) | - | 0.441 | 0.425 | 0.484 | 0.00 | 0.0190 / 0.0947 | 0.0190 / 0.0308 | 0.374 | 0.469 |
| f0 surrogate (macro stage) | - | 0.252 | 0.224 | 0.295 | 0.00 | 0.0396 / 0.0947 | 0.0390 / 0.0308 | - | - |

## ibm06 (261 layouts: br 128, el 5, src 128; S2 checkpoint step 4000)

Sanity: the label's own placed cells through the same metric code reproduce its J within a relative 2.5e-04.

| predictor | DA0 ratio (median) | Kendall tau, all | tau, heuristic sources | tau, bridge endpoints | top-5 recall | regret@1 / random's | regret@5 / random's | tau of HPWL | tau of overflow |
|---|---|---|---|---|---|---|---|---|---|
| quadratic placement (S2 control) | 1 (by definition) | 0.523 | 0.598 | 0.394 | 0.40 | 0.0211 / 0.4283 | 0.0004 / 0.0133 | -0.426 | 0.491 |
| S2 predictor | 0.642 | 0.523 | 0.552 | 0.360 | 0.00 | 0.0072 / 0.4283 | 0.0005 / 0.0133 | 0.225 | 0.384 |
| S2 centroids, footprint spread | - | 0.215 | 0.185 | 0.212 | 0.00 | 12.1986 / 0.4283 | 12.1986 / 0.0133 | 0.014 | 0.111 |
| HB-GP coarse placement (exploratory reference) | 0.490 | 0.167 | 0.189 | 0.203 | 0.00 | 12.1986 / 0.4283 | 12.1986 / 0.0133 | 0.315 | 0.145 |
| placed clusters (oracle) | - | 0.746 | 0.763 | 0.712 | 0.00 | 0.0081 / 0.4283 | 0.0042 / 0.0133 | 0.737 | 0.635 |
| f0 surrogate (macro stage) | - | -0.381 | -0.490 | -0.279 | 0.00 | 0.0525 / 0.4283 | 0.0525 / 0.0133 | - | - |

## ibm01 (261 layouts: br 128, el 5, src 128; S2 checkpoint step 4000)

Sanity: the label's own placed cells through the same metric code reproduce its J within a relative 7.5e-05.

| predictor | DA0 ratio (median) | Kendall tau, all | tau, heuristic sources | tau, bridge endpoints | top-5 recall | regret@1 / random's | regret@5 / random's | tau of HPWL | tau of overflow |
|---|---|---|---|---|---|---|---|---|---|
| quadratic placement (S2 control) | 1 (by definition) | -0.514 | -0.620 | -0.496 | 0.00 | 0.1383 / 0.1364 | 0.1383 / 0.0716 | 0.734 | 0.086 |
| S2 predictor | 0.692 | 0.310 | 0.253 | 0.414 | 0.00 | 0.1395 / 0.1364 | 0.0632 / 0.0716 | 0.651 | 0.246 |
| S2 centroids, footprint spread | - | 0.283 | 0.240 | 0.340 | 0.00 | 0.1395 / 0.1364 | 0.0632 / 0.0716 | 0.483 | 0.214 |
| HB-GP coarse placement (exploratory reference) | 0.798 | 0.252 | 0.246 | 0.262 | 0.00 | 0.0671 / 0.1364 | 0.0671 / 0.0716 | 0.627 | -0.053 |
| placed clusters (oracle) | - | 0.190 | -0.013 | 0.394 | 0.20 | 0.0000 / 0.1364 | 0.0000 / 0.0716 | 0.624 | 0.376 |
| f0 surrogate (macro stage) | - | 0.794 | 0.832 | 0.803 | 0.40 | 0.0000 / 0.1364 | 0.0000 / 0.0716 | - | - |

## ibm02 (261 layouts: br 128, el 5, src 128; S2 checkpoint step 4000)

Sanity: the label's own placed cells through the same metric code reproduce its J within a relative 2.3e-04.

| predictor | DA0 ratio (median) | Kendall tau, all | tau, heuristic sources | tau, bridge endpoints | top-5 recall | regret@1 / random's | regret@5 / random's | tau of HPWL | tau of overflow |
|---|---|---|---|---|---|---|---|---|---|
| quadratic placement (S2 control) | 1 (by definition) | 0.101 | 0.079 | 0.124 | 0.00 | 0.0176 / 0.0407 | 0.0117 / 0.0079 | 0.448 | 0.113 |
| S2 predictor | 0.694 | 0.593 | 0.697 | 0.456 | 0.00 | 0.0023 / 0.0407 | 0.0023 / 0.0079 | 0.519 | 0.570 |
| S2 centroids, footprint spread | - | 0.488 | 0.677 | 0.226 | 0.00 | 0.0023 / 0.0407 | 0.0023 / 0.0079 | 0.421 | 0.538 |
| HB-GP coarse placement (exploratory reference) | 0.655 | 0.268 | 0.432 | 0.099 | 0.00 | 0.0304 / 0.0407 | 0.0304 / 0.0079 | 0.580 | 0.217 |
| placed clusters (oracle) | - | 0.706 | 0.730 | 0.624 | 0.20 | 0.0004 / 0.0407 | 0.0004 / 0.0079 | 0.684 | 0.713 |
| f0 surrogate (macro stage) | - | 0.492 | 0.595 | 0.414 | 0.40 | 0.0000 / 0.0407 | 0.0000 / 0.0079 | - | - |

## ibm03 (261 layouts: br 128, el 5, src 128; S2 checkpoint step 4000)

Sanity: the label's own placed cells through the same metric code reproduce its J within a relative 7.9e-05.

| predictor | DA0 ratio (median) | Kendall tau, all | tau, heuristic sources | tau, bridge endpoints | top-5 recall | regret@1 / random's | regret@5 / random's | tau of HPWL | tau of overflow |
|---|---|---|---|---|---|---|---|---|---|
| quadratic placement (S2 control) | 1 (by definition) | 0.593 | 0.565 | 0.559 | 0.00 | 0.0512 / 1.7005 | 0.0473 / 0.0605 | -0.201 | 0.632 |
| S2 predictor | 0.717 | 0.737 | 0.714 | 0.728 | 0.20 | 0.0000 / 1.7005 | 0.0000 / 0.0605 | 0.707 | 0.709 |
| S2 centroids, footprint spread | - | 0.652 | 0.565 | 0.723 | 0.20 | 0.0000 / 1.7005 | 0.0000 / 0.0605 | 0.018 | 0.609 |
| HB-GP coarse placement (exploratory reference) | 0.720 | 0.527 | 0.426 | 0.642 | 0.40 | 11.4757 / 1.7005 | 0.0000 / 0.0605 | 0.224 | 0.447 |
| placed clusters (oracle) | - | 0.802 | 0.830 | 0.700 | 0.40 | 0.0473 / 1.7005 | 0.0000 / 0.0605 | 0.805 | 0.796 |
| f0 surrogate (macro stage) | - | 0.087 | 0.063 | 0.141 | 0.20 | 0.0000 / 1.7005 | 0.0000 / 0.0605 | - | - |

## ibm07 (261 layouts: br 128, el 5, src 128; S2 checkpoint step 4000)

Sanity: the label's own placed cells through the same metric code reproduce its J within a relative 2.2e-04.

| predictor | DA0 ratio (median) | Kendall tau, all | tau, heuristic sources | tau, bridge endpoints | top-5 recall | regret@1 / random's | regret@5 / random's | tau of HPWL | tau of overflow |
|---|---|---|---|---|---|---|---|---|---|
| quadratic placement (S2 control) | 1 (by definition) | 0.492 | 0.500 | 0.460 | 0.00 | 0.0133 / 0.5570 | 0.0133 / 0.0359 | 0.007 | 0.459 |
| S2 predictor | 0.629 | 0.594 | 0.602 | 0.585 | 0.20 | 0.0386 / 0.5570 | 0.0000 / 0.0359 | 0.367 | 0.552 |
| S2 centroids, footprint spread | - | 0.553 | 0.576 | 0.525 | 0.20 | 0.0386 / 0.5570 | 0.0000 / 0.0359 | 0.506 | 0.496 |
| HB-GP coarse placement (exploratory reference) | 0.600 | 0.621 | 0.666 | 0.626 | 0.00 | 0.0064 / 0.5570 | 0.0064 / 0.0359 | 0.226 | 0.561 |
| placed clusters (oracle) | - | 0.659 | 0.632 | 0.631 | 0.00 | 0.0133 / 0.5570 | 0.0064 / 0.0359 | 0.526 | 0.626 |
| f0 surrogate (macro stage) | - | -0.223 | -0.301 | -0.157 | 0.20 | 0.0000 / 0.5570 | 0.0000 / 0.0359 | - | - |

## ibm09 (261 layouts: br 128, el 5, src 128; S2 checkpoint step 4000)

Sanity: the label's own placed cells through the same metric code reproduce its J within a relative 7.1e-04.

| predictor | DA0 ratio (median) | Kendall tau, all | tau, heuristic sources | tau, bridge endpoints | top-5 recall | regret@1 / random's | regret@5 / random's | tau of HPWL | tau of overflow |
|---|---|---|---|---|---|---|---|---|---|
| quadratic placement (S2 control) | 1 (by definition) | 0.465 | 0.546 | 0.418 | 0.00 | 0.0128 / 1.5564 | 0.0089 / 0.0366 | -0.210 | 0.508 |
| S2 predictor | 0.625 | 0.601 | 0.689 | 0.511 | 0.20 | 0.0000 / 1.5564 | 0.0000 / 0.0366 | 0.559 | 0.572 |
| S2 centroids, footprint spread | - | 0.557 | 0.619 | 0.440 | 0.20 | 0.0000 / 1.5564 | 0.0000 / 0.0366 | 0.109 | 0.538 |
| HB-GP coarse placement (exploratory reference) | 0.577 | 0.507 | 0.503 | 0.488 | 0.00 | 11.4448 / 1.5564 | 11.4448 / 0.0366 | 0.123 | 0.507 |
| placed clusters (oracle) | - | 0.751 | 0.855 | 0.627 | 0.60 | 0.0000 / 1.5564 | 0.0000 / 0.0366 | 0.592 | 0.735 |
| f0 surrogate (macro stage) | - | -0.221 | -0.353 | -0.088 | 0.20 | 0.0000 / 1.5564 | 0.0000 / 0.0366 | - | - |

## ibm10 (237 layouts: br 128, el 5, src 104; S2 checkpoint step 4000)

Sanity: the label's own placed cells through the same metric code reproduce its J within a relative 1.6e-04.

| predictor | DA0 ratio (median) | Kendall tau, all | tau, heuristic sources | tau, bridge endpoints | top-5 recall | regret@1 / random's | regret@5 / random's | tau of HPWL | tau of overflow |
|---|---|---|---|---|---|---|---|---|---|
| quadratic placement (S2 control) | 1 (by definition) | 0.720 | 0.618 | 0.740 | 0.20 | 0.0000 / 0.2754 | 0.0000 / 0.1771 | 0.498 | 0.382 |
| S2 predictor | 0.880 | 0.785 | 0.748 | 0.769 | 0.20 | 0.0000 / 0.2754 | 0.0000 / 0.1771 | 0.711 | 0.531 |
| S2 centroids, footprint spread | - | 0.754 | 0.690 | 0.750 | 0.20 | 0.0000 / 0.2754 | 0.0000 / 0.1771 | 0.539 | 0.514 |
| HB-GP coarse placement (exploratory reference) | 1.135 | 0.693 | 0.746 | 0.649 | 0.60 | 0.0000 / 0.2754 | 0.0000 / 0.1771 | 0.532 | 0.723 |
| placed clusters (oracle) | - | 0.688 | 0.599 | 0.678 | 0.80 | 0.0000 / 0.2754 | 0.0000 / 0.1771 | 0.696 | 0.613 |
| f0 surrogate (macro stage) | - | 0.773 | 0.691 | 0.801 | 0.60 | 0.0000 / 0.2754 | 0.0000 / 0.1771 | - | - |

## ibm11 (261 layouts: br 128, el 5, src 128; S2 checkpoint step 4000)

Sanity: the label's own placed cells through the same metric code reproduce its J within a relative 2.7e-04.

| predictor | DA0 ratio (median) | Kendall tau, all | tau, heuristic sources | tau, bridge endpoints | top-5 recall | regret@1 / random's | regret@5 / random's | tau of HPWL | tau of overflow |
|---|---|---|---|---|---|---|---|---|---|
| quadratic placement (S2 control) | 1 (by definition) | 0.210 | 0.173 | 0.128 | 0.00 | 0.1659 / 0.3753 | 0.0581 / 0.0826 | 0.055 | 0.276 |
| S2 predictor | 0.632 | 0.476 | 0.635 | 0.308 | 0.00 | 0.0739 / 0.3753 | 0.0547 / 0.0826 | 0.554 | 0.514 |
| S2 centroids, footprint spread | - | 0.418 | 0.599 | 0.210 | 0.00 | 0.1213 / 0.3753 | 0.0929 / 0.0826 | 0.309 | 0.467 |
| HB-GP coarse placement (exploratory reference) | 0.476 | 0.337 | 0.268 | 0.263 | 0.00 | 0.1013 / 0.3753 | 0.0581 / 0.0826 | 0.182 | 0.370 |
| placed clusters (oracle) | - | 0.637 | 0.586 | 0.617 | 0.60 | 0.0000 / 0.3753 | 0.0000 / 0.0826 | 0.534 | 0.679 |
| f0 surrogate (macro stage) | - | 0.079 | 0.072 | 0.162 | 0.20 | 0.0000 / 0.3753 | 0.0000 / 0.0826 | - | - |

## ibm13 (261 layouts: br 128, el 5, src 128; S2 checkpoint step 4000)

Sanity: the label's own placed cells through the same metric code reproduce its J within a relative 2.2e-04.

| predictor | DA0 ratio (median) | Kendall tau, all | tau, heuristic sources | tau, bridge endpoints | top-5 recall | regret@1 / random's | regret@5 / random's | tau of HPWL | tau of overflow |
|---|---|---|---|---|---|---|---|---|---|
| quadratic placement (S2 control) | 1 (by definition) | 0.115 | 0.233 | -0.110 | 0.00 | 0.2564 / 0.2074 | 0.2457 / 0.1272 | -0.065 | 0.133 |
| S2 predictor | 0.584 | 0.240 | 0.380 | 0.074 | 0.20 | 0.1119 / 0.2074 | 0.0937 / 0.1272 | 0.224 | 0.264 |
| S2 centroids, footprint spread | - | 0.221 | 0.361 | 0.098 | 0.20 | 0.1733 / 0.2074 | 0.0937 / 0.1272 | 0.296 | 0.230 |
| HB-GP coarse placement (exploratory reference) | 0.590 | 0.314 | 0.504 | 0.111 | 0.60 | 0.1070 / 0.2074 | 0.0811 / 0.1272 | 0.028 | 0.308 |
| placed clusters (oracle) | - | 0.431 | 0.528 | 0.407 | 0.60 | 0.0000 / 0.2074 | 0.0000 / 0.1272 | 0.382 | 0.507 |
| f0 surrogate (macro stage) | - | -0.027 | -0.156 | 0.145 | 0.20 | 0.0000 / 0.2074 | 0.0000 / 0.1272 | - | - |

## ibm14 (240 layouts: br 128, el 5, src 107; S2 checkpoint step 4000)

Sanity: the label's own placed cells through the same metric code reproduce its J within a relative 2.4e-04.

| predictor | DA0 ratio (median) | Kendall tau, all | tau, heuristic sources | tau, bridge endpoints | top-5 recall | regret@1 / random's | regret@5 / random's | tau of HPWL | tau of overflow |
|---|---|---|---|---|---|---|---|---|---|
| quadratic placement (S2 control) | 1 (by definition) | 0.222 | 0.123 | 0.196 | 0.20 | 0.0000 / 0.2206 | 0.0000 / 0.1360 | 0.389 | 0.009 |
| S2 predictor | 0.661 | 0.510 | 0.486 | 0.509 | 0.80 | 0.0000 / 0.2206 | 0.0000 / 0.1360 | 0.749 | 0.333 |
| S2 centroids, footprint spread | - | 0.601 | 0.519 | 0.655 | 0.20 | 0.0000 / 0.2206 | 0.0000 / 0.1360 | 0.752 | 0.324 |
| HB-GP coarse placement (exploratory reference) | 0.547 | 0.515 | 0.536 | 0.485 | 0.20 | 0.0000 / 0.2206 | 0.0000 / 0.1360 | 0.484 | 0.394 |
| placed clusters (oracle) | - | 0.650 | 0.646 | 0.658 | 0.80 | 0.0000 / 0.2206 | 0.0000 / 0.1360 | 0.581 | 0.617 |
| f0 surrogate (macro stage) | - | 0.464 | 0.410 | 0.470 | 0.20 | 0.0000 / 0.2206 | 0.0000 / 0.1360 | - | - |

## ibm15 (261 layouts: br 128, el 5, src 128; S2 checkpoint step 4000)

Sanity: the label's own placed cells through the same metric code reproduce its J within a relative 2.5e-04.

| predictor | DA0 ratio (median) | Kendall tau, all | tau, heuristic sources | tau, bridge endpoints | top-5 recall | regret@1 / random's | regret@5 / random's | tau of HPWL | tau of overflow |
|---|---|---|---|---|---|---|---|---|---|
| quadratic placement (S2 control) | 1 (by definition) | 0.386 | 0.339 | 0.402 | 0.00 | 0.0830 / 0.1428 | 0.0699 / 0.0759 | 0.193 | 0.030 |
| S2 predictor | 0.618 | 0.168 | 0.008 | 0.183 | 0.00 | 0.1062 / 0.1428 | 0.1062 / 0.0759 | 0.208 | 0.223 |
| S2 centroids, footprint spread | - | 0.145 | 0.009 | 0.194 | 0.20 | 0.0000 / 0.1428 | 0.0000 / 0.0759 | 0.165 | 0.238 |
| HB-GP coarse placement (exploratory reference) | 0.542 | 0.592 | 0.518 | 0.637 | 0.20 | 0.0000 / 0.1428 | 0.0000 / 0.0759 | 0.216 | 0.101 |
| placed clusters (oracle) | - | 0.557 | 0.406 | 0.625 | 0.40 | 0.0000 / 0.1428 | 0.0000 / 0.0759 | 0.618 | 0.541 |
| f0 surrogate (macro stage) | - | 0.267 | 0.389 | 0.255 | 0.00 | 0.0965 / 0.1428 | 0.0965 / 0.0759 | - | - |

## ibm16 (253 layouts: br 128, el 5, src 120; S2 checkpoint step 4000)

Sanity: the label's own placed cells through the same metric code reproduce its J within a relative 1.8e-04.

| predictor | DA0 ratio (median) | Kendall tau, all | tau, heuristic sources | tau, bridge endpoints | top-5 recall | regret@1 / random's | regret@5 / random's | tau of HPWL | tau of overflow |
|---|---|---|---|---|---|---|---|---|---|
| quadratic placement (S2 control) | 1 (by definition) | 0.539 | 0.554 | 0.547 | 0.20 | 0.0000 / 0.0819 | 0.0000 / 0.0411 | 0.304 | -0.046 |
| S2 predictor | 0.685 | 0.425 | 0.346 | 0.503 | 0.80 | 0.0208 / 0.0819 | 0.0208 / 0.0411 | 0.544 | 0.181 |
| S2 centroids, footprint spread | - | 0.441 | 0.311 | 0.548 | 0.80 | 0.0234 / 0.0819 | 0.0208 / 0.0411 | 0.468 | 0.137 |
| HB-GP coarse placement (exploratory reference) | 0.601 | 0.698 | 0.581 | 0.832 | 1.00 | 0.0000 / 0.0819 | 0.0000 / 0.0411 | 0.323 | 0.266 |
| placed clusters (oracle) | - | 0.544 | 0.423 | 0.595 | 0.40 | 0.0234 / 0.0819 | 0.0234 / 0.0411 | 0.498 | 0.567 |
| f0 surrogate (macro stage) | - | 0.444 | 0.460 | 0.458 | 0.20 | 0.0000 / 0.0819 | 0.0000 / 0.0411 | - | - |

## ibm17 (237 layouts: br 128, el 5, src 104; S2 checkpoint step 4000)

Sanity: the label's own placed cells through the same metric code reproduce its J within a relative 1.8e-04.

| predictor | DA0 ratio (median) | Kendall tau, all | tau, heuristic sources | tau, bridge endpoints | top-5 recall | regret@1 / random's | regret@5 / random's | tau of HPWL | tau of overflow |
|---|---|---|---|---|---|---|---|---|---|
| quadratic placement (S2 control) | 1 (by definition) | -0.249 | -0.257 | -0.256 | 0.00 | 0.1079 / 0.0937 | 0.1079 / 0.0497 | 0.443 | -0.298 |
| S2 predictor | 0.810 | 0.122 | 0.067 | 0.109 | 0.20 | 0.0000 / 0.0937 | 0.0000 / 0.0497 | -0.130 | 0.311 |
| S2 centroids, footprint spread | - | -0.102 | -0.195 | -0.045 | 0.00 | 0.1460 / 0.0937 | 0.0738 / 0.0497 | -0.120 | 0.140 |
| HB-GP coarse placement (exploratory reference) | 0.912 | 0.297 | 0.373 | 0.248 | 0.00 | 0.1666 / 0.0937 | 0.1079 / 0.0497 | 0.562 | -0.214 |
| placed clusters (oracle) | - | 0.612 | 0.588 | 0.631 | 0.80 | 0.0000 / 0.0937 | 0.0000 / 0.0497 | 0.570 | 0.656 |
| f0 surrogate (macro stage) | - | 0.411 | 0.477 | 0.437 | 0.00 | 0.0619 / 0.0937 | 0.0619 / 0.0497 | - | - |

## ibm18 (261 layouts: br 128, el 5, src 128; S2 checkpoint step 4000)

Sanity: the label's own placed cells through the same metric code reproduce its J within a relative 2.4e-04.

| predictor | DA0 ratio (median) | Kendall tau, all | tau, heuristic sources | tau, bridge endpoints | top-5 recall | regret@1 / random's | regret@5 / random's | tau of HPWL | tau of overflow |
|---|---|---|---|---|---|---|---|---|---|
| quadratic placement (S2 control) | 1 (by definition) | -0.433 | -0.324 | -0.515 | 0.00 | 0.0844 / 0.0441 | 0.0720 / 0.0229 | 0.530 | -0.398 |
| S2 predictor | 0.730 | 0.117 | 0.227 | -0.020 | 0.00 | 0.0506 / 0.0441 | 0.0506 / 0.0229 | -0.045 | 0.129 |
| S2 centroids, footprint spread | - | 0.033 | 0.079 | 0.021 | 0.00 | 0.0334 / 0.0441 | 0.0289 / 0.0229 | -0.105 | 0.067 |
| HB-GP coarse placement (exploratory reference) | 0.847 | -0.109 | -0.001 | -0.224 | 0.00 | 0.0844 / 0.0441 | 0.0720 / 0.0229 | 0.378 | -0.167 |
| placed clusters (oracle) | - | 0.414 | 0.476 | 0.321 | 0.00 | 0.0178 / 0.0441 | 0.0178 / 0.0229 | 0.391 | 0.406 |
| f0 surrogate (macro stage) | - | 0.493 | 0.413 | 0.559 | 0.00 | 0.0299 / 0.0441 | 0.0233 / 0.0229 | - | - |

