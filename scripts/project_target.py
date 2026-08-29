#!/usr/bin/env python3
"""Verify this repository's one declared 1C target before native work."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _one_child(element: ET.Element, name: str) -> ET.Element:
    matches = [child for child in element if _local_name(child.tag) == name]
    if len(matches) != 1:
        raise ValueError(f"Configuration.xml must contain exactly one {name} at the declared locator")
    return matches[0]


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _repo_path(repo_root: Path, value: object, *, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty repository-relative path")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{field} must stay within repository")
    current = repo_root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"{field} contains a symlink component")
    resolved = current.resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ValueError(f"{field} must stay within repository") from exc
    return resolved


def _require_single_link(path: Path, *, field: str) -> None:
    if path.stat().st_nlink != 1:
        raise ValueError(f"{field} must have exactly one hard link")


def _manifest_entries(payload: bytes) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line_number, line in enumerate(payload.decode("utf-8").splitlines(), 1):
        digest, separator, relative = line.partition("  ")
        if (
            separator != "  "
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            or not relative
            or relative.startswith("/")
            or ".." in Path(relative).parts
        ):
            raise ValueError(f"invalid snapshot manifest line: {line_number}")
        if relative in entries:
            raise ValueError(f"duplicate snapshot manifest path: {relative}")
        entries[relative] = digest
    return entries


def _verify_snapshot(snapshot: Path, manifest_entries: dict[str, str], expected_count: int) -> int:
    snapshot_entries = list(snapshot.rglob("*"))
    for path in snapshot_entries:
        relative = path.relative_to(snapshot).as_posix()
        if path.is_symlink():
            raise ValueError(f"snapshot contains symlink: {relative}")
        if not path.is_dir() and not path.is_file():
            raise ValueError(f"snapshot contains non-regular entry: {relative}")
        if path.is_file() and path.stat().st_nlink != 1:
            raise ValueError(f"snapshot contains multiply-linked file: {relative}")
    snapshot_files = {
        path.relative_to(snapshot).as_posix(): path
        for path in snapshot_entries
        if path.is_file()
    }
    file_count = len(snapshot_files)
    if file_count != expected_count:
        raise ValueError(
            f"snapshot file count mismatch: expected {expected_count}, got {file_count}"
        )
    if set(snapshot_files) != set(manifest_entries):
        raise ValueError("snapshot paths do not match manifest")
    for relative, path in sorted(snapshot_files.items()):
        if _sha256(path) != manifest_entries[relative]:
            raise ValueError(f"snapshot content mismatch: {relative}")
    return file_count


def verify(repo_root: Path) -> dict[str, object]:
    contract_path = _repo_path(
        repo_root,
        "project-target.json",
        field="project-target.json",
    )
    _require_single_link(contract_path, field="project-target.json")
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(
        contract_bytes.decode("utf-8"),
        object_pairs_hook=_unique_json_object,
    )
    expected_keys = {
        "schemaVersion", "configuration", "sourceCf", "snapshot", "dailyNativeRoute"
    }
    if not isinstance(contract, dict) or set(contract) != expected_keys:
        raise ValueError(
            "contract keys mismatch: expected configuration, dailyNativeRoute, schemaVersion, snapshot, sourceCf"
        )
    schema_version = contract["schemaVersion"]
    if type(schema_version) is not int:
        raise ValueError("schemaVersion must be integer 1")
    if schema_version != 1:
        raise ValueError(f"unsupported schemaVersion: {schema_version}")
    nested_shapes = {
        "configuration": {"name", "version"},
        "sourceCf": {"path", "sha256"},
        "snapshot": {"path", "manifestPath", "manifestSha256", "fileCount"},
    }
    for field, keys in nested_shapes.items():
        value = contract[field]
        if not isinstance(value, dict) or set(value) != keys:
            raise ValueError(f"{field} keys mismatch: expected {', '.join(sorted(keys))}")
    file_count_contract = contract["snapshot"]["fileCount"]
    if type(file_count_contract) is not int or file_count_contract < 1:
        raise ValueError("snapshot.fileCount must be a positive integer")
    if contract["dailyNativeRoute"] != "scripts/native_cycle.py run-prepared":
        raise ValueError("dailyNativeRoute must be scripts/native_cycle.py run-prepared")
    source = _repo_path(repo_root, contract["sourceCf"]["path"], field="sourceCf.path")
    snapshot = _repo_path(repo_root, contract["snapshot"]["path"], field="snapshot.path")
    manifest = _repo_path(
        repo_root,
        contract["snapshot"]["manifestPath"],
        field="snapshot.manifestPath",
    )
    _require_single_link(source, field="source CF")
    _require_single_link(manifest, field="snapshot manifest")

    source_actual = _sha256(source)
    if source_actual != contract["sourceCf"]["sha256"]:
        raise ValueError("source CF SHA-256 mismatch")
    manifest_bytes = manifest.read_bytes()
    manifest_actual = hashlib.sha256(manifest_bytes).hexdigest()
    if manifest_actual != contract["snapshot"]["manifestSha256"]:
        raise ValueError("snapshot manifest SHA-256 mismatch")
    manifest_entries = _manifest_entries(manifest_bytes)
    file_count = _verify_snapshot(snapshot, manifest_entries, file_count_contract)

    configuration_bytes = (snapshot / "Configuration.xml").read_bytes()
    if hashlib.sha256(configuration_bytes).hexdigest() != manifest_entries["Configuration.xml"]:
        raise ValueError("snapshot content mismatch: Configuration.xml")
    root = ET.fromstring(configuration_bytes)
    configuration = _one_child(root, "Configuration")
    properties = _one_child(configuration, "Properties")
    name = _one_child(properties, "Name").text or ""
    version = _one_child(properties, "Version").text or ""
    actual_configuration = {"name": name, "version": version}
    if actual_configuration != contract["configuration"]:
        raise ValueError("configuration name/version mismatch")

    if contract_path.read_bytes() != contract_bytes:
        raise ValueError("project target contract changed during verification")
    if _sha256(source) != source_actual:
        raise ValueError("source CF changed during verification")
    final_manifest_bytes = manifest.read_bytes()
    if final_manifest_bytes != manifest_bytes:
        raise ValueError("snapshot manifest changed during verification")
    final_manifest_entries = _manifest_entries(final_manifest_bytes)
    if final_manifest_entries != manifest_entries:
        raise ValueError("snapshot manifest entries changed during verification")
    _verify_snapshot(snapshot, final_manifest_entries, file_count_contract)

    return {
        "status": "ready",
        "configuration": actual_configuration,
        "sourceCf": {
            "path": contract["sourceCf"]["path"],
            "expectedSha256": contract["sourceCf"]["sha256"],
            "actualSha256": source_actual,
        },
        "snapshot": {
            "path": contract["snapshot"]["path"],
            "manifestPath": contract["snapshot"]["manifestPath"],
            "expectedManifestSha256": contract["snapshot"]["manifestSha256"],
            "actualManifestSha256": manifest_actual,
            "expectedFileCount": contract["snapshot"]["fileCount"],
            "actualFileCount": file_count,
        },
        "dailyNativeRoute": contract["dailyNativeRoute"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        result = verify(args.repo_root.resolve())
    except Exception as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
