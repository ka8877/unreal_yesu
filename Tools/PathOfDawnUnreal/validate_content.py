#!/usr/bin/env python3
"""Validate the authoritative episode source before Unreal Editor imports it.

This validates content, not Unreal compilation, cooking, or graphical playback.
No authoring commands are evaluated; effects belong to a closed vocabulary.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys

KINDS = {"성경 사건 요약", "창작 연결 장면", "가상 분기"}
EFFECTS = {"SetFlag", "AddItem", "RemoveItem", "ChangeRelationship"}
IMAGE_IDS = {
    "IL_Title_Dawn", "IL_Arrival", "IL_Portrait_Jesus", "IL_Portrait_Simon",
    "IL_Ending_Together", "IL_Ending_Witness", "IL_Ending_Departure",
}
ENDINGS = {"Ending_Together", "Ending_Witness", "Ending_Departure"}
EXPECTED_INTERACTIONS = {
    "Task_HelpNet": {"ActorId": "Net", "NextNode": "Simon_Helped", "Effects": []},
    "Task_ObserveShore": {"ActorId": "Stone", "NextNode": "Shore_Clue", "Effects": []},
    "Task_ReturnToSimon": {"ActorId": "Simon", "NextNode": "Choice_02", "Effects": []},
    "Task_Departure": {
        "ActorId": "Village", "NextNode": "Ending_Departure",
        "Effects": [{"Command": "SetFlag", "Target": "WalkedToVillage", "Value": True}],
    },
}
EXPECTED_ENTRY_POINTS = {"Simon": "Simon_Greeting", "Jesus": "Simon_Greeting"}
REQUIRED_NODES = {
    "Intro_Arrival", "Explore", "Inspect_Net", "Inspect_Boat", "Inspect_Stone",
    "Simon_Greeting", "Jesus_Arrival", "Choice_01", "Simon_Helped", "Shore_Clue",
    "Scene_Teaching", "Traveler_Crossroads", "Choice_02", *ENDINGS, *EXPECTED_INTERACTIONS,
}
EXPECTED_BRANCHES = {
    ("HelpSimon", "Stay"): "Ending_Together",
    ("ObserveShore", "Stay"): "Ending_Witness",
    ("HelpSimon", "Depart"): "Ending_Departure",
    ("ObserveShore", "Depart"): "Ending_Departure",
}
EXPECTED_CHOICE_EFFECTS = {
    "HelpSimon": [
        {"Command": "RemoveItem", "Target": "Rope", "Amount": 1},
        {"Command": "SetFlag", "Target": "NetPrepared", "Value": True},
        {"Command": "ChangeRelationship", "Target": "Simon", "Amount": 1},
    ],
    "ObserveShore": [{"Command": "SetFlag", "Target": "ShoreClueFound", "Value": True}],
    "Stay": [
        {"Command": "SetFlag", "Target": "StayedWithSimon", "Value": True},
        {"Command": "SetFlag", "Target": "WalkedToVillage", "Value": False},
    ],
    "Depart": [
        {"Command": "SetFlag", "Target": "StayedWithSimon", "Value": False},
        {"Command": "SetFlag", "Target": "WalkedToVillage", "Value": False},
    ],
}
EXPECTED_CONDITIONS = {
    "HelpSimon": [{"Inspected": "Net"}, {"Item": "Rope", "Minimum": 1}],
    "ObserveShore": [], "Stay": [], "Depart": [],
}
EXPECTED_CHOICE_DESTINATIONS = {
    "HelpSimon": "Task_HelpNet", "ObserveShore": "Task_ObserveShore",
    "Stay": "Outcome_Stay", "Depart": "Task_Departure",
}


def validate(data: dict, root: Path | None = None, require_art: bool = False) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    if data.get("SchemaVersion") != 1 or data.get("ContentVersion") != 2:
        errors.append("Unsupported version; SchemaVersion must be 1 and ContentVersion must be 2.")
    if data.get("Language") != "ko-KR":
        errors.append("Language must be ko-KR.")
    if "여행자의 존재, 선택과 시간 회귀는 허구" not in data.get("Disclaimer", ""):
        errors.append("Missing required fiction notice.")
    if data.get("ScriptureReference") != "누가복음 5:1–11":
        errors.append("Episode must reference Luke 5:1–11 only.")
    images = data.get("Images", {})
    if not isinstance(images, dict):
        errors.append("Images must be an ID/object-path mapping.")
        images = {}
    for image_id in sorted(IMAGE_IDS):
        expected = f"/Game/PathOfDawn/Illustrations/{image_id}.{image_id}"
        if images.get(image_id) != expected:
            errors.append(f"Missing or unexpected texture path for {image_id}.")
    rows = data.get("Nodes", [])
    if not isinstance(rows, list):
        return {"ok": False, "errors": errors + ["Nodes must be an array."], "warnings": warnings}
    nodes: dict[str, dict] = {}
    text_keys: set[str] = set()
    choice_ids: set[str] = set()
    memories = data.get("Memories", [])
    memory_ids: set[str] = set()
    for memory in memories:
        mid = memory.get("Id", "")
        if not mid or mid in memory_ids:
            errors.append(f"Missing/duplicate memory ID: {mid!r}.")
        memory_ids.add(mid)
        if not memory.get("Title") or not memory.get("Text"):
            errors.append(f"Memory {mid} needs Korean title and text.")

    def check_text_key(key: object, where: str) -> None:
        if not isinstance(key, str) or not key.startswith("POD."):
            errors.append(f"{where}: missing namespaced TextKey.")
        elif key in text_keys:
            errors.append(f"{where}: duplicate TextKey {key}.")
        else:
            text_keys.add(key)

    def check_effect(effect: dict, where: str) -> None:
        command = effect.get("Command")
        if command not in EFFECTS:
            errors.append(f"{where}: unsupported effect {command!r}.")
            return
        target = effect.get("Target")
        if not isinstance(target, str) or not target.replace("_", "").isalnum():
            errors.append(f"{where}: effect Target must be a stable identifier.")
        allowed = {"Command", "Target", "Value" if command == "SetFlag" else "Amount"}
        if set(effect) != allowed:
            errors.append(f"{where}: unexpected effect fields {sorted(set(effect) ^ allowed)}.")
        if command == "SetFlag":
            if type(effect.get("Value")) is not bool:
                errors.append(f"{where}: SetFlag Value must be boolean.")
        else:
            amount = effect.get("Amount")
            if type(amount) is not int or abs(amount) > 100:
                errors.append(f"{where}: effect Amount must be a bounded integer.")
            elif command in {"AddItem", "RemoveItem"} and amount <= 0:
                errors.append(f"{where}: item Amount must be positive.")

    def check_conditions(conditions: list, where: str) -> None:
        for condition in conditions:
            if set(condition) == {"Inspected"}:
                if condition["Inspected"] not in {"Net", "Boat", "Stone"}:
                    errors.append(f"{where}: invalid inspected-object condition.")
            elif set(condition) == {"Flag", "Value"}:
                if not isinstance(condition["Flag"], str) or type(condition["Value"]) is not bool:
                    errors.append(f"{where}: invalid flag condition.")
            elif set(condition) == {"Item", "Minimum"}:
                if not isinstance(condition["Item"], str) or type(condition["Minimum"]) is not int or condition["Minimum"] < 0:
                    errors.append(f"{where}: invalid item condition.")
            else:
                errors.append(f"{where}: unsupported condition fields.")

    for node in rows:
        nid = node.get("Id", "")
        if not isinstance(nid, str) or not nid or nid in nodes:
            errors.append(f"Missing/duplicate node ID: {nid!r}.")
            continue
        nodes[nid] = node
        for field in ("Speaker", "Text", "ScriptureReference", "SourceNote"):
            if not isinstance(node.get(field), str) or not node[field].strip():
                errors.append(f"{nid}: missing {field}.")
        if node.get("ScriptureReference") != "누가복음 5:1–11":
            errors.append(f"{nid}: unexpected ScriptureReference.")
        if node.get("ContentKind") not in KINDS:
            errors.append(f"{nid}: invalid ContentKind.")
        if node.get("Speaker") == "예수님" and node.get("ContentKind") != "창작 연결 장면":
            errors.append(f"{nid}: Jesus spoken lines must be clearly marked creative adaptation.")
        if node.get("Speaker") == "예수님" and "성경 직접 인용 아님" not in node.get("DisplayNote", ""):
            errors.append(f"{nid}: Jesus creative line missing visible quote disclaimer.")
        check_text_key(node.get("TextKey"), nid)
        if "RepeatText" in node:
            if not node["RepeatText"]:
                errors.append(f"{nid}: empty repeat text.")
            check_text_key(node.get("RepeatTextKey"), nid + "/Repeat")
        for field in ("Portrait", "Illustration"):
            image_id = node.get(field, "")
            if image_id and image_id not in images:
                errors.append(f"{nid}: missing image ID {image_id}.")
        if node.get("MemoryId") and node["MemoryId"] not in memory_ids:
            errors.append(f"{nid}: unknown MemoryId.")
        check_conditions(node.get("Conditions", []), nid)
        if node.get("Conditions", []):
            errors.append(f"{nid}: node entry conditions are runtime-owned; authored node conditions must be empty.")
        for effect in node.get("Effects", []):
            check_effect(effect, nid)
        expected_node_effects = [{"Command": "AddItem", "Target": "Rope", "Amount": 1}] if nid == "Inspect_Net" else []
        if node.get("Effects", []) != expected_node_effects:
            errors.append(f"{nid}: node effects differ from the closed runtime contract.")
        if nid in EXPECTED_INTERACTIONS:
            if node.get("RuntimeStage") != "Task" or node.get("NextNode") or node.get("Choices"):
                errors.append(f"{nid}: spatial task must use Task stage and wait for interaction, with no NextNode/Choices bypass.")
            if node.get("ContentKind") != "가상 분기":
                errors.append(f"{nid}: spatial task must be marked fictional branching.")
        elif node.get("RuntimeStage") == "Task" or nid.startswith("Task_"):
            errors.append(f"{nid}: unsupported spatial task.")
        for choice in node.get("Choices", []):
            cid = choice.get("Id")
            if not cid or cid in choice_ids:
                errors.append(f"{nid}: duplicate/missing choice ID {cid!r}.")
            choice_ids.add(cid)
            check_text_key(choice.get("TextKey"), f"{nid}/{cid}")
            if not choice.get("Text") or not choice.get("NextNode"):
                errors.append(f"{nid}/{cid}: missing choice text or destination.")
            check_conditions(choice.get("Conditions", []), f"{nid}/{cid}")
            for effect in choice.get("Effects", []):
                check_effect(effect, f"{nid}/{cid}")
            if choice.get("Effects", []) != EXPECTED_CHOICE_EFFECTS.get(cid):
                errors.append(f"{nid}/{cid}: effects differ from the closed runtime contract.")
            if choice.get("Conditions", []) != EXPECTED_CONDITIONS.get(cid):
                errors.append(f"{nid}/{cid}: conditions differ from the closed runtime contract.")
            if choice.get("NextNode") != EXPECTED_CHOICE_DESTINATIONS.get(cid):
                errors.append(f"{nid}/{cid}: destination differs from the closed runtime contract.")

    for nid in sorted(REQUIRED_NODES - set(nodes)):
        errors.append(f"Required node missing: {nid}.")
    decision_nodes = {nid for nid, row in nodes.items() if row.get("Choices")}
    if decision_nodes != {"Choice_01", "Choice_02"}:
        errors.append("Exactly Choice_01 and Choice_02 must have player choices.")
    for nid, expected_ids, checkpoint in (
        ("Choice_01", ["HelpSimon", "ObserveShore"], "CP01"),
        ("Choice_02", ["Stay", "Depart"], "CP02"),
    ):
        row = nodes.get(nid, {})
        if [c.get("Id") for c in row.get("Choices", [])] != expected_ids:
            errors.append(f"{nid}: choices/order differ from runtime contract.")
        if row.get("Checkpoint") != checkpoint:
            errors.append(f"{nid}: missing checkpoint declaration.")
    if not nodes.get("Choice_01", {}).get("RepeatText"):
        errors.append("Choice_01 needs a memory-aware repeat line.")
    routing = data.get("RuntimeRouting", {})
    expected_routing = {"Outcome_Stay": {"HelpSimon": "Ending_Together", "ObserveShore": "Ending_Witness"}}
    if routing != expected_routing:
        errors.append("Outcome_Stay routing differs from required outcomes.")
    interactions = data.get("RuntimeInteractions", {})
    if interactions != EXPECTED_INTERACTIONS:
        errors.append("RuntimeInteractions differ from the four fixed spatial gates and interaction effects.")
    entry_points = data.get("RuntimeEntryPoints", {})
    if entry_points != EXPECTED_ENTRY_POINTS:
        errors.append("Simon and Jesus interactions must both enter Simon_Greeting so the introduction is not skipped.")
    if nodes.get("Traveler_Crossroads", {}).get("NextNode") != "Task_ReturnToSimon":
        errors.append("Traveler_Crossroads must lead to Task_ReturnToSimon before CP02.")
    rows_branch = data.get("Branches", [])
    branches = {(b.get("Choice1"), b.get("Choice2")): b.get("Ending") for b in rows_branch}
    if branches != EXPECTED_BRANCHES or len(rows_branch) != 4:
        errors.append("The four choice combinations must map to exactly the three specified outcomes.")
    outcome_rows = {nid for nid, row in nodes.items() if row.get("OutcomeId")}
    if outcome_rows != ENDINGS:
        errors.append("There must be exactly three authored outcome rows.")
    outcome_images = []
    for nid in sorted(ENDINGS):
        row = nodes.get(nid, {})
        if row.get("OutcomeId") != nid or row.get("NextNode") or row.get("Choices"):
            errors.append(f"{nid}: must be a terminal outcome with matching OutcomeId.")
        image_id = row.get("Illustration")
        if image_id != "IL_" + nid:
            errors.append(f"{nid}: missing dedicated ending illustration.")
        outcome_images.append(image_id)
    if len(set(outcome_images)) != 3:
        errors.append("Endings require three distinct image assets.")

    # Interactables are gameplay entry edges; the remaining transitions are authored.
    graph: dict[str, set[str]] = {nid: set() for nid in nodes}
    for nid, row in nodes.items():
        refs = [row.get("NextNode", "")] + [c.get("NextNode", "") for c in row.get("Choices", [])]
        if nid in interactions:
            refs.append(interactions[nid].get("NextNode", ""))
        for ref in filter(None, refs):
            destinations = routing.get(ref, {}).values() if ref in routing else [ref]
            for destination in destinations:
                if destination not in nodes:
                    errors.append(f"{nid}: dangling node reference {destination!r}.")
                else:
                    graph[nid].add(destination)
    if "Explore" in graph:
        graph["Explore"].update(({"Inspect_Net", "Inspect_Boat", "Inspect_Stone"} | set(entry_points.values())) & set(nodes))
    seen: set[str] = set()
    pending = ["Intro_Arrival"]
    while pending:
        nid = pending.pop()
        if nid in seen or nid not in graph:
            continue
        seen.add(nid)
        pending.extend(graph[nid] - seen)
    for nid in sorted(set(nodes) - seen):
        errors.append(f"Unreachable node: {nid}.")
    for nid in sorted(ENDINGS - seen):
        errors.append(f"Unreachable ending: {nid}.")

    # Walk the actual authored chains for each pair of player decisions. Generic
    # graph reachability alone would accept a route that reaches an ending before
    # its choice effects or bypasses the first checkpoint.
    route_walks: dict[str, str] = {}
    spatial_walks: dict[str, list[str]] = {}
    for actor, start in entry_points.items():
        for first_index, first_id in enumerate(("HelpSimon", "ObserveShore")):
            for second_index, second_id in enumerate(("Stay", "Depart")):
                label = f"{actor}/{first_id}/{second_id}"
                current = start
                visited: set[str] = set()
                crossed_gates: list[str] = []
                selected_first = selected_second = taught = False
                while current in nodes and current not in visited:
                    visited.add(current)
                    row = nodes[current]
                    taught = taught or current == "Scene_Teaching"
                    if current in ENDINGS:
                        expected = EXPECTED_BRANCHES[(first_id, second_id)]
                        expected_gates = ["Task_HelpNet" if first_index == 0 else "Task_ObserveShore", "Task_ReturnToSimon"]
                        if second_id == "Depart":
                            expected_gates.append("Task_Departure")
                        if not selected_first or not selected_second or not taught or current != expected or crossed_gates != expected_gates:
                            errors.append(f"{label}: reached {current} without the required ordered choices/scene.")
                        else:
                            route_walks[label] = current
                            spatial_walks[label] = crossed_gates
                        break
                    if current in EXPECTED_INTERACTIONS:
                        valid_phase = {
                            "Task_HelpNet": selected_first and first_id == "HelpSimon" and not taught and not selected_second,
                            "Task_ObserveShore": selected_first and first_id == "ObserveShore" and not taught and not selected_second,
                            "Task_ReturnToSimon": selected_first and taught and not selected_second,
                            "Task_Departure": selected_second and second_id == "Depart",
                        }[current]
                        if not valid_phase:
                            errors.append(f"{label}: spatial gate {current} occurs in the wrong phase.")
                            break
                        crossed_gates.append(current)
                        current = interactions.get(current, {}).get("NextNode", "")
                        continue
                    if current in {"Choice_01", "Choice_02"}:
                        is_first = current == "Choice_01"
                        if (is_first and selected_first) or (not is_first and (not selected_first or selected_second or not taught or "Task_ReturnToSimon" not in crossed_gates)):
                            errors.append(f"{label}: out-of-order checkpoint/choice {current}.")
                            break
                        index = first_index if is_first else second_index
                        choices = row.get("Choices", [])
                        if index >= len(choices):
                            break
                        selected_first = selected_first or is_first
                        selected_second = selected_second or not is_first
                        current = choices[index].get("NextNode", "")
                        if current == "Outcome_Stay":
                            current = routing.get(current, {}).get(first_id, "")
                    else:
                        if current.startswith("Scene_") and not selected_first:
                            errors.append(f"{label}: event scene precedes the first choice.")
                            break
                        current = row.get("NextNode", "")
                if label not in route_walks:
                    errors.append(f"{label}: authored route does not reach its expected ending.")
    for inspect_id in ("Net", "Boat", "Stone"):
        if nodes.get("Inspect_" + inspect_id, {}).get("NextNode") != "Explore":
            errors.append(f"Inspect_{inspect_id}: investigation must return to Explore.")
    if nodes.get("Intro_Arrival", {}).get("NextNode") != "Explore":
        errors.append("Intro_Arrival must return to Explore, matching the skip path.")

    if require_art:
        if root is None:
            errors.append("--require-art requires a repository root.")
        else:
            for image_id in sorted(IMAGE_IDS):
                path = root / "SourceArt/PathOfDawnUnreal/VisualV8/Illustrations" / f"{image_id}.png"
                if not path.is_file() or path.stat().st_size < 128:
                    errors.append(f"Missing/empty image source: {path}.")
                else:
                    try:
                        from PIL import Image
                        with Image.open(path) as image:
                            image.verify()
                        with Image.open(path) as image:
                            if min(image.size) < 512:
                                errors.append(f"Image source too small: {image_id} {image.size}.")
                            if image_id == "IL_Title_Dawn" and (image.width < 1920 or image.height < 1080):
                                warnings.append(f"Title source {image.size} is below the 1920×1080 target; do not claim native full-HD art.")
                    except ImportError:
                        errors.append("Pillow required for --require-art; install Tools/PathOfDawnUnreal/requirements-art.txt.")
                    except Exception as exc:
                        errors.append(f"Unreadable image {image_id}: {exc}.")
            font = root / "SourceArt/PathOfDawnUnreal/Fonts/NotoSansKR.otf"
            if not font.is_file():
                errors.append(f"Missing Korean font source: {font}.")
            else:
                try:
                    from fontTools.ttLib import TTFont
                    with TTFont(font) as typeface:
                        cmap = typeface.getBestCmap() or {}
                        text = data.get("Title", "") + data.get("Disclaimer", "")
                        text += "".join(r.get("Text", "") + "".join(c.get("Text", "") for c in r.get("Choices", [])) for r in rows)
                        missing = sorted({c for c in text if not c.isspace() and ord(c) not in cmap})
                        if missing:
                            errors.append("Font lacks authored glyphs: " + "".join(missing))
                except ImportError:
                    errors.append("fontTools required for --require-art; install Tools/PathOfDawnUnreal/requirements-art.txt.")
                except Exception as exc:
                    errors.append(f"Unreadable font: {exc}.")
    else:
        warnings.append("Art files, font glyph coverage, imported Unreal assets, cooking and rendered UI not checked; use --require-art for source checks.")
    return {
        "ok": not errors, "errors": errors, "warnings": warnings,
        "scope": "Authored JSON and optional source assets only; not Unreal execution.",
        "node_count": len(nodes), "outcome_count": len(outcome_rows),
        "choice_combinations": len(branches), "text_key_count": len(text_keys),
        "authored_route_walks": route_walks,
        "spatial_gate_walks": spatial_walks,
        "content_version": data.get("ContentVersion"),
        "text_characters": sum(len(row.get("Text", "")) for row in rows),
    }


def self_test(source: dict) -> list[str]:
    """Fault-inject invalid authored content to prove validation rejects it."""
    failures: list[str] = []
    if not validate(source)["ok"]:
        return ["Baseline content is invalid."]
    def reject(name: str, mutate) -> None:
        data = copy.deepcopy(source)
        mutate(data)
        if validate(data)["ok"]:
            failures.append(f"Validator incorrectly accepted {name}.")
    reject("duplicate node", lambda d: d["Nodes"].append(copy.deepcopy(d["Nodes"][0])))
    reject("dangling transition", lambda d: d["Nodes"][0].update(NextNode="Missing_Node"))
    reject("wrong outcome mapping", lambda d: d["Branches"][0].update(Ending="Ending_Witness"))
    reject("missing metadata", lambda d: d["Nodes"][0].pop("SourceNote"))
    reject("missing image", lambda d: d["Images"].pop("IL_Portrait_Jesus"))
    reject("unreachable node", lambda d: d["Nodes"].append({**d["Nodes"][0], "Id": "Lost", "TextKey": "POD.Lost.Text"}))
    reject("arbitrary command", lambda d: d["Nodes"][0].update(Effects=[{"Command": "ExecuteShell", "Target": "bad"}]))
    reject("identical outcome art", lambda d: next(n for n in d["Nodes"] if n["Id"] == "Ending_Witness").update(Illustration="IL_Ending_Together"))
    reject("wrong choice effect", lambda d: next(n for n in d["Nodes"] if n["Id"] == "Choice_01")["Choices"][0]["Effects"][0].update(Amount=2))
    reject("wrong checkpoint", lambda d: next(n for n in d["Nodes"] if n["Id"] == "Choice_02").update(Checkpoint="CP01"))
    reject("wrong choice condition", lambda d: next(n for n in d["Nodes"] if n["Id"] == "Choice_01")["Choices"][0].update(Conditions=[]))
    reject("wrong runtime destination", lambda d: next(n for n in d["Nodes"] if n["Id"] == "Choice_01")["Choices"][0].update(NextNode="Shore_Clue"))
    reject("wrong spatial actor", lambda d: d["RuntimeInteractions"]["Task_HelpNet"].update(ActorId="Stone"))
    reject("task advance bypass", lambda d: next(n for n in d["Nodes"] if n["Id"] == "Task_HelpNet").update(NextNode="Simon_Helped"))
    reject("duplicate task effect", lambda d: next(n for n in d["Nodes"] if n["Id"] == "Task_HelpNet").update(Effects=[{"Command": "RemoveItem", "Target": "Rope", "Amount": 1}]))
    reject("return-to-Simon bypass", lambda d: next(n for n in d["Nodes"] if n["Id"] == "Traveler_Crossroads").update(NextNode="Choice_02"))
    reject("premature departure completion", lambda d: next(n for n in d["Nodes"] if n["Id"] == "Choice_02")["Choices"][1]["Effects"][1].update(Value=True))
    reject("missing village arrival effect", lambda d: d["RuntimeInteractions"]["Task_Departure"].update(Effects=[]))
    reject("Jesus introduction bypass", lambda d: d["RuntimeEntryPoints"].update(Jesus="Jesus_Arrival"))
    reject("stale content version", lambda d: d.update(ContentVersion=1))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--require-art", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    source = args.root / "SourceArt/PathOfDawnUnreal/Narrative/episode.json"
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
        result = validate(data, args.root, args.require_art)
        if args.self_test:
            failures = self_test(data)
            result["mutation_tests"] = {"total": 20, "passed": 20 - len(failures), "failures": failures}
            result["errors"].extend(failures)
            result["ok"] = not result["errors"]
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        result = {"ok": False, "errors": [f"Cannot validate {source}: {exc}"], "warnings": []}
    output = json.dumps(result, ensure_ascii=False, indent=2)
    print(output)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output + "\n", encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
