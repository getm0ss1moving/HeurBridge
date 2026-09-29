# Track-B seeding (T2.7) on bp_be_top — ORFS flow, f1 = 5_1_grt, f2 = 6_report (orfs)

| Field | Value |
|---|---|
| Report | trackB_orfs_bp_be_top |
| Date | 2026-09-29 13:47 |
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

80 program evaluations (16 programs x seeds), 45 local-search evaluations, baseline x 2

## Results

**Baseline (M1, rtl_macro_placer), 2 runs, deterministic: True** — GR WL 3474093 um, GR overflow 0.0, setup WNS -0.208 ns, TNS -18.2 ns, hold WNS 0.010 ns, power 0.139 W (J = 0.95 by construction).

**Program evaluations:** 80 (46 completed, 34 failed); setup/hold gates passed on 9 of 46 completed (20%; setup failures 33, hold failures 24); layouts with GR overflow > 0: 0.
Below the baseline J 0.95: 2 layouts after the gates (2 distinct), 4 before the gates (4 distinct); completed layouts: 30 distinct of 46 (seed-independent programs repeat their layout).

| program | evals | failed | gates passed | median J before gates | best J before gates | best gated J |
|---|---|---|---|---|---|---|
| M2.v0 | 5 | 3 | 1 | 1.0593 | 0.9950 | 0.9950 |
| M2.v1 | 5 | 2 | 1 | 1.0044 | 0.8960 | 1.0044 |
| M2.v2 | 5 | 3 | 0 | 1.3074 | 1.2562 | - |
| M3.v0 | 5 | 1 | 1 | 1.1295 | 0.9764 | 0.9764 |
| M3.v1 | 5 | 0 | 2 | 1.0064 | 0.9255 | 0.9255 |
| M3.v2 | 5 | 0 | 3 | 0.9708 | 0.9281 | 0.9672 |
| M4.v0 | 5 | 5 | 0 | - | - | - |
| M4.v1 | 5 | 0 | 0 | 1.2368 | 1.2368 | - |
| M4.v2 | 5 | 0 | 0 | 1.0420 | 1.0420 | - |
| M5.v0 | 5 | 5 | 0 | - | - | - |
| M5.v1 | 5 | 5 | 0 | - | - | - |
| M6.v0 | 5 | 5 | 0 | - | - | - |
| M6.v1 | 5 | 0 | 0 | 1.2153 | 1.2153 | - |
| M6.v2 | 5 | 0 | 0 | 1.3934 | 1.3934 | - |
| M7.v0 | 5 | 2 | 0 | 1.0316 | 0.9889 | - |
| M7.v1 | 5 | 3 | 1 | 0.9829 | 0.9382 | 0.9382 |

**Same-path control and noise band** (M1's layout imported like every candidate -- standard cells not pre-placed by Hier-RTLMP -- and the same layout shifted as a whole by one site or row; J before the gates, the baseline is 0.95 at f1 and 1.00 at f2 by construction): f1: replay J 1.0242; shifted by one site/row: 1.0623, 0.9782, 1.1261; band over base and replays 0.9500-1.1261 (width 0.1761); f2: replay J 1.1034; shifted by one site/row: 1.1341, 1.0241, 1.1623; band over base and replays 1.0000-1.1623 (width 0.1623). Candidate deltas are paired with the replay; differences inside the band are not distinguishable from the flow's sensitivity to its starting point.

**Local search** (T2.7, 45 evaluations): best J among layouts passing the timing gates, after each step: -, 1.0090, 0.9772, 0.9734, 0.9721, 0.9721, 0.9178.

**Signoff (f2, 6_report; every gate enforced):** 20 layouts (the top 10 of f1 and 10 more across its ranking): 20 completed, 0 failed; all gates pass on 9 (failing gates: hold 11, setup 3); J before the gates median 0.9983, best 0.9306; best admitted J 0.9306. Rank agreement of f1 and f2 (Kendall tau of J before the gates) 0.7789 over 20 layouts. Admitted layouts below the f2 band's lower edge (1.0000): 7; below the same-path replay (1.1034): 9.

| admitted at f2 | program | seed | f1 J | f2 J |
|---|---|---|---|---|
| bp_be_top.ls7.n1.f2 | LS | None | 0.9178 | 0.9306 |
| bp_be_top.M2.v1.s0.f2 | M2.v1 | 0 | 0.8960 | 0.9500 |
| bp_be_top.M3.v1.s3.f2 | M3.v1 | 3 | 0.9255 | 0.9522 |
| bp_be_top.M3.v2.s0.f2 | M3.v2 | 0 | 0.9672 | 0.9659 |
| bp_be_top.ls7.n4.f2 | LS | None | 0.9142 | 0.9681 |
| bp_be_top.M3.v2.s4.f2 | M3.v2 | 4 | 0.9788 | 0.9812 |
| bp_be_top.M3.v2.s1.f2 | M3.v2 | 1 | 0.9708 | 0.9960 |
| bp_be_top.ls6.n3.f2 | LS | None | 0.9672 | 1.0007 |

**Archive top-k (f2-admitted):** LS J=0.9306 (f2); LS J=0.9356 (f2); M2.v1 J=0.9500 (f2); M3.v1 J=0.9522 (f2); M3.v2 J=0.9659 (f2).

## Failures (by name, counted as +inf in statistics)

- GRT-0116 Global routing finished with congestion: 41

## Exact commands

```bash
python scripts/run_seed_orfs.py --flow /data/dzy/heura_repr/third_party/ORFS-2024-12/flow --design nangate45/bp_be_top --seeds 5 --top 10 --spread 10 --ls 8 --base-runs 2 --timeout 7200 --base-timeout 28800 --noise-replays 3 --phase all --yosys /data/dzy/heura_repr/tools/yosys_048/bin/yosys
python scripts/report_trackb_dev.py --design bp_be_top --runs runs/remote/seedB_orfs7_bp_be_top/runs/seed_orfs --archive runs/remote/seedB_orfs7_bp_be_top/archive_B0_orfs_bp_be_top --label orfs
```

## Notes

J before the gates ranks every completed layout. Every row is re-scored from its record under cost_v3_2026-09-29 (the campaign resumed rows written under the earlier rule): at f1 only a failed flow is enforced and 'timing gates passed' counts rows whose setup and hold WNS are within 0.02 ns of the reference (frozen rule B.3); at f2 every gate is enforced (J = +inf on a failed gate). The timing reference is the tool's own macro layout run through the candidates' path, median over the replay and its one-site shifts (user decision 2026-09-29): setup WNS -0.228 / hold WNS 0.060 ns at f1, -0.329 / 0.055 ns at f2; J stays normalized to the unmodified flow.
