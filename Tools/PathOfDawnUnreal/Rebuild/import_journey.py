"""Editor-only import of authored Luke 2 summaries; never a runtime JSON loader.

Compile the Editor target first. This imports no scene, unlocks no event, and
never marks an asset/scene visually approved. Existing assets are never rewritten.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = "/Game/WordJourney/Narrative/DA_JourneyJournal"
SOURCE = ROOT / "SourceArt/PathOfDawnUnreal/Rebuild/Narrative/journey.json"
PEOPLE = {"Joseph": "요셉", "Mary": "마리아", "InfantJesus": "아기 예수", "Shepherds": "목자들", "TwelveYearOldJesus": "열두 살 예수", "Teachers": "선생들"}


def references(event):
    # Canonical IDs match the runtime validator; the widget localizes the book
    # name when displaying them. Localized labels remain in authored metadata.
    return [f"{ref['book']} {ref['chapter']}:{ref['verse_start']}-{ref['verse_end']}" for ref in event["scripture_references"]]


def import_data(u):
    from validate_journey import validate
    payload = SOURCE.read_bytes()
    document = json.loads(payload)
    errors = validate(document)
    if errors:
        raise ValueError("Invalid journal source: " + "; ".join(errors))
    source_hash = hashlib.sha256(payload).hexdigest()
    lib = u.EditorAssetLibrary
    if lib.does_asset_exist(PACKAGE):
        existing = lib.load_asset(PACKAGE)
        if not isinstance(existing, u.JourneyJournalData):
            raise TypeError("Existing package has a different class; preserved: " + PACKAGE)
        if lib.get_metadata_tag(existing, "JourneySourceSHA256") != source_hash:
            raise RuntimeError("Source or existing asset differs; preserved. Import a reviewed new asset version explicitly.")
        # Validate the actual loaded rows, not only a mutable metadata tag.
        if not same_content(u, existing, document):
            raise RuntimeError("Journal asset was edited; preserved without rewriting.")
        return {"status": "PRESERVED", "asset": PACKAGE, "graphicsGate": "BLOCKED"}
    rows = []
    for event in document["events"]:
        row = u.JourneyJournalEntry()
        row.set_editor_property("id", event["id"])
        row.set_editor_property("chapter_id", event["chapter_id"])
        text = lambda key, value: u.DawnAssetTools.localized_text("Journey." + event["id"] + "." + key, value)
        row.set_editor_property("title", text("Title", event["title_ko"]))
        row.set_editor_property("summary", text("Summary", event["body_ko"]))
        row.set_editor_property("source_note", text("SourceNote", event["source_note"]))
        row.set_editor_property("scripture_references", references(event))
        row.set_editor_property("people", [text("Person." + person, PEOPLE[person]) for person in event["people"]])
        row.set_editor_property("places", [text("Place", event["place_ko"])])
        row.set_editor_property("text_kind", u.JourneyTextKind.SUMMARY)
        row.set_editor_property("scene_ready", False)
        rows.append(row)
    factory = u.DataAssetFactory()
    factory.set_editor_property("data_asset_class", u.JourneyJournalData)
    data = u.AssetToolsHelpers.get_asset_tools().create_asset("DA_JourneyJournal", "/Game/WordJourney/Narrative", u.JourneyJournalData, factory)
    if not data:
        raise RuntimeError("Editor did not create the journal DataAsset.")
    data.set_editor_property("content_version", document["content_version"])
    data.set_editor_property("entries", rows)
    lib.set_metadata_tag(data, "JourneySourceSHA256", source_hash)
    if not same_content(u, data, document) or not lib.save_loaded_asset(data):
        raise RuntimeError("Journal data verification/save failed.")
    reloaded = lib.load_asset(PACKAGE)
    if not reloaded or not same_content(u, reloaded, document):
        raise RuntimeError("Journal references/content did not survive reload.")
    return {"status": "CREATED", "asset": PACKAGE, "graphicsGate": "BLOCKED", "sourceSHA256": source_hash, "freshProcessReload": "NOT_RUN"}


def same_content(u, asset, document):
    if asset.get_editor_property("content_version") != document["content_version"]:
        return False
    rows = asset.get_editor_property("entries")
    if len(rows) != len(document["events"]):
        return False
    for row, event in zip(rows, document["events"]):
        for prop, key in (("id", "id"), ("chapter_id", "chapter_id"), ("title", "title_ko"), ("summary", "body_ko"), ("source_note", "source_note")):
            if str(row.get_editor_property(prop)) != event[key]:
                return False
        if row.get_editor_property("scene_ready"):
            return False
        if list(row.get_editor_property("scripture_references")) != references(event):
            return False
        if row.get_editor_property("text_kind") != u.JourneyTextKind.SUMMARY:
            return False
        if [str(person) for person in row.get_editor_property("people")] != [PEOPLE[person] for person in event["people"]]:
            return False
        if [str(place) for place in row.get_editor_property("places")] != [event["place_ko"]]:
            return False
    return True


if __name__ == "__main__":
    import unreal
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    command_line = unreal.SystemLibrary.get_command_line()
    match = re.search(r'(?:^|\s)-JourneyDataReport=(?:"([^"]*)"|(\S+))', command_line)
    explicit_report = os.environ.get("WORD_JOURNEY_REPORT") or ((match.group(1) or match.group(2)) if match else None)
    report_path = Path(explicit_report) if explicit_report else ROOT / "Games/PathOfDawnUnreal/Saved/WordJourney/journal-import.json"
    try:
        result = import_data(unreal)
    except Exception as error:
        result = {"status": "FAILED", "error": str(error), "graphicsGate": "BLOCKED"}
        unreal.log_error(str(error))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
