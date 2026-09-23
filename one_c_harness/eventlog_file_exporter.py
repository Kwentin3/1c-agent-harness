#!/usr/bin/env python3
"""Bounded file-journal export using an isolated, disposable training infobase.

Only an administrator-selected, quiescent 1Cv8Log directory is supported. Never
point this at a live-writing journal; matching hashes cannot prove an atomic copy.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any
import xml.etree.ElementTree as ET

import eventlog_exporter as base

SNAPSHOT_ENV = "ONE_C_HARNESS_EVENTLOG_SNAPSHOT"
JOURNAL_ENV = "ONE_C_HARNESS_EVENTLOG_JOURNAL"
_MAX_SNAPSHOT_BYTES = 128 * 1024 * 1024
_MAX_JOURNAL_BYTES = 64 * 1024 * 1024
_MAX_SNAPSHOT_FILES = 10000
_MAX_JOURNAL_FILES = 128
MODULE = Path("Ext/ManagedApplicationModule.bsl")
ANCHOR = "Procedure OnStart()\r\n\t\r\n"
CLIENT = ("Procedure OnStart()\r\n"
          "\tRoot = LaunchParameter;\r\n"
          "\tWriteIssue80Marker(Root + \"/client-entered\");\r\n"
          "\tIssue80Export(Root);\r\n"
          "\tWriteIssue80Marker(Root + \"/complete\");\r\n"
          "\tReturn;\r\n\t\r\n")
SERVER = ("\r\n&AtClient\r\nProcedure WriteIssue80Marker(Path)\r\n"
          "\tWriter = New TextWriter(Path, TextEncoding.UTF8);\r\n"
          "\tWriter.Write(\"true\");\r\n\tWriter.Close();\r\nEndProcedure\r\n"
          "\r\n&AtServer\r\nProcedure Issue80ServerMarker(Path)\r\n"
          "\tWriter = New TextWriter(Path, TextEncoding.UTF8);\r\n"
          "\tWriter.Write(\"true\");\r\n\tWriter.Close();\r\nEndProcedure\r\n"
          "\r\n&AtServer\r\nFunction Issue80Read(Path)\r\n"
          "\tReader = New TextReader(Path, TextEncoding.UTF8);\r\n"
          "\tValue = Reader.Read();\r\n\tReader.Close();\r\n\tReturn Value;\r\nEndFunction\r\n"
          "\r\n&AtServer\r\nProcedure Issue80Export(Root)\r\n"
          "\tIssue80ServerMarker(Root + \"/server-entered\");\r\n"
          "\tFilter = New Structure;\r\n"
          "\tFilter.Insert(\"StartDate\", Date(Issue80Read(Root + \"/start.txt\")));\r\n"
          "\tFilter.Insert(\"EndDate\", Date(Issue80Read(Root + \"/end.txt\")));\r\n"
          "\tEventName = Issue80Read(Root + \"/filter-event.txt\");\r\n"
          "\tIf EventName <> \"\" Then\r\n\t\tFilter.Insert(\"Event\", EventName);\r\n\tEndIf;\r\n"
          "\tUserName = Issue80Read(Root + \"/filter-user.txt\");\r\n"
          "\tIf UserName <> \"\" Then\r\n\t\tFilter.Insert(\"User\", UserName);\r\n\tEndIf;\r\n"
          "\tMetadataName = Issue80Read(Root + \"/filter-metadata.txt\");\r\n"
          "\tIf MetadataName <> \"\" Then\r\n\t\tFilter.Insert(\"Metadata\", MetadataName);\r\n\tEndIf;\r\n"
          "\tLevelName = Issue80Read(Root + \"/filter-level.txt\");\r\n"
          "\tIf LevelName = \"Information\" Then\r\n\t\tFilter.Insert(\"Level\", EventLogLevel.Information);\r\n"
          "\tElsIf LevelName = \"Error\" Then\r\n\t\tFilter.Insert(\"Level\", EventLogLevel.Error);\r\n"
          "\tElsIf LevelName = \"Warning\" Then\r\n\t\tFilter.Insert(\"Level\", EventLogLevel.Warning);\r\n"
          "\tElsIf LevelName = \"Note\" Then\r\n\t\tFilter.Insert(\"Level\", EventLogLevel.Note);\r\n\tEndIf;\r\n"
          "\tMaximum = Number(Issue80Read(Root + \"/maximum-count.txt\"));\r\n"
          "\tColumns = Issue80Read(Root + \"/columns.txt\");\r\n"
          "\tInputFile = Issue80Read(Root + \"/input-file.txt\");\r\n"
          "\tIssue80ServerMarker(Root + \"/export-started\");\r\n"
          "\tUnloadEventLog(Root + \"/output.xml\", Filter, Columns, InputFile, Maximum);\r\n"
          "\tIssue80ServerMarker(Root + \"/export-returned\");\r\n"
          "EndProcedure\r\n")

_active: subprocess.Popen[bytes] | None = None


def _terminate(_signum: int, _frame: object) -> None:
    if _active is not None:
        base._stop_group(_active)
    raise base.ExportFailure("source_timeout")


def _digest_tree(root: Path, *, max_files: int = _MAX_SNAPSHOT_FILES,
                 max_bytes: int = _MAX_SNAPSHOT_BYTES,
                 deadline: float | None = None) -> tuple[int, str]:
    digest = hashlib.sha256()
    count = 0
    total = 0
    for path in sorted(root.rglob("*")):
        if deadline is not None and time.monotonic() >= deadline:
            raise base.ExportFailure("source_timeout")
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise base.ExportFailure("configuration_invalid")
        if path.is_file():
            count += 1
            size = path.stat().st_size
            total += size
            if count > max_files or total > max_bytes:
                raise base.ExportFailure("source_byte_limit")
            rel = path.relative_to(root).as_posix().encode()
            digest.update(len(rel).to_bytes(4, "big")); digest.update(rel)
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


def _owned_remove(root: Path) -> None:
    if root.exists():
        for path in (root, *root.rglob("*")):
            if path.is_dir() and not path.is_symlink():
                path.chmod(path.stat().st_mode | stat.S_IRWXU)
        shutil.rmtree(root)


def _server_for(filters: dict[str, str]) -> str:
    result = SERVER
    blocks = {
        "event": ("\tEventName =", "\tUserName ="),
        "user": ("\tUserName =", "\tMetadataName ="),
        "metadata": ("\tMetadataName =", "\tLevelName ="),
        "level": ("\tLevelName =", "\tMaximum ="),
    }
    # Only include the fixed BSL branch when that optional filter was supplied.
    for name in ("event", "user", "metadata", "level"):
        if name not in filters or name in {"user", "metadata"}:
            start, end = blocks[name]
            prefix, rest = result.split(start, 1)
            _discard, suffix = rest.split(end, 1)
            result = prefix + end + suffix
    return result


_EXPORT_COLUMNS = {
    "comment": (*base.COLUMNS[:4], "TransactionStatus", "Comment"),
    "user": (*base.COLUMNS[:4], "TransactionStatus", "User"),
    "metadata": (*base.COLUMNS[:4], "TransactionStatus", "Metadata"),
    "metadata-presentation": (*base.COLUMNS[:4], "TransactionStatus", "MetadataPresentation"),
}
_IDENTITY_COLUMNS = ("Date", "Level", "Event", "EventPresentation", "TransactionStatus")


def _xml_child(record: ET.Element, field: str) -> ET.Element | None:
    return next((item for item in record if item.tag.rsplit("}", 1)[-1] == field), None)


def _xml_value(record: ET.Element, field: str) -> str | None:
    child = _xml_child(record, field)
    return "".join(child.itertext()) if child is not None else None


def _merge_exports(documents: dict[str, ET.Element], maximum_bytes: int) -> bytes:
    if set(documents) != set(_EXPORT_COLUMNS):
        raise base.ExportFailure("source_incomplete_receipt")
    primary = documents["comment"]
    if any(len(document) != len(primary) for document in documents.values()):
        raise base.ExportFailure("source_incomplete_receipt")
    additions = {"user": "User", "metadata": "Metadata", "metadata-presentation": "MetadataPresentation"}
    for index, record in enumerate(primary):
        identity = tuple(_xml_value(record, field) for field in _IDENTITY_COLUMNS)
        for source, field in additions.items():
            other = documents[source][index]
            if tuple(_xml_value(other, name) for name in _IDENTITY_COLUMNS) != identity:
                raise base.ExportFailure("source_incomplete_receipt")
            value = _xml_child(other, field)
            if value is not None:
                record.append(value)
    payload = ET.tostring(primary, encoding="utf-8", xml_declaration=True)
    if len(payload) > maximum_bytes:
        raise base.ExportFailure("source_byte_limit")
    return payload


def _export_session(
    settings: base.Settings, ib: Path, journal: Path, root: Path,
    request: dict[str, Any], columns: tuple[str, ...], deadline: float,
) -> tuple[ET.Element, int]:
    global _active
    root.mkdir()
    home = root / "home"; home.mkdir()
    temporary = root / "tmp"; temporary.mkdir()
    base._write_request(root, request)
    (root / "columns.txt").write_text(",".join(columns), encoding="utf-8")
    (root / "input-file.txt").write_text(str(journal / "1Cv8.lgf"), encoding="utf-8")
    if deadline <= time.monotonic():
        raise base.ExportFailure("source_timeout")
    try:
        process = subprocess.Popen(
            base._prefix(settings, root / "wrapper.log") + [
                "ENTERPRISE", "/F", str(ib), "/DisableStartupDialogs", "/DisableStartupMessages",
                "/C", str(root), "/Out", str(root / "runtime.log"),
                "/DumpResult", str(root / "runtime.result"),
            ],
            env=base._environment(settings, home, temporary), stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
        )
    except OSError:
        raise base.ExportFailure("source_unavailable") from None
    _active = process
    started = time.monotonic()
    required = ("client-entered", "server-entered", "export-started", "export-returned", "complete")
    output = root / "output.xml"
    try:
        while process.poll() is None and time.monotonic() < deadline:
            if all((root / marker).is_file() for marker in required):
                break
            if output.is_file() and output.stat().st_size > request["maximumBytes"]:
                raise base.ExportFailure("source_byte_limit")
            time.sleep(.02)
    except OSError:
        raise base.ExportFailure("source_unavailable") from None
    finally:
        timed_out = process.poll() is None and not all((root / marker).is_file() for marker in required)
        if process.poll() is None:
            base._stop_group(process)
        _active = None
    if timed_out:
        raise base.ExportFailure("source_timeout")
    if not all((root / marker).is_file() for marker in required) or not output.is_file():
        raise base.ExportFailure("source_incomplete_receipt")
    payload = output.read_bytes()
    if len(payload) > request["maximumBytes"]:
        raise base.ExportFailure("source_byte_limit")
    try:
        document = ET.fromstring(payload)
    except ET.ParseError:
        raise base.ExportFailure("source_incomplete_receipt") from None
    if document.tag.rsplit("}", 1)[-1] != "EventLog":
        raise base.ExportFailure("source_incomplete_receipt")
    return document, round((time.monotonic() - started) * 1000)


def _batch(argv: list[str], env: dict[str, str], receipt: Path, deadline: float) -> None:
    global _active
    if deadline <= time.monotonic():
        raise base.ExportFailure("source_timeout")
    try:
        process = subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   start_new_session=True)
        _active = process
        try:
            process.wait(timeout=max(.001, min(110, deadline - time.monotonic())))
        except subprocess.TimeoutExpired:
            base._stop_group(process)
            raise base.ExportFailure("source_timeout") from None
        if process.returncode != 0 or receipt.read_text(encoding="utf-8-sig").strip() != "0":
            raise base.ExportFailure("source_process_failed")
    except OSError:
        raise base.ExportFailure("source_unavailable") from None
    finally:
        _active = None


def _settings() -> base.Settings:
    keys = ("ONE_C_HARNESS_EVENTLOG_RUNTIME_PROFILE", "ONE_C_HARNESS_EVENTLOG_WORK_ROOT")
    if any(not os.environ.get(key) for key in keys):
        raise base.ExportFailure("configuration_invalid")
    try:
        profile_path = Path(os.environ[keys[0]])
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        platform, xvfb, fontconfig = (Path(profile[key]) for key in ("platform", "xvfb", "fontconfig"))
        libs = profile["libs"]
        work_root = Path(os.environ[keys[1]])
        metrics_raw = os.environ.get("ONE_C_HARNESS_EVENTLOG_METRICS")
        metrics = Path(metrics_raw) if metrics_raw else None
    except (OSError, ValueError, KeyError, TypeError):
        raise base.ExportFailure("configuration_invalid") from None
    if (not base._plain_file(profile_path) or not base._plain_file(platform, True)
            or not base._plain_file(xvfb, True) or not base._plain_file(fontconfig)
            or not isinstance(libs, str) or not libs or not work_root.is_absolute()
            or work_root.is_symlink() or (metrics is not None and
            (not metrics.is_absolute() or metrics.is_symlink()))):
        raise base.ExportFailure("configuration_invalid")
    return base.Settings(platform, xvfb, libs, fontconfig, Path("/"), Path("/"),
                         work_root, None, None, metrics)


def _overlaps(left: Path, right: Path) -> bool:
    left = left.resolve()
    right = right.resolve()
    return left == right or left in right.parents or right in left.parents


def run_once(request: object) -> tuple[bytes, dict[str, object]]:
    global _active
    admitted = base._validate_request(request)
    settings = _settings()
    snapshot = Path(os.environ.get(SNAPSHOT_ENV, ""))
    journal = Path(os.environ.get(JOURNAL_ENV, ""))
    if (not snapshot.is_absolute() or snapshot.is_symlink() or not snapshot.is_dir()
            or not journal.is_absolute() or journal.is_symlink() or not journal.is_dir()
            or not base._plain_file(journal / "1Cv8.lgf")
            or _overlaps(snapshot, journal)
            or any(_overlaps(settings.work_root, source) or
                   (settings.metrics is not None and
                    (settings.metrics.resolve() == source.resolve() or
                     source.resolve() in settings.metrics.resolve().parents))
                   for source in (snapshot, journal))):
        raise base.ExportFailure("configuration_invalid")
    started = time.monotonic()
    deadline = started + 110
    source_snapshot = _digest_tree(snapshot, deadline=deadline)
    source_journal = _digest_tree(journal, max_files=_MAX_JOURNAL_FILES,
                                  max_bytes=_MAX_JOURNAL_BYTES, deadline=deadline)
    if source_snapshot[0] == 0 or source_journal[0] < 2:
        raise base.ExportFailure("configuration_invalid")
    settings.work_root.mkdir(parents=True, exist_ok=True)
    stage = "copy"
    with tempfile.TemporaryDirectory(prefix="journal-", dir=settings.work_root) as raw:
        root = Path(raw)
        evidence = root / "request"; evidence.mkdir()
        home = root / "home"; home.mkdir()
        temporary = root / "tmp"; temporary.mkdir()
        copy = root / "work-copy"
        ib = root / "ib"
        env = base._environment(settings, home, temporary)
        base._write_request(evidence, admitted)
        try:
            shutil.copytree(journal, evidence / "1Cv8Log", symlinks=False)
            if (_digest_tree(evidence / "1Cv8Log", max_files=_MAX_JOURNAL_FILES,
                             max_bytes=_MAX_JOURNAL_BYTES, deadline=deadline) != source_journal
                    or _digest_tree(journal, max_files=_MAX_JOURNAL_FILES,
                                    max_bytes=_MAX_JOURNAL_BYTES, deadline=deadline) != source_journal):
                raise base.ExportFailure("source_incomplete_receipt")
            shutil.copytree(snapshot, copy, symlinks=False)
            if (_digest_tree(copy, deadline=deadline) != source_snapshot
                    or _digest_tree(snapshot, deadline=deadline) != source_snapshot):
                raise base.ExportFailure("source_incomplete_receipt")
            module = copy / MODULE
            module.chmod(module.stat().st_mode | stat.S_IWUSR)
            content = module.read_bytes().decode("utf-8-sig")
            if content.count(ANCHOR) != 1 or content.count("Procedure OnStart()") != 1:
                raise base.ExportFailure("configuration_invalid")
            module.write_bytes(b"\xef\xbb\xbf" + content.replace(ANCHOR, CLIENT, 1).encode()
                               + _server_for(admitted["filters"]).encode())
            prefix = base._prefix(settings, evidence / "wrapper.log")
            stage = "create"
            _batch(prefix + ["CREATEINFOBASE", f"File={ib}", "/DisableStartupDialogs",
                             "/DisableStartupMessages", "/Out", str(evidence / "create.log"),
                             "/DumpResult", str(evidence / "create.result")], env, evidence / "create.result", deadline)
            stage = "load"
            _batch(prefix + ["DESIGNER", "/F", str(ib), "/DisableStartupDialogs",
                             "/DisableStartupMessages", "/LoadConfigFromFiles", str(copy),
                             "/UpdateDBCfg", "/Out", str(evidence / "load.log"),
                             "/DumpResult", str(evidence / "load.result")], env, evidence / "load.result", deadline)
            if (_digest_tree(snapshot, deadline=deadline) != source_snapshot
                    or _digest_tree(journal, max_files=_MAX_JOURNAL_FILES,
                                    max_bytes=_MAX_JOURNAL_BYTES, deadline=deadline) != source_journal):
                raise base.ExportFailure("source_incomplete_receipt")
            stage = "enterprise"
            documents: dict[str, ET.Element] = {}
            export_milliseconds = 0
            copied_journal = evidence / "1Cv8Log"
            for name, columns in _EXPORT_COLUMNS.items():
                document, elapsed = _export_session(
                    settings, ib, copied_journal, evidence / f"export-{name}",
                    admitted, columns, deadline,
                )
                documents[name] = document
                export_milliseconds += elapsed
            stage = "xml"
            xml = _merge_exports(documents, admitted["maximumBytes"])
            document = ET.fromstring(xml)
            if (_digest_tree(snapshot, deadline=deadline) != source_snapshot
                    or _digest_tree(journal, max_files=_MAX_JOURNAL_FILES,
                                    max_bytes=_MAX_JOURNAL_BYTES, deadline=deadline) != source_journal):
                raise base.ExportFailure("source_incomplete_receipt")
            metrics: dict[str, object] = {"status": "ok", "selectedInfoBase": "configured_stable_journal",
                                          "exporterInvocations": 1, "nativeExportSessions": len(documents),
                                          "lifecycleMilliseconds": round((time.monotonic() - started) * 1000),
                                          "exportMilliseconds": export_milliseconds,
                                          "xmlBytes": len(xml), "recordCount": len(document)}
            if settings.metrics:
                settings.metrics.write_text(json.dumps(metrics, sort_keys=True), encoding="utf-8")
            return xml, metrics
        except base.ExportFailure as error:
            if settings.metrics:
                diagnostic_root = evidence / "export-comment"
                status = {"status": "failed", "reasonCode": str(error), "stage": stage,
                          "markers": {name: (diagnostic_root / name).is_file() for name in
                                      ("client-entered", "server-entered", "export-started",
                                       "export-returned", "complete")},
                          "runtimeLog": base._file_diagnostic(diagnostic_root / "runtime.log"),
                          "loadLog": base._file_diagnostic(evidence / "load.log")}
                settings.metrics.write_text(json.dumps(status, sort_keys=True), encoding="utf-8")
            raise
        finally:
            _owned_remove(copy)
            _owned_remove(ib)


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
