# Server runbook (shared lab account: encrypted workflow)

The lab login is shared by several people, so everything of ours on the server is **encrypted at rest**
(`scripts/hbv.py`): the server keeps ciphertext only (`/data/dzy/heura_repr/hb/vault/` on 224), the key
stays on the Mac (`~/.config/heurbridge/vault.key`, 0600 — back it up), and every job decrypts into a RAM
workspace (`/dev/shm/hbw.*`) that is wiped when the job ends. The key reaches a job only through the stdin of
its SSH session (never a server file, command line or environment variable). Plaintext exists only while a job
runs. Never copy repository files to the server in plaintext (the old `sync_to_server.sh` was removed).

Rules (task file A.2): EDA work on **224** (backup 234); 225/231 only with explicit approval (225's GPUs
approved on 2026-09-27; use one or two and leave the rest free); never kill processes we did not start
(`pgrep -x openroad -a`, per-GPU `nvidia-smi -i N`); OpenROAD `EDA_THREADS=8`, at most 8 parallel jobs, 7200 s
per job. CUDA does not initialize on 224 and 227 (their GPU 0 is faulty and breaks the driver): GPU jobs run on 225.

Directories we did not create are never written (the HA-PR tree `/data/dzy/heura_repr/eda` is read only; on
other hosts we write only under `/tmp/.hb*`). hbv jobs set `PYTHONDONTWRITEBYTECODE=1` and the harness import shim
suppresses `__pycache__` (a run before 0.11.1 left `eda/harness/__pycache__/metrics_schema.cpython-311.pyc` on 224).

## Where things live on 224

| Path | Content | Encrypted |
|---|---|---|
| `/data/dzy/heura_repr/hb/vault/{code,data,runs}` | code snapshots, data bundles, run outputs | yes |
| `/dev/shm/hbw.*` | workspaces of running jobs | plaintext while running, wiped at the end |
| `/data/dzy/heura_repr/tools/{micromamba,openroad_new,openroad_2024}` | conda installs (OpenROAD 2022/2024-03 without Hier-RTLMP; Yosys 0.38+92 in `openroad_2024/bin`) | no (public) |
| `/data/dzy/heura_repr/tools/openroad_deb` | OpenROAD 2024-12 (.deb unpacked without root; run it through `scripts/server/openroad_deb.sh`) | no (public) |
| `/data/dzy/heura_repr/cache` | conda / pip / XDG caches of hbv jobs | no (public packages) |
| `/data/dzy/heura_repr/envs/hb` | Python environment | no (public packages) |
| `/data/dzy/heura_repr/benchmarks`, `/data/dzy/heura_repr/third_party` | public benchmarks, ORFS checkout | no (public) |
| the LLM key file (path in the local lab note) | managed by the user; read by the client via `DEEPSEEK_API_KEY_FILE` | no (runtime secret) |

Other hosts use a transient vault in `/tmp/.hbv` and caches in `/tmp/.hbcache` (cleared on reboot): fetch results
promptly. On 225 (`/data` 99 % full) the Python env is `/tmp/.hbenv/hb` and micromamba is in `/tmp/.hbtools`.

Code archives carry a `CODE_VERSION` stamp (commit, dirty flag, archive name), so `meta.json` of a server run records
the commit although the workspace has no `.git` (runs before 0.11.1 recorded `git_sha: unknown`; their code
archive is the one named in `vault/code/latest` at launch).

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
installs a recent OpenROAD + Yosys and probes it and OpenROAD 2022; t03deb probes the 2024-12 package
(`install_openroad_deb.sh` unpacks it; the .deb is fetched on the Mac and copied to `tools/openroad_deb/debs/`);
t05 builds the `hb` env and runs the GPU smoke test; t06 is the 16-token LLM self-test. On 225:

```bash
python scripts/hbv.py run --port 225 --run t05_225 -- "export PIP_NO_CACHE_DIR=1; HB_ENV=/tmp/.hbenv/hb HB_TOOLS=/tmp/.hbtools SMOKE_GPU=0 HOST_TAG=225 bash scripts/server/t0_server.sh t05"
```

## Later tasks (commands run inside `hbv.py run`)

- T1.7 / T2.7 Track A: `python scripts/run_seed_archive.py --suite ibm ...` with the DREAMPlace / HB-GP f1.
- **Track B on 224 with ORFS 2024-12** (`third_party/ORFS-2024-12`, Yosys 0.48 in `tools/yosys_048`): one job per design,
  outputs under the workspace (`WORK_HOME`), variant databases deleted after each evaluation; the vault keeps the
  base variant's synthesis and pre-macro floorplan (seeds for candidates after a resume, or for later jobs via
  `--after`), not the candidates' or the repeats' databases:
  `--exclude '(/(objects|results)/[^/]+/[^/]+/([^/]*[.][^/]*|base_r[0-9]+)/|/results/[^/]+/[^/]+/base/([3-6]_|2_[3-9]|2_floorplan)|\.png$)' -- "export HB_OPENROAD=\$PWD/scripts/server/openroad_676.sh; bash scripts/server/trackb.sh python scripts/run_seed_orfs.py --flow /data/dzy/heura_repr/third_party/ORFS-2024-12/flow --design nangate45/<design> --seeds 5 --top 10 --spread 10 --ls 8 --base-runs 2 --yosys /data/dzy/heura_repr/tools/yosys_048/bin/yosys --archive archive_B0_orfs_<design>"`
- (fallback) Track B on 224 with the mini-flow and native tools (`scripts/server/trackb.sh` sets `HB_OPENROAD`, `HB_YOSYS`,
  `EDA_THREADS=8` and links the ORFS checkout read only):
  `bash scripts/server/trackb.sh python scripts/run_seed_miniflow.py --design nangate45/ariane133 --seeds 0 --top 0 --ls 0 --base-runs 1 --archive archive_B0_trackB_dev`
  with `--exclude '/work(_f2)?/.*\.(odb|def)$'` (per-evaluation databases stay out of the vault; `fp.odb` is kept for
  the f2 job, which runs with `--after <f1 run>`).
- Track A per spec on 225 (DREAMPlace in `/tmp/.hbtools/dreamplace`, built by `scripts/server/build_dreamplace.sh`;
  the HA-PR harness comes as the encrypted bundle `eda_harness`):
  `--gpu 1 --data eda_harness:eda -- "ln -s /tmp/.hbdata/benchmarks benchmarks; export HB_EDA_DIR=\$PWD/eda HB_DREAMPLACE=/tmp/.hbtools/dreamplace OMP_NUM_THREADS=4; /tmp/.hbenv/hb/bin/python scripts/run_seed_archive.py --suite ibm --designs ibm01,... --evaluator dreamplace --out runs/seed_trackA_dp --archive archive_A0_trackA_s1"`
- T3.4 pretraining on 225 GPU 0 (`--gpu 0 --snapshot 1800`; restart with `--resume` or `--after`):
  `/tmp/.hbenv/hb/bin/python scripts/pretrain_bridge.py --steps 200000 --batch 64 --device cuda --workers 8 --out checkpoints/pretrain_small --resume`
- T3.7 Algorithm R: `scripts/algorithm_r.py ... --guard f1 --device cuda`; T4 E0: `scripts/run_e0.py ... --guard-fidelity f1 --equal-guard --random-control`.
