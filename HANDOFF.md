# HeurBridge — session handoff log

Newest entry first.  Each entry: what was done, commands, artifacts, open issues.

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
5. `eda/harness/lef_def.py` orientation handling (CHANGELOG 0.1.0 findings) -- confirm with OpenROAD on 224.

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
