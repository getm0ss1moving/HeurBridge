# Track-B development seeding (T2.7) on bp_fe_top — local mini-flow f1

| Field | Value |
|---|---|
| Report | trackB_dev_bp_fe_top |
| Date | 2026-09-26 07:06 |
| Node | local (macOS; OpenLane container, 6 vCPU) |
| Track | B-dev (ORFS-aligned mini-flow, OpenROAD b16bda7e; f1 timing from placement parasitics) |
| Tool versions | OpenROAD b16bda7e, Yosys 0.38 (efabless/openlane:master-arm64v8) |
| HeurBridge version / git | 0.10.4 / 7ff1a37da0efe1c8f5967cb5775ea0f467d0570a+dirty |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v1_2026-09-25 |
| Feeds gate | T2 exit (archive A0) — development only; the pre-registered A0 is built at f2 on the server |
| Pre-registered test | - |
| alpha-ledger entry | - |
| Status of the claim | no claim (development / descriptive run) |

## Sample sizes

80 program evaluations (16 programs x seeds), 45 local-search evaluations, baseline x 3

## Results

**Baseline (M1, rtl_macro_placer), 3 runs, deterministic: True** — GR WL 1832439 um, GR overflow 0.0, setup WNS -2.336 ns, TNS -113.5 ns, hold WNS 0.096 ns, power 0.151 W (J = 0.95 by construction).

**Program evaluations:** 80 (80 completed, 0 failed); setup/hold gates passed on 50 of 80 completed (62%; setup failures 30, hold failures 0); layouts with GR overflow > 0: 0.
Below the baseline J 0.95: 27 layouts after the gates (15 distinct), 38 before the gates (22 distinct); completed layouts: 48 distinct of 80 (seed-independent programs repeat their layout).

| program | evals | failed | gates passed | median J before gates | best J before gates | best gated J |
|---|---|---|---|---|---|---|
| M2.v0 | 5 | 0 | 4 | 0.9716 | 0.9073 | 0.9073 |
| M2.v1 | 5 | 0 | 2 | 0.9129 | 0.8696 | 0.9574 |
| M2.v2 | 5 | 0 | 1 | 1.1225 | 0.9945 | 1.0103 |
| M3.v0 | 5 | 0 | 1 | 0.9449 | 0.9110 | 0.9278 |
| M3.v1 | 5 | 0 | 4 | 0.8927 | 0.8673 | 0.8673 |
| M3.v2 | 5 | 0 | 5 | 0.8981 | 0.8790 | 0.8790 |
| M4.v0 | 5 | 0 | 5 | 0.8737 | 0.8737 | 0.8737 |
| M4.v1 | 5 | 0 | 5 | 1.0181 | 1.0181 | 1.0181 |
| M4.v2 | 5 | 0 | 0 | 0.8939 | 0.8939 | - |
| M5.v0 | 5 | 0 | 5 | 0.8559 | 0.8559 | 0.8559 |
| M5.v1 | 5 | 0 | 5 | 0.8745 | 0.8745 | 0.8745 |
| M6.v0 | 5 | 0 | 5 | 1.0256 | 1.0256 | 1.0256 |
| M6.v1 | 5 | 0 | 0 | 1.0580 | 1.0580 | - |
| M6.v2 | 5 | 0 | 5 | 1.9578 | 1.9578 | 1.9578 |
| M7.v0 | 5 | 0 | 0 | 0.9827 | 0.9051 | - |
| M7.v1 | 5 | 0 | 3 | 1.1244 | 0.9237 | 0.9237 |

**Local search** (T2.7, 45 evaluations): best gated J after each step: 0.8600, 0.8600, 0.8600, 0.8600, 0.8600, 0.8559, 0.8559.

**Archive top-k (fidelity 1, development):** M5.v0 J=0.8559 (f1); M3.v1 J=0.8673 (f1); M4.v0 J=0.8737 (f1); M5.v1 J=0.8745 (f1); M3.v2 J=0.8790 (f1).

## Failures (by name, counted as +inf in statistics)

none

## Exact commands

```bash
python scripts/run_seed_miniflow.py --design nangate45/bp_fe_top --seeds 5 --top 10 --ls 8
python scripts/report_trackb_dev.py --design bp_fe_top
```

## Notes

J before the gates ranks every completed layout; the gated J is +inf when the setup or hold WNS is worse than the baseline by more than 0.02 ns (frozen rule B.3). Superseded rows of earlier flow versions are kept under runs/seed_miniflow/bp_fe_top/superseded_*.
