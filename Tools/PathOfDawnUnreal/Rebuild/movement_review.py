"""Editor-only setup/reload for the installed sample's MetaHuman movement review.

Uses an existing complete Character blueprint and its original motion system.
Only a new, owned GameMode blueprint is saved in WordJourneyDev. No source
sample assets, map/config files, active game project or service are changed.
The separate rendered launch is a development review, not the narrative demo.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inspect_sample import asset_row, select_locomotion

BASE = "/Game/WordJourneyDev/MovementReview"
GENERATOR = "word-journey-movement-review-v1"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_hash(project, package):
    if not re.fullmatch(re.escape(BASE) + r"/r_[0-9a-f]{16}/BP_MovementReview", package):
        raise ValueError("Refusing asset outside the generated review namespace")
    stem = project / "Content" / package[len("/Game/"):]
    records = []
    for suffix in (".uasset", ".uexp", ".ubulk", ".uptnl"):
        path = stem.with_suffix(suffix)
        if path.is_file(): records.append(suffix + ":" + file_hash(path))
    return hashlib.sha256("\n".join(records).encode()).hexdigest() if records else None


def settings(project):
    path = project / "Config/DefaultEngine.ini"
    values, active = {}, False
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line.startswith("["):
            active = line == "[/Script/EngineSettings.GameMapsSettings]"
        elif active and "=" in line and not line.startswith((";", "#", "+", "-", "!")):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"')
    game_map = values.get("GameDefaultMap", "").split(".")[0]
    if not re.fullmatch(r"/Game/[A-Za-z0-9_/]+", game_map):
        raise RuntimeError("The sample must specify its existing /Game map in DefaultEngine.ini.")
    return {"map": game_map, "mode": values.get("GlobalDefaultGameMode", "/Script/Engine.GameModeBase"),
            "configSha256": file_hash(path)}


def load_class(unreal, path):
    if path.startswith("/Script/"):
        return unreal.load_class(None, path)
    # Accept an actual generated class path, but load its Blueprint asset.
    if not re.fullmatch(r"/Game/[A-Za-z0-9_/]+\.[A-Za-z0-9_]+(?:_C)?", path):
        raise RuntimeError("Unsupported class reference in the sample's game settings: " + path)
    if path.endswith("_C"): path = path[:-2]
    return unreal.EditorAssetLibrary.load_blueprint_class(path)


def mesh_asset(component):
    getter = getattr(component, "get_skeletal_mesh_asset", None)
    if callable(getter): return getter()
    # UE versions expose the same native property under these reflected names.
    for name in ("skeletal_mesh_asset", "skeletal_mesh"):
        try: return component.get_editor_property(name)
        except Exception: pass
    raise RuntimeError("Cannot read the skeletal mesh component's native asset property.")


def inspect_character(unreal, actor):
    actors = [actor] + list(actor.get_all_child_actors(include_descendants=True))
    result = []
    for owner in actors:
        for component in owner.get_components_by_class(unreal.SkeletalMeshComponent):
            mesh = mesh_asset(component)
            if mesh is None: continue
            if not isinstance(mesh, unreal.SkeletalMesh): raise TypeError("Component asset is not SkeletalMesh")
            skeleton = mesh.get_editor_property("skeleton")
            anim_class = component.get_editor_property("anim_class")
            result.append({"component": component.get_name(), "mesh": mesh.get_path_name(),
                           "skeleton": skeleton.get_path_name() if skeleton else None,
                           "animationClass": anim_class.get_path_name() if anim_class else None})
    return result


def find_character(unreal, rows, actor_subsystem, report):
    candidates = sorted([r for r in rows if r["class"] == "Blueprint" and
                         any(word in r["name"].lower() for word in ("kellan", "metahuman"))],
                        key=lambda r: ("kellan" not in r["name"].lower(), r["objectPath"]))
    for row in candidates[:16]:
        record = {"objectPath": row["objectPath"]}
        report["characterCandidates"].append(record)
        cls = unreal.EditorAssetLibrary.load_blueprint_class(row["objectPath"])
        if cls is None:
            record["reason"] = "Blueprint class could not be loaded"
            continue
        cdo = unreal.get_default_object(cls)
        record["isCharacter"] = isinstance(cdo, unreal.Character)
        if not record["isCharacter"]: continue
        actor = actor_subsystem.spawn_actor_from_class(cls, unreal.Vector(0, 0, -50000))
        if actor is None: raise RuntimeError("Cannot instantiate the sample character for component checks.")
        try:
            record["components"] = inspect_character(unreal, actor)
        finally:
            if not actor_subsystem.destroy_actor(actor): raise RuntimeError("Cannot remove the temporary probe actor.")
        # A similarly named generic retarget actor is insufficient. Require the
        # fully assembled sample Kellan face/body somewhere in its hierarchy.
        paths = [part["mesh"].lower() for part in record["components"]]
        has_face = any("/kellan/" in p and "face" in p for p in paths)
        has_body = any("/kellan/" in p and "/body/" in p for p in paths)
        animated = any(part["animationClass"] for part in record["components"])
        if has_face and has_body and animated:
            report["selectedCharacter"] = record
            return cls, row["objectPath"]
        record["reason"] = "Complete Kellan face/body and an animation class were not assembled on this Character"
    raise RuntimeError("No existing complete Kellan Character blueprint passed component checks. Candidate details were saved; no mannequin or guessed binding was substituted.")


def check_motions(unreal, rows, report):
    selected = select_locomotion(rows, per_kind=1)
    if any(not selected[kind] for kind in selected):
        raise RuntimeError("A basic idle, forward walk, stop or standing turn candidate is missing.")
    skeletons = set()
    for kind, candidates in selected.items():
        row = candidates[0]
        animation = unreal.EditorAssetLibrary.load_asset(row["objectPath"])
        if not isinstance(animation, unreal.AnimSequence): raise TypeError(kind + ": cannot load AnimSequence")
        skeleton = animation.get_editor_property("skeleton")
        additive_value = animation.get_editor_property("additive_anim_type")
        additive = str(additive_value)
        length = float(animation.get_editor_property("sequence_length"))
        if skeleton is None or length <= 0 or additive_value != unreal.AdditiveAnimationType.AAT_NONE:
            raise RuntimeError(kind + ": missing skeleton, zero duration or additive animation is unsuitable.")
        skeletons.add(skeleton.get_path_name())
        report["curatedMotions"][kind] = {**row, "skeleton": skeleton.get_path_name(),
                                          "seconds": length, "additiveType": additive}
    if len(skeletons) != 1: raise RuntimeError("Selected basic motions do not share their source skeleton.")
    report["curatedSourceSkeleton"] = next(iter(skeletons))


def owned_mode(unreal, project, state, parent, pawn, inputs, report):
    source_hash = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    package = BASE + "/r_" + source_hash[:16] + "/BP_MovementReview"
    index_file = state / (source_hash + ".json")
    library = unreal.EditorAssetLibrary
    if library.does_asset_exist(package):
        if not index_file.is_file(): raise RuntimeError("Unindexed existing review asset preserved: " + package)
        index = json.loads(index_file.read_text(encoding="utf-8"))
        asset = library.load_asset(package)
        if (library.get_metadata_tag(asset, "WordJourneyGenerator") != GENERATOR or
                index.get("sourceSha256") != source_hash or index.get("packageSha256") != package_hash(project, package)):
            raise RuntimeError("Changed or unowned review asset preserved; choose a reviewed new revision: " + package)
        report["preserved"].append(package)
    else:
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", parent)
        asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset("BP_MovementReview", package.rsplit("/", 1)[0], unreal.Blueprint, factory)
        if asset is None: raise RuntimeError("GameMode Blueprint creation failed")
        unreal.BlueprintEditorLibrary.compile_blueprint(asset)
        cls = asset.generated_class()
        if cls is None: raise RuntimeError("Review GameMode did not compile")
        unreal.get_default_object(cls).set_editor_property("default_pawn_class", pawn)
        library.set_metadata_tag(asset, "WordJourneyGenerator", GENERATOR)
        library.set_metadata_tag(asset, "WordJourneySourceSHA256", source_hash)
        if not library.save_loaded_asset(asset, only_if_is_dirty=False): raise RuntimeError("Review GameMode save failed")
        actual = package_hash(project, package)
        if not actual: raise RuntimeError("Native saved GameMode package was not found")
        write_json(index_file, {"sourceSha256": source_hash, "packageSha256": actual})
        report["created"].append(package)
    mode = library.load_blueprint_class(package)
    if mode is None or unreal.get_default_object(mode).get_editor_property("default_pawn_class") != pawn:
        raise RuntimeError("Review GameMode pawn reference did not survive loading")
    return mode.get_path_name()


def run(unreal, project, state, report, verify=False):
    if not re.match(r"^5\.8\.", unreal.SystemLibrary.get_engine_version()):
        raise RuntimeError("Use the installed stable UE5.8 sample; no automatic engine upgrade.")
    game = settings(project)
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.search_all_assets(True)
    rows = [row for item in registry.get_assets_by_path("/Game", recursive=True) if (row := asset_row(item))]
    if not any(r["class"] == "World" and r["objectPath"].split(".")[0] == game["map"] for r in rows):
        raise RuntimeError("The configured sample map was not found in its actual asset registry.")
    check_motions(unreal, rows, report)
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not levels.load_level(game["map"]): raise RuntimeError("The existing sample map could not be loaded")
    parent = load_class(unreal, game["mode"])
    if parent is None or not isinstance(unreal.get_default_object(parent), unreal.GameModeBase):
        raise RuntimeError("The sample's original GameMode could not be loaded")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    pawn, pawn_path = find_character(unreal, rows, actors, report)
    inputs = {"config": game["configSha256"], "pawn": pawn_path, "parentMode": parent.get_path_name(),
              "generatorSha256": file_hash(Path(__file__)), "selectorSha256": file_hash(Path(__file__).with_name("inspect_sample.py"))}
    # Both processes compute the same native inputs and package checksum. Verify
    # cannot generate or save a missing asset, even if preparation was partial.
    source_hash = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    package = BASE + "/r_" + source_hash[:16] + "/BP_MovementReview"
    if verify and not unreal.EditorAssetLibrary.does_asset_exist(package):
        raise RuntimeError("Fresh-process reload cannot find the prepared GameMode")
    mode = owned_mode(unreal, project, state, parent, pawn, inputs, report)
    report["launch"] = {"map": game["map"], "gameModeClass": mode, "sourcePawn": pawn_path}
    report["sourceConfigSha256"] = game["configSha256"]
    report["status"] = "MOTION_REVIEW_ASSETS_RELOADED" if verify else "MOTION_REVIEW_ASSETS_SAVED"
    report["newAssetsSaved"] = bool(report["created"])


def main(unreal):
    report = {"schemaVersion": 1, "status": "PREPARING", "created": [], "preserved": [],
              "characterCandidates": [], "curatedMotions": {}, "graphicsVerified": False,
              "retargetMotionVisuallyVerified": False, "narrativeDemoComplete": False,
              "sourceSampleAssetsModified": False, "newAssetsSaved": False,
              "scope": "Existing MetaHuman Character and motion system; one owned review GameMode, not the period narrative demo."}
    output = Path(os.environ["WORD_JOURNEY_REVIEW_REPORT"])
    try:
        run(unreal, Path(os.environ["WORD_JOURNEY_REVIEW_PROJECT"]), Path(os.environ["WORD_JOURNEY_REVIEW_STATE"]), report,
            verify=os.environ["WORD_JOURNEY_REVIEW_PHASE"] == "verify")
    except Exception as error:
        report.update(status="FAILED", error=str(error), traceback=traceback.format_exc())
    write_json(output, report)
    unreal.log("WORD_JOURNEY_MOVEMENT_STATUS=" + report["status"])
    if report["status"] == "FAILED": unreal.log_error(report["error"])


if __name__ == "__main__":
    import unreal
    main(unreal)
