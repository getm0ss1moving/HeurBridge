# Server runbook (what runs on 224 / 227 once SSH works)

Rules carried over from `eda/docs/RUNBOOK.md` and the task list (A.2): EDA work on **224** (backup 234);
225/231 only with explicit approval; never kill processes we did not start (`pgrep -x openroad -a`,
`nvidia-smi` first); OpenROAD `EDA_THREADS=8`, at most 8 parallel jobs, 7200 s per job; absolute paths in
every background script; long jobs in `tmux`, resumable (completed `run_id`s are skipped); logs under
`/data/dzy/heura_repr/heurbridge/logs/`.  Key-only SSH: `scripts/ssh_run.sh <port> '<cmd>'`.

```bash
S=/Users/duanzeyu/Desktop/HeurBridge/scripts
H=/data/dzy/heura_repr/heurbridge
```

## 0. Access and sync (from the Mac)
```bash
$S/ssh_run.sh 224 'hostname; whoami'
$S/sync_to_server.sh 224 /data/dzy/heura_repr/heurbridge
rsync -az -e "ssh -i ~/.ssh/id_ed25519_heurbridge -p 224" /Users/duanzeyu/Desktop/HeurBridge/benchmarks/ibm_bookshelf /Users/duanzeyu/Desktop/HeurBridge/benchmarks/ispd2005 <user>@<host>:/data/dzy/heura_repr/benchmarks/
```
(only if the server cannot download them itself; then verify with `shasum -a 256 -c configs/manifests/*.sha256`)

## 1. T0 (read-only probes first)
```bash
$S/ssh_run.sh 224 "bash $H/scripts/server/t0_inherit.sh"                        # T0.1
$S/ssh_run.sh 224 "bash $H/scripts/server/probe_env.sh" > $S/../reports/env/probe_224.json   # T0.2
$S/ssh_run.sh 227 "bash $H/scripts/server/probe_env.sh" > $S/../reports/env/probe_227.json
$S/ssh_run.sh 224 "tmux new -d -s hb_install 'bash $H/scripts/server/install_openroad.sh > $H/logs/install_openroad.log 2>&1'"   # T0.3
$S/ssh_run.sh 224 "/data/dzy/heura_repr/tools/openroad_new/bin/openroad -no_init -no_splash -exit $H/scripts/server/probe_openroad.tcl > $H/reports/env/probe_openroad_new.txt"
$S/ssh_run.sh 224 "/data/dzy/heura_repr/eda/tools/openroad/bin/openroad -no_init -no_splash -exit $H/scripts/server/probe_openroad.tcl > $H/reports/env/probe_openroad_2022.txt"
$S/ssh_run.sh 224 "tmux new -d -s hb_env 'bash $H/scripts/server/setup_env.sh > $H/logs/setup_env.log 2>&1'"                    # T0.5
$S/ssh_run.sh 224 "CUDA_VISIBLE_DEVICES=1 /data/dzy/heura_repr/envs/hb/bin/python $H/scripts/server/gpu_smoke.py"
$S/ssh_run.sh 224 "cd $H && /data/dzy/heura_repr/envs/hb/bin/python -m heurbridge.evolve.llm"                               # T0.6 (needs DEEPSEEK_LAB_API_KEY in the server env)
```
Track B is confirmed when ORFS `nangate45/ariane133` reaches `route` with the new OpenROAD:
```bash
$S/ssh_run.sh 224 "tmux new -d -s hb_ariane 'cd $H/third_party/OpenROAD-flow-scripts/flow && PATH=/data/dzy/heura_repr/tools/openroad_new/bin:\$PATH make DESIGN_CONFIG=designs/nangate45/ariane133/config.mk FLOW_VARIANT=hb_trackB_check NUM_CORES=8 route > $H/logs/ariane133_trackB.log 2>&1'"
```
If ORFS and the installed OpenROAD disagree, `heurbridge/eval/miniflow.py` (verified locally on bp_fe_top)
is the fallback f1 on the same platform.

## 2. T1.7 baselines and T2.7 archive seeding
- Track B (ORFS): M1 = tool-native `rtl_macro_placer` (ORFS default flow), 3 seeds at f2; seeding with
  `OrfsEvaluator` (f1 = `grt`, f2 = `finish`), top-10 to f2, 8 local-search steps.
- Track A (bookshelf): DREAMPlace build (`third_party/DREAMPlace`, CUDA), f1 with macros fixed; HB-GP is only
  the development stand-in.

## 3. T3 bridge (GPU 1 on 224)
```bash
$S/ssh_run.sh 224 "tmux new -d -s hb_pretrain 'cd $H && CUDA_VISIBLE_DEVICES=1 /data/dzy/heura_repr/envs/hb/bin/python scripts/pretrain_bridge.py --steps 200000 --batch 64 --device cuda --out $H/checkpoints/pretrain_small > $H/logs/pretrain_small.log 2>&1'"
$S/ssh_run.sh 224 "tmux new -d -s hb_algR 'cd $H && CUDA_VISIBLE_DEVICES=1 /data/dzy/heura_repr/envs/hb/bin/python scripts/algorithm_r.py --train <train designs> --val <val designs> --rounds 3 --archive $H/archive_A0 --pretrained $H/checkpoints/pretrain_small/pretrain_small.pt --device cuda --out $H/checkpoints/algR_macro > $H/logs/algR_macro.log 2>&1'"
```
T3 exit: `scripts/report_bridge.py --run <round dir> --out reports/T3_bridge_macro.md` (gate: post-guard f1 <
raw on validation, paired p < 0.05, ledger entry written by `algorithm_r.py`).

## 4. T4 E0 / G0' (f2 on the held-out family)
```bash
python scripts/run_e0.py --designs <held-out family + held-out designs> --bridge <promoted ckpt> --frozen <pretrain ckpt> --seeds 5 --out reports/e0 --campaign E0
python scripts/report_e0.py --run reports/e0 --out reports/E0_partner_ablation.md
```
Stop and report if G0' fails (task spec T4).
