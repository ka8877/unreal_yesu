# Path of Dawn workspace

## Latest user direction — 2026-11-04

Develop two separately distributed editions of the same Gospel journey: Unity `ka8877/firstgame` supplies the 2D/HD-2D edition and shared story/gameplay reference; this repository supplies a high-quality 3D Unreal edition. Follow `Docs/PathOfDawnUnreal/DualEditionPlan.md` for the product direction and `GospelImplementation.md` in that directory for the implemented source and host steps. Pinned content export, portable progression, typed Unreal runtime/UI, separate Editor generation and package preparation are implemented in source. Unreal compilation, actual Editor/game execution, cinematic final assets/BGM and hosted preview remain unverified or unfinished; do not report source implementation as a playable published build.

The reviewed Unity story is birth → twelve-year-old temple visit → adult baptism, with 23 objectives, 19 readings and a 51-screen birth prologue. Preserve this chronology, stable IDs and the distinction between scripture quotation, summary and dramatization. Earlier Luke 5-only/traveler/rewind requirements below describe the existing prototype; they do not restrict the new shared-story edition. Preserve its source/assets/saves as a separate content version. Do not add its fictional branching or rewind to the shared campaign by default.

Reuse story/rules through an explicit, versioned engine-independent content contract, not Unity runtime code or Unity-only licensed assets. Keep Unity, the unrelated FantasyCards project and existing public releases unchanged. Shared story does not imply shared save slots or implemented cross-save.

The user explicitly selected cinematic realistic/semi-realistic 3D on 2026-11-04. This is the confirmed Unreal art direction: natural human proportions and movement, believable skin/hair/cloth and environment materials, intentional lighting/cameras, actual BGM and polished UI. Use animated skeletal characters and distinguish twelve-year-old and adult portrayals. Existing static meshes and temporary audio are prototype assets, not accepted final quality. Validate all quality claims in the actual engine on a GPU host.

Prefer a dedicated build host producing packaged binaries and a fixed browser preview URL via Pixel Streaming; testers should not compile project sources. The current local updater remains a developer fallback. Hosted deployment, UE5.8/PixelStreaming2 compatibility, session-save isolation and actual video/audio/input require verification. No managed GPU service or build-host connection has been provisioned by the review.

## Existing prototype and implementation rules

Only the new PathOfDawnUnreal directories belong to this task. Preserve other projects and user edits. The initial repository was empty on 2026-10-23.

Target: stable Unreal Engine 5.8; exact installed patch must be recorded by CheckEnvironment.ps1 before building. No Unreal installation or Windows toolchain exists in the current Debian cloud workspace. Never describe source checks or Blender renders as Unreal execution.

User reports v7 launched on their Windows UE 5.8.4 PC. Current v8 visual sources are under SourceArt/PathOfDawnUnreal/VisualV8; old Illustrations/Models remain historical originals and are not the active import set. v8 title/dialogue/result UMG, 7 illustrations, 15 meshes and 3 surface textures require fresh local Editor generation and graphical validation. Existing maps/materials are protected by revision metadata, so use a fresh extracted source folder for this art overhaul. No engine reinstall is required.

Runtime C++ owns narrative/world/save state. Editor automation owns only newly generated, tagged assets and must not overwrite user-edited assets. Never write text disguised as .uasset/.umap. Runtime must not depend on Python, MCP, raw source JSON or external image URLs.

The existing Galilee prototype uses Korean UI and Luke 5:1–11 only; the new campaign follows the latest shared-story direction above. Clearly distinguish original adaptation from scripture. No combat/cards. Warm dawn, sand/linen/olive/faded blue palette remains the prototype palette, subject to the new edition's art direction. Generated portraits are creative representations, not historical likenesses. Record asset provenance and temporary geometry.

Build order: CheckEnvironment → BuildEditor → GenerateDemoAssets → TestDemo → BuildDemo → actual graphical smoke → PackageDemo. Record unperformed checks explicitly. Run portable core and content validation in this workspace. Keep output and secrets out of Git.

Independent agents must own separate files. Shared binary assets and editor mutations are serialized. See Docs/PathOfDawnUnreal for architecture, evidence and unresolved requirements.

GitHub distribution: public ka8877/unreal_yesu is the source origin. Bootstrap/SyncAndPlay fetch an immutable commit into C:\PathOfDawn\versions\source-<12 SHA chars>, preserve existing sources and launch only after successful local Windows build. Source art uses ordinary Git (largest file <17 MB) so GitHub archives contain real assets; .uasset/.umap LFS rules remain for future generated assets. Never claim GitHub hosts Unreal rendering. Browser testing remains loopback at 127.0.0.1:8080; public media and Windows updater execution need actual verification.

Windows host-tool regression tests can run on the public repository's GitHub Actions Windows runner without Unreal/GPU. Use `.github/workflows/windows-launcher-tests.yml` for launcher changes before publishing them to main. Start-Process redirects alone do not isolate inherited ancestor pipes: persistent Windows processes use WindowsProcessLauncher.cs with an explicit handle list. Do not replace this with broad handle inheritance. A Windows launcher CI pass is not an Unreal or media test.
