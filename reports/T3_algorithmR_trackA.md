# Algorithm R (T3.7) — macro-stage bridge rounds

| Field | Value |
|---|---|
| Report | algR_trackA |
| Date | 2026-09-28 16:05 |
| Node | 225 (RTX 3090, GPU 0) |
| Track | A (final cost = DREAMPlace f1 vs the M1 baseline; bridge guard at f1) |
| Tool versions | HeurBridge 0.13.3 |
| HeurBridge version / git | 0.14.0 / 1419689cacb4b7a216a9a420a3b02cc8eba042a2+dirty |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v2_2026-09-28 |
| Feeds gate | T3 exit (round 0: post-guard f1 < raw on validation, paired p < 0.05) and V5 promotion per round |
| Pre-registered test | paired one-sided Wilcoxon at the ledger's alpha_j (reserved before the round's costs are computed) |
| alpha-ledger entry | algR_trackA#1, algR_trackA#2, algR_trackA#3 |
| Status of the claim | gate PASSED: the pre-registered claim may be stated |

## Sample sizes

validation designs ibm04,ibm06, 32 sources per design; training designs ibm01,ibm02,ibm03,ibm07,ibm09,ibm10,ibm11,ibm13,ibm14,ibm15,ibm16,ibm17,ibm18

## Results

> **Caveat.** Validation designs ibm04 and ibm06; the guard selects alpha with the same f1 that scores the final cost and alpha = 0 is the raw layout, so round 0's 'bridge < raw' holds partly by construction -- E0 (partner ablation) is the test of the learned transport. Round 1 regenerated the heuristic sources (identical programs and seeds); rounds 2-3 reused round 0's cache (CHANGELOG).

| round | checkpoint | mean J (candidate) | mean J (incumbent) | one-sided p | alpha_j | promoted | ledger |
|---|---|---|---|---|---|---|---|
| 0 | checkpoints/algR_trackA/round0/best.pt | 0.4815 | 0.8870 | 2.56e-09 | 0.025 | True | algR_trackA#1 |
| 1 | checkpoints/algR_trackA/round1/best.pt | 0.4756 | 0.4815 | 0.000123 | 0.0125 | True | algR_trackA#2 |
| 2 | checkpoints/algR_trackA/round2/best.pt | 0.4864 | 0.4756 | 1 | 0.00625 | False | algR_trackA#3 |

Training per round (validation: mean guarded f0 cost of the validation sources, lower is better; raw heuristics 1.8368):

| round | training steps | best validation criterion (step) | last criterion | improved sources (best) |
|---|---|---|---|---|
| 0 | 20000 | 1.7655 (4000) | 1.7844 | 1.00 |
| 1 | 20000 | 1.7727 (4000) | 1.7856 | 0.95 |
| 2 | 20000 | 1.7836 (4000) | 1.7848 | 0.94 |

Round 0's incumbent is the raw heuristic (the T3 exit test: post-guard f1 cost < raw, paired); round r > 0 compares the round-r bridge with the promoted incumbent, both guarded. Stop rule: improvement < 0.5% of J or a failed promotion. MMD^2 between training and validation design state cards: unbiased 0.4756, biased 0.5980.

## Failures (by name, counted as +inf in statistics)

none

## Exact commands

```bash
python scripts/algorithm_r.py --suite ibm --train ibm01,ibm02,ibm03,ibm07,ibm09,ibm10,ibm11,ibm13,ibm14,ibm15,ibm16,ibm17,ibm18 --val ibm04,ibm06 --rounds 3 --archive archive_A0_trackA --runs runs/seed_trackA_dp --out checkpoints/algR_trackA --steps 20000 --val-sources 32 --pretrained checkpoints/pretrain_small/pretrain_small.pt --campaign algR_trackA --device cuda --guard f1 --final dreamplace
```

## Notes

Per-round pairs and checkpoints under runs/remote/algR_trackA2/checkpoints/algR_trackA (not in the repository).

Training data (added 2026-09-28 20:30, checked on the fetched pair shards): round 0 = 1,608 pairs on the 13 training
designs (16 seed programs x 8 seeds, 104-128 legal sources per design; each paired with the nearest of the design's
top-5 archive elites). Rounds 1 and 2 added no new information: the seed programs are fixed until T5 and the archive
is not updated with bridge outputs, so their pairs are identical to round 0's (x0, x1, weights, struct_err equal on
ibm01, ibm09, ibm18) and the DAgger aggregation holds 2 and 3 copies of them. Round 1's gain is further fine-tuning
on the same data.
