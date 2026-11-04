#!/usr/bin/env python3
"""Validate the fixed-source, engine-independent Gospel campaign.

This checks the content contract before Editor import. It neither executes
Unreal nor replaces the exporter's evaluation/parity check against pinned C#.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CAMPAIGN = ROOT / "SourceArt/PathOfDawnUnreal/Gospel/Campaign.json"
SOURCE_REPOSITORY = "ka8877/firstgame"
SOURCE_COMMIT = "808d8d1e1eeed908d8925398f80c7173653ef364"
KINDS = {"Scripture", "Summary", "Dramatization"}
QUEST_IDS = (
    "birth-road-bethlehem", "birth-birth-manger", "birth-night-shepherds",
    "birth-birth-good-news", "birth-manger-witnesses", "birth-birth-remembered",
    "birth-name-jesus", "birth-temple-dedication", "birth-simeon-peace",
    "birth-anna-thanksgiving", "birth-nazareth-growth", "nazareth-departure",
    "pilgrim-spring", "festival-courtyard", "listening-court", "teachers-circle",
    "parents-reunite", "nazareth-return", "adult-jordan-road", "john-calling",
    "baptism-request", "baptism-water", "ministry-beginning",
)
READING_IDS = (
    "road-bethlehem", "birth-manger", "night-shepherds", "birth-good-news",
    "manger-witnesses", "birth-remembered", "name-jesus", "temple-dedication",
    "simeon-peace", "anna-thanksgiving", "nazareth-growth", "temple-passover",
    "temple-teachers", "temple-parents", "temple-nazareth", "john-jordan",
    "baptism-request", "baptism-water", "ministry-thirty",
)
ROOT_KEYS = {"SchemaVersion", "CampaignId", "ContentVersion", "Title", "ScopeNote",
             "Source", "Readings", "Quests"}
READING_KEYS = {"Id", "Title", "Reference", "Text", "Source", "Context"}
QUEST_KEYS = {"Id", "ChapterId", "Title", "Objective", "NpcId", "NpcName",
              "ReadingId", "IsPrologue", "Beats"}
BEAT_KEYS = {"Id", "Speaker", "Text", "Kind", "Reference", "VoiceKey",
             "SceneTitle", "Location", "TimeLabel", "MusicRole"}
ID_RE = re.compile(r"[a-z][a-z0-9-]*\Z")
CITATION_RE = re.compile(r"^(누가복음|마태복음) (\d+):(\d+)(?:[–-](\d+))?(?:\s|$)")


def quoted_words(value: str) -> str:
    """Ignore retained verse numbers/line wrapping, never rewrite scripture words."""
    return " ".join(re.sub(r"(?m)^\s*\d+\s+", "", value).split())


def citation_range(value: object) -> tuple[str, int, int, int] | None:
    if type(value) is not str:
        return None
    match = CITATION_RE.match(value)
    if match is None:
        return None
    book, chapter, first, last = match.groups()
    start, end = int(first), int(last or first)
    return (book, int(chapter), start, end) if 0 < start <= end else None


def validate(document: object) -> list[str]:
    """Return all structural and campaign-contract failures; never mutate input."""
    errors: list[str] = []

    def record(condition: bool, message: str) -> bool:
        if not condition:
            errors.append(message)
        return condition

    def fields(value: object, expected: set[str], where: str) -> bool:
        if not record(type(value) is dict, f"{where}: expected an object."):
            return False
        actual = set(value)
        record(actual == expected,
               f"{where}: fields differ; missing={sorted(expected - actual)}, "
               f"unexpected={sorted(map(str, actual - expected))}.")
        return True

    def text(value: object, where: str, allow_empty: bool = False) -> bool:
        return record(type(value) is str and (allow_empty or bool(value.strip())),
                      f"{where}: expected {'a string' if allow_empty else 'nonempty text'}.")

    def stable_id(value: object, where: str) -> bool:
        return record(type(value) is str and ID_RE.fullmatch(value) is not None,
                      f"{where}: expected a stable lowercase identifier.")

    if not fields(document, ROOT_KEYS, "Campaign"):
        return errors
    record(type(document.get("SchemaVersion")) is int and document["SchemaVersion"] == 1,
           "Campaign.SchemaVersion must be integer 1.")
    record(type(document.get("ContentVersion")) is int and document["ContentVersion"] == 1,
           "Campaign.ContentVersion must be integer 1.")
    record(document.get("CampaignId") == "gospel-pilgrimage", "Unexpected CampaignId.")
    text(document.get("Title"), "Campaign.Title")
    text(document.get("ScopeNote"), "Campaign.ScopeNote")
    source = document.get("Source")
    if fields(source, {"Repository", "Commit"}, "Campaign.Source"):
        record(source.get("Repository") == SOURCE_REPOSITORY, "Source.Repository is not the reviewed Unity repository.")
        record(source.get("Commit") == SOURCE_COMMIT, "Source.Commit is not the reviewed immutable commit.")

    readings = document.get("Readings")
    if not record(type(readings) is list, "Readings must be an array."):
        readings = []
    record(len(readings) == 19, "Expected 19 discovered scripture readings.")
    reading_ids: list[str] = []
    reading_text: dict[str, str] = {}
    reading_references: dict[str, tuple[str, int, int, int]] = {}
    for index, reading in enumerate(readings):
        where = f"Readings[{index}]"
        if not fields(reading, READING_KEYS, where):
            continue
        rid = reading.get("Id")
        if stable_id(rid, where + ".Id"):
            reading_ids.append(rid)
            if type(reading.get("Text")) is str:
                reading_text[rid] = quoted_words(reading["Text"])
        for key in READING_KEYS - {"Id"}:
            text(reading.get(key), where + "." + key)
        reference = citation_range(reading.get("Reference"))
        record(reference is not None, where + ".Reference must retain a supported Gospel passage range.")
        if type(rid) is str and reference is not None:
            reading_references[rid] = reference
        credit = reading.get("Source")
        record(type(credit) is str and "개역한글" in credit and "대한성서공회" in credit,
               where + ".Source must preserve the translation and publisher credit.")
        if reference is not None:
            book_code = "luk" if reference[0] == "누가복음" else "mat"
            expected_url = ("https://www.bskorea.or.kr/bible/korbibReadpage.php?"
                            f"version=HAN&book={book_code}&chap={reference[1]}")
            record(type(credit) is str and expected_url in credit,
                   where + ".Source must retain the matching verified passage URL.")
    record(tuple(reading_ids) == READING_IDS, "Reading IDs/order differ from the pinned Unity catalog.")
    record(len(set(reading_ids)) == len(reading_ids), "Duplicate reading ID.")

    quests = document.get("Quests")
    if not record(type(quests) is list, "Quests must be an array."):
        quests = []
    record(len(quests) == 23, "Expected 23 ordered story objectives.")
    quest_ids: list[str] = []
    linked_readings: list[str] = []
    chapters: Counter[str] = Counter()
    beat_ids: set[str] = set()
    birth_beats = 0
    for index, quest in enumerate(quests):
        where = f"Quests[{index}]"
        if not fields(quest, QUEST_KEYS, where):
            continue
        qid = quest.get("Id")
        if stable_id(qid, where + ".Id"):
            quest_ids.append(qid)
        for key in ("Title", "Objective", "NpcName"):
            text(quest.get(key), where + "." + key)
        stable_id(quest.get("NpcId"), where + ".NpcId")
        chapter = quest.get("ChapterId")
        expected_chapter = "birth" if index < 11 else "temple" if index < 18 else "baptism"
        record(chapter == expected_chapter, where + ".ChapterId violates birth/temple/baptism chronology.")
        if type(chapter) is str:
            chapters[chapter] += 1
        record(type(quest.get("IsPrologue")) is bool and quest["IsPrologue"] == (chapter == "birth"),
               where + ".IsPrologue must be a boolean matching the birth chapter.")
        rid = quest.get("ReadingId")
        if text(rid, where + ".ReadingId", allow_empty=True) and rid:
            linked_readings.append(rid)
            record(rid in reading_ids, where + ".ReadingId references an unknown reading.")
        beats = quest.get("Beats")
        if not record(type(beats) is list and bool(beats), where + ".Beats must be a nonempty array."):
            continue
        if chapter == "birth":
            birth_beats += len(beats)
        for beat_index, beat in enumerate(beats):
            beat_where = f"{where}.Beats[{beat_index}]"
            if not fields(beat, BEAT_KEYS, beat_where):
                continue
            expected_id = f"{qid}:{beat_index}"
            bid = beat.get("Id")
            record(bid == expected_id, beat_where + ".Id must preserve the flat Unity story cursor.")
            record(beat.get("VoiceKey") == expected_id, beat_where + ".VoiceKey must preserve the Unity voice key.")
            if type(bid) is str:
                record(bid not in beat_ids, beat_where + ": duplicate beat ID.")
                beat_ids.add(bid)
            for key in ("Speaker", "Text", "Reference", "SceneTitle", "Location", "TimeLabel"):
                text(beat.get(key), beat_where + "." + key)
            record(type(beat.get("Kind")) is str and beat["Kind"] in KINDS,
                   beat_where + ".Kind must distinguish Scripture, Summary and Dramatization.")
            if beat.get("Kind") == "Scripture" and type(beat.get("Text")) is str:
                words = quoted_words(beat["Text"])
                retained = reading_text.get(rid, "") if type(rid) is str else ""
                record(bool(words) and bool(retained) and words in retained,
                       beat_where + ": Scripture text is not a retained quotation from the quest's reading.")
                citation = citation_range(beat.get("Reference"))
                passage = reading_references.get(rid) if type(rid) is str else None
                record(citation is not None and passage is not None and citation[:2] == passage[:2]
                       and passage[2] <= citation[2] <= citation[3] <= passage[3],
                       beat_where + ": Scripture reference is outside the quest's retained passage.")
            record(beat.get("MusicRole") == chapter, beat_where + ".MusicRole must match the current chapter.")
    record(tuple(quest_ids) == QUEST_IDS, "Quest IDs/order differ from the pinned Unity catalog.")
    record(len(set(quest_ids)) == len(quest_ids), "Duplicate quest ID.")
    record(chapters == {"birth": 11, "temple": 7, "baptism": 5}, "Chapter objective counts must be 11/7/5.")
    record(tuple(linked_readings) == READING_IDS, "Quest reading links must preserve the catalog's discovery order exactly once.")
    record(birth_beats == 51, "The birth prologue must preserve all 51 story beats.")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path, nargs="?", default=DEFAULT_CAMPAIGN)
    args = parser.parse_args()
    try:
        with args.campaign.open(encoding="utf-8") as stream:
            document = json.load(stream)
    except (OSError, ValueError) as exc:
        print(f"Campaign could not be read: {exc}", file=sys.stderr)
        return 1
    errors = validate(document)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"Campaign valid: 23 objectives, 19 readings, 51 birth beats; source review/contract validation only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
