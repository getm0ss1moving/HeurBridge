# Track-B seeding (T2.7) on ariane136 — ORFS flow, f1 = 5_1_grt, f2 = 6_report (orfs)

| Field | Value |
|---|---|
| Report | trackB_orfs_ariane136 |
| Date | 2026-10-01 19:13 |
| Node | thinklab-105-224 |
| Track | B (ORFS 2024-12-13 8ae3ae36); 8 threads |
| Tool versions | native OpenROAD 676f8451bb-src; the flow's Yosys: /data/dzy/heura_repr/tools/yosys_048/bin/yosys (the Yosys version in the run's metadata is the one on PATH, not used) |
| HeurBridge version / git | 0.14.0 / 9546dd4fc235383fe0df65b82f7db08ec8337ffe (9546dd4-20260928135525) |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v3_2026-09-29 |
| Feeds gate | T2 exit (archive A0, Track B; f2 verification in the f2 campaign) — descriptive |
| Pre-registered test | - |
| alpha-ledger entry | - |
| Status of the claim | no claim (development / descriptive run) |

## Sample sizes

80 program evaluations (16 programs x seeds), 48 local-search evaluations, baseline x 2

## Results

**Baseline (M1, rtl_macro_placer), 2 runs, deterministic: True** — GR WL 9432517 um, GR overflow 0.0, setup WNS 1.127 ns, TNS 0.0 ns, hold WNS 0.020 ns, power 0.260 W (J = 0.95 by construction).

**Program evaluations:** 80 (40 completed, 40 failed); setup/hold gates passed on 5 of 40 completed (12%; setup failures 25, hold failures 30); layouts with GR overflow > 0: 0.
Below the baseline J 0.95: 0 layouts after the gates (0 distinct), 15 before the gates (3 distinct); completed layouts: 7 distinct of 40 (seed-independent programs repeat their layout).

| program | evals | failed | gates passed | median J before gates | best J before gates | best gated J |
|---|---|---|---|---|---|---|
| M2.v0 | 5 | 0 | 0 | 0.9719 | 0.9719 | - |
| M2.v1 | 5 | 0 | 0 | 0.9719 | 0.9719 | - |
| M2.v2 | 5 | 0 | 0 | 0.9646 | 0.9646 | - |
| M3.v0 | 5 | 5 | 0 | - | - | - |
| M3.v1 | 5 | 5 | 0 | - | - | - |
| M3.v2 | 5 | 5 | 0 | - | - | - |
| M4.v0 | 5 | 0 | 5 | 0.9604 | 0.9604 | 0.9604 |
| M4.v1 | 5 | 5 | 0 | - | - | - |
| M4.v2 | 5 | 0 | 0 | 0.9752 | 0.9752 | - |
| M5.v0 | 5 | 5 | 0 | - | - | - |
| M5.v1 | 5 | 5 | 0 | - | - | - |
| M6.v0 | 5 | 0 | 0 | 0.9346 | 0.9346 | - |
| M6.v1 | 5 | 0 | 0 | 0.9310 | 0.9310 | - |
| M6.v2 | 5 | 0 | 0 | 0.9333 | 0.9333 | - |
| M7.v0 | 5 | 5 | 0 | - | - | - |
| M7.v1 | 5 | 5 | 0 | - | - | - |

**Same-path control and noise band** (M1's layout imported like every candidate -- standard cells not pre-placed by Hier-RTLMP -- and the same layout shifted as a whole by one site or row; J before the gates, the baseline is 0.95 at f1 and 1.00 at f2 by construction): f1: replay J 0.9576; shifted by one site/row: 0.9539, 0.9512, 0.9535; band over base and replays 0.9500-0.9576 (width 0.0076); f2: replay J 1.0089; shifted by one site/row: 1.0046, 1.0011, 1.0041; band over base and replays 1.0000-1.0089 (width 0.0089). Candidate deltas are paired with the replay; differences inside the band are not distinguishable from the flow's sensitivity to its starting point.

**Local search** (T2.7, 48 evaluations): best J among layouts passing the timing gates, after each step: 0.9321, 0.9321, 0.9308, 0.9308, 0.9308, 0.9308, 0.9308, 0.9308.

**Signoff (f2, 6_report; every gate enforced):** 20 layouts (the top 10 of f1 and 10 more across its ranking): 20 completed, 0 failed; all gates pass on 10 (failing gates: hold 8, setup 3); J before the gates median 0.9761, best 0.9757; best admitted J 0.9757. Rank agreement of f1 and f2 (Kendall tau of J before the gates) 0.9368 over 20 layouts. Admitted layouts below the f2 band's lower edge (1.0000): 10; below the same-path replay (1.0089): 10.

| admitted at f2 | program | seed | f1 J | f2 J |
|---|---|---|---|---|
| ariane136.ls7.n3.f2 | LS | None | 0.9306 | 0.9757 |
| ariane136.ls6.n4.f2 | LS | None | 0.9304 | 0.9758 |
| ariane136.ls5.n5.f2 | LS | None | 0.9307 | 0.9759 |
| ariane136.ls6.n1.f2 | LS | None | 0.9306 | 0.9759 |
| ariane136.ls5.n2.f2 | LS | None | 0.9308 | 0.9760 |
| ariane136.ls5.n1.f2 | LS | None | 0.9308 | 0.9760 |
| ariane136.ls2.n5.f2 | LS | None | 0.9308 | 0.9762 |
| ariane136.ls5.n0.f2 | LS | None | 0.9312 | 0.9765 |

**Archive top-k (f2-admitted):** LS J=0.9757 (f2); LS J=0.9757 (f2); LS J=0.9757 (f2); LS J=0.9758 (f2); LS J=0.9759 (f2).

## Failures (by name, counted as +inf in statistics)

- timeout in 3_5_place_dp: 18
- DPL-0036 Detailed placement failed: 17
- GPL-0307 RePlAce divergence detected: 5

## Exact commands

```bash
python scripts/run_seed_orfs.py --flow /data/dzy/heura_repr/third_party/ORFS-2024-12/flow --design nangate45/ariane136 --seeds 5 --top 10 --spread 10 --ls 8 --base-runs 2 --timeout 7200 --base-timeout 28800 --noise-replays 3 --phase all --yosys /data/dzy/heura_repr/tools/yosys_048/bin/yosys
python scripts/report_trackb_dev.py --design ariane136 --runs runs/remote/seedB_orfs7_ariane136/runs/seed_orfs --archive runs/remote/seedB_orfs7_ariane136/archive_B0_orfs_ariane136 --label orfs
```

## Notes

J before the gates ranks every completed layout. Every row is re-scored from its record under cost_v3_2026-09-29 (the campaign resumed rows written under the earlier rule): at f1 only a failed flow is enforced and 'timing gates passed' counts rows whose setup and hold WNS are within 0.02 ns of the reference (frozen rule B.3); at f2 every gate is enforced (J = +inf on a failed gate). The timing reference is the tool's own macro layout run through the candidates' path, median over the replay and its one-site shifts (user decision 2026-09-29): setup WNS 1.174 / hold WNS 0.080 ns at f1, 1.052 / 0.015 ns at f2; J stays normalized to the unmodified flow.
