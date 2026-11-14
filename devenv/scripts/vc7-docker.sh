#!/usr/bin/env bash
# Shared docker/wine runner for the VC7 build tasks (see vc7-build.nix).
set -euo pipefail

IMAGE="${MSVC_IMAGE:-ghcr.io/openje/msvc2002:latest}"
docker="${DOCKER:-docker}"
uid="$(id -u)"

if [ -z "${DOCKER_HOST:-}" ] && [ -S "/run/user/$uid/docker.sock" ]; then
  export DOCKER_HOST="unix:///run/user/$uid/docker.sock"
fi
if ! "$docker" info >/dev/null 2>&1; then
  printf '%s\n' "Docker daemon not reachable (rootless socket: /run/user/$uid/docker.sock)." >&2
  exit 1
fi

# First run: copy the container's prepared wine prefix into the workspace so
# builds do not depend on container-internal state (same approach as OpenVB).
# Rootless docker maps container root to the host user, so no chown is needed.
"$docker" run --rm -t --user 0:0 -v "$PWD:/work" -w /work "$IMAGE" -lc '
  mkdir -p /work/build/vc7/wineprefix
  if [ ! -f /work/build/vc7/wineprefix/system.reg ]; then
    cp -a --no-preserve=ownership /home/msvc2002/.wine32/. /work/build/vc7/wineprefix/
    chmod -R a+rwX /work/build/vc7
  fi'

# Import libraries for the original runtime DLLs are generated once from the
# original game inputs: pefile writes the defs on the host, the repo's LIB.EXE
# converts them under wine, and the repo's mapping fixes patch the archives.
# A full link is required; compile-only passes need none of this.
if [[ " $* " != *--compile-only* ]] && [ -f deps/game/F3.exe ] \
   && [ ! -f deps/imports/binkw32.lib ]; then
  python scripts/inspect_environment.py --generate-defs
  python devenv/scripts/vc7_granny_def.py
  for name in d3d8 granny2 binkw32; do
    "$docker" run --rm -t --user 0:0 -v "$PWD:/work" -w /work "$IMAGE" -lc \
      "WINEPREFIX=/work/build/vc7/wineprefix WINEDEBUG=-all wine deps/msvc70/bin/LIB.EXE /nologo /machine:x86 /def:deps/imports/$name.def /out:deps/imports/$name.lib" || exit 1
  done
  python scripts/fix_d3d8_import.py
  python scripts/fix_bink_import.py
fi

exec "$docker" run --rm -t --user 0:0 -v "$PWD:/work" -w /work "$IMAGE" -lc \
  "python3 devenv/scripts/vc7_build.py $*"
