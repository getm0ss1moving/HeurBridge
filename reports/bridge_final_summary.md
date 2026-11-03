# HeurBridge-PR: what the bridge is and what it achieved (final summary)

| Field | Value |
|---|---|
| Date | 2026-10-14 |
| Project state | stopped by the owner on 2026-10-09 (HANDOFF.md:7) |
| Code | git dfa5c64 |
| Scope | the bridge alone, without the local search or any other added method |
| Sources | every number carries `path:line`. Percentages and ratios are computed from the cited values and marked "computed". |

## 1 What the bridge is

**What it does.** The bridge refines a heuristic program's macro layout toward the design's best known layouts, its
"elites". It is "flow matching whose source is a heuristic's output" (README.md:4).

**Model.** A graph neural network of about 1.1M parameters (heurbridge/bridge/model.py:14, :47):

- Blocks: an encoder MLP, then [GATv2 (4 heads), MLP, global self-attention] repeated L times, then a decoder.
- Output: a velocity for each node.
- Sources: heurbridge/bridge/model.py:1-6.

**Graph.** It is built from the design (heurbridge/bridge/graph.py:3-6):

- Nodes are movable macros, fixed macros, IOs, and clusters of standard cells.
- Movable macros and clusters move; fixed macros and IOs stay where they are.
- Orientation is an input feature and is never changed.

**Training.**

- Loss: a corrected stochastic-interpolant flow-matching loss (heurbridge/bridge/train.py:3-7).
- Data: 1,608 pairs from 13 IBM designs (reports/T3_algorithmR_trackA.md:55-57).
- Each pair is a heuristic layout and the nearest of its design's top-5 elites (reports/T3_algorithmR_trackA.md:56-57).
- Pretraining: 200,000 steps on synthetic circuits (reports/T3_pretrain_small.md:19).

**Use (guarded partial transport).** For each heuristic layout x^h, the bridge works in three steps (reports/E0_preregistration.md:19; heurbridge/bridge/sample.py:3-6, :24):

1. It integrates 20 Euler steps to an endpoint T(x^h).
2. The "guard" tries four candidate layouts x^h + α(T(x^h) − x^h), for α = 0, 0.25, 0.5 and 1.
3. Each candidate is legalized, scored with DREAMPlace f1, and the best one is kept.

Because α = 0 is the raw layout, the bridge never returns a worse layout than its input (heurbridge/bridge/sample.py:4-5).

## 2 Where the bridge was used

- **Track A only.** Track A uses the IBM (ICCAD04) and ISPD2005 bookshelf designs. There J is a weighted sum of two
  ratios to a reference layout: wirelength (weight 0.30) and routing-congestion overflow (weight 0.15) (heurbridge/pipeline/evaluators.py:20; configs/cost.yaml:6, :8).
  - Both are measured after DREAMPlace places the standard cells around the fixed macros.
  - The reference layout scores J = 0.45; lower is better (reports/T2_trackA_ibm_dreamplace.md:23).
  - There is no timing on Track A.
  - On ISPD2005 the 0.45 reference is the benchmark's own macro placement, not DREAMPlace's (reports/defect_ispd_tool_runs.md:35-36).
- **Never on Track B.** Track B is the real OpenROAD flow to signoff. "No Track-B bridge exists"
  (reports/trackB_preregistration.md:64). Every Track-B result came from heuristic programs plus a flow-scored local search.

## 3 How much the bridge alone improves macro placement

| Comparison | Result | Label | Source |
|---|---|---|---|
| Against the raw heuristic layouts, held-out ISPD2005 family (7 designs, 405 cases) | Mean J 0.5863 → 0.5579: **−4.8 %** (computed). 365 cases better, 40 unchanged, 0 worse. | pre-registered confirmatory (gate G0′ passed) | reports/E0_partner_ablation.md:19, :29, :32, :38, :46 |
| — per design | −1.9 % to −6.9 % | same | HANDOFF.md:623 |
| — what the learned direction adds | The same guard moving in a random direction gives 0.5807: −1.0 % vs raw. **The learned direction adds −3.9 % beyond it** (computed). | same | reports/E0_partner_ablation.md:32-33, :29 |
| Against the raw heuristic layouts, held-out IBM designs ibm08 and ibm12 (145 cases) | Mean J 0.6375 → 0.6004: **−5.8 %** (computed). 66 better, **79 unchanged**, 0 worse. Random direction: 0.6302. | pre-registered confirmatory (secondary) | reports/E0_partner_ablation_ibm_heldout.md:19, :27, :30-31, :36, :44 |
| Best program per design only | ISPD2005: 0.5172 → 0.5044, −2.5 % (computed). IBM held-out: 0.5067 → 0.5067, **no change**. | same tests, reported, not tested | reports/E0_partner_ablation.md:29, :32; reports/E0_partner_ablation_ibm_heldout.md:27, :30 |
| Distance to the 0.45 reference | The bridge closes about **one fifth** of the gap: (0.5863 − 0.5579) / (0.5863 − 0.45) = 21 % on ISPD2005, and 20 % on IBM held-out (computed). **No refined layout reaches 0.45.** | same | reports/E0_partner_ablation.md:23, :29, :32; reports/E0_partner_ablation_ibm_heldout.md:27, :30 |
| — compared with DREAMPlace itself (ISPD2005, after the fix) | DREAMPlace's own 8 runs score 0.3818–0.4467 on adaptec1–4 and bigblue1, so the real tool is further ahead still. | descriptive | reports/test_audit.md:108-112 |
| Bridge applied to DREAMPlace's own layouts (IBM; 3 designs × 8 tool seeds) | −0.0028 J on average vs the tool alone (p = 0.040), about −0.6 % (computed). **Not better than running the tool twice and keeping the better result** (+0.0011, p = 0.609) at similar compute. | exploratory demo | reports/beat_tool_track_a.md:54-58 |
| — single-seed demo on 12 IBM designs | Changed the tool's layout on 2 of 12 designs only. ibm04: 0.4497 → 0.4329. ibm09: 0.4544 → 0.4132. The other 10: α = 0, no change. Over 3 seeds both gains lie outside the tool's noise band. | exploratory demo | reports/beat_tool_track_a.md:16-27, :37, :41 |
| The bridge's standard-cell sketch given to DREAMPlace as a start | No effect: mean J 0.4828 vs 0.4822 from the default start; 28 better, 36 worse (p = 0.972). | exploratory demo; negative result | reports/demo_sketch_start.md:28-29, :34 |
| Training-time gate (validation designs ibm04, ibm06) | 0.8870 → 0.4815. This holds partly by construction: the guard picks α with the same f1 that scores the result, and these designs were used for model selection. **Not an estimate of the bridge's effect.** | development (T3 exit gate) | reports/T3_algorithmR_trackA.md:23, :27 |

## 4 Why the bridge could not do more

- **Weak targets.** Only 38 % of the training pairs point at a layout at or below the tool's J. A perfect bridge would
  still stay above the tool (reports/bridge_target_audit.md:29).
- **No discrete moves.** It moves macros continuously and locally: it never changes orientation, reorders groups or
  swaps distant macros (heurbridge/bridge/graph.py:6; reports/gap_to_tool_plan.md:32-34).
- **Narrow data.** 1,608 pairs from one design family; later training rounds added no new data
  (reports/T3_algorithmR_trackA.md:55-60).
- **Never tried.** The planned fix, re-targeting the pairs at layouts at or below the tool, was never run; the
  owner's decision D5 has no recorded outcome (reports/gap_to_tool_plan.md:54-74; reports/next_phase_decisions.md:232-240).

## 5 Bottom line

**On its own, the bridge reliably improves heuristic macro layouts by about 5 % in J and never makes them worse. The
learned direction accounts for most of that gain. It closes only about one fifth of the gap to the reference layout,
is no better than simply running DREAMPlace twice, and was never used in the real OpenROAD flow (Track B).**
