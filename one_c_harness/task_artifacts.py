"""Stage bounded task data; existing owners retain source and native lifecycle."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import uuid

from .target_admission import (
    digest_value, repo_path, require_one_link, resolve_snapshot_value, unique_object,
)

__all__ = ["stage_task", "resolve_task"]

MAX_REQUEST_BYTES = 4096
MAX_PATCH_BYTES = 8192
MAX_INPUT_BYTES = 12288
MAX_ORACLE_BYTES = 65536
_MAX_MANIFEST_BYTES = 16384
TASK_NAMESPACE = ".local/task-artifacts"
_FILES = {
    "request": "request.json",
    "productionPatch": "production.patch",
    "instrumentationPatch": "instrumentation.patch",
}


def _json_bytes(value: object, maximum: int) -> bytes:
    try:
        encoder = json.JSONEncoder(
            ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
        )
        chunks: list[bytes] = []
        size = 0
        for chunk in encoder.iterencode(value):
            encoded = chunk.encode("utf-8")
            size += len(encoded)
            if size > maximum:
                raise ValueError("JSON byte budget exceeded")
            chunks.append(encoded)
        payload = b"".join(chunks)
        if json.loads(payload) != value:
            raise ValueError("input must contain JSON data only")
        return payload
    except (TypeError, UnicodeError, RecursionError) as exc:
        raise ValueError("input must contain bounded UTF-8 JSON data") from exc


def _request_bytes(value: object) -> bytes:
    if type(value) is not dict:
        raise ValueError("request must be a JSON object")
    return _json_bytes(value, MAX_REQUEST_BYTES)


def _patch_bytes(value: object) -> bytes:
    if not isinstance(value, str) or not value or "\0" in value:
        raise ValueError("patch must be nonempty UTF-8 text without NUL")
    try:
        payload = value.encode("utf-8")
    except UnicodeError as exc:
        raise ValueError("patch must be UTF-8 text") from exc
    if len(payload) > MAX_PATCH_BYTES:
        raise ValueError("patch byte budget exceeded")
    return payload


def _read_file(repo: Path, relative: str, maximum: int, *, read_only: bool = False) -> bytes:
    path = repo_path(repo, relative, field="task artifact")
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode) or (read_only and mode & 0o222):
        raise ValueError("task artifact must be a regular admitted file")
    require_one_link(path)
    if path.stat().st_size > maximum:
        raise ValueError("task artifact byte budget exceeded")
    payload = path.read_bytes()
    if len(payload) > maximum:
        raise ValueError("task artifact byte budget exceeded")
    return payload


def _oracle_root(repo: Path, value: str | None) -> str:
    relative = "." if value is None else value
    path = repo_path(repo, relative, field="oracle root")
    if not path.is_dir() or path.relative_to(repo).as_posix() != relative:
        raise ValueError("oracle root must be a canonical repository-relative directory")
    return relative


def _oracle(repo: Path, locator: object, root: str) -> tuple[str, bytes]:
    if not isinstance(locator, str) or len(locator.encode("utf-8")) > 512:
        raise ValueError("oracle locator is invalid")
    parts = locator.split("/")
    if (len(parts) != 3 or parts[0] != "experiments" or parts[2] != "oracle.py"
            or parts[1] in {"", ".", ".."} or any(c in locator for c in ("\\", ":", "\0"))):
        raise ValueError("oracle must be an existing operator-owned experiment oracle")
    relative = (Path(root) / locator).as_posix()
    return locator, _read_file(repo, relative, MAX_ORACLE_BYTES, read_only=True)


def _record(payload: bytes) -> dict[str, object]:
    return {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}


def _task_id(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("taskId is invalid")
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise ValueError("taskId is invalid") from exc
    if str(parsed) != value or parsed.version != 4 or parsed.variant != uuid.RFC_4122:
        raise ValueError("taskId must be a canonical UUID4")
    return value


def stage_task(
    *,
    repo_root: Path,
    snapshot_ref: dict[str, object],
    request: dict[str, object],
    production_patch: str,
    instrumentation_patch: str,
    oracle: str,
    oracle_root: str | None = None,
) -> dict[str, object]:
    """Publish fresh task data; oracle_root is chosen only by deployment."""
    repo = repo_root.resolve()
    resolve_snapshot_value(repo, snapshot_ref)
    payloads = {
        "request": _request_bytes(request),
        "productionPatch": _patch_bytes(production_patch),
        "instrumentationPatch": _patch_bytes(instrumentation_patch),
    }
    if sum(map(len, payloads.values())) > MAX_INPUT_BYTES:
        raise ValueError("combined input byte budget exceeded")
    selected_root = _oracle_root(repo, oracle_root)
    oracle_locator, oracle_payload = _oracle(repo, oracle, selected_root)
    task_id = _task_id(str(uuid.uuid4()))
    manifest = _json_bytes({
        "schemaVersion": 1,
        "taskId": task_id,
        "snapshotRef": snapshot_ref,
        "inputs": {name: _record(payload) for name, payload in payloads.items()},
        "oracle": {"root": selected_root, "path": oracle_locator, **_record(oracle_payload)},
    }, _MAX_MANIFEST_BYTES)
    namespace = repo_path(repo, TASK_NAMESPACE, field="task namespace")
    namespace.mkdir(mode=0o700, exist_ok=True)
    task = repo_path(repo, f"{TASK_NAMESPACE}/{task_id}", field="task root")
    task.mkdir(mode=0o700, exist_ok=False)
    # A manifest is published last. Failed partial stages are not valid handles;
    # neither failure nor a UUID collision removes or rewrites existing data.
    for name, payload in [*payloads.items(), ("manifest", manifest)]:
        filename = "task.json" if name == "manifest" else _FILES[name]
        descriptor = os.open(
            task / filename,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
            0o400,
        )
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
    return {
        "schemaVersion": 1,
        "taskId": task_id,
        "manifestSha256": hashlib.sha256(manifest).hexdigest(),
    }


def resolve_task(
    *,
    repo_root: Path,
    snapshot_ref: dict[str, object],
    task_ref: dict[str, object],
    oracle_root: str | None = None,
) -> dict[str, object]:
    """Validate staged bytes and return data kwargs for shared_task_route.run_task.

    The caller still owns timeout admission and invoking the existing runner.
    This function never creates a receipt, patches a tree or executes an oracle.
    """
    repo = repo_root.resolve()
    snapshot, _entries = resolve_snapshot_value(repo, snapshot_ref)
    if (not isinstance(task_ref, dict) or set(task_ref) != {"schemaVersion", "taskId", "manifestSha256"}
            or type(task_ref["schemaVersion"]) is not int or task_ref["schemaVersion"] != 1):
        raise ValueError("taskRef shape is invalid")
    task_id = _task_id(task_ref["taskId"])
    if not isinstance(task_ref["manifestSha256"], str):
        raise ValueError("manifestSha256 must be a digest string")
    digest_value("sha256:" + task_ref["manifestSha256"])
    relative = f"{TASK_NAMESPACE}/{task_id}"
    task = repo_path(repo, relative, field="task root")
    if not task.is_dir():
        raise ValueError("task root is unavailable")
    if os.path.lexists(task / "receipt.json"):
        raise FileExistsError("task receipt already exists")
    if {p.name for p in task.iterdir()} != {"task.json", *_FILES.values()}:
        raise ValueError("task file set is invalid")
    manifest_bytes = _read_file(repo, f"{relative}/task.json", _MAX_MANIFEST_BYTES, read_only=True)
    if hashlib.sha256(manifest_bytes).hexdigest() != task_ref["manifestSha256"]:
        raise ValueError("task manifest identity mismatch")
    manifest = json.loads(manifest_bytes, object_pairs_hook=unique_object)
    if (not isinstance(manifest, dict)
            or set(manifest) != {"schemaVersion", "taskId", "snapshotRef", "inputs", "oracle"}
            or type(manifest["schemaVersion"]) is not int or manifest["schemaVersion"] != 1
            or manifest["taskId"] != task_id or manifest["snapshotRef"] != snapshot_ref
            or not isinstance(manifest["inputs"], dict) or set(manifest["inputs"]) != set(_FILES)):
        raise ValueError("task binding is invalid")
    for name, filename in _FILES.items():
        maximum = MAX_REQUEST_BYTES if name == "request" else MAX_PATCH_BYTES
        payload = _read_file(repo, f"{relative}/{filename}", maximum, read_only=True)
        record = manifest["inputs"][name]
        if (not isinstance(record, dict) or set(record) != {"sha256", "bytes"}
                or type(record["bytes"]) is not int or record != _record(payload)):
            raise ValueError("task input identity mismatch")
        if name == "request":
            if _request_bytes(json.loads(payload, object_pairs_hook=unique_object)) != payload:
                raise ValueError("task request is not canonical")
        else:
            _patch_bytes(payload.decode("utf-8"))
    oracle_record = manifest["oracle"]
    if (not isinstance(oracle_record, dict) or set(oracle_record) != {"root", "path", "sha256", "bytes"}
            or type(oracle_record["bytes"]) is not int):
        raise ValueError("oracle binding is invalid")
    selected_root = _oracle_root(repo, oracle_root)
    if oracle_record["root"] != selected_root:
        raise ValueError("oracle root binding mismatch")
    oracle_locator, oracle_payload = _oracle(repo, oracle_record["path"], selected_root)
    if oracle_record != {"root": selected_root, "path": oracle_locator, **_record(oracle_payload)}:
        raise ValueError("oracle identity mismatch")
    return {
        "repo_root": repo,
        "input_tree": snapshot,
        "request_path": Path(relative) / _FILES["request"],
        "patch_paths": [(role, Path(relative) / _FILES[key]) for role, key in (
            ("production", "productionPatch"), ("instrumentation", "instrumentationPatch"),
        )],
        "oracle_path": Path(selected_root) / oracle_locator,
        "receipt_path": Path(relative) / "receipt.json",
    }
