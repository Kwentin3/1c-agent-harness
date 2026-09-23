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
import xml.etree.ElementTree as ET

import eventlog_exporter as base

SNAPSHOT_ENV = "ONE_C_HARNESS_EVENTLOG_SNAPSHOT"
JOURNAL_ENV = "ONE_C_HARNESS_EVENTLOG_JOURNAL"
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
          "\tIssue80ServerMarker(Root + \"/export-started\");\r\n"
          "\tUnloadEventLog(Root + \"/output.xml\", Filter, "
          "\"Date,Level,Event,EventPresentation,TransactionStatus\", "
          "Root + \"/1Cv8Log/1Cv8.lgf\", Maximum);\r\n"
          "\tIssue80ServerMarker(Root + \"/export-returned\");\r\n"
          "EndProcedure\r\n")

_active: subprocess.Popen[bytes] | None = None


def _terminate(_signum: int, _frame: object) -> None:
    if _active is not None:
        base._stop_group(_active)
    raise base.ExportFailure("source_timeout")


def _digest_tree(root: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    count = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise base.ExportFailure("configuration_invalid")
        if path.is_file():
            rel = path.relative_to(root).as_posix().encode()
            payload = path.read_bytes()
            digest.update(len(rel).to_bytes(4, "big")); digest.update(rel)
            digest.update(len(payload).to_bytes(8, "big")); digest.update(payload)
            count += 1
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
        if name not in filters:
            start, end = blocks[name]
            prefix, rest = result.split(start, 1)
            _discard, suffix = rest.split(end, 1)
            result = prefix + end + suffix
    return result


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


def run_once(request: object) -> tuple[bytes, dict[str, object]]:
    global _active
    admitted = base._validate_request(request)
    settings = _settings()
    snapshot = Path(os.environ.get(SNAPSHOT_ENV, ""))
    journal = Path(os.environ.get(JOURNAL_ENV, ""))
    if (not snapshot.is_absolute() or snapshot.is_symlink() or not snapshot.is_dir()
            or not journal.is_absolute() or journal.is_symlink() or not journal.is_dir()
            or not base._plain_file(journal / "1Cv8.lgf")
            or snapshot == journal or snapshot in journal.parents or journal in snapshot.parents
            or any(settings.work_root == source or settings.work_root in source.parents
                   or source in settings.work_root.parents for source in (snapshot, journal))):
        raise base.ExportFailure("configuration_invalid")
    source_snapshot = _digest_tree(snapshot)
    source_journal = _digest_tree(journal)
    if source_snapshot[0] == 0 or source_journal[0] < 2:
        raise base.ExportFailure("configuration_invalid")
    settings.work_root.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    deadline = started + 110
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
            if _digest_tree(evidence / "1Cv8Log") != source_journal or _digest_tree(journal) != source_journal:
                raise base.ExportFailure("source_incomplete_receipt")
            shutil.copytree(snapshot, copy, symlinks=False)
            if _digest_tree(copy) != source_snapshot or _digest_tree(snapshot) != source_snapshot:
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
            if _digest_tree(snapshot) != source_snapshot or _digest_tree(journal) != source_journal:
                raise base.ExportFailure("source_incomplete_receipt")
            argv = prefix + ["ENTERPRISE", "/F", str(ib), "/DisableStartupDialogs",
                             "/DisableStartupMessages", "/C", str(evidence),
                             "/Out", str(evidence / "runtime.log"), "/DumpResult", str(evidence / "runtime.result")]
            stage = "enterprise"
            try:
                process = subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL,
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                           start_new_session=True)
            except OSError:
                raise base.ExportFailure("source_unavailable") from None
            _active = process
            observed: set[str] = set()
            export_start: float | None = None
            export_end: float | None = None
            output = evidence / "output.xml"
            try:
                while process.poll() is None and time.monotonic() < deadline:
                    for marker in ("client-entered", "server-entered", "export-started", "export-returned", "complete"):
                        if marker not in observed and (evidence / marker).is_file():
                            observed.add(marker)
                            if marker == "export-started": export_start = time.monotonic()
                            if marker == "export-returned": export_end = time.monotonic()
                    if "complete" in observed: break
                    if output.is_file() and output.stat().st_size > admitted["maximumBytes"]:
                        raise base.ExportFailure("source_byte_limit")
                    time.sleep(.02)
            finally:
                timed_out = process.poll() is None and "complete" not in observed
                if process.poll() is None:
                    base._stop_group(process)
                _active = None
            if timed_out:
                raise base.ExportFailure("source_timeout")
            if not set(("client-entered", "server-entered", "export-started", "export-returned", "complete")) <= observed:
                raise base.ExportFailure("source_incomplete_receipt")
            if not output.is_file():
                raise base.ExportFailure("source_incomplete_receipt")
            if output.stat().st_size > admitted["maximumBytes"]:
                raise base.ExportFailure("source_byte_limit")
            stage = "xml"
            xml = output.read_bytes()
            try:
                document = ET.fromstring(xml)
            except ET.ParseError:
                raise base.ExportFailure("source_incomplete_receipt") from None
            if document.tag.rsplit("}", 1)[-1] != "EventLog":
                raise base.ExportFailure("source_incomplete_receipt")
            if _digest_tree(snapshot) != source_snapshot or _digest_tree(journal) != source_journal:
                raise base.ExportFailure("source_incomplete_receipt")
            metrics: dict[str, object] = {"status": "ok", "selectedInfoBase": "configured_stable_journal",
                                          "exporterInvocations": 1,
                                          "lifecycleMilliseconds": round((time.monotonic() - started) * 1000),
                                          "exportMilliseconds": round(1000 * (export_end - export_start)) if export_end and export_start else None,
                                          "xmlBytes": len(xml), "recordCount": len(document)}
            if settings.metrics:
                settings.metrics.write_text(json.dumps(metrics, sort_keys=True), encoding="utf-8")
            return xml, metrics
        except base.ExportFailure as error:
            if settings.metrics:
                status = {"status": "failed", "reasonCode": str(error), "stage": stage,
                          "markers": {name: (evidence / name).is_file() for name in
                                      ("client-entered", "server-entered", "export-started",
                                       "export-returned", "complete")},
                          "runtimeLog": base._file_diagnostic(evidence / "runtime.log"),
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
