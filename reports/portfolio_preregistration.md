# Two densities vs two seeds for the tool: pre-registration (confirmatory, Track A, ISPD2005)

| Field | Value |
|---|---|
| Report | portfolio_preregistration |
| Date | 2026-10-03 |
| Status | registered by the agent under the owner's delegation of 3 Oct; fixed before any ISPD2005 result of RL#1 or RL#2 was looked at (their jobs were running or fetched unread) |
| Track | A: f1 = DREAMPlace GP + LG with the macros fixed (target density 0.9); J against the ISPD2005 seeding campaign's M1 baseline (0.45 by construction) |
| Family | ISPD2005, all 8 designs; the exploration that motivated this test used IBM only (reports/beat_tool_track_a.md, Section 7) |
| alpha-ledger | campaign `RL`, entry RL#3, alpha_3 = 0.00625 (alpha = 0.05 per campaign: HEURBRIDGE_TASKS.md:541) |
| Code | scripts/density_confirm.py (`reserve3`, `analyze3`), as committed together with this document; no run is added: the runs are RL#1's (density 0.9) and RL#2's (density 0.6) |

## 1 Question

At the same number of runs, does running the tool (DREAMPlace mixed-size) once at target density 0.9 and once at 0.6
and keeping the better layout give a lower Track-A J than two runs at 0.9 with the better kept? In other words: are two
configurations a better use of two tool runs than two seeds?

**What this is not:** a HeurBridge method. If it passes, the confirmed claim is about how to spend the tool's runs.

## 2 Why (IBM exploration, exploratory)

- One run at a lower density helps on some designs and hurts on others: at 0.7, lower than 0.9 in 67 of 104 cases on
  13 IBM designs, with clear gains on ibm02-04, ibm06, ibm07 and ibm12 and losses on ibm01, ibm11, ibm13 and ibm18
  (reports/beat_tool_track_a.md, Section 7; run files under runs/remote/dens7_*, dens_*).
- Keeping the better of the seed-s runs at 0.9 and 0.7 (by f1 with seed 0) against the better of seeds s and s+1 at
  0.9: lower in 66 of 104 cases, higher in 16, median 0.4365 against 0.4485 (one-sided Wilcoxon p = 3.3e-10); one ibm09
  case where the selection seed picked a layout that blows up under the fresh seeds makes the mean worse.
- With 0.6 (four IBM designs, all of the kind where lower density helps): lower in 30 of 32, p = 3.3e-9.
- RL#2's runs on ISPD2005 are at 0.6 (reports/density_preregistration.md), so this test uses 0.6.

## 3 Procedure (fixed now)

- **Runs:** RL#1's tool runs at 0.9 (jobs `rlc_*`, scripts/tool_runs.py) and RL#2's at 0.6 (jobs `rtd_*`), seeds 0-7
  on all 8 designs, each legalized by P_M, ISPD2005 loaded with every macro movable.
- **Method (two densities):** for seed s, the better of T_s at 0.9 and T_s at 0.6 by f1 with seed 0 (ties: the run at
  0.9). Cost: two tool runs and two f1 runs.
- **Comparator (two seeds):** the better of T_s and T_(s+1) (mod 8) at 0.9 by f1 with seed 0: RL#1's "best2"
  (scripts/relink_eval.py). Cost: two tool runs and two f1 runs.
- **Endpoint:** median J over fresh f1 seeds 1, 2, 3.
- **Units:** (design, s) for s = 0-7: 64 paired units, one source per design (scripts/density_confirm.py).
- **Failures:** a failed run is +inf and never picked over a finite one, listed by name.

## 4 Test and decision

- **Primary test:** paired one-sided Wilcoxon signed-rank on the 64 differences (two densities minus two seeds; two
  densities lower), +inf kept (heurbridge/stats/paired.py:41-50), at alpha_3 = 0.00625 (RL#3).
- **Pass:** p <= 0.00625. Then the confirmed claim is: on the held-out ISPD2005 family, two runs of the tool at
  densities 0.9 and 0.6 with the better kept give a lower Track-A J than two runs at 0.9 with the better kept, at the
  same number of runs.
- **Fail:** reported as a negative result; no claim.
- **Reported, not tested:** per-design means; how often the pick is the run at 0.6; wall-clock (a run at 0.6 took
  about 30 % longer than at 0.9 on IBM: reports/density_preregistration.md, Section 5).
- **Once:** `density_confirm.py analyze3` records the result under RL#3 and refuses to record a second one.
