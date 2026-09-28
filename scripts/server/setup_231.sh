#!/usr/bin/env bash
# 231 (5 x RTX 4090; approved by the user for the full E0 on 2026-09-28).  Its root disk is 99 % full, so the tools,
# the env and the benchmarks live in RAM (/dev/shm) -- public software and data only; our files stay in the hbv vault
# (/dev/shm/.hbv).  Run inside an hbv job on the free GPU:
#   hbv.py run --port 231 --run setup_231 --gpu 4 --data eda_harness:eda -- "bash scripts/server/setup_231.sh"
# Needs the DREAMPlace source in /dev/shm/.hbsrc/DREAMPlace and the benchmarks in /dev/shm/.hbdata/benchmarks
# (streamed from the Mac).  Steps already done are skipped.
set -eu
T=/dev/shm/.hbtools
E=/dev/shm/.hbenv
export HB_TOOLS=$T
# 1. env hb with 225's package versions (torch 2.6.0+cu118 although the driver offers CUDA 12.4)
if ! "$E/hb/bin/python" -c "import torch_geometric" 2>/dev/null; then
  TORCH_SPEC=torch==2.6.0 TORCH_INDEX=https://download.pytorch.org/whl/cu118 \
  PIN_FILE=$PWD/scripts/server/hb_env_pins.txt bash scripts/server/setup_env.sh "$E/hb" 2>&1 | tail -12
fi
mkdir -p reports/env
"$E/hb/bin/python" scripts/server/gpu_smoke.py 2>&1 | tail -6 | tee reports/env/gpu_smoke_231.txt
# 2. DREAMPlace for the RTX 4090 (sm_89); 231 is shared and busy: 8 make jobs
if [ ! -e "$T/dreamplace/dreamplace/Placer.py" ]; then
  CUDA_ARCH=8.9 BUILD_ENV=$E/dpbuild HB_PYTHON=$E/hb/bin/python JOBS=8 \
    bash scripts/server/build_dreamplace.sh /dev/shm/.hbsrc/DREAMPlace "$T/dreamplace" 2>&1 | tail -25
fi
# 3. DREAMPlace smoke test on ibm01 (determinism, orientation baking) on the job's GPU
ln -sfn /dev/shm/.hbdata/benchmarks benchmarks
HB_EDA_DIR=$PWD/eda HB_DREAMPLACE=$T/dreamplace OMP_NUM_THREADS=4 "$E/hb/bin/python" scripts/server/dp_smoke.py \
  --design ibm01 2>&1 | tail -8 | tee reports/env/dp_smoke_231.txt
