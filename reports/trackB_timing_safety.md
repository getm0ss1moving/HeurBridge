# Track B: J and timing safety of every layout (decision D13 (a))

| Field | Value |
|---|---|
| Report | trackB_timing_safety |
| Label | descriptive (existing runs; no test is re-decided; the recorded TB, TW and TP results stand) |
| Code | scripts/timing_safety_report.py |

**The rule for new tests (the owner's decision D13 (a), 4 Oct).** Every position a layout ran at (f2,
unshifted or shifted) has two timing checks, setup and hold, each passed if its slack is at least the tool's run
at the same shift minus 0.02 ns (decision D11 (b)); a failed flow fails both. Two outputs per layout: **J**, the
median J before the gates over its positions, and **S**, the share of its timing checks passed. One score:
**J_safe = J + 0.04 x (1 - S)**: failing every check costs 0.04 J, about the margin's price measured on
swerv_wrapper (reports/timing_margin_explore.md). For new tests the best few layouts of every arm by J are run at
the band's shifts too, so that compared layouts have the same positions, and each arm's pick is its lowest J_safe
among them. Below, layouts with one position are listed for completeness; the picks compare equal positions.
Marks per position: S/H passed setup/hold, - failed, xx flow failed; margin = the smallest slack minus its
threshold, ns.

## bp_fe_top

**Selection stage** (each campaign's f2 layouts; the three with a shifted band have 4 positions; DREAMPlace's f2 layouts, 1 position):

| rank | layout | arm | positions | J | checks passed | marks | margin (ns) | J_safe |
|---|---|---|---|---|---|---|---|---|
| 1 | bp_fe_top.ls3.n1 | HeurBridge (local search) | 1 | 0.8937 | 2 of 2 | SH | 0.030 | 0.8937 |
| 2 | bp_fe_top.ls0.n4 | HeurBridge (local search) | 4 | 0.8942 | 8 of 8 | SH SH SH SH | 0.020 | 0.8942 |
| 3 | bp_fe_top.ls7.n2 | HeurBridge (local search) | 4 | 0.8937 | 7 of 8 | SH SH SH S- | -0.030 | 0.8987 |
| 4 | bp_fe_top.ls6.n1 | HeurBridge (local search) | 1 | 0.9011 | 2 of 2 | SH | 0.010 | 0.9011 |
| 5 | bp_fe_top.ls5.n2 | HeurBridge (local search) | 1 | 0.9085 | 2 of 2 | SH | 0.040 | 0.9085 |
| 6 | bp_fe_top.ls1.n1 | HeurBridge (local search) | 4 | 0.9060 | 7 of 8 | SH SH SH S- | -0.020 | 0.9110 |
| 7 | bp_fe_top.ls5.n3 | HeurBridge (local search) | 1 | 0.9133 | 2 of 2 | SH | 0.040 | 0.9133 |
| 8 | bp_fe_top.ls3.n3 | HeurBridge (local search) | 1 | 0.8971 | 1 of 2 | S- | -0.020 | 0.9171 |
| 9 | bp_fe_top.ls7.n1 | HeurBridge (local search) | 1 | 0.9251 | 2 of 2 | SH | 0.050 | 0.9251 |
| 10 | bp_fe_top.ls0.n3 | HeurBridge (local search) | 1 | 0.9261 | 2 of 2 | SH | 0.020 | 0.9261 |
| 11 | bp_fe_top.M3.v0.s2 | HeurBridge (programs) | 1 | 0.9268 | 2 of 2 | SH | 0.040 | 0.9268 |
| 12 | bp_fe_top.ls7.n3 | HeurBridge (local search) | 1 | 0.9089 | 1 of 2 | S- | -0.010 | 0.9289 |
| 13 | bp_fe_top.ls6.n4 | HeurBridge (local search) | 1 | 0.9522 | 2 of 2 | SH | 0.040 | 0.9522 |
| 14 | bp_fe_top.ls7.n0 | HeurBridge (local search) | 1 | 0.9670 | 2 of 2 | SH | 0.030 | 0.9670 |
| 15 | bp_fe_top.ext_dp.td1.s2 | DREAMPlace | 1 | 0.9813 | 1 of 2 | -H | -0.004 | 1.0013 |
| 16 | bp_fe_top.ls7.n4 | HeurBridge (local search) | 1 | 0.9852 | 1 of 2 | S- | -0.010 | 1.0052 |
| 17 | bp_fe_top.M6.v0.s0 | HeurBridge (programs) | 1 | 0.9978 | 0 of 2 | -- | -0.133 | 1.0378 |
| 18 | bp_fe_top.M7.v1.s4 | HeurBridge (programs) | 1 | 1.0666 | 2 of 2 | SH | 0.010 | 1.0666 |
| 19 | bp_fe_top.ext_dp.td0.6.s1 | DREAMPlace | 1 | 1.0708 | 1 of 2 | -H | -0.066 | 1.0908 |
| 20 | bp_fe_top.ext_dp.td0.6.s0 | DREAMPlace | 1 | 1.0747 | 1 of 2 | -H | -0.117 | 1.0947 |
| 21 | bp_fe_top.ext_dp.td0.8.s1 | DREAMPlace | 1 | 1.0768 | 1 of 2 | -H | -0.002 | 1.0968 |
| 22 | bp_fe_top.M3.v1.s0 | HeurBridge (programs) | 1 | 1.1352 | 2 of 2 | SH | 0.011 | 1.1352 |
| 23 | bp_fe_top.M7.v1.s1 | HeurBridge (programs) | 1 | 1.5925 | 0 of 2 | -- | -0.072 | 1.6325 |
| 24 | bp_fe_top.M2.v0.s2 | HeurBridge (programs) | 1 | 2.7662 | 1 of 2 | -H | -0.051 | 2.7862 |

- HeurBridge's pick by J_safe among its layouts with 4 positions: bp_fe_top.ls0.n4 (lambda 0: bp_fe_top.ls7.n2; 0.02: bp_fe_top.ls0.n4; 0.08: bp_fe_top.ls0.n4).
- DREAMPlace's pick by J_safe among its layouts with 1 position: bp_fe_top.ext_dp.td1.s2 (lambda 0: bp_fe_top.ext_dp.td1.s2; 0.02: bp_fe_top.ext_dp.td1.s2; 0.08: bp_fe_top.ext_dp.td1.s2).

**Test stage** (the Track-B test's six shifts; the tool's same-shift replicate as reference):

| arm | positions | J | checks passed | marks | margin (ns) | J_safe |
|---|---|---|---|---|---|---|
| HeurBridge (local search) | 6 | 0.9051 | 11 of 12 | SH SH SH SH S- SH | -0.010 | 0.9085 |
| tool | 6 | 1.0009 | 12 of 12 | SH SH SH SH SH SH | 0.020 | - (reference) |
| HeurBridge (programs) | 6 | 0.9044 | 11 of 12 | SH SH SH SH S- SH | -0.010 | 0.9077 |
| DREAMPlace | 6 | 1.0734 | 6 of 12 | -H -H -H -H -H -H | -0.132 | 1.0934 |

## bp_be_top

**Selection stage** (each campaign's f2 layouts; the three with a shifted band have 4 positions; DREAMPlace's f2 layouts, 1 position):

| rank | layout | arm | positions | J | checks passed | marks | margin (ns) | J_safe |
|---|---|---|---|---|---|---|---|---|
| 1 | bp_be_top.ext_dp.td0.8.s1 | DREAMPlace | 1 | 0.8968 | 1 of 2 | S- | -0.010 | 0.9168 |
| 2 | bp_be_top.ls1.n1 | HeurBridge (local search) | 1 | 0.9356 | 2 of 2 | SH | 0.000 | 0.9356 |
| 3 | bp_be_top.ext_dp.td0.6.s1 | DREAMPlace | 1 | 0.9428 | 2 of 2 | SH | 0.000 | 0.9428 |
| 4 | bp_be_top.M3.v2.s0 | HeurBridge (programs) | 1 | 0.9659 | 2 of 2 | SH | 0.020 | 0.9659 |
| 5 | bp_be_top.ls7.n4 | HeurBridge (local search) | 1 | 0.9681 | 2 of 2 | SH | 0.030 | 0.9681 |
| 6 | bp_be_top.M7.v1.s0 | HeurBridge (programs) | 1 | 0.9747 | 2 of 2 | SH | 0.010 | 0.9747 |
| 7 | bp_be_top.ext_dp.td0.6.s2 | DREAMPlace | 1 | 0.9555 | 1 of 2 | S- | -0.020 | 0.9755 |
| 8 | bp_be_top.ls7.n1 | HeurBridge (local search) | 4 | 0.9766 | 8 of 8 | SH SH SH SH | 0.000 | 0.9766 |
| 9 | bp_be_top.M3.v2.s4 | HeurBridge (programs) | 1 | 0.9812 | 2 of 2 | SH | 0.020 | 0.9812 |
| 10 | bp_be_top.M3.v2.s3 | HeurBridge (programs) | 1 | 0.9661 | 1 of 2 | S- | -0.010 | 0.9861 |
| 11 | bp_be_top.ext_dp.td0.6.s3 | DREAMPlace | 1 | 0.9701 | 1 of 2 | S- | -0.010 | 0.9901 |
| 12 | bp_be_top.M3.v2.s1 | HeurBridge (programs) | 1 | 0.9960 | 2 of 2 | SH | 0.020 | 0.9960 |
| 13 | bp_be_top.M3.v1.s3 | HeurBridge (programs) | 4 | 0.9900 | 6 of 8 | SH S- -H SH | -0.010 | 1.0000 |
| 14 | bp_be_top.ls6.n3 | HeurBridge (local search) | 1 | 1.0007 | 2 of 2 | SH | 0.030 | 1.0007 |
| 15 | bp_be_top.ls7.n2 | HeurBridge (local search) | 1 | 1.0092 | 2 of 2 | SH | 0.000 | 1.0092 |
| 16 | bp_be_top.M2.v0.s4 | HeurBridge (programs) | 1 | 1.0244 | 2 of 2 | SH | 0.010 | 1.0244 |
| 17 | bp_be_top.ls7.n3 | HeurBridge (local search) | 1 | 1.0339 | 2 of 2 | SH | 0.010 | 1.0339 |
| 18 | bp_be_top.M2.v1.s0 | HeurBridge (programs) | 4 | 1.0458 | 7 of 8 | SH SH -H SH | -0.012 | 1.0508 |
| 19 | bp_be_top.ls6.n4 | HeurBridge (local search) | 1 | 1.0602 | 2 of 2 | SH | 0.000 | 1.0602 |
| 20 | bp_be_top.M3.v2.s2 | HeurBridge (programs) | 1 | 1.0704 | 2 of 2 | SH | 0.010 | 1.0704 |
| 21 | bp_be_top.ls0.n2 | HeurBridge (local search) | 1 | 1.0949 | 2 of 2 | SH | 0.003 | 1.0949 |
| 22 | bp_be_top.M2.v1.s2 | HeurBridge (programs) | 1 | 1.1532 | 1 of 2 | -H | -0.060 | 1.1732 |
| 23 | bp_be_top.M6.v1.s0 | HeurBridge (programs) | 1 | 1.2377 | 0 of 2 | -- | -0.110 | 1.2777 |
| 24 | bp_be_top.M6.v2.s0 | HeurBridge (programs) | 1 | 1.3553 | 0 of 2 | -- | -0.363 | 1.3953 |

- HeurBridge's pick by J_safe among its layouts with 4 positions: bp_be_top.ls7.n1 (lambda 0: bp_be_top.ls7.n1; 0.02: bp_be_top.ls7.n1; 0.08: bp_be_top.ls7.n1).
- DREAMPlace's pick by J_safe among its layouts with 1 position: bp_be_top.ext_dp.td0.8.s1 (lambda 0: bp_be_top.ext_dp.td0.8.s1; 0.02: bp_be_top.ext_dp.td0.8.s1; 0.08: bp_be_top.ext_dp.td0.8.s1).

**Test stage** (the Track-B test's six shifts; the tool's same-shift replicate as reference):

| arm | positions | J | checks passed | marks | margin (ns) | J_safe |
|---|---|---|---|---|---|---|
| HeurBridge (local search) | 6 | 1.0167 | 12 of 12 | SH SH SH SH SH SH | 0.020 | 1.0167 |
| tool | 6 | 1.1077 | 8 of 12 | SH SH SH xx SH xx | -inf | - (reference) |
| HeurBridge (programs) | 6 | 1.0346 | 9 of 12 | SH SH SH xx SH S- | -inf | 1.0446 |
| DREAMPlace | 6 | 0.9605 | 6 of 12 | SH xx S- S- S- S- | -inf | 0.9805 |

## ariane136

**Selection stage** (each campaign's f2 layouts; the three with a shifted band have 4 positions; DREAMPlace's f2 layouts, 1 position):

| rank | layout | arm | positions | J | checks passed | marks | margin (ns) | J_safe |
|---|---|---|---|---|---|---|---|---|
| 1 | ariane136.ls6.n1 | HeurBridge (local search) | 1 | 0.9759 | 2 of 2 | SH | 0.030 | 0.9759 |
| 2 | ariane136.ls5.n2 | HeurBridge (local search) | 1 | 0.9760 | 2 of 2 | SH | 0.030 | 0.9760 |
| 3 | ariane136.ls5.n1 | HeurBridge (local search) | 1 | 0.9760 | 2 of 2 | SH | 0.059 | 0.9760 |
| 4 | ariane136.ls5.n4 | HeurBridge (local search) | 1 | 0.9760 | 2 of 2 | SH | 0.000 | 0.9760 |
| 5 | ariane136.ls2.n5 | HeurBridge (local search) | 1 | 0.9762 | 2 of 2 | SH | 0.058 | 0.9762 |
| 6 | ariane136.ls5.n0 | HeurBridge (local search) | 1 | 0.9765 | 2 of 2 | SH | 0.030 | 0.9765 |
| 7 | ariane136.ls1.n3 | HeurBridge (local search) | 1 | 0.9773 | 2 of 2 | SH | 0.000 | 0.9773 |
| 8 | ariane136.ls3.n5 | HeurBridge (local search) | 1 | 0.9779 | 2 of 2 | SH | 0.020 | 0.9779 |
| 9 | ariane136.ls6.n0 | HeurBridge (local search) | 1 | 0.9792 | 2 of 2 | SH | 0.027 | 0.9792 |
| 10 | ariane136.ls6.n4 | HeurBridge (local search) | 4 | 0.9762 | 7 of 8 | SH S- SH SH | -0.030 | 0.9812 |
| 11 | ariane136.ls3.n3 | HeurBridge (local search) | 1 | 0.9825 | 2 of 2 | SH | 0.010 | 0.9825 |
| 12 | ariane136.ls5.n5 | HeurBridge (local search) | 4 | 0.9756 | 6 of 8 | SH -- SH SH | -0.020 | 0.9856 |
| 13 | ariane136.ls7.n3 | HeurBridge (local search) | 4 | 0.9761 | 6 of 8 | SH S- S- SH | -0.050 | 0.9861 |
| 14 | ariane136.ls3.n1 | HeurBridge (local search) | 1 | 0.9757 | 1 of 2 | S- | -0.010 | 0.9957 |
| 15 | ariane136.ls7.n2 | HeurBridge (local search) | 1 | 0.9757 | 1 of 2 | -H | -0.008 | 0.9957 |
| 16 | ariane136.ls7.n5 | HeurBridge (local search) | 1 | 0.9759 | 1 of 2 | S- | -0.010 | 0.9959 |
| 17 | ariane136.ls0.n5 | HeurBridge (local search) | 1 | 0.9764 | 1 of 2 | S- | -0.010 | 0.9964 |
| 18 | ariane136.ls7.n4 | HeurBridge (local search) | 1 | 0.9770 | 1 of 2 | -H | -0.044 | 0.9970 |
| 19 | ariane136.ls2.n0 | HeurBridge (local search) | 1 | 0.9779 | 1 of 2 | -H | -0.021 | 0.9979 |
| 20 | ariane136.ext_dp.td1.s1 | DREAMPlace | 1 | 1.0378 | 1 of 2 | -H | -0.039 | 1.0578 |
| 21 | ariane136.ext_dp.td1.s0 | DREAMPlace | 1 | 1.0384 | 1 of 2 | -H | -0.081 | 1.0584 |
| 22 | ariane136.ext_dp.td1.s3 | DREAMPlace | 1 | 1.0403 | 1 of 2 | -H | -0.234 | 1.0603 |
| 23 | ariane136.M4.v2.s0 | HeurBridge (programs) | 1 | 1.0295 | 0 of 2 | -- | -0.047 | 1.0695 |

- HeurBridge's pick by J_safe among its layouts with 4 positions: ariane136.ls6.n4 (lambda 0: ariane136.ls5.n5; 0.02: ariane136.ls6.n4; 0.08: ariane136.ls6.n4).
- DREAMPlace's pick by J_safe among its layouts with 1 position: ariane136.ext_dp.td1.s1 (lambda 0: ariane136.ext_dp.td1.s1; 0.02: ariane136.ext_dp.td1.s1; 0.08: ariane136.ext_dp.td1.s1).

**Test stage** (the Track-B test's six shifts; the tool's same-shift replicate as reference):

| arm | positions | J | checks passed | marks | margin (ns) | J_safe |
|---|---|---|---|---|---|---|
| HeurBridge (local search) | 6 | 0.9761 | 12 of 12 | SH SH SH SH SH SH | 0.017 | 0.9761 |
| tool | 6 | 1.0050 | 12 of 12 | SH SH SH SH SH SH | 0.020 | - (reference) |
| HeurBridge (programs) | 6 | 1.0276 | 8 of 12 | SH -H -- SH -H SH | -0.056 | 1.0409 |
| DREAMPlace | 6 | 1.0388 | 7 of 12 | SH -H -H SH xx -H | -inf | 1.0555 |

## swerv_wrapper

**Selection stage** (each campaign's f2 layouts; the three with a shifted band have 4 positions; DREAMPlace's f2 layouts, 1 position):

| rank | layout | arm | positions | J | checks passed | marks | margin (ns) | J_safe |
|---|---|---|---|---|---|---|---|---|
| 1 | swerv_wrapper.ls5.n4 | HeurBridge (local search) | 1 | 0.8674 | 2 of 2 | SH | 0.020 | 0.8674 |
| 2 | swerv_wrapper.ls3.n4 | HeurBridge (local search) | 1 | 0.8770 | 2 of 2 | SH | 0.030 | 0.8770 |
| 3 | swerv_wrapper.ls7.n1 | HeurBridge (local search) | 1 | 0.8798 | 2 of 2 | SH | 0.012 | 0.8798 |
| 4 | swerv_wrapper.ls0.n0 | HeurBridge (local search) | 1 | 0.8907 | 2 of 2 | SH | 0.005 | 0.8907 |
| 5 | swerv_wrapper.ls1.n1 | HeurBridge (local search) | 1 | 0.8987 | 2 of 2 | SH | 0.040 | 0.8987 |
| 6 | swerv_wrapper.ls5.n0 | HeurBridge (local search) | 1 | 0.8846 | 1 of 2 | S- | -0.130 | 0.9046 |
| 7 | swerv_wrapper.ls4.n2 | HeurBridge (local search) | 1 | 0.8849 | 1 of 2 | -H | -0.018 | 0.9049 |
| 8 | swerv_wrapper.ls4.n4 | HeurBridge (local search) | 1 | 0.9057 | 2 of 2 | SH | 0.000 | 0.9057 |
| 9 | swerv_wrapper.ls4.n5 | HeurBridge (local search) | 1 | 0.9064 | 2 of 2 | SH | 0.021 | 0.9064 |
| 10 | swerv_wrapper.ls7.n3 | HeurBridge (local search) | 1 | 0.8884 | 1 of 2 | -H | -0.016 | 0.9084 |
| 11 | swerv_wrapper.ls2.n3 | HeurBridge (local search) | 1 | 0.9087 | 2 of 2 | SH | 0.036 | 0.9087 |
| 12 | swerv_wrapper.ls6.n3 | HeurBridge (local search) | 1 | 0.9153 | 2 of 2 | SH | 0.000 | 0.9153 |
| 13 | swerv_wrapper.ls0.n1 | HeurBridge (local search) | 1 | 0.9322 | 1 of 2 | -H | -0.012 | 0.9522 |
| 14 | swerv_wrapper.ls2.n1 | HeurBridge (local search) | 1 | 0.9352 | 1 of 2 | -H | -0.049 | 0.9552 |
| 15 | swerv_wrapper.ls2.n0 | HeurBridge (local search) | 1 | 0.9359 | 1 of 2 | -H | -0.004 | 0.9559 |
| 16 | swerv_wrapper.ls0.n2 | HeurBridge (local search) | 1 | 0.9371 | 1 of 2 | -H | -0.031 | 0.9571 |
| 17 | swerv_wrapper.ls6.n1 | HeurBridge (local search) | 1 | 0.9496 | 1 of 2 | -H | -0.105 | 0.9696 |
| 18 | swerv_wrapper.ls3.n0 | HeurBridge (local search) | 1 | 0.9514 | 1 of 2 | -H | -0.014 | 0.9714 |
| 19 | swerv_wrapper.ls7.n4 | HeurBridge (local search) | 1 | 0.9750 | 2 of 2 | SH | 0.016 | 0.9750 |
| 20 | swerv_wrapper.ext_dp.td0.6.s1 | DREAMPlace | 1 | 1.0355 | 1 of 2 | -H | -0.216 | 1.0555 |
| 21 | swerv_wrapper.ext_dp.td1.s0 | DREAMPlace | 1 | 1.0221 | 0 of 2 | -- | -0.330 | 1.0621 |
| 22 | swerv_wrapper.ext_dp.td0.6.s3 | DREAMPlace | 1 | 1.0498 | 1 of 2 | -H | -0.207 | 1.0698 |
| 23 | swerv_wrapper.M4.v0.s0 | HeurBridge (programs) | 1 | 1.0773 | 1 of 2 | -H | -0.190 | 1.0973 |

- HeurBridge's pick by J_safe among its layouts with 1 position: swerv_wrapper.ls5.n4 (lambda 0: swerv_wrapper.ls5.n4; 0.02: swerv_wrapper.ls5.n4; 0.08: swerv_wrapper.ls5.n4).
- DREAMPlace's pick by J_safe among its layouts with 1 position: swerv_wrapper.ext_dp.td0.6.s1 (lambda 0: swerv_wrapper.ext_dp.td1.s0; 0.02: swerv_wrapper.ext_dp.td1.s0; 0.08: swerv_wrapper.ext_dp.td0.6.s1).

**Test stage** (the Track-B test's six shifts; the tool's same-shift replicate as reference):

| arm | positions | J | checks passed | marks | margin (ns) | J_safe |
|---|---|---|---|---|---|---|
| HeurBridge (local search) | 6 | 0.9266 | 9 of 12 | SH -H SH xx SH SH | -inf | 0.9366 |
| tool | 6 | 0.9165 | 12 of 12 | SH SH SH SH SH SH | 0.020 | - (reference) |
| HeurBridge (programs) | 6 | 1.0289 | 5 of 12 | SH -- -H xx S- -H | -inf | 1.0522 |
| DREAMPlace | 6 | +inf | 2 of 12 | xx -H -H xx -- xx | -inf | +inf |

Sources: local run files `runs/remote/seedB_orfs7_<design>/runs/seed_orfs/<design>/evals_f2.jsonl` and `baseline_f2.json`, `runs/remote/seedB_band_<design>/.../evals_f2.jsonl` (bands), `runs/remote/tb_<design>/.../evals_tb.jsonl`, `runs/remote/tw_*/.../evals_ext_dp.jsonl`, `runs/remote/tp_*/.../evals_tb_pg.jsonl`, `runs/remote/tls_*/.../evals_tls_f2.jsonl` (when present).
