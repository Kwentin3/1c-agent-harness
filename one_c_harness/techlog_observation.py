"""Bounded, read-only observations of platform-authored 1C technological logs.

Supported source grammar is the verified 1C Linux 8.5.1.1150 format:
``yymmddhh.log`` supplies the source-local date/hour and each event starts with
``mm:ss.ffffff-pid,EVENT,``.  The executor configures both the log root and its
IANA source timezone; neither is model input.  A successful observation retains
only its safe, bounded selection for later paging.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_SOURCE = "1c_techlog"
_ENV_ROOT = "ONE_C_HARNESS_TECHLOG_ROOT"
_ENV_ZONE = "ONE_C_HARNESS_TECHLOG_TIME_ZONE"
_CACHE = Path(".local/runs/techlog-observations")
_MAX_RECORDS = 200
_MAX_FILES = 24
_MAX_DISCOVERED_PATHS = 96
_MAX_READ_BYTES = 256 * 1024
_MAX_RECORD_BYTES = 8 * 1024
_MAX_DESCRIPTION_CHARS = 480
_MAX_SECONDS = 2.0
_SNAPSHOT_TTL_SECONDS = 3600
_EVENT = re.compile(r"^(\d\d):(\d\d)\.(\d{6,})-\d+,([A-Za-z_][A-Za-z0-9_]*),")
_FILE = re.compile(r"^(\d{6})(\d{2})\.log$")
_CALENDAR = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?$")
_ALLOWED_EVENTS = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,31}$")
_SAFE_EXCEPTION = re.compile(r"[A-Za-z0-9_.:-]{1,128}$")
_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)\b(password|passwd|pwd|token|secret|authorization|api[_-]?key|"
    r"connectionstring|user|username|login|email|phone|customer|client|employee|"
    r"person|fullname|account|inn|taxid|document|order|contract|counterparty|amount|"
    r"value|пользователь|клиент|контрагент|инн|документ|сумма|значение)\s*=\s*"
    r"(?:\"(?:[^\"]|\"\")*\"|'(?:[^']|'')*'|[^,;\s]+)"
)
_ENDPOINT = re.compile(r"(?i)\b(?:https?|tcp)://[^\s,;]+")
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_IP_ADDRESS = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_UUID = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
_PATH = re.compile(
    r"(?<!\w)(?:(?:[A-Za-z]:)?[\\/]|[A-Za-z0-9_.-]+[\\/])"
    r"(?:[^\s,;:'\"]+[\\/])*[^\s,;:'\"]*"
)
_LONG_HEX = re.compile(r"\b[0-9a-fA-F]{24,}\b")


def _result(status: str, **values: object) -> dict[str, object]:
    return {"status": status, **values}


def _source() -> tuple[Path, ZoneInfo, str] | None:
    value = os.environ.get(_ENV_ROOT, "")
    zone_name = os.environ.get(_ENV_ZONE, "")
    root = Path(value) if value else None
    if root is None or not root.is_absolute() or root.is_symlink() or not root.is_dir():
        return None
    try:
        return root, ZoneInfo(zone_name), zone_name
    except ZoneInfoNotFoundError:
        return None


def _calendar(value: object, zone: ZoneInfo) -> datetime | None:
    if not isinstance(value, str) or not _CALENDAR.fullmatch(value):
        return None
    try:
        return datetime.fromisoformat(value).replace(tzinfo=zone)
    except ValueError:
        return None


def _valid(events: object, limit: object) -> bool:
    return (
        isinstance(events, list) and 1 <= len(events) <= 8
        and all(isinstance(event, str) and bool(_ALLOWED_EVENTS.fullmatch(event)) for event in events)
        and type(limit) is int and 1 <= limit <= 20
    )


def _properties(lines: list[str]) -> dict[str, str]:
    """Parse the documented text TechLog name/value grammar for selected fields."""
    parts = "\n".join(lines).split(",", 3)
    if len(parts) != 4:
        return {}
    text = parts[3]
    values: dict[str, str] = {}
    index = 0
    while index < len(text):
        while index < len(text) and text[index] in " ,\r\n\t":
            index += 1
        equals = text.find("=", index)
        if equals < 0:
            break
        name = text[index:equals].strip()
        index = equals + 1
        if index < len(text) and text[index] in "'\"":
            quote = text[index]
            index += 1
            collected: list[str] = []
            while index < len(text):
                if text[index] == quote:
                    if index + 1 < len(text) and text[index + 1] == quote:
                        collected.append(quote)
                        index += 2
                        continue
                    index += 1
                    break
                collected.append(text[index])
                index += 1
            value = "".join(collected)
        else:
            end = index
            while end < len(text) and text[end] not in ",\r\n":
                end += 1
            value = text[index:end]
            index = end
        if name in {"Exception", "Descr", "SrcName"}:
            values.setdefault(name, value.strip())
        while index < len(text) and text[index] not in ",\r\n":
            index += 1
    return values


def _description_projection(description: str) -> dict[str, object]:
    """Project one authorized TechLog Descr; this is not an arbitrary-text sanitizer."""
    fragment = description
    redacted = False
    for pattern, replacement in (
        (_SENSITIVE_ASSIGNMENT, lambda match: f"{match.group(1)}=<redacted:value>"),
        (_ENDPOINT, "<redacted:endpoint>"),
        (_EMAIL, "<redacted:email>"),
        (_IP_ADDRESS, "<redacted:address>"),
        (_UUID, "<redacted:id>"),
        (_PATH, "<redacted:path>"),
        (_LONG_HEX, "<redacted:token>"),
    ):
        fragment, count = pattern.subn(replacement, fragment)
        redacted = redacted or bool(count)
    fragment = re.sub(r"\s+", " ", fragment).strip()
    if fragment and re.fullmatch(r"[\w.-]{1,128}", fragment):
        fragment = ""
        redacted = True
    truncated = len(fragment) > _MAX_DESCRIPTION_CHARS
    if truncated:
        fragment = fragment[:_MAX_DESCRIPTION_CHARS - 3].rstrip() + "..."
    result: dict[str, object] = {
        "status": "projected" if fragment else "redacted",
        "fingerprint": "sha256:" + hashlib.sha256(description.encode("utf-8")).hexdigest()[:16],
        "redacted": redacted,
        "truncated": truncated,
    }
    if fragment:
        result["fragment"] = fragment
    return result


def _safe_error(lines: list[str]) -> tuple[dict[str, object], str]:
    """Expose selected TechLog fields without returning the arbitrary record body."""
    values = _properties(lines)
    exception = values.get("Exception")
    description = values.get("Descr")
    error: dict[str, object] = {"description": {"status": "redacted"}}
    if exception and _SAFE_EXCEPTION.fullmatch(exception):
        error["exceptionType"] = exception
    elif exception:
        error["exceptionType"] = "<redacted>"
    if description:
        error["description"] = _description_projection(description)
    src_name = values.get("SrcName")
    if src_name and _SAFE_EXCEPTION.fullmatch(src_name):
        error["sourceComponent"] = src_name
    signature_basis = "\x1f".join((str(error.get("exceptionType", "")), str(error.get("sourceComponent", "")), json.dumps(error["description"], sort_keys=True)))
    return error, "sha256:" + hashlib.sha256(signature_basis.encode("utf-8")).hexdigest()[:16]


def _candidates(root: Path, start: datetime, end: datetime, began: float) -> tuple[list[tuple[datetime, Path]], str | None]:
    """Bounded directory walk; only hour files that can overlap the interval."""
    wanted: list[tuple[datetime, Path]] = []
    stack = [root]
    seen = 0
    while stack:
        if time.monotonic() - began > _MAX_SECONDS:
            return wanted, "time_budget"
        directory = stack.pop()
        try:
            entries = sorted(directory.iterdir(), key=lambda path: path.name)
        except OSError:
            return wanted, "source_unreadable"
        for path in entries:
            seen += 1
            if seen > _MAX_DISCOVERED_PATHS:
                return wanted, "file_search_budget"
            if path.is_symlink():
                continue
            if path.is_dir():
                stack.append(path)
                continue
            match = _FILE.fullmatch(path.name)
            if not match:
                continue
            try:
                hour = datetime.strptime("20" + match.group(1) + match.group(2), "%Y%m%d%H").replace(tzinfo=start.tzinfo)
            except ValueError:
                continue
            if hour <= end and hour + timedelta(hours=1) >= start:
                wanted.append((hour, path))
    wanted.sort(key=lambda item: (item[0], str(item[1])))
    if len(wanted) > _MAX_FILES:
        return wanted[:_MAX_FILES], "file_budget"
    return wanted, None


def _read(root: Path, start: datetime, end: datetime, wanted: set[str]) -> tuple[list[dict[str, object]], dict[str, object], str | None] | None:
    began = time.monotonic()
    candidates, incomplete = _candidates(root, start, end, began)
    records: list[dict[str, object]] = []
    read_bytes = 0
    files_read = 0
    for hour, path in candidates:
        if incomplete or time.monotonic() - began > _MAX_SECONDS:
            incomplete = incomplete or "time_budget"
            break
        current: list[str] = []
        current_bytes = 0
        try:
            with path.open("rb") as handle:
                while True:
                    if read_bytes >= _MAX_READ_BYTES:
                        incomplete = "read_budget"; break
                    line = handle.readline(min(4096, _MAX_READ_BYTES - read_bytes + 1))
                    if not line:
                        break
                    read_bytes += len(line)
                    if len(line) > 4096 or current_bytes + len(line) > _MAX_RECORD_BYTES:
                        current = []; current_bytes = 0
                        incomplete = incomplete or "record_budget"
                        continue
                    text = line.decode("utf-8-sig" if read_bytes == len(line) else "utf-8", errors="strict").rstrip("\r\n")
                    match = _EVENT.match(text)
                    if match:
                        if current:
                            _commit(records, current, hour, start, end, wanted)
                        current = [text]; current_bytes = len(line)
                    elif current:
                        current.append(text); current_bytes += len(line)
                if current:
                    _commit(records, current, hour, start, end, wanted)
            files_read += 1
        except (OSError, UnicodeDecodeError):
            return None
        if len(records) >= _MAX_RECORDS:
            incomplete = incomplete or "record_budget"
            records = records[:_MAX_RECORDS]
            break
    records.sort(key=lambda record: (record["occurredAt"], record["recordId"]))
    coverage = {"filesRead": files_read, "bytesRead": read_bytes, "recordLimit": _MAX_RECORDS, "partial": bool(incomplete)}
    if incomplete:
        coverage["reasonCode"] = incomplete
    return records, coverage, incomplete


def _commit(records: list[dict[str, object]], lines: list[str], hour: datetime, start: datetime, end: datetime, wanted: set[str]) -> None:
    match = _EVENT.match(lines[0])
    if not match:
        return
    minute, second, micros, event = match.groups()
    if event not in wanted:
        return
    occurred = hour.replace(minute=int(minute), second=int(second), microsecond=int(micros[:6]))
    if not start <= occurred <= end:
        return
    error, signature = _safe_error(lines)
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:24]
    records.append({
        "recordId": f"techlog:{digest}", "occurredAt": occurred.isoformat(),
        "sourceTimeToken": f"{minute}:{second}.{micros}", "event": event,
        "error": error, "errorSignature": signature,
    })


def _snapshot_path(project_root: Path, payload: bytes) -> Path:
    return project_root / _CACHE / f"{hashlib.sha256(payload).hexdigest()[:32]}.json"


def _groups(records: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: Counter[tuple[str, str]] = Counter((str(record["event"]), str(record["errorSignature"])) for record in records)
    return [{"ref": f"group:{event}:{signature.rsplit(':', 1)[-1]}", "event": event, "errorSignature": signature, "count": count} for (event, signature), count in sorted(grouped.items())]


def _prune(project_root: Path, now: float) -> None:
    directory = project_root / _CACHE
    try:
        for path in directory.glob("*.json"):
            if path.is_file() and now - path.stat().st_mtime > _SNAPSHOT_TTL_SECONDS:
                path.unlink()
    except OSError:
        pass


def observe(project_root: Path, start: object, end: object, events: object, limit: object) -> dict[str, object]:
    if not _valid(events, limit):
        return _result("blocked", reasonCode="invalid_request", message="technological-journal request is invalid")
    source = _source()
    if source is None:
        return _result("unavailable", reasonCode="source_unavailable", message="technological journal source or timezone is unavailable")
    root, zone, zone_name = source
    parsed_start, parsed_end = _calendar(start, zone), _calendar(end, zone)
    if parsed_start is None or parsed_end is None or parsed_start > parsed_end:
        return _result("blocked", reasonCode="invalid_request", message="calendar interval is invalid for the configured source timezone")
    read = _read(root, parsed_start, parsed_end, set(events))
    if read is None:
        return _result("partial", reasonCode="source_unreadable", message="technological journal could not be read")
    records, coverage, incomplete = read
    groups = _groups(records)
    now = time.time()
    snapshot = {"schemaVersion": 2, "expiresAt": now + _SNAPSHOT_TTL_SECONDS, "records": records, "groups": groups, "window": {"start": parsed_start.isoformat(), "end": parsed_end.isoformat(), "sourceTimeZone": zone_name}, "coverage": coverage}
    raw = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    path = _snapshot_path(project_root, raw)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _prune(project_root, now)
        if not path.exists():
            temporary = path.with_suffix(".tmp")
            temporary.write_bytes(raw)
            os.replace(temporary, path)
    except OSError:
        return _result("partial", reasonCode="snapshot_unavailable", message="technological-journal selection could not be retained")
    public_groups = [{**group, "ref": f"snapshot:{path.stem}:{group['ref']}"} for group in groups]
    status = "partial" if incomplete else "ok"
    return _result(status, summary={"source": _SOURCE, "recordCount": len(records), "window": snapshot["window"], "coverage": coverage}, groups=public_groups[:limit], groupsTruncated=len(public_groups) > limit, snapshot={"ref": path.stem, "stable": True, "partial": bool(incomplete), "expiresInSeconds": _SNAPSHOT_TTL_SECONDS})


def expand(project_root: Path, reference: object, offset: object, limit: object) -> dict[str, object]:
    if not isinstance(reference, str) or not reference.startswith("snapshot:") or type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 20:
        return _result("blocked", reasonCode="invalid_request", message="technological-journal expansion request is invalid")
    parts = reference.split(":", 3)
    if len(parts) != 4 or not re.fullmatch(r"[a-f0-9]{32}", parts[1]) or parts[2] != "group" or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,31}", parts[3].split(":")[0]):
        return _result("blocked", reasonCode="evidence_not_found", message="technological-journal evidence is unavailable")
    path = project_root / _CACHE / f"{parts[1]}.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.get("schemaVersion") != 2 or not isinstance(value.get("records"), list) or time.time() > value.get("expiresAt", 0):
            raise ValueError
    except (OSError, ValueError, json.JSONDecodeError):
        return _result("blocked", reasonCode="evidence_not_found", message="technological-journal evidence is unavailable")
    event, fingerprint = parts[3].split(":", 1)
    selected = [record for record in value["records"] if isinstance(record, dict) and record.get("event") == event and str(record.get("errorSignature", "")).endswith(fingerprint)]
    return _result("ok", level="group", groupRef=reference, records=selected[offset:offset + limit], offset=offset, truncated=offset + limit < len(selected), total=len(selected), snapshot={"stable": True, "window": value["window"], "coverage": value["coverage"]})
