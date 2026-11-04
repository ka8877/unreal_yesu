"""Disk ownership checks for real Gospel Editor packages; no Unreal emulation."""
import hashlib
import json
import os
import re
from pathlib import Path

KIND = 'PathOfDawn.GospelGeneratedIndex'


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def package_hash(asset_path, content_dir, is_map=False):
    if not re.fullmatch(r'/Game/PathOfDawnGospel/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+', asset_path):
        raise ValueError('Expected a Gospel package path without traversal or object suffix')
    stem = Path(content_dir).absolute() / asset_path[len('/Game/'):]
    main_extension = '.umap' if is_map else '.uasset'
    root = Path(content_dir).absolute()
    if any(parent.is_symlink() for parent in (stem.parent, *stem.parents) if parent == root or root in parent.parents):
        raise ValueError('Generated package parent cannot be a symbolic link')
    paths = [stem.with_suffix(ext) for ext in (main_extension, '.uexp', '.ubulk', '.uptnl')]
    if any(path.is_symlink() for path in paths):
        raise ValueError('Generated package cannot be a symbolic link: ' + asset_path)
    if not paths[0].is_file():
        if any(path.exists() for path in paths[1:]):
            raise ValueError('Orphan package sidecars must be preserved: ' + asset_path)
        return None
    digest = hashlib.sha256()
    for extension in (main_extension, '.uexp', '.ubulk', '.uptnl'):
        path = stem.with_suffix(extension)
        if path.is_symlink():
            raise ValueError('Generated package cannot be a symbolic link: ' + str(path))
        if path.is_file():
            digest.update(extension.encode('ascii'))
            digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def load_index(path):
    path = Path(path)
    if not path.exists():
        return {'kind': KIND, 'schema': 1, 'assets': {}}
    value = json.loads(path.read_text(encoding='utf-8'))
    if (not isinstance(value, dict) or value.get('kind') != KIND or
            type(value.get('schema')) is not int or value.get('schema') != 1 or
            not isinstance(value.get('assets'), dict)):
        raise ValueError('Gospel ownership index is invalid; preserve it and recover its original baseline')
    for name, row in value['assets'].items():
        if not isinstance(row, dict) or any(not re.fullmatch(r'[0-9a-f]{64}', str(row.get(k, '')))
                                            for k in ('source_sha256', 'package_sha256')):
            raise ValueError('Invalid ownership hash for ' + name)
    return value


def save_index(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def plan(asset_path, source_hash, index, content_dir, exists, is_map=False):
    if not re.fullmatch(r'[0-9a-f]{64}', source_hash):
        raise ValueError('Invalid source digest')
    # Also validates the package path before making any creation decision.
    actual = package_hash(asset_path, content_dir, is_map)
    if not exists:
        if actual is not None:
            raise ValueError('Package exists on disk but is not registered: ' + asset_path)
        return 'create'
    entry = index['assets'].get(asset_path)
    if not entry or actual is None or actual != entry['package_sha256']:
        raise ValueError('Preserved existing/edited package without matching ownership baseline: ' + asset_path)
    if source_hash == entry['source_sha256']:
        return 'preserve'
    if is_map:
        raise ValueError('Map recipe changed; preserve this map and generate a reviewed new map path: ' + asset_path)
    return 'refresh'


def record(index, asset_path, source_hash, content_dir, is_map=False):
    if not re.fullmatch(r'[0-9a-f]{64}', source_hash):
        raise ValueError('Invalid source digest')
    actual = package_hash(asset_path, content_dir, is_map)
    if actual is None:
        raise ValueError('Editor did not save a readable package: ' + asset_path)
    index['assets'][asset_path] = {'source_sha256': source_hash, 'package_sha256': actual}
