"""Compile and execute the actual C++ Gospel state core against exported content.

This tests portable gameplay/save-state invariants. It does not compile Unreal,
exercise USaveGame, produce assets, or validate graphical execution.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "Games/PathOfDawnUnreal/Source/PathOfDawnUnreal/Core"
CAMPAIGN = ROOT / "SourceArt/PathOfDawnUnreal/Gospel/Campaign.json"
TEST_SOURCE = Path(__file__).with_name("gospel_core_tests.cpp")


def cpp_string(value):
    if not isinstance(value, str):
        raise ValueError("Campaign IDs must be strings")
    # JSON escaping is also a valid C++ UTF-8 string literal for these IDs.
    return json.dumps(value, ensure_ascii=True)


def fixture_header(document):
    """Project the actual IDs and beat boundaries; never replace story content."""
    rows = []
    for quest in document["Quests"]:
        is_prologue = quest["IsPrologue"]
        if type(is_prologue) is not bool:
            raise ValueError("IsPrologue must be a JSON boolean")
        rows.append("        {" + ", ".join([
            cpp_string(quest["Id"]), cpp_string(quest["ChapterId"]),
            cpp_string(quest["NpcId"]), cpp_string(quest["ReadingId"]),
            "true" if is_prologue else "false", str(len(quest["Beats"]))
        ]) + "}")
    if type(document["ContentVersion"]) is not int or document["ContentVersion"] < 1:
        raise ValueError("ContentVersion must be a positive integer")
    return (
        '#pragma once\n#include "GospelState.h"\n'
        "inline gospel::Campaign GospelFixture() {\n"
        f"    return {{{cpp_string(document['CampaignId'])}, {document['ContentVersion']}, {{\n"
        + ",\n".join(rows) + "\n    }};\n}\n"
    )


def run(sanitize=False):
    msvc = (shutil.which("cl.exe") or shutil.which("cl")) if os.name == "nt" else None
    compiler = msvc or shutil.which("g++") or shutil.which("clang++")
    if compiler is None:
        raise RuntimeError("C++17 compiler is required (MSVC Developer PowerShell, g++ or clang++); the Gospel core was not tested")
    if sanitize and msvc:
        raise RuntimeError("Combined ASan/UBSan mode requires g++ or clang++; the MSVC run was not executed")
    document = json.loads(CAMPAIGN.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="pathofdawn-gospel-core-") as folder:
        build = Path(folder)
        (build / "GospelFixture.h").write_text(fixture_header(document), encoding="utf-8")
        executable = build / ("gospel_core_tests.exe" if os.name == "nt" else "gospel_core_tests")
        if msvc:
            # Run from the temporary build folder so MSVC .obj/.pdb outputs
            # remain outside the source tree too. The caller supplies the VS
            # Developer PowerShell environment and its Windows SDK selectors.
            command = [compiler, "/nologo", "/std:c++17", "/W4", "/WX", "/EHsc", "/utf-8", "/Od",
                       "/I" + str(CORE), "/I" + str(build), str(TEST_SOURCE),
                       "/Fe" + str(executable), "/Fo" + str(build / "gospel_core_tests.obj")]
        else:
            flags = ["-std=c++17", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O1", "-g"]
            if sanitize:
                flags.extend(["-fsanitize=address,undefined", "-fno-omit-frame-pointer"])
            command = [compiler, *flags, "-I", str(CORE), "-I", str(build),
                       str(TEST_SOURCE), "-o", str(executable)]
        subprocess.run(command, cwd=build, check=True)
        environment = os.environ.copy()
        if sanitize:
            # LeakSanitizer's process inspection is unsupported by this sandbox.
            # Address/undefined-behaviour checks remain enabled.
            environment["ASAN_OPTIONS"] = "detect_leaks=0:halt_on_error=1"
            environment["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"
        subprocess.run([str(executable)], env=environment, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sanitize", action="store_true", help="enable ASan/UBSan; leak inspection is disabled")
    args = parser.parse_args()
    run(args.sanitize)
