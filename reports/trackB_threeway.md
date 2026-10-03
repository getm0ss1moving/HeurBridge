# Track B: HeurBridge, DREAMPlace and the tool through the OpenROAD flow

| Field | Value |
|---|---|
| Report | trackB_threeway |
| Pre-registration | reports/trackB_threeway_preregistration.md |
| Status of the claim | per design below |

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

