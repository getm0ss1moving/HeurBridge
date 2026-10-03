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
because a tool run and an f1 run take about the same time on ISPD2005 (reports/T2_trackA_ispd_dreamplace.md:29-36),
so relinking (two tool runs, five f1 runs) costs about 7 run-units against 8 for best of four and 6 for best of three:
passing against best of four shows a lower J at lower cost. And it runs in parallel with (1) instead of after it: its
procedure is fixed and cannot depend on the IBM results, the GPUs were free, and the price of a failure is campaign RL's
first alpha (0.025), recorded either way.

**Update 3 Oct 05:10 (exploratory; reports/beat_tool_track_a.md):**
- **Relinking does not generalize:** on all 17 IBM designs (136 cases) it is lower than the tool's best of four in
  29 cases and higher in 44, median difference 0 (Section 4). The three-design lead came from ibm08, whose tool
  layouts blow up under some f1 seeds. RL#1 runs to completion as registered and is reported either way; a failure is
  the likely outcome.
- **Consensus of tool runs: no** (Section 5). **Macro flipping:** J -0.0017 against one tool run (17 of 24 lower),
  nothing on top of best of two (Section 6).
- **Two levers move J a lot, both about how the tool is run:** (a) its target density: one run at 0.6 instead of 0.9
  lowers J by 0.0288 (32 of 32 lower) and beats the best of four at 0.9 in 29 of 32, with HPWL and congestion both
  lower (Section 7); (b) a second tool pass started from the first's layout: -0.0156 at 0.9 (20 of 24 lower;
  Section 8).
- **What this means for the owner's aim:** J = 0.45 is the tool at target density 0.9, which is neither DREAMPlace's
  parameter default (0.8: third_party/DREAMPlace/dreamplace/params.json:39-42) nor its benchmark setting (1.0:
  third_party/DREAMPlace/test/mms/adaptec1.json). Mean J below 0.45 is within reach of the tool's configuration
  alone, so "better than the tool" must from now on mean better than the tool at its best configuration; otherwise
  it is this effect, not a HeurBridge method.
- **Decisions (agent, under the delegation):** (i) RL#2 registered and launched at 05:02: one run at density 0.6
  against the best of four at 0.9 on ISPD2005, labelled a configuration claim (reports/density_preregistration.md);
  (ii) on IBM, whether a second pass or the flip pass adds anything on top of density 0.6 (running); (iii) every later
  HeurBridge comparison uses the tool at 0.6 as its baseline; (iv) Track-B D6 stays unlaunched (D6: the hold gate).

**Update 3 Oct 05:40 (exploratory; reports/beat_tool_track_a.md, Sections 7 and 9):**
- **Density, wider check:** at 0.7 on 13 IBM designs a single run is lower than at 0.9 in 67 of 104 cases, with
  gains on ibm02-04, ibm06, ibm07, ibm12 and losses on ibm01, ibm11, ibm13, ibm18 (one ibm09 case blows up under the
  fresh seeds). The choice of 0.6 for RL#2 rests on four designs of the favourable kind; RL#2 was registered before
  this check finished, so its prior is weaker than its draft suggests. It runs as registered.
- **On top of the tool at 0.6, nothing helps:** a second pass (+0.1427, one design blows up), heuristic starts
  (+0.0110), the flip pass (+0.0014) (Section 9).
- **Two densities vs two seeds** (the seed-s run at 0.9 and at 0.7, the better by the selection seed, against seeds s
  and s+1 at 0.9; same number of runs): lower in 66 of 104 cases, higher in 16. Registered as RL#3 on ISPD2005 with
  0.6, computed from RL#1's and RL#2's runs, no run added (reports/portfolio_preregistration.md).
- **Conclusion for Track A:** no HeurBridge method beats the tool at equal compute; the levers that move J are the
  tool's own configuration and how its runs are spent. Direction: D9.

**Update 3 Oct 08:25 (exploratory, after RL#2 and RL#3 were registered):** density 0.6 on all 13 IBM designs
(reports/beat_tool_track_a.md, Section 7): one run at 0.6 is lower than one run at 0.9 in 68 of 104 cases, but lower
than the best of four at 0.9 in only 61 (one-sided Wilcoxon p = 0.033): on IBM, RL#2's comparison would not pass its
alpha (0.0125); 0.6 is worse than 0.9 on ibm01, ibm11, ibm13 and ibm18. Two densities against two seeds: lower in 65,
higher in 20 (p = 3e-10), as RL#3 assumes. Both tests run as registered.

**Update 3 Oct 10:00: the ISPD2005 results and a defect** (reports/defect_ispd_tool_runs.md). The three analyses ran
once each at 09:46-09:47: RL#1 FAILED (p = 0.88); RL#2 and RL#3 passed their alpha. Then a pipeline defect showed: the
tool's input marked ISPD2005's macros as fixed terminals, so on 7 of 8 designs every tool run returned the benchmark's
own macro placement and every arm of the three tests is the same layout there (56-57 of 64 units tie). The passes rest
on bigblue3's 8 units alone; **none of the three tests is evidence for its claim.** Fixed in code (commit 157bf21);
the reports and the ledger carry notes. Also: on ISPD2005, J = 0.45 is the benchmark's macro placement, not the tool's.
Re-testing: D10.

## D9 Direction after the Track-A evidence (new, 3 Oct)

- **Evidence:** none of the HeurBridge methods tried (the frozen bridge on the tool's layout, relinking, consensus,
  the flip pass, local search, heuristic starts) beats the tool's best of k at equal compute on IBM; what beats the
  baseline is the tool run at another target density, or two densities instead of two seeds (reports/beat_tool_track_a.md,
  Sections 3-9). The heuristics' own layouts are 3-35 % worse than the tool's in wirelength (reports/T2_trackA_ibm_dreamplace.md:27-43).
  Three confirmatory tests on ISPD2005 are running (RL#1-RL#3).
- **Options:** (a) reframe Track A's contribution as automated tool orchestration: LLM-evolved programs that choose the
  tool's configurations and how its runs are spent per design under a run budget, judged on held-out designs against
  the best fixed configuration and against seeds at the same number of runs (T5's guard, control arm and held-out
  endpoint carry over; risk: close to parameter tuning such as AutoDMP, so the novelty must come from the programs and
  their transfer); (b) put the weight on Track B, the real OpenROAD flow, where our layouts beat the tool's own macro
  placement at f2 on three designs (descriptive; D6 needs the hold-gate rule; no cost advantage yet); (c) continue the
  original plan (T5 evolution of macro heuristics, the bridge) against the tool at its best configuration.
- **Recommendation: (a) and (b).** (a) aims at the lever that moves J on Track A with a cost claim; (b) is the only
  place where our own layouts beat a tool on real PPA. (c) stays laid aside: its gap to the tool is large.
- **Prepared (nothing runs):** a design note for (a), reports/orchestration_design.md.
- **Decided 3 Oct (owner):** (b), more effort on Track B; when Track B's seeding has finished, compare DREAMPlace's and
  HeurBridge's macro placements through the OpenROAD flow, next to the tool's own macro placement (a fair three-way
  comparison: neither DREAMPlace nor HeurBridge optimizes the flow's score). Track A stays the cheap testbed.
- **Correction (3 Oct, 23:00):** the parenthesis above is wrong for HeurBridge. Its Track-B candidates come from local
  search that scores every move with the flow itself at f1 and verifies the improving ones at f2
  (heurbridge/pipeline/seed_archive.py:269-296); all three registered candidates are local-search layouts. Only
  DREAMPlace never sees the flow's score. The comparison is registered with this asymmetry stated
  (reports/trackB_threeway_preregistration.md, Section 6): it compares layouts, not the two methods at equal flow budget.

## D10 Re-testing on ISPD2005 after the defect (new, 3 Oct)

- **Evidence:** reports/defect_ispd_tool_runs.md. RL#1-RL#3 are not evidence for their claims; the code is fixed.
  A corrected test needs new ISPD2005 tool runs that place the macros, registered before they run (8 designs x 8 seeds
  at 0.9 and 0.6: about the compute of RL#1's and RL#2's tool runs, 3-4 h on 3-4 GPUs).
- **Options:** (a) register a corrected test in campaign RL: RL#4, two densities {0.9, 0.6} against two seeds at 0.9,
  the effect that held on IBM (65 lower, 20 higher of 104 cases), at alpha_4 = 0.003125, on the 7 designs whose tool
  runs were never seen placing macros (bigblue3 excluded: its runs were seen), 56 units; (b) the same in a new campaign
  for corrected re-tests (alpha 0.05): more power, but a fresh budget after an invalid round must be declared and
  justified; (c) no confirmatory test now: use ISPD2005 as a second development family (for example, how the corrected
  tool's own placement compares with the benchmark's, J against 0.45) and find a fresh held-out family (downloads need
  your approval).
- **Recommendation: (a).** The IBM effect is strong (one-sided Wilcoxon p = 3e-10 on 104 cases); a similar effect on
  56 cases would pass alpha_4. The other two questions are not worth re-testing: relinking fails on IBM, and one run at
  0.6 against best of four at 0.9 is borderline there (p = 0.033).
- **Decided 3 Oct (owner): (a).** RL#4 registered (reports/portfolio_retest_preregistration.md, alpha 0.003125) after
  a check on bigblue3 showed the corrected tool moving every macro; seven jobs `rc4_*` running since 11:30.
- **Result (3 Oct, 22:37, analysed once):** RL#4 passed, p = 0.00014 against alpha_4 = 0.003125; median difference
  -0.0060 J, lower in 33 of 56 units, higher in 11 (reports/portfolio_retest_confirmatory.md). Confirmed: two tool runs
  at densities 0.9 and 0.6 beat two seeds at 0.9 on the held-out ISPD2005 designs; a claim about running the tool, not
  about a HeurBridge method.

## D1 Launch the T5 demo?

- **Evidence:** G0' passed, which per the pre-registration leads to T5 (reports/E0_partner_ablation.md:46,
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
  f2; its final cost is DREAMPlace f1 (reports/PROGRESS.md:291). DREAMPlace ignores start positions
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
- **Found 3 Oct (blocks the draft):** under cost_v3 the timing gates compare with the same-path replay band's median,
  and a candidate with negative slack fails whenever that median is non-negative (heurbridge/eval/cost.py:129-132).
  Hold slack on these designs is noise-level, -0.05 to +0.06 ns in the stored f2 rows (local run files
  `runs/remote/seedB_orfs7_*/runs/seed_orfs/*/evals_f2.jsonl`), so replicates would pass or fail at random:
  ariane136's pre-selected candidate has hold -0.03 ns against a replay median of +0.015 ns. The draft also gates
  the tool's own replicates against their own band, which would hand the candidate wins. **Needed from you:** the
  hold-gate rule for this test (for example the 0.02-ns guard without the sign rule); then the draft is revised
  (gates on the candidate only, the tool's replicates scored before the gates) and registered. The run phase exists
  (`scripts/run_seed_orfs.py --phase tbtest`) and is not launched.
- **Decided 3 Oct (owner):** the timing gates keep the 0.02-ns guard without the sign rule, for the Track-B tests
  (heurbridge/eval/cost.py `timing_sign_rule=False`; cost_v3's default unchanged). The protocol is registered
  (reports/trackB_preregistration.md: gates on the candidate only, the tool's replicates scored before the gates; exact
  rank-sum permutation test): TB#1 bp_fe_top, TB#2 bp_be_top, TB#3 ariane136, jobs `tb_*` on 224 since 11:52; TB#4
  swerv_wrapper when its campaign completes.
- **Results (3 Oct, 22:36, each analysed once; reports/trackB_confirmatory.md):** TB#1 bp_fe_top passed (p = 0.0022,
  alpha 0.025), TB#2 bp_be_top passed (p = 0.0011, alpha 0.0125), TB#3 ariane136 failed (p = 0.53): the hold gate
  failed on 3 of 6 shifts against a reference of +0.015 ns (four unshifted replays), although all six candidate
  replicates are below all six reference replicates before the gates. TB#1's pass rests on one replicate exactly at its
  hold threshold (p would be 0.047 one 0.01-ns step lower).

## D7 Signoff tools (f3)

- **Evidence:** reports/signoff_anchor_readiness.md: KLayout, Magic and Netgen are missing on 224; the nangate45 LVS
  deck is absent from the checkout; the RAM macros have no layout data.
- **Options:** (a) approve third-party binary downloads (conda packages) and a DRC-only f3 on a sample, with the
  macros as black boxes (a documented deviation); (b) keep f2 as the strongest Track-B fidelity and say so in every
  claim.
- **Recommendation: (b) for now, (a) before any production or state-of-the-art claim.**

## D8 Housekeeping (owner's actions; nothing was deleted)

- **Staged for deletion** (moved there on 29 Sep: HANDOFF.md:514-515; sizes measured 2 Oct):
  `/data/dzy/heura_repr/_to_delete_20260929/` on 224, 68 GB (its /data at 93 % use); on 225, 31 GB (/data at 99 %);
  on 231, 7.1 GB (root at 99 %). The final `rm -rf` is yours.
- **Faulty GPUs:** `nvidia-smi` fails on 224 ("Unable to determine the device handle for GPU 0000:02:00.0: Unknown
  Error") and on 227 (the same for GPU 0000:21:00.0), checked 2 Oct; the server admins need to reset or replace
  them.
- **Vault key:** `~/.config/heurbridge/vault.key` on the Mac (scripts/hbv.py:8, :47). Without it every encrypted
  run archive is unreadable. Whether an offline backup exists is not documented in the repo. Keep a copy in a
  password manager or on offline media; it must never be committed or copied to the servers.

## D11 The timing-gate reference for future Track-B tests (new, 3 Oct; nothing registered changes)

- **Evidence:** TB#3 failed on the hold gate although before the gates all six candidate replicates are below all six
  reference replicates: its reference is the median of four unshifted replays (+0.015 ns), while the tool's own
  shifted replicates have hold WNS -0.06 to 0.00 ns and fail the same check on 5 of 6 shifts; TB#1 passed with one
  replicate exactly at its threshold (reports/trackB_confirmatory.md, Summary).
- **Options for tests registered from now on:** (a) keep D6 as it is; (b) gate each candidate replicate against the
  tool's replicate at the same shift (paired), with the 0.02-ns guard and no sign rule: it compares like with like and
  needs no extra runs, since every test already runs the tool's replicates; (c) widen the guard to the tool's own spread
  across shifts.
- **Recommendation: (b) for future tests.** TB#4 and the three-way comparison (TW) keep D6 as registered.

## D12 An equal-budget comparison with DREAMPlace (new, 3 Oct; optional)

- **Evidence:** HeurBridge's Track-B candidates come from local search scored by the flow itself (45-48 f1 moves and
  f2 checks per design, heurbridge/pipeline/seed_archive.py:269-296); DREAMPlace's pick in the registered comparison
  sees the flow only in its selection (twelve f1 and four f2 runs; reports/trackB_threeway_preregistration.md,
  Section 6). The registered comparison therefore compares layouts, not the two methods at equal flow budget.
- **Options:** (a) the registered comparison only; (b) give DREAMPlace's pick the same local search (the campaign's
  eight steps of six neighbours at f1, the improving moves at f2) and test the result on the same six shifts: does
  HeurBridge's search do better from its own programs' starts than from DREAMPlace's? About 50 f1 and 8 f2 runs per
  design; (c) HeurBridge without its local search: the campaign's best admitted program layout (no local-search move)
  against DREAMPlace's pick on the same six shifts: 6 f2 runs per design, isolates the heuristic programs from the
  flow-scored search.
- **Recommendation:** decide after the TW results; (c) is cheap and answers the narrower question of whether the
  programs alone beat DREAMPlace through the flow.
