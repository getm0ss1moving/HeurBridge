#!/usr/bin/env bash
# Track A f1 (T1.4): DREAMPlace with CUDA, built without root on a GPU host.
# 225 has gcc 7.5, CMake 3.10, CUDA 10.x toolkits and no tclsh -- too old for torch 2.6+cu118 -- so the toolchain is a conda
# env: CMake, Boost headers, bison/flex, gcc/g++ 11, CUDA 11.8 nvcc with the runtime, cuRAND and driver-stub
# headers (NVIDIA channel).  The source (with submodules) is public and copied from the Mac: 225 cannot reach GitHub.
#   bash build_dreamplace.sh SRC [PREFIX]        (default PREFIX /tmp/.hbtools/dreamplace)
#   CUDA_ARCH (default 8.6 = RTX 3090 on 225; 8.9 = RTX 4090 on 231), HB_TOOLS, BUILD_ENV, HB_PYTHON
set -eu
SRC=${1:?DREAMPlace source dir}
PREFIX=${2:-/tmp/.hbtools/dreamplace}
TOOLS=${HB_TOOLS:-/tmp/.hbtools}
BENV=${BUILD_ENV:-/tmp/.hbenv/dpbuild}
PY=${HB_PYTHON:-/tmp/.hbenv/hb/bin/python}
MM="$TOOLS/micromamba/bin/micromamba"; export MAMBA_ROOT_PREFIX="$TOOLS/micromamba/root"
# CMake 3.2x: CMake 4 rejects the bundled pybind11 (cmake_minimum_required 3.4), and DREAMPlace relies on FindCUDA
# (policy CMP0146 from 3.27 on).  FindCUDA resets CUDA_CUDA_LIBRARY on a fresh configure and does not search
# lib/stubs, where the conda package keeps the driver stub: it is found through CMAKE_LIBRARY_PATH.
if [ ! -x "$BENV/bin/nvcc" ]; then
  "$MM" create -y -p "$BENV" -c nvidia/label/cuda-11.8.0 -c conda-forge \
    "cmake>=3.20,<3.27" boost-cpp bison flex make tk "gxx_linux-64=11" "gcc_linux-64=11" zlib \
    cuda-nvcc cuda-cudart-dev cuda-cccl libcurand-dev cuda-driver-dev 2>&1 | tail -5
fi
case "$("$BENV/bin/cmake" --version | head -1)" in
  *" 3.2"[0-6]*) ;;
  *) "$MM" install -y -p "$BENV" -c conda-forge "cmake>=3.20,<3.27" 2>&1 | tail -2 ;;
esac
[ -x "$BENV/bin/tclsh8.6" ] || "$MM" install -y -p "$BENV" -c conda-forge tk 2>&1 | tail -2    # OpenTimer needs tclsh
echo "CMAKE $("$BENV/bin/cmake" --version | head -1)"
export PATH="$BENV/bin:$PATH"
export CC="$BENV/bin/x86_64-conda-linux-gnu-gcc" CXX="$BENV/bin/x86_64-conda-linux-gnu-g++"
export CUDAHOSTCXX="$CXX"
echo "NVCC $("$BENV/bin/nvcc" --version | tail -1)"
echo "CXX $("$CXX" --version | head -1)"
ABI=$("$PY" -c "import torch; print(int(torch._C._GLIBCXX_USE_CXX11_ABI))")
echo "TORCH $("$PY" -c 'import torch; print(torch.__version__)') CXX11_ABI=$ABI"
# cairocffi: DREAMPlace imports its plotting module unconditionally (needs the system libcairo.so.2)
"$PY" -m pip install -q pyunpack patool pkgconfig shapely cairocffi torch_optimizer==0.3.0 ncg_optimizer==0.2.2 2>&1 | tail -2
B=$(mktemp -d /dev/shm/dpb.XXXXXXXX)      # build tree in RAM, removed at the end
trap 'rm -rf "$B" "$B.make.log"' EXIT
cmake -S "$SRC" -B "$B" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX" -DPython_EXECUTABLE="$PY" \
  -DCMAKE_CXX_ABI="$ABI" -DCMAKE_CUDA_ARCHITECTURES="${CUDA_ARCH:-8.6}" -DCUDA_TOOLKIT_ROOT_DIR="$BENV" -DCUDA_HOST_COMPILER="$CXX" \
  -DTCL_TCLSH="$BENV/bin/tclsh8.6" -DPYTHON_EXECUTABLE="$PY" -DCMAKE_LIBRARY_PATH="$BENV/lib/stubs" \
  -DBOOST_ROOT="$BENV" -DZLIB_ROOT="$BENV" -DCMAKE_PREFIX_PATH="$BENV" 2>&1 | grep -E "TORCH|CUDA|Boost|Python|Error|error|WARN" | head -40
rc=0; make -C "$B" -j"${JOBS:-8}" > "$B.make.log" 2>&1 || rc=$?
echo "MAKE_RC $rc"
grep -E "error|Error|\[100%\]" "$B.make.log" | head -40 || true
make -C "$B" install 2>&1 | tail -2
test -e "$PREFIX/dreamplace/Placer.py" || { echo "DREAMPLACE_BUILD_FAILED"; exit 1; }
# NumPy 2 (env hb) removed np.string_, an alias of np.bytes_ used 6 times in PlaceDB.py (the only NumPy-1-only name
# in DREAMPlace's Python): renamed in the installed copy, identical semantics.
sed -i 's/np\.string_/np.bytes_/g' "$PREFIX/dreamplace/PlaceDB.py"
echo "DREAMPLACE_INSTALLED $PREFIX"
