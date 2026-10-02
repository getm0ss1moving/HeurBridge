#!/usr/bin/env bash
# Beat-the-tool feasibility demo on 225 inside the encrypted workspace (repo root = cwd): scripts/beat_tool_demo.py.
#   bash scripts/server/beat_tool_demo.sh <designs, comma separated> <out dir> [extra arguments]
# hbv inputs: --after seedA_dp_s1 seedA_dp_s2 --data eda_harness:eda bridge_v1_e0_frozen:checkpoints/algR_trackA_final
set -euo pipefail
D=${1:?designs}; OUT=${2:?out dir}; shift 2
ln -sfn /tmp/.hbdata/benchmarks benchmarks
export HB_EDA_DIR=$PWD/eda HB_DREAMPLACE=/tmp/.hbtools/dreamplace OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
P=/tmp/.hbenv/hb/bin/python
B=checkpoints/algR_trackA_final/best.pt
echo "f95bdde8485316349a1a47b8b1e8115018085f518419f46c903c65f773a525a5  $B" | sha256sum -c -
$P scripts/beat_tool_demo.py --designs "$D" --runs runs/seed_trackA_dp --bridge $B --out "$OUT" "$@"
