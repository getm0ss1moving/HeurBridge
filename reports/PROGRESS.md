# HeurBridge-PR — progress against the task list (T0–T7)

Status as of **2026-09-28 13:25 CST**, code `369689d` (v0.13.4 + unreleased fixes). Measured against
`HEURBRIDGE_TASKS.md` (Part C tasks, Part D gates). Session history: `HANDOFF.md`; every code change: `CHANGELOG.md`.

## 1. Summary

- **Position on the critical path:** T0 ✅ → T1 ✅ → T2 (Track-B seeding still running) → T3 (exit gate **passed**;
  Algorithm R round 2 of max 3 running) → **T4 = E0 / gate G0′ is next** (needs your protocol decision) → T5 → T6.
- **Roughly 40 % of the planned effort is done** (weighted by the task list's own duration estimates, §5). The done
  part is the infrastructure: toolchains on the servers, data, evaluators f0/f1/f2, the 7 heuristic families,
  archive, the bridge and its training. The remaining part is mostly the **experiments** (E0, LLM evolution,
  E1/E2, H1–H9): compute-bound and gated — **G0′ can stop the project** (task list Part D).
- **Remaining time if every gate passes:** about 6–9 weeks (T4 ≈ 1 week incl. compute, T5 ≈ 2 weeks, T6 ≈ 3–5 weeks).

## 2. What is running right now

| Server | Job | Task | State | Expected |
|---|---|---|---|---|
| 225 GPU 0 | `algR_trackA2` | T3.7 Algorithm R (Track A, 13 IBM training + 2 validation designs) | round 0 **promoted** (= T3 exit gate), round 1 **promoted**, round 2 training | round 2 result ~16:30; round 3 (if promoted by ≥ 0.5 %) ~20:30 |
| 224 (5 jobs × 8 threads) | `seedB_orfs6_{bp_fe_top, bp_be_top, swerv_wrapper, ariane136, ariane133}` (continuing `seedB_orfs5_*`) | T1.7 / T2.7 Track-B seeding on the real ORFS 2024-12 flow | base runs done on all five (deterministic); candidates so far: 40 / 47 / 4 / 24 / 13; now evaluating the same-path M1 control, then the remaining candidates | several days (see §3, T2.7) |
| 224 (1 job) | `probe_ariane133_place` | validity control for Track B | control **passed** (import is sound); remaining diagnostic variants running | ~1 h |
| 225 GPU 1 | — | free (ISPD2005 campaign finished) | — | reserved for E0 |

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
| T2.7 seeding, Track B | 🔄 | 5 ORFS designs running (§2). Many heuristic layouts fail ORFS (GRT-0116 congestion, DPL-0036, 2-h timeouts); failures are recorded by name. Estimate: 2–4 more days for bp_*, longer for ariane/swerv unless the failure reuse speeds them up |

### T3 — The bridge 🔄

| Sub-task | Status | Evidence / note |
|---|---|---|
| T3.1–T3.3 data, model | ✅ | `heurbridge/bridge/` |
| T3.4 pretraining (warm start) | ✅ | `reports/T3_pretrain_small.md` |
| T3.5–T3.6 loss, training, validation | ✅ | `heurbridge/bridge/train.py` |
| T3.7 Algorithm R | 🔄 | round 0 promoted: bridge J 0.4815 vs raw heuristics 0.8870, p = 2.6e-9 (ledger `algR_trackA#1`); round 1 promoted: 0.4756 vs 0.4815, p = 1.2e-4 (`algR_trackA#2`); round 2 running. Report `reports/T3_*` when it ends |
| T3.8 guarded inference | ✅ | `heurbridge/bridge/sample.py` |
| T3.9 cell / route bridges | ⬜ | only after G0′ passes (task list) |
| T3.10 unit tests 1–6 | ✅ | `tests/test_bridge.py` (138 tests pass in total) |

### T4 — E0 partner ablation, gate G0′ ⏸

| Sub-task | Status | Evidence / note |
|---|---|---|
| partners + E0 driver | ✅ | `heurbridge/partners.py`, `scripts/run_e0.py` |
| development E0 (local, CPU) | ✅ | `reports/E0_partner_ablation_dev*.md` (suggestive only) |
| **pre-registered E0** | ⏸ | needs the final T3.7 checkpoint (today) **and your protocol decision** (§6) |

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

## 6. Waiting for you

1. **E0 protocol (T4, before it is pre-registered).** In the spec the co-trained bridge's guard sees f1 while the
   memetic and repertoire partners decide on f0 — the bridge can win through the guard alone. Proposal: keep the
   spec's comparison as the primary G0′ test and pre-register `--equal-guard` (every partner guarded at the same
   fidelity) and `--random-control` (the bridge's guard along a random direction) as secondary analyses. Also the
   design set: held-out ibm08 / ibm12 (≈ 0.5–1 GPU-day on one 225 GPU), and whether ISPD2005 (the held-out family,
   7 usable designs) is included (≈ 4–5 more GPU-days, mostly bigblue3/4; ~2–3 days on two GPUs). "Cost" here is
   compute time only: E0 makes no LLM calls and the servers are the lab's (the only paid resource is the DeepSeek
   API in T5).
2. **T5 LLM model:** `deepseek-v4-pro` (about 4× the price) or `deepseek-flash` (what the old `deepseek-reasoner`
   name maps to now).
3. **Timing gates at f1:** proposal — report them at f1, enforce them only at f2 / f3 (they predict f2 badly).
4. Housekeeping: back up `~/.config/heurbridge/vault.key` (without it the server vault cannot be decrypted); ask
   the admin about the faulty GPUs on 224 / 227.

## 7. Deviations and known limitations

- ariane133 runs with `RTLMP_MAX_LEVEL=1` (upstream's MPL workaround); ORFS's own macro placer does not converge
  otherwise at the 8-thread cap. Everything else is the 2024-12 configuration.
- Track A has no f2 (bookshelf benchmarks have no timing): its final cost is f1 (DREAMPlace).
- bigblue2 (23,084 macros) cannot run the heuristic programs: the dense macro affinity exceeds the sandbox's 4 GB.
- On every Track-A design DREAMPlace's own mixed-size placement (M1) is the best layout found by seeding; the
  heuristics beat it on 2 of 25 designs only. The bridge's targets are therefore mostly M1-like layouts.
