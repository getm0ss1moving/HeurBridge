# Track B: equal search budget, HeurBridge's programs vs DREAMPlace as the starts of the same local search

| Field | Value |
|---|---|
| Report | trackB_equal_budget |
| Pre-registration | reports/trackB_equal_budget_preregistration.md |
| Status of the claim | per design below |

## bp_fe_top (EB#1)

Recorded 2026-10-06T01:10:32. **FAILED**: HeurBridge (programs + local search) lower than DREAMPlace + the same local search, exact one-sided rank-sum permutation p = 0.1277 against alpha_j = 0.025.

Reported, not tested: median J before the gates: HeurBridge 0.9051, DREAMPlace+LS 0.9427, DREAMPlace 1.0734, tool 1.0009; DREAMPlace+LS lower than DREAMPlace under the same gates (what the search adds to DREAMPlace): p = 0.007576. DREAMPlace+LS's flow runs: 45 at f1 and 4 at f2 in its search (8.4 flow-run hours), after DREAMPlace's selection (16 runs, 2.3 flow-run hours).

| replicate | arm | shift | J (gated, D11 b; tool: before gates) | J before gates | gates failed |
|---|---|---|---|---|---|
| bp_fe_top.tb.cand.s1.f2 | HeurBridge | [2, 0] | 0.9080 | 0.9080 | - |
| bp_fe_top.tb.cand.s2.f2 | HeurBridge | [-2, 0] | 0.9023 | 0.9023 | - |
| bp_fe_top.tb.cand.s3.f2 | HeurBridge | [0, -1] | 0.8811 | 0.8811 | - |
| bp_fe_top.tb.cand.s4.f2 | HeurBridge | [0, 2] | 0.9747 | 0.9747 | - |
| bp_fe_top.tb.cand.s5.f2 | HeurBridge | [1, 1] | +inf | 0.9183 | hold |
| bp_fe_top.tb.cand.s6.f2 | HeurBridge | [-1, -1] | 0.9017 | 0.9017 | - |
| bp_fe_top.dpls.tb.s1.f2 | DREAMPlace+LS | [2, 0] | +inf | 0.9343 | hold |
| bp_fe_top.dpls.tb.s2.f2 | DREAMPlace+LS | [-2, 0] | 0.9511 | 0.9511 | - |
| bp_fe_top.dpls.tb.s3.f2 | DREAMPlace+LS | [0, -1] | 0.9287 | 0.9287 | - |
| bp_fe_top.dpls.tb.s4.f2 | DREAMPlace+LS | [0, 2] | 0.9255 | 0.9255 | - |
| bp_fe_top.dpls.tb.s5.f2 | DREAMPlace+LS | [1, 1] | 0.9666 | 0.9666 | - |
| bp_fe_top.dpls.tb.s6.f2 | DREAMPlace+LS | [-1, -1] | 0.9520 | 0.9520 | - |
| bp_fe_top.ext_dp.tb.s1.f2 | DREAMPlace | [2, 0] | +inf | 1.5729 | setup |
| bp_fe_top.ext_dp.tb.s2.f2 | DREAMPlace | [-2, 0] | +inf | 1.0595 | setup |
| bp_fe_top.ext_dp.tb.s3.f2 | DREAMPlace | [0, -1] | +inf | 1.1841 | setup |
| bp_fe_top.ext_dp.tb.s4.f2 | DREAMPlace | [0, 2] | +inf | 0.9562 | setup |
| bp_fe_top.ext_dp.tb.s5.f2 | DREAMPlace | [1, 1] | +inf | 1.0873 | setup |
| bp_fe_top.ext_dp.tb.s6.f2 | DREAMPlace | [-1, -1] | +inf | 0.9352 | setup |
| bp_fe_top.tb.ref.s1.f2 | tool | [2, 0] | 0.9599 | 0.9599 | - |
| bp_fe_top.tb.ref.s2.f2 | tool | [-2, 0] | 1.0562 | 1.0562 | - |
| bp_fe_top.tb.ref.s3.f2 | tool | [0, -1] | 1.0759 | 1.0759 | - |
| bp_fe_top.tb.ref.s4.f2 | tool | [0, 2] | 0.9985 | 0.9985 | - |
| bp_fe_top.tb.ref.s5.f2 | tool | [1, 1] | 1.0002 | 1.0002 | - |
| bp_fe_top.tb.ref.s6.f2 | tool | [-1, -1] | 1.0015 | 1.0015 | - |

Sources: runs/remote/tb_bp_fe_top/runs/seed_orfs/bp_fe_top/evals_tb.jsonl, runs/remote/dpls_a/runs/seed_orfs/bp_fe_top/evals_dpls_f2.jsonl, runs/remote/tw_a/runs/seed_orfs/bp_fe_top/evals_ext_dp.jsonl, runs/remote/seedB_orfs7_bp_fe_top/runs/seed_orfs/bp_fe_top/evals_f2.jsonl.

## bp_be_top (EB#2)

Recorded 2026-10-06T03:34:55. **FAILED**: HeurBridge (programs + local search) lower than DREAMPlace + the same local search, exact one-sided rank-sum permutation p = 0.7911 against alpha_j = 0.0125.

Reported, not tested: median J before the gates: HeurBridge 1.0167, DREAMPlace+LS 0.9559, DREAMPlace 0.9605, tool 1.1077; DREAMPlace+LS lower than DREAMPlace under the same gates (what the search adds to DREAMPlace): p = 0.05303. DREAMPlace+LS's flow runs: 45 at f1 and 1 at f2 in its search (8.7 flow-run hours), after DREAMPlace's selection (16 runs, 4.2 flow-run hours).

| replicate | arm | shift | J (gated, D11 b; tool: before gates) | J before gates | gates failed |
|---|---|---|---|---|---|
| bp_be_top.tb.cand.s1.f2 | HeurBridge | [2, 0] | 1.0401 | 1.0401 | - |
| bp_be_top.tb.cand.s2.f2 | HeurBridge | [-2, 0] | 0.9810 | 0.9810 | - |
| bp_be_top.tb.cand.s3.f2 | HeurBridge | [0, -1] | 0.9713 | 0.9713 | - |
| bp_be_top.tb.cand.s4.f2 | HeurBridge | [0, 2] | 1.0163 | 1.0163 | - |
| bp_be_top.tb.cand.s5.f2 | HeurBridge | [1, 1] | 1.0171 | 1.0171 | - |
| bp_be_top.tb.cand.s6.f2 | HeurBridge | [-1, -1] | 1.0192 | 1.0192 | - |
| bp_be_top.dpls.tb.s1.f2 | DREAMPlace+LS | [2, 0] | 0.9784 | 0.9784 | - |
| bp_be_top.dpls.tb.s2.f2 | DREAMPlace+LS | [-2, 0] | +inf | +inf | flow |
| bp_be_top.dpls.tb.s3.f2 | DREAMPlace+LS | [0, -1] | 0.9566 | 0.9566 | - |
| bp_be_top.dpls.tb.s4.f2 | DREAMPlace+LS | [0, 2] | +inf | 0.9551 | hold |
| bp_be_top.dpls.tb.s5.f2 | DREAMPlace+LS | [1, 1] | 0.9450 | 0.9450 | - |
| bp_be_top.dpls.tb.s6.f2 | DREAMPlace+LS | [-1, -1] | 0.8971 | 0.8971 | - |
| bp_be_top.ext_dp.tb.s1.f2 | DREAMPlace | [2, 0] | 0.9721 | 0.9721 | - |
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

Sources: runs/remote/tb_bp_be_top/runs/seed_orfs/bp_be_top/evals_tb.jsonl, runs/remote/dpls_a/runs/seed_orfs/bp_be_top/evals_dpls_f2.jsonl, runs/remote/tw_a/runs/seed_orfs/bp_be_top/evals_ext_dp.jsonl, runs/remote/seedB_orfs7_bp_be_top/runs/seed_orfs/bp_be_top/evals_f2.jsonl.

## ariane136 (EB#3)

Recorded 2026-10-07T15:34:22. **PASSED**: HeurBridge (programs + local search) lower than DREAMPlace + the same local search, exact one-sided rank-sum permutation p = 0.001082 against alpha_j = 0.00625.

Reported, not tested: median J before the gates: HeurBridge 0.9761, DREAMPlace+LS 1.0369, DREAMPlace 1.0388, tool 1.0050; DREAMPlace+LS lower than DREAMPlace under the same gates (what the search adds to DREAMPlace): p = 0.3485. DREAMPlace+LS's flow runs: 48 at f1 and 4 at f2 in its search (34.5 flow-run hours), after DREAMPlace's selection (15 runs, 18.6 flow-run hours).

| replicate | arm | shift | J (gated, D11 b; tool: before gates) | J before gates | gates failed |
|---|---|---|---|---|---|
| ariane136.tb.cand.s1.f2 | HeurBridge | [2, 0] | 0.9763 | 0.9763 | - |
| ariane136.tb.cand.s2.f2 | HeurBridge | [-2, 0] | 0.9759 | 0.9759 | - |
| ariane136.tb.cand.s3.f2 | HeurBridge | [0, -1] | 0.9763 | 0.9763 | - |
| ariane136.tb.cand.s4.f2 | HeurBridge | [0, 2] | 0.9764 | 0.9764 | - |
| ariane136.tb.cand.s5.f2 | HeurBridge | [1, 1] | 0.9753 | 0.9753 | - |
| ariane136.tb.cand.s6.f2 | HeurBridge | [-1, -1] | 0.9759 | 0.9759 | - |
| ariane136.dpls.tb.s1.f2 | DREAMPlace+LS | [2, 0] | 1.0366 | 1.0366 | - |
| ariane136.dpls.tb.s2.f2 | DREAMPlace+LS | [-2, 0] | +inf | 1.0373 | setup |
| ariane136.dpls.tb.s3.f2 | DREAMPlace+LS | [0, -1] | +inf | 1.0379 | setup |
| ariane136.dpls.tb.s4.f2 | DREAMPlace+LS | [0, 2] | 1.0363 | 1.0363 | - |
| ariane136.dpls.tb.s5.f2 | DREAMPlace+LS | [1, 1] | +inf | 1.0373 | setup |
| ariane136.dpls.tb.s6.f2 | DREAMPlace+LS | [-1, -1] | +inf | 1.0357 | setup |
| ariane136.ext_dp.tb.s1.f2 | DREAMPlace | [2, 0] | 1.0383 | 1.0383 | - |
| ariane136.ext_dp.tb.s2.f2 | DREAMPlace | [-2, 0] | +inf | 1.0394 | setup |
| ariane136.ext_dp.tb.s3.f2 | DREAMPlace | [0, -1] | +inf | 1.0369 | setup |
| ariane136.ext_dp.tb.s4.f2 | DREAMPlace | [0, 2] | 1.0381 | 1.0381 | - |
| ariane136.ext_dp.tb.s5.f2 | DREAMPlace | [1, 1] | +inf | +inf | flow |
| ariane136.ext_dp.tb.s6.f2 | DREAMPlace | [-1, -1] | +inf | 1.0403 | setup |
| ariane136.tb.ref.s1.f2 | tool | [2, 0] | 1.0203 | 1.0203 | - |
| ariane136.tb.ref.s2.f2 | tool | [-2, 0] | 1.0053 | 1.0053 | - |
| ariane136.tb.ref.s3.f2 | tool | [0, -1] | 1.0032 | 1.0032 | - |
| ariane136.tb.ref.s4.f2 | tool | [0, 2] | 1.0042 | 1.0042 | - |
| ariane136.tb.ref.s5.f2 | tool | [1, 1] | 1.0047 | 1.0047 | - |
| ariane136.tb.ref.s6.f2 | tool | [-1, -1] | 1.0055 | 1.0055 | - |

Sources: runs/remote/tb_ariane136/runs/seed_orfs/ariane136/evals_tb.jsonl, runs/remote/dpls_b/runs/seed_orfs/ariane136/evals_dpls_f2.jsonl, runs/remote/tw_b/runs/seed_orfs/ariane136/evals_ext_dp.jsonl, runs/remote/seedB_orfs7_ariane136/runs/seed_orfs/ariane136/evals_f2.jsonl.

