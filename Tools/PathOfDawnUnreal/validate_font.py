#!/usr/bin/env python3
"""Check actual source font character coverage. Not a UMG layout/rendering test."""
import json
from pathlib import Path
from fontTools.ttLib import TTFont

root = Path(__file__).resolve().parents[2]
font_path = root / "SourceArt/PathOfDawnUnreal/Fonts/NotoSansKR.otf"
font = TTFont(font_path)
cmap = font.getBestCmap()
files = list((root / "Games/PathOfDawnUnreal/Source").rglob("*.cpp"))
files += [root / "SourceArt/PathOfDawnUnreal/Narrative/episode.json"]
used = set("".join(p.read_text(encoding="utf-8") for p in files))
korean = {c for c in used if "\uac00" <= c <= "\ud7a3" or "\u3130" <= c <= "\u318f"}
missing = sorted(c for c in korean if ord(c) not in cmap)
report = {"test": "Actual OTF Korean character coverage", "font": str(font_path.relative_to(root)),
          "unique_korean_characters": len(korean), "missing": missing, "passed": not missing,
          "unverified": ["Unreal font import", "UMG shaping", "small-window wrapping", "packaged glyph rendering"]}
out = root / "Docs/PathOfDawnUnreal/Evidence/font-validation.json"
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False))
raise SystemExit(bool(missing))
