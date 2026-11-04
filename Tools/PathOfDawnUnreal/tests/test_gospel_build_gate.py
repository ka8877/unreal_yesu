"""Test evidence/package freshness gates with synthetic disk-package bytes.

The fixtures are not Unreal packages or reports of engine execution.
"""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Tools/PathOfDawnUnreal/Gospel'))
import check_generated_assets as gate
import gospel_asset_guard as guard


class GospelBuildGateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='gospel-gate-fixture-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / 'Games/PathOfDawnUnreal'
        sources = ['SourceArt/PathOfDawnUnreal/Gospel/Campaign.json',
                   'SourceArt/PathOfDawnUnreal/Gospel/TemplePreview.json',
                   'SourceArt/PathOfDawnUnreal/Fonts/NotoSansKR.otf',
                   'Tools/PathOfDawnUnreal/generate_gospel_assets.py']
        runtime = ROOT / 'Games/PathOfDawnUnreal/Source/PathOfDawnUnreal'
        sources += [str(p.relative_to(ROOT)) for p in runtime.rglob('*')
                    if p.is_file() and ('Gospel' in p.name or p.name == 'PathOfDawnUnreal.Build.cs')]
        for relative in sources:
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        source = self.root / 'SourceArt/PathOfDawnUnreal/Gospel'
        self.campaign_path = source / 'Campaign.json'
        self.recipe_path = source / 'TemplePreview.json'
        self.generator = self.root / 'Tools/PathOfDawnUnreal/generate_gospel_assets.py'
        self.campaign = json.loads(self.campaign_path.read_text(encoding='utf-8'))
        self.recipe = json.loads(self.recipe_path.read_text(encoding='utf-8'))
        temple = [q for q in self.campaign['Quests'] if q['ChapterId'] == 'temple']
        runtime_hash = gate.runtime_source_sha256(self.root)
        data_hash = gate.fingerprint(self.campaign_path.read_bytes(), self.generator.read_bytes(), runtime_hash)
        map_hash = gate.fingerprint(self.recipe_path.read_bytes(), json.dumps([(q['Id'], q['NpcId']) for q in temple]), self.generator.read_bytes())
        font_hash = guard.sha256_file(self.root / 'SourceArt/PathOfDawnUnreal/Fonts/NotoSansKR.otf')
        self.index = {'kind': guard.KIND, 'schema': 1, 'assets': {}}
        for name in sorted(gate.REQUIRED):
            is_map = name.endswith('/L_GospelTemplePreview')
            package = (self.project / 'Content' / name[len('/Game/'):]).with_suffix('.umap' if is_map else '.uasset')
            package.parent.mkdir(parents=True, exist_ok=True)
            package.write_bytes(b'NOT-AN-UNREAL-PACKAGE: filesystem-fixture:' + name.encode('ascii'))
            if '/Materials/' in name:
                short = name.rsplit('/', 1)[1]
                color = (.42, .37, .27) if short == 'M_PreviewStone' else (.70, .46, .12)
                source_hash = gate.fingerprint('blockout-material-v1', short, repr(color))
            else:
                source_hash = map_hash if is_map else data_hash if name.endswith('/DA_GospelCampaign') else font_hash
            guard.record(self.index, name, source_hash, self.project / 'Content', is_map)
        self.index_path = self.project / 'Content/PathOfDawnGospel/generated-source-index.json'
        guard.save_index(self.index_path, self.index)
        self.report = {'status': 'passed', 'mode': 'reload-verification', 'required': sorted(gate.REQUIRED),
            'campaignSha256': guard.sha256_file(self.campaign_path), 'recipeSha256': guard.sha256_file(self.recipe_path),
            'generatorSha256': guard.sha256_file(self.generator), 'runtimeSourceSha256': runtime_hash,
            'sourceCommit': self.campaign['Source']['Commit'], 'previewQuestIds': [q['Id'] for q in temple]}
        self.report_path = self.project / 'Saved/PathOfDawnGospel/asset-verification-report.json'
        self.write_report()

    def write_report(self):
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(json.dumps(self.report), encoding='utf-8')

    def check(self): return gate.check(self.project, self.report_path, self.root)

    def test_consistent_fixture_passes_integrity_only_and_does_not_claim_graphics(self):
        result = self.check()
        self.assertEqual(result['packages'], 6)
        self.assertIn('no graphical validation', result['scope'])

    def test_generation_only_or_failed_evidence_cannot_unlock_cook(self):
        for change in ({'mode': 'generation'}, {'status': 'failed'}):
            original = copy.deepcopy(self.report)
            self.report.update(change); self.write_report()
            with self.assertRaisesRegex(ValueError, 'fresh-process'): self.check()
            self.report = original

    def test_generator_changes_invalidate_previous_editor_evidence(self):
        self.generator.write_bytes(self.generator.read_bytes() + b'\n# changed\n')
        with self.assertRaisesRegex(ValueError, 'generatorSha256'): self.check()

    def test_runtime_schema_changes_invalidate_previous_editor_evidence(self):
        source = self.project / 'Source/PathOfDawnUnreal/Public/DawnGospelData.h'
        source.write_bytes(source.read_bytes() + b'\n// changed\n')
        with self.assertRaisesRegex(ValueError, 'runtimeSourceSha256'): self.check()

    def test_edited_saved_package_is_rejected_without_rewriting_it(self):
        asset = self.project / 'Content/PathOfDawnGospel/Data/DA_GospelCampaign.uasset'
        edited = asset.read_bytes() + b'user edit'; asset.write_bytes(edited)
        with self.assertRaisesRegex(ValueError, 'changed after'): self.check()
        self.assertEqual(asset.read_bytes(), edited)

    def test_material_dependency_cannot_be_dropped_from_report_or_index(self):
        material = '/Game/PathOfDawnGospel/Materials/M_PreviewStone'
        self.report['required'].remove(material); self.write_report()
        with self.assertRaisesRegex(ValueError, 'omitted required'): self.check()
        self.report['required'].append(material); self.write_report()
        del self.index['assets'][material]; guard.save_index(self.index_path, self.index)
        with self.assertRaisesRegex(ValueError, 'baseline is incomplete'): self.check()

    def test_wrong_unity_commit_or_preview_scope_is_rejected(self):
        for field, value in [('sourceCommit', '0' * 40), ('previewQuestIds', ['wrong'])]:
            old = self.report[field]; self.report[field] = value; self.write_report()
            with self.subTest(field=field), self.assertRaises(ValueError): self.check()
            self.report[field] = old

    def test_stale_package_source_baseline_is_rejected_even_with_same_bytes(self):
        path = '/Game/PathOfDawnGospel/Data/DA_GospelCampaign'
        self.index['assets'][path]['source_sha256'] = '0' * 64
        guard.save_index(self.index_path, self.index)
        with self.assertRaisesRegex(ValueError, 'stale source'): self.check()


if __name__ == '__main__': unittest.main()
