# {title}

| Field | Value |
|---|---|
| Report | {report_id} |
| Date | {date} |
| Status | **registered {date}**, before any run of the test's replicates |
| Track | B (ORFS 2024-12-13 8ae3ae36, OpenROAD 676f8451, Nangate45; ENV_REPORT.md:138-139) |
| Cost | cost_v3's J normalized to the unmodified flow (configs/cost.yaml:3, :12-25) |
| Timing gates | decision D11 (b): each replicate against the tool's replicate at the same shift (heurbridge/eval/cost.py same_shift_reference), 0.02-ns guard, no sign rule |
| Picks | decision D13 (a): lowest J_safe = J + 0.04 (1 - S) over equal positions (heurbridge/cellstage/select.py pick) |
| alpha-ledger | campaign `CS` (alpha = 0.05; alpha_j = alpha 2^-j): {entries}, reserved now |
| Code | heurbridge/cellstage/, scripts/run_cell_stage.py, {analysis_script}, as committed with this document |

## 1 Question

{question}

## 2 What exists (descriptive, measured before this registration)

{existing}

## 3 Arms

Every arm imports a fixed macro layout; only the cell stage differs.  Each recipe is given in full (its id is the
hash of its settings, heurbridge/cellstage/recipe.py):

| arm | macro layout (source row) | cell-stage recipe (name, id) | why |
|---|---|---|---|
{arms}

Recipes, as JSON: {recipes_file}.

## 4 Replicates and endpoint

- **Replicates:** the Track-B test's six whole-layout shifts (+2, 0), (-2, 0), (0, -1), (0, +2), (+1, +1), (-1, -1)
  sites and rows, with its fallbacks (common legal shifts with the tool's layout; fallbacks (+3, 0), (-3, 0), (0, -2);
  a slot with no legal shift left is dropped and named); f2; at most {slots} OpenROAD runs at a time on 224 (the cell
  chat's share, decision CS-D2), 7,200 s per step.
- **Endpoint:** f2 J with every gate enforced (gates as above); a failed gate or flow is +inf, listed by name.

## 5 Test and decision

- **Per design:** exact one-sided permutation test of the rank sum, {direction}; p = 1/924 when the bands separate
  with six replicates per arm.
- **Pass:** p <= alpha_j.  Claim per passing design: {claim}.
- **Fail:** a negative result for that design; the reverse is not tested.
- **Reported, not tested:** every replicate's J, J before the gates, gates and timing reference; each arm's J, S and
  J_safe; failures by name.
- **Once:** the analysis records each design's result and refuses a second one.

## 6 Limits stated in advance

{limits}
