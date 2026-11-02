#!/usr/bin/env python3
"""Acquire a small, licensed Poly Haven source set; never produce Unreal packages.

First run downloads original provider files and provenance. Repeated runs verify
the frozen SHA256 receipt offline. A changed local file is preserved and rejected.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import urllib.parse
import urllib.request
import uuid

ASSETS = (
    ("stone_wall_05", "pbr_material", "석조 벽면 후보"),
    ("brown_mud_dry", "pbr_material", "작은 마당의 흙바닥 후보"),
    ("rough_wood", "pbr_material", "오래된 목재 표면 후보"),
    ("ceramic_pot", "static_mesh", "도기 소품 후보; 시대 고증 확정 아님"),
)
CHANNELS = (("Diffuse", "jpg", "base_color", "sRGB"),
            ("nor_dx", "png", "normal", "linear"),
            ("Rough", "jpg", "roughness", "linear"))
MAX_FILE = 30_000_000
MAX_TOTAL = 80_000_000
ALLOWED_HOSTS = {"api.polyhaven.com", "dl.polyhaven.org", "polyhaven.com"}
LICENSE_URL = "https://polyhaven.com/license"


def digest(data: bytes, algorithm="sha256") -> str:
    return hashlib.new(algorithm, data).hexdigest()


def local_path(root: Path, relative: str) -> Path:
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or "\\" in relative or ":" in relative:
        raise ValueError(f"Unsafe source path: {relative}")
    result = root.joinpath(*path.parts).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError(f"Source path escaped root: {relative}")
    return result


def download(url: str, maximum=MAX_FILE) -> bytes:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"Unapproved download URL: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "PathOfDawnUnreal/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        if urllib.parse.urlsplit(response.geturl()).hostname not in ALLOWED_HOSTS:
            raise ValueError("Download redirected outside provider hosts")
        data = response.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError(f"Download exceeds size limit: {url}")
    return data


def retain_or_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"Existing file differs; preserved without overwrite: {path}")
        return
    temporary = path.with_name(path.name + ".download-" + uuid.uuid4().hex)
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def check_image(data: bytes, extension: str) -> dict:
    # Pillow is already an art-tool dependency; this is a real decode, not an
    # extension-only check. Unreal import/shading remains a separate operation.
    from PIL import Image
    import io
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        if image.size != (2048, 2048):
            raise ValueError(f"Expected original 2K source, got {image.size}")
        if image.format != {"jpg": "JPEG", "png": "PNG"}[extension]:
            raise ValueError("Provider file format differs from its extension")
        return {"width": image.width, "height": image.height, "format": image.format}


def verify(root: Path) -> dict:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported source manifest version")
    ids = [asset["id"] for asset in manifest["assets"]]
    if len(ids) != len(set(ids)) or set(ids) != {item[0] for item in ASSETS}:
        raise ValueError("Source asset IDs are missing, duplicated or unexpected")
    for asset in manifest["assets"]:
        expected = {"base_color", "normal", "roughness"}
        if asset["kind"] == "static_mesh":
            expected.add("mesh")
        roles = [record["role"] for record in asset["files"]]
        if len(roles) != len(set(roles)) or set(roles) != expected:
            raise ValueError(f"Incomplete source roles: {asset['id']}")
        if asset.get("license") != "CC0-1.0":
            raise ValueError(f"Unreviewed source license: {asset['id']}")
    total = 0
    records = manifest["provenance_files"] + [r for a in manifest["assets"] for r in a["files"]]
    for record in records:
        data = local_path(root, record["path"]).read_bytes()
        if len(data) != record["bytes"] or digest(data) != record["sha256"]:
            raise ValueError(f"Source receipt mismatch; file preserved: {record['path']}")
        if "md5" in record and digest(data, "md5") != record["md5"]:
            raise ValueError(f"Provider checksum mismatch: {record['path']}")
        if record.get("role") in {"base_color", "normal", "roughness"}:
            check_image(data, Path(record["path"]).suffix.lstrip("."))
        total += len(data)
    if total > MAX_TOTAL:
        raise ValueError("Source set exceeds 80 MB cap")
    return {"status": "passed", "asset_sets": len(manifest["assets"]),
            "verified_files": len(records), "bytes": total,
            "scope": "Provider checksums, frozen SHA256 and actual texture decoding only; not Unreal import or game graphics."}


def acquire(root: Path) -> dict:
    if (root / "manifest.json").exists():
        return verify(root)
    provenance = []
    assets = []
    total = 0

    def keep(relative: str, data: bytes, url: str) -> dict:
        nonlocal total
        total += len(data)
        if len(data) > MAX_FILE or total > MAX_TOTAL:
            raise ValueError("Acquisition exceeds per-file/total source cap")
        retain_or_write(local_path(root, relative), data)
        return {"path": relative, "source_url": url, "bytes": len(data), "sha256": digest(data)}

    license_data = download(LICENSE_URL)
    if b"CC0" not in license_data:
        raise ValueError("Provider license page no longer identifies CC0; review before acquisition")
    # The asset dedication is CC0; the surrounding website is not. Record the
    # reviewed response hash rather than redistribute the whole HTML document.
    license_review = {"source_url": LICENSE_URL, "response_sha256": digest(license_data),
                      "asset_license": "CC0-1.0",
                      "review": "Provider explicitly permits asset use, modification and redistribution, including commercial products. Website content itself is excluded; original HTML is not bundled.",
                      "canonical_dedication": "https://creativecommons.org/publicdomain/zero/1.0/"}
    provenance.append(keep("provenance/license-review.json", (json.dumps(license_review, indent=2) + "\n").encode("utf-8"), LICENSE_URL))
    for asset_id, kind, usage in ASSETS:
        files_url = f"https://api.polyhaven.com/files/{asset_id}"
        info_url = f"https://api.polyhaven.com/info/{asset_id}"
        raw_files, raw_info = download(files_url), download(info_url)
        files, info = json.loads(raw_files), json.loads(raw_info)
        metadata_path = f"provenance/{asset_id}.files.json"
        provenance.append(keep(metadata_path, raw_files, files_url))
        provenance.append(keep(f"provenance/{asset_id}.info.json", raw_info, info_url))
        asset = {"id": asset_id, "kind": kind, "name": info["name"], "usage": usage,
                 "source_url": f"https://polyhaven.com/a/{asset_id}",
                 "license": "CC0-1.0", "license_url": LICENSE_URL,
                 "license_text_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                 "authors": info.get("authors", {}), "source_api": files_url,
                 "metadata_path": metadata_path, "files": [],
                 "status": "downloaded_source_verified", "unreal_import_verified": False,
                 "scene_applied": False, "historical_accuracy_verified": False}
        selections = [(files[key]["2k"][extension], role, space, extension)
                      for key, extension, role, space in CHANNELS]
        if kind == "static_mesh":
            selections.insert(0, (files["fbx"]["2k"]["fbx"], "mesh", None, "fbx"))
        for provider, role, space, extension in selections:
            if provider["size"] > MAX_FILE:
                raise ValueError(f"Provider source is too large: {provider['url']}")
            data = download(provider["url"])
            if len(data) != provider["size"] or digest(data, "md5") != provider["md5"]:
                raise ValueError(f"Provider size/MD5 mismatch: {provider['url']}")
            filename = Path(urllib.parse.urlsplit(provider["url"]).path).name
            if not filename.startswith(asset_id + "_"):
                raise ValueError("Unexpected provider filename")
            record = keep(f"{asset_id}/{filename}", data, provider["url"])
            record.update({"role": role, "md5": provider["md5"]})
            if space:
                record.update({"color_space": space, "image": check_image(data, extension)})
            if role == "normal":
                record["normal_convention"] = "DirectX"
            if role == "mesh":
                if not data.startswith(b"Kaydara FBX Binary"):
                    raise ValueError("Downloaded mesh is not a binary FBX")
                record["material_assignment"] = "Bind downloaded PBR maps explicitly; provider FBX may reference omitted EXR siblings."
            asset["files"].append(record)
        assets.append(asset)
    manifest = {"schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
                "source_scope": "Original Poly Haven CC0 files, acquired without account or payment",
                "quality_gate": "BLOCKED: no Unreal import/render verification; required people, animation and complete architecture are not supplied by these assets.",
                "provenance_files": provenance, "assets": assets}
    retain_or_write(root / "manifest.json", (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return verify(root)


def self_test(root: Path) -> dict:
    """Reject altered bytes, missing roles/files and unsafe paths using real sources."""
    import shutil
    import tempfile
    checks = []
    with tempfile.TemporaryDirectory(prefix="dawn-source-acquisition-") as directory:
        target = Path(directory) / "sources"
        shutil.copytree(root, target)
        manifest_path = target / "manifest.json"
        original = manifest_path.read_bytes()
        manifest = json.loads(original)
        first = target / manifest["assets"][0]["files"][0]["path"]
        original_file = first.read_bytes()
        verify(target)
        checks.append("real source clone accepted")

        def must_reject(label):
            try:
                verify(target)
            except (ValueError, OSError):
                checks.append(label)
            else:
                raise AssertionError(f"Unsafe mutation was accepted: {label}")

        first.write_bytes(original_file[:-1] + bytes([original_file[-1] ^ 1]))
        must_reject("modified source bytes rejected")
        first.write_bytes(original_file)
        first.unlink()
        must_reject("missing source rejected")
        first.write_bytes(original_file)
        manifest["assets"][0]["files"].pop()
        manifest_path.write_text(json.dumps(manifest))
        must_reject("missing material channel rejected")
        manifest = json.loads(original)
        manifest["assets"][0]["files"][0]["path"] = "../../outside.jpg"
        manifest_path.write_text(json.dumps(manifest))
        must_reject("source path traversal rejected")
        manifest = json.loads(original)
        manifest["assets"][0]["license"] = "unknown"
        manifest_path.write_text(json.dumps(manifest))
        must_reject("unreviewed source license rejected")
        manifest = json.loads(original)
        manifest["assets"].pop()
        manifest_path.write_text(json.dumps(manifest))
        must_reject("missing asset set rejected")
    return {"status": "passed", "checks": checks, "scope": "Real source integrity and manifest mutation tests; no Unreal execution"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3] / "SourceArt/PathOfDawnUnreal/Rebuild/Environment")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        report = self_test(args.root) if args.self_test else (verify(args.root) if args.verify_only else acquire(args.root))
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, ImportError, AssertionError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
