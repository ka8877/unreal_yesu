"""Filesystem ownership tests on temporary fixture bytes, without Unreal.

Files carrying .uasset/.umap/.uexp/.ubulk/.uptnl extensions below are deliberately
synthetic byte fixtures. They are neither Unreal packages nor engine execution
evidence. These tests exercise the real disk ownership helper used by the Editor
importer, especially its refusal to overwrite user or inconsistent files.
"""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    'gospel_asset_guard', Path(__file__).resolve().parents[1] / 'gospel_asset_guard.py')
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


class GospelAssetGuardTests(unittest.TestCase):
    ASSET = '/Game/PathOfDawnGospel/Data/DA_Campaign'
    MAP = '/Game/PathOfDawnGospel/Maps/L_TemplePreview'
    SOURCE = '1' * 64
    CHANGED_SOURCE = '2' * 64

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='pod-gospel-ownership-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.content = self.root / 'Content'
        self.content.mkdir()
        self.index_path = self.root / 'generated-gospel-index.json'
        self.index = GUARD.load_index(self.index_path)

    def package_file(self, asset=None, extension='.uasset'):
        asset = self.ASSET if asset is None else asset
        return (self.content / asset.removeprefix('/Game/')).with_suffix(extension)

    def write_package(self, asset=None, *, is_map=False, sidecars=()):
        asset = self.ASSET if asset is None else asset
        main = self.package_file(asset, '.umap' if is_map else '.uasset')
        main.parent.mkdir(parents=True, exist_ok=True)
        main.write_bytes(b'SYNTHETIC filesystem ownership fixture, not an Unreal package\x00')
        for extension in sidecars:
            main.with_suffix(extension).write_bytes(b'synthetic sidecar:' + extension.encode('ascii'))
        return main

    def record(self, asset=None, *, is_map=False):
        asset = self.ASSET if asset is None else asset
        GUARD.record(self.index, asset, self.SOURCE, self.content, is_map=is_map)

    def symlink(self, path, target, *, directory=False):
        try:
            path.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError) as error:
            self.skipTest('This host cannot create symbolic-link fixtures: ' + str(error))

    def plan(self, asset=None, *, source=None, exists=True, is_map=False, index=None):
        return GUARD.plan(
            self.ASSET if asset is None else asset,
            self.SOURCE if source is None else source,
            self.index if index is None else index,
            self.content, exists, is_map=is_map)

    def test_missing_index_is_an_empty_baseline_without_writing(self):
        self.assertEqual(self.index, {'kind': GUARD.KIND, 'schema': 1, 'assets': {}})
        self.assertFalse(self.index_path.exists())

    def test_first_generation_creates_only_absent_asset_or_map(self):
        for asset, is_map in ((self.ASSET, False), (self.MAP, True)):
            with self.subTest(asset=asset):
                self.assertEqual(self.plan(asset, exists=False, is_map=is_map), 'create')
        self.assertFalse(any(self.content.rglob('*')))
        self.assertFalse(self.index['assets'])

    def test_owned_uasset_and_umap_baselines_survive_index_roundtrip(self):
        for asset, is_map in ((self.ASSET, False), (self.MAP, True)):
            self.write_package(asset, is_map=is_map, sidecars=('.uexp', '.ubulk', '.uptnl'))
            self.record(asset, is_map=is_map)
        GUARD.save_index(self.index_path, self.index)
        loaded = GUARD.load_index(self.index_path)
        self.assertEqual(loaded, self.index)
        self.assertFalse(self.index_path.with_name(self.index_path.name + '.tmp').exists())
        for asset, is_map in ((self.ASSET, False), (self.MAP, True)):
            with self.subTest(asset=asset):
                self.assertEqual(self.plan(asset, is_map=is_map, index=loaded), 'preserve')

    def test_new_data_source_refreshes_only_owned_unchanged_package(self):
        main = self.write_package(sidecars=('.uexp',))
        self.record()
        before = main.read_bytes(), copy.deepcopy(self.index)
        self.assertEqual(self.plan(source=self.CHANGED_SOURCE), 'refresh')
        self.assertEqual((main.read_bytes(), self.index), before)

    def test_user_main_edit_is_rejected_with_original_bytes_and_index_preserved(self):
        main = self.write_package()
        self.record()
        main.write_bytes(b'user-authored package fixture that must survive')
        baseline = copy.deepcopy(self.index)
        for source in (self.SOURCE, self.CHANGED_SOURCE):
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.plan(source=source)
        self.assertEqual(main.read_bytes(), b'user-authored package fixture that must survive')
        self.assertEqual(self.index, baseline)

    def test_each_edited_sidecar_blocks_refresh_and_preserve(self):
        for extension in ('.uexp', '.ubulk', '.uptnl'):
            with self.subTest(extension=extension):
                main = self.write_package(sidecars=('.uexp', '.ubulk', '.uptnl'))
                self.record()
                sidecar = main.with_suffix(extension)
                sidecar.write_bytes(b'edited user sidecar fixture')
                for source in (self.SOURCE, self.CHANGED_SOURCE):
                    with self.assertRaises(ValueError):
                        self.plan(source=source)
                self.assertEqual(sidecar.read_bytes(), b'edited user sidecar fixture')

    def test_added_or_deleted_sidecar_invalidates_the_ownership_baseline(self):
        main = self.write_package()
        self.record()
        main.with_suffix('.uexp').write_bytes(b'added sidecar fixture')
        with self.assertRaises(ValueError):
            self.plan()
        self.record()
        main.with_suffix('.uexp').unlink()
        with self.assertRaises(ValueError):
            self.plan(source=self.CHANGED_SOURCE)

    def test_existing_asset_without_ownership_index_cannot_be_overwritten(self):
        main = self.write_package()
        before = main.read_bytes()
        for source in (self.SOURCE, self.CHANGED_SOURCE):
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.plan(source=source)
        self.assertEqual(main.read_bytes(), before)
        self.assertFalse(self.index['assets'])

    def test_owned_map_recipe_change_requires_new_map_path(self):
        main = self.write_package(self.MAP, is_map=True, sidecars=('.uexp',))
        self.record(self.MAP, is_map=True)
        before = main.read_bytes(), copy.deepcopy(self.index)
        with self.assertRaises(ValueError):
            self.plan(self.MAP, source=self.CHANGED_SOURCE, is_map=True)
        self.assertEqual((main.read_bytes(), self.index), before)

    def test_unregistered_package_present_on_disk_blocks_creation(self):
        for asset, is_map in ((self.ASSET, False), (self.MAP, True)):
            with self.subTest(asset=asset):
                main = self.write_package(asset, is_map=is_map)
                before = main.read_bytes()
                with self.assertRaises(ValueError):
                    self.plan(asset, exists=False, is_map=is_map)
                self.assertEqual(main.read_bytes(), before)

    def test_registered_package_missing_on_disk_blocks_preserve_and_refresh(self):
        for asset, is_map in ((self.ASSET, False), (self.MAP, True)):
            with self.subTest(asset=asset):
                main = self.write_package(asset, is_map=is_map)
                self.record(asset, is_map=is_map)
                main.unlink()
                for source in (self.SOURCE, self.CHANGED_SOURCE):
                    with self.assertRaises(ValueError):
                        self.plan(asset, source=source, is_map=is_map)

    def test_record_requires_a_real_saved_main_file(self):
        with self.assertRaises(ValueError):
            self.record()
        self.assertFalse(self.index['assets'])

    def test_corrupt_index_is_rejected_without_rewriting_original(self):
        valid = {'kind': GUARD.KIND, 'schema': 1, 'assets': {}}
        cases = [
            '{broken json', 'null', '[]',
            json.dumps({**valid, 'kind': 'other-index'}),
            json.dumps({**valid, 'schema': 999}),
            json.dumps({**valid, 'schema': True}),
            json.dumps({**valid, 'assets': []}),
            json.dumps({**valid, 'assets': {self.ASSET: {}}}),
            json.dumps({**valid, 'assets': {self.ASSET: None}}),
            json.dumps({**valid, 'assets': {self.ASSET: {
                'source_sha256': 'invalid', 'package_sha256': self.SOURCE}}}),
        ]
        for document in cases:
            with self.subTest(document=document):
                self.index_path.write_text(document, encoding='utf-8')
                with self.assertRaises(ValueError):
                    GUARD.load_index(self.index_path)
                self.assertEqual(self.index_path.read_text(encoding='utf-8'), document)

    def test_source_hash_must_be_canonical_before_any_plan(self):
        for source in ('', 'A' * 64, '0' * 63, 'g' * 64, '../bad'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.plan(source=source, exists=False)
        self.assertFalse(any(self.content.rglob('*')))

    def test_package_paths_reject_traversal_object_suffix_and_other_roots(self):
        for asset in (
            '/Game/PathOfDawnGospel/../External', '/Game/PathOfDawnGospel/Data/../../External',
            '/Game/PathOfDawnGospel/Data/DA_Test.DA_Test', '/Game/PathOfDawnGospel/Data/DA_Test.uasset',
            '/Game/Other/Data/DA_Test', '/Game/PathOfDawnGospel',
            '/Game/PathOfDawnGospel/Data\\DA_Test', '/Game/PathOfDawnGospel//DA_Test',
            '/Game/PathOfDawnGospel/Data/DA_Test/',
        ):
            with self.subTest(asset=asset), self.assertRaises(ValueError):
                self.plan(asset, exists=False)
        self.assertFalse(any(self.content.rglob('*')))

    def test_main_and_sidecar_symlinks_cannot_claim_ownership(self):
        outside = self.root / 'outside-bytes.bin'
        outside.write_bytes(b'external fixture bytes')
        for extension in ('.uasset', '.uexp', '.ubulk', '.uptnl'):
            with self.subTest(extension=extension):
                main = self.write_package()
                link = main.with_suffix(extension)
                if link.exists() or link.is_symlink():
                    link.unlink()
                self.symlink(link, outside)
                with self.assertRaises(ValueError):
                    GUARD.package_hash(self.ASSET, self.content)
                link.unlink()
        self.assertEqual(outside.read_bytes(), b'external fixture bytes')

    def test_broken_main_symlink_cannot_be_treated_as_safe_new_package(self):
        main = self.package_file()
        main.parent.mkdir(parents=True)
        self.symlink(main, self.root / 'absent-external-file')
        with self.assertRaises(ValueError):
            self.plan(exists=False)
        self.assertTrue(main.is_symlink())

    def test_symlinked_package_directory_cannot_escape_the_content_root(self):
        outside = self.root / 'outside-directory'
        outside.mkdir()
        (outside / 'DA_Campaign.uasset').write_bytes(b'external package fixture')
        gospel = self.content / 'PathOfDawnGospel'
        gospel.mkdir()
        self.symlink(gospel / 'Data', outside, directory=True)
        with self.assertRaises(ValueError):
            GUARD.package_hash(self.ASSET, self.content)
        self.assertEqual((outside / 'DA_Campaign.uasset').read_bytes(), b'external package fixture')

    def test_orphan_sidecar_is_preserved_when_main_package_is_absent(self):
        for extension in ('.uexp', '.ubulk', '.uptnl'):
            with self.subTest(extension=extension):
                path = self.package_file(extension=extension)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'orphan user sidecar fixture')
                with self.assertRaises(ValueError):
                    self.plan(exists=False)
                self.assertEqual(path.read_bytes(), b'orphan user sidecar fixture')
                path.unlink()


if __name__ == '__main__':
    unittest.main(verbosity=2)
