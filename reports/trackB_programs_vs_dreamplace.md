# Track B: HeurBridge's programs (no local search) and DREAMPlace through the OpenROAD flow

| Field | Value |
|---|---|
| Report | trackB_programs_vs_dreamplace |
| Pre-registration | reports/trackB_programs_preregistration.md |
| Status of the claim | per design below |

## bp_fe_top (TP#1)

Program pick bp_fe_top.M3.v0.s2.f2. Recorded 2026-10-04T16:06:34. **PASSED**: programs lower than DREAMPlace, exact one-sided rank-sum permutation p = 0.007576 against alpha_j = 0.025.

Reported, not tested: median J before the gates: programs 0.9044, DREAMPlace 1.0734, HeurBridge with local search 0.9051, tool 1.0009; HeurBridge with local search lower than the programs under the same gates: p = 0.369.

| replicate | arm | shift | J (gated, D11 b; tool: before gates) | J before gates | gates failed | timing reference |
|---|---|---|---|---|---|---|
| bp_fe_top.tb_pg.cand.s1.f2 | programs | [2, 0] | 0.9046 | 0.9046 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.tb_pg.cand.s2.f2 | programs | [-2, 0] | 0.8958 | 0.8958 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.tb_pg.cand.s3.f2 | programs | [0, -1] | 0.9162 | 0.9162 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.tb_pg.cand.s4.f2 | programs | [0, 2] | 0.9225 | 0.9225 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.tb_pg.cand.s5.f2 | programs | [1, 1] | +inf | 0.8935 | hold | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.tb_pg.cand.s6.f2 | programs | [-1, -1] | 0.9042 | 0.9042 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.ext_dp.tb.s1.f2 | DREAMPlace | [2, 0] | +inf | 1.5729 | setup | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.ext_dp.tb.s2.f2 | DREAMPlace | [-2, 0] | +inf | 1.0595 | setup | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.ext_dp.tb.s3.f2 | DREAMPlace | [0, -1] | +inf | 1.1841 | setup | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.ext_dp.tb.s4.f2 | DREAMPlace | [0, 2] | +inf | 0.9562 | setup | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.ext_dp.tb.s5.f2 | DREAMPlace | [1, 1] | +inf | 1.0873 | setup | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.ext_dp.tb.s6.f2 | DREAMPlace | [-1, -1] | +inf | 0.9352 | setup | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.tb.cand.s1.f2 | HeurBridge (local search) | [2, 0] | 0.9080 | 0.9080 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.tb.cand.s2.f2 | HeurBridge (local search) | [-2, 0] | 0.9023 | 0.9023 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.tb.cand.s3.f2 | HeurBridge (local search) | [0, -1] | 0.8811 | 0.8811 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.tb.cand.s4.f2 | HeurBridge (local search) | [0, 2] | 0.9747 | 0.9747 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.tb.cand.s5.f2 | HeurBridge (local search) | [1, 1] | +inf | 0.9183 | hold | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.tb.cand.s6.f2 | HeurBridge (local search) | [-1, -1] | 0.9017 | 0.9017 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.tb.ref.s1.f2 | tool | [2, 0] | 0.9599 | 0.9599 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.tb.ref.s2.f2 | tool | [-2, 0] | 1.0562 | 1.0562 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.tb.ref.s3.f2 | tool | [0, -1] | 1.0759 | 1.0759 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.tb.ref.s4.f2 | tool | [0, 2] | 0.9985 | 0.9985 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.tb.ref.s5.f2 | tool | [1, 1] | 1.0002 | 1.0002 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_fe_top.tb.ref.s6.f2 | tool | [-1, -1] | 1.0015 | 1.0015 | - | the tool's replicate at the same shift, median of 1 runs |

Sources: runs/remote/tp_a/runs/seed_orfs/bp_fe_top/evals_tb_pg.jsonl, runs/remote/tw_a/runs/seed_orfs/bp_fe_top/evals_ext_dp.jsonl, runs/remote/tb_bp_fe_top/runs/seed_orfs/bp_fe_top/evals_tb.jsonl, runs/remote/seedB_orfs7_bp_fe_top/runs/seed_orfs/bp_fe_top/evals_f2.jsonl.

## bp_be_top (TP#2)

Program pick bp_be_top.M2.v1.s0.f2. Recorded 2026-10-04T16:54:40. **FAILED**: programs lower than DREAMPlace, exact one-sided rank-sum permutation p = 0.1212 against alpha_j = 0.0125.

Reported, not tested: median J before the gates: programs 1.0346, DREAMPlace 0.9605, HeurBridge with local search 1.0167, tool 1.1077; HeurBridge with local search lower than the programs under the same gates: p = 0.004329.

| replicate | arm | shift | J (gated, D11 b; tool: before gates) | J before gates | gates failed | timing reference |
|---|---|---|---|---|---|---|
| bp_be_top.tb_pg.cand.s1.f2 | programs | [2, 0] | 1.0572 | 1.0572 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_be_top.tb_pg.cand.s2.f2 | programs | [-2, 0] | 1.0465 | 1.0465 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_be_top.tb_pg.cand.s3.f2 | programs | [0, -1] | 1.0227 | 1.0227 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_be_top.tb_pg.cand.s4.f2 | programs | [0, 2] | +inf | +inf | flow | - |
| bp_be_top.tb_pg.cand.s5.f2 | programs | [1, 1] | 1.0208 | 1.0208 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_be_top.tb_pg.cand.s6.f2 | programs | [-1, -1] | +inf | 1.0098 | hold | the tool's completed replicates in the test, median of 4 runs |
| bp_be_top.ext_dp.tb.s1.f2 | DREAMPlace | [2, 0] | 0.9721 | 0.9721 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_be_top.ext_dp.tb.s2.f2 | DREAMPlace | [-2, 0] | +inf | +inf | flow | - |
| bp_be_top.ext_dp.tb.s3.f2 | DREAMPlace | [0, -1] | +inf | 1.0080 | hold | the tool's replicate at the same shift, median of 1 runs |
| bp_be_top.ext_dp.tb.s4.f2 | DREAMPlace | [0, 2] | +inf | 0.9417 | hold | the tool's completed replicates in the test, median of 4 runs |
| bp_be_top.ext_dp.tb.s5.f2 | DREAMPlace | [1, 1] | +inf | 0.9466 | hold | the tool's replicate at the same shift, median of 1 runs |
| bp_be_top.ext_dp.tb.s6.f2 | DREAMPlace | [-1, -1] | +inf | 0.9490 | hold | the tool's completed replicates in the test, median of 4 runs |
| bp_be_top.tb.cand.s1.f2 | HeurBridge (local search) | [2, 0] | 1.0401 | 1.0401 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_be_top.tb.cand.s2.f2 | HeurBridge (local search) | [-2, 0] | 0.9810 | 0.9810 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_be_top.tb.cand.s3.f2 | HeurBridge (local search) | [0, -1] | 0.9713 | 0.9713 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_be_top.tb.cand.s4.f2 | HeurBridge (local search) | [0, 2] | 1.0163 | 1.0163 | - | the tool's completed replicates in the test, median of 4 runs |
| bp_be_top.tb.cand.s5.f2 | HeurBridge (local search) | [1, 1] | 1.0171 | 1.0171 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_be_top.tb.cand.s6.f2 | HeurBridge (local search) | [-1, -1] | 1.0192 | 1.0192 | - | the tool's completed replicates in the test, median of 4 runs |
| bp_be_top.tb.ref.s1.f2 | tool | [2, 0] | 1.0547 | 1.0547 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_be_top.tb.ref.s2.f2 | tool | [-2, 0] | 1.0647 | 1.0647 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_be_top.tb.ref.s3.f2 | tool | [0, -1] | 1.1207 | 1.1207 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_be_top.tb.ref.s4.f2 | tool | [0, 2] | +inf | +inf | flow | - |
| bp_be_top.tb.ref.s5.f2 | tool | [1, 1] | 1.0946 | 1.0946 | - | the tool's replicate at the same shift, median of 1 runs |
| bp_be_top.tb.ref.s6.f2 | tool | [-1, -1] | +inf | +inf | flow | - |

Sources: runs/remote/tp_a/runs/seed_orfs/bp_be_top/evals_tb_pg.jsonl, runs/remote/tw_a/runs/seed_orfs/bp_be_top/evals_ext_dp.jsonl, runs/remote/tb_bp_be_top/runs/seed_orfs/bp_be_top/evals_tb.jsonl, runs/remote/seedB_orfs7_bp_be_top/runs/seed_orfs/bp_be_top/evals_f2.jsonl.

## ariane136 (TP#3)

Program pick ariane136.M4.v2.s0.f2. Recorded 2026-10-04T17:28:49. **FAILED**: programs lower than DREAMPlace, exact one-sided rank-sum permutation p = 0.1591 against alpha_j = 0.00625.

Reported, not tested: median J before the gates: programs 1.0276, DREAMPlace 1.0388, HeurBridge with local search 0.9761, tool 1.0050; HeurBridge with local search lower than the programs under the same gates: p = 0.001082.

| replicate | arm | shift | J (gated, D11 b; tool: before gates) | J before gates | gates failed | timing reference |
|---|---|---|---|---|---|---|
| ariane136.tb_pg.cand.s1.f2 | programs | [2, 0] | 1.0286 | 1.0286 | - | the tool's replicate at the same shift, median of 1 runs |
| ariane136.tb_pg.cand.s2.f2 | programs | [-2, 0] | +inf | 1.0265 | setup | the tool's replicate at the same shift, median of 1 runs |
| ariane136.tb_pg.cand.s3.f2 | programs | [0, -1] | +inf | 1.0277 | setup, hold | the tool's replicate at the same shift, median of 1 runs |
| ariane136.tb_pg.cand.s4.f2 | programs | [0, 2] | 1.0291 | 1.0291 | - | the tool's replicate at the same shift, median of 1 runs |
| ariane136.tb_pg.cand.s5.f2 | programs | [1, 1] | +inf | 1.0275 | setup | the tool's replicate at the same shift, median of 1 runs |
| ariane136.tb_pg.cand.s6.f2 | programs | [-1, -1] | 1.0256 | 1.0256 | - | the tool's replicate at the same shift, median of 1 runs |
| ariane136.ext_dp.tb.s1.f2 | DREAMPlace | [2, 0] | 1.0383 | 1.0383 | - | the tool's replicate at the same shift, median of 1 runs |
| ariane136.ext_dp.tb.s2.f2 | DREAMPlace | [-2, 0] | +inf | 1.0394 | setup | the tool's replicate at the same shift, median of 1 runs |
| ariane136.ext_dp.tb.s3.f2 | DREAMPlace | [0, -1] | +inf | 1.0369 | setup | the tool's replicate at the same shift, median of 1 runs |
| ariane136.ext_dp.tb.s4.f2 | DREAMPlace | [0, 2] | 1.0381 | 1.0381 | - | the tool's replicate at the same shift, median of 1 runs |
| ariane136.ext_dp.tb.s5.f2 | DREAMPlace | [1, 1] | +inf | +inf | flow | - |
| ariane136.ext_dp.tb.s6.f2 | DREAMPlace | [-1, -1] | +inf | 1.0403 | setup | the tool's replicate at the same shift, median of 1 runs |
| ariane136.tb.cand.s1.f2 | HeurBridge (local search) | [2, 0] | 0.9763 | 0.9763 | - | the tool's replicate at the same shift, median of 1 runs |
| ariane136.tb.cand.s2.f2 | HeurBridge (local search) | [-2, 0] | 0.9759 | 0.9759 | - | the tool's replicate at the same shift, median of 1 runs |
| ariane136.tb.cand.s3.f2 | HeurBridge (local search) | [0, -1] | 0.9763 | 0.9763 | - | the tool's replicate at the same shift, median of 1 runs |
| ariane136.tb.cand.s4.f2 | HeurBridge (local search) | [0, 2] | 0.9764 | 0.9764 | - | the tool's replicate at the same shift, median of 1 runs |
| ariane136.tb.cand.s5.f2 | HeurBridge (local search) | [1, 1] | 0.9753 | 0.9753 | - | the tool's replicate at the same shift, median of 1 runs |
| ariane136.tb.cand.s6.f2 | HeurBridge (local search) | [-1, -1] | 0.9759 | 0.9759 | - | the tool's replicate at the same shift, median of 1 runs |
| ariane136.tb.ref.s1.f2 | tool | [2, 0] | 1.0203 | 1.0203 | - | the tool's replicate at the same shift, median of 1 runs |
| ariane136.tb.ref.s2.f2 | tool | [-2, 0] | 1.0053 | 1.0053 | - | the tool's replicate at the same shift, median of 1 runs |
| ariane136.tb.ref.s3.f2 | tool | [0, -1] | 1.0032 | 1.0032 | - | the tool's replicate at the same shift, median of 1 runs |
| ariane136.tb.ref.s4.f2 | tool | [0, 2] | 1.0042 | 1.0042 | - | the tool's replicate at the same shift, median of 1 runs |
| ariane136.tb.ref.s5.f2 | tool | [1, 1] | 1.0047 | 1.0047 | - | the tool's replicate at the same shift, median of 1 runs |
| ariane136.tb.ref.s6.f2 | tool | [-1, -1] | 1.0055 | 1.0055 | - | the tool's replicate at the same shift, median of 1 runs |

Sources: runs/remote/tp_b/runs/seed_orfs/ariane136/evals_tb_pg.jsonl, runs/remote/tw_b/runs/seed_orfs/ariane136/evals_ext_dp.jsonl, runs/remote/tb_ariane136/runs/seed_orfs/ariane136/evals_tb.jsonl, runs/remote/seedB_orfs7_ariane136/runs/seed_orfs/ariane136/evals_f2.jsonl.

