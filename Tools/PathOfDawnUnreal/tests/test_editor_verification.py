"""Portable contracts for the actual Editor verification/material functions.

These fixtures deliberately expose only Python editor properties for static
meshes, and the documented unnamed first Sine input. They reproduce the two
v6 failures without pretending to load Unreal, compile shaders or save packages.
"""
import ast
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GENERATOR = ROOT / 'Tools/PathOfDawnUnreal/generate_demo_assets.py'
BASE = '/Game/PathOfDawn'
MAP = BASE + '/Maps/L_Galilee'


def load_functions(names, namespace):
    tree = ast.parse(GENERATOR.read_text(encoding='utf-8'), filename=str(GENERATOR))
    nodes = [node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in nodes} != set(names):
        raise AssertionError('Expected generator functions not found')
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(GENERATOR), 'exec'), namespace)


class EditorObject:
    def __init__(self, path='', **properties):
        self.path = path
        self.properties = properties

    def get_editor_property(self, name):
        return self.properties[name]

    def set_editor_property(self, name, value):
        self.properties[name] = value

    def get_path_name(self):
        return self.path


class StaticMeshComponentFixture(EditorObject):
    """Intentionally has no get_static_mesh method: UE Python uses a property."""


class InteractableFixture(EditorObject):
    pass


class BlueprintFixture(EditorObject):
    def generated_class(self):
        return self.properties['class']


class VerifyFixture:
    def __init__(self):
        tree = ast.parse(GENERATOR.read_text(encoding='utf-8'))
        lists = {node.targets[0].id: ast.literal_eval(node.value) for node in tree.body
                 if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                 and node.targets[0].id in ('IMAGES', 'MODELS', 'SOUNDS')}
        self.report = {'status': 'running'}
        self.namespace = dict(BASE=BASE, MAP=MAP, SOURCE=ROOT / 'SourceArt/PathOfDawnUnreal',
                              REPORT=self.report, VISUAL_SOURCE=ROOT / 'SourceArt/PathOfDawnUnreal/VisualV8', **lists)
        load_functions({'path_model', 'source_entries', 'verify'}, self.namespace)
        paths = [path for _, path in self.namespace['source_entries']()]
        paths += [MAP, BASE + '/UI/F_Korean', BASE + '/Cinematics/LS_Arrival', BASE + '/Environment/M_LakeWater', BASE + '/Environment/M_ShoreSurface']
        self.assets = {path: EditorObject(path) for path in paths}
        self.body = StaticMeshComponentFixture(static_mesh=self.assets[BASE + '/Characters/SM_Traveler'])
        self.traveler_class = EditorObject(BASE + '/Characters/BP_Traveler.BP_Traveler_C')
        self.traveler_class.cdo = EditorObject(traveler_body=self.body)
        self.game_class = EditorObject(BASE + '/Characters/BP_DawnGameMode.BP_DawnGameMode_C')
        self.game_class.cdo = EditorObject(default_pawn_class=self.traveler_class)
        self.assets[BASE + '/Characters/BP_Traveler'] = BlueprintFixture(**{'class': self.traveler_class})
        self.assets[BASE + '/Characters/BP_DawnGameMode'] = BlueprintFixture(**{'class': self.game_class})
        self.world_settings = EditorObject(default_game_mode=self.game_class)
        self.world = types.SimpleNamespace(get_world_settings=lambda: self.world_settings)
        self.load_ok = True
        self.font_ok = True
        self.narrative_error = ''
        self.source_action = 'preserve'
        self.visual_revision = 'v8'
        self.actors = [InteractableFixture(stable_id=name, mesh=StaticMeshComponentFixture(static_mesh=EditorObject(name)))
                       for name in ('Net', 'Boat', 'Stone', 'Simon', 'Jesus', 'Village')]
        self.namespace.update(
            need=self.need,
            LIB=types.SimpleNamespace(get_metadata_tag=lambda asset, key: self.visual_revision),
            source_plan=lambda file, path: (self.source_action, self.need(path), 'fixture-hash'),
            LEVELS=types.SimpleNamespace(load_level=lambda path: self.load_ok),
            ACTORS=types.SimpleNamespace(get_all_level_actors=lambda: self.actors),
            u=types.SimpleNamespace(
                DawnInteractable=InteractableFixture,
                UnrealEditorSubsystem=object(),
                get_editor_subsystem=lambda cls: types.SimpleNamespace(get_editor_world=lambda: self.world),
                get_default_object=lambda cls: cls.cdo,
                DawnAssetTools=types.SimpleNamespace(
                    validate_narrative=lambda data: self.narrative_error,
                    has_runtime_font=lambda font: self.font_ok)))

    def need(self, path):
        if path not in self.assets:
            raise RuntimeError('Required asset missing: ' + path)
        return self.assets[path]

    def run(self):
        self.namespace['verify']()


class MaterialFixture:
    def __init__(self, fail_connection=None, preserved=False):
        self.connections = []
        self.expressions = []
        self.compiled = []
        self.saved = []
        self.fail_connection = fail_connection
        self.material = EditorObject('fixture-water')
        self.namespace = dict(
            BASE=BASE,
            existing=lambda path: self.material if preserved else None,
            TOOLS=types.SimpleNamespace(create_asset=lambda *args: self.material),
            owned=self.save,
            LIB=types.SimpleNamespace(set_metadata_tag=lambda *args: None),
            u=types.SimpleNamespace(
                Material=EditorObject, MaterialFactoryNew=EditorObject,
                LinearColor=lambda *values: values,
                MaterialExpressionConstant3Vector='vector', MaterialExpressionConstant='constant',
                MaterialExpressionTime='time', MaterialExpressionSine='sine',
                MaterialExpressionMultiply='multiply',
                MaterialExpressionTextureCoordinate='uv', MaterialExpressionPanner='panner',
                MaterialExpressionTextureSample='sample',
                MaterialSamplerType=types.SimpleNamespace(SAMPLERTYPE_NORMAL='normal', SAMPLERTYPE_COLOR='color'),
                MaterialProperty=types.SimpleNamespace(MP_BASE_COLOR='base', MP_ROUGHNESS='roughness',
                                                       MP_WORLD_POSITION_OFFSET='wpo', MP_NORMAL='normal'),
                MaterialEditingLibrary=types.SimpleNamespace(
                    create_material_expression=self.expression,
                    connect_material_property=self.property_connection,
                    connect_material_expressions=self.expression_connection,
                    recompile_material=lambda material: self.compiled.append(material))))
        load_functions({'require_material_link', 'make_material'}, self.namespace)

    def expression(self, material, kind, x, y):
        expression = EditorObject(kind=kind)
        self.expressions.append(expression)
        return expression

    def result(self):
        return len(self.connections) != self.fail_connection

    def property_connection(self, source, output, target):
        self.connections.append(('property', source, output, target))
        return self.result()

    def expression_connection(self, source, output, target, input_name):
        self.connections.append(('expression', source, output, target, input_name))
        # Epic documents the empty name as the first input. The Sine in the
        # user's log rejects 'Input'; do not accept invented input names here.
        accepted = input_name == '' if target.properties['kind'] in ('sine','panner','sample') else input_name in ('A', 'B')
        return accepted and self.result()

    def save(self, material):
        self.saved.append(material)
        return material

    def run(self, water=True, normal=None, albedo=None):
        return self.namespace['make_material']('M_LakeWater', (.12, .24, .26), .28, water, normal, albedo)


class EditorVerificationContractTests(unittest.TestCase):
    def test_old_visual_map_cannot_be_certified_as_v8(self):
        fixture = VerifyFixture()
        fixture.visual_revision = ''
        with self.assertRaisesRegex(RuntimeError, 'Older or untracked visual asset preserved'):
            fixture.run()

    def test_full_verification_accepts_property_only_mesh_components(self):
        fixture = VerifyFixture()
        self.assertFalse(hasattr(fixture.body, 'get_static_mesh'))
        fixture.run()
        self.assertEqual(fixture.report['stable_ids'], ['Net', 'Boat', 'Stone', 'Simon', 'Jesus', 'Village'])
        self.assertEqual(fixture.report['player_references']['body_mesh'], BASE + '/Characters/SM_Traveler')
        self.assertIn(MAP, fixture.report['required'])

    def test_missing_required_asset_or_stale_source_rejected(self):
        fixture = VerifyFixture()
        del fixture.assets[BASE + '/Cinematics/LS_Arrival']
        with self.assertRaisesRegex(RuntimeError, 'Required asset missing'):
            fixture.run()
        for action in ('create', 'refresh'):
            with self.subTest(action=action):
                fixture = VerifyFixture()
                fixture.source_action = action
                with self.assertRaisesRegex(RuntimeError, 'stale or missing'):
                    fixture.run()

    def test_missing_or_wrong_player_mesh_rejected(self):
        for mesh in (None, EditorObject('wrong-mesh')):
            with self.subTest(mesh=mesh):
                fixture = VerifyFixture()
                fixture.body.properties['static_mesh'] = mesh
                with self.assertRaisesRegex(RuntimeError, 'TravelerBody must reference SM_Traveler'):
                    fixture.run()

    def test_wrong_game_mode_or_default_pawn_rejected(self):
        fixture = VerifyFixture()
        fixture.game_class.cdo.properties['default_pawn_class'] = None
        with self.assertRaisesRegex(RuntimeError, 'default pawn must reference BP_Traveler'):
            fixture.run()
        fixture = VerifyFixture()
        fixture.world_settings.properties['default_game_mode'] = None
        with self.assertRaisesRegex(RuntimeError, 'default game mode must reference BP_DawnGameMode'):
            fixture.run()

    def test_unloadable_map_and_missing_editor_world_rejected(self):
        fixture = VerifyFixture()
        fixture.load_ok = False
        with self.assertRaisesRegex(RuntimeError, 'Saved map cannot be loaded'):
            fixture.run()
        fixture = VerifyFixture()
        fixture.world = None
        with self.assertRaisesRegex(RuntimeError, 'No Editor world'):
            fixture.run()

    def test_missing_duplicate_or_empty_interactable_rejected(self):
        fixture = VerifyFixture()
        fixture.actors.pop()
        with self.assertRaisesRegex(RuntimeError, 'Expected one stable actor Village'):
            fixture.run()
        fixture = VerifyFixture()
        fixture.actors.append(fixture.actors[0])
        with self.assertRaisesRegex(RuntimeError, 'Expected one stable actor Net'):
            fixture.run()
        fixture = VerifyFixture()
        fixture.actors[0].properties['mesh'].properties['static_mesh'] = None
        with self.assertRaisesRegex(RuntimeError, 'Empty interactable mesh'):
            fixture.run()

    def test_narrative_and_font_rejection_propagate(self):
        fixture = VerifyFixture()
        fixture.narrative_error = 'fixture narrative rejected'
        with self.assertRaisesRegex(RuntimeError, 'fixture narrative rejected'):
            fixture.run()
        fixture = VerifyFixture()
        fixture.font_ok = False
        with self.assertRaisesRegex(RuntimeError, 'Composite font has no typeface'):
            fixture.run()


class MaterialGraphContractTests(unittest.TestCase):
    def test_ground_uses_stationary_normal_and_separate_color_sampler(self):
        fixture=MaterialFixture()
        fixture.run(water=False,normal=EditorObject('normal'),albedo=EditorObject('color'))
        pan=next(e for e in fixture.expressions if e.properties['kind']=='panner')
        self.assertEqual((pan.properties['speed_x'],pan.properties['speed_y']),(0.,0.))
        samples=[e for e in fixture.expressions if e.properties['kind']=='sample']
        self.assertEqual([e.properties['sampler_type'] for e in samples],['normal','color'])
        for failure_index in (6,7):
            rejected=MaterialFixture(fail_connection=failure_index)
            with self.assertRaisesRegex(RuntimeError,'Material connection failed'):
                rejected.run(water=False,normal=EditorObject('normal'),albedo=EditorObject('color'))
            self.assertEqual(rejected.saved,[])

    def test_water_normal_uses_normal_sampler_and_checked_connections(self):
        normal=EditorObject('T_LakeNormal')
        fixture=MaterialFixture()
        fixture.run(normal=normal)
        samples=[e for e in fixture.expressions if e.properties['kind']=='sample']
        self.assertEqual(len(samples),1)
        self.assertIs(samples[0].properties['texture'],normal)
        self.assertEqual(samples[0].properties['sampler_type'],'normal')
        self.assertEqual(fixture.connections[-1],('property',samples[0],'RGB','normal'))
        for failure_index in range(7,10):
            rejected=MaterialFixture(fail_connection=failure_index)
            with self.assertRaisesRegex(RuntimeError,'Material connection failed'):
                rejected.run(normal=normal)
            self.assertEqual(rejected.saved,[])

    def test_water_connects_unnamed_sine_input_before_save(self):
        fixture = MaterialFixture()
        self.assertIs(fixture.run(), fixture.material)
        self.assertEqual(len(fixture.connections), 6)
        sine_links = [c for c in fixture.connections if c[0] == 'expression' and c[3].properties['kind'] == 'sine']
        self.assertEqual(len(sine_links), 1)
        self.assertEqual(sine_links[0][-1], '')
        self.assertEqual(fixture.saved, [fixture.material])
        self.assertEqual(fixture.compiled, [fixture.material])

    def test_each_failed_connection_prevents_compile_and_save(self):
        for failure_index in range(1, 7):
            with self.subTest(connection=failure_index):
                fixture = MaterialFixture(fail_connection=failure_index)
                with self.assertRaisesRegex(RuntimeError, 'Material connection failed'):
                    fixture.run()
                self.assertEqual(fixture.saved, [])
                self.assertEqual(fixture.compiled, [])

    def test_existing_material_is_preserved_without_rewrite(self):
        fixture = MaterialFixture(preserved=True)
        self.assertIs(fixture.run(), fixture.material)
        self.assertEqual(fixture.expressions, [])
        self.assertEqual(fixture.connections, [])
        self.assertEqual(fixture.saved, [])
        self.assertEqual(fixture.compiled, [])


if __name__ == '__main__':
    print('Portable Editor verification/material contracts; no Unreal loading, shader compile, package save or rendering.', flush=True)
    unittest.main(verbosity=2)
