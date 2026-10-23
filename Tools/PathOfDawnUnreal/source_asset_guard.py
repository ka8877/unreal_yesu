"""Small filesystem-only guard for the demo's generated import packages.

No Unreal import is performed here. The editor calls this before a targeted
refresh and records a baseline only after the real package has been saved.
"""
import hashlib
import json
import os
from pathlib import Path

INDEX_SCHEMA = 1
INDEX_KIND = 'PathOfDawn.GeneratedSourceIndex'


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def package_sha256(asset_path, content_dir):
    """Hash the real editor package and any adjacent bulk data; never create it."""
    if not asset_path.startswith('/Game/PathOfDawn/') or '.' in asset_path.rsplit('/', 1)[-1]:
        raise ValueError('Expected a PathOfDawn /Game package path without object suffix')
    stem = Path(content_dir) / asset_path[len('/Game/'):]
    main = stem.with_suffix('.uasset')
    if not main.is_file():
        return None
    digest = hashlib.sha256()
    for extension in ('.uasset', '.uexp', '.ubulk', '.uptnl'):
        path = stem.with_suffix(extension)
        if path.is_file():
            digest.update(extension.encode('ascii'))
            digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def load_index(path):
    path = Path(path)
    if not path.exists():
        return {'kind': INDEX_KIND, 'schema': INDEX_SCHEMA, 'assets': {}}
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('kind') != INDEX_KIND or value.get('schema') != INDEX_SCHEMA or not isinstance(value.get('assets'), dict):
        raise ValueError('Generated source index is corrupt or incompatible; preserve it and recover the checked-in baseline')
    return value


def save_index(path, value):
    """Atomic index replacement; package creation/import remains the editor's job."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w', encoding='utf-8', newline='\n') as output:
        json.dump(value, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write('\n')
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def refresh_decision(source_hash, package_hash, entry, exists, imported_source_hash=None):
    """Return action/reason without mutating files or blessing unknown baselines."""
    if not exists:
        return 'create', 'No existing asset'
    if package_hash is None:
        return 'conflict', 'Existing asset has no readable on-disk package baseline'
    if not entry or not entry.get('source_sha256') or not entry.get('package_sha256'):
        if imported_source_hash == source_hash:
            return 'preserve_untracked', 'Source is unchanged, but package has no generated hash baseline; later source changes require review'
        return 'conflict', 'Missing generated baseline; source/package ownership cannot be verified'
    if source_hash == entry['source_sha256']:
        if package_hash == entry['package_sha256']:
            return 'preserve', 'Source and generated package are unchanged'
        return 'preserve_user_edit', 'Source is unchanged; preserve edited package and keep original generated baseline'
    if package_hash != entry['package_sha256']:
        return 'conflict', 'Both authoritative source and generated package changed; preserve user edits'
    return 'refresh', 'Source changed and package still exactly matches generated baseline'
