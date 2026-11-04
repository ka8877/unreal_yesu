#!/usr/bin/env python3
"""Verify fresh Editor evidence and real on-disk package baselines before Cook.

This reads Editor reports. It never creates Unreal packages, claims graphics
success, or replaces the fresh-process Editor verification pass.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
import gospel_asset_guard as guard
from gospel_build_identity import runtime_source_sha256

BASE = '/Game/PathOfDawnGospel'
REQUIRED = {BASE + '/Data/DA_GospelCampaign', BASE + '/Maps/L_GospelTemplePreview',
            BASE + '/UI/F_Korean', BASE + '/UI/FF_Korean',
            BASE + '/Materials/M_PreviewStone', BASE + '/Materials/M_PreviewMarker'}


def fingerprint(*chunks):
    # Same framed source identity as the real Editor generator.
    import hashlib
    result = hashlib.sha256()
    for chunk in chunks:
        data = chunk if isinstance(chunk, bytes) else str(chunk).encode('utf-8')
        result.update(len(data).to_bytes(8, 'big'))
        result.update(data)
    return result.hexdigest()


def check(project, report_path, root=ROOT):
    project, root = Path(project), Path(root)
    source = root / 'SourceArt/PathOfDawnUnreal/Gospel'
    campaign_path, recipe_path = source / 'Campaign.json', source / 'TemplePreview.json'
    generator = root / 'Tools/PathOfDawnUnreal/generate_gospel_assets.py'
    campaign = json.loads(campaign_path.read_text(encoding='utf-8'))
    recipe = json.loads(recipe_path.read_text(encoding='utf-8'))
    report = json.loads(Path(report_path).read_text(encoding='utf-8'))
    if report.get('status') != 'passed' or report.get('mode') != 'reload-verification':
        raise ValueError('Successful fresh-process Gospel reload report required')
    expected = {'campaignSha256': guard.sha256_file(campaign_path),
                'recipeSha256': guard.sha256_file(recipe_path),
                'generatorSha256': guard.sha256_file(generator), 'sourceCommit': campaign['Source']['Commit'],
                'runtimeSourceSha256': runtime_source_sha256(root)}
    for key, value in expected.items():
        if report.get(key) != value:
            raise ValueError('Fresh Gospel Editor evidence differs from current source: ' + key)
    temple = [row for row in campaign['Quests'] if row['ChapterId'] == 'temple']
    ids = [row['Id'] for row in temple]
    if report.get('previewQuestIds') != ids or ids != [row['QuestId'] for row in recipe['Markers']]:
        raise ValueError('Editor evidence has the wrong preview scope')
    if not REQUIRED.issubset(report.get('required', [])):
        raise ValueError('Editor report omitted required Gospel packages')
    index = guard.load_index(project / 'Content/PathOfDawnGospel/generated-source-index.json')
    if not REQUIRED.issubset(index['assets']):
        raise ValueError('Gospel package baseline is incomplete')
    data_hash = fingerprint(campaign_path.read_bytes(), generator.read_bytes(), expected['runtimeSourceSha256'])
    map_hash = fingerprint(recipe_path.read_bytes(), json.dumps([(q['Id'], q['NpcId']) for q in temple]), generator.read_bytes())
    font_hash = guard.sha256_file(root / 'SourceArt/PathOfDawnUnreal/Fonts/NotoSansKR.otf')
    for path, entry in index['assets'].items():
        if guard.package_hash(path, project / 'Content', is_map=path.endswith('/L_GospelTemplePreview')) != entry['package_sha256']:
            raise ValueError('Saved Gospel package changed after Editor validation: ' + path)
    for path in REQUIRED:
        if '/Materials/' in path:
            name = path.rsplit('/', 1)[1]
            color = (.42, .37, .27) if name == 'M_PreviewStone' else (.70, .46, .12)
            expected_hash = fingerprint('blockout-material-v1', name, repr(color))
        else:
            expected_hash = map_hash if path.endswith('/L_GospelTemplePreview') else data_hash if path.endswith('/DA_GospelCampaign') else font_hash
        if index['assets'][path]['source_sha256'] != expected_hash:
            raise ValueError('Gospel package baseline uses stale source: ' + path)
    return {'status': 'passed', 'scope': 'Editor report and disk-package integrity; no graphical validation',
            'packages': len(index['assets']), **expected}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=ROOT / 'Games/PathOfDawnUnreal')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = args.report or args.project / 'Saved/PathOfDawnGospel/asset-verification-report.json'
    try:
        print(json.dumps(check(args.project, report), ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('Gospel package verification failed: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
