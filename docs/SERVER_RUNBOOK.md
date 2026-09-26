# Server runbook (shared lab account: encrypted workflow)

The lab login is shared by several people, so everything of ours on the server is **encrypted at rest**
(`scripts/hbv.py`): the server keeps ciphertext only (`/data/dzy/heura_repr/hb/vault/` on 224), the key
stays on the Mac (`~/.config/heurbridge/vault.key`, 0600 — back it up), and every job decrypts into a RAM
workspace (`/dev/shm/hbw.*`) that is wiped when the job ends. The key reaches a job only through the stdin of
its SSH session (never a server file, command line or environment variable). Plaintext exists only while a job
runs. Never copy repository files to the server in plaintext (the old `sync_to_server.sh` was removed).

Rules (task file A.2): EDA work on **224** (backup 234); 225/231 only with explicit approval; never kill
processes we did not start (`pgrep -x openroad -a`, per-GPU `nvidia-smi -i N`); OpenROAD `EDA_THREADS=8`,
at most 8 parallel jobs, 7200 s per job. On 224 and 227 GPU 0 is faulty (plain `nvidia-smi` fails): use GPU 1
(default) or 2.

## Where things live on 224

| Path | Content | Encrypted |
|---|---|---|
| `/data/dzy/heura_repr/hb/vault/{code,data,runs}` | code snapshots, data bundles, run outputs | yes |
| `/dev/shm/hbw.*` | workspaces of running jobs | plaintext while running, wiped at the end |
| `/data/dzy/heura_repr/tools/{micromamba,openroad_new}` | third-party software | no (public) |
| `/data/dzy/heura_repr/envs/hb` | Python environment | no (public packages) |
| `/data/dzy/heura_repr/benchmarks`, `/data/dzy/heura_repr/third_party` | public benchmarks, ORFS checkout | no (public) |
| the LLM key file (path in the local lab note) | managed by the user; read by the client via `DEEPSEEK_API_KEY_FILE` | no (runtime secret) |

Hosts without a writable `/data` (e.g. 227) use a transient vault in `/tmp/.hbv` (cleared on reboot and by
systemd-tmpfiles): fetch results promptly.

## Workflow (from the Mac)

```bash
python scripts/hbv.py push-code --port 224
python scripts/hbv.py run --port 224 --run <id> --gpu 1 -- "<command>"
python scripts/hbv.py status --port 224 --run <id>
python scripts/hbv.py fetch --port 224 --run <id>
```
`run` options: `--after <id0>` (unpack an earlier run's outputs first), `--resume` (unpack this run's last
partial snapshot), `--data NAME:DEST` (a bundle uploaded with `push-data`), `--snapshot SECONDS`,
`--exclude REGEX` (paths not to archive), `--api-key-file <key file>`. `fetch` writes to
`runs/remote/<id>/` on the Mac; `stop` ends our own job (its process group).

## T0

```bash
python scripts/hbv.py run --port 224 --run t0_t01 -- "bash scripts/server/t0_server.sh t01"
python scripts/hbv.py run --port 224 --run t0_install --api-key-file <key file> -- "bash scripts/server/t0_server.sh t03; bash scripts/server/t0_server.sh t05; bash scripts/server/t0_server.sh t06"
```
t01 runs the HA-PR inheritance checks on a temporary copy of `eda/` (the original is never written); t03
installs a recent OpenROAD + Yosys and probes it and OpenROAD 2022; t05 builds the `hb` env and runs the GPU
smoke test; t06 is the 16-token LLM self-test.

## Later tasks (commands run inside `hbv.py run`)

- T1.7 / T2.7 Track A: `python scripts/run_seed_archive.py --suite ibm ...` with the DREAMPlace / HB-GP f1.
- Track B (ORFS on the new OpenROAD, or `heurbridge/eval/miniflow.py` as the fallback): seeding with
  `OrfsEvaluator` (f1 = `grt`, f2 = `finish`).
- T3.4 pretraining on GPU 1: `/data/dzy/heura_repr/envs/hb/bin/python scripts/pretrain_bridge.py --steps 200000 --batch 64 --device cuda --out checkpoints/pretrain_small`
- T3.7 Algorithm R: `scripts/algorithm_r.py ... --guard f1 --device cuda`; T4 E0: `scripts/run_e0.py ... --guard-fidelity f1 --equal-guard --random-control`.
