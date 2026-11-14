"""Generate build/vc7/granny21/granny21.def from the original demo inputs.

Host-side counterpart of the definition half of
scripts/Generate-Granny21ImportLibrary.ps1 (the d3d8/granny2/binkw32 defs come
from scripts/inspect_environment.py --generate-defs). Pure pefile inspection;
never executes the original files. The .lib conversion and patching run in the
driver (vc7_build.py).
"""
import json
import re
import sys
from pathlib import Path

import pefile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from dependency_bundle import ROOT, digest  # noqa: E402
from workspace_config import configuration  # noqa: E402

GRANNY_DEF = re.compile(r"_Granny\w+@\d+")


def pin(path):
    return {"path": str(path.resolve()), "sha256": digest(path)}


def main():
    game = configuration()["gameRoot"]
    with pefile.PE(str(game / "F3.exe")) as pe:
        imports = [row for row in pe.DIRECTORY_ENTRY_IMPORT
                   if row.dll.lower() == b"granny2.dll"]
        names = [item.name.decode("ascii") for row in imports for item in row.imports]
    with pefile.PE(str(game / "granny2.dll")) as pe:
        exports = {item.name.decode("ascii")
                   for item in pe.DIRECTORY_ENTRY_EXPORT.symbols if item.name}
    assert len(names) == 43 and len(set(names)) == 43
    assert all(GRANNY_DEF.fullmatch(name) and name in exports for name in names)
    granny_dir = ROOT / "build/vc7/granny21"
    granny_dir.mkdir(parents=True, exist_ok=True)
    (granny_dir / "granny21.def").write_text(
        "LIBRARY granny2.dll\nEXPORTS\n"
        + "".join("    " + name[1:] + "\n" for name in names), encoding="ascii")
    (granny_dir / "granny21-imports.json").write_text(json.dumps({
        "runtime": "shipped Granny2.1.0.5", "imports": names,
        "adaptation": "C stdcall symbol decoration once; exact decorated DLL export IMPORT_NAME",
        "inputs": [pin(game / "F3.exe"), pin(game / "granny2.dll")],
        "outputs": [pin(granny_dir / "granny21.def")],
    }, indent=2) + "\n")
    print("Granny2.1 import definition written: build/vc7/granny21/granny21.def")


if __name__ == "__main__":
    main()
