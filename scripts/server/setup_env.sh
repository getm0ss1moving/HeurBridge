#!/usr/bin/env bash
# T0.5: Python env "hb" (py3.11, CUDA PyTorch matching the driver, PyG, science stack) + GPU smoke test.
#   bash setup_env.sh [env_prefix]     (default /data/dzy/heura_repr/envs/hb)
set -eu
ENV=${1:-/data/dzy/heura_repr/envs/hb}
TOOLS=/data/dzy/heura_repr/tools
MM=""
for c in mamba conda micromamba; do command -v $c >/dev/null 2>&1 && { MM=$c; break; }; done
if [ -z "$MM" ] && [ -x "$TOOLS/micromamba/bin/micromamba" ]; then MM="$TOOLS/micromamba/bin/micromamba"; export MAMBA_ROOT_PREFIX="$TOOLS/micromamba/root"; fi
[ -n "$MM" ] || { echo "ENV_FAIL no conda/mamba/micromamba (run install_openroad.sh first to bootstrap micromamba)"; exit 1; }
[ -x "$ENV/bin/python" ] || "$MM" create -y -p "$ENV" -c conda-forge python=3.11 pip 2>&1 | tail -2
PY="$ENV/bin/python"
# CUDA wheel index from the driver's max CUDA version
CU=$(nvidia-smi 2>/dev/null | grep -o 'CUDA Version: [0-9]*\.[0-9]*' | awk '{print $3}')
case "$CU" in
  12.[4-9]*|13.*) IDX=https://download.pytorch.org/whl/cu124 ;;
  12.[1-3]*)      IDX=https://download.pytorch.org/whl/cu121 ;;
  11.8*|12.0*)    IDX=https://download.pytorch.org/whl/cu118 ;;
  *)              IDX=https://download.pytorch.org/whl/cpu ;;
esac
echo "DRIVER_CUDA=$CU TORCH_INDEX=$IDX"
"$PY" -m pip install -q --upgrade pip
"$PY" -m pip install -q torch --index-url "$IDX"
"$PY" -m pip install -q torch_geometric numpy scipy scikit-learn pandas pyyaml networkx matplotlib hypothesis pytest gdown
"$PY" -m pip install -q pymetis 2>/dev/null && echo "PYMETIS_OK" || echo "PYMETIS_UNAVAILABLE"
"$PY" -m pip install -q kahypar 2>/dev/null && echo "KAHYPAR_OK" || echo "KAHYPAR_UNAVAILABLE"
"$PY" -c "import torch, torch_geometric as g; print('TORCH', torch.__version__, 'CUDA', torch.version.cuda, 'avail', torch.cuda.is_available(), 'PYG', g.__version__)"
echo "ENV_DONE $ENV"
