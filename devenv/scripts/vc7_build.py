"""VC7 build driver for Linux.

Runs the workspace's own hash-checked VC7 13.00.9466 tools under wine inside
the msvc2002 container, mirroring scripts/Build-Legacy.ps1: identical unit
selection, argument assembly, /showIncludes incremental state, LIB/LINK
ordering and build records. The wine container supplies the host; the
toolchain, its identity checks and the dependency bundle are the same ones the
Windows build verifies. No game executable is ever launched.

Run inside the container (mount the workspace at /work):
  python3 devenv/scripts/vc7_build.py [--target T] [--compile-only]
      [--plan-only] [--rebuild] [--keep-going] [--configuration Release]
      [--output-directory build/legacy-vc7]
"""
import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(os.environ.get("VC7_WORKSPACE", "/work"))
sys.path.insert(0, str(WORKSPACE / "scripts"))
import dependency_bundle  # noqa: E402

INCLUDE_LOG = re.compile(r"^Note: including file:\s*(.+)$")
DIAGNOSTIC = re.compile(r"(error|fatal error|warning) [CDL][0-9]|LNK[0-9]")
KEEP_LINK_FLAGS = re.compile(r"^/SUBSYSTEM:|^/NODEFAULTLIB:|^/ENTRY:")
RESPONSE_ENCODING = "latin-1"
WINE_DEBUG = "-all"


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def full_path(relative, base=WORKSPACE):
    path = Path(relative)
    return path if path.is_absolute() else base / path


def quote_argument(argument):
    if any(character in argument for character in ' \t"'):
        return '"' + argument.replace('"', '\\"') + '"'
    return argument


def write_response(path, arguments):
    text = "\n".join(quote_argument(argument) for argument in arguments)
    Path(path).write_text(text + "\n", encoding=RESPONSE_ENCODING)


class Driver:
    def __init__(self, arguments):
        self.settings = json.loads((WORKSPACE / "config/legacy-build.json").read_bytes())
        self.manifest = json.loads((WORKSPACE / "config/build-targets.json").read_bytes())
        self.configuration = arguments.configuration
        self.compile_only = arguments.compile_only
        self.rebuild = arguments.rebuild
        self.keep_going = arguments.keep_going
        self.graph = full_path(self.settings["generatedDirectory"])
        self.output = full_path(Path(arguments.output_directory) / self.configuration.lower())
        self.target = arguments.target
        self.operations = []
        self.imports = {}
        self.failures = 0
        self.wine = arguments.wine or "wine"
        self.wine_prefix = full_path("build/vc7/wineprefix")
        self.tools = self.load_tools()

    # --- toolchain identity -------------------------------------------------
    def load_tools(self):
        tools = {}
        expected = self.settings["toolchain"]["expectedSha256"]
        for name in ("compiler", "librarian", "linker"):
            path = full_path(self.settings["toolchain"][name])
            if not path.is_file():
                raise SystemExit("Missing supplied legacy %s: %s" % (name, path))
            digest_value = digest(path)
            if digest_value != expected[name]:
                raise SystemExit("Supplied legacy %s identity changed: %s" % (name, path))
            tools[name] = path
        identity = json.loads(
            (WORKSPACE / self.settings["toolchain"]["identityManifest"]).read_bytes())
        for name, pinned in identity["tools"].items():
            path = full_path(pinned["path"])
            if digest(path) != pinned["sha256"]:
                raise SystemExit("VC7 toolchain identity changed: %s" % path)
        return tools

    def verify_inputs(self):
        if self.manifest["schemaVersion"] != 1:
            raise SystemExit("Unsupported build-target manifest")
        dependency_bundle.verify(WORKSPACE)

    # --- planning -----------------------------------------------------------
    def plan(self):
        settings = self.settings
        by_id = {node["id"]: node for node in self.manifest["targets"]}
        by_name = {node["name"]: node for node in self.manifest["targets"]}
        focus = settings.get("sourceTargets", {}).get(self.target)
        if focus:
            self.compile_only = self.compile_only or focus["compileOnly"]
            source_target = focus["target"]
        else:
            source_target = self.target
        if source_target not in by_name:
            raise SystemExit("No VC7 target named %s" % source_target)
        selected = {}

        def visit(node_id):
            if node_id in selected:
                return
            selected[node_id] = by_id[node_id]
            if not focus:
                for dependency in by_id[node_id]["dependencies"]:
                    visit(dependency["id"])

        visit(by_name[source_target]["id"])
        self.selected = selected
        self.focus = focus

        self.artifact_map = {}
        self.target_artifacts = {}
        for node in selected.values():
            if node["type"] in ("STATIC_LIBRARY", "EXECUTABLE"):
                artifacts = [a for a in node["artifacts"]
                             if a["path"].endswith((".lib", ".exe"))]
                if not artifacts:
                    raise SystemExit("No primary artifact for %s" % node["name"])
                built = self.output / Path(artifacts[0]["path"]).name
                self.artifact_map[str(full_path(artifacts[0]["path"], self.graph))] = built
                self.target_artifacts[node["id"]] = built

        self.units = []
        for node in sorted(selected.values(), key=lambda item: item["name"]):
            directory = self.output / "objects" / node["name"]
            for ordinal, source in enumerate(node["sources"]):
                if source.get("compileGroupIndex") is None:
                    continue
                if focus and source["path"].replace("\\", "/") not in focus["sources"]:
                    continue
                group = node["compileGroups"][source["compileGroupIndex"]]
                if group["language"] not in ("C", "CXX"):
                    raise SystemExit("Unsupported primary source language: %s" % group["language"])
                directory.mkdir(parents=True, exist_ok=True)
                basename = "%04d-%s" % (ordinal, Path(source["path"]).name)
                self.units.append({
                    "target": node["name"],
                    "targetID": node["id"],
                    "node": node,
                    "source": full_path(source["path"]),
                    "language": group["language"],
                    "group": group,
                    "object": directory / (basename + ".obj"),
                    "prefix": directory / basename,
                })
        self.selected_nodes = sorted(selected.values(), key=lambda item: item["name"])

    # --- execution ----------------------------------------------------------
    def run_tool(self, kind, arguments, prefix):
        response = str(prefix) + ".rsp"
        write_response(response, arguments)
        environment = dict(os.environ)
        environment["WINEPREFIX"] = str(self.wine_prefix)
        environment["WINEDEBUG"] = WINE_DEBUG
        executable = self.tools[kind]
        process = subprocess.run(
            [self.wine, str(executable.relative_to(WORKSPACE)), "@" + str(Path(response).relative_to(WORKSPACE))],
            cwd=WORKSPACE, env=environment,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = process.stdout.decode(RESPONSE_ENCODING, errors="replace")
        Path(str(prefix) + ".log").write_text(log, encoding=RESPONSE_ENCODING, errors="replace")
        self.operations.append({
            "tool": kind, "executable": str(executable), "arguments": arguments,
            "response": response, "log": str(prefix) + ".log", "exitCode": process.returncode,
        })
        if process.returncode != 0:
            for line in log.splitlines():
                if DIAGNOSTIC.search(line):
                    print("    " + line.strip())
        return process.returncode

    def compile_units(self):
        settings = self.settings
        configuration = settings["configurations"][self.configuration]
        for unit in self.units:
            arguments = list(settings["compileOptions"]) + list(configuration["compileOptions"])
            arguments.append("/TC" if unit["language"] == "C" else "/TP")
            target_options = settings.get("targetCompileOptions", {}).get(unit["target"], {})
            arguments += target_options.get(self.configuration, [])
            for source_options, overrides in settings.get("sourceCompileOptions", {}).items():
                if full_path(source_options) == unit["source"]:
                    arguments += overrides.get(self.configuration, [])
            for define in settings.get("targetCompileDefinitions", {}).get(unit["target"], []):
                arguments.append("/D" + define)
            for define in unit["group"].get("defines", []):
                arguments.append("/D" + define["define"])
            for fragment in unit["group"].get("compileCommandFragments", []):
                for flag in fragment["fragment"].split():
                    if flag.startswith("/FI"):
                        arguments.append(flag)
            for include in unit["group"].get("includes", []):
                arguments.append("/I" + str(full_path(include["path"])))
            for directory in settings["toolchain"]["includeDirectories"]:
                arguments.append("/I" + str(full_path(directory)))
            arguments += ["/c", "/Fo" + str(unit["object"].relative_to(WORKSPACE)),
                          str(unit["source"].relative_to(WORKSPACE))]
            state_path = str(unit["prefix"]) + ".state.json"
            key = json.dumps({
                "arguments": arguments,
                "compiler": self.tools["compiler"].name,
                "identity": digest(WORKSPACE / self.settings["toolchain"]["identityManifest"]),
                "settings": digest(WORKSPACE / "config/legacy-build.json"),
            }, sort_keys=True)
            can_reuse = (not self.rebuild and Path(state_path).is_file()
                         and unit["object"].is_file())
            if can_reuse:
                state = json.loads(Path(state_path).read_bytes())
                can_reuse = (state["key"] == key
                             and state["objectSha256"] == digest(unit["object"]))
                for name, expected in state.get("inputs", {}).items():
                    path = full_path(name)
                    if not path.is_file() or digest(path) != expected:
                        can_reuse = False
                        break
            if can_reuse:
                print("Current: %s/%s" % (unit["target"], unit["source"].name))
                continue
            print("CL7: %s/%s" % (unit["target"], unit["source"].name), flush=True)
            before = digest(unit["source"])
            if self.run_tool("compiler", arguments, unit["prefix"]) != 0:
                self.failures += 1
                if not self.keep_going:
                    return False
                continue
            if not unit["object"].is_file():
                raise SystemExit("CL7 returned success without object: %s" % unit["object"])
            inputs = {str(unit["source"].relative_to(WORKSPACE)): before}
            for line in Path(str(unit["prefix"]) + ".log").read_text(
                    encoding=RESPONSE_ENCODING, errors="replace").splitlines():
                match = INCLUDE_LOG.match(line)
                if not match:
                    continue
                header = match.group(1).strip().replace("\\", "/")
                if header[:3].lower() in ("z:/", "z:\\"):
                    header = header[3:].lstrip("/\\")
                header_path = full_path(header)
                if header_path.is_file():
                    inputs[str(header_path.relative_to(WORKSPACE))] = digest(header_path)
            Path(state_path).write_bytes(json.dumps(
                {"key": key, "inputs": inputs, "objectSha256": digest(unit["object"])},
                indent=1).encode())
        return self.failures == 0

    def archive_targets(self):
        for node in self.selected_nodes:
            if node["type"] != "STATIC_LIBRARY":
                continue
            objects = [str(unit["object"].relative_to(WORKSPACE))
                       for unit in self.units if unit["targetID"] == node["id"]]
            if not objects:
                raise SystemExit("No rebuilt object input for archive %s" % node["name"])
            built = str(self.target_artifacts[node["id"]].relative_to(WORKSPACE))
            arguments = ["/NOLOGO", "/MACHINE:X86", "/OUT:" + built]
            for directory in self.settings["toolchain"]["libraryDirectories"]:
                arguments.append("/LIBPATH:" + str(full_path(directory)))
            arguments += objects
            prefix = self.output / "logs" / (node["name"] + "-archive")
            prefix.parent.mkdir(parents=True, exist_ok=True)
            if self.run_tool("librarian", arguments, prefix) != 0:
                raise SystemExit("Legacy LIB failed for %s" % node["name"])

    def generate_granny21(self):
        """Build granny21.lib from the verified def, then set IMPORT_NAME."""
        directory = self.output / "granny21"
        directory.mkdir(parents=True, exist_ok=True)
        library = directory / "granny21.lib"
        arguments = [
            "/nologo", "/machine:x86",
            "/def:" + str((WORKSPACE / "build/vc7/granny21/granny21.def").relative_to(WORKSPACE)),
            "/out:" + str(library.relative_to(WORKSPACE)),
        ]
        prefix = self.output / "logs" / "granny21-archive"
        prefix.parent.mkdir(parents=True, exist_ok=True)
        if self.run_tool("librarian", arguments, prefix) != 0:
            raise SystemExit("Original Granny import generation failed")
        data = bytearray(library.read_bytes())
        assert data[:8] == b"!<arch>\n"
        offset = 8
        names = []
        while offset < len(data):
            assert data[offset + 58:offset + 60] == b"`\n"
            size = int(data[offset + 48:offset + 58].decode("ascii").strip())
            start = offset + 60
            body = data[start:start + size]
            if body[:4] == b"\x00\x00\xff\xff":
                assert struct.unpack_from("<H", body, 6)[0] == 0x14C
                name, dll = body[20:].split(b"\0")[:2]
                assert name.startswith(b"_Granny") and dll == b"granny2.dll"
                flags = struct.unpack_from("<H", body, 18)[0]
                assert flags >> 2 == 2
                struct.pack_into("<H", data, start + 18, (flags & ~0x1C) | (1 << 2))
                names.append(name.decode("ascii"))
            offset = start + size + (size % 2)
        assert len(names) == 43
        library.write_bytes(data)
        receipt_path = WORKSPACE / "build/vc7/granny21/granny21-imports.json"
        receipt = json.loads(receipt_path.read_bytes())
        receipt["outputs"].append({"path": str((WORKSPACE / library.relative_to(WORKSPACE)).resolve()),
                                   "sha256": digest(library)})
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
        self.imports[str(full_path("granny21/granny21.lib", self.graph))] = library

    def link_targets(self):
        for node in self.selected_nodes:
            if node["type"] != "EXECUTABLE":
                continue
            link_arguments = ["/NOLOGO", "/MACHINE:X86", "/INCREMENTAL:NO",
                              "/OUT:" + str(self.target_artifacts[node["id"]].relative_to(WORKSPACE))]
            link_arguments += self.settings["configurations"][self.configuration].get("linkOptions", [])
            for directory in self.settings["toolchain"]["libraryDirectories"]:
                link_arguments.append("/LIBPATH:" + str(full_path(directory)))
            link_arguments += [str(unit["object"].relative_to(WORKSPACE))
                               for unit in self.units if unit["targetID"] == node["id"]]
            for fragment in node.get("link", {}).get("commandFragments", []):
                if fragment["role"] == "flags":
                    for flag in fragment["fragment"].split():
                        if KEEP_LINK_FLAGS.match(flag):
                            link_arguments.append(flag)
                elif fragment["role"] == "libraries":
                    for library in fragment["fragment"].split():
                        mapped = self.imports.get(str(full_path(library, self.graph))) \
                            or self.artifact_map.get(str(full_path(library, self.graph)))
                        if mapped:
                            link_arguments.append(str(mapped.relative_to(WORKSPACE)))
                        elif library.startswith("deps/") or library.startswith("deps\\"):
                            link_arguments.append(library)
                        elif Path(library).is_absolute() or "/" in library or "\\" in library:
                            raise SystemExit("Unmapped link input: %s" % library)
                        else:
                            link_arguments.append(library)
                else:
                    raise SystemExit("Unsupported link fragment: %s" % fragment["role"])
            prefix = self.output / "logs" / (node["name"] + "-link")
            prefix.parent.mkdir(parents=True, exist_ok=True)
            if self.run_tool("linker", link_arguments, prefix) != 0:
                raise SystemExit("VC7 LINK failed for %s" % node["name"])

    # --- records ------------------------------------------------------------
    def write_records(self, plan, completed):
        (self.output / "logs").mkdir(parents=True, exist_ok=True)
        target_log = self.output / "logs" / re.sub(r"[^A-Za-z0-9_.-]", "_", self.target)
        target_log.mkdir(parents=True, exist_ok=True)
        (target_log / "plan.json").write_bytes(json.dumps(plan, indent=1).encode())
        (target_log / "build.json").write_bytes(json.dumps({
            "target": self.target, "configuration": self.configuration,
            "operations": self.operations, "sourceTree": str(WORKSPACE),
            "targetManifest": "config/build-targets.json",
            "compileFailures": self.failures, "compileOnly": self.compile_only,
            "runExecuted": False, "codeSnapshots": False,
            "completed": completed,
        }, indent=1).encode())
        return target_log

    def run(self, arguments):
        if self.target == "openvb" and not self.compile_only:
            game = full_path(json.loads((WORKSPACE / "config/local.json").read_bytes())
                             .get("gameRoot", "deps/game") if (WORKSPACE / "config/local.json").exists()
                             else "deps/game") / "F3.exe"
            if not game.is_file():
                raise SystemExit(
                    "Full link needs the original demo at %s (Granny/Bink imports); "
                    "provide it via config/local.json gameRoot or use --compile-only."
                    % game)
        self.verify_inputs()
        self.plan()
        plan = {
            "target": self.target, "configuration": self.configuration,
            "output": str(self.output), "compileOnly": self.compile_only,
            "sources": [{"target": unit["target"], "source": str(unit["source"]),
                         "language": unit["language"], "object": str(unit["object"])}
                        for unit in self.units],
            "targets": [{"name": node["name"], "type": node["type"]}
                        for node in self.selected_nodes],
        }
        if arguments.plan_only:
            self.write_records(plan, completed=False)
            print("VC7 plan: %s, %d canonical translation units; %s"
                  % (self.target, len(self.units), self.output))
            return
        completed = False
        try:
            if self.compile_units():
                if not self.compile_only:
                    self.archive_targets()
                    if "openvb" in self.selected:
                        self.generate_granny21()
                    self.link_targets()
            elif self.failures:
                raise SystemExit("%d canonical translation unit(s) failed under VC7" % self.failures)
            completed = True
            print("Legacy %s completed; no game executable was launched." % self.target)
        finally:
            self.write_records(plan, completed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default=None)
    parser.add_argument("--configuration", default="Release")
    parser.add_argument("--output-directory", default="build/legacy-vc7")
    parser.add_argument("--compile-only", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--keep-going", action="store_true")
    parser.add_argument("--wine", default=os.environ.get("VC7_WINE", "wine"))
    arguments = parser.parse_args()
    if arguments.target is None:
        arguments.target = json.loads(
            (WORKSPACE / "config/legacy-build.json").read_bytes())["defaultTarget"]
    Driver(arguments).run(arguments)


if __name__ == "__main__":
    main()
