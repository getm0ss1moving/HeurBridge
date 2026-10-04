# Track B: HeurBridge, DREAMPlace and the tool through the OpenROAD flow

| Field | Value |
|---|---|
| Report | trackB_threeway |
| Pre-registration | reports/trackB_threeway_preregistration.md |
| Status of the claim | **pre-registered confirmatory**: TW#1, TW#2 passed (TW#2 through the relative hold gate: see the notes); TW#3, TW#4 failed; overall at the end |

## bp_fe_top (TW#1)

Recorded 2026-10-04T02:18:43. **PASSED**: HeurBridge lower than DREAMPlace, exact one-sided rank-sum permutation p = 0.002165 against alpha_j = 0.025.

Reported, not tested: DREAMPlace lower than the tool (DREAMPlace gated, the tool before the gates): p = 0.9794. Median J before the gates: HeurBridge 0.9051, DREAMPlace 1.0734, tool 1.0009.

| replicate | arm | shift | J (HeurBridge, DREAMPlace: gated; tool: before gates) | J before gates | gates failed |
|---|---|---|---|---|---|
| bp_fe_top.tb.cand.s1.f2 | HeurBridge | [2, 0] | 0.9080 | 0.9080 | - |
| bp_fe_top.tb.cand.s2.f2 | HeurBridge | [-2, 0] | 0.9023 | 0.9023 | - |
| bp_fe_top.tb.cand.s3.f2 | HeurBridge | [0, -1] | 0.8811 | 0.8811 | - |
| bp_fe_top.tb.cand.s4.f2 | HeurBridge | [0, 2] | 0.9747 | 0.9747 | - |
| bp_fe_top.tb.cand.s5.f2 | HeurBridge | [1, 1] | 0.9183 | 0.9183 | - |
| bp_fe_top.tb.cand.s6.f2 | HeurBridge | [-1, -1] | 0.9017 | 0.9017 | - |
| bp_fe_top.ext_dp.tb.s1.f2 | DREAMPlace | [2, 0] | 1.5729 | 1.5729 | - |
| bp_fe_top.ext_dp.tb.s2.f2 | DREAMPlace | [-2, 0] | +inf | 1.0595 | setup |
| bp_fe_top.ext_dp.tb.s3.f2 | DREAMPlace | [0, -1] | 1.1841 | 1.1841 | - |
| bp_fe_top.ext_dp.tb.s4.f2 | DREAMPlace | [0, 2] | 0.9562 | 0.9562 | - |
| bp_fe_top.ext_dp.tb.s5.f2 | DREAMPlace | [1, 1] | +inf | 1.0873 | setup |
| bp_fe_top.ext_dp.tb.s6.f2 | DREAMPlace | [-1, -1] | +inf | 0.9352 | setup |
| bp_fe_top.tb.ref.s1.f2 | tool | [2, 0] | 0.9599 | 0.9599 | - |
| bp_fe_top.tb.ref.s2.f2 | tool | [-2, 0] | 1.0562 | 1.0562 | - |
| bp_fe_top.tb.ref.s3.f2 | tool | [0, -1] | 1.0759 | 1.0759 | - |
| bp_fe_top.tb.ref.s4.f2 | tool | [0, 2] | 0.9985 | 0.9985 | - |
| bp_fe_top.tb.ref.s5.f2 | tool | [1, 1] | 1.0002 | 1.0002 | - |
| bp_fe_top.tb.ref.s6.f2 | tool | [-1, -1] | 1.0015 | 1.0015 | - |

DREAMPlace's selection: 12 layouts to f1 (12 completed), 4 to f2, 2.3 flow-run hours; the tool's own flow run: 0.22 h (the campaign's f2 baseline, median). Pick: layout 10 (target density, seed: (1.0, 2)), no f2 layout admitted under D6: the best f2 J before the gates; the replicates used layout [10] (consistent).

Sources: runs/remote/tb_bp_fe_top/runs/seed_orfs/bp_fe_top/evals_tb.jsonl, runs/remote/tw_a/runs/seed_orfs/bp_fe_top/evals_ext_dp.jsonl, runs/remote/seedB_orfs7_bp_fe_top/runs/seed_orfs/bp_fe_top/evals_f2.jsonl.

## bp_be_top (TW#2)

Recorded 2026-10-04T05:22:57. **PASSED**: HeurBridge lower than DREAMPlace, exact one-sided rank-sum permutation p = 0.001082 against alpha_j = 0.0125.

Reported, not tested: DREAMPlace lower than the tool (DREAMPlace gated, the tool before the gates): p = 1. Median J before the gates: HeurBridge 1.0167, DREAMPlace 0.9605, tool 1.1077.

| replicate | arm | shift | J (HeurBridge, DREAMPlace: gated; tool: before gates) | J before gates | gates failed |
|---|---|---|---|---|---|
| bp_be_top.tb.cand.s1.f2 | HeurBridge | [2, 0] | 1.0401 | 1.0401 | - |
| bp_be_top.tb.cand.s2.f2 | HeurBridge | [-2, 0] | 0.9810 | 0.9810 | - |
| bp_be_top.tb.cand.s3.f2 | HeurBridge | [0, -1] | 0.9713 | 0.9713 | - |
| bp_be_top.tb.cand.s4.f2 | HeurBridge | [0, 2] | 1.0163 | 1.0163 | - |
| bp_be_top.tb.cand.s5.f2 | HeurBridge | [1, 1] | 1.0171 | 1.0171 | - |
| bp_be_top.tb.cand.s6.f2 | HeurBridge | [-1, -1] | 1.0192 | 1.0192 | - |
| bp_be_top.ext_dp.tb.s1.f2 | DREAMPlace | [2, 0] | +inf | 0.9721 | hold |
| bp_be_top.ext_dp.tb.s2.f2 | DREAMPlace | [-2, 0] | +inf | +inf | flow |
| bp_be_top.ext_dp.tb.s3.f2 | DREAMPlace | [0, -1] | +inf | 1.0080 | hold |
| bp_be_top.ext_dp.tb.s4.f2 | DREAMPlace | [0, 2] | +inf | 0.9417 | hold |
| bp_be_top.ext_dp.tb.s5.f2 | DREAMPlace | [1, 1] | +inf | 0.9466 | hold |
| bp_be_top.ext_dp.tb.s6.f2 | DREAMPlace | [-1, -1] | +inf | 0.9490 | hold |
| bp_be_top.tb.ref.s1.f2 | tool | [2, 0] | 1.0547 | 1.0547 | - |
| bp_be_top.tb.ref.s2.f2 | tool | [-2, 0] | 1.0647 | 1.0647 | - |
| bp_be_top.tb.ref.s3.f2 | tool | [0, -1] | 1.1207 | 1.1207 | - |
| bp_be_top.tb.ref.s4.f2 | tool | [0, 2] | +inf | +inf | flow |
| bp_be_top.tb.ref.s5.f2 | tool | [1, 1] | 1.0946 | 1.0946 | - |
| bp_be_top.tb.ref.s6.f2 | tool | [-1, -1] | +inf | +inf | flow |

DREAMPlace's selection: 12 layouts to f1 (12 completed), 4 to f2, 4.2 flow-run hours; the tool's own flow run: 0.47 h (the campaign's f2 baseline, median). Pick: layout 5 (target density, seed: (0.8, 1)), no f2 layout admitted under D6: the best f2 J before the gates; the replicates used layout [5] (consistent).

Sources: runs/remote/tb_bp_be_top/runs/seed_orfs/bp_be_top/evals_tb.jsonl, runs/remote/tw_a/runs/seed_orfs/bp_be_top/evals_ext_dp.jsonl, runs/remote/seedB_orfs7_bp_be_top/runs/seed_orfs/bp_be_top/evals_f2.jsonl.


## Notes on TW#1 and TW#2 (reported, not tested; written 2026-10-04 05:30)

- **TW#1 bp_fe_top: the pass is substantive.** Before the gates DREAMPlace's layout is worse than both HeurBridge's and
  the tool's (median J 1.073 against 0.905 and 1.001; reports/trackB_threeway.md:13), and its setup timing is worse:
  setup WNS -0.120 to -0.216 ns and TNS -0.23 to -3.04 ns, against HeurBridge's -0.031 to -0.045 ns and -0.05 to
  -0.25 ns and the tool's -0.054 to -0.084 ns and -0.15 to -0.68 ns; three replicates fail the setup gate
  (threshold -0.143 ns) (local run files `runs/remote/tw_a/runs/seed_orfs/bp_fe_top/evals_ext_dp.jsonl:17-22`,
  `runs/remote/tb_bp_fe_top/runs/seed_orfs/bp_fe_top/evals_tb.jsonl:1-12`).
- **TW#2 bp_be_top: the pass rests on a relative hold gate, not on a better layout.** Before the gates DREAMPlace's
  layout is the best of the three (median J 0.9605 against HeurBridge 1.0167 and the tool 1.1077;
  reports/trackB_threeway.md:44) and has the best setup timing (WNS -0.245 to -0.292 ns, TNS -22.8 to -28.2 ns,
  against HeurBridge's -0.269 to -0.308 ns and -24.5 to -29.2 ns). Its five completed replicates have hold WNS -0.02 to
  +0.02 ns with 0-2 hold violations; the gate's threshold is +0.035 ns (the tool's replay median +0.055 ns minus the
  0.02-ns guard), so it rejects hold slack that is still positive on four of them; one replicate failed in the flow
  (local run files `runs/remote/tw_a/runs/seed_orfs/bp_be_top/evals_ext_dp.jsonl:17-22`,
  `runs/remote/tb_bp_be_top/runs/seed_orfs/bp_be_top/evals_tb.jsonl:1-12`). The recorded result stands (PASSED under the
  registered rule); read it as "DREAMPlace's layout misses the tool's hold margin", not as "HeurBridge's layout is
  better". This is the gate behaviour of decision D11 (reports/next_phase_decisions.md, D11).
- **DREAMPlace's picks:** on both designs none of its four f2 layouts was admitted under D6, so the pick was the best
  f2 J before the gates (reports/trackB_threeway.md:36, :67).
## ariane136 (TW#3)

Recorded 2026-10-04T13:38:32. **FAILED**: HeurBridge lower than DREAMPlace, exact one-sided rank-sum permutation p = 0.1591 against alpha_j = 0.00625.

Reported, not tested: DREAMPlace lower than the tool (DREAMPlace gated, the tool before the gates): p = 1. Median J before the gates: HeurBridge 0.9761, DREAMPlace 1.0388, tool 1.0050.

| replicate | arm | shift | J (HeurBridge, DREAMPlace: gated; tool: before gates) | J before gates | gates failed |
|---|---|---|---|---|---|
| ariane136.tb.cand.s1.f2 | HeurBridge | [2, 0] | +inf | 0.9763 | hold |
| ariane136.tb.cand.s2.f2 | HeurBridge | [-2, 0] | 0.9759 | 0.9759 | - |
| ariane136.tb.cand.s3.f2 | HeurBridge | [0, -1] | 0.9763 | 0.9763 | - |
| ariane136.tb.cand.s4.f2 | HeurBridge | [0, 2] | +inf | 0.9764 | hold |
| ariane136.tb.cand.s5.f2 | HeurBridge | [1, 1] | 0.9753 | 0.9753 | - |
| ariane136.tb.cand.s6.f2 | HeurBridge | [-1, -1] | +inf | 0.9759 | hold |
| ariane136.ext_dp.tb.s1.f2 | DREAMPlace | [2, 0] | +inf | 1.0383 | setup |
| ariane136.ext_dp.tb.s2.f2 | DREAMPlace | [-2, 0] | 1.0394 | 1.0394 | - |
| ariane136.ext_dp.tb.s3.f2 | DREAMPlace | [0, -1] | +inf | 1.0369 | setup |
| ariane136.ext_dp.tb.s4.f2 | DREAMPlace | [0, 2] | 1.0381 | 1.0381 | - |
| ariane136.ext_dp.tb.s5.f2 | DREAMPlace | [1, 1] | +inf | +inf | flow |
| ariane136.ext_dp.tb.s6.f2 | DREAMPlace | [-1, -1] | +inf | 1.0403 | setup |
| ariane136.tb.ref.s1.f2 | tool | [2, 0] | 1.0203 | 1.0203 | setup, hold |
| ariane136.tb.ref.s2.f2 | tool | [-2, 0] | 1.0053 | 1.0053 | hold |
| ariane136.tb.ref.s3.f2 | tool | [0, -1] | 1.0032 | 1.0032 | - |
| ariane136.tb.ref.s4.f2 | tool | [0, 2] | 1.0042 | 1.0042 | hold |
| ariane136.tb.ref.s5.f2 | tool | [1, 1] | 1.0047 | 1.0047 | hold |
| ariane136.tb.ref.s6.f2 | tool | [-1, -1] | 1.0055 | 1.0055 | hold |

DREAMPlace's selection: 12 layouts to f1 (3 completed), 3 to f2, 18.6 flow-run hours; the tool's own flow run: 1.84 h (the campaign's f2 baseline, median). Pick: layout 9 (target density, seed: (1.0, 1)), no f2 layout admitted under D6: the best f2 J before the gates; the replicates used layout [9] (consistent).

Sources: runs/remote/tb_ariane136/runs/seed_orfs/ariane136/evals_tb.jsonl, runs/remote/tw_b/runs/seed_orfs/ariane136/evals_ext_dp.jsonl, runs/remote/seedB_orfs7_ariane136/runs/seed_orfs/ariane136/evals_f2.jsonl.


## Notes on TW#3 (reported, not tested; written 2026-10-04 13:45)

- **TW#3 ariane136 failed as recorded, but before the gates HeurBridge's layout is the best of the three.** All six
  HeurBridge replicates (J 0.9753-0.9764) are below all five completed DREAMPlace replicates (1.0369-1.0403) and below
  all six of the tool's (1.0032-1.0203) (reports/trackB_threeway.md:96-117). The gates then make three HeurBridge
  replicates +inf (hold WNS -0.02 to -0.01 ns against a threshold of -0.005 ns) and three DREAMPlace replicates +inf
  (setup WNS +0.924 to +1.009 ns, positive slack with TNS 0, against a threshold of +1.032 ns: the tool's replay median
  +1.052 ns minus the guard); one DREAMPlace replicate failed in the flow (DPL-0036); the rank test cannot separate the
  seven tied +inf values (p = 0.159). Both arms are rejected by relative gates for slack that is near zero or positive
  (local run files `runs/remote/tw_b/runs/seed_orfs/ariane136/evals_ext_dp.jsonl:16-21`,
  `runs/remote/tb_ariane136/runs/seed_orfs/ariane136/evals_tb.jsonl:1-12`).
- **Why DREAMPlace's J is higher here:** its detailed wirelength is 8.62-8.70 million um against HeurBridge's 7.33-7.35
  million and the tool's 8.05-8.52 million (the same files).
- **DREAMPlace in the flow on ariane136:** 9 of its 12 layouts failed f1, in detailed placement (DPL-0036, cells left
  unplaced) or by the 7,200-s step limit there; the three that completed are the target-density-1.0 runs
  (reports/trackB_threeway.md:119). HeurBridge's own heuristic programs fail the same way on this design: 40 of 80
  completed f1 in its campaign, 26 failing in detailed placement (local run file
  `runs/remote/seedB_orfs7_ariane136/runs/seed_orfs/ariane136/evals.jsonl`); its local-search layouts, moved step by step
  from a layout that worked, all completed (48 of 48).
## swerv_wrapper (TW#4)

Recorded 2026-10-04T15:49:56. **FAILED**: HeurBridge lower than DREAMPlace, exact one-sided rank-sum permutation p = 0.2273 against alpha_j = 0.003125.

Reported, not tested: DREAMPlace lower than the tool (DREAMPlace gated, the tool before the gates): p = 1. Median J before the gates: HeurBridge 0.9266, DREAMPlace +inf, tool 0.9165.

| replicate | arm | shift | J (HeurBridge, DREAMPlace: gated; tool: before gates) | J before gates | gates failed |
|---|---|---|---|---|---|
| swerv_wrapper.tb.cand.s1.f2 | HeurBridge | [2, 0] | +inf | 0.9143 | setup |
| swerv_wrapper.tb.cand.s2.f2 | HeurBridge | [-2, 0] | +inf | 0.9258 | setup |
| swerv_wrapper.tb.cand.s3.f2 | HeurBridge | [0, -1] | 0.8883 | 0.8883 | - |
| swerv_wrapper.tb.cand.s4.f2 | HeurBridge | [0, 2] | +inf | +inf | flow |
| swerv_wrapper.tb.cand.s5.f2 | HeurBridge | [1, 1] | +inf | 0.9273 | setup |
| swerv_wrapper.tb.cand.s6.f2 | HeurBridge | [-1, -1] | 0.9314 | 0.9314 | - |
| swerv_wrapper.ext_dp.tb.s1.f2 | DREAMPlace | [2, 0] | +inf | +inf | flow |
| swerv_wrapper.ext_dp.tb.s2.f2 | DREAMPlace | [-2, 0] | +inf | 0.9418 | setup |
| swerv_wrapper.ext_dp.tb.s3.f2 | DREAMPlace | [0, -1] | +inf | 0.9992 | setup |
| swerv_wrapper.ext_dp.tb.s4.f2 | DREAMPlace | [0, 2] | +inf | +inf | flow |
| swerv_wrapper.ext_dp.tb.s5.f2 | DREAMPlace | [1, 1] | +inf | 1.0024 | setup, hold |
| swerv_wrapper.ext_dp.tb.s6.f2 | DREAMPlace | [-1, -1] | +inf | +inf | flow |
| swerv_wrapper.tb.ref.s1.f2 | tool | [2, 0] | 0.9813 | 0.9813 | setup |
| swerv_wrapper.tb.ref.s2.f2 | tool | [-2, 0] | 0.8503 | 0.8503 | - |
| swerv_wrapper.tb.ref.s3.f2 | tool | [0, -1] | 0.8733 | 0.8733 | hold |
| swerv_wrapper.tb.ref.s4.f2 | tool | [0, 2] | 0.9658 | 0.9658 | setup |
| swerv_wrapper.tb.ref.s5.f2 | tool | [1, 1] | 0.9140 | 0.9140 | setup, hold |
| swerv_wrapper.tb.ref.s6.f2 | tool | [-1, -1] | 0.9190 | 0.9190 | setup |

DREAMPlace's selection: 12 layouts to f1 (3 completed), 3 to f2, 23.6 flow-run hours; the tool's own flow run: 1.51 h (the campaign's f2 baseline, median). Pick: layout 8 (target density, seed: (1.0, 0)), no f2 layout admitted under D6: the best f2 J before the gates; the replicates used layout [8] (consistent).

Sources: runs/remote/tb_swerv_wrapper/runs/seed_orfs/swerv_wrapper/evals_tb.jsonl, runs/remote/tw_swerv/runs/seed_orfs/swerv_wrapper/evals_ext_dp.jsonl, runs/remote/seedB_orfs7_swerv_wrapper/runs/seed_orfs/swerv_wrapper/evals_f2.jsonl.


## Overall (TW#1-TW#4; written 2026-10-04 15:52, after the four recorded results)

| design | entry | p | recorded | median J before the gates: HeurBridge / DREAMPlace / tool | DREAMPlace runs that failed in the flow: f1, replicates |
|---|---|---|---|---|---|
| bp_fe_top | TW#1 | 0.00216 (stats/alpha_ledger.jsonl:47) | **passed** | 0.905 / 1.073 / 1.001 | 0 of 12, 0 of 6 |
| bp_be_top | TW#2 | 0.00108 (stats/alpha_ledger.jsonl:49) | **passed** | 1.017 / 0.961 / 1.108 | 0 of 12, 1 of 6 |
| ariane136 | TW#3 | 0.159 (stats/alpha_ledger.jsonl:50) | failed | 0.976 / 1.039 / 1.005 | 9 of 12, 1 of 6 |
| swerv_wrapper | TW#4 | 0.227 (stats/alpha_ledger.jsonl:55) | failed | 0.927 / +inf (completed: 0.942-1.002) / 0.917 | 9 of 12, 3 of 6 |

- **Recorded:** HeurBridge's layout beats DREAMPlace's under the registered rule on 2 of 4 designs (TW#1, TW#2).
- **Read with the notes above:** only TW#1 is a better layout; TW#2's pass comes from the relative hold gate (before
  the gates DREAMPlace's bp_be_top layout is the best of the three). Before the gates HeurBridge's median is the lowest
  of the three on bp_fe_top and ariane136; on swerv_wrapper the tool's is, and half of DREAMPlace's replicates did not
  complete the flow.
- **DREAMPlace in the flow:** its layouts pass the flow on the two small designs and often fail it on the two large ones
  (detailed placement failures and 7,200-s timeouts), as HeurBridge's own heuristic programs often do there; HeurBridge's
  candidates come through because its search refines layouts that already pass the flow, scored by the flow itself.
- **Next (decided 4 Oct):** HeurBridge's programs without the flow-scored search against DREAMPlace (D12 (c), campaign TP,
  reports/trackB_programs_preregistration.md), gates under D11 (b).
