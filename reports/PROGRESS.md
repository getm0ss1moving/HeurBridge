# HeurBridge-PR — progress against the task list (T0–T7)

Status as of **2026-09-28 14:00 CST**, code `9546dd4` (v0.14.0 + unreleased). Measured against
`HEURBRIDGE_TASKS.md` (Part C tasks, Part D gates). Session history: `HANDOFF.md`; every code change: `CHANGELOG.md`.

## 1. Summary

- **Position on the critical path:** T0 ✅ → T1 ✅ → T2 (Track-B seeding still running) → T3 (exit gate **passed**;
  Algorithm R round 2 of max 3 running) → **T4 = E0 / gate G0′ started: demo running on 225** → T5 → T6.
- **Roughly 40 % of the planned effort is done** (weighted by the task list's own duration estimates, §5). The done
  part is the infrastructure: toolchains on the servers, data, evaluators f0/f1/f2, the 7 heuristic families,
  archive, the bridge and its training. The remaining part is mostly the **experiments** (E0, LLM evolution,
  E1/E2, H1–H9): compute-bound and gated — **G0′ can stop the project** (task list Part D).
- **Remaining time if every gate passes:** about 6–9 weeks (T4 ≈ 1 week incl. compute, T5 ≈ 2 weeks, T6 ≈ 3–5 weeks).

## 2. What is running right now

| Server | Job | Task | State | Expected |
|---|---|---|---|---|
| 225 GPUs 0–3 (16 processes) | `e0x_{spec,eq}_adaptec4` (3 slices each), `e0x_{spec,eq}_adaptec3` (2 each), `e0x_spec_bigblue1_ibm08`, `e0x_eq_bigblue1_spec_ibm12`, `e0x_{spec,eq}_adaptec2`, `e0x_{spec,eq}_adaptec1` | **full E0** (pre-registered E0#1–#3, commit d186667), restarted 19:52 as slices with the user's approval (commit 9f38847: same sources, partners, budgets and tests; cases done before the restart kept) | running | ≈ 29 Sep 07:00–09:00; adaptec1 (one process per protocol, budgets 221.8 / 219.3 s measured 20:39) ≈ 14:00–15:00 |
| 231 GPU 4 (8 processes) | `e0x_{spec,eq}_bigblue3` (4 slices each) | **full E0**: bigblue3 (spec keeps its measured budget 845 s; eq measures its own) | running since 19:53 | ≈ 29 Sep midday |
| 225, after the designs above | bigblue4 (spec, eq), whole on 225 | **full E0**: bigblue4; sources saved (encrypted `save_src_bigblue4`, sha256 62daf302…) | queued | ≈ 30 Sep |
| 224 (5 jobs × 8 threads) | `seedB_orfs7_{bp_fe_top, bp_be_top, swerv_wrapper, ariane136, ariane133}` (continuing earlier runs) | T1.7 / T2.7 Track-B seeding on the real ORFS 2024-12 flow | base runs done (deterministic); candidates so far: 40 / 47 / 4 / 24 / 13; now the same-path M1 control and the noise band (M1 shifted by one site/row), then the remaining candidates | several days (see §3, T2.7) |

**What I just did:** the Track-B validity control passed — ORFS's own macro placement replayed through our import
converges like the base run, so candidates that fail global placement (ariane133, swerv_wrapper) fail because of
their layouts. The probe also found that Hier-RTLMP pre-places every standard cell (a warm start that imported
layouts do not get); M1 is therefore now also evaluated through the candidates' path, and candidate deltas are paired
with that same-path control. The five ORFS jobs were continued (`hbv.py run --resume-from`) with this control and
with reuse of deterministic failures (identical layouts no longer re-run a 1–2 h failure). Everything is monitored
automatically (completions, failures, thread cap, orphaned processes).

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
| T2.7 seeding, Track B | 🔄 | 5 ORFS designs running (§2). Many heuristic layouts fail ORFS (GRT-0116 congestion, DPL-0036, 2-h timeouts; identical failing layouts are no longer re-run). **Findings:** (1) the failures come from ORFS 2024-12's timing-driven global placement diverging on scattered layouts (the same layout places fine with it off); (2) M1's own layout imported like a candidate scores worse than base M1 (bp_fe_top f2: J 1.32 vs 1.00, nearly all TNS) because Hier-RTLMP pre-places the standard cells — so candidates are paired with this same-path replay, and a per-design noise band (M1 shifted by one site/row) decides what counts as an improvement. Estimate: several more days |

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
| **full E0 (confirmatory, G0′)** | 🔄 | pre-registered (`reports/E0_preregistration.md`, ledger E0#1–#3) and running on 225 (4 GPUs) + 231 (GPU 4): ISPD2005 7 designs × both protocols, ibm08/ibm12; the pooled G0′ test (E0#1) when all runs end. Revised 19:00: CPU-bound and slower than estimated; `run_e0.py --slice` (commit 9f38847) splits a component over processes under the same protocol; restarting the running jobs as slices awaits the user's approval; G0′ ≈ 30 Sep–1 Oct with slices |

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
| T2 | 6 d | 85 % | 5.1 |
| T3 | 8.5 d | 80 % | 6.8 |
| T4 | 3.5 d | 25 % | 0.9 |
| T5 | 12 d | 30 % | 3.6 |
| T6 | 28 d | 10 % | 2.8 |
| **Total** | **64.5 d** | **≈ 39 %** | **25.4** |

T7 runs alongside and is not weighted separately. The estimate assumes every gate passes; a G0′ failure ends the
planned path at T4 ("stop and report", with a repositioning decision for you).

## 6. Decisions

Received 2026-09-28: LLM = **deepseek-flash** for every LLM call; timing gates **reported at f1, enforced at f2/f3**
(cost_v2); each experiment runs as a **demo on 225 first**, then at full capacity if the effect is good.

Open:
1. **Another server for the full runs?** You mentioned running the full experiment "in another port at the same
   time". 225's four GPUs are approved and will be used; 231 (5 × RTX 4090) needs your explicit approval (red line),
   224 / 227 have no working CUDA.
2. Housekeeping: back up `~/.config/heurbridge/vault.key` (without it the server vault cannot be decrypted); ask
   the admin about the faulty GPUs on 224 / 227.

## 7. Deviations and known limitations

- ariane133 runs with `RTLMP_MAX_LEVEL=1` (upstream's MPL workaround); ORFS's own macro placer does not converge
  otherwise at the 8-thread cap. Everything else is the 2024-12 configuration.
- Track A has no f2 (bookshelf benchmarks have no timing): its final cost is f1 (DREAMPlace).
- bigblue2 (23,084 macros) cannot run the heuristic programs: the dense macro affinity exceeds the sandbox's 4 GB.
- On every Track-A design DREAMPlace's own mixed-size placement (M1) is the best layout found by seeding; the
  heuristics beat it on 2 of 25 designs only. The bridge's targets are therefore mostly M1-like layouts.
