"""UE Editor-only source import and guarded birth benchmark preparation.

Does not change default maps, package settings, running services or legacy assets.
Unreal invocation: -ExecutePythonScript=<this file> -JourneyBindings="...json"
-JourneyReport="...json" [-JourneyImportSources] [-JourneySourcesOnly]

Process-scoped WORD_JOURNEY_BINDINGS / WORD_JOURNEY_REPORT take precedence
over CLI paths; -Journey* switches remain a fallback. No machine setting changes.
Use --bindings/--report in sys.argv when an editor Python runner supplies them.
Missing people/architecture blocks world creation, even if source import succeeds.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_readiness import BENCHMARK_MAP, BIRTH_ROLES, VIEWS, digest

ROOT = HERE.parents[2]
PROJECT = ROOT / "Games/PathOfDawnUnreal"
SOURCE_MANIFEST = ROOT / "SourceArt/PathOfDawnUnreal/Rebuild/Environment/manifest.json"
BASE = "/Game/WordJourney/Benchmark"
INDEX_PATH = PROJECT / "Content/WordJourney/Benchmark/source-index.json"


def package_hash(package):
    if not package.startswith(BASE + "/") or "." in package.rsplit("/", 1)[-1]:
        raise ValueError("outside generated benchmark namespace")
    stem = PROJECT / "Content" / package[len("/Game/"):]
    parts = []
    for suffix in (".uasset", ".umap", ".uexp", ".ubulk", ".uptnl"):
        path = stem.with_suffix(suffix)
        if path.exists():
            parts.append(suffix + ":" + digest(path))
    return hashlib.sha256("\n".join(parts).encode()).hexdigest() if parts else None


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def host_validation(bindings=None):
    """Use the authoring Python for Pillow; UE's embedded Python stays stdlib-only.

    This does not install packages in the engine or infer an Unreal/visual pass.
    Full pixel/file and capture checks still execute in validate_readiness.py.
    """
    python = os.environ.get("WORD_JOURNEY_HOST_PYTHON", "")
    if not python or not Path(python).is_file():
        raise RuntimeError("Authoring Python is not configured. Run PrepareRebuild.ps1, which sets WORD_JOURNEY_HOST_PYTHON for this Editor process.")
    environment = dict(os.environ)
    # Embedded Python settings must not redirect the separate author's Python
    # into the engine's stdlib/site-packages. Only this child is affected.
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    environment["PYTHONIOENCODING"] = "utf-8"
    with tempfile.TemporaryDirectory(prefix="word-journey-validation-") as directory:
        report_path = Path(directory) / "validation.json"
        arguments = [python, "-X", "utf8", str(HERE / "validate_readiness.py"),
                     "--root", str(ROOT), "--report", str(report_path)]
        arguments += ["--environment-only"] if bindings is None else ["--bindings", str(bindings)]
        completed = subprocess.run(arguments, stdin=subprocess.DEVNULL, capture_output=True,
                                   text=True, encoding="utf-8", env=environment, timeout=60,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        if completed.returncode not in (0, 2) or not report_path.is_file():
            raise RuntimeError("Authoring validation failed: " + (completed.stderr or completed.stdout)[-3000:])
        result = json.loads(report_path.read_text(encoding="utf-8"))
        if not isinstance(result.get("errors"), list) or (not result["errors"]) != (completed.returncode == 0):
            raise RuntimeError("Authoring validator result/exit code disagree.")
        return result


class EditorWork:
    def __init__(self, unreal, report):
        self.u = unreal
        self.lib = unreal.EditorAssetLibrary
        self.tools = unreal.AssetToolsHelpers.get_asset_tools()
        self.report = report
        self.index = {"schemaVersion": 1, "assets": {}}
        if INDEX_PATH.exists():
            self.index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
            if self.index.get("schemaVersion") != 1 or not isinstance(self.index.get("assets"), dict):
                raise RuntimeError("invalid generated source index; preserve and recover the baseline")

    def need(self, object_path, classes=None):
        asset = self.lib.load_asset(object_path)
        if not asset:
            raise RuntimeError("Unreal cannot load required asset: " + object_path)
        if classes and not any(isinstance(asset, cls) for cls in classes):
            raise RuntimeError("wrong Unreal class at " + object_path + ": " + asset.get_class().get_name())
        return asset

    def prepare(self, package, source_sha):
        if not self.lib.does_asset_exist(package):
            return None
        asset = self.need(package)
        entry = self.index["assets"].get(package)
        if not entry or self.lib.get_metadata_tag(asset, "WordJourneyGenerator") != "benchmark-v1":
            raise RuntimeError("unowned existing asset preserved; explicit reviewed new name required: " + package)
        if entry["sourceSha256"] != source_sha:
            raise RuntimeError("input changed; preserve existing asset and choose reviewed new revision: " + package)
        if entry["packageSha256"] != package_hash(package):
            self.report["warnings"].append("Preserved manually edited package: " + package)
        self.report["preserved"].append(package)
        return asset

    def save(self, asset, package, source_sha):
        self.lib.set_metadata_tag(asset, "WordJourneyGenerator", "benchmark-v1")
        self.lib.set_metadata_tag(asset, "WordJourneySourceSHA256", source_sha)
        if not self.lib.save_loaded_asset(asset, only_if_is_dirty=False):
            raise RuntimeError("Unreal save failed: " + package)
        actual = package_hash(package)
        if not actual:
            raise RuntimeError("saved Unreal package is missing on disk: " + package)
        self.index["assets"][package] = {"sourceSha256": source_sha, "packageSha256": actual}
        _write(INDEX_PATH, self.index)
        self.report["created"].append(package)
        return asset

    def import_environment(self):
        manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
        manifest_sha = digest(SOURCE_MANIFEST)
        verified = host_validation()
        self.report["sourceValidation"] = {k: v for k, v in verified.items() if k != "files"}
        if verified["errors"]:
            raise RuntimeError("environment source verification failed: " + "; ".join(verified["errors"]))
        if verified.get("manifestSha256") != manifest_sha or digest(SOURCE_MANIFEST) != manifest_sha:
            raise RuntimeError("Environment manifest changed during validation; no source import was started.")
        for source in manifest["assets"]:
            imported = {}
            for row in source["files"]:
                role = row["role"]
                name = ("SM_" if role == "mesh" else "T_") + source["id"] + "_" + role
                folder = BASE + "/EnvironmentSources/" + source["id"]
                package = folder + "/" + name
                asset = self.prepare(package, row["sha256"])
                if asset is None:
                    task = self.u.AssetImportTask()
                    for prop, value in {"filename": str((SOURCE_MANIFEST.parent / row["path"]).resolve()), "destination_path": folder,
                                        "destination_name": name, "automated": True, "save": False,
                                        "replace_existing": False}.items():
                        task.set_editor_property(prop, value)
                    if role == "mesh":
                        options = self.u.FbxImportUI()
                        for prop, value in {"import_mesh": True, "import_as_skeletal": False, "import_animations": False,
                                            "mesh_type_to_import": self.u.FBXImportType.FBXIT_STATIC_MESH,
                                            "automated_import_should_detect_type": False,
                                            "import_materials": False, "import_textures": False}.items():
                            options.set_editor_property(prop, value)
                        options.get_editor_property("static_mesh_import_data").set_editor_property("combine_meshes", True)
                        options.get_editor_property("static_mesh_import_data").set_editor_property("auto_generate_collision", True)
                        task.set_editor_property("options", options)
                    self.tools.import_asset_tasks([task])
                    if not task.get_editor_property("imported_object_paths"):
                        raise RuntimeError("import produced no assets: " + row["path"])
                    asset = self.need(package, (self.u.StaticMesh,) if role == "mesh" else (self.u.Texture2D,))
                    if role != "mesh":
                        asset.set_editor_property("srgb", row["color_space"] == "sRGB")
                        if role == "normal":
                            asset.set_editor_property("compression_settings", self.u.TextureCompressionSettings.TC_NORMALMAP)
                    # Mesh is saved after replacing FBX's external EXR references
                    # with the imported PBR material below.
                    if role != "mesh":
                        self.save(asset, package, row["sha256"])
                imported[role] = (asset, package, row["sha256"])
            material_package = BASE + "/EnvironmentSources/" + source["id"] + "/M_" + source["id"]
            material_sha = hashlib.sha256(json.dumps(source["files"], sort_keys=True).encode()).hexdigest()
            material = self.prepare(material_package, material_sha)
            if material is None:
                material = self.tools.create_asset("M_" + source["id"], str(Path(material_package).parent).replace("\\", "/"), self.u.Material, self.u.MaterialFactoryNew())
                if material is None:
                    raise RuntimeError("material creation failed: " + material_package)
                edit = self.u.MaterialEditingLibrary
                for index, (role, prop) in enumerate((("base_color", self.u.MaterialProperty.MP_BASE_COLOR), ("normal", self.u.MaterialProperty.MP_NORMAL), ("roughness", self.u.MaterialProperty.MP_ROUGHNESS))):
                    sample = edit.create_material_expression(material, self.u.MaterialExpressionTextureSample, -300, index * 220)
                    sample.set_editor_property("texture", imported[role][0])
                    sample.set_editor_property("sampler_type", self.u.MaterialSamplerType.SAMPLERTYPE_NORMAL if role == "normal" else self.u.MaterialSamplerType.SAMPLERTYPE_COLOR if role == "base_color" else self.u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
                    if not edit.connect_material_property(sample, "RGB" if role != "roughness" else "R", prop):
                        raise RuntimeError("failed PBR material connection: " + role)
                edit.recompile_material(material)
                self.save(material, material_package, material_sha)
            if "mesh" in imported:
                mesh, package, sha = imported["mesh"]
                if package not in self.report["preserved"]:
                    mesh.set_material(0, material)
                    self.save(mesh, package, sha)
            self.report["importedEnvironmentAssets"].append(source["id"])
        self.report["environmentImport"] = "COMPLETE_UNREVIEWED"

    def verify_bindings(self, data):
        loaded = {}
        for role, binding in data["assets"].items():
            if not binding.get("objectPath"):
                continue
            classes = tuple(getattr(self.u, name) for name in (binding["assetClass"],))
            asset = self.need(binding["objectPath"], classes)
            record = {"objectPath": asset.get_path_name(), "assetClass": asset.get_class().get_name(), "materials": [], "animations": {}}
            if binding["assetClass"] == "SkeletalMesh":
                skeleton = asset.get_editor_property("skeleton")
                expected = self.need(binding["skeletonPath"], (self.u.Skeleton,))
                if skeleton != expected:
                    raise RuntimeError(role + ": actual skeleton does not match its binding")
                record["skeleton"] = skeleton.get_path_name()
                for action, path in binding.get("animations", {}).items():
                    animation = self.need(path, (self.u.AnimSequence,))
                    if animation.get_editor_property("skeleton") != skeleton:
                        raise RuntimeError(role + "." + action + ": retarget to the actual skeleton before binding")
                    record["animations"][action] = animation.get_path_name()
            if binding["assetClass"] in ("StaticMesh", "SkeletalMesh"):
                slots = asset.get_editor_property("static_materials" if binding["assetClass"] == "StaticMesh" else "materials")
                if not slots:
                    raise RuntimeError(role + ": no actual material slots")
                for slot in slots:
                    material = slot.get_editor_property("material_interface")
                    if material is None:
                        raise RuntimeError(role + ": empty material slot")
                    self.need(material.get_path_name(), (self.u.MaterialInterface,))
                    record["materials"].append(material.get_path_name())
            loaded[role] = asset
            self.report["loadedBindings"][role] = record
        self.report["unrealLoadVerified"] = True
        return loaded

    def create_benchmark(self, data, loaded, source_sha):
        existing = self.prepare(BENCHMARK_MAP, source_sha)
        levels = self.u.get_editor_subsystem(self.u.LevelEditorSubsystem)
        if existing is not None:
            if self.lib.get_metadata_tag(existing, "WordJourneyBenchmarkComplete") != "true":
                raise RuntimeError("previous benchmark preparation was interrupted; preserve it and recover/review the incomplete map before retrying")
            if not levels.load_level(BENCHMARK_MAP):
                raise RuntimeError("cannot reopen preserved benchmark")
            self.report["benchmarkCreation"] = "PRESERVED_REVIEW_REQUIRED"
            return
        world = self.lib.duplicate_asset(data["assets"]["BirthEnvironment"]["objectPath"], BENCHMARK_MAP)
        if world is None:
            raise RuntimeError("could not duplicate licensed source environment")
        # Record ownership immediately; later errors never justify destroying a map.
        self.lib.set_metadata_tag(world, "WordJourneyBenchmarkComplete", "false")
        self.save(world, BENCHMARK_MAP, source_sha)
        if not levels.load_level(BENCHMARK_MAP):
            raise RuntimeError("could not load duplicated benchmark")
        actors = self.u.get_editor_subsystem(self.u.EditorActorSubsystem)
        for role in BIRTH_ROLES:
            if role == "BirthEnvironment":
                continue
            binding = data["assets"][role]
            transform = binding["transform"]
            actor_class = self.u.SkeletalMeshActor if binding["assetClass"] == "SkeletalMesh" else self.u.StaticMeshActor
            actor = actors.spawn_actor_from_class(actor_class, self.u.Vector(*transform["locationCm"]), self.u.Rotator(*transform["rotationDegrees"]))
            if actor is None:
                raise RuntimeError("could not spawn bound role: " + role)
            actor.set_actor_label("WJ_" + role)
            actor.set_actor_scale3d(self.u.Vector(*transform["scale"]))
            component = actor.get_component_by_class(self.u.SkeletalMeshComponent if binding["assetClass"] == "SkeletalMesh" else self.u.StaticMeshComponent)
            if binding["assetClass"] == "StaticMesh":
                component.set_static_mesh(loaded[role])
            else:
                # Runtime reflection checks actual editor API availability. No
                # fallback mannequin/primitive is spawned on API mismatch.
                setter = getattr(component, "set_skeletal_mesh_asset", None)
                if setter is None:
                    raise RuntimeError("SkeletalMeshComponent.set_skeletal_mesh_asset unavailable in installed editor; review exact API before continuing")
                setter(loaded[role])
                idle_path = binding.get("animations", {}).get("idle")
                if idle_path:
                    override = getattr(component, "override_animation_data", None)
                    if override is None:
                        raise RuntimeError("persistent animation-data API unavailable; do not save an unanimated stand-in")
                    override(self.need(idle_path), True, True, 0.0, 1.0)
        for view in VIEWS:
            row = data["cameras"][view]
            camera = actors.spawn_actor_from_class(self.u.CineCameraActor, self.u.Vector(*row["locationCm"]), self.u.Rotator(*row["rotationDegrees"]))
            if camera is None:
                raise RuntimeError("could not create benchmark view: " + view)
            camera.set_actor_label("WJ_View_" + view)
            camera.get_cine_camera_component().set_editor_property("current_focal_length", row["focalLengthMm"])
        if not levels.save_current_level():
            raise RuntimeError("benchmark save failed")
        completed_world = self.need(BENCHMARK_MAP)
        self.lib.set_metadata_tag(completed_world, "WordJourneyBenchmarkComplete", "true")
        self.save(completed_world, BENCHMARK_MAP, source_sha)
        self.report["benchmarkCreation"] = "CREATED_UNREVIEWED"
        self.report["warnings"].append("Reopen in a fresh Editor and inspect all three cameras with actual lighting/materials/animation. No capture or frame-rate result is inferred.")


def run_editor(unreal, bindings, report_file, import_sources=False, sources_only=False):
    report = {"status": "RUNNING", "graphicsGate": "BLOCKED", "created": [], "preserved": [], "warnings": [],
              "errors": [], "loadedBindings": {}, "importedEnvironmentAssets": [], "unrealLoadVerified": False,
              "environmentImport": "NOT_RUN", "benchmarkCreation": "NOT_RUN", "shaderCompileVerified": False,
              "actualGameplayVerified": False, "gameplayCameraFramingOnly": True,
              "engineVersion": unreal.SystemLibrary.get_engine_version()}
    try:
        if not report["engineVersion"].startswith("5.8."):
            raise RuntimeError("this editor automation requires the installed stable UE5.8 API")
        work = EditorWork(unreal, report)
        if import_sources:
            work.import_environment()
        if sources_only:
            report["status"] = "SOURCE_IMPORT_COMPLETE" if import_sources else "BLOCKED"
            if not import_sources:
                report["errors"].append("SourcesOnly requires JourneyImportSources")
            report["warnings"].append("No people or complete room acquired. Benchmark and graphics gate remain blocked.")
        else:
            data = json.loads(bindings.read_text(encoding="utf-8-sig"))
            policy = host_validation(bindings)
            report["sourcePolicy"] = policy
            if policy["readyForEditor"]:
                loaded = work.verify_bindings(data)
                work.create_benchmark(data, loaded, digest(bindings))
                report["status"] = "BENCHMARK_PREPARED_UNREVIEWED"
            else:
                report["status"] = "BLOCKED"
                report["errors"].extend(policy["errors"])
    except Exception as exc:
        report["status"] = "FAILED"
        report["errors"].append(str(exc))
        report["traceback"] = traceback.format_exc()
    _write(report_file, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def options(unreal):
    line = unreal.SystemLibrary.get_command_line()
    def value(name):
        match = re.search(r'(?:^|\s)-' + name + r'=(?:"([^\"]*)"|([^\s\"]+))', line)
        return (match.group(1) if match.group(1) is not None else match.group(2)) if match else None
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bindings", type=Path, default=value("JourneyBindings"))
    parser.add_argument("--report", type=Path, default=value("JourneyReport"))
    parser.add_argument("--import-sources", action="store_true", default="-JourneyImportSources" in line)
    parser.add_argument("--sources-only", action="store_true", default="-JourneySourcesOnly" in line)
    args, _ = parser.parse_known_args()
    # Process-scoped paths avoid the different quoting forms returned by
    # GetCommandLineW when PowerShell serializes arguments with spaces/Unicode.
    # The invoking host script owns their temporary setup and restoration.
    bindings_path = os.environ.get("WORD_JOURNEY_BINDINGS") or args.bindings
    report_path = os.environ.get("WORD_JOURNEY_REPORT") or args.report
    args.bindings = Path(bindings_path) if bindings_path else HERE / "asset-bindings.example.json"
    args.report = Path(report_path) if report_path else PROJECT / "Saved/WordJourney/benchmark-report.json"
    return args


if __name__ == "__main__":
    import unreal
    args = options(unreal)
    result = run_editor(unreal, args.bindings, args.report, args.import_sources, args.sources_only)
    if result["status"] in ("FAILED", "BLOCKED"):
        unreal.log_error("WordJourney benchmark blocked/failed. See " + str(args.report))
