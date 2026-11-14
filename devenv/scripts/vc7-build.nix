# ./devenv/scripts/vc7-build.nix

# Drives the workspace's pinned VC7 13.00.9466 toolchain (deps/msvc70) under
# wine inside the same msvc2002 container the OpenVB devenv uses. Tool
# identities, dependency hashes, unit selection and build records follow
# scripts/Build-Legacy.ps1; devenv/scripts/vc7_build.py is the driver.
{ config, pkgs, ... }:
let
  image = config.env.MSVC_IMAGE;
in {
  scripts.vc7-build = {
    description = "Build the reconstruction with the pinned VC7 toolchain (link included)";
    exec = ''
      set -euo pipefail
      exec ${pkgs.bash}/bin/bash devenv/scripts/vc7-docker.sh "$@"
    '';
  };

  scripts.vc7-build-compile = {
    description = "Compile-check the reconstruction units with the pinned VC7 toolchain (no link)";
    exec = ''
      set -euo pipefail
      exec ${pkgs.bash}/bin/bash devenv/scripts/vc7-docker.sh --compile-only "$@"
    '';
  };

  # Renderer switch for the run prefix: wined3d (default) or DXVK 32-bit.
  # DXVK state is only trusted when the system32 DLLs hash-match the declared
  # DXVK source AND the registry overrides are present; arm/disarm are decisive.
  scripts.vc7-dxvk = {
    description = "Report/arm/disarm the DXVK x32 d3d8 override in a run prefix (vc7-dxvk status|arm|disarm [prefix])";
    exec = ''
      set -euo pipefail
      cmd="''${1:-status}"; [ $# -gt 0 ] && shift
      prefix="''${1:-''${WINEPREFIX:-$PWD/build/vc7/runprefix}}"
      prefix="$(${pkgs.coreutils}/bin/realpath -m -- "$prefix")"
      sys32="$prefix/drive_c/windows/system32"
      dxvkSrc="${pkgs.dxvk.bin}/x32"
      wine="${pkgs.wine}/bin/wine"
      if [ ! -f "$prefix/system.reg" ]; then
        printf 'vc7-dxvk: no initialized prefix at %s\n' "$prefix" >&2
        exit 1
      fi
      export WINEPREFIX="$prefix"
      override_of() {
        local query
        query="$("$wine" reg query 'HKCU\Software\Wine\DllOverrides' /v "$1" 2>/dev/null | tr -d '\r')" || true
        printf '%s' "$query" | grep -q "REG_SZ.*native"
      }
      dll_is_dxvk() {
        [ -f "$sys32/$1.dll" ] && cmp -s "$dxvkSrc/$1.dll" "$sys32/$1.dll"
      }
      case "$cmd" in
        arm)
          "$wine" reg add 'HKCU\Software\Wine\DllOverrides' /v d3d8 /t REG_SZ /d native /f >/dev/null
          override_of d3d8 || { printf 'vc7-dxvk: d3d8 override write failed\n' >&2; exit 1; }
          "$wine" reg add 'HKCU\Software\Wine\DllOverrides' /v d3d9 /t REG_SZ /d native /f >/dev/null
          override_of d3d9 || { printf 'vc7-dxvk: d3d9 override write failed\n' >&2; exit 1; }
          for dll in d3d8 d3d9 dxgi; do
            cp -f "$dxvkSrc/$dll.dll" "$sys32/$dll.dll"
            dll_is_dxvk "$dll" || { printf 'vc7-dxvk: %s.dll copy failed\n' "$dll" >&2; exit 1; }
          done
          printf 'verdict: ARMED (dxvk dlls: d3d8 d3d9 dxgi; overrides: d3d8 d3d9)\n'
          ;;
        disarm)
          for dll in d3d8 d3d9 dxgi; do
            if dll_is_dxvk "$dll"; then rm -f "$sys32/$dll.dll"; fi
          done
          "$wine" reg delete 'HKCU\Software\Wine\DllOverrides' /v d3d8 /f >/dev/null 2>&1 || true
          "$wine" reg delete 'HKCU\Software\Wine\DllOverrides' /v d3d9 /f >/dev/null 2>&1 || true
          printf 'verdict: DISARMED (wined3d builtins)\n'
          ;;
        status)
          if override_of d3d8 && dll_is_dxvk d3d8; then verdict=ARMED
          elif [ -f "$sys32/d3d8.dll" ]; then verdict=UNKNOWN
          else verdict=DISARMED; fi
          printf 'verdict: %s (%s)\n' "$verdict" "$prefix"
          ;;
        *) printf 'vc7-dxvk: unknown command: %s (status|arm|disarm [prefix])\n' "$cmd" >&2; exit 2 ;;
      esac
    '';
  };

  scripts.vc7-run = {
    description = "Run F3-openvb.exe under wine from the original demo directory (vc7-run [dxvk|wined3d]; default wined3d)";
    exec = ''
      set -euo pipefail
      renderer="''${1:-''${VC7_RENDERER:-wined3d}}"
      case "$renderer" in dxvk|wined3d) ;; *) printf 'vc7-run: unknown renderer %s (dxvk|wined3d)\n' "$renderer" >&2; exit 2 ;; esac
      exe="$PWD/build/legacy-vc7/release/F3-openvb.exe"
      gameDir="$PWD/deps/game"
      if [ ! -f "$exe" ]; then
        printf '%s\n' "Missing $exe - run: devenv tasks run build:vc7" >&2
        exit 1
      fi
      if [ ! -f "$gameDir/resource.rht" ]; then
        printf '%s\n' "Missing $gameDir/resource.rht - install the original demo (scripts/setup_inputs.py)" >&2
        exit 1
      fi
      cp -f "$exe" "$gameDir/F3-openvb.exe"
      prefix="$PWD/build/vc7/runprefix"
      export WINEPREFIX="$prefix"
      export WINEARCH="''${WINEARCH:-win32}"
      export WINEDLLOVERRIDES="''${WINEDLLOVERRIDES:-mscoree,mshtml=}"
      export WINEDEBUG="''${WINEDEBUG:--all,+err}"
      mkdir -p "$prefix"
      if [ ! -f "$prefix/system.reg" ]; then
        ${pkgs.wine}/bin/wineboot -u >/dev/null
      fi
      case "$renderer" in
        dxvk) vc7dxvk=arm ;;
        wined3d) vc7dxvk=disarm ;;
      esac
      WINEPREFIX="$prefix" vc7-dxvk "$vc7dxvk" "$prefix"
      cd "$gameDir"
      exec ${pkgs.wine}/bin/wine ./F3-openvb.exe
    '';
  };
}
