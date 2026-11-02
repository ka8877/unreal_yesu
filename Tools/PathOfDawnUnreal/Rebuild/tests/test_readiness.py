"""Policy and real-file failure cases, not a mock Unreal quality certification."""
import copy
import contextlib
import io
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import validate_readiness as policy
import editor_benchmark as editor


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.evidence = self.root / "license.txt"
        self.evidence.write_text("Fixture license evidence for validator behavior only")
        template = json.loads((TOOLS / "asset-bindings.example.json").read_text())
        self.data = template
        for role, row in self.data["assets"].items():
            row.update(objectPath=f"/Game/Fixture/{role}.{role}", sourceUrl="https://example.invalid/fixture-only", license="fixture-only", qualityApproved=True)
            row["licenseReview"].update(evidencePath="license.txt", sha256=policy.digest(self.evidence), reviewer="fixture-only", permittedGameDistribution=True)
            if row["assetClass"] == "SkeletalMesh":
                row["skeletonPath"] = "/Game/Fixture/Skeleton.Skeleton"
                row["animations"] = {k: "/Game/Fixture/Animation.Animation" for k in row["animations"]}
            if "transform" in row:
                row["transform"].update(locationCm=[0, 0, 0], rotationDegrees=[0, 0, 0])
        for row in self.data["cameras"].values():
            row.update(locationCm=[0, 0, 0], rotationDegrees=[0, 0, 0])

    def tearDown(self):
        self.temp.cleanup()

    def validate(self):
        return policy.validate_bindings(self.data, self.root)

    def test_policy_ready_is_explicitly_not_unreal_or_graphics_pass(self):
        result = self.validate()
        self.assertTrue(result["readyForEditor"], result["errors"])
        self.assertFalse(result["unrealLoadVerified"])
        self.assertEqual(result["graphicsGate"], "NOT_RUN")

    def test_unacquired_template_blocks_all_roles_without_invented_paths(self):
        template = json.loads((TOOLS / "asset-bindings.example.json").read_text())
        self.assertTrue(all(v["objectPath"] is None for v in template["assets"].values()))
        result = policy.validate_bindings(template, self.root)
        self.assertFalse(result["readyForEditor"])
        for role in policy.BIRTH_ROLES:
            self.assertTrue(any(role in error for error in result["errors"]))

    def test_missing_walk_or_wrong_age_cannot_pass(self):
        del self.data["assets"]["Joseph"]["animations"]["walk"]
        self.data["assets"]["Baby"]["ageCategory"] = "adult"
        self.data["assets"]["Baby"]["transform"]["scale"] = [.2, .2, .2]
        result = self.validate()
        self.assertTrue(any("walk" in e for e in result["errors"]))
        self.assertTrue(any("age-appropriate" in e for e in result["errors"]))
        self.assertTrue(any("adult-to-child" in e for e in result["errors"]))

    def test_mannequin_and_legacy_characters_rejected(self):
        for origin in policy.FORBIDDEN_ORIGINS:
            self.data["assets"]["Joseph"]["origin"] = origin
            self.assertFalse(self.validate()["readyForEditor"])
        self.data["assets"]["Joseph"]["origin"] = "licensed_import"
        self.data["assets"]["Joseph"]["objectPath"] = "/Game/PathOfDawn/Characters/SM_Traveler.SM_Traveler"
        self.assertFalse(self.validate()["readyForEditor"])

    def test_bad_paths_license_corruption_and_lfs_pointer_rejected(self):
        review = self.data["assets"]["Mary"]["licenseReview"]
        review["evidencePath"] = "../outside.txt"
        self.assertFalse(self.validate()["readyForEditor"])
        review["evidencePath"] = "license.txt"
        self.evidence.write_text("changed license bytes")
        self.assertTrue(any("hash" in e for e in self.validate()["errors"]))
        self.evidence.write_text("version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 2\n")
        self.assertTrue(any("LFS pointer" in e for e in self.validate()["errors"]))

    def test_missing_camera_or_nonfinite_transform_rejected(self):
        self.data["cameras"]["closeup"]["locationCm"] = [float("nan"), 0, 0]
        self.data["assets"]["Joseph"]["transform"]["scale"] = [1, 1, float("inf")]
        self.assertFalse(self.validate()["readyForEditor"])

    def test_temple_cannot_be_implicitly_completed(self):
        self.data["stage"] = "temple"
        self.data["birthGraphicsGatePassed"] = True  # a boolean assertion is not evidence
        result = self.validate()
        self.assertTrue(any("birth graphics gate" in e for e in result["errors"]))
        self.assertTrue(any("ChildJesus" in e for e in result["errors"]))

    def test_blocked_bindings_never_touch_editor_map_or_asset_loader(self):
        class Unavailable:
            @staticmethod
            def get_asset_tools():
                return None
        class Editor:
            EditorAssetLibrary = None
            AssetToolsHelpers = Unavailable
            class SystemLibrary:
                @staticmethod
                def get_engine_version():
                    return "5.8.4-test-fixture"
        path = self.root / "bindings.json"
        path.write_text((TOOLS / "asset-bindings.example.json").read_text())
        with contextlib.redirect_stdout(io.StringIO()), patch.object(editor, "ROOT", self.root), patch.object(editor, "INDEX_PATH", self.root / "index.json"):
            result = editor.run_editor(Editor, path, self.root / "report.json")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["benchmarkCreation"], "NOT_RUN")
        self.assertEqual(result["created"], [])
        self.assertFalse((self.root / "index.json").exists())

    def environment(self):
        rows = []
        for role, space in (("base_color", "sRGB"), ("normal", "linear"), ("roughness", "linear")):
            path = self.root / (role + ".png")
            Image.new("RGB", (8, 8), (128, 128, 255)).save(path)
            rows.append({"role": role, "path": path.name, "bytes": path.stat().st_size, "sha256": policy.digest(path), "color_space": space, "normal_convention": "DirectX"})
        return {"schema_version": 1, "assets": [{"id": "fixture", "kind": "pbr_material", "license": "CC0-1.0", "source_url": "https://example.invalid/fixture-only", "files": rows}]}

    def test_pbr_bytes_and_color_space_must_match(self):
        data = self.environment()
        self.assertFalse(policy.validate_environment(data, self.root)["errors"])
        data["assets"][0]["files"][1]["color_space"] = "sRGB"
        self.assertTrue(policy.validate_environment(data, self.root)["errors"])
        data["assets"][0]["files"][1]["color_space"] = "linear"
        (self.root / "roughness.png").write_bytes(b"bad")
        self.assertTrue(policy.validate_environment(data, self.root)["errors"])

    def test_forged_hash_of_non_image_is_not_a_texture(self):
        data = self.environment()
        path = self.root / "base_color.png"
        path.write_bytes(b"not an image")
        data["assets"][0]["files"][0].update(bytes=path.stat().st_size, sha256=policy.digest(path))
        self.assertTrue(policy.validate_environment(data, self.root)["errors"])

    def test_absent_graphics_capture_or_nullrhi_never_passes(self):
        result = policy.validate_graphics_evidence({"bindingsSha256": "actual", "engine": "Unreal Engine 5.8", "renderMode": "NullRHI"}, self.root, "actual")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertGreater(len(result["errors"]), 10)


if __name__ == "__main__":
    unittest.main()
