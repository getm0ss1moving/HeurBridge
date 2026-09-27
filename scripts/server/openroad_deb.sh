#!/usr/bin/env bash
# OpenROAD 2024-12 (v2.0-17598-ga008522d8), unpacked without root by install_openroad_deb.sh.
# The library path is set for this binary only (the Python env must not see the package's libraries).
R=${OPENROAD_DEB_ROOT:-/data/dzy/heura_repr/tools/openroad_deb/root}
export LD_LIBRARY_PATH="$R/usr/lib:$R/usr/lib/x86_64-linux-gnu:$R/opt/or-tools/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$R/usr/bin/openroad" "$@"
