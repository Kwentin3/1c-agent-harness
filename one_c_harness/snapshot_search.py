#!/usr/bin/env python3
"""Search an admitted 1C SnapshotRef without executor-provided tools."""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Iterator

try:  # Installed companion package.
    from .target_admission import TargetBlocked, resolve_snapshot_ref, resolve_snapshot_value
except ImportError:  # ``python scripts/snapshot_search.py`` compatibility entrypoint.
    from target_admission import TargetBlocked, resolve_snapshot_ref, resolve_snapshot_value

SCHEMA_VERSION = 1
DEFAULT_LIMIT = 20
DEFAULT_MAX_BYTES = 32 * 1024
MIN_MAX_BYTES = 256
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


def _stdout_bytes(payload: dict[str, object]) -> bytes:
    return (_dump(payload) + "\n").encode("utf-8")


def _write(payload: dict[str, object], maximum: int) -> None:
    encoded = _stdout_bytes(payload)
    if len(encoded) > maximum:
        raise SearchBlocked("output_limit", "response exceeds byte limit")
    sys.stdout.buffer.write(encoded)


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


def _admitted_snapshot(repo_root: Path, ref_path: Path) -> tuple[Path, dict[str, str]]:
    try:
        return resolve_snapshot_ref(repo_root, ref_path)
    except TargetBlocked as exc:
        raise SearchBlocked("snapshot_invalid", "SnapshotRef is not admitted") from exc


def _admitted_value(repo_root: Path, snapshot_ref: object) -> tuple[Path, dict[str, str]]:
    try:
        return resolve_snapshot_value(repo_root, snapshot_ref)
    except TargetBlocked as exc:
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
        if PurePosixPath(relative).suffix.casefold() not in {".bsl", ".xml"}:
            continue
        path = snapshot / relative
        try:
            with path.open("rb") as snapshot_file:
                payload = snapshot_file.read()
            if b"\0" in payload:
                raise ValueError("binary snapshot content")
            text = payload.decode("utf-8")
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise SearchBlocked("snapshot_invalid", "Snapshot content is unreadable") from exc
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
    return _search_admitted(_admitted_snapshot(repo_root, snapshot_ref_path), query, mode, path_prefix, limit, max_bytes)


def search_value(repo_root: Path, snapshot_ref: object, query: str, mode: str, path_prefix: str | None, limit: int, max_bytes: int) -> dict[str, object]:
    """Companion-only in-memory SnapshotRef form; it has no raw-directory variant."""
    return _search_admitted(_admitted_value(repo_root, snapshot_ref), query, mode, path_prefix, limit, max_bytes)


def _search_admitted(admitted: tuple[Path, dict[str, str]], query: str, mode: str, path_prefix: str | None, limit: int, max_bytes: int) -> dict[str, object]:
    if mode not in {"literal", "regex"}:
        raise SearchBlocked("invalid_request", "mode is invalid")
    pattern = re.escape(query) if mode == "literal" else query
    try:
        matcher = re.compile(pattern)
    except re.error as exc:
        raise SearchBlocked("invalid_request", "query regex is invalid") from exc
    snapshot, entries = admitted
    results: list[dict[str, object]] = []
    truncated = False
    for hit in _matching_lines(snapshot, entries, matcher, path_prefix):
        if len(results) >= limit:
            truncated = True
            break
        candidate = results + [hit]
        if len(_stdout_bytes(_result(query, mode, path_prefix, candidate, False))) > max_bytes:
            truncated = True
            break
        results.append(hit)
    payload = _result(query, mode, path_prefix, results, truncated)
    if len(_stdout_bytes(payload)) > max_bytes:
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
    output_limit = DEFAULT_MAX_BYTES
    try:
        query = _bounded_text(args.query, name="query", maximum=MAX_QUERY_BYTES)
        limit = _positive(args.limit, name="limit", maximum=100)
        max_bytes = _positive(args.max_bytes, name="maxBytes", maximum=DEFAULT_MAX_BYTES)
        if max_bytes < MIN_MAX_BYTES:
            raise SearchBlocked("invalid_request", "maxBytes is invalid")
        output_limit = max_bytes
        prefix = _path_prefix(args.path_prefix)
        payload = search(args.repo_root.resolve(), args.snapshot_ref, query, args.mode, prefix, limit, max_bytes)
        _write(payload, output_limit)
        return 0
    except SearchBlocked as exc:
        _write(_blocked(exc.reason_code, exc.message), output_limit)
        return 1
    except Exception:
        _write(_blocked("search_failed", "search could not complete"), output_limit)
        return 1


if __name__ == "__main__":
    sys.exit(main())
