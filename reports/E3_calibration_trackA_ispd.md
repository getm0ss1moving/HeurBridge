# E3-lite macro-stage calibration, f0 proxy vs f1 (development, Track A)

| Field | Value |
|---|---|
| Report | E3_calibration_trackA_ispd |
| Date | 2026-09-28 12:16 |
| Node | local (macOS, CPU) |
| Track | A-dev (HB-GP stand-in f1) |
| Tool versions | HeurBridge f0 surrogate J0 (clustered design, bridge-guard scorer); f1 from the stored campaign records |
| HeurBridge version / git | 0.13.4 / 0498787a97a728cee5eda61c6f06f66cb6db3c0a |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v1_2026-09-25 |
| Feeds gate | G0 (T6.2) for (M, f0) — development evidence only (f1 stands in for signoff) |
| Pre-registered test | - |
| alpha-ledger entry | - |
| Status of the claim | no claim (development / descriptive run) |

## Sample sizes

535 rows over 8 design(s) (adaptec1, adaptec2, adaptec3, adaptec4, bigblue1, bigblue2, bigblue3, bigblue4)

## Results

| design | n | Spearman | Kendall | top-5 recall | regret | random regret |
|---|---|---|---|---|---|---|
| adaptec1 | 82 | 0.729 | 0.590 | 0.00 | 0.0971 | 0.0288 |
| adaptec2 | 89 | 0.802 | 0.638 | 0.00 | 0.0014 | 0.0533 |
| adaptec3 | 79 | 0.675 | 0.452 | 0.00 | 0.0198 | 0.0418 |
| adaptec4 | 81 | 0.660 | 0.445 | 0.00 | 0.0123 | 0.0504 |
| bigblue1 | 81 | 0.724 | 0.570 | 0.40 | 0.0529 | 0.0160 |
| bigblue3 | 62 | 0.793 | 0.622 | 0.20 | 0.0005 | 0.0753 |
| bigblue4 | 61 | 0.624 | 0.450 | 0.00 | 0.0007 | 0.0765 |

Mean over designs: Kendall 0.538, Spearman 0.715, top-5 recall 0.09, regret 0.0264 vs random 0.0489.

Gate G0 rule for (stage M, f0 -> f1): **not met** (regret <= 25% of random and Kendall >= 0.5).

## Failures (by name, counted as +inf in statistics)

- adaptec1.M2.v2.s0.f1: program_timeout (rc=-24 )
- adaptec1.M2.v2.s1.f1: program_timeout (rc=-24 )
- adaptec1.M2.v2.s2.f1: program_timeout (rc=-24 )
- adaptec1.M2.v2.s3.f1: program_timeout (rc=-24 )
- adaptec1.M2.v2.s4.f1: program_timeout (rc=-24 )
- adaptec2.M2.v2.s0.f1: program_timeout (rc=-24 )
- adaptec2.M2.v2.s1.f1: program_timeout (rc=-24 )
- adaptec2.M2.v2.s2.f1: program_timeout (rc=-24 )
- adaptec2.M2.v2.s3.f1: program_timeout (rc=-24 )
- adaptec2.M2.v2.s4.f1: program_timeout (rc=-24 )
- adaptec3.M2.v0.s0.f1: program_timeout (rc=-24 )
- adaptec3.M2.v0.s1.f1: program_timeout (rc=-24 )
- adaptec3.M2.v0.s2.f1: program_timeout (rc=-24 )
- adaptec3.M2.v0.s3.f1: program_timeout (rc=-24 )
- adaptec3.M2.v0.s4.f1: program_timeout (rc=-24 )
- adaptec3.M2.v1.s0.f1: program_timeout (rc=-24 )
- adaptec3.M2.v1.s1.f1: program_timeout (rc=-24 )
- adaptec3.M2.v1.s2.f1: program_timeout (rc=-24 )
- adaptec3.M2.v1.s3.f1: program_timeout (rc=-24 )
- adaptec3.M2.v1.s4.f1: program_timeout (rc=-24 )
- adaptec3.M2.v2.s0.f1: program_timeout (rc=-24 )
- adaptec3.M2.v2.s1.f1: program_timeout (rc=-24 )
- adaptec3.M2.v2.s2.f1: program_timeout (rc=-24 )
- adaptec3.M2.v2.s3.f1: program_timeout (rc=-24 )
- adaptec3.M2.v2.s4.f1: program_timeout (rc=-24 )
- adaptec4.M2.v0.s0.f1: program_timeout (rc=-24 )
- adaptec4.M2.v0.s1.f1: program_timeout (rc=-24 )
- adaptec4.M2.v0.s2.f1: program_timeout (rc=-24 )
- adaptec4.M2.v0.s3.f1: program_timeout (rc=-24 )
- adaptec4.M2.v0.s4.f1: program_timeout (rc=-24 )
- adaptec4.M2.v1.s0.f1: program_timeout (rc=-24 )
- adaptec4.M2.v1.s1.f1: program_timeout (rc=-24 )
- adaptec4.M2.v1.s2.f1: program_timeout (rc=-24 )
- adaptec4.M2.v1.s3.f1: program_timeout (rc=-24 )
- adaptec4.M2.v1.s4.f1: program_timeout (rc=-24 )
- adaptec4.M2.v2.s0.f1: program_timeout (rc=-24 )
- adaptec4.M2.v2.s1.f1: program_timeout (rc=-24 )
- adaptec4.M2.v2.s2.f1: program_timeout (rc=-24 )
- adaptec4.M2.v2.s3.f1: program_timeout (rc=-24 )
- adaptec4.M2.v2.s4.f1: program_timeout (rc=-24 )
- bigblue1.M2.v2.s0.f1: program_timeout (rc=-24 )
- bigblue1.M2.v2.s1.f1: program_timeout (rc=-24 )
- bigblue1.M2.v2.s2.f1: program_timeout (rc=-24 )
- bigblue1.M2.v2.s3.f1: program_timeout (rc=-24 )
- bigblue1.M2.v2.s4.f1: program_timeout (rc=-24 )
- bigblue2.M2.v0.s0.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M2.v0.s1.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M2.v0.s2.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M2.v0.s3.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M2.v0.s4.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M2.v1.s0.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M2.v1.s1.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M2.v1.s2.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M2.v1.s3.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M2.v1.s4.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M2.v2.s0.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M2.v2.s1.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M2.v2.s2.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M2.v2.s3.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M2.v2.s4.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M3.v0.s0.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M3.v0.s1.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M3.v0.s2.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M3.v0.s3.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M3.v0.s4.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M3.v1.s0.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M3.v1.s1.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M3.v1.s2.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M3.v1.s3.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M3.v1.s4.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M3.v2.s0.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M3.v2.s1.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M3.v2.s2.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M3.v2.s3.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M3.v2.s4.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M4.v0.s0.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M4.v0.s1.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M4.v0.s2.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M4.v0.s3.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M4.v0.s4.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M4.v1.s0.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M4.v1.s1.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M4.v1.s2.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M4.v1.s3.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M4.v1.s4.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M4.v2.s0.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M4.v2.s1.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M4.v2.s2.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M4.v2.s3.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M4.v2.s4.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M5.v0.s0.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M5.v0.s1.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M5.v0.s2.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M5.v0.s3.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M5.v0.s4.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M5.v1.s0.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M5.v1.s1.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M5.v1.s2.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M5.v1.s3.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M5.v1.s4.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M6.v0.s0.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M6.v0.s1.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M6.v0.s2.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M6.v0.s3.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M6.v0.s4.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M6.v1.s0.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M6.v1.s1.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M6.v1.s2.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M6.v1.s3.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M6.v1.s4.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M6.v2.s0.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M6.v2.s1.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M6.v2.s2.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M6.v2.s3.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M6.v2.s4.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M7.v0.s0.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M7.v0.s1.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M7.v0.s2.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M7.v0.s3.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M7.v0.s4.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M7.v1.s0.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M7.v1.s1.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M7.v1.s2.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M7.v1.s3.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue2.M7.v1.s4.f1: program_crash (rc=1 Traceback (most recent call last):
  File "<string>", line 52, in <module>
MemoryError
)
- bigblue3.M2.v0.s0.f1: program_timeout (rc=-24 )
- bigblue3.M2.v0.s1.f1: program_timeout (rc=-24 )
- bigblue3.M2.v0.s2.f1: program_timeout (rc=-24 )
- bigblue3.M2.v0.s3.f1: program_timeout (rc=-24 )
- bigblue3.M2.v0.s4.f1: program_timeout (rc=-24 )
- bigblue3.M2.v1.s0.f1: program_timeout (rc=-24 )
- bigblue3.M2.v1.s1.f1: program_timeout (rc=-24 )
- bigblue3.M2.v1.s2.f1: program_timeout (rc=-24 )
- bigblue3.M2.v1.s3.f1: program_timeout (rc=-24 )
- bigblue3.M2.v1.s4.f1: program_timeout (rc=-24 )
- bigblue3.M2.v2.s0.f1: program_timeout (rc=-24 )
- bigblue3.M2.v2.s1.f1: program_timeout (rc=-24 )
- bigblue3.M2.v2.s2.f1: program_timeout (rc=-24 )
- bigblue3.M2.v2.s3.f1: program_timeout (rc=-24 )
- bigblue3.M2.v2.s4.f1: program_timeout (rc=-24 )
- bigblue3.M3.v2.s0.f1: program_timeout (rc=-24 )
- bigblue3.M3.v2.s1.f1: program_timeout (rc=-24 )
- bigblue3.M3.v2.s2.f1: program_timeout (rc=-24 )
- bigblue3.M3.v2.s3.f1: program_timeout (rc=-24 )
- bigblue3.M3.v2.s4.f1: program_timeout (rc=-24 )
- bigblue3.M5.v0.s0.f1: program_timeout (rc=-24 )
- bigblue3.M5.v0.s1.f1: program_timeout (rc=-24 )
- bigblue3.M5.v0.s2.f1: program_timeout (rc=-24 )
- bigblue3.M5.v0.s3.f1: program_timeout (rc=-24 )
- bigblue3.M5.v0.s4.f1: program_timeout (rc=-24 )
- bigblue3.M5.v1.s0.f1: program_timeout (rc=-24 )
- bigblue3.M5.v1.s1.f1: program_timeout (rc=-24 )
- bigblue3.M5.v1.s2.f1: program_timeout (rc=-24 )
- bigblue3.M5.v1.s3.f1: program_timeout (rc=-24 )
- bigblue3.M5.v1.s4.f1: program_timeout (rc=-24 )
- bigblue4.M2.v0.s0.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M2.v0.s1.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M2.v0.s2.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M2.v0.s3.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M2.v0.s4.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M2.v1.s0.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M2.v1.s1.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M2.v1.s2.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M2.v1.s3.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M2.v1.s4.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M2.v2.s0.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M2.v2.s1.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M2.v2.s2.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M2.v2.s3.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M2.v2.s4.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M3.v2.s0.f1: program_timeout (rc=-24 )
- bigblue4.M3.v2.s1.f1: program_timeout (rc=-24 )
- bigblue4.M3.v2.s2.f1: program_timeout (rc=-24 )
- bigblue4.M3.v2.s3.f1: program_timeout (rc=-24 )
- bigblue4.M3.v2.s4.f1: program_timeout (rc=-24 )
- bigblue4.M4.v0.s0.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M4.v0.s1.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M4.v0.s2.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M4.v0.s3.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M4.v0.s4.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M4.v1.s0.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M4.v1.s1.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M4.v1.s2.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M4.v1.s3.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M4.v1.s4.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M4.v2.s0.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M4.v2.s1.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M4.v2.s2.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M4.v2.s3.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M4.v2.s4.f1: program_error (MemoryError: Unable to allocate 509. MiB for an array with shape (8170, 8170) and data type float64)
- bigblue4.M5.v0.s0.f1: program_error (MemoryError: )
- bigblue4.M5.v0.s1.f1: program_error (MemoryError: )
- bigblue4.M5.v0.s2.f1: program_error (MemoryError: )
- bigblue4.M5.v0.s3.f1: program_error (MemoryError: )
- bigblue4.M5.v0.s4.f1: program_error (MemoryError: )
- bigblue4.M5.v1.s0.f1: program_error (MemoryError: )
- bigblue4.M5.v1.s1.f1: program_error (MemoryError: )
- bigblue4.M5.v1.s2.f1: program_error (MemoryError: )
- bigblue4.M5.v1.s3.f1: program_error (MemoryError: )
- bigblue4.M5.v1.s4.f1: program_error (MemoryError: )

## Exact commands

```bash
python scripts/calibrate_dev.py --suite ispd2005 --designs adaptec1,adaptec2,adaptec3,adaptec4,bigblue1,bigblue2,bigblue3,bigblue4 --runs runs/remote/seedA_ispd_combined --out reports/E3_calibration_trackA_ispd
```

## Notes

Proxy = MacroStageScorer (f0 J0 of the clustered design); per-design statistics from heurbridge/stats/calibration.py. Supersedes reports/env/dev_calibration_f0_vs_hbgp.json, which scored a single layout per design (a harness error) and computed the Track-A cost with the raw RUDY overflow.
