"""Real separate Python processes; no Unreal or graphics emulation/certification."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import editor_benchmark as editor


class EditorPythonIsolationTests(unittest.TestCase):
    def test_stdlib_only_editor_python_runs_full_decode_in_authoring_python(self):
        # -S represents the dependency boundary, not an actual UE interpreter.
        program = f"""
import importlib.util, json, sys
assert importlib.util.find_spec('PIL') is None
sys.path.insert(0, {str(TOOLS)!r})
import editor_benchmark as editor
from validate_readiness import validate_environment
manifest = json.loads(editor.SOURCE_MANIFEST.read_text(encoding='utf-8'))
negative = validate_environment(manifest, editor.SOURCE_MANIFEST.parent)
assert any('PIL' in error for error in negative['errors'])
positive = editor.host_validation()
assert not positive['errors'], positive
assert positive['status'] == 'SOURCE_FILES_VERIFIED'
assert positive['manifestSha256'] == editor.digest(editor.SOURCE_MANIFEST)
assert positive['unrealImportVerified'] is False
print('PASS: no Pillow in editor interpreter; genuine source images fully checked by authoring Python')
"""
        environment = dict(os.environ, WORD_JOURNEY_HOST_PYTHON=sys.executable)
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONHOME", None)
        result = subprocess.run([sys.executable, "-S", "-c", program], capture_output=True,
                                text=True, encoding="utf-8", env=environment, timeout=40)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS:", result.stdout)

    def test_forged_image_bytes_with_matching_hash_are_rejected_by_host(self):
        with tempfile.TemporaryDirectory(prefix="journey source 경로 ") as temporary:
            root = Path(temporary)
            source = root / "SourceArt/PathOfDawnUnreal/Rebuild/Environment"
            source.mkdir(parents=True)
            files = []
            for role, space in (("base_color", "sRGB"), ("normal", "linear"), ("roughness", "linear")):
                file = source / (role + ".png")
                Image.new("RGB", (8, 8), (128, 128, 255)).save(file)
                if role == "base_color":
                    file.write_bytes(b"not actually a PNG")
                files.append({"role": role, "path": file.name, "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                              "bytes": file.stat().st_size, "color_space": space, "normal_convention": "DirectX"})
            manifest = {"schema_version": 1, "assets": [{"id": "fixture", "kind": "pbr_material", "license": "CC0-1.0",
                                                          "source_url": "https://example.invalid/test-only", "files": files}]}
            (source / "manifest.json").write_text(json.dumps(manifest))
            with patch.object(editor, "ROOT", root), patch.dict(os.environ, {"WORD_JOURNEY_HOST_PYTHON": sys.executable}):
                result = editor.host_validation()
            self.assertEqual(result["status"], "BLOCKED")
            self.assertTrue(any("base_color" in error for error in result["errors"]))
            self.assertFalse(result["unrealImportVerified"])

    def test_unconfigured_host_fails_before_spawning_a_process(self):
        with patch.dict(os.environ, {"WORD_JOURNEY_HOST_PYTHON": ""}), patch.object(subprocess, "run") as start:
            with self.assertRaisesRegex(RuntimeError, "PrepareRebuild.ps1"):
                editor.host_validation()
            start.assert_not_called()

    def test_host_timeout_is_reported_without_leaving_validation_files(self):
        created = []
        def timeout(arguments, **kwargs):
            created.append(Path(arguments[arguments.index("--report") + 1]).parent)
            raise subprocess.TimeoutExpired(arguments, kwargs["timeout"])
        with patch.dict(os.environ, {"WORD_JOURNEY_HOST_PYTHON": sys.executable}), patch.object(subprocess, "run", side_effect=timeout):
            with self.assertRaises(subprocess.TimeoutExpired):
                editor.host_validation()
        self.assertTrue(created)
        self.assertTrue(all(not path.exists() for path in created))


if __name__ == "__main__":
    unittest.main()
