#!/usr/bin/env bash
# T0.3 (route 2, approved by the user 2026-09-27): the prebuilt OpenROAD for Ubuntu 20.04 (Precision Innovations
# release 2024-12-14, 53,059,724 bytes), unpacked without root into <prefix>/root.  Declared dependencies that are
# not installed on the host are fetched with `apt-get download` (no root) and unpacked into the same root.
#   bash install_openroad_deb.sh [prefix]      (default /data/dzy/heura_repr/tools/openroad_deb)
set -eu
T=${1:-/data/dzy/heura_repr/tools/openroad_deb}
URL=https://github.com/Precision-Innovations/OpenROAD/releases/download/2024-12-14/openroad_2.0-17598-ga008522d8_amd64-ubuntu-20.04.deb
SIZE=53059724
SHA=c24ca8ffd12636a93d0c8c4ac01ff96ca1d621a1f1a77421fb10de7c0535dfdb
# 224 cannot fetch GitHub release assets ("Empty reply from server"): download elsewhere and copy the file to
# <prefix>/debs/openroad.deb first; the download below is then skipped.
mkdir -p "$T/debs" "$T/root"
cd "$T/debs"
[ -s openroad.deb ] || curl -L --fail --retry 3 -sS -o openroad.deb "$URL"
[ "$(stat -c %s openroad.deb)" = "$SIZE" ] || { echo "DEB_SIZE_MISMATCH $(stat -c %s openroad.deb)"; exit 1; }
[ "$(sha256sum openroad.deb | cut -d' ' -f1)" = "$SHA" ] || { echo "DEB_SHA256_MISMATCH"; exit 1; }
dpkg-deb --info openroad.deb > /dev/null && echo "DEB_OK sha256=$SHA"
dpkg -x openroad.deb "$T/root"
# declared dependencies: package names (alternatives: first installable), versions ignored
deps=$(dpkg-deb -f openroad.deb Depends | tr ',' '\n' | sed -E 's/\(.*\)//; s/^ +| +$//g')
echo "DEPENDS $(echo "$deps" | tr '\n' ' ')"
need=""
while IFS= read -r alt; do
  [ -z "$alt" ] && continue
  ok=""; first=""
  for p in $(echo "$alt" | tr '|' ' '); do
    [ -z "$first" ] && first=$p
    dpkg -s "$p" >/dev/null 2>&1 && { ok=$p; break; }
  done
  [ -z "$ok" ] && need="$need $first"
done <<< "$deps"
echo "NOT_INSTALLED$need"
for p in $need; do
  apt-get download "$p" >/dev/null 2>&1 && echo "APT_DOWNLOADED $p" || echo "APT_DOWNLOAD_FAILED $p"
done
for f in *.deb; do [ "$f" = openroad.deb ] || dpkg -x "$f" "$T/root"; done
OR=$(find "$T/root" -type f -name openroad -perm -u+x | head -1)
LIBS=$(find "$T/root" -type d \( -path '*/lib' -o -path '*/lib/x86_64-linux-gnu' -o -path '*/lib64' \) | tr '\n' ':')
echo "OPENROAD_BIN $OR"
echo "LIB_PATH $LIBS"
echo "LDD_MISSING $(LD_LIBRARY_PATH="$LIBS" ldd "$OR" | awk '/not found/{print $1}' | tr '\n' ' ')"
LD_LIBRARY_PATH="$LIBS" "$OR" -version 2>&1 | head -2 | sed 's/^/OPENROAD_VERSION /'
