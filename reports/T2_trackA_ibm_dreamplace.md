# Track-A seeding campaign (T1.7 / T2.7): ibm_dreamplace

| Field | Value |
|---|---|
| Report | trackA_ibm_dreamplace |
| Date | 2026-09-27 20:55 |
| Node | 225 (RTX 3090 GPU 1; two campaign streams) |
| Track | A (DREAMPlace f1; M1 = DREAMPlace mixed-size) |
| Tool versions | DREAMPlace 4.3.1 (GPU; CUDA 11.8, torch 2.6.0) + f0 RUDY/HPWL |
| HeurBridge version / git | 0.12.0 / c6279e5d93ff37fd7acfe1add901ca82767809b7+dirty (c6279e5-dirty-20260927144729) |
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
| ibm01 | 35.3 / 0.0107 | 2484943 | 0.0000 | 10.3 | 80 (0) | M2.v2 0.5227 | 0 (0) | 0.5170 | 0.4500 |
| ibm02 | 35.2 / 0.0047 | 12170547 | 5.3541 | 8.9 | 80 (0) | M6.v0 0.1640 | 80 (37) | 0.1636 | 0.1636 |
| ibm03 | 40.1 / 0.0015 | 7108828 | 0.0111 | 9.5 | 80 (0) | M6.v0 0.4782 | 0 (0) | 0.4762 | 0.4500 |
| ibm04 | 34.3 / 0.0112 | 7926444 | 0.2226 | 8.7 | 80 (0) | M6.v1 0.4598 | 0 (0) | 0.4578 | 0.4497 |
| ibm06 | 46.2 / 0.0079 | 6353543 | 0.1893 | 9.1 | 80 (0) | M6.v0 0.4256 | 21 (9) | 0.4251 | 0.4251 |
| ibm07 | 22.6 / 0.0008 | 10174416 | 0.2165 | 10.6 | 80 (0) | M6.v0 0.4535 | 0 (0) | 0.4526 | 0.4497 |
| ibm08 | 28.9 / 0.0044 | 11443092 | 0.8012 | 10.7 | 80 (0) | M3.v2 0.5330 | 0 (0) | 0.5029 | 0.4498 |
| ibm09 | 23.0 / 0.0015 | 12336031 | 0.4822 | 9.6 | 80 (0) | M6.v0 0.4559 | 0 (0) | 0.4536 | 0.4500 |
| ibm10 | 23.2 / 0.0016 | 28332212 | 17.7813 | 10.5 | 80 (15) | M6.v1 0.5984 | 0 (0) | 0.5975 | 0.4498 |
| ibm11 | 24.2 / 0.0022 | 18788282 | 2.1041 | 10.2 | 80 (0) | M6.v0 0.5069 | 0 (0) | 0.5057 | 0.4493 |
| ibm12 | 23.5 / 0.0065 | 33360902 | 17.6958 | 10.9 | 80 (15) | M6.v0 0.4934 | 0 (0) | 0.4933 | 0.4499 |
| ibm13 | 23.4 / 0.0027 | 22803788 | 3.6861 | 11.6 | 80 (0) | M3.v2 0.5590 | 0 (0) | 0.5425 | 0.4498 |
| ibm14 | 21.1 / 0.0014 | 34593952 | 10.3222 | 13.4 | 80 (5) | M6.v1 0.5819 | 0 (0) | 0.5804 | 0.4499 |
| ibm15 | 32.3 / 0.0010 | 45026320 | 22.4233 | 15.3 | 80 (0) | M6.v2 0.5192 | 0 (0) | 0.5188 | 0.4501 |
| ibm16 | 25.6 / 0.0013 | 55367416 | 32.9164 | 15.9 | 80 (5) | M6.v2 0.4879 | 0 (0) | 0.4842 | 0.4500 |
| ibm17 | 25.0 / 0.0051 | 64529364 | 24.6404 | 16.9 | 80 (15) | M6.v1 0.4832 | 0 (0) | 0.4828 | 0.4500 |
| ibm18 | 26.6 / 0.0031 | 41168520 | 11.6694 | 18.4 | 80 (0) | M4.v1 0.4650 | 0 (0) | 0.4622 | 0.4503 |

Distinct layouts below the baseline, all designs: 46.

## Failures (by name, counted as +inf in statistics)

- program_timeout (rc=-24): 55

## Exact commands

```bash
python scripts/run_seed_archive.py --designs ibm01,ibm02,ibm04,ibm07,ibm09,ibm11,ibm13,ibm16,ibm18 --archive archive_A0_trackA_s1 --evaluator dreamplace --ls 8 --min-fidelity 1 --out runs/seed_trackA_dp --seeds 5 --suite ibm --top 10
python scripts/run_seed_archive.py --designs ibm03,ibm06,ibm08,ibm10,ibm12,ibm14,ibm15,ibm17 --archive archive_A0_trackA_s2 --evaluator dreamplace --ls 8 --min-fidelity 1 --out runs/seed_trackA_dp --seeds 5 --suite ibm --top 10
```

## Notes

M1 = the tool-native macro placement (DREAMPlace mixed-size for the dreamplace evaluator; the benchmark macro positions for the HB-GP development runs); P_M disp = mean macro displacement of the legality check, core-normalized. Failures are counted as +inf and listed by name. Against DREAMPlace's own mixed-size placement the programs win on two designs only: ibm02, whose M1 is anomalous (HPWL 12.2 M and RUDY OF 5.4 % where the benchmark macro positions give 5.97 M with HB-GP), and ibm06 (best J 0.4251, 9 distinct layouts). The archive entries just below 0.45 are the M1 baselines themselves (J = median over its 3 seeds against the median-metric normalizer). The 55 program timeouts are the M2 family on designs with >= 614 macros (sandbox CPU limit 60 s).
