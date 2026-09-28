# Track-A seeding campaign (T1.7 / T2.7): ispd_dreamplace

| Field | Value |
|---|---|
| Report | trackA_ispd_dreamplace |
| Date | 2026-09-28 11:23 |
| Node | 225 (RTX 3090, GPU 1; two streams) |
| Track | A (DREAMPlace f1; M1 = DREAMPlace mixed-size) |
| Tool versions | DREAMPlace 4.3.1 (GPU; CUDA 11.8, torch 2.6.0) + f0 RUDY/HPWL |
| HeurBridge version / git | 0.13.1 / 924fcd1e20c03ac6a3f51ab374ec2771e2e7da9e (924fcd1-20260927232718) |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v1_2026-09-25 |
| Feeds gate | T2 exit (archive A0, Track A) — descriptive |
| Pre-registered test | - |
| alpha-ledger entry | - |
| Status of the claim | no claim (development / descriptive run) |

## Sample sizes

8 designs; 640 program evaluations; 336 local-search evaluations; baseline 3 seeds per design

## Results

J is relative to the baseline (J = 0.45 for the baseline by construction; lower is better); a layout 'beats' the baseline when J < 0.45.

| design | M1 s / P_M disp | baseline HPWL (median of 3) | RUDY OF % | f1 s | program evals (failed) | best program J | layouts < baseline (distinct) | LS best J | archive best J |
|---|---|---|---|---|---|---|---|---|---|
| adaptec1 | 15.3 / 0.0264 | 75245792 | 48.6529 | 15.3 | 80 (5) | M6.v0 0.4891 | 0 (0) | 0.4883 | 0.4500 |
| adaptec2 | 17.0 / 0.0389 | 100185552 | 62.5044 | 17.2 | 80 (5) | M6.v0 0.5065 | 0 (0) | 0.5043 | 0.4500 |
| adaptec3 | 25.6 / 0.0013 | 199646832 | 77.1509 | 26.1 | 80 (15) | M6.v0 0.4805 | 0 (0) | 0.4784 | 0.4500 |
| adaptec4 | 25.8 / 0.0025 | 179981232 | 76.7062 | 26.8 | 80 (15) | M6.v0 0.5283 | 0 (0) | 0.5269 | 0.4500 |
| bigblue1 | 18.5 / 0.0453 | 92813408 | 56.5976 | 19.0 | 80 (5) | M6.v2 0.4834 | 0 (0) | 0.4793 | 0.4500 |
| bigblue2 | 28.2 / 0.0073 | 147728864 | 70.4064 | 29.9 | 80 (80) | - | 0 (0) | - | 0.4500 |
| bigblue3 | 50.5 / 0.0487 | 385394688 | 88.8021 | 56.2 | 80 (30) | M6.v2 0.5335 | 0 (0) | 0.5330 | 0.4500 |
| bigblue4 | 97.9 / 0.0011 | 793540224 | 90.1590 | 103.3 | 80 (45) | M6.v0 0.5996 | 0 (0) | 0.5992 | 0.4500 |

Distinct layouts below the baseline, all designs: 0.

## Failures (by name, counted as +inf in statistics)

- program_timeout (rc=-24): 80
- program_crash (rc=1 MemoryError): 80
- program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64): 30
- program_error (MemoryError:): 10

## Exact commands

```bash
python scripts/run_seed_archive.py --designs adaptec1,bigblue1,bigblue4 --archive archive_A0_ispd_s1 --evaluator dreamplace --ls 8 --min-fidelity 1 --out runs/seed_trackA_ispd --seeds 5 --suite ispd2005 --top 10
python scripts/run_seed_archive.py --designs adaptec2,adaptec3,adaptec4,bigblue2,bigblue3 --archive archive_A0_ispd_s2 --evaluator dreamplace --ls 8 --min-fidelity 1 --out runs/seed_trackA_ispd --seeds 5 --suite ispd2005 --top 10
```

## Notes

M1 = the tool-native macro placement (DREAMPlace mixed-size for the dreamplace evaluator; the benchmark macro positions for the HB-GP development runs); P_M disp = mean macro displacement of the legality check, core-normalized. Failures are counted as +inf and listed by name. ISPD2005 in the MMS convention: every macro (fixed block) is movable. DREAMPlace's own mixed-size placement (M1) is the best layout on every design; the best program is 6.8-33% worse in J (M6 is the best program on all seven designs where programs ran). Memory is the program API's scaling limit: the program view carries a dense macro affinity (M x M float64) and programs run under a 4 GB address-space limit. bigblue2 (23,084 macros, affinity 4.3 GB): every program run crashes with MemoryError before the program starts, so its archive holds M1 only; bigblue4 (8,170 macros, 0.53 GB): the view loads, but 40 runs fail with MemoryError when a program allocates further M x M arrays. Program timeouts (60 s CPU) grow with the macro count (adaptec3/4, bigblue3, bigblue4: 15-45 of 80).
