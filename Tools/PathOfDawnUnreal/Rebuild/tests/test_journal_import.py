"""Import-policy contracts only. This fake does not emulate Unreal serialization."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("journey_import", HERE / "import_journey.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Row:
    def __init__(self): self.properties = {}
    def set_editor_property(self, name, value): self.properties[name] = value
    def get_editor_property(self, name): return self.properties[name]


class Data(Row): pass


class ImportContracts(unittest.TestCase):
    def setUp(self):
        self.asset = None
        self.created = 0
        self.saved = 0
        self.tags = {}
        def create(*_):
            self.created += 1
            self.asset = Data()
            return self.asset
        def save(_):
            self.saved += 1
            return True
        self.u = SimpleNamespace(
            JourneyJournalData=Data, JourneyJournalEntry=Row,
            JourneyTextKind=SimpleNamespace(SUMMARY="summary"), DataAssetFactory=Row,
            DawnAssetTools=SimpleNamespace(localized_text=lambda key, value: value),
            AssetToolsHelpers=SimpleNamespace(get_asset_tools=lambda: SimpleNamespace(create_asset=create)),
            EditorAssetLibrary=SimpleNamespace(
                does_asset_exist=lambda _: self.asset is not None,
                load_asset=lambda _: self.asset,
                get_metadata_tag=lambda _, key: self.tags.get(key),
                set_metadata_tag=lambda _, key, value: self.tags.update({key: value}),
                save_loaded_asset=save,
            ))
        self.document = json.loads(module.SOURCE.read_text(encoding="utf-8"))

    def test_canonical_references_and_korean_people_match_runtime_contract(self):
        result = module.import_data(self.u)
        self.assertEqual(result["status"], "CREATED")
        rows = self.asset.properties["entries"]
        self.assertEqual([r.properties["scripture_references"] for r in rows], [["Luke 2:1-7"], ["Luke 2:8-20"], ["Luke 2:41-52"]])
        self.assertIn("요셉", rows[0].properties["people"])
        self.assertTrue(all(not row.properties["scene_ready"] for row in rows))
        self.assertEqual(result["freshProcessReload"], "NOT_RUN")

    def test_identical_asset_is_preserved_without_saving_or_creating(self):
        module.import_data(self.u)
        self.assertEqual(module.import_data(self.u)["status"], "PRESERVED")
        self.assertEqual((self.created, self.saved), (1, 1))

    def test_user_edits_to_any_display_field_are_preserved_and_rejected(self):
        module.import_data(self.u)
        original = copy.deepcopy(self.asset.properties)
        for field, value in (("summary", "changed"), ("people", ["changed"]), ("places", ["changed"]), ("text_kind", "quote"), ("scene_ready", True)):
            self.asset.properties = copy.deepcopy(original)
            self.asset.properties["entries"][0].properties[field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError): module.import_data(self.u)
            self.assertEqual((self.created, self.saved), (1, 1))

    def test_missing_or_changed_source_tag_never_overwrites(self):
        module.import_data(self.u)
        self.tags.clear()
        with self.assertRaises(RuntimeError): module.import_data(self.u)
        self.assertEqual((self.created, self.saved), (1, 1))

    def test_wrong_existing_class_never_overwrites(self):
        self.asset = object()
        with self.assertRaises(TypeError): module.import_data(self.u)
        self.assertEqual((self.created, self.saved), (0, 0))

    def test_invalid_authored_data_prevents_factory_use(self):
        from unittest.mock import patch
        import validate_journey
        with patch.object(validate_journey, "validate", return_value=["bad reference"]):
            with self.assertRaises(ValueError): module.import_data(self.u)
        self.assertEqual((self.created, self.saved), (0, 0))


if __name__ == "__main__": unittest.main()
