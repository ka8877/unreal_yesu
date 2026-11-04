#!/usr/bin/env python3
"""Check the real OTF against Gospel content and UI text, without rendering it."""
import json
from pathlib import Path
from fontTools.ttLib import TTFont


def main():
    root = Path(__file__).resolve().parents[3]
    font_path = root / 'SourceArt/PathOfDawnUnreal/Fonts/NotoSansKR.otf'
    files = [root / 'SourceArt/PathOfDawnUnreal/Gospel/Campaign.json']
    files += list((root / 'Games/PathOfDawnUnreal/Source/PathOfDawnUnreal').rglob('*Gospel*.cpp'))
    used = set(''.join(path.read_text(encoding='utf-8') for path in files))
    required = {c for c in used if '\uac00' <= c <= '\ud7a3' or '\u3130' <= c <= '\u318f'}
    with TTFont(font_path) as font:
        cmap = font.getBestCmap()
        missing = sorted(c for c in required if ord(c) not in cmap)
    print(json.dumps({'test': 'Gospel source Korean glyph coverage', 'files': len(files),
                      'uniqueKoreanCharacters': len(required), 'missing': missing,
                      'passed': not missing, 'unverified': ['Editor font import', 'UMG layout', 'actual rendering']},
                     ensure_ascii=False))
    return int(bool(missing))


if __name__ == '__main__':
    raise SystemExit(main())
