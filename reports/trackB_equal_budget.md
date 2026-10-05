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

