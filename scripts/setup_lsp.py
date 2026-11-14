"""Prepare the local clangd environment for the OpenVB sources.

The pinned SDK headers use Windows casing (Include/Windows.h, SYS/STAT.H) while
sources include them in other spellings (<windows.h>, <sys/stat.h>), and this
host's filesystem is case-sensitive. This script builds an include-shim tree
under build/lsp-shims/ that mirrors the SDK trees under their exact names and
adds symlinks for the spellings sources actually use; deps/ itself is never
modified. It then remaps the -I directories in compile_commands.json and adds
clang relaxations for VC7-era idioms the real compiler accepts.
"""
import json
import os
import re
from pathlib import Path

from dependency_bundle import ROOT, verify

SHIMS = "build/lsp-shims"
INCLUDE_PATTERN = re.compile(r"#include\s*[<\"]([^>\"]+)[>\"]")
# compile_commands.json -I directory -> shim directory.
MAPPING = {
    "deps/msvc70/include": "msvc70",
    "deps/psdk2001/include": "psdk2001",
    "deps/psdk2001/Include": "psdk2001",
    "deps/dx81/include": "dx81",
    "deps/dx81-font/include": "dx81-font",
    "deps/dx81-audio/include": "dx81-audio",
}
SCAN_TREES = ["repos/openvb", "src/dependencies", "deps"]
SCAN_SUFFIXES = {".c", ".cpp", ".hpp", ".h", ".inl"}
# clang relaxations for VC7-era idioms the real compiler accepts (VC7 does not
# require 'typename' here; on-disk header casing differs from source includes),
# the /MT runtime baseline (_MT), and silencing of VC7-internal header noise.
EXTRA_FLAGS = [
    "-fno-digraphs",  # VC7 parses '< ::' where clang's C++98 digraph '<:' breaks
    "-fpermissive",
    "-D_MT",
    "-Wno-nonportable-include-path",
    "-Wno-microsoft-template",
    "-Wno-microsoft-exception-spec",
    "-Wno-delete-incomplete",
]


def include_spellings():
    spellings = set()
    for tree in SCAN_TREES:
        for path in (ROOT / tree).rglob("*"):
            if path.suffix.lower() not in SCAN_SUFFIXES or not path.is_file():
                continue
            text = path.read_text(errors="replace")
            spellings.update(INCLUDE_PATTERN.findall(text))
    return spellings


def follow(current, part):
    """Case-insensitive child lookup; None when missing or ambiguous."""
    matches = [entry for entry in current.iterdir()
               if entry.name.casefold() == part.casefold()]
    exact = [entry for entry in matches if entry.name == part]
    if exact:
        return exact[0]
    return matches[0] if len(matches) == 1 else None


def resolve(root, spelling, directories=False):
    """Follow spelling case-insensitively below root; return the real path."""
    current = root
    for part in Path(spelling.replace("\\", "/")).parts:
        if part in ("", "."):
            continue
        if part == "..":
            current = current.parent
            continue
        current = follow(current, part)
        if current is None:
            return None
    if directories:
        return current if current.is_dir() else None
    return current if current.is_file() else None


def mirror_of(real_path):
    """Shim-tree location mirroring a real path under an SDK include root."""
    for source, key in MAPPING.items():
        root = ROOT / source
        if root.is_dir() and (real_path == root or root in real_path.parents):
            return ROOT / SHIMS / key / real_path.relative_to(root)
    return None


def real_include_paths():
    """Real paths of every file under the SDK include roots."""
    paths = set()
    for source in MAPPING:
        root = ROOT / source
        if root.is_dir():
            paths.update(path for path in root.rglob("*") if path.is_file())
    return paths


def build_shims():
    shim_root = ROOT / SHIMS
    shim_root.mkdir(parents=True, exist_ok=True)
    real_paths = real_include_paths()
    created_placeholder = False

    # Mirror every SDK include tree under its exact names.
    for source, key in sorted(MAPPING.items()):
        root = ROOT / source
        if not root.is_dir():
            continue
        shim_dir = shim_root / key
        shim_dir.mkdir(parents=True, exist_ok=True)
        for path in root.rglob("*"):
            relative = path.relative_to(root)
            destination = shim_dir / relative
            if path.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            elif not destination.exists():
                destination.symlink_to(path)
        print("Mirrored " + source + " under " + str(shim_dir.relative_to(ROOT)))

    # Aliases: all-lowercase names plus every spelling the sources use that
    # differs from the on-disk casing. Alias directory links always point
    # inside the shim tree, never into deps/.
    aliases = {}  # real parent directory -> alias file names
    for path in real_paths:
        lowered = path.name.lower()
        if lowered != path.name:
            aliases.setdefault(path.parent, set()).add(lowered)
    created = 0
    for spelling in sorted(include_spellings()):
        parts = list(Path(spelling.replace("\\", "/")).parts)
        for source in MAPPING:
            root = ROOT / source
            if not root.is_dir():
                continue
            current = root
            chain = []
            mismatched = False
            for part in parts[:-1]:
                if part in ("", "."):
                    continue
                if part == "..":
                    current = current.parent
                    continue
                step = follow(current, part)
                if step is None or not step.is_dir():
                    mismatched = True
                    break
                if step.name != part:
                    chain.append((current, part, step))
                current = step
            if mismatched or not current.is_dir():
                continue
            final = follow(current, parts[-1]) if parts else None
            if final is None or not final.is_file() or final.name == parts[-1]:
                continue  # exact on-disk match or not under this root
            for parent, alias_part, real_directory in chain:
                destination = mirror_of(parent) / alias_part
                target = mirror_of(real_directory)
                if destination.is_symlink() or destination.exists():
                    continue
                destination.symlink_to(target)
                created += 1
            aliases.setdefault(final.parent, set()).add(parts[-1])
    for directory, names in sorted(aliases.items()):
        mirror = mirror_of(directory)
        if mirror is None:
            continue
        for name in sorted(names):
            destination = mirror / name
            if destination.is_symlink() or destination.exists():
                continue
            matches = [entry for entry in directory.iterdir()
                       if entry.name.casefold() == name.casefold()
                       and entry.name != name]
            if not matches:
                continue
            destination.symlink_to(matches[0])
            created += 1
    print("Added %d case aliases under " % created + SHIMS)


def standard_arguments(source):
    return [
        "clang++",
        "--target=i686-pc-windows-msvc",
        "-fms-extensions",
        "-DWIN32",
        "-D_WINDOWS",
        "-DWINVER=0x0400",
        "-D_WIN32_WINNT=0x0400",
        "-D_WIN32_WINDOWS=0x0410",
        "-DNDEBUG",
        "-std=c++98",
        "-fdelayed-template-parsing",
        "-I" + str(ROOT / SHIMS / "msvc70"),
        "-I" + str(ROOT / SHIMS / "psdk2001"),
        "-I" + str(ROOT / SHIMS / "dx81"),
        "-I" + str(ROOT / "repos/openvb/src"),
        "-I" + str(ROOT / "repos/openvb/openje/src"),
        "-I" + str(ROOT / "src/dependencies/small-script/src"),
        str(ROOT / source),
    ]


def cover_database(entries):
    listed = {entry["file"] for entry in entries}
    for source in sorted((ROOT / "repos/openvb").rglob("*.cpp")):
        if str(source) in listed:
            continue
        entries.append({
            "directory": str(ROOT),
            "file": str(source),
            "arguments": standard_arguments(source.relative_to(ROOT)),
        })
        print("Added LSP entry for non-build source: " + str(source.relative_to(ROOT)))


def patch_database():
    database = ROOT / "compile_commands.json"
    if not database.is_file():
        print("compile_commands.json not found; skipping")
        return
    entries = json.loads(database.read_bytes())
    cover_database(entries)
    replaced = 0
    for entry in entries:
        arguments = entry["arguments"]
        for flag in EXTRA_FLAGS:
            if flag not in arguments:
                arguments.insert(arguments.index(entry["file"]), flag)
        for index, argument in enumerate(arguments):
            head, separator, path = argument.partition("-I")
            if not separator or not path:
                # Repair bare shim paths left behind by an earlier broken patch.
                if argument.startswith(str(ROOT / SHIMS)):
                    arguments[index] = "-I" + argument
                    replaced += 1
                continue
            path = Path(path)
            if path.is_absolute():
                path = path.relative_to(ROOT)
            key = MAPPING.get(str(path).replace("\\", "/").lower())
            if key:
                arguments[index] = head + "-I" + str(ROOT / SHIMS / key)
                replaced += 1
    database.write_bytes(json.dumps(entries, indent=1).encode())
    print("Remapped %d include directories in compile_commands.json" % replaced)


def main():
    verify(ROOT)
    build_shims()
    patch_database()


if __name__ == "__main__":
    main()
