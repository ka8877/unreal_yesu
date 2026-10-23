"""Portable tests of the actual narrative-import function, without Unreal.

The small fixture below models only the Texture2D-versus-SoftObjectPath property
constraint observed in the user's UE 5.8.4 traceback and records write boundaries.
It does not implement Unreal, validate other engine APIs, create packages, or
replace the separate fresh-editor reload verification.
"""
import ast
import hashlib
import json
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GENERATOR = ROOT / 'Tools/PathOfDawnUnreal/generate_demo_assets.py'
SOURCE = ROOT / 'SourceArt/PathOfDawnUnreal'
DOCUMENT = json.loads((SOURCE / 'Narrative/episode.json').read_text(encoding='utf-8'))
BASE = '/Game/PathOfDawn'
IMAGE_IDS = sorted({row[field] for row in DOCUMENT['Nodes']
                    for field in ('Portrait', 'Illustration') if row.get(field)})


def extracted_functions():
    """Execute source functions directly; never import the editor-only module."""
    tree = ast.parse(GENERATOR.read_text(encoding='utf-8'), filename=str(GENERATOR))
    names = {'localized', 'create_narrative'}
    functions = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in functions} != names:
        raise AssertionError('Narrative import functions were not found')
    return compile(ast.Module(body=functions, type_ignores=[]), str(GENERATOR), 'exec')


class PropertyRecord:
    def __init__(self):
        self.properties = {}

    def set_editor_property(self, name, value):
        self.properties[name] = value


class Texture2DFixture:
    def __init__(self, image_id):
        self.image_id = image_id


class DialogueNodeFixture(PropertyRecord):
    def set_editor_property(self, name, value):
        if name in ('portrait', 'illustration') and not isinstance(value, Texture2DFixture):
            raise TypeError('SoftObjectProperty requires a Texture2D object')
        super().set_editor_property(name, value)


class ImportFixture:
    def __init__(self, action='create', validation_error=''):
        self.action = action
        self.validation_error = validation_error
        self.asset = PropertyRecord()
        self.asset.properties['sentinel'] = 'existing user data'
        self.created = []
        self.saved = []
        self.metadata = []
        self.lookups = []
        self.textures = {BASE + '/Illustrations/' + name: Texture2DFixture(name)
                         for name in IMAGE_IDS}
        self.source_hash = hashlib.sha256((SOURCE / 'Narrative/episode.json').read_bytes()).hexdigest()
        self.report = {'preserved': []}
        self.namespace = dict(
            BASE=BASE, SOURCE=SOURCE, REPORT=self.report, json=json,
            source_plan=lambda _file, _path: (self.action, self.asset, self.source_hash),
            save_source_asset=self.save, need=self.need,
            TOOLS=types.SimpleNamespace(create_asset=self.create),
            LIB=types.SimpleNamespace(set_metadata_tag=self.tag),
            u=types.SimpleNamespace(
                Texture2D=Texture2DFixture, DawnDialogueNode=DialogueNodeFixture,
                DawnChoice=PropertyRecord, DataAssetFactory=PropertyRecord,
                DawnNarrativeData=PropertyRecord,
                DawnAssetTools=types.SimpleNamespace(
                    localized_text=lambda key, value: (key, value),
                    validate_narrative=lambda _asset: self.validation_error)),
        )
        exec(extracted_functions(), self.namespace)

    def need(self, path):
        self.lookups.append(path)
        if path not in self.textures:
            raise RuntimeError('Required asset missing: ' + path)
        return self.textures[path]

    def create(self, name, path, asset_class, factory):
        self.created.append((name, path, asset_class, factory))
        self.asset = asset_class()
        return self.asset

    def tag(self, asset, key, value):
        self.metadata.append((asset, key, value))

    def save(self, asset, path, source_file, source_hash, action):
        self.saved.append((asset, path, source_file, source_hash, action))
        return asset

    def run(self):
        return self.namespace['create_narrative']()


class NarrativeImportContractTests(unittest.TestCase):
    def test_authored_nodes_use_typed_images_and_retain_text_choices_metadata(self):
        fixture = ImportFixture()
        result = fixture.run()
        rows = result.properties['nodes']
        self.assertEqual(len(rows), 34)
        self.assertEqual(len(IMAGE_IDS), 7)
        self.assertEqual(len(fixture.created), 1)
        self.assertEqual(len(fixture.saved), 1)
        self.assertEqual(result.properties['content_version'], DOCUMENT['ContentVersion'])
        self.assertEqual(set(fixture.lookups), set(fixture.textures))
        for authored, converted in zip(DOCUMENT['Nodes'], rows):
            props = converted.properties
            self.assertEqual(props['id'], authored['Id'])
            self.assertEqual(props['text'], (authored['TextKey'], authored['Text']))
            self.assertEqual(props['speaker'][1], authored['Speaker'])
            self.assertEqual(props['repeat_text'][1], authored.get('RepeatText', ''))
            self.assertEqual(props['display_note'][1], authored.get('DisplayNote', ''))
            self.assertEqual(props['next_node'], authored.get('NextNode', ''))
            self.assertEqual(props['content_kind'], authored['ContentKind'])
            self.assertEqual(props['scripture_reference'], authored['ScriptureReference'])
            self.assertEqual(props['source_note'], authored['SourceNote'])
            for field in ('Portrait', 'Illustration'):
                if authored.get(field):
                    self.assertIs(props[field.lower()], fixture.textures[BASE + '/Illustrations/' + authored[field]])
                else:
                    self.assertNotIn(field.lower(), props)
            expected_choices = [(c['Id'], (c['TextKey'], c['Text']), c['NextNode'])
                                for c in authored.get('Choices', [])]
            actual_choices = [(c.properties['id'], c.properties['text'], c.properties['next_node'])
                              for c in props['choices']]
            self.assertEqual(actual_choices, expected_choices)
        self.assertEqual(fixture.saved[0][3], fixture.source_hash)

    def test_missing_image_never_saves_partial_narrative(self):
        for image_id in IMAGE_IDS:
            with self.subTest(image=image_id):
                fixture = ImportFixture()
                del fixture.textures[BASE + '/Illustrations/' + image_id]
                with self.assertRaisesRegex(RuntimeError, 'Required asset missing'):
                    fixture.run()
                self.assertEqual(fixture.saved, [])
                self.assertEqual(fixture.metadata, [])

    def test_wrong_image_type_never_saves_partial_narrative(self):
        for image_id in IMAGE_IDS:
            with self.subTest(image=image_id):
                fixture = ImportFixture()
                fixture.textures[BASE + '/Illustrations/' + image_id] = PropertyRecord()
                with self.assertRaisesRegex(TypeError, 'Expected Texture2D'):
                    fixture.run()
                self.assertEqual(fixture.saved, [])
                self.assertEqual(fixture.metadata, [])

    def test_preserved_assets_are_returned_without_rewrite_or_image_lookup(self):
        for action in ('preserve', 'preserve_user_edit', 'preserve_untracked'):
            with self.subTest(action=action):
                fixture = ImportFixture(action=action)
                existing = fixture.asset
                self.assertIs(fixture.run(), existing)
                self.assertEqual(existing.properties, {'sentinel': 'existing user data'})
                self.assertEqual(fixture.created, [])
                self.assertEqual(fixture.saved, [])
                self.assertEqual(fixture.metadata, [])
                self.assertEqual(fixture.lookups, [])
                self.assertEqual(fixture.report['preserved'], [BASE + '/Narrative/DA_DawnNarrative'])

    def test_refresh_reuses_asset_and_saves_only_after_conversion(self):
        fixture = ImportFixture(action='refresh')
        existing = fixture.asset
        self.assertIs(fixture.run(), existing)
        self.assertEqual(fixture.created, [])
        self.assertEqual(len(fixture.saved), 1)
        self.assertEqual(fixture.saved[0][4], 'refresh')
        self.assertEqual(len(existing.properties['nodes']), 34)

    def test_engine_validator_rejection_is_propagated_without_save(self):
        fixture = ImportFixture(validation_error='fixture validation rejection')
        with self.assertRaisesRegex(RuntimeError, 'Narrative validation: fixture validation rejection'):
            fixture.run()
        self.assertEqual(fixture.saved, [])


if __name__ == '__main__':
    print('Portable narrative-import contract tests; no Unreal engine, package creation, or rendering is exercised.', flush=True)
    unittest.main(verbosity=2)
