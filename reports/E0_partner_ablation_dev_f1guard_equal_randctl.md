# E0 partner-type ablation (development)

| Field | Value |
|---|---|
| Report | heldout_r0_f1guard_equal_randctl |
| Date | 2026-09-26 06:39 |
| Node | local (macOS, CPU) |
| Track | A-dev (HB-GP stand-in final cost; bridge guard at f1, equal f1 guard, random-direction control) |
| Tool versions | HeurBridge 0.10.3 |
| HeurBridge version / git | 0.10.3 / 9e17205a15599a7a060a7de2d66c9d7c13bd343b+dirty |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v1_2026-09-25 |
| Feeds gate | G0' (co-trained beats memetic AND repertoire at p < 0.01 on the held-out family) |
| Pre-registered test | paired one-sided Wilcoxon, co-trained < each partner, Holm over the comparisons |
| alpha-ledger entry | E0_dev#3 |
| Status of the claim | no claim (development / descriptive run) |

## Sample sizes

64 paired cases (design x program x seed); designs ibm04,ibm06

## Results

> **Caveat.** HB-GP (the dev final cost) ran multi-threaded here and is not reproducible across processes: the same layout's J differs by a median of 7e-4 (max 3.4e-3) between runs. The bridge's f1 guard and the equal guard select the minimum over candidates using the same evaluations that are reported as the final cost, so the guarded partners' wins include selection on this noise (winner's curse). Superseded by the deterministic rerun (single-threaded HB-GP, ledger E0_dev#4). The none / memetic / repertoire / co-trained rows were copied from the run above (ledger E0_dev#2); only the random control was evaluated in this process, so its comparison with raw also carries the cross-process noise (14 'losses' against raw that its guard makes impossible within one process).

| partner | mean J | portfolio J | Kendall tau vs raw | co-trained better: frac | one-sided p | Holm p_adj |
|---|---|---|---|---|---|---|
| cotrained | 0.4941 | 0.4298 | 0.8666666666666667 | - | - | - |
| memetic | 0.5871 | 0.4315 | 0.9750000000000001 | 0.53 | 2.12e-05 | 6.37e-05 |
| none | 0.5910 | 0.4321 | 1.0 | 0.55 | 1.23e-07 | 4.93e-07 |
| random_guard | 0.4935 | 0.4323 | 0.8833333333333333 | 0.56 | 0.0706 | 0.0706 |
| repertoire | 0.5782 | 0.4321 | 1.0 | 0.48 | 0.00524 | 0.0105 |

| partner | wins vs raw | losses | ties | median dJ vs raw | geometric-mean J ratio vs raw |
|---|---|---|---|---|---|
| cotrained | 35 | 0 | 29 | -0.0012 | 0.9307 |
| memetic | 16 | 0 | 48 | +0.0000 | 0.9937 |
| random_guard | 50 | 14 | 0 | -0.0009 | 0.9329 |
| repertoire | 18 | 0 | 46 | +0.0000 | 0.9869 |

Guard: the co-trained bridge's guard scores its alpha candidates at **f1**; equal guard for the other partners: **True**.

**G0' decision (development, not the pre-registered test):** co-trained vs memetic p = 2.12e-05, vs repertoire p = 0.00524 -> PASS.

**Learned-transport check:** co-trained vs the random-direction control (the same guard along a random displacement of matched length) p = 0.0706 (Holm-adjusted 0.0706). The bridge's direction is not distinguishable from a random one at this sample size: a G0' pass here cannot be attributed to the learned transport.

## Failures (by name, counted as +inf in statistics)

none

## Exact commands

```bash
python scripts/run_e0.py --suite ibm --designs ibm04,ibm06 --runs ./runs/seed_dev --bridge checkpoints/bridge_dev_r0/best.pt --final hbgp --seeds 2 --K 20 --out runs/e0_dev/heldout_r0_f1guard_equal_randctl --campaign E0_dev --guard-fidelity f1 --equal-guard True --random-control True
```

## Notes

raw rows: runs/e0_dev/heldout_r0_f1guard_equal_randctl/e0_rows.jsonl. Wins / losses count paired cases where the partner's final J is below / above the raw layout's; the geometric-mean ratio < 1 means lower J on average in log terms.
