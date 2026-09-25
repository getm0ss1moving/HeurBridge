# E3-lite macro-stage calibration, f0 proxy vs f1 (development, Track B)

| Field | Value |
|---|---|
| Report | E3_calibration_dev_bp_fe_top |
| Date | 2026-09-26 07:07 |
| Node | local (macOS, CPU) |
| Track | B-dev (local mini-flow f1, OpenLane OpenROAD b16bda7e) |
| Tool versions | HeurBridge f0 surrogate J0 (clustered design, bridge-guard scorer); f1 from the stored campaign records |
| HeurBridge version / git | 0.10.4 / 7ff1a37da0efe1c8f5967cb5775ea0f467d0570a+dirty |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v1_2026-09-25 |
| Feeds gate | G0 (T6.2) for (M, f0) — development evidence only (f1 stands in for signoff) |
| Pre-registered test | - |
| alpha-ledger entry | - |
| Status of the claim | no claim (development / descriptive run) |

## Sample sizes

87 rows over 1 design(s) (bp_fe_top)

## Results

| design | n | Spearman | Kendall | top-5 recall | regret | random regret |
|---|---|---|---|---|---|---|
| bp_fe_top | 87 | 0.487 | 0.350 | 0.00 | 0.1157 | 0.1072 |

Mean over designs: Kendall 0.350, Spearman 0.487, top-5 recall 0.00, regret 0.1157 vs random 0.1072.

Gate G0 rule for (stage M, f0 -> f1): **not met** (regret <= 25% of random and Kendall >= 0.5).

Track B: J before the gates is ranked above; the setup/hold gate passes on 72% of the rows. On the gated rows only: Kendall 0.387, top-5 recall 0.00.

## Failures (by name, counted as +inf in statistics)

none

## Exact commands

```bash
python scripts/calibrate_dev.py --miniflow nangate45/bp_fe_top --runs runs/seed_miniflow --out reports/E3_calibration_dev_bp_fe_top
```

## Notes

Proxy = MacroStageScorer (f0 J0 of the clustered design); per-design statistics from heurbridge/stats/calibration.py. Supersedes reports/env/dev_calibration_f0_vs_hbgp.json, which scored a single layout per design (a harness error) and computed the Track-A cost with the raw RUDY overflow.
