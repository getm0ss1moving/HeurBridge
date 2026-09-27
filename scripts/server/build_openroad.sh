#!/usr/bin/env bash
# OpenROAD 676f8451 -- the commit ORFS 8ae3ae36 (2024-12-13) pins -- built without root on 224.  The prebuilt
# package (a008522d8) lacks mpl2 PR #6335 ("cluster placement for stdcell-only levels"): ariane133's tool-native
# macro placement fails there with MPL-0040.  Dependencies come from conda-forge (CMake, gcc 11, Boost, SWIG, Eigen,
# LEMON, spdlog, Tcl, OR-Tools, flex/bison, Python) plus CUDD 3.0.0 from source; GUI and tests are off.
#   bash build_openroad.sh [SRC] [PREFIX]
set -eu
SRC=${1:-/data/dzy/heura_repr/src/OpenROAD-676f8451}
PREFIX=${2:-/data/dzy/heura_repr/tools/openroad_676f8451}
T=/data/dzy/heura_repr/tools
BENV=${BUILD_ENV:-$T/orbuild}
MM="$T/micromamba/bin/micromamba"; export MAMBA_ROOT_PREFIX="$T/micromamba/root"
if [ ! -x "$BENV/bin/cmake" ]; then
  "$MM" create -y -p "$BENV" -c conda-forge "cmake>=3.24,<3.30" make "gxx_linux-64=11" "gcc_linux-64=11" \
    "libboost-devel>=1.80,<1.87" "swig>=4.1,<4.3" "eigen=3.4" "lemon=1.3.1" "spdlog>=1.12,<1.16" tk \
    flex bison zlib readline "python=3.10" pkg-config "ortools-cpp=9.6" 2>&1 | tail -4
fi
# tclreadline: without it Main.cc (676f8451) does not compile (TCLRL_VERSION_STR)
[ -e "$BENV/include/tclreadline.h" ] || "$MM" install -y -p "$BENV" -c conda-forge tclreadline 2>&1 | tail -2
export PATH="$BENV/bin:$PATH"
export CC="$BENV/bin/x86_64-conda-linux-gnu-gcc" CXX="$BENV/bin/x86_64-conda-linux-gnu-g++"
echo "CMAKE $(cmake --version | head -1); CXX $($CXX --version | head -1)"
echo "PKGS $("$MM" list -p "$BENV" 2>/dev/null | grep -E ' (libboost-devel|swig|spdlog|fmt|ortools-cpp|libortools|lemon|tk|eigen) ' | awk '{print $1"="$2}' | tr '\n' ' ')"
if [ ! -e "$BENV/lib/libcudd.a" ]; then
  B0=$(mktemp -d /dev/shm/cudd.XXXXXXXX); cp -a /data/dzy/heura_repr/src/cudd-3.0.0/. "$B0/"
  (cd "$B0" && ./configure --prefix="$BENV" --enable-shared=no CC="$CC" CXX="$CXX" > configure.log 2>&1 \
     && make -j8 > make.log 2>&1 && make install > install.log 2>&1) || { tail -20 "$B0"/*.log; exit 1; }
  rm -rf "$B0"
fi
echo "CUDD $(ls "$BENV"/lib/libcudd.a)"
B=/data/dzy/heura_repr/build/openroad-676f8451
# a fresh configure: cached pkg-config results (Cbc_FOUND) skip the lookups that create OR-Tools' imported targets
rm -rf "$B"; mkdir -p "$B"
cmake -S "$SRC" -B "$B" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX" -DENABLE_TESTS=OFF \
  -DBUILD_GUI=OFF -DUSE_SYSTEM_BOOST=ON -DCMAKE_PREFIX_PATH="$BENV" -DCUDD_DIR="$BENV" \
  -DTCL_LIBRARY="$BENV/lib/libtcl8.6.so" -DTCL_INCLUDE_PATH="$BENV/include" -DPython3_EXECUTABLE="$BENV/bin/python" \
  -DCMAKE_CXX_STANDARD_LIBRARIES="-L$BENV/lib -lreadline" \
  -DOPENROAD_VERSION="${OPENROAD_VERSION:-676f8451bb-src}" \
  > "$B/cmake.log" 2>&1 || { grep -E "Error|error|Could NOT" "$B/cmake.log" | head -20; exit 1; }
grep -E "CUDD|TCL|Boost|ortools|spdlog|SWIG|Python" "$B/cmake.log" | head -20
rc=0; make -C "$B" -j"${JOBS:-8}" > "$B/make.log" 2>&1 || rc=$?
echo "MAKE_RC $rc"
if [ $rc -ne 0 ]; then grep -E "error:|Error " "$B/make.log" | head -20; exit 1; fi
make -C "$B" install > "$B/install.log" 2>&1
LD_LIBRARY_PATH="$BENV/lib" "$PREFIX/bin/openroad" -version && echo "OPENROAD_INSTALLED $PREFIX"
