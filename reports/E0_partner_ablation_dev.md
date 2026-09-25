# E0 partner-type ablation (development)

| Field | Value |
|---|---|
| Report | heldout_r0 |
| Date | 2026-09-26 04:16 |
| Node | local (macOS, CPU) |
| Track | A-dev (HB-GP stand-in final cost; f0 guard for every partner) |
| Tool versions | HeurBridge 0.9.1 |
| HeurBridge version / git | 0.10.1 / b4dd4224721d71a2ca9d3b1f19a6b032fa9c6436+dirty |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v1_2026-09-25 |
| Feeds gate | G0' (co-trained beats memetic AND repertoire at p < 0.01 on the held-out family) |
| Pre-registered test | paired one-sided Wilcoxon, co-trained < each partner, Holm over the comparisons |
| alpha-ledger entry | E0_dev#1 |
| Status of the claim | no claim (development / descriptive run) |

## Sample sizes

160 paired cases (design x program x seed); designs ibm04,ibm06

## Results

| partner | mean J | portfolio J | Kendall tau vs raw | co-trained better: frac | one-sided p | Holm p_adj |
|---|---|---|---|---|---|---|
| cotrained | 0.5086 | 0.4293 | 0.7166666666666666 | - | - | - |
| memetic | 0.5878 | 0.4300 | 0.975 | 0.41 | 0.99 | 1 |
| none | 0.5869 | 0.4315 | 1.0 | 0.44 | 0.985 | 1 |
| repertoire | 0.5824 | 0.4297 | 0.9166666666666667 | 0.47 | 0.681 | 1 |

| partner | wins vs raw | losses | ties | median dJ vs raw | geometric-mean J ratio vs raw |
|---|---|---|---|---|---|
| cotrained | 71 | 89 | 0 | +0.0004 | 0.9643 |
| memetic | 78 | 82 | 0 | +0.0000 | 1.0013 |
| repertoire | 60 | 100 | 0 | +0.0009 | 1.0049 |

Guard: the co-trained bridge's guard scores its alpha candidates at **f0 (fixed before v0.10.1)**; equal guard for the other partners: **False**.

**G0' decision (development, not the pre-registered test):** co-trained vs memetic p = 0.99, vs repertoire p = 0.681 -> FAIL.

## Failures (by name, counted as +inf in statistics)

none

## Exact commands

```bash
python scripts/run_e0.py --suite ibm --designs ibm04,ibm06 --runs ./runs/seed_dev --bridge checkpoints/bridge_dev_r0/best.pt --final hbgp --seeds 5 --K 20 --out runs/e0_dev/heldout_r0 --campaign E0_dev
```

## Notes

raw rows: runs/e0_dev/heldout_r0/e0_rows.jsonl. Wins / losses count paired cases where the partner's final J is below / above the raw layout's; the geometric-mean ratio < 1 means lower J on average in log terms.
