# E0 pre-registration (task T4, gate G0')

Registered 2026-09-28 16:06 before any confirmatory E0 data exist. Bridge checkpoint sha256 `f95bdde8485316349a1a47b8b1e8115018085f518419f46c903c65f773a525a5`
(the final promoted T3.7 Algorithm R checkpoint); frozen generator `checkpoints/pretrain_small/pretrain_small.pt` (T3.4 pretraining).

Go decision based on the demo `reports/E0_demo_spec.md, reports/E0_demo_eq.md` (designs outside this confirmatory set).

## Question

Does the co-trained bridge, as the evaluation partner of a heuristic's macro layout, give a lower final cost than
the partners that do not learn from the heuristics (memetic search, repertoire repair, the frozen generator, no
partner), at the same wall-clock per call?

## Protocol (task list T4)

- Sources: the 16 seed programs (T2.2) x seeds 0-4 on every design; a source is kept when the program runs and
  its layout projects legally (P_M).
- Partners: none (the raw layout), memetic (SA on f0), repertoire (checked repair on f0), frozen generator (partial
  noising, best by f0), co-trained bridge (K = 20 Euler steps, guard over alpha in 0 / 0.25 / 0.5 / 1). Memetic and
  repertoire get the bridge's median wall-clock per call (measured first, including its guard). Control:
  random_guard = the bridge's guard along a random displacement of the bridge's typical length.
- Every partner's output -> P_M -> final cost J (Track A: DREAMPlace f1 with the macros fixed, J relative to the
  M1 baseline of the Track-A seeding campaign; a failure counts as +inf).
- Each design runs whole on one server (225: RTX 3090; 231: RTX 4090): pairs never cross GPU types.

## Tests

| ledger entry | role | designs | guarded partners | alpha_j |
|---|---|---|---|---|
| E0#1 | primary | adaptec1, adaptec2, adaptec3, adaptec4, bigblue1, bigblue3, bigblue4 | bridge only | 0.02500 |
| E0#2 | secondary_equal_guard | adaptec1, adaptec2, adaptec3, adaptec4, bigblue1, bigblue3, bigblue4 | all partners | 0.01250 |
| E0#3 | secondary_ibm_heldout | ibm08, ibm12 | bridge only | 0.00625 |

Test: paired one-sided Wilcoxon, co-trained < partner; Holm over none/memetic/repertoire/frozen_gen. Gate: G0' passes iff Holm-adjusted p < 0.01 for memetic AND repertoire; the ledger's alpha_j of E0#1 (0.025) is above 0.01, so the gate threshold binds.
Also reported, not tested: portfolio J (best program per design), Kendall tau of each partner's program ranking vs
raw, per-metric deltas, the random-direction control (co-trained vs random_guard, one-sided Wilcoxon).

## Decision

- G0' passes (E0#1): continue to T5 (LLM evolution, deepseek-flash).
- G0' fails: stop and report; the N1-N2 novelty claims are withdrawn and the user decides the repositioning
  (task list T4). The secondary tests do not change this decision; they qualify it (whether a win survives an equal
  guard, whether it comes from the learned direction, whether it holds on the training family's held-out designs).
