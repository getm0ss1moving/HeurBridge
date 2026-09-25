# E3-lite macro-stage calibration, f0 proxy vs f1 (development, Track A)

| Field | Value |
|---|---|
| Report | E3_calibration_dev_ibm |
| Date | 2026-09-26 02:33 |
| Node | local (macOS, CPU) |
| Track | A-dev (HB-GP stand-in f1) |
| Tool versions | HeurBridge f0 surrogate J0 (clustered design, bridge-guard scorer); f1 from the stored campaign records |
| HeurBridge version / git | 0.9.1 / 12b29e1862473f9c3fc7a60e55805f4d563ba06e+dirty |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v1_2026-09-25 |
| Feeds gate | G0 (T6.2) for (M, f0) — development evidence only (f1 stands in for signoff) |
| Pre-registered test | - |
| alpha-ledger entry | - |
| Status of the claim | no claim (development / descriptive run) |

## Sample sizes

384 rows over 3 design(s) (ibm01, ibm02, ibm03)

## Results

| design | n | Spearman | Kendall | top-5 recall | regret | random regret |
|---|---|---|---|---|---|---|
| ibm01 | 128 | 0.815 | 0.654 | 0.00 | 0.0294 | 0.0490 |
| ibm02 | 128 | 0.723 | 0.504 | 0.00 | 0.0131 | 0.0496 |
| ibm03 | 128 | 0.060 | 0.034 | 0.00 | 0.0709 | 0.1091 |

Mean over designs: Kendall 0.398, Spearman 0.533, top-5 recall 0.00, regret 0.0378 vs random 0.0692.

Gate G0 rule for (stage M, f0 -> f1): **not met** (regret <= 25% of random and Kendall >= 0.5).

## Failures (by name, counted as +inf in statistics)

none

## Exact commands

```bash
python scripts/calibrate_dev.py --suite ibm --designs ibm01,ibm02,ibm03 --runs runs/seed_dev --out reports/E3_calibration_dev_ibm
```

## Notes

Proxy = MacroStageScorer (f0 J0 of the clustered design); per-design statistics from heurbridge/stats/calibration.py. Supersedes reports/env/dev_calibration_f0_vs_hbgp.json, which scored a single layout per design (a harness error) and computed the Track-A cost with the raw RUDY overflow.
