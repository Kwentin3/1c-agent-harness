"""Bounded reader for platform-authored 1C technological-journal records.

Only the executor supplies the log root via ONE_C_HARNESS_TECHLOG_ROOT.  A query
creates a small task-local immutable selection so later expansion is unaffected
by log rotation or new events.  It is not a monitoring database or framework.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

_SOURCE = "1c_techlog"
_ENV = "ONE_C_HARNESS_TECHLOG_ROOT"
_CACHE = Path(".local/runs/techlog-observations")
_MAX_RECORDS = 200
_EVENT = re.compile(r"^(\d\d:\d\d\.\d{6,})-\d+,([A-Za-z_][A-Za-z0-9_]*),")
_DAY = re.compile(r"^\d{6}$")
_TIME = re.compile(r"^\d\d:\d\d\.\d{6,}$")
_SAFE_FIELDS = {"process", "OSThread", "Usr", "DBMS", "DataBase", "Context", "Exception", "Descr", "IB", "ID", "Nmb"}


def _result(status: str, **values: object) -> dict[str, object]:
    return {"status": status, **values}


def _source() -> Path | None:
    value = os.environ.get(_ENV, "")
    path = Path(value) if value else None
    if path is None or not path.is_absolute() or path.is_symlink() or not path.is_dir():
        return None
    return path


def _valid(day: object, start: object, end: object, events: object, limit: object) -> bool:
    return (
        isinstance(day, str) and bool(_DAY.fullmatch(day))
        and isinstance(start, str) and bool(_TIME.fullmatch(start))
        and isinstance(end, str) and bool(_TIME.fullmatch(end)) and start <= end
        and isinstance(events, list) and 1 <= len(events) <= 8
        and all(isinstance(event, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,31}", event) for event in events)
        and type(limit) is int and 1 <= limit <= 20
    )


def _safe_body(lines: list[str]) -> list[dict[str, object]]:
    """Safe source representation: names remain, literal values are marked hidden."""
    fields: list[str] = []
    for name in _SAFE_FIELDS:
        if any(re.search(rf"(?:^|,){re.escape(name)}=", line) for line in lines):
            fields.append(name)
    return [{"field": name, "value": "<hidden>"} for name in sorted(fields)] + [{"field": "body", "value": "<hidden>"}]


def _read(root: Path, day: str, start: str, end: str, wanted: set[str]) -> list[dict[str, object]] | None:
    records: list[dict[str, object]] = []
    candidates = sorted(path for path in root.rglob(f"{day}*.log") if path.is_file() and not path.is_symlink())
    try:
        for path in candidates:
            current: list[str] = []
            def commit() -> None:
                if not current:
                    return
                match = _EVENT.match(current[0])
                if not match:
                    return
                source_time, event = match.groups()
                if start <= source_time <= end and event in wanted:
                    digest = hashlib.sha256("\n".join(current).encode("utf-8")).hexdigest()[:24]
                    records.append({"recordId": f"techlog:{digest}", "sourceDate": day, "sourceTimeToken": source_time, "event": event, "safeSource": _safe_body(current)})
            for line in path.read_text(encoding="utf-8-sig", errors="strict").splitlines():
                if _EVENT.match(line):
                    commit(); current = [line]
                elif current:
                    current.append(line)
            commit()
    except (OSError, UnicodeDecodeError):
        return None
    records.sort(key=lambda record: (record["sourceTimeToken"], record["recordId"]))
    return records


def _snapshot_path(project_root: Path, payload: bytes) -> Path:
    return project_root / _CACHE / f"{hashlib.sha256(payload).hexdigest()[:32]}.json"


def observe(project_root: Path, day: object, start: object, end: object, events: object, limit: object) -> dict[str, object]:
    if not _valid(day, start, end, events, limit):
        return _result("blocked", reasonCode="invalid_request", message="technological-journal request is invalid")
    root = _source()
    if root is None:
        return _result("unavailable", reasonCode="source_unavailable", message="technological journal is unavailable")
    records = _read(root, day, start, end, set(events))
    if records is None:
        return _result("partial", reasonCode="source_partial", message="technological journal could not be read completely")
    partial = len(records) > _MAX_RECORDS
    selected = records[:_MAX_RECORDS]
    groups = [{"ref": f"group:{event}", "event": event, "count": count} for event, count in sorted(Counter(record["event"] for record in selected).items())]
    snapshot = {"schemaVersion": 1, "records": selected, "groups": groups, "window": {"date": day, "start": start, "end": end}}
    raw = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    path = _snapshot_path(project_root, raw)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            temporary = path.with_suffix(".tmp")
            temporary.write_bytes(raw)
            os.replace(temporary, path)
    except OSError:
        return _result("partial", reasonCode="snapshot_unavailable", message="technological-journal selection could not be retained")
    public_groups = [{**group, "ref": f"snapshot:{path.stem}:{group['ref']}"} for group in groups]
    return _result("ok", summary={"source": _SOURCE, "recordCount": len(selected), "window": snapshot["window"]}, groups=public_groups[:limit], snapshot={"ref": path.stem, "stable": True, "partial": partial})


def expand(project_root: Path, reference: object, offset: object, limit: object) -> dict[str, object]:
    if not isinstance(reference, str) or not reference.startswith("snapshot:") or type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 20:
        return _result("blocked", reasonCode="invalid_request", message="technological-journal expansion request is invalid")
    parts = reference.split(":", 2)
    if len(parts) != 3 or not re.fullmatch(r"[a-f0-9]{32}", parts[1]) or not parts[2].startswith("group:"):
        return _result("blocked", reasonCode="evidence_not_found", message="technological-journal evidence is unavailable")
    path = project_root / _CACHE / f"{parts[1]}.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.get("schemaVersion") != 1 or not isinstance(value.get("records"), list):
            raise ValueError
    except (OSError, ValueError, json.JSONDecodeError):
        return _result("blocked", reasonCode="evidence_not_found", message="technological-journal evidence is unavailable")
    event = parts[2][len("group:"):]
    selected = [record for record in value["records"] if isinstance(record, dict) and record.get("event") == event]
    return _result("ok", level="group", groupRef=reference, records=selected[offset:offset + limit], offset=offset, truncated=offset + limit < len(selected), total=len(selected))
