"""Read-only asset inventory. No saves, migration, retargeting or rendered proof.

Run using Unreal's Python commandlet. The companion PowerShell tool supplies a
temporary descriptor enabling editor Python without editing the original file.
Reports stay on the Windows host; licensed sample assets are never exported.
"""
from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import re
import traceback

SCHEMA_VERSION = 1
INTERESTING = {"SkeletalMesh", "Skeleton", "AnimSequence", "AnimBlueprint",
               "IKRetargeter", "IKRigDefinition", "PoseSearchDatabase", "World"}
MOTION_WORDS = {"idle": ("idle", "stand"), "walk": ("walk",),
                "stop": ("stop",), "turn": ("turn", "pivot")}


def classify_motion(name):
    lower = name.lower()
    return [kind for kind, words in MOTION_WORDS.items() if any(word in lower for word in words)]


def locomotion_rank(row, kind):
    """Selection hints only. Exclude poses/interactions and prefer basic loops.

    The first native inventory exposed alphabetical AimOffset, takedown and
    crouch false positives. A name containing 'walk' never suffices by itself.
    Runtime skeleton/additive checks and visual review remain separate.
    """
    path, name = row["objectPath"].lower(), row["name"].lower()
    tokens = set(re.split(r"[^a-z0-9]+", path))
    rejected = {"aimoffset", "ao", "crouch", "interactions", "interaction", "takedowns",
                "takedown", "traversal", "ragdoll", "slide", "poses", "pose", "mocap",
                "additive", "avoidance", "lookatpoi", "jump", "run", "sprint"}
    if tokens & rejected:
        return None
    if kind not in classify_motion(name):
        return None
    if kind == "idle" and any(word in name for word in ("turn", "pivot", "walk", "stop", "break")):
        return None
    if kind == "walk" and any(word in name for word in ("stop", "turn", "start", "pivot", "slope", "reface", "spin")):
        return None
    score = 0
    if "relaxed" in tokens: score -= 10
    if kind == "idle" and name.endswith("idle_loop"): score -= 100
    if kind == "walk" and name.endswith("walk_loop_f"): score -= 100
    if kind == "walk" and "loop" in tokens: score -= 30
    if kind == "stop" and "_stop_f_" in name: score -= 100
    if kind == "turn" and "_stand_turn_090_" in name: score -= 100
    return score


def select_locomotion(rows, per_kind=3):
    result = {}
    sequences = [row for row in rows if row["class"] == "AnimSequence"]
    for kind in MOTION_WORDS:
        scored = [(rank, row["objectPath"], row) for row in sequences
                  if (rank := locomotion_rank(row, kind)) is not None]
        result[kind] = [row for _, _, row in sorted(scored)[:per_kind]]
    return result


def asset_row(asset_data):
    package = str(asset_data.package_name)
    name = str(asset_data.asset_name)
    if not package.startswith("/Game/"):
        return None
    return {"objectPath": package + "." + name, "name": name,
            "class": str(asset_data.asset_class_path.asset_name)}


def inspect_assets(unreal, max_meshes=6, max_animations=12, max_rows=5000):
    version = unreal.SystemLibrary.get_engine_version()
    if not re.match(r"^5\.8\.", version):
        raise RuntimeError("Use the sample's UE5.8 engine. No project upgrade is performed.")
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.search_all_assets(True)
    rows = [row for data in registry.get_assets_by_path("/Game", recursive=True)
            if (row := asset_row(data)) is not None]
    rows.sort(key=lambda row: row["objectPath"])
    if not rows:
        raise RuntimeError("No /Game assets were found. Check the selected sample project.")
    counts = dict(Counter(row["class"] for row in rows))
    interesting = [row for row in rows if row["class"] in INTERESTING]
    report = {"schemaVersion": SCHEMA_VERSION, "status": "INSPECTING",
              "scope": "Asset metadata and limited object loading only; NullRHI, no visual/play/retarget approval.",
              "classCounts": counts, "totalAssetCount": len(rows),
              "assets": interesting[:max_rows], "assetRowsTruncated": len(interesting) > max_rows,
              "loadedMeshes": [], "loadedAnimations": [], "warnings": [],
              "graphicsVerified": False, "retargetVerified": False,
              "sourceAssetsSaved": False, "licensedSourceFilesExported": False}

    def optional(obj, property_name):
        try:
            return obj.get_editor_property(property_name)
        except Exception as error:
            message = property_name + ": " + str(error)
            if len(report["warnings"]) < 50:
                report["warnings"].append(message[:600])
            return None

    def object_path(obj):
        return obj.get_path_name() if obj is not None else None

    # Loading is bounded. Registry inventory does not load every animation or BP.
    def mesh_priority(row):
        path = row["objectPath"].lower()
        return (0 if "uefn_mannequin/meshes" in path else 1 if "/metahumans/" in path and "/common/" not in path else 2,
                row["objectPath"])
    meshes = sorted([row for row in rows if row["class"] == "SkeletalMesh"], key=mesh_priority)[:max_meshes]
    for row in meshes:
        try:
            mesh = unreal.EditorAssetLibrary.load_asset(row["objectPath"])
            if not isinstance(mesh, unreal.SkeletalMesh):
                raise TypeError("Registry entry did not load as SkeletalMesh")
            materials = []
            for material in optional(mesh, "materials") or []:
                materials.append({"slot": str(optional(material, "material_slot_name")),
                                  "material": object_path(optional(material, "material_interface"))})
            report["loadedMeshes"].append({**row, "skeleton": object_path(optional(mesh, "skeleton")),
                                           "materials": materials, "visualStatus": "NOT_REVIEWED"})
        except Exception as error:
            report["warnings"].append(row["objectPath"] + ": " + str(error))

    # Give each requested motion category a chance instead of loading only the
    # first alphabetical batch (often hundreds of unrelated additive clips).
    candidates = []
    selected = set()
    per_kind = max(1, max_animations // len(MOTION_WORDS))
    for matching in select_locomotion(rows, per_kind).values():
        for row in matching:
            if row["objectPath"] not in selected:
                candidates.append(row)
                selected.add(row["objectPath"])
    for row in candidates[:max_animations]:
        try:
            animation = unreal.EditorAssetLibrary.load_asset(row["objectPath"])
            if not isinstance(animation, unreal.AnimSequence):
                raise TypeError("Registry entry did not load as AnimSequence")
            report["loadedAnimations"].append({**row, "skeleton": object_path(optional(animation, "skeleton")),
                                               "motionNameHints": classify_motion(row["name"]),
                                               "locomotionCandidateKinds": [kind for kind in MOTION_WORDS if locomotion_rank(row, kind) is not None],
                                               "playLengthSeconds": optional(animation, "sequence_length"),
                                               "motionVisuallyReviewed": False})
        except Exception as error:
            report["warnings"].append(row["objectPath"] + ": " + str(error))
    report["motionCandidates"] = {
        kind: [row["objectPath"] for row in report["loadedAnimations"] if kind in row["locomotionCandidateKinds"]]
        for kind in MOTION_WORDS}
    report["sameSkeletonPairs"] = [
        {"mesh": mesh["objectPath"], "animation": animation["objectPath"], "skeleton": mesh["skeleton"]}
        for mesh in report["loadedMeshes"] for animation in report["loadedAnimations"]
        if mesh["skeleton"] and mesh["skeleton"] == animation["skeleton"]]
    report["status"] = "SAMPLE_ASSETS_INSPECTED" if report["loadedMeshes"] and report["loadedAnimations"] else "PARTIAL_INVENTORY"
    report["note"] = "Names are selection hints. Shared skeleton does not prove retarget quality, natural appearance or period clothing."
    return report


def main(unreal):
    target = os.environ.get("WORD_JOURNEY_SAMPLE_REPORT")
    if not target:
        raise RuntimeError("Use InspectSample.ps1 to set the private report location.")
    destination = Path(target)
    try:
        report = inspect_assets(unreal)
    except Exception as error:
        report = {"schemaVersion": SCHEMA_VERSION, "status": "FAILED", "error": str(error),
                  "traceback": traceback.format_exc(), "graphicsVerified": False}
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)
    unreal.log("WORD_JOURNEY_SAMPLE_STATUS=" + report["status"])
    if report["status"] == "FAILED":
        unreal.log_error(report["error"])


if __name__ == "__main__":
    import unreal
    main(unreal)
