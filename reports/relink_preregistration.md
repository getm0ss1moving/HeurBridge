# Relinking two tool runs vs the tool's best of four: pre-registration (confirmatory, Track A, ISPD2005)

| Field | Value |
|---|---|
| Report | relink_preregistration |
| Date | 2026-10-03 |
| Status | registered by the agent under the owner's delegation of 3 Oct ("you can decide which decision have high priority"); fixed before any ISPD2005 run of this protocol |
| Track | A: f1 = DREAMPlace GP + LG with the macros fixed; J against the ISPD2005 seeding campaign's M1 baseline (0.45 by construction) |
| Family | ISPD2005, all 8 designs; untouched by the exploration that motivated this test (IBM only: reports/beat_tool_track_a.md) |
| alpha-ledger | campaign `RL`, entry RL#1, alpha_1 = 0.025 (alpha = 0.05 per campaign: HEURBRIDGE_TASKS.md:541), reserved before the first run |
| Code | scripts/tool_runs.py, scripts/relink_eval.py, scripts/relink_confirm.py, as committed together with this document (later commits may fix bugs, not change the procedure) |

## 1 Question

At equal or lower compute, does relinking two runs of the tool (DREAMPlace mixed-size) give a lower Track-A J than
the tool's best of four runs? The owner's aim is a macro placer that beats the tool on output and on cost (3 Oct).

## 2 Procedure (fixed now)

- **Tool runs:** per design, DREAMPlace mixed-size with seeds 0-7, each legalized by P_M (scripts/tool_runs.py;
  ISPD2005 loaded with every macro movable, as the seeding campaign: scripts/tool_refine_eval.py:42-53).
- **Selection seed and endpoint:** every arm picks among its layouts by f1 with seed 0; every picked layout is
  judged by the median J over fresh f1 seeds 1, 2, 3. The tool's own baseline is a median over three f1 seeds
  (configs/cost.yaml:11), and a single DREAMPlace run can blow the overflow term up (reports/beat_tool_track_a.md,
  Notes).
- **Units:** (design, s) for s = 0-7: 64 paired units, one confirmatory job per design (`rlc_*`); the analysis refuses a
  second source for a design (scripts/relink_confirm.py).
- **Relink arm (the method):** partner p = (s + 1) mod 8; the candidates P_M(T_s + a (T_p' - T_s)) for a in
  {0.25, 0.5, 0.75}, T_p' = T_p with its interchangeable macros matched to T_s (bridge.data.match_symmetric); the pick is
  the best of {T_s, T_p, candidates} by the selection seed (scripts/relink_eval.py). Cost: two tool runs and five f1
  runs. The matching is exact for groups of up to 2,000 interchangeable macros and exact within the blocks of
  recursive median splits above that (`--match-block 2000`): the largest groups are 14,321 macros on bigblue2 and
  6,150 on bigblue4 (counted from the .nodes files), too large for one dense assignment; every other ISPD2005 group
  and every IBM group has at most 731.
- **Best-of-4 arm (the comparator, more compute):** the best of T_s, T_(s+1), T_(s+2), T_(s+3) (mod 8) by the
  selection seed. Cost: four tool runs and four f1 runs.
- **Failures:** a failed tool run, P_M or f1 is a +inf candidate: never picked over a finite candidate; an arm whose
  candidates all fail is +inf. Each failure is listed by name (scripts/relink_eval.py writes them per row).

## 3 Test and decision

- **Primary test:** paired one-sided Wilcoxon signed-rank on the 64 differences relink - best-of-4 (relink lower),
  with +inf kept (heurbridge/stats/paired.py:41-50), at alpha_1 = 0.025 (RL#1).
- **Pass:** p <= 0.025. Then the confirmed claim is: on the held-out ISPD2005 family, relinking two tool runs gives a
  lower J than the tool's best of four runs while using fewer runs (two tool runs and five f1 runs against four and
  four).
- **Fail:** reported as a negative result; no claim.
- **Reported, not tested:** per-design means of every arm (single tool run, best of 2, 3, 4, relink); the mean J of
  the relink arm with a bootstrap 95 % interval against 0.45; measured wall-clock per arm (tool runs and selection f1
  runs, plus the relink candidates' P_M and f1 runs; the fresh-seed endpoint runs belong to neither arm).
- **Once:** `relink_confirm.py analyze` records the result under RL#1 and refuses to record a second one.

## 4 Compute

Tool run 15.3-97.9 s and f1 run 15.3-103.3 s per ISPD2005 design (reports/T2_trackA_ispd_dreamplace.md:27-34). Per
design: 8 tool runs, 32 f1 runs for the tool layouts (selection and fresh seeds), and up to 48 f1 runs for the relink
candidates and their picks.
