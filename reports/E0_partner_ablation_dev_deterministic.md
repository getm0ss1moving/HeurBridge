# E0 partner-type ablation (development)

| Field | Value |
|---|---|
| Report | det_f1guard_equal_randctl |
| Date | 2026-09-26 09:16 |
| Node | local (macOS, CPU) |
| Track | A-dev (HB-GP stand-in final cost, single-threaded; bridge guard at f1, equal f1 guard, random-direction control) |
| Tool versions | HeurBridge 0.10.3 |
| HeurBridge version / git | 0.10.6 / 517dfb46bc458d21df8e10c6fc251524c2d3c97d+dirty |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v1_2026-09-25 |
| Feeds gate | G0' (co-trained beats memetic AND repertoire at p < 0.01 on the held-out family) |
| Pre-registered test | paired one-sided Wilcoxon, co-trained < each partner, Holm over the comparisons |
| alpha-ledger entry | E0_dev#4 |
| Status of the claim | no claim (development / descriptive run) |

## Sample sizes

64 paired cases (design x program x seed); designs ibm04,ibm06

## Results

| partner | mean J | portfolio J | Kendall tau vs raw | co-trained better: frac | one-sided p | Holm p_adj |
|---|---|---|---|---|---|---|
| cotrained | 0.4936 | 0.4300 | 0.85 | - | - | - |
| memetic | 0.5858 | 0.4310 | 0.9666666666666666 | 0.52 | 8.56e-05 | 0.000257 |
| none | 0.5903 | 0.4323 | 1.0 | 0.53 | 1.82e-07 | 7.27e-07 |
| random_guard | 0.4935 | 0.4323 | 0.8999999999999999 | 0.44 | 0.0564 | 0.0564 |
| repertoire | 0.5770 | 0.4323 | 0.975 | 0.47 | 0.00608 | 0.0122 |

| partner | wins vs raw | losses | ties | median dJ vs raw | geometric-mean J ratio vs raw |
|---|---|---|---|---|---|
| cotrained | 34 | 0 | 30 | -0.0008 | 0.9303 |
| memetic | 19 | 0 | 45 | +0.0000 | 0.9925 |
| random_guard | 24 | 0 | 40 | +0.0000 | 0.9333 |
| repertoire | 19 | 0 | 45 | +0.0000 | 0.9848 |

Guard: the co-trained bridge's guard scores its alpha candidates at **f1**; equal guard for the other partners: **True**.

**G0' decision (development, not the pre-registered test):** co-trained vs memetic p = 8.56e-05, vs repertoire p = 0.00608 -> PASS.

**Learned-transport check:** co-trained vs the random-direction control (the same guard along a random displacement of matched length) p = 0.0564 (Holm-adjusted 0.0564). The bridge's direction is not distinguishable from a random one at this sample size: a G0' pass here cannot be attributed to the learned transport.

## Failures (by name, counted as +inf in statistics)

none

## Exact commands

```bash
python scripts/run_e0.py --suite ibm --designs ibm04,ibm06 --runs ./runs/seed_dev --bridge checkpoints/bridge_dev_r0/best.pt --final hbgp --seeds 2 --K 20 --out runs/e0_dev/det_f1guard_equal_randctl --campaign E0_dev --guard-fidelity f1 --equal-guard True --random-control True
```

## Notes

raw rows: runs/e0_dev/det_f1guard_equal_randctl/e0_rows.jsonl. Wins / losses count paired cases where the partner's final J is below / above the raw layout's; the geometric-mean ratio < 1 means lower J on average in log terms.
