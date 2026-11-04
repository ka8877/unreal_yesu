# Shared Gospel content export

`SourceArt/PathOfDawnUnreal/Gospel/Campaign.json` contains the reviewed Unity
story as engine-independent content: 23 objectives, 19 readings and 81 story
beats, including 51 birth-prologue beats. The temple preview covers the seven
objectives from `nazareth-departure` through `nazareth-return`.

The snapshot in `SourceReferences` was read from `ka8877/firstgame` at immutable
commit `808d8d1e1eeed908d8925398f80c7173653ef364`. `manifest.json` records each
original file's Git blob SHA, byte count and SHA-256. These are byte-exact C#
references, not copied Unity art, scenes, packages or executables. Existing Unity
development files and its public deployment are not changed by this exporter.

The exporter compiles and evaluates the original C# classes with the .NET 8 SDK's
Roslyn compiler. It calls `GospelStorybookCatalog.GetDetails` for every original
dialogue page; no story is extracted by regular expressions or rewritten in
Python. Scripture text, summary/dramatization labels, references, story-scene
metadata and stable voice cursors are retained. The original Unity progression
class is also executed through all objectives to verify that readings are only
discovered at event completion. This is a portable source test, not Unity or
Unreal graphical execution.

The offline export uses only the SDK reference assemblies and writes compiled
output to a temporary directory. It does not restore NuGet packages. Install a
.NET 8 SDK yourself or pass the existing SDK's `dotnet` executable:

```sh
python3 Tools/PathOfDawnUnreal/Gospel/export_campaign.py --dotnet /path/to/dotnet
python3 Tools/PathOfDawnUnreal/Gospel/export_campaign.py --dotnet /path/to/dotnet --check
```

`--check` recompiles and evaluates the same original C# and requires exact UTF-8
output bytes; it never updates the checked-in campaign. These checks need no SDK:

```sh
python3 Tools/PathOfDawnUnreal/Gospel/export_campaign.py --verify-sources-only
python3 Tools/PathOfDawnUnreal/Gospel/validate_campaign.py
python3 -m unittest discover -s Tools/PathOfDawnUnreal/tests -p test_gospel_content.py
```

The scripture credit and source links are preserved from the original catalogs.
An engine's use restrictions on Unity sample assets do not transfer to this
export: those assets are excluded entirely. Three-dimensional art, animation,
music and UI require their own suitable provenance and engine implementation.
JSON is an Editor authoring input; packaged Unreal runtime consumes cooked data
assets and does not read C#, Python, GitHub or this JSON file.
