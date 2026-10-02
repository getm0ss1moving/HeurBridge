#!/usr/bin/env bash
# A Track-A GPU job inside the encrypted workspace (repo root = cwd) on a host with the hb env, DREAMPlace and the
# IBM/ISPD2005 benchmarks:
#   bash scripts/server/trackA_gpu.sh scripts/<script>.py [arguments]
# HB_TOOLS_ROOT is where the host keeps .hbenv, .hbtools and .hbdata: /tmp on 225 and 227, /dev/shm on 231.
# Usual hbv inputs: --after seedA_dp_s1 seedA_dp_s2 --data eda_harness:eda bridge_v1_e0_frozen:checkpoints/algR_trackA_final
set -euo pipefail
R=${HB_TOOLS_ROOT:-/tmp}
ln -sfn $R/.hbdata/benchmarks benchmarks
export HB_EDA_DIR=$PWD/eda HB_DREAMPLACE=$R/.hbtools/dreamplace OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
B=checkpoints/algR_trackA_final/best.pt
if [ -e "$B" ]; then echo "f95bdde8485316349a1a47b8b1e8115018085f518419f46c903c65f773a525a5  $B" | sha256sum -c -; fi
exec $R/.hbenv/hb/bin/python "$@"
