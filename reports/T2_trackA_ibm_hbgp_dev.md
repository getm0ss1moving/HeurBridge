# Track-A seeding campaign (T1.7 / T2.7): ibm_hbgp_dev

| Field | Value |
|---|---|
| Report | trackA_ibm_hbgp_dev |
| Date | 2026-09-27 15:17 |
| Node | 224 (CPU; HB-GP single-threaded, 9 parallel processes) |
| Track | A-dev (HB-GP stand-in) |
| Tool versions | HB-GP (heurbridge.eval.gp, 1 thread) + f0 RUDY/HPWL |
| HeurBridge version / git | 0.10.7 / 805008c+dirty (code archive 805008c-dirty-20260927032907, the tree committed as v0.11.0 b443316) |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v1_2026-09-25 |
| Feeds gate | T2 exit (archive A0, Track A) — descriptive |
| Pre-registered test | - |
| alpha-ledger entry | - |
| Status of the claim | no claim (development / descriptive run) |

## Sample sizes

17 designs; 1360 program evaluations; 809 local-search evaluations; baseline 3 seeds per design

## Results

J is relative to the baseline (J = 0.45 for the baseline by construction; lower is better); a layout 'beats' the baseline when J < 0.45.

| design | M1 s / P_M disp | baseline HPWL (median of 3) | RUDY OF % | f1 s | program evals (failed) | best program J | layouts < baseline (distinct) | LS best J | archive best J |
|---|---|---|---|---|---|---|---|---|---|
| ibm01 | - | 2649306 | 0.0000 | 5.3 | 80 (0) | M2.v0 0.5114 | 0 (0) | 0.5091 | 0.4500 |
| ibm02 | - | 5966056 | 0.0000 | 9.2 | 80 (0) | M6.v1 0.4582 | 0 (0) | 0.4576 | 0.4500 |
| ibm03 | - | 8088808 | 0.0218 | 9.8 | 80 (0) | M6.v0 0.4644 | 0 (0) | 0.4638 | 0.4498 |
| ibm04 | - | 8617169 | 0.0253 | 11.6 | 80 (0) | M6.v1 0.4865 | 0 (0) | 0.4840 | 0.4500 |
| ibm06 | - | 8044006 | 0.2468 | 17.3 | 80 (0) | M6.v0 0.3825 | 54 (29) | 0.3819 | 0.3819 |
| ibm07 | - | 11759426 | 0.4218 | 22.9 | 80 (0) | M3.v2 0.4217 | 20 (8) | 0.4205 | 0.4205 |
| ibm08 | - | 14492745 | 0.3788 | 22.4 | 80 (0) | M3.v2 0.4616 | 0 (0) | 0.4586 | 0.4500 |
| ibm09 | - | 20183974 | 15.9446 | 25.2 | 80 (0) | M3.v2 0.2518 | 77 (32) | 0.2511 | 0.2511 |
| ibm10 | - | 40611568 | 14.9675 | 35.0 | 80 (15) | M6.v1 0.4920 | 0 (0) | 0.4914 | 0.4501 |
| ibm11 | - | 21532874 | 3.4082 | 27.7 | 80 (0) | M3.v2 0.4911 | 0 (0) | 0.4890 | 0.4500 |
| ibm12 | - | 47906768 | 18.9247 | 41.1 | 80 (15) | M6.v1 0.3889 | 26 (10) | 0.3889 | 0.3889 |
| ibm13 | - | 39035288 | 20.9801 | 49.1 | 80 (3) | M2.v2 0.2772 | 52 (24) | 0.2748 | 0.2748 |
| ibm14 | - | 39994404 | 9.6334 | 61.8 | 80 (15) | M6.v1 0.5201 | 0 (0) | 0.5193 | 0.4500 |
| ibm15 | - | 110953720 | 61.7165 | 182.6 | 80 (0) | M3.v2 0.3360 | 30 (18) | 0.3354 | 0.3354 |
| ibm16 | - | 113096416 | 40.2314 | 173.0 | 80 (5) | M6.v1 0.2804 | 53 (25) | 0.2793 | 0.2793 |
| ibm17 | - | 104944368 | 35.2532 | 205.8 | 80 (15) | M6.v2 0.5149 | 0 (0) | 0.5083 | 0.4500 |
| ibm18 | - | 208315024 | 76.1154 | 369.4 | 80 (0) | M4.v2 0.1231 | 18 (10) | 0.1205 | 0.1205 |

Distinct layouts below the baseline, all designs: 156.

## Failures (by name, counted as +inf in statistics)

- program_timeout (rc=-24): 68

## Exact commands

```bash
python scripts/run_seed_archive.py --designs ibm01,ibm02,ibm03,ibm04,ibm06,ibm07,ibm08,ibm09,ibm10,ibm11,ibm12,ibm13,ibm14,ibm15,ibm16,ibm17,ibm18 --archive archive_A0_trackA_dev --evaluator hbgp --ls 8 --min-fidelity 1 --out runs/seed_trackA --seeds 5 --suite ibm --top 10
```

## Notes

M1 = the tool-native macro placement (DREAMPlace mixed-size for the dreamplace evaluator; the benchmark macro positions for the HB-GP development runs); P_M disp = mean macro displacement of the legality check, core-normalized. Failures are counted as +inf and listed by name.
