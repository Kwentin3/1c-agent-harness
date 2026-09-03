#!/usr/bin/env python3
"""Return a bounded, read-only context map for one 1C Document snapshot object."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable
import xml.etree.ElementTree as ET


DEFAULT_LIMIT = 24
DEFAULT_BYTE_LIMIT = 32 * 1024
NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
OUTLINE = re.compile(
    r"^\s*(Procedure|Function)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)\s*(Export)?\s*$",
    re.IGNORECASE,
)
END_OUTLINE = re.compile(r"^\s*End(Procedure|Function)\s*;?\s*$", re.IGNORECASE)
METADATA_TOKEN = re.compile(
    r"\b(AccumulationRegister|BusinessProcess|Catalog|ChartOfCharacteristicTypes|"
    r"Document|ExchangePlan|InformationRegister|Report|Role|Subsystem)\.([A-Za-z_][A-Za-z0-9_]*)\b"
)


def local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if local_name(child) == name]


def first_child(element: ET.Element, name: str) -> ET.Element | None:
    matches = children(element, name)
    return matches[0] if matches else None


def element_text(element: ET.Element | None) -> str:
    return (element.text or "").strip() if element is not None else ""


def text_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8-sig", errors="strict").splitlines()


def locator(relative: Path, line: int, end_line: int | None = None) -> dict[str, Any]:
    return {
        "path": relative.as_posix(),
        "startLine": line,
        "endLine": line if end_line is None else end_line,
    }


def find_line(lines: list[str], needle: str, occurrence: int = 1) -> int:
    seen = 0
    for number, line in enumerate(lines, start=1):
        if needle in line:
            seen += 1
            if seen == occurrence:
                return number
    return 1


def read_regular(root: Path, relative: Path) -> tuple[Path, list[str]]:
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise InputBlocked("snapshot_invalid", f"required artifact is not a regular file: {relative.as_posix()}")
    return path, text_lines(path)


class InputBlocked(RuntimeError):
    def __init__(self, reason_code: str, message: str):
        super().__init__(message)
        self.reason_code = reason_code


def block(reason_code: str, message: str) -> dict[str, Any]:
    return {"schemaVersion": 1, "status": "blocked", "reasonCode": reason_code, "message": message}


def artifact(relative: Path, kind: str) -> dict[str, Any]:
    return {"kind": kind, "locator": locator(relative, 1)}


def collect_owned_artifacts(snapshot: Path, name: str) -> list[dict[str, Any]]:
    owner = Path("Documents") / name
    package = snapshot / owner
    if package.is_symlink() or not package.is_dir():
        raise InputBlocked("object_not_found", f"Document.{name} has no object package")
    result: list[dict[str, Any]] = []
    for path in sorted(package.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(snapshot)
        parts = relative.parts
        if relative.suffix.lower() == ".bsl":
            kind = "bslModule"
        elif "Forms" in parts and relative.name == "Form.xml":
            kind = "form"
        elif "Forms" in parts and relative.suffix.lower() == ".xml":
            kind = "formDescriptor"
        elif "Templates" in parts:
            kind = "template"
        else:
            kind = "ownedArtifact"
        result.append(artifact(relative, kind))
    return result


def parse_descriptor(snapshot: Path, name: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    relative = Path("Documents") / f"{name}.xml"
    path, lines = read_regular(snapshot, relative)
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise InputBlocked("snapshot_invalid", f"cannot parse descriptor: {relative.as_posix()}") from exc
    document = next((item for item in root.iter() if local_name(item) == "Document"), None)
    properties = first_child(document, "Properties") if document is not None else None
    if document is None or properties is None or element_text(first_child(properties, "Name")) != name:
        raise InputBlocked("snapshot_invalid", f"descriptor identity mismatch: {relative.as_posix()}")

    def named_items(parent_name: str, item_name: str) -> list[dict[str, Any]]:
        parent = first_child(properties, parent_name)
        result: list[dict[str, Any]] = []
        if parent is None:
            return result
        for item in children(parent, item_name):
            item_name_value = element_text(first_child(item, "Name"))
            if not item_name_value:
                continue
            result.append(
                {
                    "name": item_name_value,
                    "type": element_text(first_child(item, "Type")) or None,
                    "locator": locator(relative, find_line(lines, f"<Name>{item_name_value}</Name>")),
                }
            )
        return result

    attributes = named_items("Attributes", "Attribute")
    tabular_sections: list[dict[str, Any]] = []
    sections = first_child(properties, "TabularSections")
    if sections is not None:
        for section in children(sections, "TabularSection"):
            section_name = element_text(first_child(section, "Name"))
            if not section_name:
                continue
            section_attributes: list[dict[str, Any]] = []
            section_attributes_node = first_child(section, "Attributes")
            if section_attributes_node is not None:
                for child in children(section_attributes_node, "Attribute"):
                    child_name = element_text(first_child(child, "Name"))
                    if child_name:
                        section_attributes.append(
                            {
                                "name": child_name,
                                "type": element_text(first_child(child, "Type")) or None,
                                "locator": locator(relative, find_line(lines, f"<Name>{child_name}</Name>")),
                            }
                        )
            tabular_sections.append(
                {
                    "name": section_name,
                    "attributes": sorted(section_attributes, key=lambda value: value["name"]),
                    "locator": locator(relative, find_line(lines, f"<Name>{section_name}</Name>")),
                }
            )
    metadata = {
        "descriptor": {"name": name, "kind": "Document", "locator": locator(relative, find_line(lines, f"<Name>{name}</Name>"))},
        "attributes": sorted(attributes, key=lambda value: value["name"]),
        "tabularSections": sorted(tabular_sections, key=lambda value: value["name"]),
        "forms": sorted(element_text(item) for item in children(first_child(properties, "Forms") or ET.Element("empty"), "Form") if element_text(item)),
        "templates": sorted(element_text(item) for item in children(first_child(properties, "Templates") or ET.Element("empty"), "Template") if element_text(item)),
    }
    return metadata, collect_owned_artifacts(snapshot, name)


def parse_outline(
    snapshot: Path, artifacts: Iterable[dict[str, Any]], focus_terms: Iterable[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    outline: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    focus = tuple(term.casefold() for term in focus_terms)
    for item in artifacts:
        if item["kind"] != "bslModule":
            continue
        relative = Path(item["locator"]["path"])
        _, lines = read_regular(snapshot, relative)
        active: tuple[str, str, int, bool] | None = None
        for number, line in enumerate(lines, start=1):
            match = OUTLINE.match(line)
            if match:
                active = (match.group(1).lower(), match.group(2), number, bool(match.group(4)))
            elif active is not None and END_OUTLINE.match(line):
                kind, name, start, exported = active
                outline.append(
                    {"name": name, "kind": kind, "exported": exported, "locator": locator(relative, start, number)}
                )
                active = None
            for relation_match in METADATA_TOKEN.finditer(line):
                token = f"{relation_match.group(1)}.{relation_match.group(2)}"
                if token != "Document." + relative.parts[1] and (
                    not focus or any(term in line.casefold() for term in focus)
                ):
                    candidates.append(
                        {
                            "kind": "lexical",
                            "target": token,
                            "state": "candidate",
                            "locator": locator(relative, number),
                        }
                    )
    key = lambda item: (item["name"], item["locator"]["path"], item["locator"]["startLine"])
    relation_key = lambda item: (item["target"], item["locator"]["path"], item["locator"]["startLine"])
    return sorted(outline, key=key), sorted({json.dumps(item, sort_keys=True): item for item in candidates}.values(), key=relation_key)


def parse_forms(snapshot: Path, artifacts: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    forms: list[dict[str, Any]] = []
    for item in artifacts:
        if item["kind"] != "form":
            continue
        relative = Path(item["locator"]["path"])
        path, lines = read_regular(snapshot, relative)
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as exc:
            raise InputBlocked("snapshot_invalid", f"cannot parse form: {relative.as_posix()}") from exc
        data_paths = []
        events = []
        commands = []
        for node in root.iter():
            node_kind = local_name(node)
            value = element_text(node)
            if node_kind == "DataPath" and value:
                data_paths.append({"value": value, "locator": locator(relative, find_line(lines, value))})
            elif node_kind == "Event" and value:
                events.append({"name": node.get("name") or value, "handler": value, "locator": locator(relative, find_line(lines, value))})
            elif node_kind in {"CommandName", "Action"} and value:
                commands.append({"name": value, "locator": locator(relative, find_line(lines, value))})
        forms.append(
            {
                "name": relative.parts[3],
                "locator": locator(relative, 1),
                "dataPaths": sorted(data_paths, key=lambda value: (value["value"], value["locator"]["startLine"])),
                "events": sorted(events, key=lambda value: (value["name"], value["handler"])),
                "commands": sorted(commands, key=lambda value: value["name"]),
            }
        )
    return sorted(forms, key=lambda value: value["name"])


def confirmed_relations(snapshot: Path, object_name: str) -> list[dict[str, Any]]:
    token = f"Document.{object_name}"
    roots = {
        "Configuration.xml": "configuration",
        "Roles": "role",
        "EventSubscriptions": "eventSubscription",
        "Subsystems": "subsystem",
        "FunctionalOptions": "functionalOption",
    }
    result: list[dict[str, Any]] = []
    for raw_root, kind in roots.items():
        source = snapshot / raw_root
        paths = [source] if source.is_file() else sorted(source.rglob("*.xml")) if source.is_dir() and not source.is_symlink() else []
        for path in paths:
            if path.is_symlink() or not path.is_file():
                continue
            relative = path.relative_to(snapshot)
            for number, line in enumerate(text_lines(path), start=1):
                if token in line or (kind == "configuration" and f">{object_name}<" in line):
                    result.append({"kind": kind, "target": token, "state": "confirmed", "locator": locator(relative, number)})
    unique = {json.dumps(item, sort_keys=True): item for item in result}
    return sorted(unique.values(), key=lambda value: (value["kind"], value["locator"]["path"], value["locator"]["startLine"]))


def cap(values: list[Any], limit: int, diagnostics: list[str], label: str) -> list[Any]:
    if len(values) > limit:
        diagnostics.append(label)
        return values[:limit]
    return values


def apply_limits(payload: dict[str, Any], limit: int) -> None:
    diagnostics: list[str] = []
    payload["metadata"]["attributes"] = cap(payload["metadata"]["attributes"], limit, diagnostics, "metadata.attributes")
    payload["metadata"]["tabularSections"] = cap(payload["metadata"]["tabularSections"], limit, diagnostics, "metadata.tabularSections")
    payload["artifacts"] = cap(payload["artifacts"], limit, diagnostics, "artifacts")
    payload["bsl"]["outline"] = cap(payload["bsl"]["outline"], limit, diagnostics, "bsl.outline")
    payload["relations"]["confirmed"] = cap(payload["relations"]["confirmed"], limit, diagnostics, "relations.confirmed")
    payload["relations"]["candidates"] = cap(payload["relations"]["candidates"], limit, diagnostics, "relations.candidates")
    for form in payload["forms"]:
        for key in ("dataPaths", "events", "commands"):
            form[key] = cap(form[key], limit, diagnostics, f"forms.{key}")
    payload["forms"] = cap(payload["forms"], limit, diagnostics, "forms")
    payload["truncated"] = bool(diagnostics)
    payload["diagnostics"] = sorted(set(diagnostics))


def encode(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"


def inspect(snapshot: Path, canonical_name: str, limit: int, focus_terms: Iterable[str] = ()) -> dict[str, Any]:
    if not snapshot.exists() or snapshot.is_symlink() or not snapshot.is_dir():
        raise InputBlocked("snapshot_unavailable", "snapshot must be an existing regular directory")
    if not canonical_name.startswith("Document."):
        if "." in canonical_name and all(NAME.fullmatch(part) for part in canonical_name.split(".", 1)):
            return {"schemaVersion": 1, "status": "unsupported", "object": {"canonicalName": canonical_name}}
        raise InputBlocked("invalid_object", "object must be canonical Document.<Name>")
    name = canonical_name.removeprefix("Document.")
    if not NAME.fullmatch(name):
        raise InputBlocked("invalid_object", "object must be canonical Document.<Name>")
    descriptor = snapshot / "Documents" / f"{name}.xml"
    if descriptor.is_symlink() or not descriptor.is_file():
        raise InputBlocked("object_not_found", f"Document.{name} is absent from snapshot")
    metadata, artifacts = parse_descriptor(snapshot, name)
    normalized_focus = tuple(sorted({term.strip() for term in focus_terms if term.strip()}))
    outline, candidates = parse_outline(snapshot, artifacts, normalized_focus)
    payload: dict[str, Any] = {
        "schemaVersion": 1,
        "status": "ready",
        "object": {"canonicalName": canonical_name, "kind": "Document"},
        "focusTerms": list(normalized_focus),
        "metadata": metadata,
        "artifacts": artifacts,
        "bsl": {"outline": outline},
        "forms": parse_forms(snapshot, artifacts),
        "relations": {"confirmed": confirmed_relations(snapshot, name), "candidates": candidates},
        "unknown": ["BSL lexical candidates are not semantic links; inspect their cited source before using them."],
        "unsupported": ["Non-Document metadata objects", "recursive relation graph", "BSL bodies and full AST"],
        "truncated": False,
        "diagnostics": [],
    }
    apply_limits(payload, limit)
    while len(encode(payload).encode("utf-8")) > DEFAULT_BYTE_LIMIT and limit > 1:
        limit = max(1, limit // 2)
        apply_limits(payload, limit)
        payload["diagnostics"] = sorted(set(payload["diagnostics"] + ["byteLimit"]))
        payload["truncated"] = True
    if len(encode(payload).encode("utf-8")) > DEFAULT_BYTE_LIMIT:
        raise InputBlocked("result_too_large", "minimum bounded result exceeds 32 KiB")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect_parser = commands.add_parser("inspect", help="inspect one canonical Document object")
    inspect_parser.add_argument("--snapshot", required=True, type=Path)
    inspect_parser.add_argument("--object", required=True)
    inspect_parser.add_argument("--focus", action="append", default=[], help="optional term for BSL lexical candidates")
    inspect_parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    args = parser.parse_args(argv)
    if args.limit < 1 or args.limit > 64:
        print(encode(block("invalid_limit", "limit must be between 1 and 64")), end="")
        return 2
    try:
        result = inspect(args.snapshot, args.object, args.limit, args.focus)
    except InputBlocked as exc:
        print(encode(block(exc.reason_code, str(exc))), end="")
        return 2
    print(encode(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
