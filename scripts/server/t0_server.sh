#!/usr/bin/env bash
# T0 on 224, run inside the encrypted workspace:
#   scripts/hbv.py run --port 224 --run t0_<part> [--api-key-file <key file>] -- bash scripts/server/t0_server.sh <part>
# Parts: t01 (HA-PR inheritance checks on a temporary copy of eda/, so the original is never written),
#        t03 (recent OpenROAD + Yosys into tools/openroad_new; command probe of it and of OpenROAD 2022),
#        t03deb (command probe of the OpenROAD 2024-12 .deb unpacked by install_openroad_deb.sh),
#        t05 (Python env "hb" + GPU smoke test on GPU 1; HB_ENV/HB_TOOLS/SMOKE_GPU/HOST_TAG for other hosts), t06 (LLM 16-token self-test; key read from the key file).
# Every output lands in the workspace (reports/env/, logs/) and leaves the server only as ciphertext.
# Installed third-party software (tools/, envs/hb) is public and stays in plaintext outside the vault.
set -u
H=/data/dzy/heura_repr
mkdir -p reports/env
part=${1:-all}

t01() {
  mkdir -p eda_t01
  for d in harness config docs results pdk flow; do [ -e "$H/eda/$d" ] && cp -a "$H/eda/$d" eda_t01/; done
  for d in runs runs_replay tools openlane_runs; do [ -e "$H/eda/$d" ] && ln -s "$H/eda/$d" "eda_t01/$d"; done
  HB_EDA_DIR="$PWD/eda_t01" bash scripts/server/t0_inherit.sh 2>&1 | tee reports/env/t01_inherit_224.txt
}

t03() {
  local pfx="$H/tools/${OR_PREFIX_NAME:-openroad_new}"
  bash scripts/server/install_openroad.sh "$pfx" 2>&1 | tail -30
  "$pfx/bin/openroad" -no_init -no_splash -exit scripts/server/probe_openroad.tcl \
    > "reports/env/probe_${OR_PREFIX_NAME:-openroad_new}_224.txt" 2>&1; echo "probe new rc=$?"
  (export LD_LIBRARY_PATH="$H/eda/tools/openroad_syslibs:$H/eda/tools/tclreadline/lib"
   export TCL_LIBRARY="$H/eda/tools/openroad_syslibs/share_tcltk/tcl8.6"
   "$H/eda/tools/openroad/bin/openroad" -no_init -no_splash -exit scripts/server/probe_openroad.tcl) \
    > reports/env/probe_openroad_2022_224.txt 2>&1; echo "probe 2022 rc=$?"
  head -3 reports/env/probe_openroad_new_224.txt reports/env/probe_openroad_2022_224.txt
}

t03deb() {
  local R="$H/tools/openroad_deb/root"
  export LD_LIBRARY_PATH="$R/usr/lib:$R/usr/lib/x86_64-linux-gnu:$R/opt/or-tools/lib"
  "$R/usr/bin/openroad" -no_init -no_splash -exit scripts/server/probe_openroad.tcl \
    > reports/env/probe_openroad_deb_224.txt 2>&1; echo "probe deb rc=$?"
  grep -E '^PROBE' reports/env/probe_openroad_deb_224.txt
  # Python API (the .deb links libpython3.8): the macro-placement miniflow may drive ODB from Python
  printf 'import openroad, odb\nprint("PYTHON_API", hasattr(openroad, "Design"), hasattr(odb, "dbDatabase"))\n' > reports/env/or_api.py
  "$R/usr/bin/openroad" -python -no_splash -exit reports/env/or_api.py 2>&1 | tail -3
}

t05() {
  # other hosts: HB_ENV=/tmp/.hbenv/hb HB_TOOLS=/tmp/.hbtools SMOKE_GPU=0 HOST_TAG=225
  local env=${HB_ENV:-$H/envs/hb}
  bash scripts/server/setup_env.sh "$env" 2>&1 | tail -20
  CUDA_VISIBLE_DEVICES=${SMOKE_GPU:-1} "$env/bin/python" scripts/server/gpu_smoke.py 2>&1 \
    | tee "reports/env/gpu_smoke_${HOST_TAG:-224}.txt"
}

t06() {
  # the key file is named by DEEPSEEK_API_KEY_FILE (set by hbv.py --api-key-file); the value is never printed
  "$H/envs/hb/bin/python" -m heurbridge.evolve.llm 2>&1 | tee reports/env/llm_selftest_224.json
}

case "$part" in
  t01) t01 ;; t03) t03 ;; t03deb) t03deb ;; t05) t05 ;; t06) t06 ;;
  all) t01; t03; t05; t06 ;;
  *) echo "unknown part $part"; exit 2 ;;
esac
