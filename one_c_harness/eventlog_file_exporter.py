#!/usr/bin/env python3
"""Bounded read-only export of a deployment-selected 1C file event log via ibcmd."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any
import xml.etree.ElementTree as ET

import eventlog_exporter as base

IBCMD_ENV = "ONE_C_HARNESS_EVENTLOG_IBCMD"
JOURNAL_ENV = "ONE_C_HARNESS_EVENTLOG_JOURNAL"
WORK_ROOT_ENV = "ONE_C_HARNESS_EVENTLOG_WORK_ROOT"
METRICS_ENV = "ONE_C_HARNESS_EVENTLOG_METRICS"
_MAX_JOURNAL_BYTES = 64 * 1024 * 1024
_MAX_JOURNAL_FILES = 128
_TIMEOUT_SECONDS = 30
_NAMESPACE = "http://v8.1c.ru/eventLog"
_REQUIRED_SOURCE_FIELDS = ("Date", "Level", "Event")
_XML_FIELDS = (
    "Date", "Level", "Event", "EventPresentation", "User", "UserPresentation",
    "Metadata", "MetadataPresentation", "TransactionStatus", "Comment",
)
_FILTER_FIELDS = {
    "event": "Event", "level": "Level", "user": "User",
    "metadata": "MetadataPresentation",
}

_active: subprocess.Popen[bytes] | None = None


class Settings:
    def __init__(self, ibcmd: Path, journal: Path, work_root: Path, metrics: Path | None):
        self.ibcmd = ibcmd
        self.journal = journal
        self.work_root = work_root
        self.metrics = metrics


def _terminate(_signum: int, _frame: object) -> None:
    if _active is not None:
        base._stop_group(_active)
    raise base.ExportFailure("source_timeout")


def _digest_tree(
    root: Path, *, max_files: int = _MAX_JOURNAL_FILES,
    max_bytes: int = _MAX_JOURNAL_BYTES, deadline: float | None = None,
) -> tuple[int, str]:
    digest = hashlib.sha256()
    count = 0
    total = 0
    for path in sorted(root.rglob("*")):
        if deadline is not None and time.monotonic() >= deadline:
            raise base.ExportFailure("source_timeout")
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise base.ExportFailure("configuration_invalid")
        if not path.is_file():
            continue
        count += 1
        size = path.stat().st_size
        total += size
        if count > max_files or total > max_bytes:
            raise base.ExportFailure("source_byte_limit")
        relative = path.relative_to(root).as_posix().encode()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(size.to_bytes(8, "big"))
        with path.open("rb") as stream:
            remaining = size
            while remaining:
                if deadline is not None and time.monotonic() >= deadline:
                    raise base.ExportFailure("source_timeout")
                chunk = stream.read(min(65536, remaining))
                if not chunk:
                    raise base.ExportFailure("source_incomplete_receipt")
                digest.update(chunk)
                remaining -= len(chunk)
            if stream.read(1):
                raise base.ExportFailure("source_incomplete_receipt")
    return count, digest.hexdigest()


def _plain_file(path: Path, executable: bool = False) -> bool:
    try:
        mode = path.stat().st_mode
    except OSError:
        return False
    return (
        path.is_absolute() and not _has_symlink_component(path) and stat.S_ISREG(mode)
        and (not executable or os.access(path, os.X_OK))
    )


def _has_symlink_component(path: Path) -> bool:
    if not path.is_absolute():
        return True
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            return True
    return False


def _overlaps(left: Path, right: Path) -> bool:
    left = left.resolve()
    right = right.resolve()
    return left == right or left in right.parents or right in left.parents


def _aliases_tree(path: Path, root: Path) -> bool:
    if not path.exists():
        return False
    try:
        identity = (path.stat().st_dev, path.stat().st_ino)
        return any(
            child.is_file() and (child.stat().st_dev, child.stat().st_ino) == identity
            for child in root.rglob("*")
        )
    except OSError:
        return True


def _same_inode(left: Path, right: Path) -> bool:
    try:
        left_stat = left.stat()
        right_stat = right.stat()
    except OSError:
        return False
    return (left_stat.st_dev, left_stat.st_ino) == (right_stat.st_dev, right_stat.st_ino)


def _settings() -> Settings:
    values = {name: os.environ.get(name) for name in (IBCMD_ENV, JOURNAL_ENV, WORK_ROOT_ENV)}
    if any(not value for value in values.values()):
        raise base.ExportFailure("configuration_invalid")
    ibcmd = Path(values[IBCMD_ENV] or "")
    journal = Path(values[JOURNAL_ENV] or "")
    work_root = Path(values[WORK_ROOT_ENV] or "")
    metrics_raw = os.environ.get(METRICS_ENV)
    metrics = Path(metrics_raw) if metrics_raw else None
    if (
        not _plain_file(ibcmd, executable=True)
        or not journal.is_absolute() or _has_symlink_component(journal) or not journal.is_dir()
        or not _plain_file(journal / "1Cv8.lgf")
        or not work_root.is_absolute() or _has_symlink_component(work_root)
        or (work_root.exists() and not work_root.is_dir())
        or _overlaps(work_root, journal) or _overlaps(work_root, ibcmd)
        or (
            metrics is not None
            and (
                not metrics.is_absolute() or _has_symlink_component(metrics)
                or (metrics.exists() and not stat.S_ISREG(metrics.stat().st_mode))
                or _overlaps(metrics, journal) or _overlaps(metrics, ibcmd)
                or _same_inode(metrics, ibcmd) or _aliases_tree(metrics, journal)
            )
        )
    ):
        raise base.ExportFailure("configuration_invalid")
    return Settings(ibcmd, journal, work_root, metrics)


def _source_value(record: dict[str, Any], field: str) -> object:
    if field == "UserPresentation":
        return record.get("UserName")
    if field in {"Metadata", "MetadataPresentation"}:
        return record.get("MetadataPresentation")
    return record.get(field)


def _json_sequence_to_xml(
    payload: bytes, maximum_bytes: int, filters: dict[str, str] | None = None,
) -> bytes:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        raise base.ExportFailure("source_incomplete_receipt") from None
    decoder = json.JSONDecoder()
    position = 0
    records: list[dict[str, Any]] = []
    try:
        while position < len(text):
            while position < len(text) and text[position].isspace():
                position += 1
            if position == len(text):
                break
            value, position = decoder.raw_decode(text, position)
            if not isinstance(value, dict):
                raise ValueError
            if any(not isinstance(value.get(name), str) or not value[name] for name in _REQUIRED_SOURCE_FIELDS):
                raise ValueError
            for name in _XML_FIELDS:
                source = _source_value(value, name)
                if source is not None and not isinstance(source, str):
                    raise ValueError
            if all(
                value.get(_FILTER_FIELDS[key]) == expected
                for key, expected in (filters or {}).items()
            ):
                records.append(value)
    except (json.JSONDecodeError, ValueError, TypeError):
        raise base.ExportFailure("source_incomplete_receipt") from None

    ET.register_namespace("v8e", _NAMESPACE)
    root = ET.Element(f"{{{_NAMESPACE}}}EventLog")
    for source in records:
        item = ET.SubElement(root, f"{{{_NAMESPACE}}}Event")
        for field in _XML_FIELDS:
            value = _source_value(source, field)
            if isinstance(value, str) and value:
                child = ET.SubElement(item, f"{{{_NAMESPACE}}}{field}")
                child.text = value
    result = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    if len(result) > maximum_bytes:
        raise base.ExportFailure("source_byte_limit")
    return result


def _write_metrics(path: Path | None, value: dict[str, object]) -> None:
    if path is not None:
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def _run_ibcmd(settings: Settings, request: dict[str, Any], root: Path, deadline: float) -> tuple[bytes, int]:
    global _active
    output = root / "eventlog.json"
    argv = [
        str(settings.ibcmd), "eventlog", "export", "--format=json", "--skip-root",
        f"--from={request['start']}", f"--to={request['end']}", f"--out={output}",
        str(settings.journal),
    ]
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
        _active = process
        while process.poll() is None:
            if time.monotonic() >= deadline:
                base._stop_group(process)
                raise base.ExportFailure("source_timeout")
            if output.is_file() and output.stat().st_size > request["maximumBytes"]:
                base._stop_group(process)
                raise base.ExportFailure("source_byte_limit")
            time.sleep(.02)
    except OSError:
        raise base.ExportFailure("source_unavailable") from None
    finally:
        _active = None
    if process.returncode != 0:
        raise base.ExportFailure("source_process_failed")
    try:
        if output.stat().st_size > request["maximumBytes"]:
            raise base.ExportFailure("source_byte_limit")
        payload = output.read_bytes()
    except base.ExportFailure:
        raise
    except OSError:
        raise base.ExportFailure("source_incomplete_receipt") from None
    if len(payload) > request["maximumBytes"]:
        raise base.ExportFailure("source_byte_limit")
    return payload, round((time.monotonic() - started) * 1000)


def run_once(request: object) -> tuple[bytes, dict[str, object]]:
    admitted = base._validate_request(request)
    settings = _settings()
    started = time.monotonic()
    deadline = started + _TIMEOUT_SECONDS
    source_journal = _digest_tree(settings.journal, deadline=deadline)
    if source_journal[0] < 2:
        raise base.ExportFailure("configuration_invalid")
    settings.work_root.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="eventlog-ibcmd-", dir=settings.work_root) as raw:
            payload, export_milliseconds = _run_ibcmd(settings, admitted, Path(raw), deadline)
            xml = _json_sequence_to_xml(
                payload, admitted["maximumBytes"], admitted["filters"],
            )
            document = ET.fromstring(xml)
            if _digest_tree(settings.journal, deadline=deadline) != source_journal:
                raise base.ExportFailure("source_incomplete_receipt")
            metrics: dict[str, object] = {
                "status": "ok", "backend": "ibcmd", "selectedInfoBase": "configured_stable_journal",
                "exporterInvocations": 1, "nativeExportSessions": 1,
                "lifecycleMilliseconds": round((time.monotonic() - started) * 1000),
                "exportMilliseconds": export_milliseconds, "xmlBytes": len(xml),
                "recordCount": len(document),
            }
            _write_metrics(settings.metrics, metrics)
            return xml, metrics
    except base.ExportFailure as error:
        _write_metrics(settings.metrics, {"status": "failed", "backend": "ibcmd", "reasonCode": str(error)})
        raise


def main() -> int:
    signal.signal(signal.SIGTERM, _terminate)
    try:
        request = json.loads(sys.stdin.buffer.read(65537))
        xml, _metrics = run_once(request)
        sys.stdout.buffer.write(xml)
        return 0
    except (json.JSONDecodeError, UnicodeDecodeError):
        failure = "invalid_request"
    except base.ExportFailure as error:
        failure = str(error)
    except (OSError, ValueError, ET.ParseError):
        failure = "source_failed"
    sys.stderr.write(json.dumps({"reasonCode": failure}, sort_keys=True) + "\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
