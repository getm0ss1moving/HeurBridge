#!/usr/bin/env bash
# T0.3: recent OpenROAD + Yosys into an isolated prefix; the old OpenROAD 2022 binary is untouched.
#   bash install_openroad.sh [prefix]      (default /data/dzy/heura_repr/tools/openroad_new)
# Order: conda/mamba (litex-hub::openroad) -> micromamba bootstrap -> report (Docker / source build are
# left for a human decision: they need root or hours of build time).
set -eu
PREFIX=${1:-/data/dzy/heura_repr/tools/openroad_new}
TOOLS=$(dirname "$PREFIX")
mkdir -p "$TOOLS"
MM=""
for c in mamba conda micromamba; do command -v $c >/dev/null 2>&1 && { MM=$c; break; }; done
if [ -z "$MM" ]; then
  if [ ! -x "$TOOLS/micromamba/bin/micromamba" ]; then
    mkdir -p "$TOOLS/micromamba" && cd "$TOOLS/micromamba"
    curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba >/dev/null
  fi
  MM="$TOOLS/micromamba/bin/micromamba"
  export MAMBA_ROOT_PREFIX="$TOOLS/micromamba/root"
fi
echo "INSTALLER $MM"
# OPENROAD_SPEC pins a build: unpinned, the solver picked litex-hub's 2022 build (f12e2f47, no place_macro)
# although the channel also has 2.0_6493_g758c1d57c (2024-03)
if [ ! -x "$PREFIX/bin/openroad" ]; then
  # the 2024 litex-hub builds link libboost 1.73 and qt 5.9.7, which only Anaconda's main channel has:
  # EXTRA_CHANNELS="-c https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main" OPENROAD_SPEC="openroad=2.0_12381_g01bba3695"
  # shellcheck disable=SC2086
  "$MM" create -y -p "$PREFIX" ${CHANNELS:--c litex-hub -c conda-forge} ${EXTRA_CHANNELS:-} "${OPENROAD_SPEC:-openroad}" \
    "${YOSYS_SPEC:-yosys}" ${EXTRA_SPECS:-} 2>&1 | tail -15
fi
"$PREFIX/bin/openroad" -version 2>&1 | head -1 | sed 's/^/OPENROAD_NEW_VERSION /'
"$PREFIX/bin/yosys" -V 2>&1 | head -1 | sed 's/^/YOSYS_VERSION /'
echo "INSTALL_DONE prefix=$PREFIX"
