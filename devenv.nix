# Minimal devenv for the OpenVB sources. The pinned VC7 toolchain (deps/msvc70)
# builds and links the reconstruction on Linux through the msvc2002 container
# (devenv tasks build:vc7, build:vc7-compile) and the game runs under host wine
# (run:vc7, run:vc7-dxvk). The unwrapped clang does syntax checks and clangd
# serves the LSP using compile_commands.json; scripts/setup_lsp.py installs
# deps/ (hash-checked SDK bundle) and the include shims once per checkout.
{ pkgs, ... }: {
  env.MSVC_IMAGE = "ghcr.io/openje/msvc2002:latest";

  imports = [ ./devenv/scripts/vc7-build.nix ];

  tasks."build:vc7".exec = "vc7-build";
  tasks."build:vc7-compile".exec = "vc7-build-compile";
  tasks."run:vc7".exec = "vc7-run";
  tasks."run:vc7-dxvk".exec = "vc7-run dxvk";

  packages = [
    # Unwrapped: cc-wrapped pkgs.clang injects -fPIC/-Wl flags that break the
    # Windows cross-target checks. Provides clang, clang++ and clangd.
    pkgs.llvmPackages_21.clang-tools
    (pkgs.python311.withPackages (ps: [ ps.pefile ]))
    pkgs.wine # runs the built F3-openvb.exe with the original demo assets
  ];

  enterShell = ''
    if [ ! -d deps/psdk2001 ]; then
      echo "Run scripts/setup_lsp.py to install the pinned SDK bundle before using clangd."
    fi
  '';
}
