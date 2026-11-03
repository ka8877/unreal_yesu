"""Read-only registry/load contracts. Fixtures do not claim an Unreal run."""
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

TOOLS = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sample_probe", TOOLS / "inspect_sample.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class Object:
    def __init__(self, path, **properties): self.path, self.properties = path, properties
    def get_path_name(self): return self.path
    def get_editor_property(self, name): return self.properties[name]


class Mesh(Object): pass
class Animation(Object): pass


def asset(name, kind):
    return SimpleNamespace(package_name="/Game/Fixture/" + name, asset_name=name,
                           asset_class_path=SimpleNamespace(asset_name=kind))


class SampleInspectionTests(unittest.TestCase):
    def make_editor(self, records, objects):
        self.loaded = []
        self.scanned = []
        def load(path):
            self.loaded.append(path)
            return objects.get(path)
        registry = SimpleNamespace(search_all_assets=lambda sync: self.scanned.append(sync),
                                   get_assets_by_path=lambda root, recursive: records)
        return SimpleNamespace(SystemLibrary=SimpleNamespace(get_engine_version=lambda: "5.8.0-fixture"),
                               AssetRegistryHelpers=SimpleNamespace(get_asset_registry=lambda: registry),
                               EditorAssetLibrary=SimpleNamespace(load_asset=load), SkeletalMesh=Mesh, AnimSequence=Animation)

    def test_real_paths_and_exact_skeleton_identity_without_visual_approval(self):
        skeleton = Object("/Game/Fixture/HumanSkeleton.HumanSkeleton")
        records = [asset("Person", "SkeletalMesh"), asset("Walk", "AnimSequence"), asset("Level", "World")]
        objects = {"/Game/Fixture/Person.Person": Mesh("Person", skeleton=skeleton, materials=[]),
                   "/Game/Fixture/Walk.Walk": Animation("Walk", skeleton=skeleton, sequence_length=1.2)}
        result = probe.inspect_assets(self.make_editor(records, objects))
        self.assertEqual(result["status"], "SAMPLE_ASSETS_INSPECTED")
        self.assertEqual(result["sameSkeletonPairs"][0]["skeleton"], skeleton.path)
        self.assertEqual(result["motionCandidates"]["walk"], ["/Game/Fixture/Walk.Walk"])
        self.assertFalse(result["graphicsVerified"])
        self.assertFalse(result["retargetVerified"])
        self.assertFalse(result["sourceAssetsSaved"])
        self.assertFalse(result["licensedSourceFilesExported"])
        self.assertNotIn("/Game/Fixture/Level.Level", self.loaded)

    def test_loading_budget_and_each_motion_category(self):
        records, objects = [], {}
        skeleton = Object("/Game/Fixture/Skeleton.Skeleton")
        for number in range(10):
            name = "Person" + str(number)
            records.append(asset(name, "SkeletalMesh"))
            objects["/Game/Fixture/" + name + "." + name] = Mesh(name, skeleton=skeleton, materials=[])
        for kind in ("Idle", "Walk", "Stop", "Turn"):
            for number in range(20):
                name = kind + str(number)
                records.append(asset(name, "AnimSequence"))
                objects["/Game/Fixture/" + name + "." + name] = Animation(name, skeleton=skeleton, sequence_length=1)
        result = probe.inspect_assets(self.make_editor(records, objects))
        self.assertEqual(len(result["loadedMeshes"]), 6)
        self.assertLessEqual(len(result["loadedAnimations"]), 12)
        self.assertTrue(all(result["motionCandidates"][kind] for kind in probe.MOTION_WORDS))
        self.assertLessEqual(len(self.loaded), 18)

    def test_wrong_loaded_class_and_missing_properties_are_not_assumed(self):
        records = [asset("Person", "SkeletalMesh"), asset("Idle", "AnimSequence")]
        objects = {"/Game/Fixture/Person.Person": Object("WrongClass"),
                   "/Game/Fixture/Idle.Idle": Animation("Idle")}
        result = probe.inspect_assets(self.make_editor(records, objects))
        self.assertEqual(result["status"], "PARTIAL_INVENTORY")
        self.assertEqual(result["loadedMeshes"], [])
        self.assertIsNone(result["loadedAnimations"][0]["skeleton"])
        self.assertTrue(result["warnings"])
        self.assertEqual(result["sameSkeletonPairs"], [])

    def test_empty_registry_and_engine_mismatch_block(self):
        with self.assertRaisesRegex(RuntimeError, "No /Game assets"):
            probe.inspect_assets(self.make_editor([], {}))
        editor = self.make_editor([asset("Person", "SkeletalMesh")], {})
        editor.SystemLibrary.get_engine_version = lambda: "5.7.0-fixture"
        with self.assertRaisesRegex(RuntimeError, "UE5.8"):
            probe.inspect_assets(editor)

    def test_inventory_cap_is_explicit_and_engine_assets_are_excluded(self):
        records = [asset("Rig" + str(i), "Skeleton") for i in range(10)]
        records.append(SimpleNamespace(package_name="/Engine/Cube", asset_name="Cube", asset_class_path=SimpleNamespace(asset_name="StaticMesh")))
        result = probe.inspect_assets(self.make_editor(records, {}), max_rows=3)
        self.assertTrue(result["assetRowsTruncated"])
        self.assertEqual(len(result["assets"]), 3)
        self.assertEqual(result["totalAssetCount"], 10)

    def test_standalone_launcher_pins_the_exact_companion_source(self):
        import hashlib
        expected = hashlib.sha256((TOOLS / "inspect_sample.py").read_bytes()).hexdigest()
        launcher = (TOOLS / "InspectSample.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("$ExpectedPythonSha256='" + expected + "'", launcher)
        self.assertNotIn("PYTHON_HASH_PENDING", launcher)


if __name__ == "__main__": unittest.main()
