# E0 partner-type ablation

| Field | Value |
|---|---|
| Report | E0_1_spec |
| Date | 2026-09-30 23:20 |
| Node | 225 (RTX 3090): adaptec1-4, bigblue1, bigblue4; 231 (RTX 4090, GPU 4): bigblue3; each design whole on one server |
| Track | A (final cost = DREAMPlace f1 vs the M1 baseline); protocol of the task list: only the co-trained bridge is guarded (f1) |
| Tool versions | HeurBridge 0.14.0 |
| HeurBridge version / git | 0.14.0 / 3ea4e7fe8dd8d35c56367c913f9b735e5372a673+dirty |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v3_2026-09-29 |
| Feeds gate | G0' (co-trained beats memetic AND repertoire at p < 0.01 on the held-out family) |
| Pre-registered test | paired one-sided Wilcoxon, co-trained < each partner, Holm over the comparisons |
| alpha-ledger entry | E0#1 |
| Status of the claim | gate PASSED: the pre-registered claim may be stated |

## Sample sizes

405 paired cases (design x program x seed); designs adaptec1,adaptec2,adaptec3,adaptec4,bigblue1,bigblue3,bigblue4

## Results

> **Caveat.** Pre-registered primary test E0#1, the G0' test (bridge sha256 f95bdde8...). Final cost = DREAMPlace f1 with the macros fixed: Track A has no f2 (bookshelf, no timing), as registered. J = 0.45 is DREAMPlace's own mixed-size macro placement (M1) by construction; on these designs every partner's mean J, and every bridge-refined layout, is above it. The gate record's note that the protocol 'is pre-registered only after the user's decision' is a stale string in scripts/run_e0.py, not a statement about this run: the protocol was registered on 2026-09-28 16:06 before any confirmatory data (reports/E0_preregistration.md). Deviations, none changing the registered protocol (reports/PROGRESS.md s.7): bigblue4 has 30 legal sources of 80 and uses the memory-lean RUDY (HB_RUDY_IMPL=bmm, equal to the reference to ~1e-6); this protocol's bigblue3 slice 2 was OOM-killed and re-run from its 11 finished rows as two sub-slices; bigblue4's slices ran two code versions (9b3c8e8 and 5e1c009, CHANGELOG 30 Sep).
>
> **Correction (3 Oct 2026):** on ISPD2005 the tool's runs could not move the macros (they were written to DREAMPlace as fixed terminals), so M1 and J = 0.45 here are the benchmark's own macro placement after P_M, not DREAMPlace's (bigblue3's movable macros excepted). See reports/defect_ispd_tool_runs.md. The comparisons among HeurBridge's partners (G0') do not involve the tool and are unaffected.

| partner | mean J | portfolio J | Kendall tau vs raw | co-trained better: frac | one-sided p | Holm p_adj |
|---|---|---|---|---|---|---|
| cotrained | 0.5579 | 0.5044 | 0.7897340754483612 | - | - | - |
| frozen_gen | 0.5874 | 0.5143 | 0.6566163994735422 | 0.73 | 2.09e-16 | 2.09e-16 |
| memetic | 0.5843 | 0.5166 | 0.9577982692583253 | 0.93 | 8.21e-66 | 3.29e-65 |
| none | 0.5863 | 0.5172 | 0.9999999999999999 | 0.90 | 7.12e-62 | 2.14e-61 |
| random_guard | 0.5807 | 0.5152 | 0.9411065125350838 | 0.87 | 1.29e-59 | - |
| repertoire | 0.6137 | 0.5127 | 0.8747443033157317 | 0.94 | 1.2e-61 | 2.41e-61 |

| partner | wins vs raw | losses | ties | median dJ vs raw | geometric-mean J ratio vs raw |
|---|---|---|---|---|---|
| cotrained | 365 | 0 | 40 | -0.0211 | 0.9538 |
| frozen_gen | 172 | 204 | 29 | +0.0010 | 0.9924 |
| memetic | 166 | 145 | 94 | +0.0000 | 0.9976 |
| random_guard | 227 | 0 | 178 | -0.0011 | 0.9919 |
| repertoire | 193 | 205 | 7 | +0.0000 | 1.0141 |

Guard: the co-trained bridge's guard scores its alpha candidates at **f1**; equal guard for the other partners: **False**.

**G0' decision (pre-registered):** co-trained vs memetic p = 3.29e-65, vs repertoire p = 2.41e-61 -> PASS.

**Learned-transport check:** co-trained vs the random-direction control (the same guard along a random displacement of matched length) p = 1.29e-59 (Holm-adjusted -). The bridge's direction beats a random one.

## Failures (by name, counted as +inf in statistics)

none

## Exact commands

```bash
python scripts/run_e0.py --suite ispd2005 --designs adaptec1,adaptec2,adaptec3,adaptec4,bigblue1,bigblue3,bigblue4 --runs runs/seed_trackA_ispd --bridge checkpoints/algR_trackA_final/best.pt --frozen checkpoints/pretrain_small/pretrain_small.pt --final dreamplace --seeds 5 --K 20 --out runs/e0/spec_adaptec1 --campaign E0 --guard-fidelity f1 --equal-guard False --component E0 --random-control True --budget-s 0.0 --prepare-only False --bridge-sha256-16 f95bdde848531634 --budget-used {'adaptec1': {'budget_s': 221.76253056526184, 'scale': 0.07808305642372909, 'from': 'measured'}}
```

## Notes

raw rows: runs/e0_full/E0_1_spec/e0_rows.jsonl. Wins / losses count paired cases where the partner's final J is below / above the raw layout's; the geometric-mean ratio < 1 means lower J on average in log terms.
