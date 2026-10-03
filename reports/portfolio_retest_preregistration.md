# Two densities vs two seeds for the tool, corrected re-test: pre-registration (confirmatory, Track A, ISPD2005)

| Field | Value |
|---|---|
| Report | portfolio_retest_preregistration |
| Date | 2026-10-03 |
| Status | registered under the owner's approval of 3 Oct ("make a correct ISPD2005 test"); fixed before any ISPD2005 tool run with the corrected input |
| Replaces | RL#3 (reports/portfolio_preregistration.md), not evidence because the tool could not move ISPD2005's macros (reports/defect_ispd_tool_runs.md) |
| Track | A: f1 = DREAMPlace GP + LG with the macros fixed (target density 0.9, unchanged); J against the ISPD2005 seeding campaign's baseline (the benchmark's macro placement after P_M; 0.45 by construction) |
| Family | ISPD2005 without bigblue3: adaptec1-4, bigblue1, bigblue2, bigblue4. bigblue3 is excluded: it is the only design whose tool runs placed macros before the fix, and those runs were seen (RL#2, RL#3) |
| alpha-ledger | campaign `RL`, entry RL#4, alpha_4 = 0.003125 (alpha = 0.05 per campaign: HEURBRIDGE_TASKS.md:541), reserved before the first run |
| Code | scripts/tool_runs.py with the corrected tool input (heurbridge/eval/dreamplace.py:50-56, commit 157bf21), scripts/portfolio_retest_confirm.py, as committed together with this document |

## 1 Question

At the same number of tool runs, is running the tool (DREAMPlace mixed-size, every macro movable) once at target
density 0.9 and once at 0.6 and keeping the better layout better than two runs at 0.9 with different seeds and the
better kept?

**What this is not:** a HeurBridge method. If it passes, the confirmed claim is about how to spend the tool's runs.

## 2 Why (IBM exploration, where the tool's runs place the macros)

The seed-s runs at 0.9 and 0.6, the better by the selection seed, against seeds s and s+1 at 0.9: lower in 65 of 104
cases on 13 IBM designs, higher in 20, one-sided Wilcoxon p = 3.1e-10 (reports/beat_tool_track_a.md, Section 7).

## 3 Procedure (fixed now)

- **Check before the runs (excluded design):** two tool runs on bigblue3 with the corrected input must move the macros
  (positions differ from the benchmark's and between the two seeds). If not, no run of this test starts.
- **Tool runs (jobs `rc4_*`):** per design, DREAMPlace mixed-size with every macro movable, seeds 0-7, at target
  density 0.9 and at 0.6 (16 runs), each legalized by P_M and scored by f1 with seed 0 (selection) and with fresh
  seeds 1, 2, 3 (scripts/tool_runs.py --suite ispd2005 --runs runs/seed_trackA_ispd --target-density 0.9 or 0.6).
- **Method (two densities):** for seed s, the better of T_s at 0.9 and T_s at 0.6 by f1 with seed 0 (ties: the run at
  0.9). Two tool runs, two f1 runs.
- **Comparator (two seeds):** the better of T_s and T_(s+1 mod 8), both at 0.9, by f1 with seed 0. Two tool runs, two f1
  runs.
- **Endpoint:** median J over fresh f1 seeds 1, 2, 3.
- **Units:** (design, s), s = 0-7, 7 designs: 56 paired units, one source per design (the analysis refuses two).
- **Failures:** a failed tool run or P_M is +inf, never picked over a finite run, listed by name.

## 4 Test and decision

- **Primary test:** paired one-sided Wilcoxon signed-rank on the 56 differences (method minus comparator; method lower),
  +inf kept (heurbridge/stats/paired.py:41-50), at alpha_4 = 0.003125 (RL#4).
- **Pass:** p <= 0.003125. Then the confirmed claim is: on the held-out ISPD2005 designs (bigblue3 excluded), with the
  tool placing every macro, two runs at densities 0.9 and 0.6 with the better kept give a lower Track-A J than two runs
  at 0.9 with the better kept, at the same number of runs.
- **Fail:** reported as a negative result; no claim.
- **Reported, not tested:** per-design means of one run at 0.9, one run at 0.6, the two arms; how the tool's own
  layouts compare with the benchmark's macro placement (J against 0.45); how often the pick is the run at 0.6;
  wall-clock; failures.
- **Once:** `portfolio_retest_confirm.py analyze` records the result under RL#4 and refuses to record a second one.

## 5 Notes stated in advance

- With every macro movable the tool's run time on ISPD2005 is unknown (bigblue2 has 23,084 macros, bigblue4 8,170);
  a failure counts as +inf in the arm that needs the run.
- The J reference stays the seeding campaign's baseline, so values above 0.45 mean the tool's own placement is worse
  than the benchmark's; both arms share the reference.
