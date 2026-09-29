# HeurBridge-PR — progress against the task list (T0–T7)

Status as of **2026-09-29 13:10 CST**, code `7ecfc68` (v0.14.0 + unreleased). Measured against
`HEURBRIDGE_TASKS.md` (Part C tasks, Part D gates). Session history: `HANDOFF.md`; every code change: `CHANGELOG.md`.

## 1. Summary

- **Position on the critical path:** T0 ✅ → T1 ✅ → T2 (Track-B seeding: 2 of 5 designs complete) → T3 ✅ (exit
  gate passed) → **T4 = full E0 / gate G0′ running: 10 of 16 design × protocol parts complete (13:47)** (blinded: no result
  has been read) → T5 → T6. **G0′ expected 30 Sep late evening – 1 Oct morning** (bigblue4 sets the date).
- **Roughly 42 % of the planned effort is done** (weighted by the task list's own duration estimates, §5). The done
  part is the infrastructure: toolchains on the servers, data, evaluators f0/f1/f2, the 7 heuristic families,
  archive, the bridge and its training. The remaining part is mostly the **experiments** (E0, LLM evolution,
  E1/E2, H1–H9): compute-bound and gated — **G0′ can stop the project** (task list Part D).
- **Remaining time if every gate passes:** about 6–9 weeks (T4 ≈ 1 week incl. compute, T5 ≈ 2 weeks, T6 ≈ 3–5 weeks).

## 2. What is running right now

| Server | Job | Task | State | Expected |
|---|---|---|---|---|
| 225 GPUs 0–3 | `e0x_{spec,eq}_adaptec1` | **full E0** adaptec1 | 380 / 376 of 390 rows | ≈ 13:30 today |
| 225 | `e0x_spec_bigblue1_ibm08` → ibm08, `e0x_eq_bigblue1_spec_ibm12` → ibm12 | **full E0**, E0#3 held-out IBM designs (bigblue1 done in both jobs) | ibm08 388 of 480 rows; ibm12 170 of 390 | ibm08 ≈ 15:00, ibm12 ≈ 18:00 today |
| 225 | `e0x_{spec,eq}_bigblue4` (slices 0–3), `e0x_{spec,eq}_bigblue4_w45` (slices 4–5) | **full E0** bigblue4, whole on 225: 30 legal sources (of 80), budgets 2259 / 2231 s, memory-lean RUDY (`HB_RUDY_IMPL=bmm`) | 12 slices running (sources 0–22), 1–2 rows each after 2 h: ≈ 4 h per case | slices 0–5 ≈ 30 Sep 01:00–05:00; slices 6–7 (sources 22–30) start then (memory) → **bigblue4 ≈ 30 Sep 19:00–22:00** |
| 231 GPU 4 | `e0x_eq_bigblue3` (4 slices), `e0x_spec_bigblue3_r2` (sources 25–38, re-run of the OOM-killed slice) | **full E0** bigblue3 (spec slices 0, 1, 3 done: 37 of 50 cases) | eq 275 of 300 rows; spec re-run 64 of 78 | ≈ 14:30–16:00 today |
| 224 (3 jobs × 8 threads) | `seedB_orfs7_{swerv_wrapper, ariane136, ariane133}` | T2.7 Track-B seeding (bp_fe_top, bp_be_top **complete**, reports committed) | f1 rows 21 / 77 / 59; noise-band replays done | several days |

**Done in the full E0 (both protocols, checked for completeness only):** adaptec2, adaptec3, adaptec4, bigblue1 —
390 rows = 65 cases × 6 partners each, exit code 0, no duplicate case.

**What I just did (28 Sep 19:50 – 29 Sep 13:00):**
- **Restarted the full E0 as slices** (your approval, 19:52): every component keeps its sources, partners and first
  measured time budget; the recomputed random-control scale matched the original probe's exactly on all five
  restarted designs.
- **Found and fixed an out-of-memory kill** (bigblue3 spec slice 2 at 22:46, 21 GB): RUDY's three-operand einsum
  builds an 18 GB temporary without `opt_einsum`. Fix: a memory-lean equivalent (`HB_RUDY_IMPL=bmm`, used for
  bigblue4 only, so every design stays internally consistent) and a per-host slot cap; the killed slice was re-run
  from its 11 finished rows (bit-identical settings). The watcher now reports kernel OOM kills, stalled slices and
  low memory. A placer run killed by the host OOM killer is now re-run instead of being scored as a failure.
- **Moved bigblue4 whole to 225** (sources saved encrypted on 231 and copied as ciphertext; identical sha256).
- **Track B:** bp_fe_top and bp_be_top finished; reports re-score every row under cost_v2 and add the signoff (f2)
  results (§3, T2.7). The report generator now records the Yosys the flow actually runs (0.48).
- **Cleanup survey** of the HeurAgenix reproduction folders (your request, §6).

## 3. Status per task

Legend: ✅ done · 🔄 running · ⚠️ done with a limitation · ⏸ waiting for your decision · ⬜ not started

### T0 — Environment and feasibility ✅

| Sub-task | Status | Evidence / note |
|---|---|---|
| T0.1 inherit state | ✅ | `ENV_REPORT.md` |
| T0.2 probe servers | ✅ | `ENV_REPORT.md` (224, 225, 227; 225 approved by you) |
| T0.3 recent OpenROAD / ORFS | ✅ | OpenROAD 676f8451 built from source (the ORFS 2024-12 pin); **ariane133 through detailed routing: DRC 0, bit-identical repeats** (`ENV_REPORT.md`) |
| T0.4 benchmarks | ✅ | IBM (ICCAD04), ISPD2005, ORFS Nangate45 designs with sha256 manifests (`configs/manifests/`) |
| T0.5 Python env, GPU | ⚠️ | 225: env + GPU smoke PASS (`reports/env/gpu_smoke_225.txt`); 224/227 CUDA broken by a faulty GPU (admin); ChipDiffusion cloned but not reproduced (no licence; checkpoints on Google Drive) — the bridge uses our own backbone (spec fallback) |
| T0.6 LLM client + budget ledger | ✅ | DeepSeek self-test PASS |

### T1 — Data model, contract, fidelity ladder ✅

| Sub-task | Status | Evidence / note |
|---|---|---|
| T1.1 design object, loaders | ✅ | round trips on 26 bookshelf + 18 LEF/DEF designs (`reports/T1_roundtrip_*.json`) |
| T1.2 contract checker | ✅ | `heurbridge/core/contract.py`, tests |
| T1.3 f0 (GPU-batched) | ✅ | `heurbridge/eval/f0.py` |
| T1.4 f1 | ✅ | Track A: DREAMPlace 4.3.1 (macros fixed); Track B: ORFS to global routing |
| T1.5 f2 / f3 | ⚠️ | f2 = ORFS to 6_report (Track B). f3 signoff (KLayout DRC/LVS) not possible on the servers (no KLayout) — only via local OpenLane on a sample |
| T1.6 cost J and gates | ✅ | `heurbridge/eval/cost.py`, weights frozen (`configs/cost.yaml`) |
| T1.7 seed baselines | ✅ | Track A: 25 designs; Track B: 5 ORFS designs × 2 deterministic runs |

### T2 — Heuristic population, projections, archive 🔄 (T2.7 Track B)

| Sub-task | Status | Evidence / note |
|---|---|---|
| T2.1 program contract + sandbox | ✅ | `heurbridge/evolve/sandbox.py` (V0) |
| T2.2 macro seeds (≥ 7 families) | ✅ | M1 (tool-native) + M2–M7, 16 program versions |
| T2.3 / T2.4 cell and route seeds | ✅ | `heuristics/cell`, `heuristics/route` |
| T2.5 projections P_M / P_C / P_R | ✅ | `heurbridge/core/project.py` |
| T2.6 elite archive | ✅ | `heurbridge/archive/` |
| T2.7 seeding, Track A | ✅ | IBM 17 designs `reports/T2_trackA_ibm_dreamplace.md`; ISPD2005 8 designs `reports/T2_trackA_ispd_dreamplace.md` |
| T2.7 seeding, Track B | 🔄 | **bp_fe_top and bp_be_top complete** (`reports/T2_trackB_orfs_bp_fe_top.md`, `…_bp_be_top.md`; cost_v3: gates vs the same-path replay): at signoff 16 / 9 of 20 layouts pass every gate, 14 / 7 of them below the unmodified flow (best 0.881 / 0.931, local search); the same-path replay of the tool's own layout scores 1.323 / 1.103 (band of one-site shifts 1.03–1.40 / 1.02–1.16); f1–f2 Kendall tau 0.51 / 0.78. Descriptive: candidates need their own noise band before any claim. swerv_wrapper, ariane136, ariane133 running. Many heuristic layouts fail ORFS (GRT-0116 congestion, DPL-0036, 2-h timeouts; identical failing layouts are no longer re-run). **Findings:** (1) the failures come from ORFS 2024-12's timing-driven global placement diverging on scattered layouts (the same layout places fine with it off); (2) M1's own layout imported like a candidate scores worse than base M1 (bp_fe_top f2: J 1.32 vs 1.00, nearly all TNS) because Hier-RTLMP pre-places the standard cells — so candidates are paired with this same-path replay, and a per-design noise band (M1 shifted by one site/row) decides what counts as an improvement. Estimate: several more days |

### T3 — The bridge ✅ (T3.9 after G0′)

| Sub-task | Status | Evidence / note |
|---|---|---|
| T3.1–T3.3 data, model | ✅ | `heurbridge/bridge/` |
| T3.4 pretraining (warm start) | ✅ | `reports/T3_pretrain_small.md` |
| T3.5–T3.6 loss, training, validation | ✅ | `heurbridge/bridge/train.py` |
| T3.7 Algorithm R | ✅ | round 0 promoted (T3 exit gate: J 0.4815 vs raw 0.8870, p = 2.6e-9), round 1 promoted (0.4756, p = 1.2e-4), round 2 not promoted → final checkpoint round 1 (`reports/T3_algorithmR_trackA.md`) |
| T3.8 guarded inference | ✅ | `heurbridge/bridge/sample.py` |
| T3.9 cell / route bridges | ⬜ | only after G0′ passes (task list) |
| T3.10 unit tests 1–6 | ✅ | `tests/test_bridge.py` (138 tests pass in total) |

### T4 — E0 partner ablation, gate G0′ 🔄

| Sub-task | Status | Evidence / note |
|---|---|---|
| partners + E0 driver | ✅ | `heurbridge/partners.py`, `scripts/run_e0.py` |
| development E0 (local, CPU) | ✅ | `reports/E0_partner_ablation_dev*.md` (suggestive only) |
| E0 demo (225) | ✅ | positive direction: the co-trained bridge has the lowest J under both protocols (`reports/E0_demo_spec.md`, `reports/E0_demo_eq.md`); much of the gain comes from the f1 guard (random direction + guard is close), the learned direction still beats it (p = 2.3e-9) |
| **full E0 (confirmatory, G0′)** | 🔄 | pre-registered (`reports/E0_preregistration.md`, ledger E0#1–#3) and running on 225 (4 GPUs) + 231 (GPU 4): ISPD2005 7 designs × both protocols, ibm08/ibm12; the pooled G0′ test (E0#1) when all runs end. Revised 19:00: CPU-bound and slower than estimated; `run_e0.py --slice` (commit 9f38847) splits a component over processes under the same protocol; restarted as slices 28 Sep 19:52 (approved). 29 Sep 13:00: adaptec2, adaptec3, adaptec4, bigblue1 complete in both protocols; adaptec1, bigblue3, ibm08/ibm12 finish today; bigblue4 (30 sources, ≈ 4 h per case) ≈ 30 Sep 19:00–22:00 → pooled G0′ right after |

### T5 — LLM evolution ⏸ (after G0′)

| Sub-task | Status | Evidence / note |
|---|---|---|
| T5.1–T5.4 prompts, fitness, population, RLCE | ✅ | `heurbridge/evolve/`; end-to-end with a mock LLM (`scripts/run_evolution.py --llm mock`) |
| T5.5 baseline engines | ✅ | five proposers implemented |
| T5.6 knowledge loop | ⬜ | later (after H1) |
| real evolution runs | ⬜ | need G0′ pass and the LLM choice (§6) |

### T6 — Online solving and main experiments ⬜ (mostly)

| Sub-task | Status | Evidence / note |
|---|---|---|
| T6.1 online pipeline | ✅ | `heurbridge/online/solve.py` |
| T6.2 E3 calibration, gate G0 | 🔄 | Track A done: IBM `reports/E3_calibration_trackA_dreamplace.md`, ISPD2005 `reports/E3_calibration_trackA_ispd.md` — **G0 not met** on both (f0 is not an admissible proxy for f1; the f1 guard stays). Track B pending the campaign |
| T6.3 E1, T6.4 E2, T6.5 H1–H9 / A1–A11 | ⬜ | weeks of compute after T4/T5 |

### T7 — Verification, statistics, reporting (continuous) ✅ so far

V0 sandbox, V1 metamorphic tests, V2 contract/legality, V5 promotion gate: implemented (`heurbridge/verify/`); V3
pin-geometry check (`reports/V3_*.json`); V4 signoff limited (no KLayout on the servers). Statistics
(`heurbridge/stats/`), α-ledger (`stats/alpha_ledger.jsonl`; the two T3.7 entries are merged when the job ends),
report template (`reports/templates/`), originality tool (`heurbridge/verify/originality.py`).

## 4. Gates (Part D)

| Gate | Status |
|---|---|
| T0 exit (a track available) | ✅ both tracks |
| T3 exit (bridge beats raw on validation, paired) | ✅ passed (p = 2.6e-9); caveat: its guard uses the same f1 as the final cost |
| **G0′** (bridge beats memetic and repertoire, p < 0.01) | ⏸ next — decides whether the project continues as planned |
| G0 (proxy admissible) | ❌ not met on Track A (IBM, ISPD2005); Track B pending → fitness stays at f1 |
| G1, G2, G3, G4 | ⬜ later (T5, T3.9, T6) |

## 5. How far from completion

Effort weights are the midpoints of the task list's own estimates; completion fractions are my assessment.

| Task | Planned effort | Done | Done (days) |
|---|---|---|---|
| T0 | 1.5 d | 95 % | 1.4 |
| T1 | 5 d | 95 % | 4.8 |
| T2 | 6 d | 90 % | 5.4 |
| T3 | 8.5 d | 80 % | 6.8 |
| T4 | 3.5 d | 60 % | 2.1 |
| T5 | 12 d | 30 % | 3.6 |
| T6 | 28 d | 10 % | 2.8 |
| **Total** | **64.5 d** | **≈ 42 %** | **26.9** |

T7 runs alongside and is not weighted separately. The estimate assumes every gate passes; a G0′ failure ends the
planned path at T4 ("stop and report", with a repositioning decision for you).

## 6. Decisions

Received 2026-09-28: LLM = **deepseek-flash** for every LLM call; timing gates **reported at f1, enforced at f2/f3**
(cost_v2); each experiment runs as a **demo on 225 first**, then at full capacity if the effect is good.

Received 2026-09-28: 231 approved for the full E0 (GPU 4 only); restart of the full E0 as slices approved (19:52).
Received 2026-09-29: clean the HeurAgenix reproduction folders HeurBridge does not need. Staged (moved, reversible)
into `/data/dzy/heura_repr/_to_delete_20260929/` on 224 (68 GB: eda/runs*, models, envs/heura, envs/miniconda3,
repo, datasets, output, logs, results, evidence) and 231 (7 GB: envs, models, repo, datasets, output, logs; its
results/ kept). The final delete is yours to run (I cannot delete files permanently). Kept on 224: hb, envs/hb,
tools, cache, third_party, benchmarks, eda/{harness,flow,tools,pdk,...}, src, build.

Received 2026-09-29 (afternoon): **Track-B timing gates referenced to the same-path replay** (cost_v3, done: code,
tests, both Track-B reports re-scored); **225's reproduction monitors stopped** (`b_monitor`, `b_reason_monitor`;
the other tmux sessions there, `agent1`, `agent2`, `tmp`, belong to another project -- `taorui/auto_project` -- and
were left alone) and 225's reproduction folders staged for deletion (31 GB; result tables and docs kept).

Open:
1. **Stop the 4 newest bigblue4 slices?** (`e0x_{spec,eq}_bigblue4_w45`, launched 11:25.) 12 bigblue4 slices bring
   225 to within ~17 GB of its memory at peaks; stopping them does not change bigblue4's finish (the last slices
   wait for memory either way) and removes the risk. They run protected meanwhile (first OOM victims; killed placer
   runs are re-run). My recommendation: stop them.
2. **Hold gate under cost_v3:** on bp_be_top the same-path replay has +0.055 ns hold slack, so B.3's "no more
   than 0.02 ns worse" now fails candidates that still have positive hold slack (13 → 9 admitted). Keep B.3 as
   frozen, or check hold only for new violations (cand ≥ 0)? A change to a frozen rule is your call.
3. Housekeeping: back up `~/.config/heurbridge/vault.key` (without it the server vault cannot be decrypted); ask
   the admin about the faulty GPUs on 224 / 227.

## 7. Deviations and known limitations

- Full E0: bigblue4 has 30 legal sources (only 30 of its 80 program runs project legally) and uses the memory-lean
  RUDY (`HB_RUDY_IMPL=bmm`, equal to the reference to ~1e-6); bigblue3 spec's slice 2 was OOM-killed and re-run
  from its 11 finished rows as two sub-slices (same settings, bit-identical scale). Neither changes the registered
  protocol; both are listed for the report.
- ariane133 runs with `RTLMP_MAX_LEVEL=1` (upstream's MPL workaround); ORFS's own macro placer does not converge
  otherwise at the 8-thread cap. Everything else is the 2024-12 configuration.
- Track A has no f2 (bookshelf benchmarks have no timing): its final cost is f1 (DREAMPlace).
- bigblue2 (23,084 macros) cannot run the heuristic programs: the dense macro affinity exceeds the sandbox's 4 GB.
- On every Track-A design DREAMPlace's own mixed-size placement (M1) is the best layout found by seeding; the
  heuristics beat it on 2 of 25 designs only. The bridge's targets are therefore mostly M1-like layouts.
