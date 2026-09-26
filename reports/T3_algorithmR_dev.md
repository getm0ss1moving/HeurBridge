# Algorithm R (T3.7) — macro-stage bridge rounds (development)

| Field | Value |
|---|---|
| Report | algR_dev |
| Date | 2026-09-26 08:11 |
| Node | local (macOS, CPU) |
| Track | A-dev (HB-GP stand-in f1, single-threaded) |
| Tool versions | HeurBridge 0.10.5 |
| HeurBridge version / git | 0.10.5 / c4dfda4639f7ffd4764d41af89e35c87fe885dc9+dirty |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v1_2026-09-25 |
| Feeds gate | T3 exit (round 0: post-guard f1 < raw on validation, paired p < 0.05) and V5 promotion per round |
| Pre-registered test | paired one-sided Wilcoxon at the ledger's alpha_j (reserved before the round's costs are computed) |
| alpha-ledger entry | algR_dev#1, algR_dev#2 |
| Status of the claim | no claim (development / descriptive run) |

## Sample sizes

validation designs ibm03, 16 sources per design; training designs ibm01,ibm02

## Results

> **Caveat.** With the f1 guard, alpha = 0 (the raw heuristic) is always a candidate, so the bridged cost is <= raw by construction; with the deterministic evaluator the round-0 gains are real f1 improvements, but this test cannot tell learned transport from guarded search (see the E0 random-direction control). The dev population does not evolve between rounds, so round 1's DAgger set repeats round 0's pairs.

| round | checkpoint | mean J (candidate) | mean J (incumbent) | one-sided p | alpha_j | promoted | ledger |
|---|---|---|---|---|---|---|---|
| 0 | checkpoints/bridge_dev_r0/best.pt | 0.5578 | 0.6009 | 0.000481 | 0.025 | True | algR_dev#1 |
| 1 | checkpoints/algR_dev/round1/best.pt | 0.5569 | 0.5578 | 0.389 | 0.0125 | False | algR_dev#2 |

Round 0's incumbent is the raw heuristic (the T3 exit test: post-guard f1 cost < raw, paired); round r > 0 compares the round-r bridge with the promoted incumbent, both guarded. Stop rule: improvement < 0.5% of J or a failed promotion. MMD^2 between training and validation design state cards: not valid in this run (-0.25833474970795556 came from the estimator fixed in 0.10.6: with one validation design the unbiased statistic is undefined).

## Failures (by name, counted as +inf in statistics)

none

## Exact commands

```bash
python scripts/algorithm_r.py --suite ibm --train ibm01,ibm02 --val ibm03 --rounds 1 --archive archive_dev_v2 --runs runs/seed_dev --out checkpoints/algR_dev --steps 400 --val-sources 16 --campaign algR_dev --device cpu --round0-dir checkpoints/bridge_dev_r0 --guard f1
```

## Notes

Per-round pairs and checkpoints under checkpoints/algR_dev (not in the repository).
