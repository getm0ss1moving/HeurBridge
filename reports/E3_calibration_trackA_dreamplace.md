# E3-lite macro-stage calibration, f0 proxy vs f1 (development, Track A)

| Field | Value |
|---|---|
| Report | E3_calibration_trackA_dreamplace |
| Date | 2026-09-27 20:57 |
| Node | local (macOS, CPU) |
| Track | A-dev (HB-GP stand-in f1) |
| Tool versions | HeurBridge f0 surrogate J0 (clustered design, bridge-guard scorer); f1 from the stored campaign records |
| HeurBridge version / git | 0.13.0 / b9f350bed56e04b2eb8b1670ddc99125e455c9ba |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v1_2026-09-25 |
| Feeds gate | G0 (T6.2) for (M, f0) — development evidence only (f1 stands in for signoff) |
| Pre-registered test | - |
| alpha-ledger entry | - |
| Status of the claim | no claim (development / descriptive run) |

## Sample sizes

1420 rows over 17 design(s) (ibm01, ibm02, ibm03, ibm04, ibm06, ibm07, ibm08, ibm09, ibm10, ibm11, ibm12, ibm13, ibm14, ibm15, ibm16, ibm17, ibm18)

## Results

| design | n | Spearman | Kendall | top-5 recall | regret | random regret |
|---|---|---|---|---|---|---|
| ibm01 | 84 | 0.908 | 0.754 | 0.20 | 0.0024 | 0.0476 |
| ibm02 | 84 | 0.827 | 0.645 | 0.00 | 0.0001 | 0.0138 |
| ibm03 | 91 | 0.554 | 0.343 | 0.00 | 0.3924 | 1.4238 |
| ibm04 | 85 | 0.524 | 0.373 | 0.00 | 0.0632 | 0.0450 |
| ibm06 | 88 | -0.269 | -0.126 | 0.00 | 12.2013 | 0.1767 |
| ibm07 | 84 | 0.229 | 0.216 | 0.00 | 0.2990 | 0.0806 |
| ibm08 | 80 | -0.093 | 0.015 | 0.00 | 0.0559 | 0.1167 |
| ibm09 | 81 | -0.011 | 0.043 | 0.00 | 12.5645 | 0.5191 |
| ibm10 | 79 | 0.697 | 0.507 | 0.00 | 0.0011 | 0.0788 |
| ibm11 | 83 | 0.552 | 0.398 | 0.00 | 0.1065 | 0.1588 |
| ibm12 | 80 | 0.885 | 0.714 | 0.00 | 0.0001 | 0.0535 |
| ibm13 | 86 | -0.453 | -0.339 | 0.00 | 0.1186 | 0.0719 |
| ibm14 | 82 | 0.750 | 0.567 | 0.00 | 0.0695 | 0.0719 |
| ibm15 | 86 | 0.504 | 0.321 | 0.00 | 0.0256 | 0.0231 |
| ibm16 | 81 | 0.538 | 0.343 | 0.00 | 0.0179 | 0.0455 |
| ibm17 | 79 | 0.651 | 0.424 | 0.00 | 0.0282 | 0.0355 |
| ibm18 | 87 | 0.751 | 0.538 | 0.00 | 0.0033 | 0.0282 |

Mean over designs: Kendall 0.337, Spearman 0.444, top-5 recall 0.01, regret 1.5264 vs random 0.1759.

Gate G0 rule for (stage M, f0 -> f1): **not met** (regret <= 25% of random and Kendall >= 0.5).

## Failures (by name, counted as +inf in statistics)

- ibm10.M2.v0.s0.f1: program_timeout (rc=-24 )
- ibm10.M2.v0.s1.f1: program_timeout (rc=-24 )
- ibm10.M2.v0.s2.f1: program_timeout (rc=-24 )
- ibm10.M2.v0.s3.f1: program_timeout (rc=-24 )
- ibm10.M2.v0.s4.f1: program_timeout (rc=-24 )
- ibm10.M2.v1.s0.f1: program_timeout (rc=-24 )
- ibm10.M2.v1.s1.f1: program_timeout (rc=-24 )
- ibm10.M2.v1.s2.f1: program_timeout (rc=-24 )
- ibm10.M2.v1.s3.f1: program_timeout (rc=-24 )
- ibm10.M2.v1.s4.f1: program_timeout (rc=-24 )
- ibm10.M2.v2.s0.f1: program_timeout (rc=-24 )
- ibm10.M2.v2.s1.f1: program_timeout (rc=-24 )
- ibm10.M2.v2.s2.f1: program_timeout (rc=-24 )
- ibm10.M2.v2.s3.f1: program_timeout (rc=-24 )
- ibm10.M2.v2.s4.f1: program_timeout (rc=-24 )
- ibm12.M2.v0.s0.f1: program_timeout (rc=-24 )
- ibm12.M2.v0.s1.f1: program_timeout (rc=-24 )
- ibm12.M2.v0.s2.f1: program_timeout (rc=-24 )
- ibm12.M2.v0.s3.f1: program_timeout (rc=-24 )
- ibm12.M2.v0.s4.f1: program_timeout (rc=-24 )
- ibm12.M2.v1.s0.f1: program_timeout (rc=-24 )
- ibm12.M2.v1.s1.f1: program_timeout (rc=-24 )
- ibm12.M2.v1.s2.f1: program_timeout (rc=-24 )
- ibm12.M2.v1.s3.f1: program_timeout (rc=-24 )
- ibm12.M2.v1.s4.f1: program_timeout (rc=-24 )
- ibm12.M2.v2.s0.f1: program_timeout (rc=-24 )
- ibm12.M2.v2.s1.f1: program_timeout (rc=-24 )
- ibm12.M2.v2.s2.f1: program_timeout (rc=-24 )
- ibm12.M2.v2.s3.f1: program_timeout (rc=-24 )
- ibm12.M2.v2.s4.f1: program_timeout (rc=-24 )
- ibm14.M2.v2.s0.f1: program_timeout (rc=-24 )
- ibm14.M2.v2.s1.f1: program_timeout (rc=-24 )
- ibm14.M2.v2.s2.f1: program_timeout (rc=-24 )
- ibm14.M2.v2.s3.f1: program_timeout (rc=-24 )
- ibm14.M2.v2.s4.f1: program_timeout (rc=-24 )
- ibm16.M2.v2.s0.f1: program_timeout (rc=-24 )
- ibm16.M2.v2.s1.f1: program_timeout (rc=-24 )
- ibm16.M2.v2.s2.f1: program_timeout (rc=-24 )
- ibm16.M2.v2.s3.f1: program_timeout (rc=-24 )
- ibm16.M2.v2.s4.f1: program_timeout (rc=-24 )
- ibm17.M2.v0.s0.f1: program_timeout (rc=-24 )
- ibm17.M2.v0.s1.f1: program_timeout (rc=-24 )
- ibm17.M2.v0.s2.f1: program_timeout (rc=-24 )
- ibm17.M2.v0.s3.f1: program_timeout (rc=-24 )
- ibm17.M2.v0.s4.f1: program_timeout (rc=-24 )
- ibm17.M2.v1.s0.f1: program_timeout (rc=-24 )
- ibm17.M2.v1.s1.f1: program_timeout (rc=-24 )
- ibm17.M2.v1.s2.f1: program_timeout (rc=-24 )
- ibm17.M2.v1.s3.f1: program_timeout (rc=-24 )
- ibm17.M2.v1.s4.f1: program_timeout (rc=-24 )
- ibm17.M2.v2.s0.f1: program_timeout (rc=-24 )
- ibm17.M2.v2.s1.f1: program_timeout (rc=-24 )
- ibm17.M2.v2.s2.f1: program_timeout (rc=-24 )
- ibm17.M2.v2.s3.f1: program_timeout (rc=-24 )
- ibm17.M2.v2.s4.f1: program_timeout (rc=-24 )

## Exact commands

```bash
python scripts/calibrate_dev.py --suite ibm --designs ibm01,ibm02,ibm03,ibm04,ibm06,ibm07,ibm08,ibm09,ibm10,ibm11,ibm12,ibm13,ibm14,ibm15,ibm16,ibm17,ibm18 --runs runs/remote/seedA_dp_combined --out reports/E3_calibration_trackA_dreamplace
```

## Notes

Proxy = MacroStageScorer (f0 J0 of the clustered design); per-design statistics from heurbridge/stats/calibration.py. Supersedes reports/env/dev_calibration_f0_vs_hbgp.json, which scored a single layout per design (a harness error) and computed the Track-A cost with the raw RUDY overflow.
