#!/usr/bin/env python3
"""Collect a bounded, task-driven context packet from an admitted 1C snapshot."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable
import xml.etree.ElementTree as ET

from target_admission import TargetBlocked, admit_target, load_contract, paths, snapshot_ref, unique_object


NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
START = re.compile(
    r"^\s*(Procedure|Function|Процедура|Функция)\s+([^\W\d]\w*)\s*\((.*?)\)\s*(Export|Экспорт)?\s*$",
    re.IGNORECASE,
)
END = re.compile(r"^\s*(End(Procedure|Function)|Конец(Процедуры|Функции))\s*;?\s*$", re.IGNORECASE)
TOKEN = re.compile(
    r"\b(?:AccumulationRegister|Catalog|Document|InformationRegister|Report|Role|Subsystem)\.[A-Za-z_][A-Za-z0-9_]*\b"
)
DEFAULT_LIMIT = 12
MAX_LIMIT = 32


class ContextBlocked(RuntimeError):
    def __init__(self, reason_code: str, message: str):
        super().__init__(message)
        self.reason_code = reason_code


def encode(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def blocked(reason_code: str, message: str) -> dict[str, Any]:
    return {"schemaVersion": 1, "status": "blocked", "reasonCode": reason_code, "message": message}


def local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def child(element: ET.Element, name: str) -> ET.Element | None:
    return next((item for item in element if local_name(item) == name), None)


def text(element: ET.Element | None) -> str:
    return "" if element is None else "".join(element.itertext()).strip()


def locator(path: Path, start: int, end: int | None = None) -> dict[str, Any]:
    return {"path": path.as_posix(), "startLine": start, "endLine": start if end is None else end}


def lines(path: Path) -> list[str]:
    if path.is_symlink() or not path.is_file():
        raise ContextBlocked("snapshot_invalid", f"artifact is not a regular file: {path.as_posix()}")
    return path.read_text(encoding="utf-8-sig").splitlines()


def find_line(source: list[str], needle: str, occurrence: int = 1) -> int:
    found = 0
    for number, value in enumerate(source, start=1):
        if needle in value:
            found += 1
            if found == occurrence:
                return number
    return 1


def request_data(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"schemaVersion", "focus", "seeds", "limit"}:
        raise ContextBlocked("request_invalid", "request must contain schemaVersion, focus, seeds, and limit")
    if value["schemaVersion"] != 1 or type(value["limit"]) is not int or not 1 <= value["limit"] <= MAX_LIMIT:
        raise ContextBlocked("request_invalid", "request schemaVersion or limit is invalid")
    focus = value["focus"]
    seeds = value["seeds"]
    if not isinstance(focus, list) or not focus or not all(isinstance(item, str) and item.strip() for item in focus):
        raise ContextBlocked("request_invalid", "focus must be a non-empty list of strings")
    if not isinstance(seeds, list) or not seeds:
        raise ContextBlocked("request_invalid", "seeds must be a non-empty list")
    normalized: list[dict[str, str]] = []
    for seed in seeds:
        if not isinstance(seed, dict) or set(seed) != {"kind", "value", "state"}:
            raise ContextBlocked("request_invalid", "seed shape is invalid")
        if seed["kind"] not in {"metadata", "term", "artifact"} or seed["state"] != "candidate" or not isinstance(seed["value"], str) or not seed["value"].strip():
            raise ContextBlocked("request_invalid", "seed value is invalid")
        normalized.append({"kind": seed["kind"], "value": seed["value"].strip(), "state": "candidate"})
    return {"schemaVersion": 1, "focus": sorted(set(item.strip() for item in focus)), "seeds": sorted(normalized, key=lambda item: (item["kind"], item["value"])), "limit": value["limit"]}


def document_seeds(request: dict[str, Any]) -> list[str]:
    result = []
    for seed in request["seeds"]:
        if seed["kind"] != "metadata" or not seed["value"].startswith("Document."):
            continue
        name = seed["value"].removeprefix("Document.")
        if not NAME.fullmatch(name):
            raise ContextBlocked("request_invalid", "Document seed must use Document.<Name>")
        result.append(name)
    if not result:
        raise ContextBlocked("unsupported", "no supported Document metadata seed")
    return sorted(set(result))


def metadata_domain(snapshot: Path, document_names: Iterable[str]) -> dict[str, Any]:
    """Read XML only and return data-only entity/attribute/artifact references."""
    entities: list[dict[str, str]] = []
    attributes: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    for name in document_names:
        descriptor = Path("Documents") / f"{name}.xml"
        absolute = snapshot / descriptor
        source = lines(absolute)
        try:
            root = ET.fromstring(absolute.read_bytes())
        except ET.ParseError as exc:
            raise ContextBlocked("snapshot_invalid", f"cannot parse descriptor: {descriptor.as_posix()}") from exc
        document = next((item for item in root.iter() if local_name(item) == "Document"), None)
        properties = child(document, "Properties") if document is not None else None
        if document is None or properties is None or text(child(properties, "Name")) != name:
            raise ContextBlocked("snapshot_invalid", f"descriptor identity mismatch: {descriptor.as_posix()}")
        entities.append({"canonicalName": f"Document.{name}", "kind": "Document"})
        artifacts.append({"kind": "descriptor", "locator": locator(descriptor, 1)})
        children = child(document, "ChildObjects")
        occurrences: dict[str, int] = {}
        if children is not None:
            for item in children:
                if local_name(item) != "Attribute":
                    continue
                properties = child(item, "Properties")
                item_properties = properties if properties is not None else item
                attribute_name = text(child(item_properties, "Name"))
                attribute_type = text(child(item_properties, "Type")) or None
                if attribute_name:
                    occurrences[attribute_name] = occurrences.get(attribute_name, 0) + 1
                    attributes.append(
                        {
                            "entity": f"Document.{name}",
                            "name": attribute_name,
                            "type": attribute_type,
                            "state": "confirmed",
                            "locator": locator(descriptor, find_line(source, f"<Name>{attribute_name}</Name>", occurrences[attribute_name])),
                        }
                    )
        package = snapshot / "Documents" / name
        if package.is_symlink() or not package.is_dir():
            raise ContextBlocked("snapshot_invalid", f"document package is missing: {name}")
        for relative, kind in (
            (Path("Documents") / name / "Ext" / "ObjectModule.bsl", "bsl"),
            (Path("Documents") / name / "Ext" / "ManagerModule.bsl", "bsl"),
        ):
            candidate = snapshot / relative
            if candidate.is_file() and not candidate.is_symlink():
                artifacts.append({"kind": kind, "locator": locator(relative, 1)})
        forms = package / "Forms"
        if forms.is_dir() and not forms.is_symlink():
            for form in sorted(forms.rglob("Form.xml")):
                if form.is_file() and not form.is_symlink():
                    artifacts.append({"kind": "form", "locator": locator(form.relative_to(snapshot), 1)})
    return {
        "entities": sorted(entities, key=lambda item: item["canonicalName"]),
        "attributes": sorted(attributes, key=lambda item: (item["entity"], item["name"], item["locator"]["startLine"])),
        "artifacts": sorted(artifacts, key=lambda item: (item["kind"], item["locator"]["path"])),
    }


def bsl_domain(snapshot: Path, artifacts: Iterable[dict[str, Any]], focus: Iterable[str]) -> dict[str, Any]:
    """Read only supplied artifact references; emit bounded procedure fragments and lexical candidates."""
    focus_values = tuple(item.casefold() for item in focus)
    fragments: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for artifact in artifacts:
        if artifact["kind"] != "bsl":
            continue
        relative = Path(artifact["locator"]["path"])
        source = lines(snapshot / relative)
        active: tuple[str, int] | None = None
        for number, value in enumerate(source, start=1):
            start = START.match(value)
            if start:
                active = (start.group(2), number)
                continue
            if active is not None and END.match(value):
                name, beginning = active
                body = source[beginning - 1:number]
                joined = "\n".join(body)
                if name.casefold() in focus_values or any(term in joined.casefold() for term in focus_values):
                    fragments.append(
                        {
                            "procedure": name,
                            "state": "confirmed",
                            "locator": locator(relative, beginning, number),
                            "text": joined,
                        }
                    )
                active = None
            for match in TOKEN.finditer(value):
                candidates.append({"state": "candidate", "target": match.group(0), "locator": locator(relative, number)})
    unique = {json.dumps(item, sort_keys=True): item for item in candidates}
    return {
        "fragments": sorted(fragments, key=lambda item: (item["locator"]["path"], item["locator"]["startLine"], item["procedure"])),
        "lexical": sorted(unique.values(), key=lambda item: (item["target"], item["locator"]["path"], item["locator"]["startLine"])),
    }


def artifact_candidates(snapshot: Path, request: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for seed in request["seeds"]:
        if seed["kind"] != "artifact":
            continue
        relative = Path(seed["value"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ContextBlocked("request_invalid", "artifact seed must be snapshot-relative")
        candidate = snapshot / relative
        if candidate.is_symlink() or not candidate.is_file():
            raise ContextBlocked("seed_invalid", "artifact seed is not a regular snapshot file")
        result.append({"state": "candidate", "locator": locator(relative, 1)})
    unique = {json.dumps(item, sort_keys=True): item for item in result}
    return sorted(unique.values(), key=lambda item: item["locator"]["path"])


def apply_limit(values: list[Any], limit: int, label: str, diagnostics: list[str]) -> list[Any]:
    if len(values) > limit:
        diagnostics.append(label)
        return values[:limit]
    return values


def collect(snapshot: Path, raw_request: object) -> dict[str, Any]:
    if snapshot.is_symlink() or not snapshot.is_dir():
        raise ContextBlocked("snapshot_invalid", "snapshot must be a regular directory")
    request = request_data(raw_request)
    metadata = metadata_domain(snapshot, document_seeds(request))
    bsl = bsl_domain(snapshot, metadata["artifacts"], request["focus"])
    diagnostics: list[str] = []
    limit = request["limit"]
    payload: dict[str, Any] = {
        "schemaVersion": 1,
        "status": "ready",
        "focus": request["focus"],
        "seedCount": len(request["seeds"]),
        "confirmed": {
            "entities": apply_limit(metadata["entities"], limit, "confirmed.entities", diagnostics),
            "metadata": {"attributes": apply_limit(metadata["attributes"], limit, "confirmed.metadata.attributes", diagnostics)},
            "artifacts": apply_limit(metadata["artifacts"], limit, "confirmed.artifacts", diagnostics),
        },
        "fragments": apply_limit(bsl["fragments"], limit, "fragments", diagnostics),
        "candidates": {
            "artifacts": apply_limit(artifact_candidates(snapshot, request), limit, "candidates.artifacts", diagnostics),
            "lexical": apply_limit(bsl["lexical"], limit, "candidates.lexical", diagnostics),
        },
        "unknown": ["Dynamic calls, query text, and semantic execution order are not confirmed by this collector."],
        "unsupported": ["Non-Document metadata seeds", "recursive dependency graph", "full BSL AST"],
        "truncated": bool(diagnostics),
        "diagnostics": sorted(set(diagnostics)),
    }
    return payload


def resolve_snapshot(repo_root: Path, reference: Path) -> Path:
    if reference.is_symlink() or not reference.is_file():
        raise ContextBlocked("snapshot_ref_invalid", "SnapshotRef must be a regular JSON file")
    try:
        received = json.loads(reference.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
        contract, _ = load_contract(repo_root)
        action = received.get("action") if isinstance(received, dict) else None
        if action not in {"materialized", "reused"} or received != snapshot_ref(contract, action):
            raise ValueError("SnapshotRef does not match project target")
        _, target, snapshot, manifest, binding = paths(repo_root, contract)
        admit_target(target, snapshot, manifest, binding, contract)
        return snapshot
    except (OSError, ValueError, TypeError, TargetBlocked) as exc:
        raise ContextBlocked("snapshot_ref_invalid", "SnapshotRef failed authoritative target admission") from exc


def load_request(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ContextBlocked("request_invalid", "request must be a regular JSON file")
    try:
        return request_data(json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object))
    except (OSError, ValueError, TypeError) as exc:
        raise ContextBlocked("request_invalid", "request JSON is invalid") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True)
    collect_parser = commands.add_parser("collect", allow_abbrev=False)
    collect_parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    collect_parser.add_argument("--snapshot-ref", type=Path, required=True)
    collect_parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        payload = collect(resolve_snapshot(args.repo_root.resolve(), args.snapshot_ref), load_request(args.request))
    except ContextBlocked as exc:
        print(encode(blocked(exc.reason_code, str(exc))), end="")
        return 2
    print(encode(payload), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
