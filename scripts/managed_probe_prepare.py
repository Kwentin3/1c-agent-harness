#!/usr/bin/env python3
"""Fail-closed primitive for a disposable managed-application probe tree.

The caller owns the probe's request and receipt grammar. This module owns only
copying a source tree, placing supplied client/server blocks in the two declared
modules, checking the exact file-content closure, and freezing the prepared tree.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import shutil
import stat
from typing import Any
from xml.etree import ElementTree


MANAGED_RELATIVE = Path("Ext/ManagedApplicationModule.bsl")
SERVER_RELATIVE = Path("CommonModules/JetServerCall/Ext/Module.bsl")
SERVER_METADATA_RELATIVE = Path("CommonModules/JetServerCall.xml")
_ALLOWED_CHANGED = (SERVER_RELATIVE.as_posix(), MANAGED_RELATIVE.as_posix())
_FORBIDDEN_GENERATED = {
    "Execute": rb"(?i)\bexecute\s*\(",
    "Eval": rb"(?i)\beval\s*\(",
    "Documents": rb"(?i)\bdocuments\s*\.",
    "Catalogs": rb"(?i)\bcatalogs\s*\.",
    "InventoryTransfer": rb"(?i)\binventorytransfer\b",
    "ErrorDescription": rb"(?i)\berrordescription\b",
    "ErrorInfo": rb"(?i)\berrorinfo\b",
    "Chr": rb"(?i)\bchr\s*\(",
}


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _repo_relative(repo_root: Path, candidate: Path, *, field: str, inside: Path) -> Path:
    repo_root = repo_root.resolve()
    if candidate.is_absolute():
        raw = candidate
        try:
            relative = raw.relative_to(repo_root)
        except ValueError as exc:
            raise ValueError(f"{field} must be inside repository") from exc
    else:
        relative = candidate
        raw = repo_root / relative
    if not relative.parts or ".." in relative.parts:
        raise ValueError(f"{field} must be a descendant of repository")
    current = repo_root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"{field} contains symlink path component: {current}")
    resolved = raw.resolve(strict=False)
    try:
        resolved.relative_to(inside.resolve())
    except ValueError as exc:
        raise ValueError(f"{field} must be inside {inside}") from exc
    return raw


def _line_ending(payload: bytes) -> bytes:
    return b"\r\n" if b"\r\n" in payload else b"\n"


def _onstart_bounds(payload: bytes) -> tuple[int, int, int]:
    starts = list(re.finditer(
        rb"(?im)^[ \t]*Procedure[ \t]+OnStart[ \t]*\([ \t]*\)[ \t]*(?://[^\r\n]*)?\r?\n",
        payload,
    ))
    if len(starts) != 1:
        raise ValueError(f"expected exactly one Procedure OnStart(), found {len(starts)}")
    start = starts[0]
    end = re.search(rb"(?im)^[ \t]*EndProcedure[ \t]*(?://[^\r\n]*)?\r?(?:\n|$)", payload[start.end():])
    if end is None:
        raise ValueError("OnStart has no matching EndProcedure")
    end_at = start.end() + end.end()
    insertion_at = start.end()
    awaiting_var_terminator = False
    for line in payload[start.end():end_at].splitlines(keepends=True):
        stripped = line.strip()
        uncommented = line.split(b"//", 1)[0]
        if awaiting_var_terminator:
            insertion_at += len(line)
            awaiting_var_terminator = b";" not in uncommented
            continue
        if not stripped or stripped.startswith(b"//"):
            insertion_at += len(line)
            continue
        if re.match(rb"(?i)^Var\b", stripped):
            insertion_at += len(line)
            awaiting_var_terminator = b";" not in uncommented
            continue
        break
    if awaiting_var_terminator:
        raise ValueError("OnStart has an unterminated Var declaration")
    return start.start(), insertion_at, end_at


def _ensure_server_call_metadata(payload: bytes) -> None:
    if len(payload) > 1_048_576:
        raise ValueError("JetServerCall metadata exceeds 1 MiB safety limit")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("JetServerCall metadata must be UTF-8") from exc
    if "\x00" in text:
        raise ValueError("JetServerCall metadata must not contain NUL")
    if re.search(r"(?i)<![ \t\r\n]*(?:doctype|entity)\b", text):
        raise ValueError("JetServerCall metadata must not contain a DTD or entity declaration")
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        raise ValueError("JetServerCall metadata is not valid XML") from exc

    def value(name: str) -> str:
        matches = [
            (element.text or "").strip()
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] == name
        ]
        if len(matches) != 1:
            raise ValueError(f"JetServerCall metadata must declare exactly one {name}")
        return matches[0]

    if value("Server") != "true" or value("ServerCall") != "true":
        raise ValueError("JetServerCall metadata must declare Server=true and ServerCall=true")


def _content_hashes(root: Path) -> dict[str, str]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"tree must be a non-symlink directory: {root}")
    hashes: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"tree contains symlink: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f"tree contains non-regular entry: {path}")
        hashes[path.relative_to(root).as_posix()] = _sha256(path.read_bytes())
    return hashes


def _validate_blocks(client_block: bytes, server_block: bytes) -> list[str]:
    for label, block in (("clientBlock", client_block), ("serverBlock", server_block)):
        if not isinstance(block, bytes) or not block:
            raise ValueError(f"{label} must be non-empty bytes")
        if b"\x00" in block:
            raise ValueError(f"{label} contains NUL")
        try:
            block.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ValueError(f"{label} must be ASCII") from exc
    generated = client_block + b"\n" + server_block
    return [label for label, pattern in _FORBIDDEN_GENERATED.items() if re.search(pattern, generated)]


def _freeze_tree(root: Path) -> None:
    for path in sorted((root, *root.rglob("*")), key=lambda item: len(item.parts), reverse=True):
        path.chmod(path.stat().st_mode & ~0o222)


def _remove_prepared_tree(prepared_root: Path) -> None:
    if not prepared_root.exists():
        return
    if prepared_root.is_symlink() or not prepared_root.is_dir():
        raise ValueError(f"refusing to remove non-directory preparedRoot: {prepared_root}")
    for path in sorted((prepared_root, *prepared_root.rglob("*")), key=lambda item: len(item.parts), reverse=True):
        if path.is_symlink():
            raise ValueError(f"refusing to remove prepared tree containing symlink: {path}")
        mode = path.stat().st_mode
        if path.is_dir():
            path.chmod(mode | stat.S_IRWXU)
        else:
            path.chmod(mode | stat.S_IWUSR)
    shutil.rmtree(prepared_root)


def discard_prepared_tree(*, repo_root: Path, prepared_root: Path) -> None:
    """Safely remove one known disposable prepared child after a later-stage error."""
    repo_root = repo_root.resolve()
    validated = _repo_relative(
        repo_root,
        prepared_root,
        field="preparedRoot",
        inside=repo_root / ".local" / "prepared",
    )
    if validated == repo_root / ".local" / "prepared":
        raise ValueError("preparedRoot must be a strict child of .local/prepared")
    _remove_prepared_tree(validated)


def prepare_probe(
    *,
    repo_root: Path,
    snapshot_root: Path,
    prepared_root: Path,
    client_block: bytes,
    server_block: bytes,
) -> dict[str, Any]:
    """Create one frozen prepared tree from caller-supplied, statically audited blocks."""
    repo_root = repo_root.resolve()
    snapshot_root = _repo_relative(repo_root, snapshot_root, field="snapshotRoot", inside=repo_root)
    prepared_base = repo_root / ".local" / "prepared"
    prepared_root = _repo_relative(repo_root, prepared_root, field="preparedRoot", inside=prepared_base)
    if prepared_root == prepared_base:
        raise ValueError("preparedRoot must be a strict child of .local/prepared")
    if not snapshot_root.is_dir() or snapshot_root.is_symlink():
        raise ValueError("snapshotRoot must be a non-symlink directory")
    if prepared_root.exists() or prepared_root.is_symlink():
        raise FileExistsError(f"preparedRoot already exists: {prepared_root}")

    forbidden = _validate_blocks(client_block, server_block)
    if forbidden:
        raise ValueError(f"generated probe contains forbidden terms: {forbidden}")
    source_hashes = _content_hashes(snapshot_root)
    source_client = (snapshot_root / MANAGED_RELATIVE).read_bytes()
    source_server = (snapshot_root / SERVER_RELATIVE).read_bytes()
    _ensure_server_call_metadata((snapshot_root / SERVER_METADATA_RELATIVE).read_bytes())
    procedure_start, insertion_at, procedure_end = _onstart_bounds(source_client)
    prepared_client = source_client[:insertion_at] + client_block + source_client[insertion_at:]
    separator = b"" if source_server.endswith((b"\n", b"\r")) else _line_ending(source_server)
    prepared_server = source_server + separator + server_block

    try:
        shutil.copytree(snapshot_root, prepared_root, copy_function=shutil.copy2)
        for relative in (MANAGED_RELATIVE, SERVER_RELATIVE):
            target = prepared_root / relative
            target.chmod(target.stat().st_mode | stat.S_IWUSR)
        (prepared_root / MANAGED_RELATIVE).write_bytes(prepared_client)
        (prepared_root / SERVER_RELATIVE).write_bytes(prepared_server)
        _freeze_tree(prepared_root)
        prepared_hashes = _content_hashes(prepared_root)
        changed_paths = sorted(
            path
            for path in set(source_hashes) | set(prepared_hashes)
            if source_hashes.get(path) != prepared_hashes.get(path)
        )
        if tuple(changed_paths) != _ALLOWED_CHANGED:
            raise RuntimeError(f"changed path closure mismatch: {changed_paths}")
    except Exception:
        _remove_prepared_tree(prepared_root)
        raise

    return {
        "schemaVersion": 1,
        "staticCheck": "pass",
        "snapshotRoot": snapshot_root.relative_to(repo_root).as_posix(),
        "preparedRoot": prepared_root.relative_to(repo_root).as_posix(),
        "changedPaths": changed_paths,
        "client": {
            "sourceSha256": _sha256(source_client),
            "preparedSha256": _sha256(prepared_client),
            "prefixSha256": _sha256(source_client[:procedure_start]),
            "suffixSha256": _sha256(source_client[procedure_end:]),
            "addedSha256": _sha256(client_block),
        },
        "server": {
            "sourceSha256": _sha256(source_server),
            "preparedSha256": _sha256(prepared_server),
            "addedSha256": _sha256(server_block),
        },
        "forbiddenAddedMatches": forbidden,
    }
