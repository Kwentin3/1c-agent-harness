"""Read-only provider for retained native 1C execution receipts.

This is deliberately one concrete provider, not a provider framework.  It reads
only the harness-owned, retained `native-cycle` result receipts below the active
executor workspace; it never launches 1C, opens a socket, or writes source data.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from . import runtime_diagnostics


_SOURCE = "native_run_history"
_HISTORY_ROOT = Path(".local/runs/native-cycle")
_MAX_SCAN = 64
_ALLOWED_STATUSES = {
    "runtime_contract_completed",
    "runtime_exited_before_completion",
    "runtime_timeout",
}


def _blocked(reason_code: str, message: str) -> dict[str, object]:
    return {"status": "blocked", "reasonCode": reason_code, "message": message}


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _valid_window(start: object, end: object, limit: object) -> bool:
    return (
        isinstance(start, datetime)
        and isinstance(end, datetime)
        and start.tzinfo is not None
        and end.tzinfo is not None
        and start <= end
        and type(limit) is int
        and 1 <= limit <= 20
    )


def _candidate_paths(project_root: Path) -> list[Path]:
    root = project_root / _HISTORY_ROOT
    if not root.is_dir() or root.is_symlink():
        return []
    candidates = [path for path in root.glob("*/run/result.json") if path.is_file() and not path.is_symlink()]
    candidates.sort(key=lambda path: (-path.stat().st_mtime_ns, path.as_posix()))
    return candidates[:_MAX_SCAN]


def _records(project_root: Path, start: datetime, end: datetime) -> list[dict[str, Any]] | dict[str, object]:
    records: list[dict[str, Any]] = []
    for path in _candidate_paths(project_root):
        try:
            raw = path.read_bytes()
            value = json.loads(raw.decode("utf-8-sig"))
            occurred = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, OverflowError):
            return _blocked("provider_record_invalid", "retained runtime receipt is invalid")
        if not isinstance(value, dict) or value.get("status") not in _ALLOWED_STATUSES:
            return _blocked("provider_record_invalid", "retained runtime receipt is invalid")
        duration = value.get("totalDurationSeconds")
        if type(duration) not in {int, float} or duration < 0:
            return _blocked("provider_record_invalid", "retained runtime receipt is invalid")
        if not start <= occurred <= end:
            continue
        digest = hashlib.sha256(raw).hexdigest()[:24]
        records.append({
            "source": _SOURCE,
            "recordId": f"native-run:{digest}",
            "occurredAt": _timestamp(occurred),
            "kind": "native_run",
            "attributes": {"status": value["status"], "durationSeconds": duration},
            "raw": {"status": value["status"], "totalDurationSeconds": duration},
        })
    records.sort(key=lambda record: (record["occurredAt"], record["recordId"]))
    return records


def investigate(project_root: Path, start: datetime, end: datetime, limit: int) -> dict[str, object]:
    """Return bounded deterministic findings from real retained native receipts."""
    if not _valid_window(start, end, limit):
        return _blocked("invalid_request", "runtime investigation request is invalid")
    records = _records(project_root, start, end)
    if isinstance(records, dict):
        return records
    normalized = [{key: record[key] for key in ("source", "recordId", "occurredAt", "kind", "attributes")} for record in records]
    result = runtime_diagnostics.investigate(normalized, start, end)
    if result.get("status") != "ok":
        return result
    findings = result.get("findings")
    if isinstance(findings, list):
        result["findings"] = findings[:limit]
    return result


def expand(project_root: Path, reference: object, limit: object) -> dict[str, object]:
    """Resolve exactly one provider-owned finding or evidence reference."""
    if not isinstance(reference, str) or type(limit) is not int or not 1 <= limit <= 20:
        return _blocked("invalid_request", "runtime evidence request is invalid")
    paths = _candidate_paths(project_root)
    if not paths:
        return _blocked("evidence_not_found", "runtime evidence is unavailable")
    start = datetime.fromtimestamp(min(path.stat().st_mtime for path in paths), tz=timezone.utc)
    end = datetime.fromtimestamp(max(path.stat().st_mtime for path in paths), tz=timezone.utc)
    records = _records(project_root, start, end)
    if isinstance(records, dict):
        return records
    normalized = [{key: record[key] for key in ("source", "recordId", "occurredAt", "kind", "attributes")} for record in records]
    summary = runtime_diagnostics.investigate(normalized, start, end)
    if summary.get("status") != "ok":
        return summary
    groups = {group["ref"]: group for group in summary["evidenceGroups"]}
    if reference in groups:
        wanted = set(groups[reference]["recordRefs"])
        selected = [record for record in records if f"{record['source']}:{record['recordId']}" in wanted]
        return {"status": "ok", "level": "evidence", "evidenceGroup": groups[reference], "records": selected[:limit]}
    prefix = f"finding:native-run-history:"
    if reference.startswith(prefix):
        status = reference[len(prefix):]
        selected = [record for record in records if record["attributes"]["status"] == status]
        if selected:
            return {
                "status": "ok",
                "level": "finding",
                "findingRef": reference,
                "records": selected[:limit],
                "truncated": len(selected) > limit,
            }
    return _blocked("evidence_not_found", "runtime evidence is unavailable")
