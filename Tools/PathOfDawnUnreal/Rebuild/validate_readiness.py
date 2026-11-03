"""Portable asset-policy preflight. PASS here is never a visual or Unreal pass.

A binding resolves an existing licensed Unreal object; this file does not invent
assets, accept legacy placeholders, or infer loaded assets from a supplied path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

SCHEMA_VERSION = 1
BENCHMARK_MAP = "/Game/WordJourney/Benchmark/L_BirthBenchmark"
BIRTH_ROLES = {
    "BirthEnvironment": {"classes": {"World"}},
    "Joseph": {"classes": {"SkeletalMesh"}, "age": "adult", "animations": ("idle", "walk", "turn")},
    "Mary": {"classes": {"SkeletalMesh"}, "age": "adult", "animations": ("idle",)},
    "Baby": {"classes": {"SkeletalMesh", "StaticMesh"}, "age": "infant"},
    "Shepherd": {"classes": {"SkeletalMesh"}, "age": "adult", "animations": ("idle", "walk", "turn")},
    "Manger": {"classes": {"StaticMesh"}},
}
TEMPLE_ROLES = {
    "TempleEnvironment": {"classes": {"World"}},
    "ChildJesus": {"classes": {"SkeletalMesh"}, "age": "child", "animations": ("idle",)},
    "Teacher": {"classes": {"SkeletalMesh"}, "age": "adult", "animations": ("idle",)},
}
OBJECT_PATH = re.compile(r"^/Game/(?:[A-Za-z0-9_]+/)*([A-Za-z0-9_]+)\.\1$")
HASH = re.compile(r"^[0-9a-fA-F]{64}$")
FORBIDDEN_ORIGINS = {"legacy_v8", "primitive", "mannequin", "adult_scaled_to_child"}
VIEWS = ("environment", "closeup", "gameplay")


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        value = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
        return value.hexdigest()


def local_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("file path must be nonempty repository-relative POSIX text")
    candidate = (root / relative).resolve()
    if Path(relative).is_absolute() or not candidate.is_relative_to(root.resolve()):
        raise ValueError("file path escapes the repository")
    if not candidate.is_file():
        raise ValueError("file is missing: " + relative)
    with candidate.open("rb") as stream:
        prefix = stream.read(160)
    if prefix.startswith(b"version https://git-lfs.github.com/spec/v1"):
        raise ValueError("file is a Git LFS pointer, not the asset: " + relative)
    return candidate


def _object_path(value, errors, label):
    if not isinstance(value, str) or not OBJECT_PATH.fullmatch(value):
        errors.append(label + ": existing /Game/Package.Asset object path required")
    elif value.startswith("/Game/PathOfDawn/") or value.startswith("/Game/WordJourney/Benchmark/"):
        errors.append(label + ": legacy placeholder/generated benchmark cannot be an input asset")


def _vector(value, positive=False):
    return isinstance(value, list) and len(value) == 3 and all(
        isinstance(n, (float, int)) and not isinstance(n, bool) and math.isfinite(n)
        and (not positive or n > 0) for n in value
    )


def validate_bindings(data: dict, root: Path) -> dict:
    errors, warnings = [], []
    if not isinstance(data, dict):
        return {"status": "BLOCKED", "readyForEditor": False, "errors": ["bindings root must be an object"], "warnings": [], "graphicsGate": "NOT_RUN"}
    if data.get("schemaVersion") != SCHEMA_VERSION:
        errors.append("unsupported bindings schemaVersion")
    stage = data.get("stage")
    if stage not in ("birth", "temple"):
        errors.append("stage must be birth or temple")
    if stage == "temple":
        try:
            evidence_path = local_file(root, data.get("birthGraphicsEvidence"))
            evidence = json.loads(evidence_path.read_text(encoding="utf-8-sig"))
            birth_hash = data.get("birthBindingsSha256", "")
            if not HASH.fullmatch(birth_hash):
                raise ValueError("reviewed birth bindings hash required")
            observed = validate_graphics_evidence(evidence, root, birth_hash)
            if observed["errors"]:
                raise ValueError("; ".join(observed["errors"]))
        except (TypeError, ValueError, OSError) as exc:
            errors.append("temple expansion requires the separately observed birth graphics gate: " + str(exc))
    roles = {**BIRTH_ROLES, **(TEMPLE_ROLES if stage == "temple" else {})}
    assets = data.get("assets", {})
    if not isinstance(assets, dict):
        assets = {}
        errors.append("assets must be an object")
    for role, requirements in roles.items():
        asset = assets.get(role)
        if not isinstance(asset, dict):
            errors.append(role + ": asset is not acquired/bound")
            continue
        _object_path(asset.get("objectPath"), errors, role)
        if asset.get("assetClass") not in requirements["classes"]:
            errors.append(role + ": expected " + "/".join(sorted(requirements["classes"])))
        if not asset.get("sourceUrl") or not str(asset.get("sourceUrl")).startswith("https://"):
            errors.append(role + ": HTTPS source URL required")
        if not asset.get("license"):
            errors.append(role + ": license identifier/terms required")
        if asset.get("origin") in FORBIDDEN_ORIGINS or asset.get("temporary") is not False:
            errors.append(role + ": temporary/basic/legacy geometry is not a final input")
        if asset.get("qualityApproved") is not True:
            errors.append(role + ": real source asset quality review is not recorded")
        review = asset.get("licenseReview", {})
        if not isinstance(review, dict):
            review = {}
        if review.get("permittedGameDistribution") is not True or not review.get("reviewer"):
            errors.append(role + ": game-distribution permission review required")
        try:
            evidence = local_file(root, review.get("evidencePath"))
            if not HASH.fullmatch(str(review.get("sha256", ""))) or digest(evidence) != review["sha256"].lower():
                errors.append(role + ": license evidence hash does not match")
        except (TypeError, ValueError, OSError) as exc:
            errors.append(role + ": " + str(exc))
        if "age" in requirements and asset.get("ageCategory") != requirements["age"]:
            errors.append(role + ": must use age-appropriate " + requirements["age"] + " asset")
        if asset.get("assetClass") == "SkeletalMesh":
            _object_path(asset.get("skeletonPath"), errors, role + ".skeletonPath")
        animations = asset.get("animations", {})
        if not isinstance(animations, dict):
            animations = {}
        for action in requirements.get("animations", ()):
            _object_path(animations.get(action), errors, role + ".animations." + action)
        if asset.get("assetClass") != "World":
            transform = asset.get("transform", {})
            if not isinstance(transform, dict) or not _vector(transform.get("locationCm")) or not _vector(transform.get("rotationDegrees")) or not _vector(transform.get("scale"), True):
                errors.append(role + ": measured location/rotation/scale placement required")
            elif "age" in requirements and any(n < .8 or n > 1.2 for n in transform["scale"]):
                errors.append(role + ": character scale must stay near authored proportions; no adult-to-child scaling")
    cameras = data.get("cameras", {})
    for view in VIEWS:
        camera = cameras.get(view) if isinstance(cameras, dict) else None
        if not isinstance(camera, dict) or not _vector(camera.get("locationCm")) or not _vector(camera.get("rotationDegrees")):
            errors.append(view + ": measured camera location/rotation required")
        elif not isinstance(camera.get("focalLengthMm"), (int, float)) or not 18 <= camera["focalLengthMm"] <= 100:
            errors.append(view + ": focal length must be 18–100 mm")
    warnings.append("Policy checks use declarations and hashes only. Unreal loading, shader compilation, animation and visual quality remain unverified.")
    return {"schemaVersion": SCHEMA_VERSION, "stage": stage, "status": "SOURCE_POLICY_READY" if not errors else "BLOCKED", "readyForEditor": not errors,
            "errors": errors, "warnings": warnings, "benchmarkMap": BENCHMARK_MAP, "graphicsGate": "NOT_RUN", "unrealLoadVerified": False}


def validate_environment(manifest: dict, directory: Path) -> dict:
    """Verify actual downloaded bytes before an independent editor import."""
    errors, files = [], []
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        return {"status": "BLOCKED", "errors": ["unsupported environment manifest"], "files": []}
    seen = set()
    for asset in manifest.get("assets", []):
        asset_id = asset.get("id")
        if not isinstance(asset_id, str) or not re.fullmatch(r"[a-z0-9_]+", asset_id) or asset_id in seen:
            errors.append("invalid/duplicate environment asset ID")
            continue
        seen.add(asset_id)
        if asset.get("license") != "CC0-1.0" or not str(asset.get("source_url", "")).startswith("https://"):
            errors.append(asset_id + ": reviewed CC0 source required")
        found = set()
        for row in asset.get("files", []):
            role = row.get("role")
            if role not in ("base_color", "normal", "roughness", "mesh") or role in found:
                errors.append(asset_id + ": invalid/duplicate file role")
                continue
            found.add(role)
            try:
                file = local_file(directory, row.get("path"))
                if not HASH.fullmatch(str(row.get("sha256", ""))) or digest(file) != row["sha256"].lower():
                    raise ValueError("SHA256 mismatch")
                if file.stat().st_size != row.get("bytes"):
                    raise ValueError("file size mismatch")
                if role != "mesh":
                    from PIL import Image
                    with Image.open(file) as image:
                        if image.format not in ("PNG", "JPEG"):
                            raise ValueError("unsupported source image format")
                        image.verify()
                    with Image.open(file) as image:
                        image.load()
                elif not file.read_bytes()[:23].startswith(b"Kaydara FBX Binary"):
                    raise ValueError("expected actual binary FBX source")
                if role == "normal" and (row.get("color_space") != "linear" or row.get("normal_convention") != "DirectX"):
                    raise ValueError("normal must declare linear DirectX convention")
                if role == "base_color" and row.get("color_space") != "sRGB":
                    raise ValueError("base color must declare sRGB")
                if role == "roughness" and row.get("color_space") != "linear":
                    raise ValueError("roughness must declare linear color space")
                files.append({"id": asset_id, **row, "absolutePath": str(file)})
            except (TypeError, ValueError, OSError, ImportError) as exc:
                errors.append(asset_id + "." + str(role) + ": " + str(exc))
        if not {"base_color", "normal", "roughness"}.issubset(found):
            errors.append(asset_id + ": full BaseColor/Normal/Roughness set required")
        if asset.get("kind") == "static_mesh" and "mesh" not in found:
            errors.append(asset_id + ": mesh file required")
    if not seen:
        errors.append("no downloaded environment assets")
    return {"status": "SOURCE_FILES_VERIFIED" if not errors else "BLOCKED", "errors": errors, "files": files, "unrealImportVerified": False}


def validate_graphics_evidence(data: dict, root: Path, bindings_sha256: str) -> dict:
    errors = []
    if data.get("bindingsSha256") != bindings_sha256:
        errors.append("visual review belongs to different bindings")
    if data.get("engine") != "Unreal Engine 5.8" or data.get("renderMode") != "real-time-rhi":
        errors.append("actual UE5.8 real-time rendered scene required; source renders and NullRHI do not count")
    if not data.get("reviewer") or not data.get("reviewedUtc"):
        errors.append("named visual reviewer and timestamp required")
    captures = data.get("captures", {})
    for view in VIEWS:
        capture = captures.get(view, {})
        try:
            path = local_file(root, capture.get("path"))
            if path.suffix.lower() not in (".png", ".jpg", ".jpeg") or path.stat().st_size < 1024:
                raise ValueError("actual nonempty game image required")
            if digest(path) != capture.get("sha256"):
                raise ValueError("capture hash mismatch")
            from PIL import Image
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                image.load()
        except (TypeError, ValueError, OSError, ImportError) as exc:
            errors.append(view + ": " + str(exc))
    for check in ("naturalCharacters", "periodClothing", "ageAppropriateBaby", "consistentMaterials", "animationAndFeet", "cameraMovement", "readableFaces", "noPlaceholders", "noDarknessOrBlurConcealment"):
        if data.get("checks", {}).get(check) is not True:
            errors.append("visual check not observed: " + check)
    return {"status": "REVIEW_EVIDENCE_COMPLETE" if not errors else "BLOCKED", "errors": errors,
            "note": "Evidence validation checks completeness and identity, not automatic image quality scoring."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--bindings", type=Path)
    parser.add_argument("--environment-only", action="store_true")
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args(argv)
    if not args.environment_only and args.bindings is None:
        parser.error("--bindings is required unless --environment-only is supplied")
    try:
        if args.environment_only:
            manifest_path = args.root / "SourceArt/PathOfDawnUnreal/Rebuild/Environment/manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            result = validate_environment(manifest, manifest_path.parent)
            result["manifestSha256"] = digest(manifest_path)
        else:
            data = json.loads(args.bindings.read_text(encoding="utf-8-sig"))
            result = validate_bindings(data, args.root)
    except (ValueError, OSError) as exc:
        result = {"status": "BLOCKED", "readyForEditor": False, "errors": [str(exc)], "graphicsGate": "NOT_RUN"}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not result["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
