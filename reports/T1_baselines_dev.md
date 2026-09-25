# T1 baselines (development, Track-A stand-in)

| Field | Value |
|---|---|
| Report | T1_baselines_dev |
| Date | 2026-09-25 15:09 |
| Node | local (macOS, CPU) |
| Track | A-dev: benchmark macro positions -> P_M -> HB-GP (3 GP seeds) |
| Tool versions | HB-GP (heurbridge.eval.gp), not DREAMPlace |
| HeurBridge version / git | 0.9.0 / 66a126d452c2a692fc6d247abded8bc58f449aab+dirty |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v1_2026-09-25 |
| Feeds gate | T1 exit (baseline table, f1 runtime per design) |
| Pre-registered test | - |
| alpha-ledger entry | - |
| Status of the claim | no claim (development / descriptive run) |

## Sample sizes

3 GP seeds per design

## Results

| design | objects | movable macros | HPWL (median of 3) | RUDY OF % | GP overflow | legalization failures | f1 runtime s (median) |
|---|---|---|---|---|---|---|---|
| ibm01 | 12752 | 246 | 2.676e+06 | 0.0000 | 0.069 | [29, 28, 24] | 1.98 |
| ibm02 | 19601 | 271 | 5.986e+06 | 0.0000 | 0.069 | [19, 11, 13] | 3.39 |
| ibm03 | 23136 | 290 | 8.099e+06 | 0.0023 | 0.070 | [59, 60, 61] | 3.88 |

## Failures (by name, counted as +inf in statistics)

none

## Exact commands

```bash
python scripts/run_seed_archive.py --suite ibm --designs ibm01,ibm02,ibm03 --evaluator hbgp --out runs/seed_dev --archive archive_dev --min-fidelity 1
```

## Notes


