"""Real packaged art checks through Windows-style path semantics on any OS.

Only relative path presentation is adapted. File reads, PNG decoding, FBX
headers and SHA256/provenance comparisons use the real repository sources.
This catches the Windows-only failure without claiming a Windows/UE run.
"""
import importlib.util
import json
import os
import unittest
from pathlib import Path, PureWindowsPath
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    'visual_source_validator', ROOT / 'Tools/PathOfDawnUnreal/validate_visual_sources.py')
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class WindowsPathView(os.PathLike):
    """Use real local I/O while relative_to returns actual PureWindowsPath."""
    def __init__(self, path):
        self.path = Path(path)

    def __truediv__(self, other):
        return WindowsPathView(self.path / other)

    def __fspath__(self):
        return os.fspath(self.path)

    @property
    def stem(self):
        return self.path.stem

    def relative_to(self, other):
        return PureWindowsPath(*self.path.relative_to(other.path).parts)

    def read_bytes(self):
        return self.path.read_bytes()

    def read_text(self, **kwargs):
        return self.path.read_text(**kwargs)

    def is_file(self):
        return self.path.is_file()


class VisualSourcePathsTests(unittest.TestCase):
    def test_real_sources_match_manifest_with_windows_relative_paths(self):
        result = VALIDATOR.validate(WindowsPathView(ROOT))
        self.assertEqual(result['status'], 'passed', result['errors'])
        self.assertEqual(len(result['sources']), 25)
        self.assertTrue(all('\\' not in row['file'] for row in result['sources']))
        self.assertIn('SourceArt/PathOfDawnUnreal/VisualV8/Illustrations/IL_Title_Dawn.png',
                      {row['file'] for row in result['sources']})

    def test_windows_and_native_validation_have_identical_asset_records(self):
        windows = VALIDATOR.validate(WindowsPathView(ROOT))
        native = VALIDATOR.validate(ROOT)
        self.assertEqual(windows['sources'], native['sources'])
        self.assertEqual(windows['errors'], native['errors'])

    def assert_changed_manifest_rejected(self, mutate):
        manifest = ROOT / 'Docs/PathOfDawnUnreal/AssetManifest.json'
        contents = json.loads(manifest.read_text(encoding='utf-8'))
        file = 'SourceArt/PathOfDawnUnreal/VisualV8/Illustrations/IL_Title_Dawn.png'
        mutate(contents, file)
        read_text = WindowsPathView.read_text

        def overridden(view, **kwargs):
            if view.path == manifest:
                return json.dumps(contents)
            return read_text(view, **kwargs)

        with patch.object(WindowsPathView, 'read_text', overridden):
            result = VALIDATOR.validate(WindowsPathView(ROOT))
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['errors'], ['Missing/stale provenance manifest entry: ' + file])

    def test_windows_still_rejects_wrong_asset_hash(self):
        def change(contents, file):
            next(row for row in contents['assets'] if row['file'] == file)['sha256'] = '0' * 64
        self.assert_changed_manifest_rejected(change)

    def test_windows_still_rejects_missing_manifest_entry(self):
        def change(contents, file):
            contents['assets'] = [row for row in contents['assets'] if row['file'] != file]
        self.assert_changed_manifest_rejected(change)


if __name__ == '__main__':
    unittest.main()
