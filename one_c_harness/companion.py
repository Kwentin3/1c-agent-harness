#!/usr/bin/env python3
"""Installed, workspace-relative JSON front door for the 1C Harness core."""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
from typing import Any

try:  # Installed package.
    from . import ARTIFACT_ID, CAPABILITY_VERSION
    from . import project_target, shared_task_route, snapshot_search
    from .target_admission import TargetBlocked, resolve_snapshot_value
except ImportError:  # Repository-local compatibility for focused tests.
    from __init__ import ARTIFACT_ID, CAPABILITY_VERSION
    import project_target
    import shared_task_route
    import snapshot_search
    from target_admission import TargetBlocked, resolve_snapshot_value

SCHEMA_VERSION = 1
MAX_REQUEST_BYTES = 16 * 1024
MAX_OUTPUT_BYTES = 32 * 1024


class CompanionError(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise CompanionError("duplicate JSON key")
        value[key] = item
    return value


def _blocked(reason_code: str, message: str) -> dict[str, object]:
    return {
        "artifactId": ARTIFACT_ID,
        "capabilityVersion": CAPABILITY_VERSION,
        "message": message,
        "reasonCode": reason_code,
        "schemaVersion": SCHEMA_VERSION,
        "status": "blocked",
    }


def _dump(value: dict[str, object]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len((payload + "\n").encode("utf-8")) > MAX_OUTPUT_BYTES:
        payload = json.dumps(_blocked("output_limit", "response exceeds byte limit"), separators=(",", ":"))
    return payload + "\n"


def _request(raw: bytes) -> tuple[str, dict[str, object]]:
    if not raw or len(raw) > MAX_REQUEST_BYTES:
        raise CompanionError("request is invalid")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CompanionError("request is invalid") from exc
    if not isinstance(value, dict) or set(value) != {"schemaVersion", "operation", "arguments"}:
        raise CompanionError("request keys are invalid")
    if value["schemaVersion"] != SCHEMA_VERSION or not isinstance(value["operation"], str):
        raise CompanionError("request is invalid")
    if not isinstance(value["arguments"], dict):
        raise CompanionError("arguments must be an object")
    return value["operation"], value["arguments"]


def _relative_path(value: object, field: str) -> Path:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > 512:
        raise CompanionError(f"{field} is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or any(part in {"", "."} for part in path.parts):
        raise CompanionError(f"{field} is invalid")
    return Path(path.as_posix())


def _positive(value: object, field: str, maximum: int, default: int) -> int:
    if value is None:
        return default
    if type(value) is not int or value < 1 or value > maximum:
        raise CompanionError(f"{field} is invalid")
    return value


def _open(arguments: dict[str, object], project_root: Path) -> dict[str, object]:
    if arguments:
        raise CompanionError("open does not accept arguments")
    try:
        snapshot_ref = project_target.open_target(project_root)
    except TargetBlocked as exc:
        return _blocked(exc.reason_code, exc.message)
    return {
        "artifactId": ARTIFACT_ID,
        "capabilityVersion": CAPABILITY_VERSION,
        "operation": "open",
        "schemaVersion": SCHEMA_VERSION,
        "snapshotRef": snapshot_ref,
        "status": "ok" if snapshot_ref.get("status") == "ready" else snapshot_ref.get("status"),
    }


def _narrow(arguments: dict[str, object], project_root: Path) -> dict[str, object]:
    allowed = {"snapshotRef", "query", "mode", "pathPrefix", "limit", "maxBytes"}
    if set(arguments) - allowed or "snapshotRef" not in arguments or "query" not in arguments:
        raise CompanionError("narrow arguments are invalid")
    query = arguments["query"]
    if not isinstance(query, str) or not query or len(query.encode("utf-8")) > snapshot_search.MAX_QUERY_BYTES:
        raise CompanionError("query is invalid")
    mode = arguments.get("mode", "literal")
    if mode not in {"literal", "regex"}:
        raise CompanionError("mode is invalid")
    prefix = arguments.get("pathPrefix")
    if prefix is not None and not isinstance(prefix, str):
        raise CompanionError("pathPrefix is invalid")
    prefix = snapshot_search._path_prefix(prefix)
    result = snapshot_search.search_value(
        project_root,
        arguments["snapshotRef"],
        query,
        mode,
        prefix,
        _positive(arguments.get("limit"), "limit", 100, snapshot_search.DEFAULT_LIMIT),
        _positive(arguments.get("maxBytes"), "maxBytes", MAX_OUTPUT_BYTES, snapshot_search.DEFAULT_MAX_BYTES),
    )
    return {"artifactId": ARTIFACT_ID, "capabilityVersion": CAPABILITY_VERSION, **result}


def _verify(arguments: dict[str, object], project_root: Path) -> dict[str, object]:
    required = {
        "snapshotRef", "request", "productionPatch", "instrumentationPatch", "oracle", "receipt", "timeoutSeconds",
    }
    if set(arguments) != required:
        raise CompanionError("verify arguments are invalid")
    snapshot, _entries = resolve_snapshot_value(project_root, arguments["snapshotRef"])
    receipt_path = _relative_path(arguments["receipt"], "receipt")
    receipt = shared_task_route.run_task(
        repo_root=project_root,
        input_tree=snapshot,
        request_path=_relative_path(arguments["request"], "request"),
        patch_paths=[
            ("production", _relative_path(arguments["productionPatch"], "productionPatch")),
            ("instrumentation", _relative_path(arguments["instrumentationPatch"], "instrumentationPatch")),
        ],
        oracle_path=_relative_path(arguments["oracle"], "oracle"),
        receipt_path=receipt_path,
        timeout_seconds=_positive(arguments["timeoutSeconds"], "timeoutSeconds", 480, 300),
    )
    receipt_file = project_root / receipt_path
    if not receipt_file.is_file():
        raise CompanionError("verify receipt is unavailable")
    cleanup = receipt.get("cleanup")
    oracle = receipt.get("result", {}).get("oracle") if isinstance(receipt.get("result"), dict) else None
    return {
        "artifactId": ARTIFACT_ID,
        "capabilityVersion": CAPABILITY_VERSION,
        "cleanup": cleanup,
        "operation": "verify",
        "oracleStatus": oracle.get("status") if isinstance(oracle, dict) else None,
        "receipt": {"path": receipt_path.as_posix(), "sha256": hashlib.sha256(receipt_file.read_bytes()).hexdigest()},
        "schemaVersion": SCHEMA_VERSION,
        "status": "ok",
    }


def execute(raw: bytes, project_root: Path) -> dict[str, object]:
    """Run one closed request against the selected terminal workspace only."""
    try:
        operation, arguments = _request(raw)
        root = project_root.resolve()
        if not root.is_dir() or root.is_symlink():
            raise CompanionError("active project workspace is invalid")
        if operation == "open":
            return _open(arguments, root)
        if operation == "narrow":
            return _narrow(arguments, root)
        if operation == "verify":
            return _verify(arguments, root)
        raise CompanionError("operation is invalid")
    except snapshot_search.SearchBlocked as exc:
        return _blocked(exc.reason_code, exc.message)
    except TargetBlocked as exc:
        return _blocked(exc.reason_code, exc.message)
    except CompanionError as exc:
        return _blocked("invalid_request", str(exc))
    except (OSError, ValueError, json.JSONDecodeError, shared_task_route.SharedRouteError):
        return _blocked("operation_failed", "operation could not complete")
    except Exception:
        return _blocked("operation_failed", "operation could not complete")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--request-stdin", action="store_true")
    source.add_argument("--request-base64")
    args = parser.parse_args(argv)
    if args.request_stdin:
        raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
    else:
        try:
            raw = base64.b64decode(args.request_base64, validate=True)
        except (ValueError, binascii.Error):
            raw = b""
    sys.stdout.write(_dump(execute(raw, Path.cwd())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
