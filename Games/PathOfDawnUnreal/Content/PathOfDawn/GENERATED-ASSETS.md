This directory intentionally contains no fabricated Unreal binary assets.
Run BuildEditor.ps1 then GenerateDemoAssets.ps1 on a supported Unreal 5.8 Windows host.
The generator imports SourceArt assets and creates real maps, Blueprints, materials,
font, dialogue DataAsset and Sequencer assets through the Editor API. It refuses to
overwrite existing user-owned assets. BuildDemo must refuse packaging without them.
