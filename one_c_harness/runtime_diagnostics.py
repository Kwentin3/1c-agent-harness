"""Deterministic, read-only aggregation for bounded 1C runtime observations.

Providers collect records from RAC, OS metrics or log infrastructure. This module
never opens a host path, launches a command, stores history or explains causes.
It only validates a bounded provider result, groups known identifiers and preserves
record references for later provider-owned expansion.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


_ALLOWED_KINDS = {"session", "process_sample", "timeout"}


def _blocked(reason_code: str, message: str) -> dict[str, str]:
    return {"status": "blocked", "reasonCode": reason_code, "message": message}


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return result if result.tzinfo is not None else None


def _validate(record: object, start: datetime, end: datetime) -> dict[str, Any] | None:
    if not isinstance(record, dict) or set(record) != {"source", "recordId", "occurredAt", "kind", "attributes"}:
        return None
    if (not isinstance(record["source"], str) or not record["source"]
            or not isinstance(record["recordId"], str) or not record["recordId"]
            or record["kind"] not in _ALLOWED_KINDS or not isinstance(record["attributes"], dict)):
        return None
    occurred_at = _timestamp(record["occurredAt"])
    if occurred_at is None or occurred_at < start or occurred_at > end:
        return None
    return record


def _evidence_group(source: str, records: list[dict[str, Any]]) -> dict[str, object]:
    refs = sorted(f"{source}:{record['recordId']}" for record in records)
    return {"ref": f"evidence:{source}:{refs[0]}:{len(refs)}", "source": source, "recordRefs": refs}


def investigate(records: object, start: datetime, end: datetime) -> dict[str, object]:
    """Return bounded facts and provenance for one provider-bounded incident window."""
    if (not isinstance(records, list) or start.tzinfo is None or end.tzinfo is None or start > end):
        return _blocked("invalid_request", "runtime investigation request is invalid")
    checked = [_validate(record, start, end) for record in records]
    if any(record is None for record in checked):
        return _blocked("provider_record_invalid", "runtime provider returned an invalid record")
    accepted = [record for record in checked if record is not None]
    by_source: dict[str, list[dict[str, Any]]] = {}
    for item in accepted:
        by_source.setdefault(item["source"], []).append(item)
    evidence_groups = [_evidence_group(source, by_source[source]) for source in sorted(by_source)]
    evidence_refs = [group["ref"] for group in evidence_groups]

    sessions = [item for item in accepted if item["kind"] == "session"]
    samples = [item for item in accepted if item["kind"] == "process_sample"]
    timeouts = [item for item in accepted if item["kind"] == "timeout"]
    findings: list[dict[str, object]] = []
    job_values = {item["attributes"].get("job") for item in sessions + timeouts}
    pid_values = {item["attributes"].get("pid") for item in sessions + samples + timeouts}
    cpu_values = [item["attributes"].get("cpuPercent") for item in samples]
    if (len(job_values) == 1 and None not in job_values and len(pid_values) == 1 and None not in pid_values
            and sessions and samples and timeouts and all(type(value) in {int, float} for value in cpu_values)):
        findings.append({
            "ref": "finding:job-runtime-anomaly:1",
            "kind": "job_runtime_anomaly",
            "classification": "derived_deterministically",
            "observed": {
                "job": next(iter(job_values)),
                "pid": next(iter(pid_values)),
                "sessionCount": len(sessions),
                "cpuAvgPercent": round(sum(cpu_values) / len(cpu_values)),
                "timeoutCount": len(timeouts),
            },
            "evidenceRefs": evidence_refs,
        })
    return {
        "status": "ok",
        "summary": {"recordCount": len(accepted), "window": {"start": start.isoformat(), "end": end.isoformat()}},
        "findings": findings,
        "evidenceGroups": evidence_groups,
    }
