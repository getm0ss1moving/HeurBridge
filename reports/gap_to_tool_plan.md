# Plan: closing the gap to the tool's own macro placement

| Field | Value |
|---|---|
| Report | gap_to_tool_plan |
| Date | 2026-10-02 |
| Status | plan (no result claim); the recommended experiment needs the owner's go |
| Scope | Track A first (the tool baseline is J = 0.45 by construction); Track B after a Track-B bridge exists |

## 1 The gap, as measured

- Confirmed (pre-registered): the co-trained bridge beats the non-learning partners (G0'; reports/E0_partner_ablation.md:46).
- Also measured: every partner's mean J, and every bridge-refined layout, stays above 0.45, the tool's own
  mixed-size macro placement; the bridge lowers mean J by 1.9-6.9 % per design against the raw heuristic
  (HANDOFF.md:286-288). Mean J of the co-trained bridge: 0.5579 on ISPD2005 (reports/E0_partner_ablation.md:29),
  0.6004 on the held-out IBM designs ibm08 and ibm12 (reports/E0_partner_ablation_ibm_heldout.md:27), against 0.45.
  *Pre-registered confirmatory result (E0) plus its descriptive context.*
- Seeding: the heuristics beat the tool on 2 of 25 Track-A designs only (reports/PROGRESS.md:293-295); on ISPD2005
  no layout is below the baseline (reports/T2_trackA_ispd_dreamplace.md:38). *Development / descriptive.*

## 2 Why the bridge cannot reach the tool today (evidence)

1. **Most training targets cost more than the tool.** A pair's target is the nearest of the design's top-5 archive
   elites (heurbridge/bridge/data.py:8, :66). On the 13 training designs, 38 % of the 1,608 pairs target an elite
   at or below the tool's J and 30 % the tool's own layout; the rest target local-search or heuristic elites that
   cost more (reports/bridge_target_audit.md:29; e.g. ibm14 median target J 0.5819, :23). Even a perfect bridge
   would therefore leave most refined layouts above 0.45. *Development / descriptive.* This corrects an earlier statement
   in reports/PROGRESS.md (Section 7) that the targets are "mostly M1-like layouts": they are M1-like in position,
   not in cost (corrected there on 2 Oct).
2. **Better-than-tool targets barely exist.** Only ibm02 (whose M1 is anomalous) and ibm06 have elites below the tool
   (reports/T2_trackA_ibm_dreamplace.md:60).
3. **Discrete structure is outside the bridge's reach.** Orientation is a condition and never transported
   (heurbridge/bridge/graph.py:6); the bridge moves macros continuously and locally and does not reorder groups or
   swap distant identical macros (heurbridge/evolve/prompts/skill_v0.md:8-10).
4. **The cell-stage sketch did not help.** Both DREAMPlace demos, the S1 fine-tune and the S2 predictor missed their
   pre-set bars (reports/demo_sketch_start.md:34, reports/sketch_finetune_s1.md:45,
   reports/sketch_predictor_s2.md:38). *Negative results.*
5. **Narrow data.** Round 0 has 1,608 pairs from 13 IBM designs, and later rounds added no new information
   (reports/T3_algorithmR_trackA.md:55-60). Known data defect: on 15 of 17 IBM designs the top elite's cluster target
   was a quadratic placement (CHANGELOG.md:206-210). It affects clusters, not macro targets.

## 3 Levers

| Lever | What changes | Expected effect on the gap | Cost (estimate) | Risk |
|---|---|---|---|---|
| A. Targets at or below the tool | re-pair every source with the nearest elite whose J <= the tool's (the tool's layout where nothing better exists), then fine-tune | removes the cap of reason 1; the only lever aimed at it | re-pairing from cached sources: CPU minutes; one fine-tune about 1-1.5 GPU-h (S1 used 8,000 steps: reports/sketch_finetune_s1.md); evaluation about 3 GPU-h | single far target per design: larger, harder moves; may not generalize to held-out designs |
| B. Better-than-tool elites | local search starting from the tool's layout under f1 on the training designs, admitting layouts below 0.45 | creates targets that beat the tool (reason 2) | 100-200 f1 runs per design x 13 designs at 9-18 s each (reports/T2_trackA_ibm_dreamplace.md:27-43): about 4-13 GPU-h | the tool's layout may be locally optimal under f1: few or tiny gains |
| C. More than one training family | add ISPD2005 pairs to the IBM pairs | broader generalization; does not lift the cap (ISPD targets are also at or above the tool: reports/T2_trackA_ispd_dreamplace.md:38) | pair generation plus retraining: about 1 GPU-day (estimate) | ISPD2005 stops being a held-out family; a future confirmatory test needs another held-out family |
| D. Cluster loss weight or a dedicated cluster head (today 0.1 x area: heurbridge/bridge/graph.py:13) | weight 10 was tried in S1 (ft_both) | low: S1 missed its bar on ibm04 for every model (reports/sketch_finetune_s1.md:36-45); clusters do not set Track-A J directly | one fine-tune | none new |
| E. Condition on the committed macros (the look-ahead) | feed a cell-stage prediction to the macro bridge | low so far: the S2 predictor ranks layouts poorly on ibm04 (Kendall tau 0.152) and no better than the quadratic placement on ibm06 (0.523) (reports/sketch_predictor_s2_ranking.md) | medium | the predictor misses both parts of its bar |
| F. Richer sketch format (centroid, footprint, density, RUDY) | the hand-off to the cell stage | low on Track-A J: DREAMPlace ignores start positions (reports/demo_sketch_start.md:34) | medium | as before |
| G. Reframe the claim | "a learned scoring device for heuristics", the claim G0' supports | closes nothing; states the result honestly | none | weaker paper claim |

## 4 Recommended first experiment: lever A (targets at or below the tool), one fine-tune

- **Change (one):** re-pair the 13 training designs' cached sources with the nearest elite of J <= the tool's J
  (0.45 + 5e-4, the audit's tolerance); fine-tune the frozen bridge (sha256 f95bdde8...,
  checkpoints/bridge_v1_e0_frozen/MANIFEST.json:4) for 8,000 steps at lr 1e-4, as S1 did.
- **Design split:** training = the 13 IBM training designs (reports/T3_algorithmR_trackA.md:19); model selection on
  V = ibm04, ibm06; report on T = ibm08, ibm12 (held out from training and selection: reports/E0_preregistration.md:32).
  ISPD2005 stays untouched as the held-out family for any later confirmatory test.
- **Endpoint:** on T, per source: guarded post-bridge DREAMPlace-f1 J of the new bridge against the frozen bridge
  (same sources, same guard, paired); and the share of refined layouts with J <= 0.45.
- **Success (prediction of the plan):** mean J on T falls against the frozen bridge, and some refined layouts reach
  J <= 0.45.
- **Falsification:** no refined layout on T reaches J <= 0.45, and the paired mean J does not fall (one-sided
  Wilcoxon, heurbridge/stats/paired.py:41). Then cost targets are not what holds the bridge back, and the next step is
  lever B or the reframing (lever G).
- **Stopping rule:** one fine-tune only; the checkpoint is chosen on V before T is evaluated; no second attempt
  without the owner's decision.
- **Compute:** re-pairing CPU minutes; fine-tune about 1-1.5 GPU-h on 225; evaluation 2 designs x 32 sources x 4
  alphas x about 10 s per f1 run for each of V and T, about 1 GPU-h each (estimates from
  reports/T2_trackA_ibm_dreamplace.md:30-37 run times).
- **Status:** exploratory demo when run; no protocol is changed (E0 and its frozen checkpoint stay as registered).
