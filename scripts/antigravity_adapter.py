#!/usr/bin/env python3
"""Strict representation adapter for one Antigravity answer work unit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import stat
import sys
from typing import Any


class AdapterError(RuntimeError):
    pass


def reject_symlink_path(path: Path, label: str) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            return
        if stat.S_ISLNK(mode):
            raise AdapterError(f"{label} contains a symlink: {current}")


def strict_json_loads(data: str, label: str) -> Any:
    def object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise AdapterError(f"duplicate JSON key in {label}: {key}")
            result[key] = value
        return result

    def reject_non_finite(value: str) -> Any:
        raise AdapterError(f"non-finite JSON number in {label}: {value}")

    return json.loads(
        data,
        object_pairs_hook=object_without_duplicates,
        parse_constant=reject_non_finite,
    )


def read_object(path: Path, label: str) -> dict[str, Any]:
    reject_symlink_path(path, label)
    if not path.is_file():
        raise AdapterError(f"{label} must be a regular non-symlink file")
    try:
        value = strict_json_loads(path.read_text(encoding="utf-8-sig"), label)
    except (OSError, UnicodeError, json.JSONDecodeError, AdapterError) as exc:
        raise AdapterError(f"invalid {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise AdapterError(f"{label} must be a JSON object")
    return value


def extract_unit(task: dict[str, Any]) -> dict[str, Any]:
    if task.get("status") != "completed":
        raise AdapterError("task status must be completed")
    result = task.get("result")
    if not isinstance(result, dict):
        raise AdapterError("task result must be an object")
    result_keys = {"summary", "findings", "risks", "recommendations", "sources"}
    if set(result) != result_keys:
        raise AdapterError("task result must contain exactly the native five-field envelope")
    for name in ("findings", "risks", "recommendations", "sources"):
        if result[name] != []:
            raise AdapterError(f"task result {name} must be empty for a typed unit")
    summary = result.get("summary")
    if not isinstance(summary, str):
        raise AdapterError("task result summary must be a string")
    try:
        unit = strict_json_loads(summary, "summary")
    except (json.JSONDecodeError, AdapterError) as exc:
        raise AdapterError(f"invalid summary JSON: {exc}") from exc
    if not isinstance(unit, dict):
        raise AdapterError("summary JSON must be an object")
    return unit


def write_new(path: Path, value: dict[str, Any]) -> None:
    reject_symlink_path(path, "output")
    if path.exists() or path.is_symlink():
        raise AdapterError(f"refusing existing output: {path}")
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise AdapterError("output parent must be an existing non-symlink directory")
    try:
        data = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    except (TypeError, ValueError) as exc:
        raise AdapterError(f"output is not strict JSON: {exc}") from exc
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(data)
    except FileExistsError as exc:
        raise AdapterError(f"refusing existing output: {path}") from exc


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    command = commands.add_parser("extract-unit")
    command.add_argument("--task-record", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        task = read_object(args.task_record, "task record")
        write_new(args.output, extract_unit(task))
    except AdapterError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
