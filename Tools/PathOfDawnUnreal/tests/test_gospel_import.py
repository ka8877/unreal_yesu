"""Execute real import/reload functions with a property-only fixture.

These tests preserve every authored field and model NAME_None's Python text.
They do not emulate UE, prove its API compatibility, or create real packages.
"""
import ast
import copy
import json
from pathlib import Path
import types
import unittest

ROOT = Path(__file__).resolve().parents[3]
GENERATOR = ROOT / 'Tools/PathOfDawnUnreal/generate_gospel_assets.py'
SOURCE = ROOT / 'SourceArt/PathOfDawnUnreal/Gospel'
DOCUMENT = json.loads((SOURCE / 'Campaign.json').read_text(encoding='utf-8'))
RECIPE = json.loads((SOURCE / 'TemplePreview.json').read_text(encoding='utf-8'))


class Name:
    def __init__(self, value): self.value = value
    def __str__(self): return self.value or 'None'


class PropertyRecord:
    def __init__(self): self.properties = {}; self.error = ''
    def set_editor_property(self, key, value):
        self.properties[key] = Name(value) if key in ('id', 'campaign_id', 'chapter_id', 'npc_id', 'reading_id') else value
    def get_editor_property(self, key): return self.properties[key]
    def validation_error(self): return self.error


class ImportFixture:
    def __init__(self, action='create', validation_error=''):
        self.action = action
        self.asset = PropertyRecord()
        self.asset.error = validation_error
        self.saved = []
        self.created = []
        self.BASE = '/Game/PathOfDawnGospel'
        data = self.BASE + '/Data/DA_GospelCampaign'
        self.ns = {'u': types.SimpleNamespace(
            DawnGospelReading=PropertyRecord, DawnGospelBeat=PropertyRecord,
            DawnGospelQuest=PropertyRecord, DawnGospelData=PropertyRecord, DataAssetFactory=PropertyRecord,
            DawnAssetTools=types.SimpleNamespace(localized_text=lambda _key, value: value, has_runtime_font=lambda _font: True)),
            'BASE': self.BASE, 'DATA': data, 'FONT': self.BASE + '/UI/F_Korean', 'FACE': self.BASE + '/UI/FF_Korean',
            'MAP': self.BASE + '/Maps/L_GospelTemplePreview', 'ROOT': ROOT,
            'TOOLS': types.SimpleNamespace(create_asset=self.create),
            'REPORT': {'preserved': []}, 'action_for': lambda *a, **k: self.action,
            'need': lambda path: self.asset if path == data else PropertyRecord(), 'save_asset': self.save,
            'guard': types.SimpleNamespace(sha256_file=lambda _path: 'font-hash')}
        tree = ast.parse(GENERATOR.read_text(encoding='utf-8'))
        names = {'localized', 'apply_fields', 'create_campaign', 'verify', 'fingerprint'}
        functions = [row for row in tree.body if isinstance(row, ast.FunctionDef) and row.name in names]
        if {row.name for row in functions} != names:
            raise AssertionError('Actual importer/reload functions missing')
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(GENERATOR), 'exec'), self.ns)
        import hashlib
        self.ns['hashlib'] = hashlib

    def create(self, *args): self.created.append(args); return self.asset
    def save(self, asset, *args): self.saved.append(args); return asset
    def run(self): return self.ns['create_campaign'](DOCUMENT, 'source-hash')
    def verify(self):
        self.ns['action_for'] = lambda *a, **k: 'preserve'
        expected_class = object()
        world = types.SimpleNamespace(get_world_settings=lambda: types.SimpleNamespace(get_editor_property=lambda _key: expected_class))
        levels, worlds = object(), object()
        actors = []
        for row in RECIPE['Markers']:
            actors.append(types.SimpleNamespace(tags=['GospelQuest:' + row['QuestId'], 'GospelNpc:' + row['NpcId']],
                get_actor_location=lambda p=row['Position']: types.SimpleNamespace(x=p[0], y=p[1], z=p[2])))
        self.ns['u'].LevelEditorSubsystem = levels
        self.ns['u'].UnrealEditorSubsystem = worlds
        self.ns['u'].DawnGospelGameMode = types.SimpleNamespace(static_class=lambda: expected_class)
        self.ns['u'].get_editor_subsystem = lambda cls: (types.SimpleNamespace(load_level=lambda _path: True)
            if cls is levels else types.SimpleNamespace(get_editor_world=lambda: world))
        self.ns['ACTORS'] = types.SimpleNamespace(get_all_level_actors=lambda: actors)
        return self.ns['verify'](DOCUMENT, RECIPE, 'data-hash', 'map-hash')


class GospelImportTests(unittest.TestCase):
    def test_all_authored_text_and_identity_fields_survive_import_and_reload(self):
        fixture = ImportFixture()
        asset = fixture.run()
        self.assertEqual(len(fixture.created), 1)
        self.assertEqual(len(fixture.saved), 1)
        self.assertEqual(len(asset.properties['quests']), 23)
        self.assertEqual(len(asset.properties['readings']), 19)
        self.assertEqual(sum(len(q.properties['beats']) for q in asset.properties['quests']), 81)
        fixture.verify()

    def test_empty_reading_names_rendered_as_none_are_not_false_reload_failures(self):
        fixture = ImportFixture(); fixture.run()
        empty = [row for row in fixture.asset.properties['quests'] if str(row.properties['reading_id']) == 'None']
        self.assertEqual(len(empty), 4)
        fixture.verify()

    def test_existing_owned_unchanged_asset_is_preserved_without_property_writes(self):
        fixture = ImportFixture(action='preserve')
        fixture.asset.properties['user-sentinel'] = 'preserved'
        fixture.run()
        self.assertEqual(fixture.asset.properties, {'user-sentinel': 'preserved'})
        self.assertFalse(fixture.created or fixture.saved)

    def test_existing_changed_data_refreshes_without_creating_second_asset(self):
        fixture = ImportFixture(action='refresh')
        fixture.run(); fixture.verify()
        self.assertFalse(fixture.created)
        self.assertEqual(len(fixture.saved), 1)

    def test_runtime_validation_failure_never_saves_invalid_data(self):
        fixture = ImportFixture(validation_error='invalid-source')
        with self.assertRaisesRegex(RuntimeError, 'invalid-source'): fixture.run()
        self.assertFalse(fixture.saved)

    def test_reload_rejects_modified_scripture_and_source_attribution(self):
        for property_name in ('text', 'source', 'reference', 'context'):
            fixture = ImportFixture(); fixture.run()
            fixture.asset.properties['readings'][0].properties[property_name] += ' changed'
            with self.subTest(property=property_name), self.assertRaisesRegex(RuntimeError, 'scripture differs'):
                fixture.verify()

    def test_reload_rejects_changed_voice_kind_scene_and_dialogue_text(self):
        for property_name in ('voice_key', 'kind', 'scene_title', 'text', 'reference', 'music_role'):
            fixture = ImportFixture(); fixture.run()
            fixture.asset.properties['quests'][0].properties['beats'][0].properties[property_name] += ' changed'
            with self.subTest(property=property_name), self.assertRaisesRegex(RuntimeError, 'story beat differs'):
                fixture.verify()

    def test_preview_recipe_targets_exact_ordered_temple_events_and_npcs(self):
        actual = [(row['QuestId'], row['NpcId']) for row in RECIPE['Markers']]
        expected = [(row['Id'], row['NpcId']) for row in DOCUMENT['Quests'] if row['ChapterId'] == 'temple']
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), 7)
        for row in RECIPE['Markers']:
            self.assertEqual(len(row['Position']), 3)


if __name__ == '__main__':
    unittest.main()
