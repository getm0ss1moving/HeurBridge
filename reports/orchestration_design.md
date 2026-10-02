# Tool orchestration by evolved programs: design note (DRAFT for decision D9, option a)

| Field | Value |
|---|---|
| Report | orchestration_design |
| Date | 2026-10-03 |
| Status | **design draft, awaiting the owner's decision D9** (reports/next_phase_decisions.md); nothing runs |
| Track | A (DREAMPlace mixed-size as the tool; f1 and J unchanged) |

## 1 Why

On IBM, none of the HeurBridge methods tried beats the tool's best of k at equal compute, while the way the tool is
run moves J a lot (reports/beat_tool_track_a.md, Sections 3-9, exploratory):

- one run at target density 0.6 instead of 0.9: J -0.0288 on four designs (Section 7);
- the effect depends on the design: at 0.7 on 13 designs, lower in 67 of 104 cases, losses on four designs (Section 7);
- two densities instead of two seeds at the same number of runs: lower in 66 of 104 cases, higher in 16 (Section 7).

So the open question with a cost claim is: **given a design and a budget of k tool runs, which runs should be made?**
A design-dependent effect is what a per-design policy can exploit and a fixed configuration cannot.

## 2 What would be evolved

A program `plan(view, k) -> [config_1, ..., config_k]` that sees the design's features (sizes, utilization, macro
area share, net-degree statistics, pin counts; never its identity, as in T5: scripts/run_evolution.py:21-23) and
returns k tool configurations (target density, seed, start mode: random or from a layout, iterations). The k runs are
made, the best is kept by f1 with the selection seed, and the endpoint is the median J over fresh seeds, as in RL#1-3.

## 3 Reused from T5 (exists)

Proposers and the population (heurbridge/evolve/engine.py, population.py), the program sandbox and its V0
certificate (heurbridge/evolve/sandbox.py), the LLM budget ledger and the no-LLM control arm (`--llm perturb`:
parameter perturbation at the same evaluation budget), kept program sources, and the held-out endpoint
(reports/t5_demo_preregistration.md). New: the program's output contract (a list of configurations instead of a
layout) and the evaluator (k tool runs plus selection instead of bridge plus guard).

## 4 How it would be judged (to be pre-registered before any held-out run)

- **Training designs:** IBM (the exploration family). **Held out:** ISPD2005 (after RL#1-3, which use it) or a split
  of IBM fixed in advance.
- **Comparators at the same number of tool runs k:** (i) k seeds at 0.9 (the baseline configuration); (ii) k seeds at
  the best fixed density chosen on the training designs; (iii) a fixed two-density portfolio (RL#3's kind). The claim
  that matters is (ii) and (iii): a per-design policy must beat the best fixed setting, not only the default.
- **Cost:** tool runs and f1 runs counted per arm; the program's own run time reported (seconds).
- **Controls:** the no-LLM perturbation arm at the same evaluation budget (T5's control).

## 5 Compute (estimate from the exploration's run times)

IBM tool run 15-50 s and f1 run 8-13 s (reports/beat_tool_track_a.md, Section 7). With k = 2 and 4 training
designs, one program costs about 8 tool runs and 8 f1 runs, about 5-7 minutes on one GPU; 10 generations of 4
children per arm about 4-5 hours, two arms (LLM, control) on two GPUs in parallel.

## 6 Risks

- **Novelty:** close to automated parameter tuning of DREAMPlace for macro placement (e.g. AutoDMP, ISPD 2023, which
  tunes DREAMPlace's parameters per design by Bayesian optimization). The difference to make good on: programs that
  transfer to unseen designs without per-design search (the cost claim), and the LLM against the control arm.
- **f1's heavy tail:** some layouts blow up under other f1 seeds (ibm08; ibm09 at 0.7; ibm12 after a second pass at
  0.6), which a one-seed selection cannot see; the endpoint's fresh seeds expose it, and the evaluator could add a
  second selection seed at extra cost.
- **The density effect may not transfer:** RL#2 and RL#3 on ISPD2005 answer this first; if both fail, this design
  should be revisited before any run.
