#!/usr/bin/env bash
# OpenROAD 676f8451 (the commit ORFS 8ae3ae36 pins), built by build_openroad.sh against conda-forge libraries:
# their directory is the library path of this binary only.  OpenMP is capped at EDA_THREADS (red line A.2).
T=/data/dzy/heura_repr/tools
export LD_LIBRARY_PATH="$T/orbuild/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OMP_NUM_THREADS=${EDA_THREADS:-8}
exec "$T/openroad_676f8451/bin/openroad" "$@"
