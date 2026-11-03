"""Narrow editor contracts; fixture objects are not Unreal or graphics evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("motion_review_contract", TOOLS / "movement_review.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


def row(name, folder="Walk", kind="AnimSequence"):
    return {"name": name, "class": kind, "objectPath": "/Game/Fixture/Animations/" + folder + "/" + name + "." + name}


class PropertyObject:
    def __init__(self, **properties): self.properties = properties
    def get_editor_property(self, name): return self.properties[name]
    def set_editor_property(self, name, value): self.properties[name] = value


class Animation(PropertyObject): pass


class BlueprintAsset:
    def __init__(self, cls): self.cls = cls
    def generated_class(self): return self.cls


class MovementReviewTests(unittest.TestCase):
    def test_curated_selection_rejects_name_false_positives_and_prefers_basic_motions(self):
        rows = [row("M_relaxed_takedown_walk_B", "Interactions/Takedowns"),
                row("M_Neutral_AO_Stand", "AimOffset"), row("M_Neutral_Crouch_Stop_F", "Crouch"),
                row("M_Neutral_Crouch_Idle_Turn_090_L", "Crouch"),
                row("M_Relaxed_Walk_Stop_F_Lfoot"), row("M_Neutral_Walk_Loop_F"),
                row("M_Relaxed_Walk_Loop_F"), row("M_Relaxed_Walk_Turn_090_L_Lfoot"),
                row("M_Relaxed_Stand_Idle_Loop", "Idle"), row("M_Relaxed_Stand_Turn_090_L", "Idle")]
        selected = review.select_locomotion(rows, 1)
        self.assertEqual(selected["idle"][0]["name"], "M_Relaxed_Stand_Idle_Loop")
        self.assertEqual(selected["walk"][0]["name"], "M_Relaxed_Walk_Loop_F")
        self.assertEqual(selected["stop"][0]["name"], "M_Relaxed_Walk_Stop_F_Lfoot")
        self.assertEqual(selected["turn"][0]["name"], "M_Relaxed_Stand_Turn_090_L")
        self.assertFalse(review.select_locomotion(rows[:4])["walk"])

    def test_native_motion_checks_reject_additive_zero_length_and_mixed_skeletons(self):
        skeleton = SimpleNamespace(get_path_name=lambda: "/Game/Fixture/Skeleton.Skeleton")
        rows = [row("M_Relaxed_Stand_Idle_Loop", "Idle"), row("M_Relaxed_Walk_Loop_F"),
                row("M_Relaxed_Walk_Stop_F_Lfoot"), row("M_Relaxed_Stand_Turn_090_L", "Idle")]
        objects = {r["objectPath"]: Animation(skeleton=skeleton, additive_anim_type=0, sequence_length=1.0) for r in rows}
        unreal = SimpleNamespace(AnimSequence=Animation, AdditiveAnimationType=SimpleNamespace(AAT_NONE=0),
                                 EditorAssetLibrary=SimpleNamespace(load_asset=lambda path: objects[path]))
        report = {"curatedMotions": {}}
        review.check_motions(unreal, rows, report)
        self.assertEqual(len(report["curatedMotions"]), 4)
        objects[rows[1]["objectPath"]].properties["additive_anim_type"] = 1
        with self.assertRaisesRegex(RuntimeError, "additive"): review.check_motions(unreal, rows, {"curatedMotions": {}})
        objects[rows[1]["objectPath"]].properties.update(additive_anim_type=0, sequence_length=0)
        with self.assertRaisesRegex(RuntimeError, "zero duration"): review.check_motions(unreal, rows, {"curatedMotions": {}})
        objects[rows[1]["objectPath"]].properties.update(sequence_length=1, skeleton=SimpleNamespace(get_path_name=lambda: "/Game/Fixture/Other.Other"))
        with self.assertRaisesRegex(RuntimeError, "source skeleton"): review.check_motions(unreal, rows, {"curatedMotions": {}})

    def test_settings_reads_actual_sample_map_without_modifying_config(self):
        with TemporaryDirectory() as temp:
            project = Path(temp); (project / "Config").mkdir()
            path = project / "Config/DefaultEngine.ini"
            original = b'[/Script/EngineSettings.GameMapsSettings]\nGameDefaultMap=/Game/Fixture/Map.Map\nGlobalDefaultGameMode=/Game/Fixture/Mode.Mode_C\n+GameModeClassAliases=ignored\n'
            path.write_bytes(original)
            result = review.settings(project)
            self.assertEqual(result["map"], "/Game/Fixture/Map")
            self.assertEqual(path.read_bytes(), original)
            path.write_text('[OTHER]\nGameDefaultMap=/Game/Fixture/Map.Map\n')
            with self.assertRaisesRegex(RuntimeError, "existing /Game map"): review.settings(project)

    def test_incomplete_character_is_rejected_and_temporary_actor_is_removed(self):
        class Character: pass
        character = Character()
        cls = SimpleNamespace(get_path_name=lambda: "/Game/Fixture/Person.Person_C"); destroyed = []
        unreal = SimpleNamespace(Character=Character, Blueprint=BlueprintAsset, Vector=lambda *v: v, get_default_object=lambda _: character,
                                 EditorAssetLibrary=SimpleNamespace(load_asset=lambda _: BlueprintAsset(cls)))
        actors = SimpleNamespace(spawn_actor_from_class=lambda *args: character,
                                  destroy_actor=lambda actor: destroyed.append(actor) or True)
        candidates = [{"name": "Fixture_Metahuman", "class": "Blueprint", "objectPath": "/Game/Fixture/Person.Person"}]
        report = {"characterCandidates": []}
        with patch.object(review, "inspect_character", return_value=[{"component": "Mesh", "mesh": "/Game/Fixture/Mannequin.Mannequin", "skeleton": "OtherSkeleton", "animationClass": "FixtureAnim"}]):
            with self.assertRaisesRegex(review.CharacterAssemblyNotFound, "No existing complete Kellan Character"):
                review.find_character(unreal, candidates, actors, report)
        self.assertEqual(destroyed, [character])

    def test_owned_asset_is_reused_but_user_edits_and_unindexed_assets_are_preserved(self):
        pawn, mode = object(), object()
        cdo = PropertyObject(default_pawn_class=pawn)
        asset = object(); saved = []
        library = SimpleNamespace(does_asset_exist=lambda _: True, load_asset=lambda _: asset,
                                  get_metadata_tag=lambda *_: review.GENERATOR, load_blueprint_class=lambda _: mode,
                                  save_loaded_asset=lambda *_: saved.append(True))
        mode_path = "/Game/Fixture/Mode.Mode_C"
        # Generated UClass objects expose get_path_name natively.
        mode = SimpleNamespace(get_path_name=lambda: mode_path)
        library.load_blueprint_class = lambda _: mode
        unreal = SimpleNamespace(EditorAssetLibrary=library, get_default_object=lambda _: cdo)
        inputs = {"fixture": "stable"}; source_hash = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
        with TemporaryDirectory() as temp, patch.object(review, "package_hash", return_value="original"):
            state = Path(temp); report = {"preserved": [], "created": []}
            with self.assertRaisesRegex(RuntimeError, "Unindexed existing"):
                review.owned_mode(unreal, state, state, None, pawn, inputs, report)
            review.write_json(state / (source_hash + ".json"), {"sourceSha256": source_hash, "packageSha256": "original"})
            self.assertEqual(review.owned_mode(unreal, state, state, None, pawn, inputs, report), mode_path)
            self.assertFalse(saved)
            with patch.object(review, "package_hash", return_value="user-edited"):
                with self.assertRaisesRegex(RuntimeError, "Changed or unowned"):
                    review.owned_mode(unreal, state, state, None, pawn, inputs, report)
            self.assertFalse(saved)

    def test_loader_rejects_invalid_class_reference_without_executing_commands(self):
        with self.assertRaisesRegex(RuntimeError, "Unsupported class reference"):
            review.load_class(None, 'BlueprintGeneratedClass\'; run anything')
        with self.assertRaisesRegex(ValueError, "outside the generated"):
            review.package_hash(Path("."), "/Game/UserContent/Mode")

    def test_standalone_tool_pins_all_companions_and_rendered_launch_is_explicit(self):
        launcher = (TOOLS / "PrepareMovementReview.ps1").read_text(encoding="utf-8-sig")
        for name, path in {"movement_review.py": TOOLS / "movement_review.py", "inspect_sample.py": TOOLS / "inspect_sample.py", "WindowsProcessLauncher.cs": TOOLS.parent / "WindowsProcessLauncher.cs"}.items():
            self.assertIn("'" + name + "'='" + hashlib.sha256(path.read_bytes()).hexdigest() + "'", launcher)
        self.assertIn("MOTION_REVIEW_ASSETS_RELOADED", launcher)
        # Native preparation uses NullRHI. The separate persistent game launch
        # must render; it is never used as an automatic graphics-pass claim.
        launch_block = launcher.split('if (-not $PrepareOnly) {', 1)[1]
        self.assertIn("'-game'", launch_block)
        self.assertIn("if ($sampleEditor)", launch_block)
        self.assertNotIn("NullRHI", launch_block)
        self.assertNotIn("RenderOffscreen", launch_block)

    def appearance_fixture(self, redirect=False, include_named_character=False):
        class Actor: pass
        class Character(Actor): pass
        appearance, player = Actor(), Character()
        appearance_class = SimpleNamespace(get_path_name=lambda: "/Game/Fixture/BP_Kellan.BP_Kellan_C")
        player_class = SimpleNamespace(get_path_name=lambda: "/Game/Fixture/Avatar.Avatar_C")
        body = {"component": "Body", "mesh": "/Game/Fixture/Common/Body.Body", "skeleton": "HumanBodySkeleton", "animationClass": "GenericRetarget"}
        face = {"component": "Face", "mesh": "/Game/Fixture/Kellan/Face.Face", "skeleton": "FaceSkeleton", "animationClass": "FaceAnim"}
        rows = [{"name": "BP_Kellan", "class": "Blueprint", "objectPath": "/Game/Fixture/BP_Kellan.BP_Kellan"},
                {"name": "GenericAvatar", "class": "ObjectRedirector" if redirect else "Blueprint", "objectPath": "/Game/Fixture/OldAvatar.OldAvatar" if redirect else "/Game/Fixture/Avatar.Avatar"}]
        if include_named_character:
            rows.append({"name": "CBP_Kellan_Alias", "class": "Blueprint", "objectPath": "/Game/Fixture/Alias.Alias"})
        assets = {r["objectPath"]: BlueprintAsset(appearance_class if r["name"] == "BP_Kellan" else player_class) for r in rows}
        class Redirector(PropertyObject):
            def get_path_name(self): return "/Game/Fixture/OldAvatar.OldAvatar"
        if redirect:
            assets[rows[1]["objectPath"]] = Redirector(destination_object=BlueprintAsset(player_class))
        self.destroyed = []
        unreal = SimpleNamespace(Actor=Actor, Character=Character, Blueprint=BlueprintAsset, ObjectRedirector=Redirector,
            Vector=lambda *v: v, EditorAssetLibrary=SimpleNamespace(load_blueprint_class=lambda _: self.fail("Specialized class loading must not precede type validation"), load_asset=lambda path: assets[path]),
            get_default_object=lambda cls: appearance if cls is appearance_class else player)
        actors = SimpleNamespace(spawn_actor_from_class=lambda cls, _: appearance if cls is appearance_class else player,
                                 destroy_actor=lambda actor: self.destroyed.append(actor) or True)
        return unreal, actors, rows, player_class, lambda *_: [dict(body), dict(face)]

    def test_plain_appearance_actor_and_generic_named_character_are_kept_separate(self):
        unreal, actors, rows, player_class, parts = self.appearance_fixture()
        report = {"characterCandidates": []}
        with patch.object(review, "inspect_character", side_effect=parts):
            cls, path = review.find_character(unreal, rows, actors, report)
        self.assertIs(cls, player_class)
        self.assertEqual(path, "/Game/Fixture/Avatar.Avatar")
        self.assertEqual(report["characterCandidates"][0]["kind"], "appearanceActor")
        self.assertFalse(report["characterCandidates"][0]["isCharacter"])
        self.assertEqual(len(self.destroyed), 2)

    def test_redirected_character_is_resolved_and_shared_body_location_is_accepted(self):
        unreal, actors, rows, player_class, parts = self.appearance_fixture(redirect=True)
        report = {"characterCandidates": []}
        with patch.object(review, "inspect_character", side_effect=parts):
            cls, _ = review.find_character(unreal, rows, actors, report)
        self.assertIs(cls, player_class)
        self.assertEqual(report["referenceAppearance"]["bodyMeshes"], ["/Game/Fixture/Common/Body.Body"])

    def test_source_editor_review_does_not_save_assets_or_claim_binding(self):
        class Mode: pass
        parent = SimpleNamespace()
        registry = SimpleNamespace(search_all_assets=lambda _: None,
                                   get_assets_by_path=lambda *args, **kw: [{"class": "World", "objectPath": "/Game/Fixture/Map.Map"}])
        unreal = SimpleNamespace(SystemLibrary=SimpleNamespace(get_engine_version=lambda: "5.8.0-fixture"), GameModeBase=Mode,
            AssetRegistryHelpers=SimpleNamespace(get_asset_registry=lambda: registry), LevelEditorSubsystem=object(), EditorActorSubsystem=object(),
            get_editor_subsystem=lambda _: SimpleNamespace(load_level=lambda _: True), get_default_object=lambda _: Mode())
        for verify in (False, True):
            report = {"created": [], "graphicsVerified": False}
            with patch.object(review, "settings", return_value={"map": "/Game/Fixture/Map", "mode": "fixture", "configSha256": "stable"}), \
                    patch.object(review, "asset_row", side_effect=lambda r: r), patch.object(review, "check_motions"), \
                    patch.object(review, "load_class", return_value=parent), \
                    patch.object(review, "find_character", side_effect=review.CharacterAssemblyNotFound("No configured Character")), \
                    patch.object(review, "owned_mode") as save:
                review.run(unreal, Path("."), Path("."), report, verify=verify)
            save.assert_not_called()
            self.assertEqual(report["launch"]["mode"], "sampleEditor")
            self.assertEqual(report["launch"]["gameModeClass"], "")
            self.assertEqual(report["launch"]["sourcePawn"], "")
            self.assertTrue(report["launch"]["manualCharacterSelectionRequired"])
            self.assertFalse(report["graphicsVerified"])

    def test_non_blueprint_redirect_is_not_sent_to_native_error_logging_loader(self):
        class Redirector(PropertyObject):
            def get_path_name(self): return "/Game/Fixture/OldRig.OldRig"
        non_blueprint = object()
        redirect = Redirector(destination_object=non_blueprint)
        native_errors = []
        special_calls = []
        # Native UE logs an Error and returns None here; it does NOT raise a
        # Python exception. Commandlets later return 1 because errors exist.
        def specialized_loader(path):
            special_calls.append(path)
            native_errors.append("LogEditorAssetSubsystem: Error: LoadBlueprintClass failed: The asset is not a Blueprint.")
            return None
        unreal = SimpleNamespace(Blueprint=BlueprintAsset, ObjectRedirector=Redirector,
            EditorAssetLibrary=SimpleNamespace(load_asset=lambda _: redirect, load_blueprint_class=specialized_loader))
        result = review.blueprint_class(unreal, {"class": "ObjectRedirector", "objectPath": redirect.get_path_name()})
        self.assertIsNone(result)
        self.assertEqual(special_calls, [])
        self.assertEqual(native_errors, [])
        self.assertEqual(1 if native_errors else 0, 0)

    def test_missing_generated_class_is_reported_without_forcing_source_compilation(self):
        unreal = SimpleNamespace(Blueprint=BlueprintAsset, EditorAssetLibrary=SimpleNamespace(load_asset=lambda _: BlueprintAsset(None)))
        with self.assertRaisesRegex(RuntimeError, "no generated class; source asset preserved"):
            review.blueprint_class(unreal, {"class": "Blueprint", "objectPath": "/Game/Fixture/Unbuilt.Unbuilt"})


if __name__ == "__main__": unittest.main()
