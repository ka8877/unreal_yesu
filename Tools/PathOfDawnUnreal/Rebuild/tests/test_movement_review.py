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
        cls = object(); destroyed = []
        unreal = SimpleNamespace(Character=Character, Vector=lambda *v: v, get_default_object=lambda _: character,
                                 EditorAssetLibrary=SimpleNamespace(load_blueprint_class=lambda _: cls))
        actors = SimpleNamespace(spawn_actor_from_class=lambda *args: character,
                                  destroy_actor=lambda actor: destroyed.append(actor) or True)
        candidates = [{"name": "Fixture_Metahuman", "class": "Blueprint", "objectPath": "/Game/Fixture/Person.Person"}]
        report = {"characterCandidates": []}
        with patch.object(review, "inspect_character", return_value=[{"mesh": "/Game/Fixture/Mannequin.Mannequin", "animationClass": "FixtureAnim"}]):
            with self.assertRaisesRegex(RuntimeError, "No existing complete Kellan Character"):
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
        game_line = next(line for line in launcher.splitlines() if "$values=@($gameEditor" in line)
        self.assertIn("'-game'", game_line)
        self.assertNotIn("NullRHI", game_line)
        self.assertNotIn("RenderOffscreen", game_line)


if __name__ == "__main__": unittest.main()
