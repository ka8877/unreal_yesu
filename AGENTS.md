# Path of Dawn workspace

Only the new PathOfDawnUnreal directories belong to this task. Preserve other projects and user edits. The initial repository was empty on 2026-10-23.

Target: stable Unreal Engine 5.8; exact installed patch must be recorded by CheckEnvironment.ps1 before building. No Unreal installation or Windows toolchain exists in the current Debian cloud workspace. Never describe source checks or Blender renders as Unreal execution.

User reports v7 launched on their Windows UE 5.8.4 PC. Current v8 visual sources are under SourceArt/PathOfDawnUnreal/VisualV8; old Illustrations/Models remain historical originals and are not the active import set. v8 title/dialogue/result UMG, 7 illustrations, 15 meshes and 3 surface textures require fresh local Editor generation and graphical validation. Existing maps/materials are protected by revision metadata, so use a fresh extracted source folder for this art overhaul. No engine reinstall is required.

Runtime C++ owns narrative/world/save state. Editor automation owns only newly generated, tagged assets and must not overwrite user-edited assets. Never write text disguised as .uasset/.umap. Runtime must not depend on Python, MCP, raw source JSON or external image URLs.

Use Korean UI, Luke 5:1–11 only, clearly distinguish original adaptation from scripture. No combat/cards. Warm dawn, sand/linen/olive/faded blue palette. Generated portraits are creative representations, not historical likenesses. Record asset provenance and temporary geometry.

Build order: CheckEnvironment → BuildEditor → GenerateDemoAssets → TestDemo → BuildDemo → actual graphical smoke → PackageDemo. Record unperformed checks explicitly. Run portable core and content validation in this workspace. Keep output and secrets out of Git.

Independent agents must own separate files. Shared binary assets and editor mutations are serialized. See Docs/PathOfDawnUnreal for architecture, evidence and unresolved requirements.

GitHub distribution: public ka8877/unreal_yesu is the source origin. Bootstrap/SyncAndPlay fetch an immutable commit into C:\PathOfDawn\versions\source-<12 SHA chars>, preserve existing sources and launch only after successful local Windows build. Source art uses ordinary Git (largest file <17 MB) so GitHub archives contain real assets; .uasset/.umap LFS rules remain for future generated assets. Never claim GitHub hosts Unreal rendering. Browser testing remains loopback at 127.0.0.1:8080; public media and Windows updater execution need actual verification.
