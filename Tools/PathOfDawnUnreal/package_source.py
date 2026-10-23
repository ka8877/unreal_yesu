#!/usr/bin/env python3
"""Package authoring sources only. This never produces a playable Windows ZIP."""
import argparse, hashlib, zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument("--id", default="20261023")
args = parser.parse_args()
if not args.id or any(c not in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_-" for c in args.id):
    raise SystemExit("Invalid source bundle ID")
out = root / "Builds/PathOfDawnUnreal" / f"PathOfDawn-Source-{args.id}.zip"
if out.exists():
    raise SystemExit(f"Preserved existing bundle: {out}. Use another --id.")
files = []
for folder in ["Games/PathOfDawnUnreal", "SourceArt/PathOfDawnUnreal", "Tools/PathOfDawnUnreal", "Docs/PathOfDawnUnreal", "Streaming/PathOfDawnUnreal"]:
    for p in (root / folder).rglob("*"):
        if not p.is_file(): continue
        if any(x in p.parts for x in ["Binaries", "Intermediate", "Saved", "DerivedDataCache", "vendor", "runtime", "__pycache__", "node_modules"]): continue
        if p.name == "local.settings.json" or p.suffix in [".blend1", ".tmp"]: continue
        files.append(p)
files += [root / p for p in ["README.md", "AGENTS.md", ".gitignore", ".gitattributes", "Start-PathOfDawn.cmd", "Setup-PathOfDawn-PC.cmd", "Update-PathOfDawn.cmd"]]
out.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for p in sorted(files): archive.write(p, p.relative_to(root))
    archive.writestr("SOURCE-ONLY.txt", "AUTHORING SOURCE BUNDLE. No Windows executable. Unreal Editor compilation, asset generation, cooking and graphical validation are still required. See Docs/PathOfDawnUnreal/README.md.\n")
with zipfile.ZipFile(out) as archive:
    bad = archive.testzip()
    if bad: raise SystemExit(f"ZIP CRC failure: {bad}")
digest = hashlib.sha256(out.read_bytes()).hexdigest()
out.with_suffix(".zip.sha256").write_text(f"{digest}  {out.name}\n")
print(f"Source-only bundle: {out}\nFiles: {len(files)+1}; bytes: {out.stat().st_size}\nSHA256: {digest}\nZIP CRC: PASS. This is not a game execution test.")
