# One tool run at target density 0.6 vs the tool's best of four at 0.9: pre-registration (confirmatory, Track A, ISPD2005)

| Field | Value |
|---|---|
| Report | density_preregistration |
| Date | 2026-10-03 |
| Status | registered by the agent under the owner's delegation of 3 Oct; fixed before any ISPD2005 run at a target density other than 0.9 and before any result of RL#1 was looked at |
| Track | A: f1 = DREAMPlace GP + LG with the macros fixed (target density 0.9, unchanged); J against the ISPD2005 seeding campaign's M1 baseline (0.45 by construction) |
| Family | ISPD2005, all 8 designs; untouched by the exploration that motivated this test (IBM only: reports/beat_tool_track_a.md, Section 7) |
| alpha-ledger | campaign `RL`, entry RL#2, alpha_2 = 0.0125 (alpha = 0.05 per campaign: HEURBRIDGE_TASKS.md:541), reserved before the first run |
| Code | scripts/tool_runs.py (`--target-density`), scripts/density_confirm.py, as committed together with this document; the comparator's runs are RL#1's (reports/relink_preregistration.md) |

## 1 Question

At a quarter of the runs, does one run of the tool (DREAMPlace mixed-size) at target density 0.6 give a lower Track-A
J than the tool's best of four runs at target density 0.9? J's baseline (0.45) is the tool at 0.9, so this asks
whether a configuration of the tool alone moves J below the baseline on held-out designs at a lower cost.

**What this is not:** a HeurBridge method. If it passes, the confirmed claim is about the tool's configuration for
this J, and every later "better than the tool" claim must compare with the tool at density 0.6, not 0.9.

## 2 Procedure (fixed now)

- **Density d* = 0.6**, chosen on the IBM exploration only (ibm04, ibm06, ibm10, ibm12; reports/beat_tool_track_a.md,
  Section 7): the lowest mean J of a single run among the densities tried there, 0.8, 0.7, 0.6 and 0.5 (Section 5).
- **Method runs (jobs `rtd_*`):** per design, DREAMPlace mixed-size at target density 0.6 with seeds 0-7, each
  legalized by P_M, ISPD2005 loaded with every macro movable (scripts/tool_runs.py --target-density 0.6;
  scripts/tool_refine_eval.py:42-53). Everything else as RL#1's tool runs.
- **Comparator:** RL#1's best of four, T_s..T_(s+3) (mod 8) at density 0.9, picked by f1 with seed 0 (the "best4"
  of scripts/relink_eval.py rows in RL#1's `rlc_*` jobs). No run is added for it.
- **Endpoint:** median J over fresh f1 seeds 1, 2, 3 (f1 at density 0.9 as always).
- **Units:** (design, s) for s = 0-7: 64 paired units, one source per design (scripts/density_confirm.py refuses two).
- **Failures:** a failed tool run or P_M is +inf for its arm, listed by name.

## 3 Test and decision

- **Primary test:** paired one-sided Wilcoxon signed-rank on the 64 differences (one run at 0.6 minus best of four at
  0.9; the run lower), +inf kept (heurbridge/stats/paired.py:41-50), at alpha_2 = 0.0125 (RL#2).
- **Pass:** p <= 0.0125. Then the confirmed claim is: on the held-out ISPD2005 family, one run of the tool at target
  density 0.6 gives a lower Track-A J than the best of four runs at 0.9 (one tool run and one f1 run against four and
  four).
- **Fail:** reported as a negative result; no claim.
- **Reported, not tested:** per-design means of one run at 0.9, best of four at 0.9 and one run at 0.6; wall-clock per
  arm (measured while jobs share GPUs); J's components (HPWL, RUDY overflow) of the runs at 0.6.
- **Once:** `density_confirm.py analyze` records the result under RL#2 and refuses to record a second one.

## 4 Notes stated in advance

- Utilization (movable cell and macro area over the core, from the benchmark files): 0.888, 0.915, 0.744, 0.626,
  0.686, 0.616, 0.856, 0.652 for adaptec1-4 and bigblue1-4; 0.80 on the IBM designs explored. A density below a
  design's utilization cannot be met, and DREAMPlace then spreads the objects as far as it can. 0.6 is below the
  utilization of every ISPD2005 design and of the four IBM designs explored, so the held-out designs are in the regime
  the IBM exploration covered
  (utilization over target 1.03-1.53 on ISPD2005; 1.14-1.6 on IBM at 0.7-0.5).
- RL#1 runs on the same family; its tool runs at 0.9 are this test's comparator, and its result was not looked at
  when this was fixed.

## 5 IBM evidence that fixed d* (exploratory)

Mean J of a single run (8 tool seeds per design, fresh-seed medians), the tool's median run time, and the comparison
with the same seeds at 0.9 (one-sided Wilcoxon, paired by seed; scripts/report_beat_tool.py, Section 7; run files
under runs/remote/dens_*, densB_*):

| density | ibm04 | ibm06 | ibm10 | ibm12 | all 32 | lower than 0.9 | tool run (median) |
|---|---|---|---|---|---|---|---|
| 0.9 | 0.4411 | 0.4519 | 0.4729 | 0.4483 | 0.4536 | - | 20 s |
| 0.8 | 0.4253 | 0.4452 | 0.4868 | 0.4249 | 0.4455 | 24 of 32, p = 0.0097 | 25 s |
| 0.7 | 0.4166 | 0.4221 | 0.4596 | 0.4195 | 0.4295 | 28 of 32, p = 1.0e-5 | 24 s |
| **0.6** | 0.4156 | 0.4171 | 0.4493 | 0.4172 | **0.4248** | 32 of 32, p = 2.3e-10 | 26 s |
| 0.5 | 0.4156 | 0.4171 | 0.4622 | 0.4192 | 0.4285 | 28 of 32, p = 1.8e-7 | 28 s |

At 0.6 both terms of J improve: HPWL 3.1-3.8 % below the baseline on ibm04, ibm06 and ibm12 (+0.8 % on ibm10), RUDY
overflow from about 0.2 % to 0.01-0.02 % on ibm04 and ibm06 and from 17.7 % to 14.8 % on ibm12. The best of four at
0.9 averages 0.4433.
