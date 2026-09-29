# Track-B seeding (T2.7) on bp_fe_top — ORFS flow, f1 = 5_1_grt, f2 = 6_report (orfs)

| Field | Value |
|---|---|
| Report | trackB_orfs_bp_fe_top |
| Date | 2026-09-29 16:05 |
| Node | thinklab-105-224 |
| Track | B (ORFS 2024-12-13 8ae3ae36); 8 threads |
| Tool versions | native OpenROAD 676f8451bb-src; flow Yosys: Yosys 0.48 (/data/dzy/heura_repr/tools/yosys_048/bin/yosys) |
| HeurBridge version / git | 0.14.0 / 5a70d06799f63858e13bfd99ab7c91c5c73a2ee8 (5a70d06-20260929142457) |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v3_2026-09-29 |
| Feeds gate | T2 exit (archive A0, Track B; f2 verification in the f2 campaign) — descriptive |
| Pre-registered test | - |
| alpha-ledger entry | - |
| Status of the claim | no claim (development / descriptive run) |

## Sample sizes

80 program evaluations (16 programs x seeds), 45 local-search evaluations, baseline x 2

## Results

**Baseline (M1, rtl_macro_placer), 2 runs, deterministic: True** — GR WL 2648184 um, GR overflow 0.0, setup WNS -0.005 ns, TNS -0.0 ns, hold WNS 0.010 ns, power 0.160 W (J = 0.95 by construction).

**Program evaluations:** 80 (56 completed, 24 failed); setup/hold gates passed on 15 of 56 completed (27%; setup failures 41, hold failures 1); layouts with GR overflow > 0: 0.
Below the baseline J 0.95: 12 layouts after the gates (12 distinct), 14 before the gates (14 distinct); completed layouts: 32 distinct of 56 (seed-independent programs repeat their layout).

| program | evals | failed | gates passed | median J before gates | best J before gates | best gated J |
|---|---|---|---|---|---|---|
| M2.v0 | 5 | 1 | 2 | 0.9741 | 0.9161 | 0.9161 |
| M2.v1 | 5 | 3 | 2 | 0.9371 | 0.9284 | 0.9284 |
| M2.v2 | 5 | 3 | 1 | 1.0047 | 0.9998 | 1.0097 |
| M3.v0 | 5 | 3 | 1 | 0.9168 | 0.9055 | 0.9055 |
| M3.v1 | 5 | 0 | 3 | 0.9351 | 0.9140 | 0.9140 |
| M3.v2 | 5 | 0 | 3 | 0.9474 | 0.9103 | 0.9103 |
| M4.v0 | 5 | 0 | 0 | 1.1711 | 1.1711 | - |
| M4.v1 | 5 | 0 | 0 | 1.5195 | 1.5195 | - |
| M4.v2 | 5 | 0 | 0 | 0.9993 | 0.9993 | - |
| M5.v0 | 5 | 0 | 0 | 1.0680 | 1.0680 | - |
| M5.v1 | 5 | 0 | 0 | 1.1199 | 1.1199 | - |
| M6.v0 | 5 | 0 | 0 | 0.9935 | 0.9935 | - |
| M6.v1 | 5 | 5 | 0 | - | - | - |
| M6.v2 | 5 | 5 | 0 | - | - | - |
| M7.v0 | 5 | 3 | 1 | 0.9651 | 0.9634 | 0.9634 |
| M7.v1 | 5 | 1 | 2 | 0.9510 | 0.9302 | 0.9302 |

**Same-path control and noise band** (M1's layout imported like every candidate -- standard cells not pre-placed by Hier-RTLMP -- and the same layout shifted as a whole by one site or row; J before the gates, the baseline is 0.95 at f1 and 1.00 at f2 by construction): f1: replay J 0.9591; shifted by one site/row: 0.9692, 0.9502, 0.9461; band over base and replays 0.9461-0.9692 (width 0.0231); f2: replay J 1.3232; shifted by one site/row: 1.4049, 1.1350, 1.0330; band over base and replays 1.0000-1.4049 (width 0.4049). Candidate deltas are paired with the replay; differences inside the band are not distinguishable from the flow's sensitivity to its starting point.

**Local search** (T2.7, 45 evaluations): best J among layouts passing the timing gates, after each step: 0.8992, 0.8992, 0.8992, 0.8942, 0.8942, 0.8942, 0.8942.

**Signoff (f2, 6_report; every gate enforced):** 20 layouts (the top 10 of f1 and 10 more across its ranking): 20 completed, 0 failed; all gates pass on 16 (failing gates: setup 3, hold 2); J before the gates median 0.9256, best 0.8809; best admitted J 0.8809. Rank agreement of f1 and f2 (Kendall tau of J before the gates) 0.5053 over 20 layouts. Admitted layouts below the f2 band's lower edge (1.0000): 14; below the same-path replay (1.3232): 16.

| admitted at f2 | program | seed | f1 J | f2 J |
|---|---|---|---|---|
| bp_fe_top.ls0.n4.f2 | LS | None | 0.9001 | 0.8809 |
| bp_fe_top.ls7.n2.f2 | LS | None | 0.9017 | 0.8903 |
| bp_fe_top.ls1.n1.f2 | LS | None | 0.9065 | 0.8920 |
| bp_fe_top.ls3.n1.f2 | LS | None | 0.9019 | 0.8937 |
| bp_fe_top.ls6.n1.f2 | LS | None | 0.9010 | 0.9011 |
| bp_fe_top.ls5.n2.f2 | LS | None | 0.9013 | 0.9085 |
| bp_fe_top.ls7.n3.f2 | LS | None | 0.9161 | 0.9089 |
| bp_fe_top.ls5.n3.f2 | LS | None | 0.8983 | 0.9133 |

**Candidate noise bands** (f2, J before the gates; the same one-site shifts as the tool's own layout). A candidate counts as better than the tool only if its whole band is below the tool's same-path band:

| candidate | J (as run) | J after one-site / one-row shifts | band | all 4 below the tool's same-path band (min 1.0330) |
|---|---|---|---|---|
| bp_fe_top.ls0.n4.f2 | 0.8809 | 0.8945, 0.9060, 0.8939 | 0.8809-0.9060 | yes |
| bp_fe_top.ls7.n2.f2 | 0.8903 | 0.8971, 0.8741, 0.9344 | 0.8741-0.9344 | yes |
| bp_fe_top.ls1.n1.f2 | 0.8920 | 0.9200, 0.8788, 0.9487 | 0.8788-0.9487 | yes |

**Archive top-k (f2-admitted):** LS J=0.8809 (f2); LS J=0.8903 (f2); LS J=0.8920 (f2); LS J=0.8937 (f2); LS J=0.8971 (f2).

## Failures (by name, counted as +inf in statistics)

- GRT-0116 Global routing finished with congestion: 8
- timeout in 5_1_grt: 7
- GPL-0307 RePlAce divergence detected: 7
- DPL-0036 Detailed placement failed: 2
- GPL-0305 RePlAce diverged at newStepLength: 1

## Exact commands

```bash
python scripts/run_seed_orfs.py --flow /data/dzy/heura_repr/third_party/ORFS-2024-12/flow --design nangate45/bp_fe_top --seeds 5 --top 10 --spread 10 --ls 8 --base-runs 2 --timeout 7200 --base-timeout 28800 --noise-replays 3 --phase band --yosys /data/dzy/heura_repr/tools/yosys_048/bin/yosys
python scripts/report_trackb_dev.py --design bp_fe_top --runs runs/remote/seedB_band_bp_fe_top/runs/seed_orfs --archive runs/remote/seedB_band_bp_fe_top/archive_B0_orfs_bp_fe_top --label orfs
```

## Notes

J before the gates ranks every completed layout. Every row is re-scored from its record under cost_v3_2026-09-29 (the campaign resumed rows written under the earlier rule): at f1 only a failed flow is enforced and 'timing gates passed' counts rows whose setup and hold WNS are within 0.02 ns of the reference (frozen rule B.3); at f2 every gate is enforced (J = +inf on a failed gate). The timing reference is the tool's own macro layout run through the candidates' path, median over the replay and its one-site shifts (user decision 2026-09-29): setup WNS -0.011 / hold WNS 0.015 ns at f1, -0.123 / -0.030 ns at f2; J stays normalized to the unmodified flow.
