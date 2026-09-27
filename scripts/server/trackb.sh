#!/usr/bin/env bash
# Track-B jobs on 224 inside the encrypted workspace (repo root = cwd):
#   scripts/hbv.py run --port 224 --run RUN -- bash scripts/server/trackb.sh python scripts/run_seed_miniflow.py ...
# Native tools: OpenROAD 2024-12 (.deb, wrapper sets its library path), Yosys 0.38 (litex-hub, tools/openroad_2024).
# ORFS platform and design files come from the public checkout in /data/dzy/heura_repr/third_party (read only;
# find in hbv's archiving does not follow the symlink, so none of it is copied into the vault).
set -eu
H=/data/dzy/heura_repr
export HB_OPENROAD=${HB_OPENROAD:-$PWD/scripts/server/openroad_deb.sh}   # ORFS jobs: scripts/server/openroad_676.sh
export HB_YOSYS="$H/tools/openroad_2024/bin/yosys"
export EDA_THREADS=${EDA_THREADS:-8}                 # red line A.2
export OMP_NUM_THREADS=$EDA_THREADS                  # OpenMP is not bounded by set_thread_count
[ -e third_party ] || ln -s "$H/third_party" third_party
PY=${HB_PYTHON:-$H/envs/hb/bin/python}
"$HB_OPENROAD" -version 2>&1 | head -1 | sed 's/^/OPENROAD /'
"$HB_YOSYS" -V 2>&1 | head -1 | cut -c1-40 | sed 's/^/YOSYS /'
[ "${1:-}" = python ] && shift && set -- "$PY" "$@"
exec "$@"
