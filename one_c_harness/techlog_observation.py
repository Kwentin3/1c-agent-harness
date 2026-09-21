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
import hmac
import json
import os
from pathlib import Path
import re
import secrets
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
_SAFE_FILTER = re.compile(r"[A-Za-z0-9_.:-]{1,128}$")
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
        if name in {"Exception", "Descr", "SrcName", "process", "SessionID"}:
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


def _safe_error(lines: list[str]) -> tuple[dict[str, object], dict[str, str], str]:
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
    technical: dict[str, str] = {}
    process = values.get("process")
    if process and _SAFE_EXCEPTION.fullmatch(process):
        technical["process"] = process
    session = values.get("SessionID")
    if session:
        technical["_sessionValue"] = session
    signature_basis = "\x1f".join((str(error.get("exceptionType", "")), str(error.get("sourceComponent", "")), json.dumps(error["description"], sort_keys=True)))
    return error, technical, "sha256:" + hashlib.sha256(signature_basis.encode("utf-8")).hexdigest()[:16]


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


def _read(root: Path, start: datetime, end: datetime, wanted: set[str] | None) -> tuple[list[dict[str, object]], dict[str, object], str | None] | None:
    began = time.monotonic()
    candidates, incomplete = _candidates(root, start, end, began)
    records: list[dict[str, object]] = []
    read_bytes = 0
    files_read = 0
    for hour, path in candidates:
        if time.monotonic() - began > _MAX_SECONDS:
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
    for index, record in enumerate(records):
        record["selectionIndex"] = index
    coverage = {"filesRead": files_read, "bytesRead": read_bytes, "recordLimit": _MAX_RECORDS, "partial": bool(incomplete)}
    if incomplete:
        coverage["reasonCode"] = incomplete
    return records, coverage, incomplete


def _commit(records: list[dict[str, object]], lines: list[str], hour: datetime, start: datetime, end: datetime, wanted: set[str] | None) -> None:
    match = _EVENT.match(lines[0])
    if not match:
        return
    minute, second, micros, event = match.groups()
    if wanted is not None and event not in wanted:
        return
    occurred = hour.replace(minute=int(minute), second=int(second), microsecond=int(micros[:6]))
    if not start <= occurred <= end:
        return
    error, technical, signature = _safe_error(lines)
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:24]
    records.append({
        "recordId": f"techlog:{digest}", "occurredAt": occurred.isoformat(),
        "sourceTimeToken": f"{minute}:{second}.{micros}", "event": event,
        "error": error, "technical": technical, "errorSignature": signature,
    })


def _snapshot_path(project_root: Path, payload: bytes) -> Path:
    return project_root / _CACHE / f"{hashlib.sha256(payload).hexdigest()[:32]}.json"


def _groups(records: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: Counter[tuple[str, str]] = Counter((str(record["event"]), str(record["errorSignature"])) for record in records)
    result: list[dict[str, object]] = []
    for (event, signature), count in sorted(grouped.items()):
        matching = [record for record in records if record["event"] == event and record["errorSignature"] == signature]
        sample = matching[0]
        error = sample.get("error", {})
        if not isinstance(error, dict):
            error = {}
        description = error.get("description", {})
        fragment = description.get("fragment") if isinstance(description, dict) else None
        pieces = [str(error.get("exceptionType", event))]
        if fragment:
            pieces.append(str(fragment))
        result.append({
            "ref": f"group:{event}:{signature.rsplit(':', 1)[-1]}",
            "event": event,
            "errorSignature": signature,
            "count": count,
            "countScope": "retainedFilteredSelection",
            "firstOccurredAt": matching[0]["occurredAt"],
            "lastOccurredAt": matching[-1]["occurredAt"],
            "summary": {"meaning": ": ".join(pieces)},
        })
    return sorted(result, key=lambda group: (
        str(group["event"]), str(group["summary"]["meaning"]), str(group["errorSignature"]),
    ))


def _valid_filters(filters: object) -> bool:
    if filters is None:
        return True
    if not isinstance(filters, dict) or not set(filters) <= {"text", "sourceComponent", "process"}:
        return False
    if "text" in filters:
        text = filters["text"]
        if not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > 120:
            return False
    return all(
        isinstance(value, str) and bool(_SAFE_FILTER.fullmatch(value))
        for key, value in filters.items() if key != "text"
    )


def _matches(record: dict[str, object], filters: dict[str, str]) -> bool:
    error = record.get("error", {})
    technical = record.get("technical", {})
    if not isinstance(error, dict) or not isinstance(technical, dict):
        return False
    description = error.get("description", {})
    fragment = description.get("fragment", "") if isinstance(description, dict) else ""
    searchable = " ".join((
        str(record.get("event", "")), str(error.get("exceptionType", "")),
        str(error.get("sourceComponent", "")), str(technical.get("process", "")), str(fragment),
    )).casefold()
    if "text" in filters and filters["text"].casefold() not in searchable:
        return False
    for key in ("sourceComponent", "process"):
        if key not in filters:
            continue
        actual = error.get(key) if key == "sourceComponent" else technical.get(key)
        if actual != filters[key]:
            return False
    return True


def _project_private_tokens(records: list[dict[str, object]]) -> None:
    """Replace correlatable private digests with selection-scoped opaque tokens."""
    key = secrets.token_bytes(32)
    for record in records:
        raw_record_id = record.get("recordId")
        if isinstance(raw_record_id, str):
            digest = hmac.new(key, b"record\0" + raw_record_id.encode("ascii"), hashlib.sha256).hexdigest()[:24]
            record["recordId"] = "techlog:" + digest
        technical = record.get("technical")
        if isinstance(technical, dict):
            session = technical.pop("_sessionValue", None)
            if isinstance(session, str):
                digest = hmac.new(key, b"session\0" + session.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
                technical["sessionFingerprint"] = "hmac-sha256:" + digest
        error = record.get("error")
        if not isinstance(error, dict):
            continue
        description = error.get("description")
        if isinstance(description, dict):
            fingerprint = description.get("fingerprint")
            if isinstance(fingerprint, str):
                digest = hmac.new(key, b"description\0" + fingerprint.encode("ascii"), hashlib.sha256).hexdigest()[:16]
                description["fingerprint"] = "hmac-sha256:" + digest
        signature_basis = "\x1f".join((
            str(error.get("exceptionType", "")),
            str(error.get("sourceComponent", "")),
            json.dumps(error.get("description", {}), sort_keys=True),
        ))
        digest = hmac.new(key, b"error\0" + signature_basis.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
        record["errorSignature"] = "hmac-sha256:" + digest


def _prune(project_root: Path, now: float) -> None:
    directory = project_root / _CACHE
    try:
        for path in directory.glob("*.json"):
            if path.is_file() and now - path.stat().st_mtime > _SNAPSHOT_TTL_SECONDS:
                path.unlink()
    except OSError:
        pass


def source_info(project_root: Path) -> dict[str, object]:
    """Describe the configured source through one bounded observation pass."""
    del project_root  # The source is deployment-selected; discovery retains nothing.
    source = _source()
    if source is None:
        return _result("unavailable", reasonCode="source_unavailable", message="technological journal source or timezone is unavailable")
    root, zone, zone_name = source
    start = datetime(2000, 1, 1, tzinfo=zone)
    end = datetime(2099, 12, 31, 23, 59, 59, 999999, tzinfo=zone)
    read = _read(root, start, end, None)
    if read is None:
        return _result("partial", reasonCode="source_unreadable", message="technological journal could not be inspected")
    records, coverage, incomplete = read
    interval = None
    if records:
        interval = {
            "start": records[0]["occurredAt"],
            "end": records[-1]["occurredAt"],
            "complete": not bool(incomplete),
        }
    return _result(
        "partial" if incomplete else "ok",
        source=_SOURCE,
        sourceTimeZone=zone_name,
        observedInterval=interval,
        observedEvents=sorted({str(record["event"]) for record in records}),
        supportedFilters=["events", "text", "sourceComponent", "process"],
        coverage=coverage,
    )


def observe(project_root: Path, start: object, end: object, events: object, limit: object, filters: object = None) -> dict[str, object]:
    if not _valid(events, limit) or not _valid_filters(filters):
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
    _project_private_tokens(records)
    selected_filters = dict(filters) if isinstance(filters, dict) else {}
    if selected_filters:
        records = [record for record in records if _matches(record, selected_filters)]
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
    public_filters = {"events": list(events), **selected_filters}
    return _result(status, summary={"source": _SOURCE, "recordCount": len(records), "countScope": "retainedFilteredSelection", "filters": public_filters, "window": snapshot["window"], "coverage": coverage}, groups=public_groups[:limit], groupsTruncated=len(public_groups) > limit, observationRef=f"snapshot:{path.stem}", snapshot={"ref": path.stem, "stable": True, "partial": bool(incomplete), "expiresInSeconds": _SNAPSHOT_TTL_SECONDS})


def _load_snapshot(project_root: Path, snapshot_id: str) -> dict[str, Any] | None:
    if not re.fullmatch(r"[a-f0-9]{32}", snapshot_id):
        return None
    path = project_root / _CACHE / f"{snapshot_id}.json"
    try:
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest()[:32] != snapshot_id:
            raise ValueError
        value = json.loads(raw)
        if not isinstance(value, dict) or value.get("schemaVersion") != 2 or not isinstance(value.get("records"), list) or not isinstance(value.get("groups"), list) or time.time() > value.get("expiresAt", 0):
            raise ValueError
        return value
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def _evidence_missing() -> dict[str, object]:
    return _result("blocked", reasonCode="evidence_not_found", message="technological-journal evidence is unavailable")


def _public_record(snapshot_id: str, record: dict[str, object]) -> dict[str, object]:
    digest = str(record.get("recordId", "")).removeprefix("techlog:")
    index = record.get("selectionIndex")
    return {**record, "recordRef": f"snapshot:{snapshot_id}:record:{index}:{digest}"}


def expand_groups(project_root: Path, reference: object, offset: object, limit: object) -> dict[str, object]:
    if not isinstance(reference, str) or type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 20:
        return _result("blocked", reasonCode="invalid_request", message="technological-journal expansion request is invalid")
    parts = reference.split(":")
    if len(parts) != 2 or parts[0] != "snapshot":
        return _evidence_missing()
    value = _load_snapshot(project_root, parts[1])
    if value is None:
        return _evidence_missing()
    groups = [{**group, "ref": f"snapshot:{parts[1]}:{group['ref']}"} for group in value["groups"] if isinstance(group, dict)]
    return _result(
        "ok", level="observation", observationRef=reference,
        groups=groups[offset:offset + limit], offset=offset,
        truncated=offset + limit < len(groups), total=len(groups),
        snapshot={"stable": True, "window": value["window"], "coverage": value["coverage"]},
    )


def expand(project_root: Path, reference: object, offset: object, limit: object) -> dict[str, object]:
    if not isinstance(reference, str) or type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 20:
        return _result("blocked", reasonCode="invalid_request", message="technological-journal expansion request is invalid")
    parts = reference.split(":", 3)
    if len(parts) != 4 or parts[0] != "snapshot" or parts[2] != "group" or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,31}", parts[3].split(":")[0]):
        return _evidence_missing()
    value = _load_snapshot(project_root, parts[1])
    if value is None:
        return _evidence_missing()
    canonical_refs = {
        f"snapshot:{parts[1]}:{group.get('ref')}"
        for group in value["groups"] if isinstance(group, dict)
    }
    if reference not in canonical_refs:
        return _evidence_missing()
    canonical_group = next(
        group for group in value["groups"]
        if isinstance(group, dict) and f"snapshot:{parts[1]}:{group.get('ref')}" == reference
    )
    selected = [
        record for record in value["records"]
        if isinstance(record, dict)
        and record.get("event") == canonical_group.get("event")
        and record.get("errorSignature") == canonical_group.get("errorSignature")
    ]
    records = [_public_record(parts[1], record) for record in selected[offset:offset + limit]]
    return _result("ok", level="group", groupRef=reference, records=records, offset=offset, truncated=offset + limit < len(selected), total=len(selected), snapshot={"stable": True, "window": value["window"], "coverage": value["coverage"]})


def expand_record(project_root: Path, reference: object, before: object, after: object) -> dict[str, object]:
    if not isinstance(reference, str) or type(before) is not int or type(after) is not int or not 0 <= before <= 5 or not 0 <= after <= 5:
        return _result("blocked", reasonCode="invalid_request", message="technological-journal record expansion request is invalid")
    parts = reference.split(":")
    if len(parts) != 5 or parts[0] != "snapshot" or parts[2] != "record" or not parts[3].isdigit() or not re.fullmatch(r"[a-f0-9]{24}", parts[4]):
        return _evidence_missing()
    value = _load_snapshot(project_root, parts[1])
    if value is None:
        return _evidence_missing()
    records = [record for record in value["records"] if isinstance(record, dict)]
    wanted_index = int(parts[3])
    index = next((position for position, record in enumerate(records) if record.get("selectionIndex") == wanted_index and record.get("recordId") == f"techlog:{parts[4]}"), None)
    if index is None:
        return _evidence_missing()
    return _result(
        "ok", level="record", recordRef=reference,
        record=_public_record(parts[1], records[index]),
        before=[_public_record(parts[1], record) for record in records[max(0, index - before):index]],
        after=[_public_record(parts[1], record) for record in records[index + 1:index + 1 + after]],
        scope="retainedFilteredSelection",
        relation="time adjacency only; no causal relationship is implied",
        snapshot={"stable": True, "window": value["window"], "coverage": value["coverage"]},
    )
