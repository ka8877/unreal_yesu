"""Real Unreal Editor import and fresh-process reload for the Gospel preview.

This does not produce screenshots or validate cinematic visual quality. Existing
Galilee packages are never touched. Edited Gospel packages stop generation.
"""
import hashlib
import json
import math
import sys
import traceback
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / 'Gospel'))
import gospel_asset_guard as guard
from validate_campaign import validate
from gospel_build_identity import runtime_source_sha256

ROOT = HERE.parents[1]
PROJECT = ROOT / 'Games/PathOfDawnUnreal'
SOURCE = ROOT / 'SourceArt/PathOfDawnUnreal/Gospel'
CONTENT = PROJECT / 'Content'
BASE = '/Game/PathOfDawnGospel'
DATA = BASE + '/Data/DA_GospelCampaign'
MAP = BASE + '/Maps/L_GospelTemplePreview'
FONT = BASE + '/UI/F_Korean'
FACE = BASE + '/UI/FF_Korean'
VERIFY = '-PODVerifyAssets' in u.SystemLibrary.get_command_line()
REPORT_DIR = PROJECT / 'Saved/PathOfDawnGospel'
REPORT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = REPORT_DIR / ('asset-verification-report.json' if VERIFY else 'asset-generation-report.json')
INDEX_PATH = CONTENT / 'PathOfDawnGospel/generated-source-index.json'
LIB = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
ACTORS = u.get_editor_subsystem(u.EditorActorSubsystem)
REPORT = {'status': 'running', 'mode': 'reload-verification' if VERIFY else 'generation',
          'stage': 'preflight', 'required': [DATA, MAP, FONT, FACE,
              BASE + '/Materials/M_PreviewStone', BASE + '/Materials/M_PreviewMarker'],
          'created': [], 'refreshed': [], 'preserved': [],
          'engineVersion': u.SystemLibrary.get_engine_version(),
          'graphicalSmoke': 'not-performed', 'visualQuality': 'development-blockout'}


def localized(key, text):
    return u.DawnAssetTools.localized_text('Gospel.' + key, str(text))


def need(path):
    asset = LIB.load_asset(path)
    if not asset:
        raise RuntimeError('Required asset missing: ' + path)
    return asset


def fingerprint(*chunks):
    result = hashlib.sha256()
    for chunk in chunks:
        data = chunk if isinstance(chunk, bytes) else str(chunk).encode('utf-8')
        result.update(len(data).to_bytes(8, 'big'))
        result.update(data)
    return result.hexdigest()


def action_for(path, source_hash, is_map=False):
    return guard.plan(path, source_hash, INDEX, CONTENT, LIB.does_asset_exist(path), is_map)


def record_saved(path, source_hash, action, is_map=False):
    guard.record(INDEX, path, source_hash, CONTENT, is_map)
    guard.save_index(INDEX_PATH, INDEX)
    REPORT['refreshed' if action == 'refresh' else 'created'].append(path)


def save_asset(asset, path, source_hash, action):
    LIB.set_metadata_tag(asset, 'PathOfDawnGospelSourceSHA256', source_hash)
    if not LIB.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError('Cannot save Gospel package: ' + path)
    record_saved(path, source_hash, action)
    return asset


def apply_fields(target, row, fields, text_fields=()):
    for source, prop in fields:
        value = row[source]
        if source in text_fields:
            value = localized(row['Id'] + '.' + source, value)
        target.set_editor_property(prop, value)


def create_campaign(document, source_hash):
    action = action_for(DATA, source_hash)
    if action == 'preserve':
        REPORT['preserved'].append(DATA)
        return need(DATA)
    if action == 'create':
        factory = u.DataAssetFactory()
        factory.set_editor_property('data_asset_class', u.DawnGospelData)
        asset = TOOLS.create_asset('DA_GospelCampaign', BASE + '/Data', u.DawnGospelData, factory)
        if not asset:
            raise RuntimeError('Gospel DataAsset creation failed')
    else:
        asset = need(DATA)
    readings = []
    for row in document['Readings']:
        item = u.DawnGospelReading()
        apply_fields(item, row, [('Id', 'id'), ('Title', 'title'), ('Reference', 'reference'),
                                ('Text', 'text'), ('Source', 'source'), ('Context', 'context')],
                     ('Title', 'Reference', 'Text', 'Source', 'Context'))
        readings.append(item)
    quests = []
    for row in document['Quests']:
        quest = u.DawnGospelQuest()
        apply_fields(quest, row, [('Id', 'id'), ('ChapterId', 'chapter_id'), ('Title', 'title'),
                                 ('Objective', 'objective'), ('NpcId', 'npc_id'), ('NpcName', 'npc_name'),
                                 ('ReadingId', 'reading_id'), ('IsPrologue', 'is_prologue')],
                     ('Title', 'Objective', 'NpcName'))
        beats = []
        for authored in row['Beats']:
            beat = u.DawnGospelBeat()
            apply_fields(beat, authored, [('Id', 'id'), ('Speaker', 'speaker'), ('Text', 'text'),
                                         ('Kind', 'kind'), ('Reference', 'reference'), ('VoiceKey', 'voice_key'),
                                         ('SceneTitle', 'scene_title'), ('Location', 'location'),
                                         ('TimeLabel', 'time_label'), ('MusicRole', 'music_role')],
                         ('Speaker', 'Text', 'Reference', 'SceneTitle', 'Location', 'TimeLabel'))
            beats.append(beat)
        quest.set_editor_property('beats', beats)
        quests.append(quest)
    for name, value in [('schema_version', document['SchemaVersion']), ('campaign_id', document['CampaignId']),
                        ('content_version', document['ContentVersion']),
                        ('title', localized('Title', document['Title'])),
                        ('scope_note', localized('ScopeNote', document['ScopeNote'])),
                        ('source_repository', document['Source']['Repository']),
                        ('source_commit', document['Source']['Commit']), ('readings', readings), ('quests', quests)]:
        asset.set_editor_property(name, value)
    error = asset.validation_error()
    if error:
        raise RuntimeError('Runtime Gospel data validation failed: ' + str(error))
    return save_asset(asset, DATA, source_hash, action)


def create_font():
    source = ROOT / 'SourceArt/PathOfDawnUnreal/Fonts/NotoSansKR.otf'
    source_hash = guard.sha256_file(source)
    face_action = action_for(FACE, source_hash)
    font_action = action_for(FONT, source_hash)
    if face_action == 'refresh' or font_action == 'refresh':
        raise RuntimeError('Font changed; review a new face/composite font path in Editor before replacing')
    if face_action == 'create':
        task = u.AssetImportTask()
        for key, value in [('filename', str(source)), ('destination_path', BASE + '/UI'),
                           ('destination_name', 'FF_Korean'), ('automated', True),
                           ('save', False), ('replace_existing', False), ('factory', u.FontFileImportFactory())]:
            task.set_editor_property(key, value)
        TOOLS.import_asset_tasks([task])
        save_asset(need(FACE), FACE, source_hash, face_action)
    else:
        REPORT['preserved'].append(FACE)
    if font_action == 'create':
        font = u.DawnAssetTools.create_composite_font(need(FACE), FONT)
        if not font:
            raise RuntimeError('Cannot create Korean composite font')
        save_asset(font, FONT, source_hash, font_action)
    else:
        REPORT['preserved'].append(FONT)


def spawn(cls, label, location, rotation=(0, 0, 0), scale=None, tags=()):
    actor = ACTORS.spawn_actor_from_class(cls, u.Vector(*location), u.Rotator(*rotation))
    if not actor:
        raise RuntimeError('Cannot spawn ' + label)
    actor.set_actor_label(label)
    actor.set_editor_property('tags', [u.Name('GospelPreviewGenerated')] + [u.Name(tag) for tag in tags])
    if scale:
        actor.set_actor_scale3d(u.Vector(*scale))
    return actor


def material(name, color):
    path = BASE + '/Materials/' + name
    digest = fingerprint('blockout-material-v1', name, repr(color))
    action = action_for(path, digest)
    if path not in REPORT['required']:
        REPORT['required'].append(path)
    if action == 'preserve':
        REPORT['preserved'].append(path)
        return need(path)
    asset = (TOOLS.create_asset(name, BASE + '/Materials', u.Material, u.MaterialFactoryNew())
             if action == 'create' else need(path))
    editing = u.MaterialEditingLibrary
    # Source changes are not currently authored; edited packages fail the guard.
    if action == 'refresh':
        raise RuntimeError('Material recipe changed; use a reviewed new material path')
    expression = editing.create_material_expression(asset, u.MaterialExpressionConstant3Vector, -200, 0)
    expression.set_editor_property('constant', u.LinearColor(*color, 1.0))
    if not editing.connect_material_property(expression, '', u.MaterialProperty.MP_BASE_COLOR):
        raise RuntimeError('Cannot connect blockout material color')
    editing.recompile_material(asset)
    return save_asset(asset, path, digest, action)


def static(label, mesh_path, location, scale, surface, collision=True):
    actor = spawn(u.StaticMeshActor, label, location, scale=scale)
    component = actor.static_mesh_component
    component.set_static_mesh(need(mesh_path))
    component.set_material(0, surface)
    component.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS if collision else u.CollisionEnabled.NO_COLLISION)
    return actor


def create_map(recipe, map_hash):
    action = action_for(MAP, map_hash, is_map=True)
    if action == 'preserve':
        REPORT['preserved'].append(MAP)
        return
    world = u.EditorLoadingAndSavingUtils.new_blank_map(False)
    if not world:
        raise RuntimeError('Cannot create new transient Gospel preview world')
    stone = material('M_PreviewStone', (.42, .37, .27))
    marker = material('M_PreviewMarker', (.70, .46, .12))
    cube = '/Engine/BasicShapes/Cube'
    static('PreviewFloor', cube, (1500, 0, -10), (54, 36, .2), stone)
    for label, location, scale in [
        ('NorthBoundary', (1500, 1760, 200), (54, .4, 4)),
        ('SouthBoundary', (1500, -1760, 200), (54, .4, 4)),
        ('WestBoundary', (-1160, 0, 200), (.4, 36, 4)),
        ('EastBoundary', (4160, 0, 200), (.4, 36, 4))]:
        static(label, cube, location, scale, stone)
    for x in (200, 1100, 2000, 2900, 3800):
        for y in (-1300, 1300):
            static('BlockoutColumn_%s_%s' % (x, y), '/Engine/BasicShapes/Cylinder',
                   (x, y, 220), (1.3, 1.3, 4.4), stone)
    for index, row in enumerate(recipe['Markers']):
        position = row['Position']
        spawn(u.TargetPoint, 'Meeting_%02d_%s' % (index + 1, row['QuestId']), position,
              tags=('GospelQuest:' + row['QuestId'], 'GospelNpc:' + row['NpcId']))
        static('MeetingPedestal_%02d' % (index + 1), '/Engine/BasicShapes/Cylinder',
               (position[0], position[1], 25), (1.2, 1.2, .5), marker, collision=False)
    spawn(u.PlayerStart, 'GospelPlayerStart', recipe['PlayerStart'])
    world.get_world_settings().set_editor_property('default_game_mode', u.DawnGospelGameMode.static_class())
    spawn(u.SkyAtmosphere, 'PreviewSky', (0, 0, 0))
    sun = spawn(u.DirectionalLight, 'PreviewSun', (0, 0, 1500), (-35, -25, 0))
    light = sun.get_component_by_class(u.DirectionalLightComponent)
    light.set_editor_property('intensity', 4.0)
    light.set_editor_property('atmosphere_sun_light', True)
    fill = spawn(u.SkyLight, 'PreviewFill', (0, 0, 1000))
    fill.get_component_by_class(u.SkyLightComponent).set_editor_property('intensity', 1.0)
    fill.get_component_by_class(u.SkyLightComponent).set_editor_property('real_time_capture', True)
    if not u.EditorLoadingAndSavingUtils.save_map(world, MAP):
        raise RuntimeError('Cannot save Gospel preview map')
    record_saved(MAP, map_hash, action, is_map=True)


def verify(document, recipe, data_hash, map_hash):
    for path in (DATA, FONT, FACE, MAP):
        expected = (map_hash if path == MAP else data_hash if path == DATA else
                    guard.sha256_file(ROOT / 'SourceArt/PathOfDawnUnreal/Fonts/NotoSansKR.otf'))
        if action_for(path, expected, is_map=path == MAP) != 'preserve':
            raise RuntimeError('Required generated asset is stale: ' + path)
    for name, color in [('M_PreviewStone', (.42, .37, .27)), ('M_PreviewMarker', (.70, .46, .12))]:
        if action_for(BASE + '/Materials/' + name, fingerprint('blockout-material-v1', name, repr(color))) != 'preserve':
            raise RuntimeError('Preview material is missing or stale: ' + name)
    asset = need(DATA)
    if str(asset.get_editor_property('source_commit')) != document['Source']['Commit']:
        raise RuntimeError('Reloaded Gospel source commit differs')
    if asset.validation_error():
        raise RuntimeError('Reloaded Gospel data failed C++ validation: ' + str(asset.validation_error()))
    # Compare complete imported text and attribution, not only list lengths.
    for source, loaded in zip(document['Readings'], asset.get_editor_property('readings')):
        for key, prop in [('Id', 'id'), ('Title', 'title'), ('Reference', 'reference'),
                          ('Text', 'text'), ('Source', 'source'), ('Context', 'context')]:
            if str(loaded.get_editor_property(prop)) != str(source[key]):
                raise RuntimeError('Reloaded scripture differs: ' + source['Id'] + '.' + key)
    rows = asset.get_editor_property('quests')
    if len(rows) != len(document['Quests']) or len(asset.get_editor_property('readings')) != len(document['Readings']):
        raise RuntimeError('Reloaded campaign count differs')
    for source, loaded in zip(document['Quests'], rows):
        for key, prop in [('Id', 'id'), ('ChapterId', 'chapter_id'), ('Title', 'title'), ('Objective', 'objective'),
                          ('NpcId', 'npc_id'), ('NpcName', 'npc_name'), ('ReadingId', 'reading_id')]:
            value = str(loaded.get_editor_property(prop))
            # FName("") is NAME_None; Python renders it as "None".
            if key == 'ReadingId' and source[key] == '' and value == 'None':
                value = ''
            if value != str(source[key]):
                raise RuntimeError('Reloaded quest differs: ' + source['Id'] + '.' + key)
        beats = loaded.get_editor_property('beats')
        if len(beats) != len(source['Beats']) or loaded.get_editor_property('is_prologue') != source['IsPrologue']:
            raise RuntimeError('Reloaded quest structure differs: ' + source['Id'])
        for original, beat in zip(source['Beats'], beats):
            for key, prop in [('Id', 'id'), ('Speaker', 'speaker'), ('Text', 'text'), ('Kind', 'kind'),
                              ('Reference', 'reference'), ('VoiceKey', 'voice_key'), ('SceneTitle', 'scene_title'),
                              ('Location', 'location'), ('TimeLabel', 'time_label'), ('MusicRole', 'music_role')]:
                if str(beat.get_editor_property(prop)) != str(original[key]):
                    raise RuntimeError('Reloaded story beat differs: ' + original['Id'] + '.' + key)
    if not u.DawnAssetTools.has_runtime_font(need(FONT)):
        raise RuntimeError('Reloaded Korean font has no runtime typeface')
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not levels.load_level(MAP):
        raise RuntimeError('Cannot reload Gospel preview map')
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    if world.get_world_settings().get_editor_property('default_game_mode') != u.DawnGospelGameMode.static_class():
        raise RuntimeError('Gospel preview uses the wrong game mode')
    actors = ACTORS.get_all_level_actors()
    for row in recipe['Markers']:
        quest_tag = 'GospelQuest:' + row['QuestId']
        npc_tag = 'GospelNpc:' + row['NpcId']
        matches = [actor for actor in actors if quest_tag in [str(tag) for tag in actor.tags]]
        if len(matches) != 1 or npc_tag not in [str(tag) for tag in matches[0].tags]:
            raise RuntimeError('Missing/duplicate/wrong NPC marker: ' + row['QuestId'])
        location = matches[0].get_actor_location()
        if sum((actual - expected) ** 2 for actual, expected in zip(
                (location.x, location.y, location.z), row['Position'])) > 1.0:
            raise RuntimeError('Quest marker position differs: ' + row['QuestId'])
    REPORT['previewQuestIds'] = [row['QuestId'] for row in recipe['Markers']]


def run():
    global INDEX
    document = json.loads((SOURCE / 'Campaign.json').read_text(encoding='utf-8'))
    errors = validate(document)
    if errors:
        raise RuntimeError('Gospel content validation failed: ' + '; '.join(errors))
    recipe = json.loads((SOURCE / 'TemplePreview.json').read_text(encoding='utf-8'))
    temple = [row for row in document['Quests'] if row['ChapterId'] == 'temple']
    if recipe['Map'] != MAP or [(q['Id'], q['NpcId']) for q in temple] != [(q['QuestId'], q['NpcId']) for q in recipe['Markers']]:
        raise RuntimeError('Preview recipe does not match the actual ordered temple quests')
    for row in recipe['Markers']:
        if len(row['Position']) != 3 or any(type(x) not in (int, float) or not math.isfinite(x) for x in row['Position']):
            raise RuntimeError('Invalid 3D preview marker')
    INDEX = guard.load_index(INDEX_PATH)
    runtime_hash = runtime_source_sha256(ROOT)
    data_hash = fingerprint((SOURCE / 'Campaign.json').read_bytes(), Path(__file__).read_bytes(), runtime_hash)
    map_hash = fingerprint((SOURCE / 'TemplePreview.json').read_bytes(),
                           json.dumps([(q['Id'], q['NpcId']) for q in temple]), Path(__file__).read_bytes())
    REPORT.update(campaignSha256=guard.sha256_file(SOURCE / 'Campaign.json'), generatorSha256=guard.sha256_file(__file__),
                  runtimeSourceSha256=runtime_hash,
                  recipeSha256=guard.sha256_file(SOURCE / 'TemplePreview.json'), sourceCommit=document['Source']['Commit'])
    if not VERIFY:
        REPORT['stage'] = 'campaign-import'
        create_campaign(document, data_hash)
        REPORT['stage'] = 'font'
        create_font()
        REPORT['stage'] = 'map'
        create_map(recipe, map_hash)
    REPORT['stage'] = 'persisted-reference-validation'
    verify(document, recipe, data_hash, map_hash)
    REPORT['status'] = 'passed'
    REPORT['stage'] = 'complete'


try:
    run()
except Exception as error:
    REPORT.update(status='failed', error=str(error), traceback=traceback.format_exc())
    u.log_error(REPORT['traceback'])
finally:
    REPORT_PATH.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
if REPORT['status'] != 'passed':
    raise RuntimeError(REPORT.get('error', 'Gospel generation failed'))
