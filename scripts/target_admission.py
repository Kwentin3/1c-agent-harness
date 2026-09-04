"""The one authoritative contract/admission/store boundary for project targets."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import uuid
import xml.etree.ElementTree as ET


class TargetBlocked(Exception):
    def __init__(self, reason_code: str, message: str, *, locator: str | None = None) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.message = message
        self.locator = locator


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def repo_path(repo_root: Path, value: object, *, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty repository-relative path")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{field} must stay within repository")
    current = repo_root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"{field} contains a symlink")
    resolved = current.resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ValueError(f"{field} must stay within repository") from exc
    return resolved


def require_one_link(path: Path) -> None:
    if path.stat().st_nlink != 1:
        raise ValueError("identity input has multiple hard links")


def digest_value(value: object) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        raise ValueError("identity must use sha256:<64 lowercase hex>")
    result = value[7:]
    if len(result) != 64 or any(ch not in "0123456789abcdef" for ch in result):
        raise ValueError("identity must use sha256:<64 lowercase hex>")
    return result


def manifest_entries(payload: bytes) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in payload.decode("utf-8").splitlines():
        digest, separator, relative = line.partition("  ")
        if (separator != "  " or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest)
                or not relative or relative.startswith("/") or ".." in Path(relative).parts or relative in entries):
            raise ValueError("invalid snapshot manifest")
        entries[relative] = digest
    return entries


def tree_manifest(root: Path) -> bytes:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("tree must be a non-symlink directory")
    records: list[str] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
            raise ValueError("tree contains unsafe entry")
        if path.is_file():
            if path.stat().st_nlink != 1:
                raise ValueError("tree contains multiply-linked file")
            records.append(f"{sha256(path)}  {relative}\n")
    return "".join(records).encode("utf-8")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def one_child(parent: ET.Element, name: str) -> ET.Element:
    matches = [child for child in parent if local_name(child.tag) == name]
    if len(matches) != 1:
        raise ValueError("Configuration.xml does not have declared identity locator")
    return matches[0]


def load_contract(repo_root: Path) -> tuple[dict[str, object], bytes]:
    path = repo_path(repo_root, "project-target.json", field="project target contract")
    require_one_link(path)
    payload = path.read_bytes()
    contract = json.loads(payload.decode("utf-8"), object_pairs_hook=unique_object)
    if not isinstance(contract, dict) or set(contract) != {"schemaVersion", "configuration", "source", "snapshot", "dailyNativeRoute"}:
        raise ValueError("project target contract keys are invalid")
    if type(contract["schemaVersion"]) is not int or contract["schemaVersion"] != 2:
        raise ValueError("project target schemaVersion is unsupported")
    configuration = contract["configuration"]
    snapshot = contract["snapshot"]
    source = contract["source"]
    if not isinstance(configuration, dict) or set(configuration) != {"name", "version"} or not all(isinstance(configuration[x], str) and configuration[x] for x in ("name", "version")):
        raise ValueError("configuration identity is invalid")
    if not isinstance(snapshot, dict) or set(snapshot) != {"root", "manifest", "contentId", "fileCount"}:
        raise ValueError("snapshot contract is invalid")
    digest_value(snapshot["contentId"])
    if type(snapshot["fileCount"]) is not int or snapshot["fileCount"] < 1:
        raise ValueError("snapshot file count is invalid")
    if not isinstance(source, dict) or source.get("kind") not in {"cf", "hierarchical"}:
        raise TargetBlocked("unsupported_source", "source kind is unsupported")
    if source["kind"] == "cf":
        if set(source) != {"kind", "path", "sha256"} or not isinstance(source["sha256"], str):
            raise ValueError("CF source contract is invalid")
        digest_value("sha256:" + source["sha256"])
    else:
        if set(source) != {"kind", "path", "contentId", "fileCount"}:
            raise ValueError("hierarchical source contract is invalid")
        digest_value(source["contentId"])
        if type(source["fileCount"]) is not int or source["fileCount"] < 1:
            raise ValueError("hierarchical source file count is invalid")
    if contract["dailyNativeRoute"] != "scripts/shared_task_route.py run":
        raise ValueError("daily native route is invalid")
    return contract, payload


def admit_snapshot(snapshot: Path, manifest: Path, contract: dict[str, object], *, read_only: bool) -> None:
    definition = contract["snapshot"]
    configuration = contract["configuration"]
    assert isinstance(definition, dict) and isinstance(configuration, dict)
    if snapshot.is_symlink() or not snapshot.is_dir() or manifest.is_symlink() or not manifest.is_file():
        raise ValueError("snapshot or manifest is not a regular retained shape")
    require_one_link(manifest)
    payload = manifest.read_bytes()
    if sha256(manifest) != digest_value(definition["contentId"]):
        raise ValueError("snapshot manifest identity mismatch")
    entries = manifest_entries(payload)
    actual = tree_manifest(snapshot)
    if actual != payload or len(entries) != definition["fileCount"]:
        raise ValueError("snapshot tree does not match manifest")
    configuration_path = snapshot / "Configuration.xml"
    if not configuration_path.is_file():
        raise ValueError("snapshot Configuration.xml is missing")
    root = ET.fromstring(configuration_path.read_bytes())
    properties = one_child(one_child(root, "Configuration"), "Properties")
    if {"name": one_child(properties, "Name").text or "", "version": one_child(properties, "Version").text or ""} != configuration:
        raise ValueError("snapshot configuration identity mismatch")
    if read_only and any(item.lstat().st_mode & 0o222 for item in (snapshot, manifest, *snapshot.rglob("*"))):
        raise ValueError("retained snapshot is writable")
    if manifest.read_bytes() != payload or tree_manifest(snapshot) != payload:
        raise ValueError("snapshot changed during admission")


def source_identity(contract: dict[str, object]) -> str:
    source = contract["source"]
    assert isinstance(source, dict)
    return f"sha256:{source['sha256']}" if source["kind"] == "cf" else str(source["contentId"])


def binding_bytes(contract: dict[str, object]) -> bytes:
    snapshot = contract["snapshot"]
    assert isinstance(snapshot, dict)
    return (json.dumps({"schemaVersion": 1, "sourceIdentity": source_identity(contract), "snapshotContentId": snapshot["contentId"]}, sort_keys=True, separators=(",", ":")) + "\n").encode()


def admit_target(target: Path, snapshot: Path, manifest: Path, binding: Path, contract: dict[str, object]) -> None:
    if target.is_symlink() or not target.is_dir() or {item.name for item in target.iterdir()} != {snapshot.name, manifest.name, binding.name}:
        raise ValueError("retained target shape is invalid")
    if binding.is_symlink() or not binding.is_file() or binding.read_bytes() != binding_bytes(contract) or binding.lstat().st_mode & 0o222:
        raise ValueError("retained source binding is invalid")
    require_one_link(binding)
    admit_snapshot(snapshot, manifest, contract, read_only=True)


def freeze(snapshot: Path, manifest: Path, binding: Path) -> None:
    for path in (snapshot, manifest, binding, *snapshot.rglob("*")):
        path.chmod(path.lstat().st_mode & ~0o222)


def remove_owned(path: Path) -> None:
    if not path.exists():
        return
    if path.is_symlink() or not path.is_dir():
        raise RuntimeError("owned cleanup target is invalid")
    entries = sorted((path, *path.rglob("*")), key=lambda item: len(item.parts), reverse=True)
    for item in entries:
        mode = item.lstat().st_mode
        if stat.S_ISLNK(mode):
            item.unlink()
        elif stat.S_ISREG(mode):
            item.chmod(mode | stat.S_IRUSR | stat.S_IWUSR)
            item.unlink()
        elif stat.S_ISDIR(mode):
            item.chmod(mode | stat.S_IRWXU)
            item.rmdir()
        else:
            raise RuntimeError("owned cleanup target has special entry")


def paths(repo_root: Path, contract: dict[str, object]) -> tuple[Path, Path, Path, Path, Path]:
    definition = contract["snapshot"]
    assert isinstance(definition, dict)
    snapshot = repo_path(repo_root, definition["root"], field="snapshot root")
    manifest = repo_path(repo_root, definition["manifest"], field="snapshot manifest")
    target, base, binding = snapshot.parent, repo_root / ".local/targets", snapshot.parent / "source.json"
    if manifest.parent != target or target.parent != base or len({snapshot.name, manifest.name, binding.name}) != 3:
        raise ValueError("retained target paths are invalid")
    return base, target, snapshot, manifest, binding


def snapshot_ref(contract: dict[str, object], action: str) -> dict[str, object]:
    snapshot = contract["snapshot"]; configuration = contract["configuration"]
    assert isinstance(snapshot, dict) and isinstance(configuration, dict)
    return {"schemaVersion": 1, "status": "ready", "action": action, "sourceIdentity": source_identity(contract), "snapshot": {"kind": "1c-configuration-files", "format": "hierarchical", "root": snapshot["root"], "manifest": snapshot["manifest"], "contentId": snapshot["contentId"], "fileCount": snapshot["fileCount"], "configuration": configuration}}


def resolve_snapshot_ref(repo_root: Path, ref_path: Path) -> tuple[Path, dict[str, str]]:
    """Resolve one exact data-only SnapshotRef through the retained-target boundary."""
    try:
        contract, _ = load_contract(repo_root)
        if ref_path.is_symlink() or not ref_path.is_file() or ref_path.stat().st_size > 16 * 1024:
            raise ValueError("invalid snapshot reference")
        actual = json.loads(ref_path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
        if not isinstance(actual, dict) or actual.get("action") not in {"materialized", "reused"}:
            raise ValueError("invalid snapshot reference")
        if actual != snapshot_ref(contract, str(actual["action"])):
            raise ValueError("snapshot reference does not match target")
        _base, target, snapshot, manifest, binding = paths(repo_root, contract)
        admit_target(target, snapshot, manifest, binding, contract)
        return snapshot, manifest_entries(manifest.read_bytes())
    except TargetBlocked:
        raise
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise TargetBlocked("snapshot_invalid", "SnapshotRef is not admitted") from exc
