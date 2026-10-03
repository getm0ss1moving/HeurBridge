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

## Addendum (4 Oct 00:20): swerv_wrapper's candidate, fixed before its test

As Section 3 provides, after swerv_wrapper's campaign completed (job `seedB_orfs7_swerv_wrapper`, 4 Oct 00:15) and
before its test ran: **swerv_wrapper.ls5.n4** (f2 J 0.8674 under Section 4's rule; 9 of 20 f2 layouts admitted),
computed by `scripts/trackb_confirm.py candidate --design swerv_wrapper` from the local run file
`runs/remote/seedB_orfs7_swerv_wrapper/runs/seed_orfs/swerv_wrapper/evals_f2.jsonl:5`. TB#4 is reserved with it
(alpha_4 = 0.003125). Descriptive, not part of the test: unlike on the other three designs, this candidate's f2 J lies
above all four same-path replays of the tool's layout (J 0.8407-0.8611, the same file's lines 1-4). The test runs as
registered.
