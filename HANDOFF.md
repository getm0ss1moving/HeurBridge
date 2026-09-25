# HeurBridge — session handoff log

Newest entry first.  Each entry: what was done, commands, artifacts, open issues.

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

**Environment.** Local repo `/Users/duanzeyu/Desktop/HeurBridge` (git `main`, remote
`github.com/getm0ss1moving/HeurBridge`). HA-PR harness used from `/Users/duanzeyu/Desktop/heura_repro_en/eda`
(the task list's `/Users/duanzeyu/Desktop/papers/heura_repro` no longer exists; the English copy is the only
local checkout). Local venv: Python 3.11, torch 2.14 (CPU), PyG 2.8.

**T0.1 inherit state (local): PASS.**
```bash
cd /Users/duanzeyu/Desktop/heura_repro_en/eda && export HEURA_EDA_BASE=$PWD
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
