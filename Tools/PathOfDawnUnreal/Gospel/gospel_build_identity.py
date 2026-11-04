"""Source identity binding for Gospel Editor evidence and packaged candidates."""
import hashlib
from pathlib import Path


def runtime_source_sha256(root):
    root = Path(root)
    runtime = root / 'Games/PathOfDawnUnreal/Source/PathOfDawnUnreal'
    files = [runtime / 'Core/GospelState.h', runtime / 'PathOfDawnUnreal.Build.cs']
    files += sorted((runtime / 'Public').glob('DawnGospel*.h'))
    files += sorted((runtime / 'Private').glob('DawnGospel*.cpp'))
    if len(files) < 15 or any(not path.is_file() for path in files):
        raise ValueError('Gospel runtime source set is missing or incomplete')
    digest = hashlib.sha256()
    for path in sorted(files):
        relative = path.relative_to(root).as_posix().encode('utf-8')
        digest.update(len(relative).to_bytes(4, 'big'))
        digest.update(relative)
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()
