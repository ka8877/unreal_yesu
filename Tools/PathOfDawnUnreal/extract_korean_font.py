#!/usr/bin/env python3
"""Reproduce font face extraction on Debian with fonts-noto-cjk/fontTools installed."""
from pathlib import Path
import shutil
from fontTools.ttLib import TTCollection
root = Path(__file__).resolve().parents[2]
out = root / "SourceArt/PathOfDawnUnreal/Fonts"
out.mkdir(parents=True, exist_ok=True)
target = out / "NotoSansKR.otf"
if target.exists():
    raise SystemExit("Font already exists; preserved. Remove only your generated copy to regenerate.")
collection = TTCollection("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
font = next(f for f in collection.fonts if f["name"].getDebugName(1) == "Noto Sans CJK KR")
font.save(target)
shutil.copyfile("/usr/share/doc/fonts-noto-cjk/copyright", out / "LICENSE-Debian-Noto.txt")
print(target)
