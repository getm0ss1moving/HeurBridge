# Next phase: decisions for the owner

| Field | Value |
|---|---|
| Report | next_phase_decisions |
| Date | 2026-10-02 |
| Status | decision sheet: options, evidence, recommendation. Nothing listed here has been launched; every protocol stays as registered. |

## Re-prioritization under the owner's aim (3 Oct)

The owner set the first aim: **macro layouts with mean Track-A J below 0.45, shown to beat the tool on output and
on cost**, and delegated the priorities. Evidence that shaped them: the heuristics' layouts are 3-35 % worse than
the tool's in wirelength on almost every IBM design, and none of them has less congestion than the tool on the
congested designs (seeding ledgers `runs/seed_trackA_dp/<design>/evals.jsonl`, local; per-design numbers in
reports/T2_trackA_ibm_dreamplace.md:27-43). So the shortest route below 0.45 starts from the tool's own layout.

| Priority | Item | Decision |
|---|---|---|
| 1, running | Beat-the-tool feasibility demo (`scripts/beat_tool_demo.py`, 12 IBM designs on 225 and 231): the tool's layout, the tool with three more seeds (more compute), the frozen bridge applied to the tool's layout, local search from the tool's layout; all scored by f1 with wall-clock | launched 3 Oct; exploratory |
| 1 | f1-seed noise band of every best layout against the tool's band (`scripts/beat_tool_band.py`) | after the demo; a result below 0.45 counts only if its whole band is below the tool's |
| 2 | Equal-compute comparison: "tool + learned refiner" against "the tool's best of k seeds" at the same wall-clock, on held-out designs, many tool seeds | next, if the demo shows room; pre-registered before its held-out run |
| 2 | Refiner retrained for this job: sources = the tool's layouts from several seeds, targets = better-than-tool layouts found by local search on the training designs (levers A and B of reports/gap_to_tool_plan.md, re-scoped) | after the demo |
| 3 | Track-B confirmatory test (D6) | kept as a draft; output only, no cost advantage yet |
| laid aside | T5 LLM demo (D1), ariane133 re-run (D2), T3.9 cell bridge (D3), S2 (D4: recorded negative), f3 tools (D7) | revisit when the Track-A route is settled |

Not applicable: DREAMPlace's routability mode on these benchmarks. It always builds a congestion map that needs
per-layer routing capacities, which the IBM Bookshelf files lack (third_party/DREAMPlace/dreamplace/PlaceObj.py:250-257;
the demo's runs fail with that error). Using it would require a tool modification, so the tool's fair
more-compute baseline is more seeds of its default mode.

Capacity: 227's three RTX 3090 GPUs are idle; 225's environment and DREAMPlace build were copied there (public
software) and the encrypted inputs copied as ciphertext with matching sha256 (3 Oct). 227's DREAMPlace smoke test
reproduces 231's result exactly (HPWL 2,568,479.75 on ibm01; reports/env/dp_smoke_231.txt).

**First results (3 Oct, exploratory; reports/beat_tool_track_a.md):**
- Local search from the tool's layout: its whole f1-seed band lies below the tool's on 7 of 12 designs, but the gains
  are small (median J 0.4314-0.4497) and cost 8-28 minutes per design against 23-46 s for the tool.
- The frozen bridge on the tool's layout: equal to the tool's best of two seeds at equal compute (24 cases on ibm04,
  ibm06, ibm08: difference +0.0011, p = 0.61).
- **Relinking two tool runs** (guarded partial transport from one tool layout toward another): lower than the
  tool's best of three seeds at about equal compute in 14 of 24 cases (4 higher), mean 0.4375 against 0.6067
  (one-sided Wilcoxon p = 0.004); without ibm08, whose tool layouts often blow up under other f1 seeds,
  0.4377 against 0.4392. This is the most promising lead and is being run on the other 14 IBM designs.
- f1 itself is noisy and heavy-tailed on some designs, so every comparison picks with one f1 seed and judges with
  three fresh seeds (median).

**Next, in order:** (1) relinking on all 17 IBM designs (running); (2) the confirmatory test on the held-out
ISPD2005 family, untouched by any of this exploration: **registered and launched on 3 Oct 03:40**
(reports/relink_preregistration.md, alpha-ledger RL#1); (3) a refiner that learns the relinking move from a single tool
run, to cut the second tool run from the cost; (4) the refiner pairs from local search (running on 225) are kept as a
second data source.

Two choices in (2), made under the owner's delegation: the comparator is the tool's best of **four** runs, not three,
because a tool run and an f1 run take about the same time on ISPD2005 (reports/T2_trackA_ispd_dreamplace.md:27-34),
so relinking (two tool runs, five f1 runs) costs about 7 run-units against 8 for best of four and 6 for best of three:
passing against best of four shows a lower J at lower cost. And it runs in parallel with (1) instead of after it: its
procedure is fixed and cannot depend on the IBM results, the GPUs were free, and the price of a failure is campaign RL's
first alpha (0.025), recorded either way.

## D1 Launch the T5 demo?

- **Evidence:** G0' passed, which per the pre-registration leads to T5 (reports/E0_partner_ablation.md:44,
  reports/E0_preregistration.md:40). The T5 code is ready: a DREAMPlace-f1 guard as in E0, a no-LLM control arm,
  programs blind to the design's identity, kept sources, and a held-out endpoint. The mock smoke test passed on 225
  (reports/t5_demo_preregistration.md, Section 9). *Infrastructure.* The draft fixes the designs, arms, endpoint,
  test and a mechanical five-part decision rule before any data (reports/t5_demo_preregistration.md, Sections 3-5).
- **Options:** (a) approve the draft and launch: two arms on 225 GPUs 0-1 (about 3-4 h), then the endpoint on V and T
  (about 3 h each), at most 110 LLM calls; (b) approve with changes (more generations or designs: cost grows about
  linearly); (c) wait for the gap experiment (D5) first.
- **Recommendation: (a).** The demo is cheap, its decision rule is fixed, and it tests the LLM's value against a
  control at equal budget, independently of the gap to the tool. The full campaign has open blockers either way
  (reports/t5_demo_preregistration.md, Section 7).

## D2 ariane133: diagnose further, adopt a flow deviation, or drop?

- **Evidence:** reports/trackB_ariane133_diagnosis.md. Every failing layout's global placement stops at the
  5,000-iteration cap with overflow near 0.3 instead of 0.10; the resizer then adds about 110,000 buffers and
  detailed placement fails. The tool's own layout shifted by one site fails the same way, so the flow configuration
  is fragile, not only the heuristics. *Development / descriptive.* Probes (five layouts, f1): with PLACE_DENSITY 0.35, 4 of 5 complete with
  setup TNS no worse than -0.15 ns and the fifth fails with a named divergence (GPL-0307); with virtual resizing all
  5 complete but two carry large setup violations (TNS -50.7 ns and -1.02 ns) (reports/trackB_ariane133_diagnosis.md,
  Section 3).
- **Options:** (a) adopt PLACE_DENSITY 0.35, the value ariane136 sets, for every ariane133 run including the
  baseline, and re-run its campaign (about one to two days on 224, estimate); (b) adopt virtual timing-driven
  resizing (`-keep_resize_below_overflow 0.01`) the same way; (c) drop ariane133 from Track B as a documented
  deviation.
- **Recommendation: (a)**, PLACE_DENSITY 0.35 for every ariane133 run including the baseline, then re-run the
  campaign; (c) if the re-run baseline itself fails. The deviation is chosen after seeing the probes and is recorded
  as such; it applies to the baseline and every candidate alike, so J stays normalized to the same flow.

## D3 T3.9: the cell bridge's endpoint

- **Evidence:** the task list ranks the cell bridge's targets by f2 J (HEURBRIDGE_TASKS.md:372), but Track A has no
  f2; its final cost is DREAMPlace f1 (reports/PROGRESS.md:268). DREAMPlace ignores start positions
  (reports/demo_sketch_start.md:34), so a cell bridge cannot hand its result to DREAMPlace; it must deliver a placement.
  The look-ahead predictor misses both parts of its bar (reports/sketch_predictor_s2.md:38,
  reports/sketch_predictor_s2_ranking.md). *Negative results.*
- **Options:** (a) Track A: f1 J (the f1 evaluator's own metrics and cost) of the cell bridge's placement after P_C,
  against DREAMPlace's placement of the same macro layout, paired per macro layout on held-out designs; (b) Track B:
  f2 J with the cell placement imported as a full warm start (OpenROAD keeps one:
  HEURBRIDGE_PLAN_downstream_aware.md:42-44); (c) a fidelity endpoint (distance to the tool's placement, DA3).
- **Recommendation: (a) as the primary endpoint, (b) as the second.** (a) asks the question that matters, beating the
  tool's own cell placement with the registered cost, and needs no new tool port. (c) measures imitation, which
  cannot beat the tool by construction.

## D4 S2 predictor follow-up

- **Evidence:** distance bar missed (DA0 0.747 / 0.642 against <= 0.5: reports/sketch_predictor_s2.md:38); ranking
  bar missed on ibm04 (Kendall tau 0.152) and met on ibm06 (0.523) (reports/sketch_predictor_s2_ranking.md). Under the
  same scoring the placed clusters themselves reach only tau 0.441 on ibm04: the bar there is above what the true
  cluster positions achieve, so a cluster-level predictor is very unlikely to meet it. The one allowed change, the bridge's augmentation, also misses the distance bar:
  best step 8,000, DA0 0.777 (ibm04) and 0.611 (ibm06), mean criterion 0.694 against 0.695 without it
  (reports/sketch_predictor_s2_aug.md); it overfits less but trades ibm04 for ibm06, and it ranks worse on both designs (Kendall tau 0.114 and 0.401).
- **Options:** (a) record S2 as a negative result now (both runs miss the distance part, so neither can pass the bar); (b) keep iterating on S2 (regularization, a smaller model), one change at a time; (c) replace the
  cluster-level scoring by a cell-level one before any further S2 work.
- **Recommendation: (a).** Keep the bar as fixed. S2 is not on the critical path: T5 and the gap experiment do not
  need it.

## D5 Gap to the tool: run the first experiment?

- **Evidence:** 62 % of the bridge's training pairs target elites that cost more than the tool
  (reports/bridge_target_audit.md:29). The plan's first experiment re-pairs to targets at or below the tool and runs
  one fine-tune (reports/gap_to_tool_plan.md, Section 4).
- **Options:** (a) run it on 225 (about 3-4 GPU-hours, estimate); (b) run lever B (better-than-tool elites) first;
  (c) reframe the claim now ("a scoring device for heuristics").
- **Recommendation: (a)**, after or alongside the T5 demo. It is cheap, and its falsification criterion is stated.

## D6 Track-B confirmatory test

- **Evidence and draft:** reports/trackB_preregistration.md: one pre-selected candidate per design, six fresh shifts
  per arm, the whole-band rule as an exact permutation test (p = 1/924 when the bands separate), alpha-ledger
  campaign TB.
- **Options:** (a) approve and run on bp_fe_top, bp_be_top and ariane136 (36 f2 runs on 224); (b) wait for
  swerv_wrapper and the ariane133 decision (D2) to test all designs at once.
- **Recommendation: (a)** for the three complete designs; the other two join only through their own TB entries.

## D7 Signoff tools (f3)

- **Evidence:** reports/signoff_anchor_readiness.md: KLayout, Magic and Netgen are missing on 224; the nangate45 LVS
  deck is absent from the checkout; the RAM macros have no layout data.
- **Options:** (a) approve third-party binary downloads (conda packages) and a DRC-only f3 on a sample, with the
  macros as black boxes (a documented deviation); (b) keep f2 as the strongest Track-B fidelity and say so in every
  claim.
- **Recommendation: (b) for now, (a) before any production or state-of-the-art claim.**

## D8 Housekeeping (owner's actions; nothing was deleted)

- **Staged for deletion** (moved there on 29 Sep: HANDOFF.md:413-414; sizes measured 2 Oct):
  `/data/dzy/heura_repr/_to_delete_20260929/` on 224, 68 GB (its /data at 93 % use); on 225, 31 GB (/data at 99 %);
  on 231, 7.1 GB (root at 99 %). The final `rm -rf` is yours.
- **Faulty GPUs:** `nvidia-smi` fails on 224 ("Unable to determine the device handle for GPU 0000:02:00.0: Unknown
  Error") and on 227 (the same for GPU 0000:21:00.0), checked 2 Oct; the server admins need to reset or replace
  them.
- **Vault key:** `~/.config/heurbridge/vault.key` on the Mac (scripts/hbv.py:8, :47). Without it every encrypted
  run archive is unreadable. Whether an offline backup exists is not documented in the repo. Keep a copy in a
  password manager or on offline media; it must never be committed or copied to the servers.
