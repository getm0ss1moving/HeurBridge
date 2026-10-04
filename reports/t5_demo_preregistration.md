# T5 demo: pre-registration (DRAFT, awaiting the owner's approval)

| Field | Value |
|---|---|
| Report | t5_demo_preregistration |
| Date | 2026-10-02 |
| Status | **Draft, awaiting approval.** Nothing in this document has been run with the real LLM; no data exist. |
| Track | A (IBM, DREAMPlace f1 as the final cost) |
| Code | scripts/run_evolution.py, scripts/eval_t5_portfolio.py, scripts/t5_demo_decision.py, scripts/server/t5_demo.sh, heurbridge/evolve/ (git 3bfbd95 or later) |
| Feeds gate | none (exploratory demo). It decides only whether the full T5 campaign is proposed (Section 7). |
| alpha-ledger entry | none for the demo (exploratory, no promotion). The full campaign's reservations are in Section 7. |
| Status of any result | exploratory demo (no claim) |

Every number below has a source. A number this document decides itself (a demo choice) is marked "(this
document)" and was fixed before any data.

## 1 Question

Does LLM-driven evolution of macro heuristics, scored by refinability (the post-bridge cost), give a better
post-bridge portfolio on designs the evolution never saw than (a) the seed programs and (b) the same loop without
an LLM at the same evaluation budget? And does the real LLM produce valid programs at a usable rate and cost?

The demo comes first by the project's workflow: each experiment runs as a demo on 225 first, then at full capacity if the effect is good (owner's decision of 28 Sep, reports/PROGRESS.md:241-242).

## 2 Fixed elements

| Element | Value | Source |
|---|---|---|
| Final cost | Track-A J: rWL and OF terms only (weights 0.30, 0.15), normalized to the design's M1 baseline; baseline J = 0.45 by construction, lower is better | heurbridge/pipeline/evaluators.py:20, heurbridge/eval/cost.py:26, reports/T2_trackA_ibm_dreamplace.md:23 |
| Evaluator | DREAMPlace f1 (GP + LG, macros fixed), J against the M1 baseline of the seeding campaign `runs/seed_trackA_dp`, exactly as E0 | scripts/run_evolution.py:97 (`--guard dp`), scripts/run_e0.py:114-129 |
| Bridge | the frozen E0 checkpoint, sha256 f95bdde8...a5, 9,087,346 bytes; not retrained during the demo | checkpoints/bridge_v1_e0_frozen/MANIFEST.json:4-5 |
| Guard | alpha in {0, 0.25, 0.5, 1}, each candidate projected by P_M and scored; alpha = 0 is the raw layout; K = 20 Euler steps | heurbridge/bridge/sample.py:24, heurbridge/bridge/sample.py:85, reports/E0_preregistration.md:19 |
| Seed programs | the 16 program versions M2-M7 (M1 is the tool itself) | reports/PROGRESS.md:157, heurbridge/heuristics/macro/registry.py:62 |
| LLM | deepseek-flash, through the budget ledger with a hard stop at 110 % of the scope's budget | heurbridge/evolve/llm.py:33, heurbridge/evolve/llm.py:94, heurbridge/evolve/llm.py:126 |
| Proposer (LLM arm) | `heurbridge`: parent code + RLCE evidence + skill document v0 | heurbridge/evolve/engine.py:81, heurbridge/evolve/prompts/skill_v0.md |
| Fitness | refinability F = portfolio marginal gain - lambda_B x standalone post-bridge cost - lambda_t x max(0, runtime - 30 s); lambda_B = 0.2, lambda_t = 0.01 | heurbridge/evolve/fitness.py:3-7, heurbridge/evolve/fitness.py:24-26, HEURBRIDGE_TASKS.md:445 |
| Population | MAP-Elites per island, 4 islands, migration every 5 generations, portfolio q = 8 by greedy facility location | heurbridge/evolve/population.py:50, HEURBRIDGE_TASKS.md:454-455 |
| Sandbox | AST allow-list, separate interpreter with CPU 60 s and memory 4 GB limits, determinism, permutation equivariance (MR1) | heurbridge/evolve/sandbox.py:1-24, heurbridge/evolve/prompts.py:27 |
| Identity rule | programs never see the design's name and a program that names it is rejected (no per-design branching) | scripts/run_evolution.py:125, scripts/run_evolution.py:227 |
| Statistics | paired one-sided Wilcoxon signed-rank; a failure is +inf and never dropped | heurbridge/stats/paired.py:3-6, heurbridge/stats/paired.py:41-50 |

## 3 Demo choices (this document, fixed before any data)

| Choice | Value | Why |
|---|---|---|
| D_evo (fitness designs) | ibm01, ibm03, 2 seeds each | the bridge's training designs (reports/T3_algorithmR_trackA.md:19) with the shortest f1 runs among them, 10.3 s and 9.5 s (reports/T2_trackA_ibm_dreamplace.md:27, :29). The spec's 6 designs x 3 seeds (HEURBRIDGE_TASKS.md:444) is reduced for the demo. |
| V (acceptance designs) | ibm04, ibm06, 3 seeds each | the bridge's validation designs, never in its training (reports/T3_algorithmR_trackA.md:19); never used by the evolution |
| T (report-only designs) | ibm08, ibm12, 3 seeds each | held out from the bridge's training and model selection (reports/E0_preregistration.md:32); never used for any decision |
| Arms | HB: `--proposer heurbridge --llm deepseek`; CTRL: `--proposer heurbridge --llm perturb` (no LLM: every decimal constant of the parent's EVOLVE block rescaled by its own factor in [0.7, 1.3]) | CTRL isolates what the LLM adds at the same evaluation budget (scripts/run_evolution.py:61) |
| Generations x parents x children | 4 x 4 x 2 = 32 children per arm | the spec's 8 x 4 per generation (HEURBRIDGE_TASKS.md:456), reduced for the demo |
| LLM budget | 100 calls in scope M/t5demo (hard stop at 110) | each child needs one call, plus at most one retry on a malformed reply (heurbridge/evolve/engine.py:63-75) |
| Not in the demo | promotion to f2 (Track A has no f2), bridge co-training and fitness re-anchoring, the T5.5 baseline engines, the T5.6 knowledge loop | HEURBRIDGE_TASKS.md:446, :450, :470, :480 |

## 4 Endpoint and test

- **Unit:** a (design, seed) pair of V: 2 designs x 3 seeds = 6 units (this document).
- **Portfolio J of a unit:** the minimum, over the portfolio's programs, of the guarded post-bridge DREAMPlace-f1 J
  of the program's layout on that unit; a failed program counts +inf (scripts/eval_t5_portfolio.py:56).
- **Portfolios:** each arm's final portfolio and the seed portfolio, each chosen by the population's own rule on
  D_evo (q = 8; scripts/eval_t5_portfolio.py:45). The seed programs stay candidates of every arm's portfolio.
- **Primary comparison:** HB portfolio vs the seed portfolio on V. **Secondary:** HB vs CTRL on V; CTRL vs seed
  reported. T is reported with the same table and never used for a decision.
- **Test:** paired one-sided Wilcoxon (HB lower), Holm over HB's two comparisons, nominal and adjusted p reported.
  With 6 units the smallest attainable one-sided p is 1/64 = 0.016 (this document), so the demo cannot produce a
  confirmatory result by design; the decision rule below uses directions and means, not p.

## 5 Decision rule (fixed before any data)

The full T5 campaign is proposed to the owner if and only if all five hold:

| Rule | Condition | Measured from |
|---|---|---|
| R1 validity | at least 50 % of the HB arm's children are certified and evaluated without failure | events.jsonl kinds (scripts/run_evolution.py summary) |
| R2 progress | the HB final portfolio's mean post-bridge J on D_evo is below the seed portfolio's | population files (B per program) |
| R3 transfer | on V, the HB portfolio's mean J is below the seed portfolio's, and HB is lower on at least 4 of the 6 units | eval_t5_portfolio.py summary.json |
| R4 LLM value | on V, the HB portfolio's mean J is below the CTRL portfolio's | eval_t5_portfolio.py summary.json |
| R5 cost and safety | LLM calls within the budget; no sandbox escape; every failure named | llm ledger, events.jsonl |

- All five hold: propose the full campaign (Section 7) with these numbers as the evidence.
- R1 fails: fix prompts or parsing and repeat the demo (owner approval); no full campaign.
- R2 holds but R3 or R4 fails: report a negative demo ("no transfer" or "no value beyond parameter perturbation");
  the full campaign is not proposed as designed; options go to reports/next_phase_decisions.md.
- **Adoption rule (no harm):** evolved programs are used downstream only if R3 holds; otherwise the seed portfolio
  stays, so the delivered portfolio is never worse than the seeds on V.

## 6 What protects against a negative effect, and what does not

What the design guarantees:

1. **The seeds are never lost.** The 16 seed programs are in the population from the start
   (heurbridge/evolve/engine.py:194) and every portfolio is chosen over all programs, seeds included.
2. **The guard cannot make a layout worse under its evaluator.** alpha = 0, the raw layout, is always a candidate
   and the argmin is kept (heurbridge/bridge/sample.py:85-97).
3. **Selection, acceptance and report use different designs.** D_evo for fitness, V for the adoption rule, T for
   reporting only (Section 3).
4. **No-harm adoption.** Evolved programs replace the seeds only when they win on V (Section 5).
5. **The LLM's contribution is measured, not assumed.** The CTRL arm runs the same loop, budget and evaluator
   without an LLM; R4 requires HB to beat it.
6. **No per-design shortcuts.** The design's identity is hidden and naming it is rejected (Section 2).
7. **Unsafe or broken code cannot reach the evaluator.** Static checks, resource limits, determinism and MR1
   (heurbridge/evolve/sandbox.py:1-24); malformed replies cost one retry and are then logged and discarded
   (heurbridge/evolve/engine.py:63-75).
8. **Spending is capped.** The ledger stops calls at 110 % of the budget (heurbridge/evolve/llm.py:126).

What it does not guarantee: that the LLM improves anything; that a V improvement also holds on T (T is reported to
show exactly this); or any confirmatory claim (6 units, Section 4).

## 7 Full campaign (outline for approval after the demo)

- Scope per the task list: one campaign per family split at the macro stage, with ledgers
  (HEURBRIDGE_TASKS.md:482); splits leave one family out (configs/families.yaml:22-25).
- Gate G2: H1 significant on at least 2 of 3 held-out folds (HEURBRIDGE_TASKS.md:567). H1's exact wording is in the
  proposal, which is not in the repo: not documented in the repo.
- Proposed test per fold: HB portfolio vs the best T5.5 baseline engine's portfolio (HEURBRIDGE_TASKS.md:470) on the
  test family's (design, seed) units, paired one-sided Wilcoxon; reservations T5#1-#3 made before any campaign data,
  alpha_j = 0.025, 0.0125, 0.00625 (alpha = 0.05 per campaign: HEURBRIDGE_TASKS.md:541).
- **Blockers (owner decisions):** the bridge is trained on IBM only (reports/T3_algorithmR_trackA.md:19), so the
  fold that tests on IBM needs a bridge trained without IBM; the fold that tests on orfs_cpu needs a Track-B bridge,
  and Track B has heuristics only so far (reports/PROGRESS.md:162). Until these are settled, at most one of the three
  folds (test ispd05) can run as specified.

## 8 Compute and cost estimate

- One (program, design, seed) evaluation runs the program, the bridge, and four DREAMPlace f1 runs of 8.7-10.9 s on
  these designs (reports/T2_trackA_ibm_dreamplace.md:27-37): roughly 40-60 s (estimate, not measured).
- Per arm: (16 seeds + 32 children) x 4 D_evo units, about 2.7 GPU-hours, plus RLCE diagnoses for the HB arm
  (counterfactual splices re-run the guard). The two arms run in parallel on two GPUs.
- Endpoint: at most 32 distinct programs x 6 units on V, and the same on T: about 2.7 GPU-hours each.
- LLM: at most 110 calls; the price per call is not documented in the repo (the ledger records tokens).

## 9 Runbook and checks done before submission

- Exact commands: HANDOFF.md, section "T5 demo runbook"; every job is a mode of scripts/server/t5_demo.sh, and the
  decision rule of Section 5 is applied by scripts/t5_demo_decision.py (no judgement step).
- Mock smoke test on 225 (job `t5_smoke_mock`, 2026-10-02, exit code 0): 2 seed programs and 1 child on ibm01 with
  the DREAMPlace guard in 373 s, then the endpoint on one ibm04 unit; the decision script read its outputs.
  Infrastructure check only; its numbers mean nothing.
- Known limitation seen in the smoke test: RLCE's reachability radius was 0.0 on ibm01 (no macro ends within one
  site of its elite after the frozen bridge), so RLCE labels every macro structural and its evidence reduces to the
  decisive group (heurbridge/evolve/rlce.py:66-75). The demo runs with it as is; this is recorded, not tuned.
