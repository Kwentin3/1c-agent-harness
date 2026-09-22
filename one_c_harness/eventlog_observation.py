"""Bounded, retained registration-log selections from a deployment-owned exporter."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
import tempfile
import time
from typing import Any
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_ENV_COMMAND = "ONE_C_HARNESS_EVENTLOG_COMMAND"
_ENV_ZONE = "ONE_C_HARNESS_EVENTLOG_TIME_ZONE"
_CACHE = Path(".local/runs/eventlog-selections")
_TTL_SECONDS = 3600
_MAX_INTERVAL_SECONDS = 24 * 60 * 60
_MAXIMUM_COUNT = 100
_MAX_PAGE = 20
_MAX_XML_BYTES = 1024 * 1024
_TIMEOUT_SECONDS = 120
_FIELDS = (
    "Date", "Level", "Event", "EventPresentation", "User", "UserPresentation",
    "Metadata", "MetadataPresentation", "TransactionStatus",
)
_FILTERS = {"event": "Event", "level": "Level", "user": "User", "metadata": "Metadata"}
_FIELD_LIMITS = {
    "Date": 32, "Level": 32, "Event": 128, "EventPresentation": 160,
    "User": 80, "UserPresentation": 160, "Metadata": 128,
    "MetadataPresentation": 160, "TransactionStatus": 32,
}


def _result(status: str, **values: object) -> dict[str, object]:
    return {"status": status, **values}


def _blocked(reason: str, message: str) -> dict[str, object]:
    return _result("blocked", reasonCode=reason, message=message)


def _source() -> tuple[Path, str] | None:
    command_value = os.environ.get(_ENV_COMMAND)
    zone_value = os.environ.get(_ENV_ZONE)
    if not command_value or not zone_value:
        return None
    command = Path(command_value)
    try:
        mode = command.stat().st_mode
        ZoneInfo(zone_value)
    except (OSError, ZoneInfoNotFoundError):
        return None
    if not command.is_absolute() or command.is_symlink() or not stat.S_ISREG(mode) or not os.access(command, os.X_OK):
        return None
    return command, zone_value


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or len(value) > 32 or value.endswith("Z"):
        raise ValueError(f"{field} is invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} is invalid") from exc
    if parsed.tzinfo is not None:
        raise ValueError(f"{field} is invalid")
    return parsed


def _validated(
    start: object, end: object, filters: object, maximum_count: object, limit: object,
) -> tuple[str, str, dict[str, str], int, int, datetime, datetime]:
    start_value = _timestamp(start, "start")
    end_value = _timestamp(end, "end")
    if end_value < start_value or (end_value - start_value).total_seconds() > _MAX_INTERVAL_SECONDS:
        raise ValueError("interval is invalid")
    if not isinstance(filters, dict) or set(filters) - set(_FILTERS):
        raise ValueError("filters are invalid")
    clean: dict[str, str] = {}
    for key, value in filters.items():
        if not isinstance(value, str) or not value.strip() or len(value) > 128 or any(ord(ch) < 32 for ch in value):
            raise ValueError("filters are invalid")
        clean[key] = value
    if type(maximum_count) is not int or not 1 <= maximum_count <= _MAXIMUM_COUNT:
        raise ValueError("maximumCount is invalid")
    if type(limit) is not int or not 1 <= limit <= _MAX_PAGE:
        raise ValueError("limit is invalid")
    return str(start), str(end), clean, maximum_count, limit, start_value, end_value


def _export(command: Path, request: dict[str, object], project_root: Path) -> tuple[bytes | None, dict[str, object] | None]:
    cache = project_root / _CACHE
    if cache.is_symlink():
        return None, _blocked("source_invalid", "registration log cache is invalid")
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile(dir=cache) as output:
        try:
            completed = subprocess.run(
                [str(command)], input=json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"),
                stdout=output, stderr=subprocess.DEVNULL, timeout=_TIMEOUT_SECONDS, check=False,
            )
        except subprocess.TimeoutExpired:
            return None, _result("unavailable", reasonCode="source_timeout", message="registration log source timed out")
        except OSError:
            return None, _result("unavailable", reasonCode="source_unavailable", message="registration log source is unavailable")
        if completed.returncode != 0:
            return None, _result("unavailable", reasonCode="source_failed", message="registration log source failed")
        size = output.tell()
        if size > _MAX_XML_BYTES:
            return None, _blocked("source_byte_limit", "registration log XML exceeded the byte limit")
        output.seek(0)
        return output.read(), None


def _text(element: ET.Element, name: str) -> str | None:
    for child in element:
        if child.tag.rsplit("}", 1)[-1] == name:
            value = "".join(child.itertext()).strip()
            if len(value) > _FIELD_LIMITS[name]:
                raise ValueError("registration log field exceeds limit")
            return value or None
    return None


def _parse(payload: bytes, start: datetime, end: datetime, filters: dict[str, str]) -> tuple[int, list[dict[str, object]]]:
    upper = payload.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("unsafe XML declaration")
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise ValueError("registration log XML is invalid") from exc
    if root.tag.rsplit("}", 1)[-1] != "EventLog":
        raise ValueError("registration log XML root is invalid")
    records: list[dict[str, object]] = []
    source_count = 0
    for item in root:
        if item.tag.rsplit("}", 1)[-1] != "Event":
            continue
        source_count += 1
        values = {name: _text(item, name) for name in _FIELDS}
        date_text = values["Date"]
        if not isinstance(date_text, str) or not isinstance(values["Event"], str) or not isinstance(values["Level"], str):
            raise ValueError("registration log record required field is missing")
        try:
            occurred = datetime.fromisoformat(date_text)
        except ValueError as exc:
            raise ValueError("registration log record date is invalid") from exc
        if occurred.tzinfo is not None or occurred < start or occurred > end:
            continue
        if any(values[source_name] != expected for key, expected in filters.items() for source_name in [_FILTERS[key]]):
            continue
        records.append({
            "occurredAt": date_text,
            "level": values["Level"],
            "event": values["Event"],
            "eventPresentation": values["EventPresentation"],
            "user": {"name": values["User"], "presentation": values["UserPresentation"]},
            "metadata": {"name": values["Metadata"], "presentation": values["MetadataPresentation"]},
            "transactionStatus": values["TransactionStatus"],
        })
    return source_count, records


def _digest(value: dict[str, object]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _write_selection(project_root: Path, value: dict[str, object]) -> Path:
    root = project_root / _CACHE
    if root.is_symlink():
        raise ValueError("registration log cache is invalid")
    root.mkdir(parents=True, exist_ok=True)
    value["integrity"] = _digest(value)
    path = root / f"{value['id']}.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    os.replace(temporary, path)
    return path


def _read_selection(project_root: Path, reference: object) -> dict[str, Any] | None:
    if not isinstance(reference, str) or not reference.startswith("eventlog:") or len(reference) > 128:
        return None
    selection_id = reference.split(":", 2)[1]
    if not selection_id or any(ch not in "0123456789abcdef" for ch in selection_id):
        return None
    path = project_root / _CACHE / f"{selection_id}.json"
    if path.is_symlink():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or value.get("id") != selection_id or value.get("expiresAt", 0) < time.time():
        return None
    integrity = value.pop("integrity", None)
    if not isinstance(integrity, str) or not hmac.compare_digest(integrity, _digest(value)):
        return None
    value["integrity"] = integrity
    if reference != f"eventlog:{selection_id}" and not reference.startswith(f"eventlog:{selection_id}:record:"):
        return None
    return value


def _facets(records: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    sources = {
        "events": [record.get("event") for record in records],
        "levels": [record.get("level") for record in records],
        "users": [record.get("user", {}).get("name") for record in records],
        "metadata": [record.get("metadata", {}).get("name") for record in records],
    }
    result: dict[str, list[dict[str, object]]] = {}
    for name, values in sources.items():
        counter = Counter(value for value in values if isinstance(value, str))
        result[name] = [{"value": value, "count": count} for value, count in sorted(counter.items())[:20]]
    return result


def select(
    project_root: Path, start: object, end: object, filters: object,
    maximumCount: object, limit: object,
) -> dict[str, object]:
    try:
        start_text, end_text, clean_filters, maximum_count, page_limit, start_value, end_value = _validated(
            start, end, filters, maximumCount, limit,
        )
    except ValueError as exc:
        return _blocked("invalid_request", str(exc))
    source = _source()
    if source is None:
        return _result("unavailable", reasonCode="source_unavailable", message="registration log source is unavailable")
    command, zone_name = source
    request = {
        "schemaVersion": 1, "operation": "unloadEventLog", "start": start_text, "end": end_text,
        "filters": clean_filters, "columns": list(_FIELDS), "maximumCount": maximum_count,
        "maximumBytes": _MAX_XML_BYTES,
    }
    payload, failure = _export(command, request, project_root)
    if failure is not None:
        return failure
    assert payload is not None
    try:
        source_count, matched_records = _parse(payload, start_value, end_value, clean_filters)
    except ValueError:
        return _blocked("source_invalid", "registration log source returned invalid XML")
    matched_count = len(matched_records)
    retained = matched_records[:maximum_count]
    selection_id = secrets.token_hex(12)
    key = secrets.token_bytes(32)
    for index, record_value in enumerate(retained):
        token = hmac.new(key, f"{index}\0{_digest(record_value)}".encode(), hashlib.sha256).hexdigest()[:16]
        record_value["recordRef"] = f"eventlog:{selection_id}:record:{index}:{token}"
        record_value["selectionIndex"] = index
    reason = None
    if source_count > maximum_count:
        reason = "maximum_count_exceeded"
    elif source_count == maximum_count:
        reason = "maximum_count_boundary"
    created = time.time()
    selection = {
        "schemaVersion": 1, "id": selection_id, "createdAt": created, "expiresAt": created + _TTL_SECONDS,
        "window": {"start": start_text, "end": end_text, "sourceTimeZone": zone_name},
        "filters": clean_filters, "maximumCount": maximum_count, "sourceRecordCount": source_count,
        "matchedRecordCount": matched_count,
        "coverage": {"complete": reason is None, "partial": reason is not None, **({"reasonCode": reason} if reason else {})},
        "records": retained,
    }
    try:
        _write_selection(project_root, selection)
    except (OSError, ValueError):
        return _blocked("source_invalid", "registration log selection storage is unavailable")
    selection_ref = f"eventlog:{selection_id}"
    status = "partial" if reason else "ok"
    first_page = retained[:page_limit]
    return _result(
        status,
        selectionRef=selection_ref,
        records=first_page,
        recordsTruncated=len(retained) > page_limit,
        summary={
            "source": "1c_registration_log", "window": selection["window"], "filters": clean_filters,
            "recordCount": len(retained), "sourceRecordCount": source_count, "matchedRecordCount": matched_count,
            "countScope": "retainedFilteredSelection", "facets": _facets(retained),
            "coverage": selection["coverage"],
        },
        snapshot={"stable": True, "expiresInSeconds": _TTL_SECONDS},
    )


def page(project_root: Path, selection_ref: object, offset: object, limit: object) -> dict[str, object]:
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= _MAX_PAGE:
        return _blocked("invalid_request", "page arguments are invalid")
    selection = _read_selection(project_root, selection_ref)
    if selection is None or selection_ref != f"eventlog:{selection['id']}":
        return _blocked("evidence_not_found", "registration log selection is unavailable")
    records = selection["records"]
    page_records = records[offset:offset + limit]
    return _result(
        "partial" if selection["coverage"]["partial"] else "ok",
        selectionRef=selection_ref, offset=offset, total=len(records), truncated=offset + len(page_records) < len(records),
        records=page_records, coverage=selection["coverage"], snapshot={"stable": True},
    )


def record(project_root: Path, record_ref: object) -> dict[str, object]:
    selection = _read_selection(project_root, record_ref)
    if selection is None or not isinstance(record_ref, str):
        return _blocked("evidence_not_found", "registration log record is unavailable")
    for value in selection["records"]:
        if value.get("recordRef") == record_ref:
            return _result(
                "partial" if selection["coverage"]["partial"] else "ok",
                record=value, coverage=selection["coverage"], snapshot={"stable": True},
            )
    return _blocked("evidence_not_found", "registration log record is unavailable")
