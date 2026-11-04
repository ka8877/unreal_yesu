#!/usr/bin/env python3
"""Prepare a vendor-neutral Windows preview, without building or deploying Unreal.

First create a candidate, test its extracted ZIP on a Windows GPU host, and use
the candidate manifest's identities in a graphical smoke report. Packaging and
file-header checks are not proof of an Unreal build, gameplay, or streaming.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[3]
PREVIEW_MAP = "/Game/PathOfDawnGospel/Maps/L_GospelTemplePreview"
PREVIEW_QUESTS = (
    "nazareth-departure", "pilgrim-spring", "festival-courtyard",
    "listening-court", "teachers-circle", "parents-reunite", "nazareth-return",
)
SMOKE_CHECKS = (
    "extractedPackageLaunch", "title", "movement", "dialogue",
    "allPreviewQuests", "koreanGlyphs", "audio", "saveRestartContinue",
)
RESERVED = {"preview-manifest.json", "play-gospel.cmd", "readme-gospel.txt", "evidence"}
FORBIDDEN_PARTS = {
    "saved", "logs", "screenshots", "crashes", "intermediate", ".git", ".aws",
    ".ssh", ".codex", "secrets", "credentials", "__pycache__", "node_modules",
}
FORBIDDEN_SUFFIXES = {".pdb", ".exp", ".lib", ".pem", ".key", ".p12", ".pfx", ".sav", ".log"}
SECRET_ASSIGNMENT = re.compile(
    r"(?im)[\"']?(?:api[_-]?key|access[_-]?token|secret[_-]?key|password|client[_-]?secret)"
    r"[\"']?\s*[:=]\s*[\"']?([^\r\n\"',}]+)"
)


class ReleaseError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReleaseError(message)


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def strict_json(path: Path) -> object:
    def unique(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            require(key not in result, f"Duplicate JSON key in {path.name}: {key}")
            result[key] = value
        return result
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique,
                          parse_constant=lambda value: (_ for _ in ()).throw(ReleaseError(f"Invalid JSON number: {value}")))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReleaseError(f"Cannot read JSON {path.name}: {error}") from error


def safe_relative(value: str) -> PurePosixPath:
    require(isinstance(value, str) and value != "", "File paths must be nonempty strings")
    require("\\" not in value and ":" not in value and "\0" not in value, f"Unsafe archive path: {value!r}")
    parts = value.split("/")
    require(not value.startswith("/") and all(p not in {"", ".", ".."} for p in parts), f"Unsafe archive path: {value!r}")
    require(all(not p.endswith((" ", ".")) and not re.search(r'[<>|?*\x00-\x1f]', p) for p in parts), f"Unsafe Windows path: {value!r}")
    require(all(p.split(".")[0].casefold() not in {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))} for p in parts), f"Reserved Windows filename: {value!r}")
    return PurePosixPath(value)


def no_link_components(path: Path) -> None:
    for parent in (path, *path.parents):
        require(not parent.is_symlink(), f"Symbolic links are not accepted: {parent.name}")
        if parent.exists():
            attributes = getattr(parent.lstat(), "st_file_attributes", 0)
            require(not attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400), f"Windows reparse points are not accepted: {parent.name}")


def check_upload_path(relative: str) -> None:
    p = safe_relative(relative)
    require(not any(part.casefold() in FORBIDDEN_PARTS for part in p.parts), f"Private/generated directory in build: {relative}")
    require(not any(part.casefold().startswith(".env") for part in p.parts), f"Environment file in build: {relative}")
    require(p.suffix.casefold() not in FORBIDDEN_SUFFIXES, f"Private/debug file in build: {relative}")
    require(p.name.casefold() not in {"credentials.json", "secrets.json", "config_el.json", "id_rsa", "id_ed25519"}, f"Credential file in build: {relative}")


def inspect_text(path: Path, relative: str) -> None:
    if path.suffix.casefold() not in {".ini", ".json", ".txt", ".yaml", ".yml", ".xml", ".cfg", ".config"}:
        return
    require(path.stat().st_size <= 16 * 1024 * 1024, f"Unexpectedly large configuration file: {relative}")
    try:
        content = path.read_text(encoding="utf-8-sig")
    except UnicodeError:
        raise ReleaseError(f"Configuration is not UTF-8; inspect before uploading: {relative}")
    require("-----BEGIN " not in content or "PRIVATE KEY-----" not in content, f"Private key in build file: {relative}")
    for match in SECRET_ASSIGNMENT.finditer(content):
        value = match.group(1).strip().rstrip(";").strip()
        require(value.casefold() in {"", "none", "null", "false", "changeme", "placeholder"} or
                (value.startswith("${") and value.endswith("}")), f"Possible credential in build file: {relative}")


def inventory(build_root: Path) -> tuple[list[dict], dict[str, Path]]:
    no_link_components(build_root)
    require(build_root.is_dir(), "--build-root must be an existing packaged folder")
    files: dict[str, Path] = {}
    seen = set()
    for path in sorted(build_root.rglob("*")):
        relative = path.relative_to(build_root).as_posix()
        no_link_components(path)
        check_upload_path(relative)
        folded = relative.casefold()
        require(folded not in seen, f"Case-insensitive Windows path collision: {relative}")
        seen.add(folded)
        require(relative.split("/")[0].casefold() not in RESERVED, f"Reserved release filename: {relative}")
        if path.is_dir():
            continue
        require(stat.S_ISREG(path.lstat().st_mode), f"Non-regular file in build: {relative}")
        inspect_text(path, relative)
        files[relative] = path
    require(bool(files), "Packaged build is empty")
    rows = [{"path": name, "bytes": path.stat().st_size, "sha256": digest_file(path)} for name, path in files.items()]
    return rows, files


def verify_packaged_layout(files: dict[str, Path]) -> str:
    executables = [name for name in files if re.fullmatch(r"(?:[^/]+/)*Binaries/Win64/PathOfDawnUnreal[^/]*\.exe", name, re.IGNORECASE)]
    require(len(executables) == 1, "Expected exactly one PathOfDawnUnreal*.exe under Binaries/Win64")
    exe = files[executables[0]]
    with exe.open("rb") as stream:
        header = stream.read(64)
        require(len(header) == 64 and header[:2] == b"MZ", "Executable has no DOS/PE header")
        offset = struct.unpack_from("<I", header, 60)[0]
        require(64 <= offset <= exe.stat().st_size - 6, "Executable PE header offset is invalid")
        stream.seek(offset)
        require(stream.read(6) == b"PE\0\0\x64\x86", "Expected an x64 Windows PE executable")
    containers = {name: path for name, path in files.items() if Path(name).suffix.casefold() in {".pak", ".utoc", ".ucas"}}
    require(bool(containers), "No cooked .pak or .utoc/.ucas containers found")
    folded = {name.casefold(): path for name, path in containers.items()}
    for name, path in containers.items():
        require("content/paks/" in name.casefold(), f"Cooked container is outside Content/Paks: {name}")
        require(path.stat().st_size > 0, f"Empty cooked container: {name}")
        suffix = path.suffix.casefold()
        if suffix == ".pak":
            with path.open("rb") as stream:
                stream.seek(max(0, path.stat().st_size - 4096))
                footer = stream.read()
            marker = footer.rfind(struct.pack("<I", 0x5A6F12E1))
            require(marker >= 0 and marker + 8 <= len(footer), f"Missing Unreal PAK footer signature: {name}")
            require(1 <= struct.unpack_from("<I", footer, marker + 4)[0] <= 20, f"Unsupported/corrupt PAK footer version: {name}")
        if suffix in {".utoc", ".ucas"}:
            if suffix == ".utoc":
                with path.open("rb") as stream:
                    require(stream.read(16) == b"-==--==--==--==-", f"Missing Unreal IoStore TOC signature: {name}")
            stem = name[:-5] if suffix == ".utoc" else re.sub(r"_s\d+$", "", name[:-5], flags=re.IGNORECASE)
            other = stem + (".ucas" if suffix == ".utoc" else ".utoc")
            require(other.casefold() in folded, f"Incomplete IoStore pair: {name}")
    return executables[0]


def read_campaign(path: Path) -> tuple[dict, str]:
    no_link_components(path)
    document = strict_json(path)
    require(isinstance(document, dict), "Campaign must be a JSON object")
    require(document.get("SchemaVersion") == 1 and document.get("CampaignId") == "gospel-pilgrimage", "Unsupported Gospel campaign schema/id")
    require(type(document.get("ContentVersion")) is int and document["ContentVersion"] > 0, "Campaign ContentVersion is missing")
    quests = document.get("Quests")
    require(isinstance(quests, list) and all(isinstance(q, dict) for q in quests), "Campaign Quests is invalid")
    ids = [q.get("Id") for q in quests]
    require(all(isinstance(qid, str) and qid for qid in ids) and len(set(ids)) == len(ids), "Campaign quest IDs are missing/duplicated")
    require(tuple(q["Id"] for q in quests if q.get("ChapterId") == "temple") == PREVIEW_QUESTS, "Campaign temple preview must contain the reviewed seven quests in order")
    source = document.get("Source", {})
    require(isinstance(source, dict) and source.get("Repository") == "ka8877/firstgame" and re.fullmatch(r"[0-9a-fA-F]{40}", str(source.get("Commit", ""))), "Campaign Unity source identity is invalid")
    return document, digest_file(path)


def source_identity(commit: str | None, repo_root: Path) -> dict:
    require(commit is None or re.fullmatch(r"[0-9a-fA-F]{40}", commit) is not None, "--source-commit must be a full 40-character Git SHA")
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=repo_root, check=True, capture_output=True, text=True).stdout)
    except (OSError, subprocess.CalledProcessError):
        head, dirty = None, None
    require(commit is not None or (head is not None and re.fullmatch(r"[0-9a-f]{40}", head) is not None), "Git identity unavailable; provide --source-commit")
    return {"commit": (commit or head).lower(), "dirty": dirty if commit is None or commit.lower() == head else None,
            "identityMethod": "supplied-commit" if commit else "git-head", "packagingHead": head}


def check_build_receipt(files: dict[str, Path], build_id: str, source: dict, campaign_sha: str) -> None:
    for name, path in files.items():
        if Path(name).name.casefold() not in {"build-manifest.json", "gospel-build-manifest.json"}:
            continue
        receipt = strict_json(path)
        require(isinstance(receipt, dict), f"Build manifest must be an object: {name}")
        require(receipt.get("buildId") == build_id, f"Build manifest belongs to another build: {name}")
        # Legacy manifests may not carry Gospel identities. Validate every supplied
        # identity, without upgrading their absence to evidence of a Gospel build.
        for key, expected in (("sourceCommit", source["commit"]), ("campaignSha256", campaign_sha), ("map", PREVIEW_MAP)):
            require(key not in receipt or receipt[key] == expected, f"Build manifest {key} mismatch: {name}")
        require("previewQuestIds" not in receipt or receipt["previewQuestIds"] == list(PREVIEW_QUESTS), f"Build manifest preview quest mismatch: {name}")
        for key in ("executable", "runtimeExecutable"):
            if key in receipt:
                target = receipt[key]
                require(isinstance(target, str), f"Build manifest {key} is invalid: {name}")
                relative = str(safe_relative(target.replace("\\", "/")))
                require(relative in files and relative.casefold().endswith(".exe"), f"Build manifest {key} is missing: {name}")
        if "files" in receipt:
            require(isinstance(receipt["files"], list) and receipt["files"], f"Build manifest files is invalid: {name}")
            seen = set()
            for row in receipt["files"]:
                require(isinstance(row, dict), f"Invalid manifest file entry: {name}")
                relative = str(safe_relative(row.get("path", "")))
                require(relative not in seen and relative in files and relative != name, f"Invalid/missing manifest file: {relative}")
                seen.add(relative)
                require(row.get("sha256") == digest_file(files[relative]) and row.get("bytes") == files[relative].stat().st_size, f"Manifest file changed: {relative}")
        if "payloadSha256" in receipt:
            expected_sha = receipt["payloadSha256"]
            require(isinstance(expected_sha, str) and re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha), f"Build manifest payload hash is invalid: {name}")
            payload = {relative: path for relative, path in files.items() if Path(relative).name.casefold() not in {"build-manifest.json", "gospel-build-manifest.json", "smoke-report.json"}}
            algorithm = receipt.get("payloadHashAlgorithm")
            if algorithm == "sha256-of-canonical-indented-json-file-rows-v1":
                rows = [{"path": relative, "bytes": path.stat().st_size, "sha256": digest_file(path)} for relative, path in sorted(payload.items())]
                hashes = {digest_bytes(canonical(rows))}
            elif algorithm is None and Path(name).name.casefold() == "build-manifest.json":
                # Legacy Common.ps1 Get-DawnPayloadHash used uppercase hashes and
                # a tab-separated path list; Windows versions retained either
                # native or normalized separators. No unsupported hash is trusted.
                hashes = set()
                for order in (sorted(payload), sorted(payload, key=str.casefold)):
                    for separator in ("/", "\\"):
                        text = "\n".join(relative.replace("/", separator) + "\t" + digest_file(payload[relative]).upper() for relative in order)
                        hashes.add(digest_bytes(text.encode("utf-8")))
            else:
                raise ReleaseError(f"Unsupported build manifest payload hash algorithm: {name}")
            require(expected_sha.lower() in hashes, f"Build manifest payload changed: {name}")


def graphical_evidence(path: Path, expected: dict) -> tuple[dict, dict[str, Path]]:
    no_link_components(path)
    report = strict_json(path)
    require(isinstance(report, dict), "Graphical smoke report must be an object")
    require(report.get("evidenceKind") == "actual-unreal-graphical", "Smoke report must attest actual Unreal graphical execution")
    for key, value in expected.items():
        require(report.get(key) == value, f"Smoke report {key} belongs to different content/build")
    require(isinstance(report.get("tester"), str) and report["tester"].strip(), "Smoke report requires a tester")
    require(isinstance(report.get("engineVersion"), str) and re.fullmatch(r"5\.8\.\d+(?:[-+][A-Za-z0-9._-]+)?", report["engineVersion"]), "Smoke report requires the actual UE 5.8 patch version")
    try:
        when = datetime.fromisoformat(report.get("testedUtc", "").replace("Z", "+00:00"))
        require(when.utcoffset() is not None and when.utcoffset().total_seconds() == 0, "Smoke testedUtc must be UTC")
    except (ValueError, TypeError, AttributeError):
        raise ReleaseError("Smoke report testedUtc must be a UTC ISO date/time")
    checks = report.get("checks", {})
    require(isinstance(checks, dict) and all(checks.get(key) is True for key in SMOKE_CHECKS), "Actual graphical smoke checks are missing/failed")
    captures = report.get("captures")
    require(isinstance(captures, list) and len(captures) >= 6, "Smoke report needs at least six actual gameplay captures")
    sources = {}
    capture_rows = []
    hashes = set()
    for index, capture in enumerate(captures):
        require(isinstance(capture, dict), "Smoke captures must include relative path and sha256")
        relative = safe_relative(capture.get("path", ""))
        source_path = path.parent.joinpath(*relative.parts)
        no_link_components(source_path)
        require(source_path.is_file(), "Smoke capture is missing")
        with source_path.open("rb") as stream:
            header = stream.read(16)
        suffix = source_path.suffix.casefold()
        require((suffix == ".png" and header.startswith(b"\x89PNG\r\n\x1a\n")) or (suffix in {".jpg", ".jpeg"} and header.startswith(b"\xff\xd8\xff")), "Smoke capture must be a PNG/JPEG image")
        sha = digest_file(source_path)
        require(capture.get("sha256") == sha and sha not in hashes, "Smoke capture hash mismatch or duplicate image")
        hashes.add(sha)
        destination = f"evidence/captures/{index + 1:02d}{suffix}"
        sources[destination] = source_path
        capture_rows.append({"path": destination, "sha256": sha, "bytes": source_path.stat().st_size})
    normalized = {key: report[key] for key in (*expected.keys(), "evidenceKind", "tester", "engineVersion", "testedUtc", "checks")}
    normalized["captures"] = capture_rows
    return normalized, sources


def launch_script(executable: str, build_id: str) -> bytes:
    # All arguments are validated literals; the quoted %~dp0 form supports spaces
    # and uses the real cooked binary instead of the historical default map.
    path = executable.replace("/", "\\").replace("%", "%%")
    return (f'@echo off\r\nsetlocal DisableDelayedExpansion\r\nchcp 65001 >nul\r\ncd /d "%~dp0"\r\n'
            f'"%~dp0{path}" {PREVIEW_MAP} -DawnBuildId={build_id} %*\r\n'
            'exit /b %errorlevel%\r\n').encode("utf-8")


def readme(status: str) -> bytes:
    return (f"Path of Dawn - Gospel Temple Preview\nStatus: {status}\n\n"
            "Extract the whole ZIP on a compatible Windows GPU computer and run PLAY-GOSPEL.cmd.\n"
            "Testers do not need Unreal Editor or Visual Studio. If Windows reports missing runtime\n"
            "prerequisites, use Epic's official Unreal runtime prerequisite installer supplied with\n"
            "the build (Engine/Extras/Redist/en-us), or obtain it from the build maintainer.\n"
            f"The launcher explicitly requests {PREVIEW_MAP}.\n"
            "This is a seven-quest temple preview; it is not the historical Galilee prototype.\n"
            "A missing-map error requires a fresh Cook including this Gospel map.\n\n"
            "Managed Pixel Streaming: upload this ZIP as a packaged Windows application.\n"
            "Select the real executable recorded in preview-manifest.json and set its map\n"
            f"argument to {PREVIEW_MAP}. The .cmd is for local play, not a host control service.\n"
            "The provider supplies the actual -PixelStreamingURL=ws://... endpoint and any\n"
            "-RenderOffscreen/-AudioMixer arguments. Do not hard-code a localhost endpoint.\n"
            "UE 5.8 / PixelStreaming2 compatibility, GPU capacity, audio/video/input and\n"
            "the provider's real URL must be tested. No provider upload or deployment occurred.\n"
            "The current game uses a local save slot. Host sessions require isolated storage\n"
            "or explicit reset; persistent cross-session/cross-edition saves are not provided.\n\n"
            "Manifest hashes and PE/container presence checks do not prove a successful Cook\n"
            "or game launch. Candidate status means actual graphical tests have not been supplied.\n"
            "Graphical-smoke-attested status records the named tester's evidence; it does not\n"
            "certify final cinematic art quality, streaming media, or readiness for public release.\n").encode("utf-8")


def prepare(build_root: Path, output: Path, build_id: str, campaign_path: Path,
            commit: str | None = None, smoke_report: Path | None = None, repo_root: Path = ROOT) -> dict:
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,79}", build_id) is not None, "Invalid --build-id")
    build_root, output, campaign_path = (p.absolute() for p in (build_root, output, campaign_path))
    no_link_components(output)
    no_link_components(build_root)
    build_root, output = build_root.resolve(), output.resolve()
    require(not output.exists(), "Output directory already exists; choose a new directory")
    require(not output.is_relative_to(build_root) and not build_root.is_relative_to(output), "Output and build-root must not contain each other")
    campaign, campaign_sha = read_campaign(campaign_path)
    source = source_identity(commit, repo_root)
    rows, files = inventory(build_root)
    executable = verify_packaged_layout(files)
    payload_sha = digest_bytes(canonical(rows))
    check_build_receipt(files, build_id, source, campaign_sha)
    status = "candidate-not-graphically-verified"
    evidence, evidence_files = None, {}
    if smoke_report:
        require(source["dirty"] is not True, "A dirty source checkout cannot receive graphical-smoke-attested status")
        evidence, evidence_files = graphical_evidence(smoke_report.absolute(), {
            "buildId": build_id, "sourceCommit": source["commit"], "payloadSha256": payload_sha,
            "campaignSha256": campaign_sha, "map": PREVIEW_MAP, "previewQuestIds": list(PREVIEW_QUESTS),
        })
        status = "graphical-smoke-attested"
    manifest = {
        "schemaVersion": 1, "artifactType": "gospel-windows-preview", "buildId": build_id,
        "status": status, "sourceCommit": source["commit"], "source": source,
        "campaign": {"id": campaign["CampaignId"], "schemaVersion": campaign["SchemaVersion"],
                     "contentVersion": campaign["ContentVersion"], "sha256": campaign_sha, "unitySource": campaign["Source"]},
        "map": PREVIEW_MAP, "previewQuestIds": list(PREVIEW_QUESTS), "executable": executable,
        "payloadSha256": payload_sha, "payloadHashAlgorithm": "sha256-of-canonical-indented-json-file-rows-v1",
        "files": rows, "graphicalSmoke": evidence,
        "validation": {"executable": "x64-PE-header-only", "containers": "pak-footer-or-iostore-header-pairs-and-byte-hashes-only",
                       "unrealBuild": "not-established-by-this-tool", "mapCook": "tester-attested" if evidence else "not-established",
                       "pixelStreamingMedia": "not-performed", "hostedDeployment": "not-performed", "publicReady": False},
    }
    generated = {"PLAY-GOSPEL.cmd": launch_script(executable, build_id), "README-GOSPEL.txt": readme(status)}
    manifest["releaseFiles"] = [{"path": name, "bytes": len(data), "sha256": digest_bytes(data)} for name, data in sorted(generated.items())]
    if evidence:
        generated["evidence/graphical-smoke.json"] = canonical(evidence)
    generated["preview-manifest.json"] = canonical(manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    archive = output / f"PathOfDawn-Gospel-Windows-{build_id}.zip"
    try:
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as zipped:
            for name in sorted(set(files) | set(generated) | set(evidence_files)):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                with zipped.open(info, "w", force_zip64=True) as target:
                    if name in generated:
                        target.write(generated[name])
                    else:
                        original = files.get(name) or evidence_files[name]
                        expected_sha = next((row["sha256"] for row in rows if row["path"] == name), None)
                        if expected_sha is None:
                            expected_sha = next(row["sha256"] for row in evidence["captures"] if row["path"] == name)
                        h = hashlib.sha256()
                        with original.open("rb") as original_stream:
                            for block in iter(lambda: original_stream.read(1024 * 1024), b""):
                                target.write(block)
                                h.update(block)
                        require(h.hexdigest() == expected_sha, f"Input changed while archiving: {name}")
        # Re-read decompressed bytes, including the explicit-map launcher, before
        # presenting a downloadable archive. This is integrity, not execution.
        with zipfile.ZipFile(archive) as zipped:
            require(zipped.testzip() is None, "Archive CRC verification failed")
            for row in rows:
                with zipped.open(row["path"]) as stream:
                    h = hashlib.sha256()
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        h.update(block)
                require(h.hexdigest() == row["sha256"], f"Archived payload mismatch: {row['path']}")
        (output / "preview-manifest.json").write_bytes(generated["preview-manifest.json"])
        (output / (archive.name + ".sha256")).write_text(f"{digest_file(archive)}  {archive.name}\n", encoding="ascii")
        if not evidence:
            template = {"buildId": build_id, "sourceCommit": source["commit"], "payloadSha256": payload_sha,
                        "campaignSha256": campaign_sha, "map": PREVIEW_MAP, "previewQuestIds": list(PREVIEW_QUESTS),
                        "evidenceKind": "not-performed", "tester": "", "engineVersion": "", "testedUtc": "",
                        "checks": {key: False for key in SMOKE_CHECKS}, "captures": [],
                        "instructions": "Only after real extracted-package tests: set evidenceKind to actual-unreal-graphical, record tester/UTC/engine patch, observed checks and at least six distinct actual PNG/JPEG captures as relative path + sha256. Do not put this unfilled template in --smoke-report."}
            (output / "graphical-smoke.template.json").write_bytes(canonical(template))
    except BaseException:
        # Only artifacts in our newly-created directory belong to this operation.
        for artifact in output.iterdir():
            if artifact.is_file():
                artifact.unlink()
        output.rmdir()
        raise
    return {"archive": str(archive), "manifest": str(output / "preview-manifest.json"), "status": status,
            "payloadSha256": payload_sha, "publicReady": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--build-id", required=True)
    parser.add_argument("--campaign", type=Path, default=ROOT / "SourceArt/PathOfDawnUnreal/Gospel/Campaign.json")
    parser.add_argument("--source-commit")
    parser.add_argument("--smoke-report", type=Path)
    args = parser.parse_args(argv)
    try:
        result = prepare(args.build_root, args.output, args.build_id, args.campaign, args.source_commit, args.smoke_report)
    except (ReleaseError, OSError, zipfile.BadZipFile) as error:
        print(f"Release preparation refused: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("File integrity checked. This command did not build, launch, upload, or publicly deploy Unreal.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
