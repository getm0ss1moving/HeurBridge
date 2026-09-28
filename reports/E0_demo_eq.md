# E0 partner-type ablation (demo)

| Field | Value |
|---|---|
| Report | e0_demo_eq |
| Date | 2026-09-28 15:26 |
| Node | 225 (RTX 3090, GPUs 1-3) |
| Track | A (final cost = DREAMPlace f1 vs the M1 baseline); equal guard: every partner's output kept only if it beats the raw layout at f1 |
| Tool versions | HeurBridge 0.13.4 |
| HeurBridge version / git | 0.14.0 / 90ad3975465e5cfb86a2e5ecb4e943caf3469003+dirty |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v2_2026-09-28 |
| Feeds gate | G0' (co-trained beats memetic AND repertoire at p < 0.01 on the held-out family) |
| Pre-registered test | paired one-sided Wilcoxon, co-trained < each partner, Holm over the comparisons |
| alpha-ledger entry | E0_demo_eq#1, E0_demo_eq#1 |
| Status of the claim | no claim (development / descriptive run) |

## Sample sizes

64 paired cases (design x program x seed); designs ibm04,ibm06

## Results

> **Caveat.** Exploratory demo (direction check), not the pre-registered G0' test. Designs ibm04 and ibm06 are the validation designs on which T3.7 selected the bridge checkpoint (round 1, sha256 f95bdde8...), so the result is optimistic for the bridge; 16 programs x 2 seeds. The confirmatory E0 (E0#1) runs on the held-out family ISPD2005 with the final T3.7 checkpoint and 5 seeds.

| partner | mean J | portfolio J | Kendall tau vs raw | co-trained better: frac | one-sided p | Holm p_adj |
|---|---|---|---|---|---|---|
| cotrained | 0.4822 | 0.4368 | 0.6 | - | - | - |
| frozen_gen | 0.5032 | 0.4427 | 0.875 | 0.73 | 2.09e-06 | 2.09e-06 |
| memetic | 0.6970 | 0.4427 | 0.95 | 0.77 | 1.4e-09 | 4.21e-09 |
| none | 0.8970 | 0.4427 | 1.0 | 0.84 | 8.1e-11 | 3.24e-10 |
| random_guard | 0.5084 | 0.4427 | 0.8833333333333333 | 0.78 | 2.32e-09 | - |
| repertoire | 0.6994 | 0.4427 | 0.8916666666666666 | 0.78 | 2.71e-09 | 5.42e-09 |

| partner | wins vs raw | losses | ties | median dJ vs raw | geometric-mean J ratio vs raw |
|---|---|---|---|---|---|
| cotrained | 54 | 0 | 10 | -0.0233 | 0.8445 |
| frozen_gen | 14 | 0 | 50 | +0.0000 | 0.8816 |
| memetic | 32 | 0 | 32 | -0.0002 | 0.9364 |
| random_guard | 19 | 0 | 45 | +0.0000 | 0.8887 |
| repertoire | 16 | 0 | 48 | +0.0000 | 0.9363 |

Guard: the co-trained bridge's guard scores its alpha candidates at **f1**; equal guard for the other partners: **True**.

**G0' decision (demo: exploratory, not the pre-registered test):** co-trained vs memetic p = 4.21e-09, vs repertoire p = 5.42e-09 -> PASS.

**Learned-transport check:** co-trained vs the random-direction control (the same guard along a random displacement of matched length) p = 2.32e-09 (Holm-adjusted -). The bridge's direction beats a random one.

## Failures (by name, counted as +inf in statistics)

none

## Exact commands

```bash
python scripts/run_e0.py --suite ibm --designs ibm04,ibm06 --runs runs/seed_trackA_dp --bridge checkpoints/algR_trackA_round1/best.pt --frozen checkpoints/pretrain_small/pretrain_small.pt --final dreamplace --seeds 2 --K 20 --out runs/e0_demo/eq_ibm04 --campaign E0_demo_eq --guard-fidelity f1 --equal-guard True --random-control True
```

## Notes

raw rows: runs/e0_demo_eq/e0_rows.jsonl. Wins / losses count paired cases where the partner's final J is below / above the raw layout's; the geometric-mean ratio < 1 means lower J on average in log terms.
