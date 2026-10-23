"""Checks refresh ownership decisions on temporary byte files, without Unreal."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('source_asset_guard', Path(__file__).resolve().parents[1] / 'source_asset_guard.py')
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)

class SourceAssetGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pod-source-guard-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'authoring.txt'
        self.package = self.root / 'package-bytes.bin'
        self.source.write_bytes(b'original authoring bytes')
        self.package.write_bytes(b'generated binary package bytes')
        self.source_hash = GUARD.sha256_file(self.source)
        self.package_hash = GUARD.sha256_file(self.package)
        self.entry = {'source_sha256': self.source_hash, 'package_sha256': self.package_hash}

    def decide(self, entry=None, exists=True, imported=None):
        return GUARD.refresh_decision(GUARD.sha256_file(self.source), GUARD.sha256_file(self.package), self.entry if entry is None else entry, exists, imported)[0]

    def test_first_generation_and_repeat(self):
        self.assertEqual(self.decide(exists=False), 'create')
        self.assertEqual(self.decide(), 'preserve')

    def test_source_update_refreshes_only_known_generated_package(self):
        self.source.write_bytes(b'new authoritative source')
        self.assertEqual(self.decide(), 'refresh')
        self.assertEqual(GUARD.sha256_file(self.package), self.package_hash)

    def test_user_package_edit_is_preserved_with_unchanged_source(self):
        self.package.write_bytes(b'user edited package')
        self.assertEqual(self.decide(), 'preserve_user_edit')
        self.assertEqual(self.entry['package_sha256'], self.package_hash)

    def test_source_and_package_change_conflicts_without_mutation(self):
        self.package.write_bytes(b'user edited package')
        self.source.write_bytes(b'updated source')
        before = self.package.read_bytes()
        self.assertEqual(self.decide(), 'conflict')
        self.assertEqual(self.package.read_bytes(), before)

    def test_missing_baseline_never_permits_refresh(self):
        self.assertEqual(self.decide(entry={}), 'conflict')
        self.assertEqual(self.decide(entry={}, imported=self.source_hash), 'preserve_untracked')
        self.source.write_bytes(b'updated source')
        self.assertEqual(self.decide(entry={}, imported=self.source_hash), 'conflict')

    def test_missing_package_blocks_existing_asset(self):
        self.assertEqual(GUARD.refresh_decision(self.source_hash, None, self.entry, True)[0], 'conflict')

    def test_index_roundtrip_and_reject_bad_version(self):
        path = self.root / 'generated-source-index.json'
        index = GUARD.load_index(path)
        index['assets']['/Game/PathOfDawn/Illustrations/IL_Test'] = self.entry
        GUARD.save_index(path, index)
        self.assertEqual(GUARD.load_index(path), index)
        self.assertFalse(path.with_name(path.name+'.tmp').exists())
        path.write_text('{"kind":"PathOfDawn.GeneratedSourceIndex","schema":999,"assets":{}}')
        with self.assertRaises(ValueError): GUARD.load_index(path)

if __name__ == '__main__': unittest.main(verbosity=2)
