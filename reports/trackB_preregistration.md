# Track B: pre-registration (DRAFT, awaiting the owner's approval)

| Field | Value |
|---|---|
| Report | trackB_preregistration |
| Date | 2026-10-02 |
| Status | **Draft, awaiting approval.** No data of this test exist; nothing has run. |
| Track | B (ORFS 2024-12-13 8ae3ae36, OpenROAD 676f8451, Nangate45; ENV_REPORT.md:138-139) |
| Cost | cost_v3: J normalized to the unmodified flow; timing gates referenced to the same-path replay; every gate enforced at f2; failure = +inf (configs/cost.yaml:3, :12-25) |
| alpha-ledger | new campaign `TB` (alpha = 0.05), entries TB#1-#4 reserved before any test run (Section 5) |

## 1 Question

Does a heuristic macro layout found by the Track-B seeding beat the tool's own macro placement at signoff (f2), by
more than the flow's sensitivity to a one-site or one-row shift of the layout?

## 2 What exists now (descriptive, not usable as the test)

- bp_fe_top: the top three admitted candidates' four-point bands lie wholly below the tool's same-path band, whose
  lower edge is 1.0330 (reports/T2_trackB_orfs_bp_fe_top.md:78-82).
- bp_be_top: only the best candidate's band (0.9306-1.0002) lies below the tool band's lower edge 1.0241; the next
  two overlap it (reports/T2_trackB_orfs_bp_be_top.md:78-82).
- ariane136: best admitted J 0.9757, below the tool band 1.0000-1.0089; the candidates' own bands are being measured
  (reports/T2_trackB_orfs_ariane136.md:47, :51; HANDOFF.md:131-133).

**Why these cannot serve as the confirmatory test:** the candidates were selected on the same f2 values their bands
were measured around, with the same three shifts as the tool's band (scripts/run_seed_orfs.py:369). Selection on
noisy values favours candidates whose noise was favourable (winner's curse). The test therefore re-measures
pre-selected candidates on **fresh shifts**.

## 3 Design

- **Designs and order (fixed):** TB#1 bp_fe_top, TB#2 bp_be_top, TB#3 ariane136, TB#4 swerv_wrapper (only if its
  campaign completes with an f2-admitted layout; otherwise TB#4 stays unused). ariane133 enters only if the owner
  adopts a flow deviation for it and its campaign is re-run under it, baseline included; otherwise it is dropped as a
  documented deviation (reports/trackB_ariane133_diagnosis.md).
- **Candidate per design (one, fixed before the test):** the campaign's best f2-admitted layout:
  bp_fe_top.ls0.n4 (reports/T2_trackB_orfs_bp_fe_top.md:80), bp_be_top.ls7.n1 (reports/T2_trackB_orfs_bp_be_top.md:80),
  and ariane136's best admitted layout (reports/T2_trackB_orfs_ariane136.md:51).
- **Reference:** the tool's macro layout run through the candidates' path (the same-path replay, cost_v3's gate
  reference: configs/cost.yaml:17-19).
- **Replicates (fresh, not used before):** the whole layout shifted by (+2, 0), (-2, 0), (0, -1), (0, +2), (+1, +1),
  (-1, -1) sites and rows, the same six for candidate and reference. A shift that leaves the core is replaced by the
  next of (+3, 0), (-3, 0), (0, -2), in that order, for both arms (this document).
- **Endpoint:** f2 J (6_report) of each replicate, every gate enforced; a failure is +inf.
- **Signoff layouts:** 6 candidate + 6 reference replicates per design = 12 f2 runs; 36-48 in all.

## 4 Test and what counts as beating the tool

- **Per design (exact permutation test):** "the candidate beats the tool's macro placement" iff all six candidate
  replicates have a lower J than all six reference replicates, i.e. its whole band lies below the tool's band. Under
  the null hypothesis (candidate and reference replicates exchangeable) this happens with probability
  1 / C(12, 6) = 1/924 = 0.0011 (this document), the test's p-value when it occurs; otherwise p is the one-sided
  Mann-Whitney p of the twelve values.
- **Stronger wording, "beats the unmodified tool flow":** additionally every candidate replicate below the
  unmodified flow's J of 1.00 at f2 (by construction: reports/T2_trackB_orfs_bp_fe_top.md:47). Reported per design.
- **Anything else** (bands overlap) is "indistinguishable from noise", never an improvement.

## 5 alpha-ledger reservation and decision

- Campaign `TB`, alpha = 0.05, alpha_j = alpha x 2^-j (HEURBRIDGE_TASKS.md:541; heurbridge/stats/alpha_ledger.py:3-7):
  TB#1 0.025, TB#2 0.0125, TB#3 0.00625, TB#4 0.003125, and TB#5 0.0015625 for ariane133 if it is re-run under an
  adopted deviation. The smallest attainable p, 0.0011, is below every alpha_j, so each design can pass on its own.
- Reservations are written with `AlphaLedger.reserve` before the first test run; results with `record` afterwards.
- **Track-B claim** (confirmatory): "heuristic layouts beat the tool's macro placement at signoff on k of n designs",
  k = the designs whose test passes at their alpha_j. No design passing: a negative Track-B result, reported as such.

## 6 Limits stated in advance

- f3 (DRC by KLayout or Magic, LVS) is not available (reports/signoff_anchor_readiness.md): passing f2 gates is not
  production signoff.
- Six shifts measure the flow's sensitivity to one kind of perturbation (whole-layout shifts), not every source of
  variation (e.g. other tool versions).
- These are heuristic or local-search layouts; no Track-B bridge exists yet.

## 7 Compute

At most 8 OpenROAD runs at a time and 7,200 s per step on 224 (red line). Twelve f2 runs per design; the f2 wall time
per run is not documented in the repo.
