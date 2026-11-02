#!/usr/bin/env python3
"""Validate Luke 2 authored metadata, never certify rendered scenes or gameplay."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

RELATIVE_SOURCE = Path("SourceArt/PathOfDawnUnreal/Rebuild/Narrative/journey.json")
EXPECTED = {
    "Birth": (1, 7, "Birth", [], "BirthWitnessed", "BirthRecorded"),
    "Shepherds": (8, 20, "Birth", ["Birth"], "ShepherdsWitnessed", "BirthChapterComplete"),
    "Temple": (41, 52, "Temple", ["Birth", "Shepherds"], "TempleWitnessed", "TempleRecorded"),
}


def validate(document: dict) -> list[str]:
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    require(document.get("schema_version") == 1, "schema_version must be 1")
    require(document.get("content_version") == 1, "content_version must be 1")
    require(document.get("language") == "ko", "primary language must be Korean")
    require(document.get("project_module") == "PathOfDawnUnreal", "preserve existing module identity")
    source = document.get("source_policy", {})
    require(source.get("reference_url") == "https://bible.usccb.org/bible/luke/2", "reference source missing")
    require(bool(source.get("reference_checked_utc")), "source check date missing")
    require(source.get("direct_quotation_used") is False, "this edition must use original summaries, not unlicensed direct quotation")
    require(bool(source.get("summary_author")), "summary provenance missing")
    disclaimer = document.get("disclaimer", {})
    require(disclaimer.get("text_kind") == "GameGuide" and bool(disclaimer.get("text_ko")), "game adaptation disclaimer missing")
    events = document.get("events", [])
    ids = [event.get("id") for event in events]
    require(ids == list(EXPECTED), "exactly three unique ordered events Birth, Shepherds, Temple required")
    scenes = document.get("scenes", [])
    scene_ids = [scene.get("id") for scene in scenes]
    require(len(scene_ids) == 3 and len(set(scene_ids)) == 3, "three unique scene IDs required")
    scene_map = {scene.get("id"): scene for scene in scenes}
    for event in events:
        event_id = event.get("id")
        if event_id not in EXPECTED:
            errors.append("unknown event ID")
            continue
        start, end, chapter, prerequisites, unlock, checkpoint = EXPECTED[event_id]
        require(event.get("chapter_id") == chapter, f"{event_id}: wrong chapter")
        for field in ("title_ko", "body_ko", "source_note", "place_ko"):
            require(isinstance(event.get(field), str) and bool(event[field].strip()), f"{event_id}: {field} missing")
        require(event.get("text_kind") == "ScriptureSummary", f"{event_id}: summary must not be labeled direct quotation or invented dialogue")
        body = event.get("body_ko", "")
        require(not body.lstrip().startswith(('"', "“", "「")), f"{event_id}: do not present an original summary as a scripture quotation")
        references = event.get("scripture_references", [])
        require(len(references) == 1, f"{event_id}: one explicit passage required")
        if len(references) == 1:
            reference = references[0]
            require((reference.get("book"), reference.get("chapter"), reference.get("verse_start"), reference.get("verse_end")) == ("Luke", 2, start, end), f"{event_id}: wrong passage; do not mix Gospel scenes")
            require(bool(reference.get("label_ko")), f"{event_id}: visible Korean reference missing")
        require(bool(event.get("people")), f"{event_id}: people metadata missing")
        require(event.get("prerequisite_written") == prerequisites, f"{event_id}: chapter/event gates changed")
        require(event.get("unlock_event") == unlock, f"{event_id}: observation must precede writing")
        require(event.get("checkpoint_after_written") == checkpoint, f"{event_id}: stable checkpoint mismatch")
        require(event.get("write_action") == "WriteEntry", f"{event_id}: explicit write action required")
        scene = scene_map.get(event.get("scene_id"))
        require(scene is not None, f"{event_id}: referenced scene missing")
        if scene:
            require(scene.get("event_id") == event_id, f"{event_id}: scene maps to another event")
            require(scene.get("skip_completes_only_event") == event_id, f"{event_id}: skip must not unlock future scenes")
            status = scene.get("status")
            require(status in {"BLOCKED", "IMPLEMENTED_UNVERIFIED", "VERIFIED"}, f"{event_id}: explicit scene status required")
            if status == "BLOCKED":
                require(bool(scene.get("blockers")), f"{event_id}: describe the blocked assets/environment")
            if status == "VERIFIED":
                # This is an evidence metadata contract, not a substitute for
                # inspecting the actual captures and running the real game.
                evidence = scene.get("evidence", {})
                require(evidence.get("engine") == "Unreal" and bool(evidence.get("build_id")) and bool(evidence.get("reviewer")) and len(evidence.get("captures", [])) >= 3, f"{event_id}: cannot claim verified without actual Unreal build and reviewed captures")
            implementation = event.get("implementation", {})
            if status != "VERIFIED":
                require(implementation.get("visual_review") != "PASS" and implementation.get("playtest") != "PASS", f"{event_id}: source implementation is not scene verification")
        if event_id == "Birth" and scene:
            require(45 <= scene.get("planned_opening_seconds", 0) <= 90, "birth opening plan must be 45–90 seconds; this is not a measured duration")
    book = document.get("book_presentation", {})
    require(book.get("locked_entries_expose_title") is False, "locked future titles must remain hidden")
    require(book.get("locked_entries_expose_body") is False, "locked future bodies must remain hidden")
    require(book.get("future_chapters_shown_as_playable") is False, "unimplemented future chapters must not appear playable")
    require(bool(book.get("initial_body_ko")), "empty-book guidance missing")
    transition = document.get("time_transition", {})
    require(transition.get("after_written") == ["Birth", "Shepherds"], "time transition must follow both first-chapter records")
    require(transition.get("next_checkpoint") == "TempleArrival", "time transition checkpoint mismatch")
    require(transition.get("counts_as_experienced") is False and transition.get("creates_journal_entry") is False, "omitted middle events must not be recorded as experienced")
    omitted = transition.get("unplayed_reference", {})
    require((omitted.get("book"), omitted.get("chapter"), omitted.get("verse_start"), omitted.get("verse_end")) == ("Luke", 2, 21, 40), "identify the omitted Luke 2:21–40 passage")
    require(bool(transition.get("omission_note_ko")) and transition.get("text_kind") == "GameGuide", "identify time jump as game guidance and explain omitted events")
    return errors


def self_test(document: dict) -> dict:
    def modified(path: tuple, value):
        result = copy.deepcopy(document)
        target = result
        for part in path[:-1]:
            target = target[part]
        target[path[-1]] = value
        return result

    mutations = [
        (("schema_version",), 99),
        (("content_version",), 99),
        (("language",), "en"),
        (("events", 1, "id"), "Birth"),
        (("events", 0, "body_ko"), ""),
        (("events", 0, "text_kind"), "DirectQuotation"),
        (("events", 2, "body_ko"), '"직접 작성한 요약을 인용처럼 제시"'),
        (("events", 0, "scripture_references", 0, "book"), "Matthew"),
        (("events", 2, "scripture_references", 0, "verse_start"), 21),
        (("events", 2, "prerequisite_written"), []),
        (("events", 0, "unlock_event"), "AllFutureEvents"),
        (("events", 1, "scene_id"), "MissingScene"),
        (("scenes", 0, "planned_opening_seconds"), 300),
        (("scenes", 0, "skip_completes_only_event"), "Temple"),
        (("scenes", 2, "status"), "VERIFIED"),
        (("scenes", 1, "blockers"), []),
        (("events", 2, "implementation", "visual_review"), "PASS"),
        (("source_policy", "direct_quotation_used"), True),
        (("book_presentation", "locked_entries_expose_title"), True),
        (("book_presentation", "locked_entries_expose_body"), True),
        (("book_presentation", "future_chapters_shown_as_playable"), True),
        (("time_transition", "counts_as_experienced"), True),
        (("time_transition", "creates_journal_entry"), True),
        (("time_transition", "unplayed_reference", "verse_start"), 8),
    ]
    failures = ["/".join(map(str, path)) for path, value in mutations if not validate(modified(path, value))]
    return {"total": len(mutations), "rejected": len(mutations) - len(failures), "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    source = args.root / RELATIVE_SOURCE
    try:
        payload = source.read_bytes()
        document = json.loads(payload)
        errors = validate(document)
        mutations = self_test(document) if args.self_test and not errors else None
        if mutations and mutations["failures"]:
            errors.append("mutation checks failed")
        report = {"ok": not errors, "status": "PASSED_SOURCE_ONLY" if not errors else "FAILED", "scope": "Authored metadata and mutation checks only; not Unreal compilation, playback or visual verification.", "source": RELATIVE_SOURCE.as_posix(), "source_sha256": hashlib.sha256(payload).hexdigest(), "event_count": len(document.get("events", [])), "errors": errors, "scene_statuses": {scene["id"]: scene["status"] for scene in document.get("scenes", [])}, "mutations": mutations}
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        report = {"ok": False, "status": "FAILED", "errors": [str(error)]}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
