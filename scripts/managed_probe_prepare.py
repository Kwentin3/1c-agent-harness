#!/usr/bin/env python3
"""Fail-closed primitive for a disposable managed-application probe tree.

The caller owns the probe's request and receipt grammar. This module owns
copying a source tree, placing supplied client/server blocks in the two declared
modules, checking the exact file-content closure, freezing the prepared tree,
and issuing the shared provenance receipt after the task oracle passes.
"""

from __future__ import annotations

import base64
import difflib
import hashlib
import json
from pathlib import Path
import re
import shutil
import stat
from subprocess import PIPE, run as _run
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


def _disjoint(first: Path, second: Path) -> bool:
    first = first.resolve(strict=False)
    second = second.resolve(strict=False)
    try:
        first.relative_to(second)
    except ValueError:
        try:
            second.relative_to(first)
        except ValueError:
            return True
    return False


def _line_ending(payload: bytes) -> bytes:
    return b"\r\n" if b"\r\n" in payload else b"\n"


def _has_unquoted_semicolon(line: bytes) -> bool:
    in_string = False
    index = 0
    while index < len(line):
        current = line[index]
        following = line[index + 1] if index + 1 < len(line) else None
        if current == ord('"'):
            if in_string and following == ord('"'):
                index += 2
                continue
            in_string = not in_string
        elif not in_string and current == ord('/') and following == ord('/'):
            return False
        elif not in_string and current == ord(';'):
            return True
        index += 1
    return False


def _onstart_bounds(payload: bytes) -> tuple[int, int, int]:
    starts = list(re.finditer(
        rb"(?im)^(?:\xef\xbb\xbf)?[ \t]*Procedure[ \t]+OnStart[ \t]*\([ \t]*\)[ \t]*(?://[^\r\n]*)?\r?\n",
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
        has_terminator = _has_unquoted_semicolon(line)
        if awaiting_var_terminator:
            insertion_at += len(line)
            awaiting_var_terminator = not has_terminator
            continue
        if not stripped or stripped.startswith(b"//"):
            insertion_at += len(line)
            continue
        if re.match(rb"(?i)^Var\b", stripped):
            insertion_at += len(line)
            awaiting_var_terminator = not has_terminator
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


def _content_identity(hashes: dict[str, str]) -> dict[str, object]:
    digest = hashlib.sha256()
    for relative, value in sorted(hashes.items()):
        digest.update(relative.encode("utf-8") + b"\0" + bytes.fromhex(value))
    return {"files": len(hashes), "sha256": digest.hexdigest()}


def _unified_patch(relative: Path, before: bytes, after: bytes) -> bytes:
    return b"".join(difflib.diff_bytes(
        difflib.unified_diff,
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{relative.as_posix()}".encode("ascii"),
        tofile=f"b/{relative.as_posix()}".encode("ascii"),
    ))


def _json_copy(value: object) -> object:
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return _sha256(payload.encode("utf-8"))


def _require_sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return value


def _require_tree_identity(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != {"files", "directories", "bytes", "sha256"}:
        raise ValueError(f"{field} must be one complete tree identity")
    if any(type(value[key]) is not int or value[key] < 0 for key in ("files", "directories", "bytes")):
        raise ValueError(f"{field} counters must be non-negative integers")
    _require_sha256(value["sha256"], f"{field}.sha256")
    return value


def _raw_receipt(payload: bytes) -> dict[str, object]:
    if not isinstance(payload, bytes) or not payload:
        raise ValueError("raw receipt must be non-empty bytes")
    return {"bytes": len(payload), "sha256": _sha256(payload), "base64": base64.b64encode(payload).decode("ascii")}


def build_provenance_receipt(
    *, preparation: dict[str, object], request: dict[str, object], runner: dict[str, object],
    client_receipt: bytes, server_receipt: bytes, business_payload: object,
    oracle: dict[str, object], prepared_cleanup: str,
) -> dict[str, object]:
    """Issue one generic receipt after a task oracle accepts opaque business bytes."""
    prepared = _require_tree_identity(preparation.get("runnerInput"), "preparation.runnerInput")
    invocation = runner.get("preparedInvocation")
    if not isinstance(invocation, dict):
        raise ValueError("runner omitted preparedInvocation")
    frozen = invocation.get("frozenInput")
    input_chain = {
        "prepared": _json_copy(prepared),
        "sourceBefore": _json_copy(invocation.get("sourceBefore")),
        "sourceAfter": _json_copy(invocation.get("sourceAfter")),
        "copiedBeforeFreeze": _json_copy(invocation.get("copiedBeforeFreeze")),
        "frozen": _json_copy(frozen.get("identity")) if isinstance(frozen, dict) else None,
        "inputAfter": _json_copy(runner.get("inputAfter")),
    }
    if any(_require_tree_identity(value, f"input.{key}") != prepared for key, value in input_chain.items()):
        raise ValueError("prepared/frozen runner input identity mismatch")
    runtime, cleanup = runner.get("runtime"), runner.get("storageCompaction")
    if runner.get("status") != "runtime_contract_completed" or not isinstance(runtime, dict):
        raise ValueError("runner did not complete the runtime contract")
    if not isinstance(cleanup, dict):
        raise ValueError("runner omitted cleanup result")
    client, server = _raw_receipt(client_receipt), _raw_receipt(server_receipt)
    request_sha, payload_sha = _canonical_sha256(request), _canonical_sha256(business_payload)
    oracle_binding = dict(oracle)
    oracle_binding.update({"requestSha256": request_sha, "businessPayloadSha256": payload_sha, "serverReceiptSha256": server["sha256"]})
    receipt = {
        "schemaVersion": 1,
        "canonicalBase": _json_copy(preparation.get("canonicalBase")),
        "patches": _json_copy(preparation.get("patches")),
        "changedPaths": sorted(preparation.get("changedPaths", [])),
        "input": input_chain,
        "request": {"payload": _json_copy(request), "sha256": request_sha},
        "runtime": {"status": runner.get("status"), "completed": runtime.get("completed"), "clientReceipt": client},
        "cleanup": {"runner": _json_copy(cleanup), "preparedTree": prepared_cleanup},
        "business": {"rawReceipt": server, "payload": _json_copy(business_payload), "payloadSha256": payload_sha},
        "oracle": oracle_binding,
    }
    validate_provenance_receipt(receipt)
    return receipt


def validate_provenance_receipt(receipt: dict[str, object]) -> dict[str, object]:
    expected = {"schemaVersion", "canonicalBase", "patches", "changedPaths", "input", "request", "runtime", "cleanup", "business", "oracle"}
    if not isinstance(receipt, dict) or set(receipt) != expected or receipt.get("schemaVersion") != 1:
        raise ValueError("provenance receipt schema mismatch")
    canonical = receipt["canonicalBase"]
    if not isinstance(canonical, dict) or set(canonical) != {"files", "sha256"} or type(canonical["files"]) is not int or canonical["files"] <= 0:
        raise ValueError("canonical base identity mismatch")
    _require_sha256(canonical["sha256"], "canonicalBase.sha256")
    patches = receipt["patches"]
    if not isinstance(patches, list) or not patches:
        raise ValueError("patch set is empty")
    roles: set[str] = set()
    for patch in patches:
        if not isinstance(patch, dict) or set(patch) != {"role", "sha256"} or not isinstance(patch["role"], str) or not patch["role"] or patch["role"] in roles:
            raise ValueError("patch binding mismatch")
        roles.add(patch["role"]); _require_sha256(patch["sha256"], "patch.sha256")
    changed = receipt["changedPaths"]
    if not isinstance(changed, list) or not changed or changed != sorted(set(changed)) or not all(isinstance(path, str) and path and not Path(path).is_absolute() and ".." not in Path(path).parts for path in changed):
        raise ValueError("changed-path closure mismatch")
    input_chain = receipt["input"]
    if not isinstance(input_chain, dict) or set(input_chain) != {"prepared", "sourceBefore", "sourceAfter", "copiedBeforeFreeze", "frozen", "inputAfter"}:
        raise ValueError("input chain mismatch")
    prepared = _require_tree_identity(input_chain["prepared"], "input.prepared")
    if any(_require_tree_identity(value, f"input.{key}") != prepared for key, value in input_chain.items()):
        raise ValueError("prepared/frozen input mismatch")
    request = receipt["request"]
    if not isinstance(request, dict) or set(request) != {"payload", "sha256"} or request["sha256"] != _canonical_sha256(request["payload"]):
        raise ValueError("request binding mismatch")
    runtime = receipt["runtime"]
    if not isinstance(runtime, dict) or set(runtime) != {"status", "completed", "clientReceipt"} or runtime["status"] != "runtime_contract_completed" or runtime["completed"] is not True:
        raise ValueError("runtime is incomplete")
    cleanup = receipt["cleanup"]
    if not isinstance(cleanup, dict) or set(cleanup) != {"runner", "preparedTree"} or cleanup.get("preparedTree") != "discarded":
        raise ValueError("prepared cleanup is incomplete")
    runner_cleanup = cleanup["runner"]
    if not isinstance(runner_cleanup, dict) or runner_cleanup.get("status") != "completed" or runner_cleanup.get("manualCleanupActions") != 0:
        raise ValueError("runner cleanup is incomplete")
    business = receipt["business"]
    if not isinstance(business, dict) or set(business) != {"rawReceipt", "payload", "payloadSha256"} or business["payloadSha256"] != _canonical_sha256(business["payload"]):
        raise ValueError("business payload binding mismatch")
    for label, raw in (("client", runtime["clientReceipt"]), ("server", business["rawReceipt"])):
        if not isinstance(raw, dict) or set(raw) != {"bytes", "sha256", "base64"}:
            raise ValueError(f"{label} receipt binding mismatch")
        decoded = base64.b64decode(raw["base64"], validate=True)
        if raw["bytes"] != len(decoded) or raw["sha256"] != _sha256(decoded):
            raise ValueError(f"{label} receipt byte/hash mismatch")
    oracle = receipt["oracle"]
    bindings = {"requestSha256": request["sha256"], "businessPayloadSha256": business["payloadSha256"], "serverReceiptSha256": business["rawReceipt"]["sha256"]}
    if not isinstance(oracle, dict) or oracle.get("status") != "PASS" or any(oracle.get(key) != value for key, value in bindings.items()):
        raise ValueError("task oracle binding mismatch")
    return {"status": "PASS", "schemaVersion": 1}


def prepare_patched_tree(
    *,
    repo_root: Path,
    snapshot_root: Path,
    prepared_root: Path,
    patches: list[tuple[str, bytes]],
) -> dict[str, object]:
    """Copy canonical input, apply exact unified patches, audit, and freeze it."""
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
    if not isinstance(patches, list) or not patches:
        raise ValueError("patches must be a non-empty ordered list")
    roles: set[str] = set()
    normalized: list[tuple[str, bytes]] = []
    for role, payload in patches:
        if not isinstance(role, str) or not role or role in roles:
            raise ValueError("patch roles must be unique non-empty strings")
        if not isinstance(payload, bytes) or not payload or b"\x00" in payload:
            raise ValueError(f"{role} patch must be non-empty bytes without NUL")
        roles.add(role)
        normalized.append((role, payload))

    source_hashes = _content_hashes(snapshot_root)
    prepared_root.parent.mkdir(parents=True, exist_ok=True)
    if prepared_root.parent.is_symlink() or not prepared_root.parent.is_dir():
        raise ValueError("preparedRoot parent must be a non-symlink directory")
    try:
        prepared_root.mkdir()
    except FileExistsError as exc:
        raise FileExistsError(f"preparedRoot already exists: {prepared_root}") from exc
    try:
        shutil.copytree(snapshot_root, prepared_root, copy_function=shutil.copy2, dirs_exist_ok=True)
        for directory in (prepared_root, *sorted(path for path in prepared_root.rglob("*") if path.is_dir())):
            directory.chmod(directory.stat().st_mode | stat.S_IRWXU)
        for role, payload in normalized:
            for check_only in (True, False):
                command = ["git", "apply", "--no-index", "--whitespace=nowarn"]
                if check_only:
                    command.append("--check")
                completed = _run(
                    command,
                    cwd=prepared_root,
                    input=payload,
                    stdout=PIPE,
                    stderr=PIPE,
                )
                if completed.returncode != 0:
                    detail = completed.stderr.decode("utf-8", errors="replace").strip()
                    raise ValueError(f"{role} patch does not apply exactly: {detail}")
        prepared_hashes = _content_hashes(prepared_root)
        changed_paths = sorted(
            path
            for path in set(source_hashes) | set(prepared_hashes)
            if source_hashes.get(path) != prepared_hashes.get(path)
        )
        if not changed_paths:
            raise ValueError("patch set produced no changed paths")
        _freeze_tree(prepared_root)
    except BaseException as primary_exc:
        try:
            _remove_prepared_tree(prepared_root)
        except BaseException as cleanup_exc:
            raise RuntimeError(
                f"preparation failed: {primary_exc}; prepared cleanup failed: {cleanup_exc}"
            ) from cleanup_exc
        raise

    return {
        "schemaVersion": 1,
        "staticCheck": "pass",
        "snapshotRoot": snapshot_root.relative_to(repo_root).as_posix(),
        "preparedRoot": prepared_root.relative_to(repo_root).as_posix(),
        "canonicalBase": _content_identity(source_hashes),
        "preparedInput": _content_identity(prepared_hashes),
        "patches": [{"role": role, "sha256": _sha256(payload)} for role, payload in normalized],
        "changedPaths": changed_paths,
    }


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
    if not _disjoint(snapshot_root, prepared_root):
        raise ValueError("snapshotRoot and preparedRoot must be disjoint")
    if not snapshot_root.is_dir() or snapshot_root.is_symlink():
        raise ValueError("snapshotRoot must be a non-symlink directory")

    forbidden = _validate_blocks(client_block, server_block)
    if forbidden:
        raise ValueError(f"generated probe contains forbidden terms: {forbidden}")
    source_client = (snapshot_root / MANAGED_RELATIVE).read_bytes()
    source_server = (snapshot_root / SERVER_RELATIVE).read_bytes()
    _ensure_server_call_metadata((snapshot_root / SERVER_METADATA_RELATIVE).read_bytes())
    procedure_start, insertion_at, procedure_end = _onstart_bounds(source_client)
    prepared_client = source_client[:insertion_at] + client_block + source_client[insertion_at:]
    separator = b"" if source_server.endswith((b"\n", b"\r")) else _line_ending(source_server)
    prepared_server = source_server + separator + server_block

    audit = prepare_patched_tree(
        repo_root=repo_root,
        snapshot_root=snapshot_root,
        prepared_root=prepared_root,
        patches=[
            ("instrumentation.client", _unified_patch(MANAGED_RELATIVE, source_client, prepared_client)),
            ("instrumentation.server", _unified_patch(SERVER_RELATIVE, source_server, prepared_server)),
        ],
    )
    changed_paths = audit["changedPaths"]
    if tuple(changed_paths) != _ALLOWED_CHANGED:
        _remove_prepared_tree(prepared_root)
        raise RuntimeError(f"changed path closure mismatch: {changed_paths}")

    return {
        **audit,
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
