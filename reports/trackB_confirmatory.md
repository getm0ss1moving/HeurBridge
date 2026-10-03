# Track B: confirmatory results

| Field | Value |
|---|---|
| Report | trackB_confirmatory |
| Pre-registration | reports/trackB_preregistration.md |
| Status of the claim | **pre-registered confirmatory**: TB#1 passed, TB#2 passed, TB#3 failed (negative result); TB#4 pending |

## Summary (pre-registered confirmatory; written 2026-10-03 22:47, after the three recorded results)

| design | ledger | alpha_j | p | result | median J before the gates, candidate / reference |
|---|---|---|---|---|---|
| bp_fe_top | TB#1 | 0.025 | 0.0022 (stats/alpha_ledger.jsonl:38) | **passed** | 0.9051 / 1.0009 (reports/trackB_confirmatory.md:123) |
| bp_be_top | TB#2 | 0.0125 | 0.0011 (stats/alpha_ledger.jsonl:39) | **passed** | 1.0167 / 1.1077 (reports/trackB_confirmatory.md:148) |
| ariane136 | TB#3 | 0.00625 | 0.530 (stats/alpha_ledger.jsonl:40) | **failed** (negative result) | 0.9761 / 1.0050 (reports/trackB_confirmatory.md:173) |

Track-B claim so far: the HeurBridge layout beats the tool's macro placement at signoff, beyond the flow's shift
sensitivity, on 2 of 3 designs (bp_fe_top, bp_be_top). TB#4 (swerv_wrapper) runs when its campaign completes; TB#5
(ariane133) only under decision D2.

Notes (descriptive, not part of the test):

1. **TB#1's pass rests on a boundary replicate.** bp_fe_top.tb.cand.s2 has hold WNS -0.050 ns against a threshold of
   exactly -0.050 ns (the replay median -0.030 ns minus the 0.02-ns guard; the rule is candidate >= threshold)
   (reports/trackB_confirmatory.md:106, reports/trackB_confirmatory.md:111). One 0.01-ns step lower, it would be +inf and p would be 43/924 = 0.047 > 0.025
   (trackb_confirm.rank_sum_p on the recorded values with that replicate set to +inf): TB#1 would have failed.
2. **TB#2 does not depend on how its two failed reference runs are counted.** Both are flow failures (GRT-0116, global
   routing finished with congestion) on shifts (0, +2) and (-1, -1) (reports/trackB_confirmatory.md:144, reports/trackB_confirmatory.md:146); the candidate band
   0.971-1.040 also lies below the four finite references 1.055-1.121 (reports/trackB_confirmatory.md:68-79), which alone would give
   p = 1/210 = 0.0048.
3. **Why TB#3 failed.** The hold gate failed on 3 of 6 shifts: hold WNS -0.02, -0.01 and -0.01 ns against a threshold of
   -0.005 ns (the median of four unshifted replays, +0.015 ns, minus 0.02 ns) (reports/trackB_confirmatory.md:156, reports/trackB_confirmatory.md:160-165). Before
   the gates, all six candidate replicates (0.975-0.976) are below all six reference replicates (1.003-1.020), and the
   tool's own shifted layouts have hold WNS from -0.06 to 0.00 ns, failing the same check on 5 of 6 shifts
   (reports/trackB_confirmatory.md:166-171). On this design the tool's layout moves hold WNS between -0.06 and +0.05 ns across replays and
   shifts (replays: 0.00, +0.05, +0.03, -0.02 ns, runs/remote/seedB_orfs7_ariane136/runs/seed_orfs/ariane136/evals_f2.jsonl:1-4),
   more than the 0.02-ns guard. This describes the gate; it does not re-read the result: TB#3 is a negative result.
4. **Cost.** Finding the candidates took 29.3, 33.4 and 86.3 flow-run hours: 133x, 72x and 47x one run of the
   unmodified flow (reports/trackB_confirmatory.md:125, reports/trackB_confirmatory.md:150, reports/trackB_confirmatory.md:175).

## bp_fe_top (TB#1)

Candidate bp_fe_top.ls0.n4.f2; recorded 2026-10-03T22:36:47. **PASSED**: exact one-sided rank-sum permutation p = 0.002165 against alpha_j = 0.025; whole candidate band below the reference band: no.

| replicate | arm | shift | J (candidate: gated; reference: before gates) | gates failed |
|---|---|---|---|---|
| bp_fe_top.tb.cand.s1.f2 | TB_CAND | [2, 0] | 0.9080 | - |
| bp_fe_top.tb.cand.s2.f2 | TB_CAND | [-2, 0] | 0.9023 | - |
| bp_fe_top.tb.cand.s3.f2 | TB_CAND | [0, -1] | 0.8811 | - |
| bp_fe_top.tb.cand.s4.f2 | TB_CAND | [0, 2] | 0.9747 | - |
| bp_fe_top.tb.cand.s5.f2 | TB_CAND | [1, 1] | 0.9183 | - |
| bp_fe_top.tb.cand.s6.f2 | TB_CAND | [-1, -1] | 0.9017 | - |
| bp_fe_top.tb.ref.s1.f2 | TB_REF | [2, 0] | 0.9599 | - |
| bp_fe_top.tb.ref.s2.f2 | TB_REF | [-2, 0] | 1.0562 | - |
| bp_fe_top.tb.ref.s3.f2 | TB_REF | [0, -1] | 1.0759 | - |
| bp_fe_top.tb.ref.s4.f2 | TB_REF | [0, 2] | 0.9985 | - |
| bp_fe_top.tb.ref.s5.f2 | TB_REF | [1, 1] | 1.0002 | - |
| bp_fe_top.tb.ref.s6.f2 | TB_REF | [-1, -1] | 1.0015 | - |

Sources: runs/remote/tb_bp_fe_top/runs/seed_orfs/bp_fe_top/evals_tb.jsonl, runs/remote/seedB_orfs7_bp_fe_top/runs/seed_orfs/bp_fe_top/evals_f2.jsonl.

## bp_be_top (TB#2)

Candidate bp_be_top.ls7.n1.f2; recorded 2026-10-03T22:36:47. **PASSED**: exact one-sided rank-sum permutation p = 0.001082 against alpha_j = 0.0125; whole candidate band below the reference band: yes.

| replicate | arm | shift | J (candidate: gated; reference: before gates) | gates failed |
|---|---|---|---|---|
| bp_be_top.tb.cand.s1.f2 | TB_CAND | [2, 0] | 1.0401 | - |
| bp_be_top.tb.cand.s2.f2 | TB_CAND | [-2, 0] | 0.9810 | - |
| bp_be_top.tb.cand.s3.f2 | TB_CAND | [0, -1] | 0.9713 | - |
| bp_be_top.tb.cand.s4.f2 | TB_CAND | [0, 2] | 1.0163 | - |
| bp_be_top.tb.cand.s5.f2 | TB_CAND | [1, 1] | 1.0171 | - |
| bp_be_top.tb.cand.s6.f2 | TB_CAND | [-1, -1] | 1.0192 | - |
| bp_be_top.tb.ref.s1.f2 | TB_REF | [2, 0] | 1.0547 | - |
| bp_be_top.tb.ref.s2.f2 | TB_REF | [-2, 0] | 1.0647 | - |
| bp_be_top.tb.ref.s3.f2 | TB_REF | [0, -1] | 1.1207 | - |
| bp_be_top.tb.ref.s4.f2 | TB_REF | [0, 2] | +inf | - |
| bp_be_top.tb.ref.s5.f2 | TB_REF | [1, 1] | 1.0946 | - |
| bp_be_top.tb.ref.s6.f2 | TB_REF | [-1, -1] | +inf | - |

Sources: runs/remote/tb_bp_be_top/runs/seed_orfs/bp_be_top/evals_tb.jsonl, runs/remote/seedB_orfs7_bp_be_top/runs/seed_orfs/bp_be_top/evals_f2.jsonl.

## ariane136 (TB#3)

Candidate ariane136.ls7.n3.f2; recorded 2026-10-03T22:36:47. **FAILED**: exact one-sided rank-sum permutation p = 0.5303 against alpha_j = 0.00625; whole candidate band below the reference band: no.

| replicate | arm | shift | J (candidate: gated; reference: before gates) | gates failed |
|---|---|---|---|---|
| ariane136.tb.cand.s1.f2 | TB_CAND | [2, 0] | +inf | hold |
| ariane136.tb.cand.s2.f2 | TB_CAND | [-2, 0] | 0.9759 | - |
| ariane136.tb.cand.s3.f2 | TB_CAND | [0, -1] | 0.9763 | - |
| ariane136.tb.cand.s4.f2 | TB_CAND | [0, 2] | +inf | hold |
| ariane136.tb.cand.s5.f2 | TB_CAND | [1, 1] | 0.9753 | - |
| ariane136.tb.cand.s6.f2 | TB_CAND | [-1, -1] | +inf | hold |
| ariane136.tb.ref.s1.f2 | TB_REF | [2, 0] | 1.0203 | setup, hold |
| ariane136.tb.ref.s2.f2 | TB_REF | [-2, 0] | 1.0053 | hold |
| ariane136.tb.ref.s3.f2 | TB_REF | [0, -1] | 1.0032 | - |
| ariane136.tb.ref.s4.f2 | TB_REF | [0, 2] | 1.0042 | hold |
| ariane136.tb.ref.s5.f2 | TB_REF | [1, 1] | 1.0047 | hold |
| ariane136.tb.ref.s6.f2 | TB_REF | [-1, -1] | 1.0055 | hold |

Sources: runs/remote/tb_ariane136/runs/seed_orfs/ariane136/evals_tb.jsonl, runs/remote/seedB_orfs7_ariane136/runs/seed_orfs/ariane136/evals_f2.jsonl.

## bp_fe_top: reported, not tested (pre-registration Section 5)

Gate reference: the campaign's 4 same-path replays at f2, median setup WNS -0.123 ns and hold WNS -0.030 ns; a candidate replicate fails a timing gate below the reference minus 0.02 ns (hold WNS is reported in steps of 0.01 ns). Gates failed: under the candidate's rule (D6) for both arms; for the reference arm they are shown for information only, its endpoint being J before the gates.

| replicate | arm | shift | J before gates | setup WNS (ns) | hold WNS (ns) | hold violations | gates failed | flow wall (s) |
|---|---|---|---|---|---|---|---|---|
| bp_fe_top.tb.cand.s1.f2 | TB_CAND | [2, 0] | 0.9080 | -0.033 | -0.020 | 340 | - | 621 |
| bp_fe_top.tb.cand.s2.f2 | TB_CAND | [-2, 0] | 0.9023 | -0.044 | -0.050 | 427 | - | 594 |
| bp_fe_top.tb.cand.s3.f2 | TB_CAND | [0, -1] | 0.8811 | -0.031 | 0.010 | 0 | - | 598 |
| bp_fe_top.tb.cand.s4.f2 | TB_CAND | [0, 2] | 0.9747 | -0.045 | -0.020 | 60 | - | 640 |
| bp_fe_top.tb.cand.s5.f2 | TB_CAND | [1, 1] | 0.9183 | -0.041 | -0.030 | 69 | - | 647 |
| bp_fe_top.tb.cand.s6.f2 | TB_CAND | [-1, -1] | 0.9017 | -0.040 | -0.010 | 31 | - | 613 |
| bp_fe_top.tb.ref.s1.f2 | TB_REF | [2, 0] | 0.9599 | -0.060 | 0.000 | 3 | - | 748 |
| bp_fe_top.tb.ref.s2.f2 | TB_REF | [-2, 0] | 1.0562 | -0.064 | -0.030 | 126 | - | 802 |
| bp_fe_top.tb.ref.s3.f2 | TB_REF | [0, -1] | 1.0759 | -0.084 | -0.030 | 87 | - | 802 |
| bp_fe_top.tb.ref.s4.f2 | TB_REF | [0, 2] | 0.9985 | -0.077 | -0.030 | 153 | - | 850 |
| bp_fe_top.tb.ref.s5.f2 | TB_REF | [1, 1] | 1.0002 | -0.054 | 0.000 | 7 | - | 722 |
| bp_fe_top.tb.ref.s6.f2 | TB_REF | [-1, -1] | 1.0015 | -0.076 | -0.030 | 71 | - | 813 |

Median J before the gates: candidate 0.9051, reference 1.0009 (difference -0.0957).

Cost of finding the candidate: the campaign's 129 flow runs to f1 (104 completed) and 24 to f2, 29.3 flow-run hours in all (the sum of the runs' wall-clock; the campaign ran up to 8 at a time; the four same-path replays are included), against one run of the unmodified flow with the tool's macro placement, 0.22 h (the median of the campaign's 2 f2 baseline runs): 133x. This test's replicates took a median of 617 s (candidate) and 802 s (reference) per run.

Sources: runs/remote/tb_bp_fe_top/runs/seed_orfs/bp_fe_top/evals_tb.jsonl, runs/remote/seedB_orfs7_bp_fe_top/runs/seed_orfs/bp_fe_top/evals.jsonl, runs/remote/seedB_orfs7_bp_fe_top/runs/seed_orfs/bp_fe_top/evals_f2.jsonl, runs/remote/seedB_orfs7_bp_fe_top/runs/seed_orfs/bp_fe_top/baseline_f2.json.

## bp_be_top: reported, not tested (pre-registration Section 5)

Gate reference: the campaign's 4 same-path replays at f2, median setup WNS -0.329 ns and hold WNS 0.055 ns; a candidate replicate fails a timing gate below the reference minus 0.02 ns (hold WNS is reported in steps of 0.01 ns). Gates failed: under the candidate's rule (D6) for both arms; for the reference arm they are shown for information only, its endpoint being J before the gates.

| replicate | arm | shift | J before gates | setup WNS (ns) | hold WNS (ns) | hold violations | gates failed | flow wall (s) |
|---|---|---|---|---|---|---|---|---|
| bp_be_top.tb.cand.s1.f2 | TB_CAND | [2, 0] | 1.0401 | -0.308 | 0.050 | 0 | - | 1367 |
| bp_be_top.tb.cand.s2.f2 | TB_CAND | [-2, 0] | 0.9810 | -0.278 | 0.050 | 0 | - | 1215 |
| bp_be_top.tb.cand.s3.f2 | TB_CAND | [0, -1] | 0.9713 | -0.269 | 0.050 | 0 | - | 1299 |
| bp_be_top.tb.cand.s4.f2 | TB_CAND | [0, 2] | 1.0163 | -0.279 | 0.050 | 0 | - | 1341 |
| bp_be_top.tb.cand.s5.f2 | TB_CAND | [1, 1] | 1.0171 | -0.286 | 0.050 | 0 | - | 1315 |
| bp_be_top.tb.cand.s6.f2 | TB_CAND | [-1, -1] | 1.0192 | -0.307 | 0.050 | 0 | - | 1245 |
| bp_be_top.tb.ref.s1.f2 | TB_REF | [2, 0] | 1.0547 | -0.335 | 0.040 | 0 | - | 1808 |
| bp_be_top.tb.ref.s2.f2 | TB_REF | [-2, 0] | 1.0647 | -0.301 | 0.050 | 0 | - | 1538 |
| bp_be_top.tb.ref.s3.f2 | TB_REF | [0, -1] | 1.1207 | -0.337 | 0.050 | 0 | - | 1511 |
| bp_be_top.tb.ref.s4.f2 | TB_REF | [0, 2] | +inf (flow failed: RuntimeError: tool returncode 2 (GRT-0116 Global routing finished with congestion. Check t) | - | - | - | - | 818 |
| bp_be_top.tb.ref.s5.f2 | TB_REF | [1, 1] | 1.0946 | -0.324 | 0.050 | 0 | - | 1646 |
| bp_be_top.tb.ref.s6.f2 | TB_REF | [-1, -1] | +inf (flow failed: RuntimeError: tool returncode 2 (GRT-0116 Global routing finished with congestion. Check t) | - | - | - | - | 1346 |

Median J before the gates: candidate 1.0167, reference 1.1077 (difference -0.0910).

Cost of finding the candidate: the campaign's 129 flow runs to f1 (88 completed) and 24 to f2, 33.4 flow-run hours in all (the sum of the runs' wall-clock; the campaign ran up to 8 at a time; the four same-path replays are included), against one run of the unmodified flow with the tool's macro placement, 0.47 h (the median of the campaign's 2 f2 baseline runs): 72x. This test's replicates took a median of 1307 s (candidate) and 1524 s (reference) per run.

Sources: runs/remote/tb_bp_be_top/runs/seed_orfs/bp_be_top/evals_tb.jsonl, runs/remote/seedB_orfs7_bp_be_top/runs/seed_orfs/bp_be_top/evals.jsonl, runs/remote/seedB_orfs7_bp_be_top/runs/seed_orfs/bp_be_top/evals_f2.jsonl, runs/remote/seedB_orfs7_bp_be_top/runs/seed_orfs/bp_be_top/baseline_f2.json.

## ariane136: reported, not tested (pre-registration Section 5)

Gate reference: the campaign's 4 same-path replays at f2, median setup WNS 1.052 ns and hold WNS 0.015 ns; a candidate replicate fails a timing gate below the reference minus 0.02 ns (hold WNS is reported in steps of 0.01 ns). Gates failed: under the candidate's rule (D6) for both arms; for the reference arm they are shown for information only, its endpoint being J before the gates.

| replicate | arm | shift | J before gates | setup WNS (ns) | hold WNS (ns) | hold violations | gates failed | flow wall (s) |
|---|---|---|---|---|---|---|---|---|
| ariane136.tb.cand.s1.f2 | TB_CAND | [2, 0] | 0.9763 | 1.111 | -0.020 | 20 | hold | 3818 |
| ariane136.tb.cand.s2.f2 | TB_CAND | [-2, 0] | 0.9759 | 1.079 | 0.010 | 8 | - | 3621 |
| ariane136.tb.cand.s3.f2 | TB_CAND | [0, -1] | 0.9763 | 1.159 | 0.000 | 68 | - | 3528 |
| ariane136.tb.cand.s4.f2 | TB_CAND | [0, 2] | 0.9764 | 1.116 | -0.010 | 16 | hold | 3527 |
| ariane136.tb.cand.s5.f2 | TB_CAND | [1, 1] | 0.9753 | 1.123 | 0.050 | 0 | - | 3534 |
| ariane136.tb.cand.s6.f2 | TB_CAND | [-1, -1] | 0.9759 | 1.073 | -0.010 | 23 | hold | 3583 |
| ariane136.tb.ref.s1.f2 | TB_REF | [2, 0] | 1.0203 | 0.983 | -0.020 | 165 | setup, hold | 3898 |
| ariane136.tb.ref.s2.f2 | TB_REF | [-2, 0] | 1.0053 | 1.083 | -0.020 | 92 | hold | 3743 |
| ariane136.tb.ref.s3.f2 | TB_REF | [0, -1] | 1.0032 | 1.060 | 0.000 | 128 | - | 3632 |
| ariane136.tb.ref.s4.f2 | TB_REF | [0, 2] | 1.0042 | 1.060 | -0.060 | 472 | hold | 3656 |
| ariane136.tb.ref.s5.f2 | TB_REF | [1, 1] | 1.0047 | 1.070 | -0.030 | 127 | hold | 3723 |
| ariane136.tb.ref.s6.f2 | TB_REF | [-1, -1] | 1.0055 | 1.048 | -0.040 | 203 | hold | 3643 |

Median J before the gates: candidate 0.9761, reference 1.0050 (difference -0.0289).

Cost of finding the candidate: the campaign's 132 flow runs to f1 (92 completed) and 24 to f2, 86.3 flow-run hours in all (the sum of the runs' wall-clock; the campaign ran up to 8 at a time; the four same-path replays are included), against one run of the unmodified flow with the tool's macro placement, 1.84 h (the median of the campaign's 2 f2 baseline runs): 47x. This test's replicates took a median of 3558 s (candidate) and 3689 s (reference) per run.

Sources: runs/remote/tb_ariane136/runs/seed_orfs/ariane136/evals_tb.jsonl, runs/remote/seedB_orfs7_ariane136/runs/seed_orfs/ariane136/evals.jsonl, runs/remote/seedB_orfs7_ariane136/runs/seed_orfs/ariane136/evals_f2.jsonl, runs/remote/seedB_orfs7_ariane136/runs/seed_orfs/ariane136/baseline_f2.json.

