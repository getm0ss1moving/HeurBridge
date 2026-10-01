# Sketch redesign S2: ranking check (look-ahead part of the S2 bar)

| Field | Value |
|---|---|
| Report | lookahead_rank |
| Date | 2026-10-02 02:40 |
| Node | 225 (RTX 3090) |
| Track | A (labels: DREAMPlace f1 placements, scripts/make_cell_labels.py) |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v3_2026-09-29 |
| Feeds gate | none (S2 diagnostic) |
| Pre-registered test | - (bar fixed before any S2 result: local plan, S2 row) |
| alpha-ledger entry | - |
| Status of the claim | no claim |

**Bar (fixed before any S2 result):** DA0 ratio <= 0.5 against the quadratic placement; Kendall tau(predicted J, actual f1 J) >= 0.5 per design; top-1 regret <= 25 % of random's.

**Outcome against the bar (the bar above is unchanged):** ibm04: S2 Kendall tau 0.152, top-1 regret 0.0394 = 0.42 of random's: **fails**. ibm06: tau 0.523, top-1 regret 0.0072 = 0.017 of random's: passes. The bar requires every validation design, so **S2 fails its look-ahead part as well as its distance part** (DA0 0.747 / 0.642, unchanged from reports/sketch_predictor_s2.md). Two observations, not bar changes: (1) on ibm04 even the placed clusters themselves, scored the same way, reach only tau 0.441, so no cluster-level prediction scored this way can reach 0.5 there; (2) on ibm06 S2 ranks no better than the quadratic placement (tau 0.523 both) but picks better (top-1 regret 0.0072 against 0.0211). As a selector among the 261 labelled layouts, the S2 first pick is 0.0394 (ibm04) and 0.0072 (ibm06) above the best layout's J; f0's first pick 0.0396 and 0.0525; random selection's expectation 0.0947 and 0.4283. Exploratory reference, not S2: the HB-GP coarse placement of the clustered netlist is closer to the placed clusters than S2 (DA0 0.593 and 0.490) but ranks worse on ibm06, and with the footprint spread its first pick on ibm06 is a congested layout 12.2 above the best (so is the S2 centroids' with the footprint spread): the predicted spread matters for the overflow term.

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

