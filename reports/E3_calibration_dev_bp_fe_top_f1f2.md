# E3-lite f1 -> f2 calibration on bp_fe_top (development, Track B)

| Field | Value |
|---|---|
| Report | f1f2_bp_fe_top |
| Date | 2026-09-26 09:35 |
| Node | local (macOS; OpenLane container, 6 vCPU) |
| Track | B-dev (mini-flow f1: placement-stage timing; f2: CTS + repair_timing + DRT + OpenRCX) |
| Tool versions | OpenROAD b16bda7e (efabless/openlane:master-arm64v8) |
| HeurBridge version / git | 0.10.6 / 517dfb46bc458d21df8e10c6fc251524c2d3c97d+dirty |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v1_2026-09-25 |
| Feeds gate | G0 (T6.2) for (M, f1 -> f2) — development evidence; decision 9 (timing gates at f1) |
| Pre-registered test | - |
| alpha-ledger entry | - |
| Status of the claim | no claim (development / descriptive run) |

## Sample sizes

14 layouts with f1 and f2 (f1 top by J before the gates + an even spread over the f1 range); M1 baseline at f2 x 2

## Results

**Baselines (M1):** f1 setup WNS -2.336 ns / TNS -113.5 ns; f2 setup WNS -1.794 ns / TNS -62.0 ns, DRC 0, detailed WL 1618921 um, 264712 vias.

| layout | program | f1 J | f2 J | f1 gates | f2 gates | setup WNS f1 -> f2 (ns) | TNS f1 -> f2 (ns) | DRC |
|---|---|---|---|---|---|---|---|---|
| bp_fe_top.M5.v0.s0 | M5.v0 | 0.8559 | 0.9531 | pass | fail | -2.235 -> -1.887 | -79.5 -> -53.0 | 0 |
| bp_fe_top.ls0.n3 | LS | 0.8600 | 0.9483 | pass | fail | -2.231 -> -1.886 | -80.8 -> -52.1 | 0 |
| bp_fe_top.ls7.n1 | LS | 0.8601 | 0.9689 | pass | fail | -2.180 -> -1.938 | -78.7 -> -55.2 | 0 |
| bp_fe_top.ls5.n1 | LS | 0.8619 | 0.9524 | pass | fail | -2.214 -> -1.874 | -80.7 -> -52.5 | 0 |
| bp_fe_top.ls1.n4 | LS | 0.8628 | 0.9510 | pass | fail | -2.205 -> -1.841 | -78.9 -> -51.0 | 0 |
| bp_fe_top.ls5.n4 | LS | 0.8644 | 0.9529 | pass | fail | -2.211 -> -1.792 | -79.5 -> -51.4 | 0 |
| bp_fe_top.ls0.n0 | LS | 0.8659 | 0.9536 | pass | fail | -2.284 -> -1.869 | -83.5 -> -53.2 | 0 |
| bp_fe_top.M3.v1.s2 | M3.v1 | 0.8673 | 0.9573 | pass | fail | -2.237 -> -1.878 | -77.7 -> -50.5 | 0 |
| bp_fe_top.ls4.n4 | LS | 0.8684 | 0.9680 | pass | fail | -2.205 -> -1.881 | -80.2 -> -53.8 | 0 |
| bp_fe_top.M3.v2.s2 | M3.v2 | 0.8790 | 0.9445 | pass | fail | -2.316 -> -1.700 | -86.1 -> -50.3 | 0 |
| bp_fe_top.M4.v2.s0 | M4.v2 | 0.8939 | 0.9592 | fail | pass | -2.363 -> -1.803 | -90.5 -> -52.0 | 0 |
| bp_fe_top.M3.v0.s0 | M3.v0 | 0.9278 | 0.9892 | pass | pass | -2.332 -> -1.672 | -103.2 -> -58.7 | 0 |
| bp_fe_top.M7.v0.s0 | M7.v0 | 0.9827 | 1.0427 | fail | fail | -2.420 -> -2.033 | -117.1 -> -65.0 | 0 |
| bp_fe_top.M6.v2.s0 | M6.v2 | 1.9578 | 1.0263 | pass | pass | -2.282 -> -1.673 | -481.6 -> -56.6 | 0 |

**Rank agreement of J before the gates (f1 vs f2, 14 layouts):** Spearman 0.600, Kendall 0.495, top-5 recall 0.600.
**Gate agreement (setup/hold at f1 vs setup/hold/DRC at f2):** pass->pass 2, pass->fail 10, fail->pass 1, fail->fail 1.

## Failures (by name, counted as +inf in statistics)

none

## Exact commands

```bash
python scripts/run_f2_miniflow.py --design nangate45/bp_fe_top --top 8 --spread 6 --base-runs 2
python scripts/calibrate_f1_f2.py --design bp_fe_top
```

## Notes

J before the gates is normalized per fidelity by that fidelity's M1 baseline (f1: 4 terms, M1 = 0.95; f2: 5 terms, M1 = 1.00). f2 gates: setup/hold WNS within 0.02 ns of M1 at f2 and DRC = 0 (frozen rule B.3).
