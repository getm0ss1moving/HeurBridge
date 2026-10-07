# Track B: pre-registration (confirmatory: a HeurBridge macro layout against the tool's at signoff)

| Field | Value |
|---|---|
| Report | trackB_preregistration |
| Date | 2026-10-03 |
| Status | **registered 3 Oct** under the owner's decisions of 3 Oct: put the effort on Track B, and D6 (the timing gates keep the 0.02-ns guard without the sign rule); fixed before any run of this test |
| Track | B (ORFS 2024-12-13 8ae3ae36, OpenROAD 676f8451, Nangate45; ENV_REPORT.md:138-139) |
| Cost | cost_v3's J normalized to the unmodified flow (configs/cost.yaml:3, :12-25), with this test's timing-gate rule (Section 4) |
| alpha-ledger | campaign `TB` (alpha = 0.05): TB#1 bp_fe_top 0.025, TB#2 bp_be_top 0.0125, TB#3 ariane136 0.00625 reserved now; TB#4 swerv_wrapper 0.003125 reserved when its campaign completes, before its test runs; TB#5 ariane133 only under an adopted flow deviation (decision D2) |
| Code | scripts/run_seed_orfs.py `--phase tbtest`, scripts/trackb_confirm.py, heurbridge/eval/cost.py (`timing_sign_rule`), as committed together with this document |

## 1 Question

Does a macro layout found by HeurBridge's Track-B seeding (heuristic programs and their local search) beat the tool's
own macro placement (ORFS's rtl_macro_placer, Hier-RTLMP) at signoff (f2), by more than the flow's sensitivity to a
whole-layout shift of a few sites or rows?

## 2 What exists (descriptive, not the test)

The campaigns' best admitted layouts lie below the tool's same-path band on bp_fe_top, bp_be_top and ariane136
(reports/T2_trackB_orfs_bp_fe_top.md, reports/T2_trackB_orfs_bp_be_top.md, reports/T2_trackB_orfs_ariane136.md).
They were selected on the same f2 values their bands were measured around (winner's curse), so the test re-measures
pre-selected candidates on **fresh shifts**.

## 3 Design

- **Candidate per design (fixed now):** the campaign's best f2 layout admitted under Section 4's rule, computed from
  the stored f2 rows (local run files `runs/remote/seedB_orfs7_<design>/runs/seed_orfs/<design>/evals_f2.jsonl`):
  bp_fe_top.ls0.n4 (f2 J 0.8809), bp_be_top.ls7.n1 (0.9306), ariane136.ls7.n3 (0.9757). swerv_wrapper's is fixed the
  same way when its campaign completes, before its test runs.
- **Reference:** the tool's macro layout run through the candidates' path (the same-path replay).
- **Replicates (fresh, not used before):** the whole layout shifted by (+2, 0), (-2, 0), (0, -1), (0, +2), (+1, +1),
  (-1, -1) sites and rows, the same for candidate and reference; a shift that leaves the core for either arm is replaced
  by the next of (+3, 0), (-3, 0), (0, -2), in that order, for both arms; a slot with no legal shift left is dropped for
  both arms and named (scripts/run_seed_orfs.py, `tb_pairs`).
- **Runs:** each replicate at f2 (6_report), 12 per design, at most 8 OpenROAD runs at a time on 224, 7,200 s per step.

## 4 Endpoint (decision D6)

- **Candidate replicates:** f2 J with every gate enforced; the setup and hold gates compare with the same-path replay
  band's median at f2 (the campaign's four replays, cost_v3's gate reference) with the 0.02-ns guard and **without the
  sign rule** (heurbridge/eval/cost.py, `timing_sign_rule=False`); a failed gate or flow is +inf.
- **Reference replicates:** f2 J before the gates (the gates are defined relative to the tool itself); a failed flow is
  +inf.

## 5 Test and decision

- **Per design:** exact one-sided permutation test of the rank sum over the C(12, 6) = 924 splits (candidate lower).
  When all six candidate replicates are below all six reference replicates, p = 1/924 = 0.0011, below every alpha_j
  of TB#1-TB#4.
- **Pass:** p <= alpha_j of the design's entry. Claim per passing design: "the HeurBridge layout beats the tool's
  macro placement at signoff, beyond the flow's shift sensitivity". Overall Track-B claim: k of n designs pass.
- **Fail:** reported as a negative result for that design.
- **Reported, not tested:** every replicate's J, gates and wall-clock; the replicates' J before the gates for both arms;
  the cost of finding each candidate (the campaign's flow runs) against the tool's one run.
- **Once:** `trackb_confirm.py analyze --design <d>` records the design's result and refuses a second one.

## 6 Limits stated in advance

- f3 (DRC by KLayout or Magic, LVS) is not available (reports/signoff_anchor_readiness.md): passing f2's gates is not
  production signoff.
- Six shifts measure one kind of perturbation (whole-layout shifts), not every source of variation.
- The candidates come from heuristic programs and local search; no Track-B bridge exists yet.
- The comparison with DREAMPlace's macro placement through this flow (the owner's request of 3 Oct) is a separate
  step after Track B's seeding finishes.

## Addendum (4 Oct 00:16): swerv_wrapper's candidate, fixed before its test

As Section 3 provides, after swerv_wrapper's campaign completed (job `seedB_orfs7_swerv_wrapper`, 4 Oct 00:15) and
before its test ran: **swerv_wrapper.ls5.n4** (f2 J 0.8674 under Section 4's rule; 9 of 20 f2 layouts admitted),
computed by `scripts/trackb_confirm.py candidate --design swerv_wrapper` from the local run file
`runs/remote/seedB_orfs7_swerv_wrapper/runs/seed_orfs/swerv_wrapper/evals_f2.jsonl:5`. TB#4 is reserved with it
(alpha_4 = 0.003125). Descriptive, not part of the test: unlike on the other three designs, this candidate's f2 J lies
above all four same-path replays of the tool's layout (J 0.8407-0.8611, the same file's lines 1-4). The test runs as
registered.

## Addendum (7 Oct 15:36): ariane133's candidate, fixed before its test (TB#5)

ariane133 runs under the owner's decision D2 (b) of 5 Oct (reports/next_phase_decisions.md, D2): virtual
timing-driven resizing for every run, the baseline included (`GLOBAL_PLACEMENT_ARGS=-keep_resize_below_overflow 0.01`,
with `RTLMP_MAX_LEVEL=1` as before). It is a documented flow deviation, the same for the candidate's and the tool's
runs, so J stays normalized to the same flow. As Section 3 provides, after the campaign completed (job
`seedB_orfs9_ariane133`) and before its test ran: **ariane133.ls5.n5** (f2 J 0.9038 under Section 4's rule; 12 of 20
f2 layouts admitted), computed by `scripts/trackb_confirm.py candidate --design ariane133 --campaign-prefix seedB_orfs9_`
from the local run file `runs/remote/seedB_orfs9_ariane133/runs/seed_orfs/ariane133/evals_f2.jsonl:15`. The gates stay
as registered (D6: the replay band's median, the 0.02-ns guard, no sign rule; decision D11 keeps D6 for TB#5). TB#5 is
reserved with it (alpha_5 = 0.0015625). The test's runs: job `tb9_ariane133` (`--phase tbtest` with the campaign's make
variables), analysed with `--tb-prefix tb9_ --campaign-prefix seedB_orfs9_`.

Stated in advance: with six replicates per arm the smallest attainable p is 1/924 = 0.0011, below alpha_5; the next is
2/924 = 0.0022, above it. TB#5 therefore passes only if all six candidate replicates lie below all six reference
replicates (a failed gate or flow is +inf; a shift slot without a legal common shift leaves fewer replicates, and then
no p below alpha_5 is attainable). Descriptive, not part of the test: the tool's four same-path replays at f2 vary J
from 0.739 to 1.877 (the same file's lines 1-4), almost entirely through setup TNS: under this flow ariane133's f2 J is
dominated by timing noise.

## Addendum (7 Oct 19:15): TB#5's runs restarted (decision D14 (c))

Another user's jobs took about 40 of 224's 64 cores from the afternoon of 7 Oct. Both of TB#5's first runs (job
`tb9_ariane133`: the candidate and the tool at shift (+2, 0)) hit the 7,200-s cap, in `4_1_cts` and `5_2_route`. The
campaign's ariane133 f2 runs had taken 1.0-1.9 h. No replicate had completed (0 of 12). The owner decided (D14 (c),
reports/next_phase_decisions.md) to stop the job and re-run the test with only TB#5's runs on our side of 224. The
voided runs stay in the record (`runs/remote/tb9_ariane133/runs/seed_orfs/ariane133/evals_tb.jsonl`). Unchanged: the
candidate `ariane133.ls5.n5.f2`, the six shifts and their fallback rule, the gates (D6), alpha_5 and the analysis. The
re-run is job `tb10_ariane133` (2 runs at a time), analysed once with `--tb-prefix tb10_ --campaign-prefix
seedB_orfs9_`.
