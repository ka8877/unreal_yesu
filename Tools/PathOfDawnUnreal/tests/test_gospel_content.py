"""Mutation tests of the actual exported Gospel data and import contract.

These are content checks, not Unity/Unreal execution or graphical tests.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
VALIDATOR_PATH = ROOT / "Tools/PathOfDawnUnreal/Gospel/validate_campaign.py"
CAMPAIGN_PATH = ROOT / "SourceArt/PathOfDawnUnreal/Gospel/Campaign.json"
SOURCE_DIRECTORY = ROOT / "Tools/PathOfDawnUnreal/Gospel/SourceReferences"
spec = importlib.util.spec_from_file_location("gospel_campaign_validator", VALIDATOR_PATH)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class GospelContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = json.loads(CAMPAIGN_PATH.read_text(encoding="utf-8"))

    def assert_rejected(self, edit, message):
        altered = copy.deepcopy(self.original)
        edit(altered)
        errors = validator.validate(altered)
        self.assertTrue(any(message in error for error in errors), errors)

    def test_actual_export_is_valid_without_mutation(self):
        before = copy.deepcopy(self.original)
        self.assertEqual([], validator.validate(self.original))
        self.assertEqual(before, self.original)

    def test_pinned_reference_bytes_match_git_blobs_and_manifest(self):
        manifest = json.loads((SOURCE_DIRECTORY / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(validator.SOURCE_REPOSITORY, manifest["repository"])
        self.assertEqual(validator.SOURCE_COMMIT, manifest["commit"])
        self.assertGreaterEqual(len(manifest["files"]), 10)
        self.assertEqual(len(manifest["files"]), len({row["path"] for row in manifest["files"]}))
        for row in manifest["files"]:
            path = Path(row["path"])
            self.assertEqual(path.name, str(path), "Snapshot references must be plain C# filenames")
            content = (SOURCE_DIRECTORY / path).read_bytes()
            self.assertEqual(row["bytes"], len(content), row["path"])
            self.assertEqual(row["sha256"], hashlib.sha256(content).hexdigest(), row["path"])
            git_blob = b"blob " + str(len(content)).encode("ascii") + b"\0" + content
            self.assertEqual(row["git_blob_sha"], hashlib.sha1(git_blob).hexdigest(), row["path"])

    def test_immutable_source_is_required(self):
        self.assert_rejected(lambda data: data["Source"].update(Commit="main"), "immutable commit")
        self.assert_rejected(lambda data: data["Source"].update(Repository="other/repository"), "reviewed Unity repository")

    def test_integer_versions_cannot_be_booleans(self):
        self.assert_rejected(lambda data: data.update(SchemaVersion=True), "SchemaVersion")
        self.assert_rejected(lambda data: data.update(ContentVersion=True), "ContentVersion")

    def test_missing_quote_reference_is_rejected(self):
        def edit(data):
            quote = next(beat for quest in data["Quests"] for beat in quest["Beats"] if beat["Kind"] == "Scripture")
            quote["Reference"] = ""
        self.assert_rejected(edit, ".Reference")

    def test_translation_credit_is_preserved(self):
        self.assert_rejected(lambda data: data["Readings"][0].update(Source="Unknown translation"), "publisher credit")

    def test_verified_passage_url_is_preserved(self):
        self.assert_rejected(lambda data: data["Readings"][0].update(Source="성경전서 개역한글판 · 대한성서공회"), "verified passage URL")

    def test_direct_quotation_cannot_cite_an_unrelated_passage(self):
        def edit(data):
            quote = next(beat for quest in data["Quests"] for beat in quest["Beats"] if beat["Kind"] == "Scripture")
            quote["Reference"] = "마태복음 3:15"
        self.assert_rejected(edit, "outside the quest's retained passage")

    def test_duplicate_objective_and_reading_ids_are_rejected(self):
        self.assert_rejected(lambda data: data["Quests"][1].update(Id=data["Quests"][0]["Id"]), "Duplicate quest ID")
        self.assert_rejected(lambda data: data["Readings"][1].update(Id=data["Readings"][0]["Id"]), "Duplicate reading ID")

    def test_chronology_cannot_be_reordered(self):
        def edit(data):
            data["Quests"][15], data["Quests"][16] = data["Quests"][16], data["Quests"][15]
        self.assert_rejected(edit, "Quest IDs/order")

    def test_unknown_and_repeated_rewards_are_rejected(self):
        self.assert_rejected(lambda data: data["Quests"][0].update(ReadingId="unwritten-passage"), "unknown reading")
        self.assert_rejected(lambda data: data["Quests"][1].update(ReadingId=data["Quests"][0]["ReadingId"]), "discovery order")

    def test_unknown_kind_and_mixed_quote_labels_are_rejected(self):
        self.assert_rejected(lambda data: data["Quests"][0]["Beats"][0].update(Kind="ScriptureAndFiction"), ".Kind")

    def test_invented_words_cannot_be_labelled_scripture(self):
        def edit(data):
            quote = next(beat for quest in data["Quests"] for beat in quest["Beats"] if beat["Kind"] == "Scripture")
            quote["Text"] = "This invented dialogue is not part of the retained scripture."
        self.assert_rejected(edit, "retained quotation")

    def test_summary_cannot_silently_become_a_direct_quotation(self):
        self.assert_rejected(lambda data: data["Quests"][0]["Beats"][0].update(Kind="Scripture"), "retained quotation")

    def test_malformed_collections_fail_with_diagnostics(self):
        for value in (None, [], 1, "campaign"):
            self.assertTrue(validator.validate(value))
        self.assert_rejected(lambda data: data.update(Quests="not an array"), "Quests must be an array")
        self.assert_rejected(lambda data: data["Quests"].__setitem__(0, None), "expected an object")
        self.assert_rejected(lambda data: data["Readings"].__setitem__(0, []), "expected an object")
        self.assert_rejected(lambda data: data["Quests"][0].update(Beats={}), "nonempty array")

    def test_extra_authoring_commands_and_disclosed_book_state_are_rejected(self):
        self.assert_rejected(lambda data: data["Quests"][0].update(Execute="anything"), "unexpected=['Execute']")
        self.assert_rejected(lambda data: data["Readings"][0].update(IsDiscovered=True), "IsDiscovered")

    def test_birth_details_and_voice_cursors_cannot_be_lost(self):
        self.assert_rejected(lambda data: data["Quests"][0]["Beats"].pop(), "51 story beats")
        self.assert_rejected(lambda data: data["Quests"][0]["Beats"][0].update(VoiceKey="renumbered:1"), "VoiceKey")
        self.assert_rejected(lambda data: data["Quests"][0]["Beats"][0].update(Id="other:0"), ".Id")

    def test_music_and_prologue_follow_age_chapters(self):
        self.assert_rejected(lambda data: data["Quests"][0]["Beats"][0].update(MusicRole="baptism"), "MusicRole")
        self.assert_rejected(lambda data: data["Quests"][11].update(IsPrologue=True), "IsPrologue")

    def test_cli_accepts_actual_export_and_rejects_invalid_file(self):
        result = subprocess.run([sys.executable, str(VALIDATOR_PATH), str(CAMPAIGN_PATH)], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        with tempfile.TemporaryDirectory(prefix="dawn-gospel-content-") as temporary:
            invalid = Path(temporary) / "invalid.json"
            invalid.write_text("{}", encoding="utf-8")
            rejected = subprocess.run([sys.executable, str(VALIDATOR_PATH), str(invalid)], capture_output=True, text=True)
            self.assertNotEqual(0, rejected.returncode)
            self.assertIn("SchemaVersion", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
