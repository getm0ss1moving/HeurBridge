# E0 partner-type ablation

| Field | Value |
|---|---|
| Report | E0_3_ibm |
| Date | 2026-09-30 23:20 |
| Node | 225 (RTX 3090) |
| Track | A (final cost = DREAMPlace f1 vs the M1 baseline); protocol of the task list: only the co-trained bridge is guarded (f1) |
| Tool versions | HeurBridge 0.14.0 |
| HeurBridge version / git | 0.14.0 / 3ea4e7fe8dd8d35c56367c913f9b735e5372a673+dirty |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v3_2026-09-29 |
| Feeds gate | G0' (co-trained beats memetic AND repertoire at p < 0.01 on the held-out family) |
| Pre-registered test | paired one-sided Wilcoxon, co-trained < each partner, Holm over the comparisons |
| alpha-ledger entry | E0#3 |
| Status of the claim | gate PASSED: the pre-registered claim may be stated |

## Sample sizes

145 paired cases (design x program x seed); designs ibm08,ibm12

## Results

> **Caveat.** Pre-registered secondary test E0#3: the training family's held-out designs ibm08 and ibm12 (neither in the bridge's training nor validation set). It qualifies the G0' decision, it does not change it. Final cost = DREAMPlace f1 with the macros fixed: Track A has no f2 (bookshelf, no timing), as registered. J = 0.45 is DREAMPlace's own mixed-size macro placement (M1) by construction; on these designs every partner's mean J, and every bridge-refined layout, is above it. The gate record's note that the protocol 'is pre-registered only after the user's decision' is a stale string in scripts/run_e0.py, not a statement about this run: the protocol was registered on 2026-09-28 16:06 before any confirmatory data (reports/E0_preregistration.md).

| partner | mean J | portfolio J | Kendall tau vs raw | co-trained better: frac | one-sided p | Holm p_adj |
|---|---|---|---|---|---|---|
| cotrained | 0.6004 | 0.5067 | 0.8275641025641025 | - | - | - |
| frozen_gen | 1.0578 | 0.5295 | 0.26538461538461533 | 0.82 | 1.87e-19 | 5.61e-19 |
| memetic | 0.6395 | 0.5088 | 0.9749999999999999 | 0.73 | 2.16e-17 | 4.32e-17 |
| none | 0.6375 | 0.5067 | 0.9999999999999999 | 0.46 | 8.02e-13 | 8.02e-13 |
| random_guard | 0.6302 | 0.5045 | 0.9749999999999999 | 0.43 | 2.52e-10 | - |
| repertoire | 0.7098 | 0.5127 | 0.8384615384615384 | 0.88 | 4.05e-22 | 1.62e-21 |

| partner | wins vs raw | losses | ties | median dJ vs raw | geometric-mean J ratio vs raw |
|---|---|---|---|---|---|
| cotrained | 66 | 0 | 79 | +0.0000 | 0.9505 |
| frozen_gen | 25 | 102 | 18 | +0.0525 | 1.2455 |
| memetic | 44 | 62 | 39 | +0.0000 | 1.0029 |
| random_guard | 54 | 0 | 91 | +0.0000 | 0.9905 |
| repertoire | 32 | 109 | 4 | +0.0042 | 1.0368 |

Guard: the co-trained bridge's guard scores its alpha candidates at **f1**; equal guard for the other partners: **False**.

**G0' decision (pre-registered):** co-trained vs memetic p = 4.32e-17, vs repertoire p = 1.62e-21 -> PASS.

**Learned-transport check:** co-trained vs the random-direction control (the same guard along a random displacement of matched length) p = 2.52e-10 (Holm-adjusted -). The bridge's direction beats a random one.

## Failures (by name, counted as +inf in statistics)

none

## Exact commands

```bash
python scripts/run_e0.py --suite ibm --designs ibm08,ibm12 --runs runs/seed_trackA_dp --bridge checkpoints/algR_trackA_final/best.pt --frozen checkpoints/pretrain_small/pretrain_small.pt --final dreamplace --seeds 5 --K 20 --out runs/e0/spec_ibm08 --campaign E0 --guard-fidelity f1 --equal-guard False --component E0 --random-control True --budget-s 0.0 --prepare-only False --bridge-sha256-16 f95bdde848531634 --budget-used {'ibm08': {'budget_s': 19.12632465362549, 'scale': 0.09882741545393965, 'from': 'measured'}}
```

## Notes

raw rows: runs/e0_full/E0_3_ibm/e0_rows.jsonl. Wins / losses count paired cases where the partner's final J is below / above the raw layout's; the geometric-mean ratio < 1 means lower J on average in log terms.
