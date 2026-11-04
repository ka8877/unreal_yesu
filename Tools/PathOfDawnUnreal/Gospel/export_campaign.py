#!/usr/bin/env python3
"""Evaluate pinned Unity C# catalogs and emit the shared Gospel content.

Requires .NET 8 SDK, not Unity. No NuGet sources or network access are used.
The imported C# source snapshot is checked against both Git blob IDs and SHA256
before compiling; it is never parsed into an alternate, handwritten story.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEFAULT_OUTPUT = ROOT / "SourceArt/PathOfDawnUnreal/Gospel/Campaign.json"
SOURCE_COMMIT = "808d8d1e1eeed908d8925398f80c7173653ef364"


def verify_sources():
    source = HERE / "SourceReferences"
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("repository") != "ka8877/firstgame" or manifest.get("commit") != SOURCE_COMMIT:
        raise ValueError("The source manifest does not identify the reviewed Unity commit")
    paths = []
    for entry in manifest["files"]:
        name = entry["path"]
        if Path(name).name != name or not name.endswith(".cs") or name in paths:
            raise ValueError("Invalid or duplicate source filename: " + name)
        paths.append(name)
        raw = (source / name).read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
        if blob != entry["git_blob_sha"] or hashlib.sha256(raw).hexdigest() != entry["sha256"] or len(raw) != entry["bytes"]:
            raise ValueError("Pinned Unity source differs: " + name)
    if set(paths) != {path.name for path in source.glob("*.cs")}:
        raise ValueError("Untracked C# reference source found outside the manifest")
    return manifest


def evaluate(dotnet):
    verify_sources()
    executable = shutil.which(dotnet)
    if not executable:
        raise ValueError(".NET 8 SDK unavailable; pass --dotnet /path/to/dotnet")
    with tempfile.TemporaryDirectory(prefix="pathofdawn-gospel-export-") as temporary:
        work = Path(temporary)
        env = dict(os.environ, DOTNET_CLI_HOME=str(work / "cli"),
                   DOTNET_SKIP_FIRST_TIME_EXPERIENCE="1", DOTNET_NOLOGO="1",
                   DOTNET_CLI_TELEMETRY_OPTOUT="1")
        # Invoke the SDK's real C# compiler directly: no package restore, SDK
        # first-run migration mutex, downloaded dependencies or project output.
        # This also works in managed sandboxes that disallow NuGet's named mutex.
        sdk_list = subprocess.run([executable, "--list-sdks"], env=env, check=True,
                                  text=True, stdout=subprocess.PIPE).stdout.splitlines()
        sdk = next((line for line in reversed(sdk_list) if line.startswith("8.")), None)
        if sdk is None:
            raise ValueError(".NET 8 SDK is required to evaluate the Unity catalogs")
        version, location = sdk.split(" ", 1)
        sdk_path = Path(location.strip("[]")) / version
        framework_refs = sorted((sdk_path.parent.parent / "packs/Microsoft.NETCore.App.Ref").glob("8.*/ref/net8.0"))
        if not framework_refs:
            raise ValueError(".NET 8 reference assemblies are unavailable")
        assembly = work / "ExportUnityCampaign.dll"
        build = subprocess.run([
            executable, str(sdk_path / "Roslyn/bincore/csc.dll"), "-nologo",
            "-target:exe", "-deterministic+", "-utf8output", "-nostdlib+",
            "-out:" + str(assembly),
            *("-r:" + str(path) for path in sorted(framework_refs[-1].glob("*.dll"))),
            str(HERE / "ExportUnityCampaign.cs"),
            *(str(path) for path in sorted((HERE / "SourceReferences").glob("*.cs"))),
        ], env=env, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if build.returncode:
            raise ValueError("Unity catalog compilation failed:\n" + build.stdout)
        (work / "ExportUnityCampaign.runtimeconfig.json").write_text(json.dumps({
            "runtimeOptions": {"tfm": "net8.0", "framework": {
                "name": "Microsoft.NETCore.App", "version": "8.0.0"}}}), encoding="utf-8")
        result = subprocess.run([executable, str(assembly)],
                                env=env, text=True, encoding="utf-8", stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        if result.returncode:
            raise ValueError("Unity catalog evaluation failed:\n" + result.stderr)
        return json.loads(result.stdout)


def canonical_bytes(document):
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dotnet", default="dotnet")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="Reevaluate C# and require exact existing output bytes")
    parser.add_argument("--verify-sources-only", action="store_true")
    args = parser.parse_args()
    try:
        manifest = verify_sources()
        if args.verify_sources_only:
            print("Verified", len(manifest["files"]), "exact Unity C# source files at", SOURCE_COMMIT)
            return 0
        document = evaluate(args.dotnet)
        from validate_campaign import validate
        errors = validate(document)
        if errors:
            raise ValueError("Invalid evaluated content:\n" + "\n".join(errors))
        raw = canonical_bytes(document)
        if args.check:
            if not args.output.is_file() or args.output.read_bytes() != raw:
                raise ValueError("Campaign output differs from the evaluated Unity source: " + str(args.output))
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(raw)
        count = sum(len(quest["Beats"]) for quest in document["Quests"])
        print(("Verified" if args.check else "Exported"), len(document["Quests"]),
              "quests,", len(document["Readings"]), "readings,", count,
              "story beats from the original Unity C# catalogs")
        return 0
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
