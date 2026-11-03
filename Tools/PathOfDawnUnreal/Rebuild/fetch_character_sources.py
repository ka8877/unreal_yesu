#!/usr/bin/env python3
"""Acquire CC0 garment/foundation sources, never mark a finished game character.

The 192 MB community archive is NOT downloaded wholesale. Validated HTTP ranges
retrieve only the CC0 robe members, using ZIP directory sizes and CRC32. Existing
local files are preserved. Repeated invocation verifies the frozen SHA256 receipt.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import urllib.request
import uuid
import zipfile
import zlib

ARCHIVE = "https://files.makehumancommunity.org/asset_packs/suits02/suits02_cc0.zip"
ARCHIVE_SIZE = 192511027
MAKEHUMAN_COMMIT = "a8bc2d54ff0ac92e78ff71431b1023eda42bf482"
CAP = 100_000_000
ROBE_FILES = ("Monks_Robe.obj", "monks_robe_brown.mhmat", "donitz_monk_robe.mhclo",
              "robe_brown__diffuse.png", "donitz_monk_robe.thumb", "robe__normal_gl.png")
FOUNDATION_FILES = ("LICENSE.ASSETS.md", "LICENSE.md", "makehuman/data/3dobjs/base.obj",
                    "makehuman/data/rigs/default.mhskel", "makehuman/data/rigs/default_weights.mhw")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def request(url, start=None, end=None):
    headers = {"User-Agent": "PathOfDawnUnreal/1.0"}
    if start is not None:
        headers["Range"] = f"bytes={start}-{end}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=90) as response:
        if start is not None:
            expected = f"bytes {start}-{end}/{ARCHIVE_SIZE}"
            if response.status != 206 or response.headers.get("Content-Range") != expected:
                raise ValueError("Provider did not honor the exact byte range; full archive download refused")
            maximum = end - start + 1
        else:
            maximum = 5_000_000
        data = response.read(maximum + 1)
        if len(data) > maximum or (start is not None and len(data) != maximum):
            raise ValueError("Provider response length differs from the allowed byte range")
    return data


def store(root, relative, data):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"Existing local source differs and was preserved: {path}")
    else:
        temporary = path.with_name(path.name + ".download-" + uuid.uuid4().hex)
        try:
            with temporary.open("xb") as output:
                output.write(data)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    return {"path": relative, "bytes": len(data), "sha256": sha(data)}


def verify(root):
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("game_ready") is not False:
        raise ValueError("Unexpected character-source manifest or unsupported game-ready claim")
    if len(manifest["files"]) != len(ROBE_FILES) + len(FOUNDATION_FILES):
        raise ValueError("Character-source receipt is incomplete")
    expected = {"DonitzRobe/" + name for name in ROBE_FILES} | {
        "MakeHumanFoundation/" + name.removeprefix("makehuman/data/") for name in FOUNDATION_FILES}
    if {entry["path"] for entry in manifest["files"]} != expected:
        raise ValueError("Character-source receipt has missing, duplicate or unexpected paths")
    for entry in manifest["files"]:
        relative = entry["path"]
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()) or "\\" in relative:
            raise ValueError("Unsafe source path")
        data = path.read_bytes()
        expected_license = "License notice" if relative == "MakeHumanFoundation/LICENSE.md" else "CC0-1.0"
        if entry.get("license") != expected_license:
            raise ValueError("Unexpected source license; explicit review required")
        if len(data) != entry["bytes"] or sha(data) != entry["sha256"]:
            raise ValueError(f"Source integrity failed; local file preserved: {relative}")
        if "zip_crc32" in entry and f"{zlib.crc32(data):08x}" != entry["zip_crc32"]:
            raise ValueError("Community ZIP CRC32 mismatch")
        if relative.endswith(".png"):
            from PIL import Image
            with Image.open(io.BytesIO(data)) as image:
                image.load()
                if image.size != (4096, 4096):
                    raise ValueError("Expected original 4K garment texture")
        if relative.endswith(".mhclo") and b"# license: CC0" not in data:
            raise ValueError("Garment fitting source no longer declares CC0")
        if relative.endswith(".mhmat") and b"license CC0" not in data:
            raise ValueError("Garment material source no longer declares CC0")
    total = sum(entry["bytes"] for entry in manifest["files"])
    if total > CAP:
        raise ValueError("Character sources exceed the 100 MB cap")
    return {"status": "passed", "verified_files": len(manifest["files"]), "bytes": total,
            "game_ready": False,
            "scope": "CC0 source acquisition, ZIP CRC32, SHA256 and 4K image decode only; no assembled adult, Unreal rig, motion or graphical quality pass"}


def acquire(root):
    if (root / "manifest.json").exists():
        return verify(root)
    tail = request(ARCHIVE, ARCHIVE_SIZE - 65536, ARCHIVE_SIZE - 1)
    position = tail.rfind(b"PK\x05\x06")
    if position < 0:
        raise ValueError("ZIP end record is missing")
    end_record = list(struct.unpack("<4s4H2LH", tail[position:position + 22]))
    if end_record[1:3] != [0, 0] or end_record[3] != end_record[4] or end_record[7] != 0:
        raise ValueError("Unexpected multipart ZIP or archive comment")
    directory_size, directory_offset = end_record[5:7]
    if directory_size > 1_000_000 or directory_offset + directory_size > ARCHIVE_SIZE - 22:
        raise ValueError("Invalid community archive directory")
    central = request(ARCHIVE, directory_offset, directory_offset + directory_size - 1)
    end_record[6] = 0
    directory = zipfile.ZipFile(io.BytesIO(central + struct.pack("<4s4H2LH", *end_record)))
    records = []
    transferred = len(tail) + len(central)
    for filename in ROBE_FILES:
        member = "clothes/donitz_monk_robe/" + filename
        info = directory.getinfo(member)
        if info.file_size > 30_000_000 or info.compress_size > 30_000_000 or info.flag_bits & 1:
            raise ValueError("Unsupported oversized or encrypted garment member")
        fixed_header = request(ARCHIVE, info.header_offset, info.header_offset + 29)
        header = struct.unpack("<4s5H3L2H", fixed_header)
        if header[0] != b"PK\x03\x04" or header[3] != info.compress_type:
            raise ValueError("ZIP local header differs from central directory")
        name_length, extra_length = header[-2:]
        data_start = info.header_offset + 30 + name_length + extra_length
        payload = request(ARCHIVE, data_start, data_start + info.compress_size - 1)
        transferred += len(fixed_header) + len(payload)
        if info.compress_type == zipfile.ZIP_DEFLATED:
            decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
            data = decompressor.decompress(payload, info.file_size + 1)
            if not decompressor.eof or decompressor.unconsumed_tail:
                raise ValueError("Garment member decompression exceeded declared bounds")
        elif info.compress_type == zipfile.ZIP_STORED:
            data = payload
        else:
            raise ValueError("Unsupported garment compression")
        if len(data) != info.file_size or zlib.crc32(data) != info.CRC:
            raise ValueError("Downloaded garment member failed ZIP size/CRC32 checks")
        record = store(root, "DonitzRobe/" + filename, data)
        record.update(source_url=ARCHIVE, archive_member=member, zip_crc32=f"{info.CRC:08x}",
                      license="CC0-1.0", author="Donitz")
        if filename.endswith("diffuse.png"):
            record.update(role="base_color", color_space="sRGB")
        elif filename.endswith("normal_gl.png"):
            record.update(role="normal", color_space="linear", normal_convention="OpenGL")
        records.append(record)
    for filename in FOUNDATION_FILES:
        url = f"https://raw.githubusercontent.com/makehumancommunity/makehuman/{MAKEHUMAN_COMMIT}/{filename}"
        data = request(url)
        transferred += len(data)
        if transferred > CAP:
            raise ValueError("Character-source network transfer exceeds 100 MB cap")
        relative = "MakeHumanFoundation/" + filename.removeprefix("makehuman/data/")
        record = store(root, relative, data)
        record.update(source_url=url, license="CC0-1.0" if filename != "LICENSE.md" else "License notice",
                      author="MakeHuman Team")
        records.append(record)
    manifest = {"schema_version": 1, "game_ready": False,
                "status": "CC0_PRODUCTION_SOURCES_ONLY_NOT_FINAL_CHARACTERS",
                "makehuman_commit": MAKEHUMAN_COMMIT, "network_bytes": transferred,
                "garment_license_reference": "https://static.makehumancommunity.org/assets/assetpacks/suits02.html",
                "garment_note": "Author describes this as a classic MEDIEVAL monk's robe. CC0 production source for adaptation only; not first-century clothing, not approved final costume. Design changes, fit and historical/art review required.",
                "foundation_note": "Base topology plus rig definition/weights only. No skin textures, final hair, animation, assembled skeletal mesh, baby or child supplied. Never use the unclothed foundation as a final scene actor.",
                "unreal_import_verified": False, "files": records}
    store(root, "manifest.json", (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode())
    return verify(root)


def self_test(root):
    import tempfile
    import shutil
    checks = []
    with tempfile.TemporaryDirectory(prefix="dawn-character-sources-") as directory:
        target = Path(directory) / "sources"
        shutil.copytree(root, target)
        receipt = target / "manifest.json"
        original = receipt.read_bytes()
        manifest = json.loads(original)
        first = target / manifest["files"][0]["path"]
        body = first.read_bytes()
        verify(target)
        checks.append("real character-source clone accepted")

        def reject(label):
            try:
                verify(target)
            except (OSError, ValueError):
                checks.append(label)
            else:
                raise AssertionError(label + " was accepted")

        first.write_bytes(body + b"altered")
        reject("source mutation rejected")
        first.write_bytes(body)
        manifest["game_ready"] = True
        receipt.write_text(json.dumps(manifest))
        reject("unsupported final-character claim rejected")
        manifest = json.loads(original)
        manifest["files"][0]["path"] = "../outside.obj"
        receipt.write_text(json.dumps(manifest))
        reject("source path escape rejected")
        manifest = json.loads(original)
        manifest["files"].pop()
        receipt.write_text(json.dumps(manifest))
        reject("incomplete source set rejected")
    return {"status": "passed", "checks": checks, "game_ready": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3] / "SourceArt/PathOfDawnUnreal/Rebuild/CharacterSources")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        report = self_test(args.root) if args.self_test else (verify(args.root) if args.verify_only else acquire(args.root))
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, ImportError, zipfile.BadZipFile, AssertionError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
