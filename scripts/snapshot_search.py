#!/usr/bin/env python3
"""Search an admitted 1C SnapshotRef without executor-provided tools."""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Iterator

from target_admission import (
    TargetBlocked,
    admit_target,
    load_contract,
    manifest_entries,
    paths,
    snapshot_ref,
    unique_object,
)

SCHEMA_VERSION = 1
DEFAULT_LIMIT = 20
DEFAULT_MAX_BYTES = 32 * 1024
MAX_QUERY_BYTES = 512
MAX_FRAGMENT_BYTES = 512


class SearchBlocked(Exception):
    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        self.message = message
        super().__init__(message)


def _blocked(reason_code: str, message: str) -> dict[str, object]:
    return {
        "message": message,
        "reasonCode": reason_code,
        "schemaVersion": SCHEMA_VERSION,
        "status": "blocked",
    }


def _dump(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _bounded_text(value: object, *, name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > maximum:
        raise SearchBlocked("invalid_request", f"{name} is invalid")
    return value


def _positive(value: str, *, name: str, maximum: int) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise SearchBlocked("invalid_request", f"{name} is invalid") from exc
    if parsed < 1 or parsed > maximum:
        raise SearchBlocked("invalid_request", f"{name} is invalid")
    return parsed


def _path_prefix(value: str | None) -> str | None:
    if value is None:
        return None
    if not value or len(value.encode("utf-8")) > MAX_QUERY_BYTES:
        raise SearchBlocked("invalid_request", "pathPrefix is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or any(not part or part == "." for part in path.parts):
        raise SearchBlocked("invalid_request", "pathPrefix is invalid")
    return path.as_posix()


def _read_snapshot_ref(path: Path, contract: dict[str, object]) -> None:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 16 * 1024:
            raise ValueError("invalid snapshot reference")
        actual = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
        if not isinstance(actual, dict) or actual.get("action") not in {"materialized", "reused"}:
            raise ValueError("invalid snapshot reference")
        if actual != snapshot_ref(contract, str(actual["action"])):
            raise ValueError("snapshot reference does not match target")
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise SearchBlocked("snapshot_invalid", "SnapshotRef is not admitted") from exc


def _admitted_snapshot(repo_root: Path, ref_path: Path) -> tuple[Path, dict[str, str]]:
    try:
        contract, _ = load_contract(repo_root)
        _read_snapshot_ref(ref_path, contract)
        _base, target, snapshot, manifest, binding = paths(repo_root, contract)
        admit_target(target, snapshot, manifest, binding, contract)
        return snapshot, manifest_entries(manifest.read_bytes())
    except SearchBlocked:
        raise
    except (OSError, TargetBlocked, ValueError) as exc:
        raise SearchBlocked("snapshot_invalid", "SnapshotRef is not admitted") from exc


def _fragment(line: str) -> str:
    compact = line.strip()
    encoded = compact.encode("utf-8")
    if len(encoded) <= MAX_FRAGMENT_BYTES:
        return compact
    kept: list[str] = []
    used = len("…".encode("utf-8"))
    for character in compact:
        size = len(character.encode("utf-8"))
        if used + size > MAX_FRAGMENT_BYTES:
            break
        kept.append(character)
        used += size
    return "".join(kept) + "…"


def _matching_lines(snapshot: Path, entries: dict[str, str], matcher: re.Pattern[str], prefix: str | None) -> Iterator[dict[str, object]]:
    for relative in sorted(entries):
        if prefix is not None and relative != prefix and not relative.startswith(prefix + "/"):
            continue
        path = snapshot / relative
        try:
            payload = path.read_bytes()
            if b"\0" in payload:
                continue
            text = payload.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if matcher.search(line):
                yield {"fragment": _fragment(line), "line": line_number, "path": relative}


def _result(query: str, mode: str, prefix: str | None, results: list[dict[str, object]], truncated: bool) -> dict[str, object]:
    request: dict[str, object] = {"mode": mode, "value": query}
    if prefix is not None:
        request["pathPrefix"] = prefix
    return {
        "query": request,
        "results": results,
        "schemaVersion": SCHEMA_VERSION,
        "status": "ok",
        "truncated": truncated,
    }


def search(repo_root: Path, snapshot_ref_path: Path, query: str, mode: str, path_prefix: str | None, limit: int, max_bytes: int) -> dict[str, object]:
    if mode not in {"literal", "regex"}:
        raise SearchBlocked("invalid_request", "mode is invalid")
    pattern = re.escape(query) if mode == "literal" else query
    try:
        matcher = re.compile(pattern)
    except re.error as exc:
        raise SearchBlocked("invalid_request", "query regex is invalid") from exc
    snapshot, entries = _admitted_snapshot(repo_root, snapshot_ref_path)
    results: list[dict[str, object]] = []
    truncated = False
    for hit in _matching_lines(snapshot, entries, matcher, path_prefix):
        if len(results) >= limit:
            truncated = True
            break
        candidate = results + [hit]
        if len(_dump(_result(query, mode, path_prefix, candidate, True)).encode("utf-8")) > max_bytes:
            truncated = True
            break
        results.append(hit)
    payload = _result(query, mode, path_prefix, results, truncated)
    if len(_dump(payload).encode("utf-8")) > max_bytes:
        raise SearchBlocked("invalid_request", "maxBytes is too small")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--snapshot-ref", type=Path, required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--mode", default="literal")
    parser.add_argument("--path-prefix")
    parser.add_argument("--limit", default=str(DEFAULT_LIMIT))
    parser.add_argument("--max-bytes", default=str(DEFAULT_MAX_BYTES))
    args = parser.parse_args()
    try:
        query = _bounded_text(args.query, name="query", maximum=MAX_QUERY_BYTES)
        limit = _positive(args.limit, name="limit", maximum=100)
        max_bytes = _positive(args.max_bytes, name="maxBytes", maximum=DEFAULT_MAX_BYTES)
        prefix = _path_prefix(args.path_prefix)
        payload = search(args.repo_root.resolve(), args.snapshot_ref, query, args.mode, prefix, limit, max_bytes)
        print(_dump(payload))
        return 0
    except SearchBlocked as exc:
        print(_dump(_blocked(exc.reason_code, exc.message)))
        return 1
    except Exception:
        print(_dump(_blocked("search_failed", "search could not complete")))
        return 1


if __name__ == "__main__":
    sys.exit(main())
