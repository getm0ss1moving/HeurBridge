# HeurBridge — session handoff log

Newest entry first.  Each entry: what was done, commands, artifacts, open issues.

---

## 2026-09-27 — Session 3: server access, encrypted workflow, T0 on 224

**Access.** Key-only SSH works on ports 224, 225, 227, 231, 232, 234 (the lab note `LAB_PORTS_AND_API_KEY.md`
is local-only). The login is shared by several people: everything of ours on the servers goes through
`scripts/hbv.py` (encrypted vault, key on the Mac, RAM workspaces wiped at job end) — see `docs/SERVER_RUNBOOK.md`.
Back up `~/.config/heurbridge/vault.key`: without it the vault cannot be decrypted.

**T0 on 224** (details in ENV_REPORT s.6): T0.1 PASS; T0.4 benchmarks uploaded and verified; T0.6 DeepSeek PASS;
T0.5 env built but **CUDA fails on 224 and 227** (faulty GPU 0 breaks the driver: report to the admin);
**225's four RTX 3090 work but need the user's approval** (A.2); T0.3: conda OpenROAD builds lack Hier-RTLMP and
`place_macro` — a prebuilt 2024-12 package (.deb, unpacked without root) awaits approval to download.

**Running:** `seedA_ibm` on 224 — T1.7/T2.7 Track-A seeding of 17 IBM designs with the deterministic HB-GP f1
(outputs in the vault; `python scripts/hbv.py fetch --port 224 --run seedA_ibm` when done).

**Decisions for the user:** (a) GPU 225 for T3.4 pretraining / T3.7 training; (b) download the prebuilt OpenROAD
package for Track B; (c) ask the admin to reset the faulty GPUs on 224/227.

---

## 2026-09-26 — Session 2: audit of the work so far, Track-B flow fixed and aligned with ORFS, T5 driver

**Server access still blocked** (key-only SSH to 224/227/234: publickey denied), so all work is local.

**Audit findings (each fixed, tested, and in CHANGELOG 0.10.0 / Unreleased)**
- Track-B mini-flow was not ORFS-faithful: placement density 0.6 (ORFS platform default 0.30), core margin 2,
  generic tracks, no tapcells / power grid / port buffers / dont-use. Now layered ORFS config + the ORFS stage
  order (macros -> tapcell -> pdngen -> GP -> resize -> DP -> GRT).
- f1 lost 7 of 18 evaluations: `estimate_parasitics -global_routing` is broken in the local OpenROAD
  (bad_alloc exit, segfault, OOM kill) -> timing/power from placement parasitics for every layout; GR timing
  opt-in. `report_power` segfaulted once the grid existed -> bisected to pdngen's VDD/VSS block pins.
  Every failure is named; the baseline is evaluated 3x (bit-identical at 6 threads; thread count matters).
- FastRoute stopped with GRT-0119 on congested layouts, so OF could never be measured -> `-allow_congestion`.
- P_M: (a) largest-first greedy failed on 0.5% of dense layouts -> fallback orders incl. bottom-left
  packing (1,000/1,000 legal); (b) Track-B spacing must be 2 x MACRO_PLACE_HALO (per-side halo in
  rtl_macro_placer); with 1 x the edge channels broke pdngen on 6 of 16 layouts (PDN-0179).
- V0 certificate rejected every program on real designs (NaN != NaN for unplaced cells) — found by the first
  end-to-end evolution dry run. RLCE groups were unbounded (one 246-macro "group") -> bounded to 8.
- The earlier f0-vs-f1 calibration JSON scored one layout per design -> redone (`scripts/calibrate_dev.py`).
- Run metadata recorded the end-of-run commit with the start-of-run code version -> commit at start.
- Local absolute paths removed from tracked docs; reports relativize paths; dev archives untracked.

**Development results (no claims; stand-ins for the server experiments)**
- T1.1: bookshelf load -> write -> load identity on all 26 designs (`reports/T1_roundtrip_bookshelf.json`).
- E3-lite (one row per distinct layout): f0 J0 (the guard's scorer) vs f1 — Track A (HB-GP,
  `reports/E3_calibration_dev_ibm.md`) Kendall 0.70 / 0.51 / 0.16 on ibm01 / 02 / 03; Track B (mini-flow,
  `reports/E3_calibration_dev_bp_fe_top.md`) Kendall 0.35, top-5 recall 0, f0's pick worse than random. G0 rule
  not met on either track: f0 must not make macro-stage decisions (the spec's f1 guard / fitness stand).
- T3 dev bridge (`reports/T3_bridge_macro_dev.md`): f0 criterion 2.0125 vs raw 2.0411 on ibm03 (91% of sources
  improved) while the validation residual and terminal error rose.
- E0 dev on held-out ibm04 / ibm06 (`reports/E0_partner_ablation_dev.md`; 16 programs x 5 seeds, every partner
  decides on f0, final J = HB-GP f1): G0' dev **FAIL** (co-trained vs memetic p = 0.99, vs repertoire p = 0.68;
  ledger E0_dev#1). The bridge's mean J is lower (0.509 vs raw 0.587) only because it rescues catastrophic
  sources (M5.v1: J 3.45 -> 0.76); paired vs raw it wins 71 / loses 89 (median +0.0004; ibm06: 15 / 40): the
  f0 guard accepts moves that f1 rejects. Portfolio J (best program per design) is the same for all partners
  (0.429-0.432). With the bridge's guard at f1 and the equal f1 guard for the others (E0_dev#2), G0' passes
  (p = 2.1e-5 / 0.0052) — but a random displacement of matched length with the same guard does as well as the
  bridge (geometric-mean J ratio vs raw 0.933 vs 0.931, bridge vs control p = 0.071; E0_dev#3), and HB-GP was
  not reproducible in these runs (winner's curse on noise). **Deterministic rerun with all controls**
  (`reports/E0_partner_ablation_dev_deterministic.md`, E0_dev#4): G0' criterion met (p = 8.6e-5 / 0.0061), the
  learned-transport check inconclusive (bridge vs random direction p = 0.056: 22 : 1 for the bridge on ibm06,
  6 : 11 on ibm04). With a CPU-trained 2-design bridge this is suggestive only; the server E0 decides.
- Track-B dev seeding on bp_fe_top with the corrected flow (`reports/T2_trackB_dev_bp_fe_top.md`): 80/80
  evaluations completed, gates passed on 62% (all failures setup WNS), 15 distinct gated layouts beat the M1
  baseline (J 0.95); best M5.v0 0.8559; dev archive top-5 0.856-0.879 (fidelity 1).
- Track-B f2 verification (`reports/E3_calibration_dev_bp_fe_top_f1f2.md`; ORFS-style staged f2: CTS,
  repair_timing, DRT, OpenRCX): 14/14 layouts routed with DRC 0. f1 -> f2 Kendall 0.50; the f1 gates predict
  the f2 gates badly (10 of 12 f1-passing layouts fail at f2; one f1-failing layout passes). Two layouts beat
  M1 with every f2 gate passed: M4.v2 J 0.959 (gated out at f1) and M3.v0 0.989. The best f2 J (M3.v2 0.9445,
  better setup WNS than M1) fails only because its met hold slack (+0.074 ns) is > 0.02 ns below M1's (+0.095).

**New tools**: `scripts/run_evolution.py` (T5 driver; `--llm mock` dry runs, all five proposers work end to
end), `scripts/run_f2_miniflow.py` + `MiniflowF2Evaluator` (Track-B dev f2: CTS, repair_timing, GRT, DRT,
fill, OpenRCX, STA — untested on the tool yet), `scripts/calibrate_dev.py`, `run_e0.py --guard-fidelity
--equal-guard`.

**Open issues / decisions for the user (additions)**
8. E0 protocol (T4, before it is pre-registered) — supported by the dev runs above: the co-trained bridge's guard sees f1, memetic and
   repertoire decide on f0 only. With a weakly calibrated f0 (Kendall 0.03-0.65 above) the bridge can win
   through the guard's access to f1 alone. Proposal: run E0 with `--equal-guard` (every partner's output
   kept only if it beats the raw layout at the same fidelity) and `--random-control` (the bridge's guard along
   a random displacement of matched length); both are implemented. Also required: reproducible evaluators
   (fixed thread counts; HB-GP was not) and a final cost evaluated independently of the guard's evaluations
   (on the server the f1 guard and the f2 final cost are separate runs, which already satisfies this).
9. Timing gates at f1 — now with f2 evidence: at f1 (pre-CTS, no timing repair) 38% of bp_fe_top layouts fail
   the 0.02 ns setup-WNS gate against M1, but the f1 gates predict the f2 gates badly (10 of 12 f1-passing
   layouts fail at f2, and the best gated f2 layout, M4.v2, was gated out at f1). Proposal: at f1 report the
   gates but rank by J before the gates; enforce the gates at f2/f3 (needs your decision: frozen rule B.3).
   Related: the frozen guard also fails a *met* check whose slack shrinks by > 0.02 ns (hold +0.095 -> +0.074
   ns keeps the best f2 layout out). If that is not intended, a "met stays met" rule for positive baselines is
   the alternative — your call; nothing was changed.
10. The (1+OF) term (open issue 6) is confirmed on Track B: GR overflow 8 against a zero-overflow baseline
    raises J from ~0.95 to 2.14.

---

## 2026-09-25 — Session 1 (later): local Track-B flow, dev bridge training, overflow-proxy fix

**Local Track B (development).** `heurbridge/eval/miniflow.py` runs a minimal Nangate45 flow in the local
OpenLane container (OpenROAD b16bda7e, Yosys 0.38; current ORFS does not run there). On `nangate45/bp_fe_top`:
hierarchical synthesis 15 s, floorplan 4 s, tool-native `rtl_macro_placer` (M1) 285 s, f1 126 s (GR WL 1.758e6 um,
overflow 0, setup WNS -2.20 ns / TNS -310.9 ns pre-CTS, hold +0.086 ns, 0.128 W). Placement/GR results are
deterministic across repeats; the old build segfaults intermittently after GR (evaluator retries once and
records the crash). `place_macro -exact` is not available in this build (made optional).
*[2026-09-26: these are flow-v1 values (density 0.6, no tapcells/power grid, GR-stage timing); superseded —
see the 2026-09-26 entry.]*
```bash
nohup .venv/bin/python scripts/run_seed_miniflow.py --design nangate45/bp_fe_top --seeds 2 > logs/seed_miniflow_bp_fe_top.log 2>&1 &
```
The first attempt failed on every candidate because of `-exact` (a harness bug, recorded as eval_failed);
its records are kept in `runs/seed_miniflow/bp_fe_top/failed_attempt_1/`.

**Track-A overflow proxy fixed.** Raw RUDY overflow in microns made (1+OF)~ explode against zero-overflow
baselines (ibm02 J up to 2e4; an artificial 25% "gain" on ibm03). Proxy is now `rudy_of_pct`; the development
archive was rebuilt from stored records: `archive_dev_v2` (`scripts/rescore_archive.py`). With it the benchmark
macro positions are the best layout on ibm01-03 and the seed heuristics are 1.8-9.5% worse.

**Dev bridge (round 0).** `scripts/train_bridge.py --train ibm01,ibm02 --val ibm03 --archive archive_dev_v2`
(CPU, 1.13M params, 256 pairs). Guarded post-projection f0 on held-out ibm03: 2.0393 / 2.0389 / 2.0322 vs raw
2.0411 at steps 400 / 800 / 1200 (up to 0.44% better; the guard picks alpha > 0 for 40-53% of sources).
Development evidence only (two training designs, f0 criterion); not the T3 exit gate.

**Also added:** ODB loader (verified on nangate45 gcd), V5 promotion gate + H8 null injection, ORFS signoff
stage (f3), MMD^2, Algorithm R driver, report generators, `docs/SERVER_RUNBOOK.md`, T1 baseline table (dev).

**Open issues (additions)**
6. The (1+OF)~ normalization also makes the Track-B J very sensitive when the baseline GR overflow is ~0
   (decision for the user: keep frozen weights, or use e.g. log(1+OF) / an absolute cap).
7. The bridge is not conditioned on x^h (deviation from T3.2, evidence in CHANGELOG 0.3.0).

---

## 2026-09-25 — Session 1 (continued): T0.4 local, T1-T7 software, first development campaign

**Server access is still blocked** (key not authorized), so everything below ran on the Mac. Versions v0.2.0 ..
v0.8.x are on GitHub (`getm0ss1moving/HeurBridge`, tags `v*`); CHANGELOG.md lists every change.

**Done (local, tested; 100+ tests)**
- T0.4 benchmarks on the Mac with sha256 manifests (`configs/manifests/`): IBM-MSwPins bookshelf + LEF/DEF,
  ISPD2005 (originals offline; Drive copy, header statistics match), ORFS Nangate45 macro designs (sparse clone).
- T0.3 probe on the local OpenLane OpenROAD (b16bda7e): every required command and flag present
  (`reports/env/openroad_probe_local_openlane_b16bda7e.txt`). `ENV_REPORT.md` is a draft.
- T1.4 f1 (OpenROAD Track-B script + parser; Track-A metrics; HB-GP dev placer), Track-B ORFS glue
  (`eval/orfs.py`: MACRO_PLACEMENT_TCL injection, stage grt = f1, finish = f2).
- T2.2 seed population (16 programs, V0-certified), T2.5 P_M, T2.6 archive, T2.7 driver (resumable).
- T3 bridge (graph, model, pairs + symmetry matching, loss, trainer, guarded inference); all T3.10 unit tests
  pass. Deviation: no x^h conditioning (evidence in CHANGELOG 0.3.0).
- T4 partners + E0 driver; T5 prompts/skill v0, RLCE, fitness, MAP-Elites, engine with 5 proposers;
  T6.1 online solve (macro stage); T6.2 calibration + gate G0; T7.1 V1 metamorphic tests; T7.2/7.3 stats and
  alpha ledger; T7.5 originality check.

**Development campaign (Track-A stand-in, NOT a pre-registered experiment)**
```bash
.venv/bin/python scripts/run_seed_archive.py --suite ibm --designs ibm01,ibm02,ibm03 --evaluator hbgp \
    --out runs/seed_dev --archive archive_dev --min-fidelity 1
```
Archive `archive_dev/` (labelled DEV, fidelity 1). ibm01 top J: baseline 0.450, best heuristic 0.493;
ibm02: 0.450 / 0.458 (Track-A partial J = 0.30 rWL~ + 0.15 (1+OF)~ with HPWL and RUDY proxies).

**Open issues / decisions for the user**
1. SSH key authorization (blocks T0.1-server, T0.2, T0.3 install, T0.5, and every real f1/f2 run).
2. DeepSeek key: put `DEEPSEEK_LAB_API_KEY` in the server environment (not in chat).
3. Track-A cost: bookshelf designs have no timing/power; J uses rWL (HPWL proxy) + OF (RUDY proxy) only,
   and Track-A archives would admit fidelity-1 elites. Needs your confirmation.
4. HB-GP is a stand-in (not DREAMPlace) and does not converge on ibm18; DREAMPlace must be built on the server.
5. `eda/harness/lef_def.py` orientation handling (CHANGELOG 0.1.0 findings) -- **confirmed 2026-09-26 with
   OpenROAD's pin geometry** (`reports/V3_pin_geometry_vs_openroad.json`: OpenROAD = HeurBridge exactly;
   lef_def +5.25..5.96% on spm). Decision for the user: revise the HA-PR `hpwl_um` numbers or not.

---

## 2026-09-25 — Session 1: T0.1 (local), T1 foundations

**Environment.** Local clone of `github.com/getm0ss1moving/HeurBridge` (git `main`). HA-PR harness: the
English copy `heura_repro_en/eda` next to the repo on the Mac, exported as `$HEURA_EDA_BASE` (the task list's
`papers/heura_repro` no longer exists). Local venv: Python 3.11, torch 2.14 (CPU), PyG 2.8.

**T0.1 inherit state (local): PASS.**
```bash
cd "$HEURA_EDA_BASE"    # the HA-PR harness (English copy)
python3 harness/smoke_test.py            # SMOKE_TEST_PASS
python3 harness/session_status.py        # v2=222, control coverage 46/46
python3 harness/validate_replay_v2.py    # VALIDATE_REPLAY_V2_PASS
python3 harness/build_checkpoint_dataset.py --strict   # 46 decisions / 176 samples / 0 errors
```
Server side (224) pending: SSH key not yet authorized (see open issues).

**T1.1–T1.3, T1.6 (local).** See CHANGELOG 0.1.0. Tests: `.venv/bin/python -m pytest -q tests` → 27 passed.

**Open issues**
1. **Server access blocked.** Password login is not used by the agent. A dedicated key
   `~/.ssh/id_ed25519_heurbridge` was created; the owner must authorize it once:
   `for p in 224 225 226 227 228 229 230 231 232 233 234; do ssh-copy-id -i ~/.ssh/id_ed25519_heurbridge.pub -p $p <user>@<host>; done`.
   Port 223 closed the connection during probing.
2. `lef_def.py` orientation handling (CHANGELOG findings) — verify with OpenROAD `odb` pin coordinates.
3. `DEEPSEEK_LAB_API_KEY` is not set locally; needed for T0.6 and T5.
