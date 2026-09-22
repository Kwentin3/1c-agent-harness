"""Fixed deployment-owned 1C registration-log exporter.

The companion supplies one closed JSON request on stdin. Deployment alone binds
the selected file infobase, runtime profile, compiled EPF and task-owned work root.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
import threading
import time
from typing import Any

COLUMNS = (
    "Date", "Level", "Event", "EventPresentation", "User", "UserPresentation",
    "Metadata", "MetadataPresentation", "TransactionStatus",
)
ENVIRONMENT_KEYS = (
    "ONE_C_HARNESS_EVENTLOG_RUNTIME_PROFILE",
    "ONE_C_HARNESS_EVENTLOG_INFOBASE",
    "ONE_C_HARNESS_EVENTLOG_EPF",
    "ONE_C_HARNESS_EVENTLOG_WORK_ROOT",
    "ONE_C_HARNESS_EVENTLOG_USERNAME",
    "ONE_C_HARNESS_EVENTLOG_PASSWORD",
    "ONE_C_HARNESS_EVENTLOG_METRICS",
)
_REQUEST_KEYS = {
    "schemaVersion", "operation", "start", "end", "filters", "columns", "maximumCount", "maximumBytes",
}
_FILTERS = {"event", "level", "user", "metadata"}
_TIMEOUT_SECONDS = 115
_MAX_BYTES = 1024 * 1024
_DIAGNOSTIC_BYTES = 4096
_DIAGNOSTIC_MESSAGE_BYTES = 512


class ExportFailure(RuntimeError):
    """Stable non-secret exporter failure."""

    def __init__(self, reason_code: str, diagnostic: dict[str, object] | None = None):
        super().__init__(reason_code)
        self.diagnostic = diagnostic


class _BoundedStderr:
    def __init__(self) -> None:
        self._digest = hashlib.sha256()
        self._payload = bytearray()
        self.byte_count = 0

    def consume(self, stream: object) -> None:
        assert hasattr(stream, "read")
        while chunk := stream.read(4096):
            self.byte_count += len(chunk)
            self._digest.update(chunk)
            if len(self._payload) < _DIAGNOSTIC_BYTES:
                self._payload.extend(chunk[:_DIAGNOSTIC_BYTES - len(self._payload)])

    def join(self, reader: threading.Thread) -> None:
        reader.join(timeout=2)

    def summary(self) -> dict[str, object]:
        return _diagnostic_summary(bytes(self._payload), self.byte_count, self._digest.hexdigest())


@dataclass(frozen=True)
class Settings:
    platform: Path
    xvfb: Path
    libs: str
    fontconfig: Path
    infobase: Path
    epf: Path
    work_root: Path
    username: str | None
    password: str | None
    metrics: Path | None


def _plain_file(path: Path, executable: bool = False) -> bool:
    try:
        mode = path.stat().st_mode
    except OSError:
        return False
    return path.is_absolute() and not path.is_symlink() and stat.S_ISREG(mode) and (not executable or os.access(path, os.X_OK))


def _load_settings(*, require_epf: bool = True) -> Settings:
    values = {key: os.environ.get(key) for key in ENVIRONMENT_KEYS}
    required = ENVIRONMENT_KEYS[:4]
    if any(not values[key] for key in required):
        raise ExportFailure("configuration_invalid")
    profile_path = Path(values[required[0]] or "")
    if not _plain_file(profile_path):
        raise ExportFailure("configuration_invalid")
    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        if set(profile) < {"platform", "xvfb", "libs", "fontconfig"}:
            raise ValueError
        platform = Path(profile["platform"])
        xvfb = Path(profile["xvfb"])
        libs = profile["libs"]
        fontconfig = Path(profile["fontconfig"])
        infobase = Path(values[required[1]] or "")
        epf = Path(values[required[2]] or "")
        work_root = Path(values[required[3]] or "")
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        raise ExportFailure("configuration_invalid") from None
    if not isinstance(libs, str) or not libs or not _plain_file(platform, True) or not _plain_file(xvfb, True):
        raise ExportFailure("configuration_invalid")
    if not _plain_file(fontconfig) or not infobase.is_absolute() or infobase.is_symlink() or not infobase.is_dir():
        raise ExportFailure("configuration_invalid")
    if require_epf and not _plain_file(epf):
        raise ExportFailure("configuration_invalid")
    if not work_root.is_absolute() or work_root.is_symlink():
        raise ExportFailure("configuration_invalid")
    work_root.mkdir(parents=True, exist_ok=True)
    metrics_value = values[ENVIRONMENT_KEYS[-1]]
    metrics = Path(metrics_value) if metrics_value else None
    if metrics is not None and (not metrics.is_absolute() or metrics.is_symlink()):
        raise ExportFailure("configuration_invalid")
    return Settings(
        platform, xvfb, libs, fontconfig, infobase, epf, work_root,
        values[ENVIRONMENT_KEYS[4]], values[ENVIRONMENT_KEYS[5]], metrics,
    )


def _validate_request(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _REQUEST_KEYS:
        raise ExportFailure("invalid_request")
    if value.get("schemaVersion") != 1 or value.get("operation") != "unloadEventLog":
        raise ExportFailure("invalid_request")
    try:
        start = datetime.fromisoformat(value["start"])
        end = datetime.fromisoformat(value["end"])
    except (TypeError, ValueError):
        raise ExportFailure("invalid_request") from None
    if start.tzinfo is not None or end.tzinfo is not None or end < start or (end - start).total_seconds() > 86400:
        raise ExportFailure("invalid_request")
    filters = value.get("filters")
    if not isinstance(filters, dict) or set(filters) - _FILTERS:
        raise ExportFailure("invalid_request")
    if any(not isinstance(item, str) or not item or len(item) > 128 or any(ord(ch) < 32 for ch in item) for item in filters.values()):
        raise ExportFailure("invalid_request")
    if value.get("columns") != list(COLUMNS):
        raise ExportFailure("invalid_request")
    maximum = value.get("maximumCount")
    maximum_bytes = value.get("maximumBytes")
    if type(maximum) is not int or not 1 <= maximum <= 100:
        raise ExportFailure("invalid_request")
    if type(maximum_bytes) is not int or not 4096 <= maximum_bytes <= _MAX_BYTES:
        raise ExportFailure("invalid_request")
    return value


def _environment(settings: Settings, home: Path, temporary: Path) -> dict[str, str]:
    environment = dict(os.environ)
    environment["LD_LIBRARY_PATH"] = f"{settings.platform.parent}:{settings.libs}"
    environment["FONTCONFIG_FILE"] = str(settings.fontconfig)
    environment["PATH"] = f"{settings.xvfb.parent}:{environment.get('PATH', '')}"
    environment["HOME"] = str(home)
    environment["TMPDIR"] = str(temporary)
    return environment


def _prefix(settings: Settings) -> list[str]:
    return [
        str(settings.xvfb), "-a", "-s", "-screen 0 1024x768x8 -nolisten tcp", str(settings.platform),
    ]


def _connection(settings: Settings) -> list[str]:
    result = ["/F", str(settings.infobase)]
    if settings.username:
        result += ["/N", settings.username]
    if settings.password:
        result += ["/P", settings.password]
    return result


def _stop_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=2)


def _safe_message(payload: bytes) -> str | None:
    text = payload.decode("utf-8", errors="replace")
    lines = []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue
        line = line.replace("\x00", "")
        if "/" in line:
            line = "<path-redacted>"
        if len(line.encode("utf-8")) > _DIAGNOSTIC_MESSAGE_BYTES:
            line = line.encode("utf-8")[:_DIAGNOSTIC_MESSAGE_BYTES].decode("utf-8", errors="ignore")
        lines.append(line)
        break
    return lines[0] if lines else None


def _diagnostic_summary(payload: bytes, byte_count: int, digest: str) -> dict[str, object]:
    if byte_count == 0:
        return {"state": "empty"}
    result: dict[str, object] = {
        "state": "captured" if byte_count <= len(payload) else "truncated",
        "byteCount": byte_count,
        "sha256": digest,
    }
    message = _safe_message(payload)
    if message is not None:
        result["message"] = message
    return result


def _file_diagnostic(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        return {"state": "not_created"}
    try:
        with path.open("rb") as stream:
            payload = stream.read(_DIAGNOSTIC_BYTES)
        byte_count = path.stat().st_size
    except OSError:
        return {"state": "unreadable"}
    return _diagnostic_summary(payload, byte_count, hashlib.sha256(payload).hexdigest())


def _runtime_diagnostic(
    root: Path, process: subprocess.Popen[bytes], stderr: _BoundedStderr, started: float,
) -> dict[str, object]:
    return {
        "stage": "enterprise_process",
        "wrapperExitCode": process.returncode,
        "lifecycleMilliseconds": round((time.monotonic() - started) * 1000),
        "receipts": {name: (root / name).is_file() for name in (
            "client-entered", "server-entered", "export-started", "export-returned", "complete",
        )},
        "stderr": stderr.summary(),
        "runtimeLog": _file_diagnostic(root / "runtime.log"),
        "dumpResult": _file_diagnostic(root / "runtime.result"),
    }


def _write_request(root: Path, request: dict[str, Any]) -> None:
    start = datetime.fromisoformat(request["start"]).strftime("%Y%m%d%H%M%S")
    end = datetime.fromisoformat(request["end"]).strftime("%Y%m%d%H%M%S")
    (root / "start.txt").write_text(start, encoding="utf-8")
    (root / "end.txt").write_text(end, encoding="utf-8")
    (root / "maximum-count.txt").write_text(str(request["maximumCount"]), encoding="ascii")
    for name in sorted(_FILTERS):
        (root / f"filter-{name}.txt").write_text(request["filters"].get(name, ""), encoding="utf-8")


def run_once(request: object) -> tuple[bytes, dict[str, object]]:
    admitted = _validate_request(request)
    settings = _load_settings()
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="request-", dir=settings.work_root) as raw_root:
        root = Path(raw_root)
        home = root / "home"; home.mkdir()
        temporary = root / "tmp"; temporary.mkdir()
        _write_request(root, admitted)
        argv = _prefix(settings) + [
            "ENTERPRISE", *_connection(settings), "/DisableStartupDialogs", "/DisableStartupMessages",
            "/Execute", str(settings.epf), "/C", str(root),
            "/Out", str(root / "runtime.log"), "/DumpResult", str(root / "runtime.result"),
        ]
        try:
            process = subprocess.Popen(
                argv, env=_environment(settings, home, temporary), stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, start_new_session=True,
            )
        except OSError:
            raise ExportFailure("source_unavailable") from None
        assert process.stderr is not None
        stderr = _BoundedStderr()
        reader = threading.Thread(target=stderr.consume, args=(process.stderr,), daemon=True)
        reader.start()
        deadline = started + _TIMEOUT_SECONDS
        export_started: float | None = None
        export_returned: float | None = None
        output = root / "output.xml"
        while process.poll() is None:
            now = time.monotonic()
            if export_started is None and (root / "export-started").is_file():
                export_started = now
            if export_returned is None and (root / "export-returned").is_file():
                export_returned = now
            try:
                output_size = output.stat().st_size
            except OSError:
                output_size = 0
            if output_size > admitted["maximumBytes"]:
                _stop_group(process)
                stderr.join(reader)
                process.stderr.close()
                raise ExportFailure("source_byte_limit", _runtime_diagnostic(root, process, stderr, started))
            if now >= deadline:
                _stop_group(process)
                stderr.join(reader)
                process.stderr.close()
                raise ExportFailure("source_timeout", _runtime_diagnostic(root, process, stderr, started))
            time.sleep(.02)
        ended = time.monotonic()
        stderr.join(reader)
        process.stderr.close()
        diagnostic = _runtime_diagnostic(root, process, stderr, started)
        if process.returncode != 0:
            raise ExportFailure("source_process_failed", diagnostic)
        required = ("client-entered", "server-entered", "export-started", "export-returned", "complete")
        if any(not (root / name).is_file() for name in required) or not output.is_file():
            raise ExportFailure("source_incomplete_receipt", diagnostic)
        xml = output.read_bytes()
        if len(xml) > admitted["maximumBytes"]:
            raise ExportFailure("source_byte_limit", diagnostic)
        if export_started is None:
            export_started = started
        if export_returned is None:
            export_returned = ended
        metrics: dict[str, object] = {
            "status": "ok", "selectedInfoBase": "configured_file_infobase", "exporterInvocations": 1,
            "lifecycleMilliseconds": round((ended - started) * 1000),
            "exportMilliseconds": round(max(0, export_returned - export_started) * 1000),
            "xmlBytes": len(xml),
        }
        if settings.metrics is not None:
            settings.metrics.parent.mkdir(parents=True, exist_ok=True)
            temporary_metrics = settings.metrics.with_suffix(".tmp")
            temporary_metrics.write_text(json.dumps(metrics, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            os.replace(temporary_metrics, settings.metrics)
        return xml, metrics


def build_epf(destination: Path) -> dict[str, object]:
    settings = _load_settings(require_epf=False)
    if not destination.is_absolute() or destination.is_symlink():
        raise ExportFailure("configuration_invalid")
    source = Path(__file__).with_name("eventlog_epf") / "Issue80EventLog.xml"
    if not source.is_file():
        raise ExportFailure("configuration_invalid")
    with tempfile.TemporaryDirectory(prefix="build-", dir=settings.work_root) as raw_root:
        root = Path(raw_root); ib = root / "ib"; home = root / "home"; home.mkdir(); temporary = root / "tmp"; temporary.mkdir()
        environment = _environment(settings, home, temporary)
        commands = (
            _prefix(settings) + ["CREATEINFOBASE", f"File={ib}", "/DisableStartupDialogs", "/DisableStartupMessages", "/Out", str(root / "create.log"), "/DumpResult", str(root / "create.result")],
            _prefix(settings) + ["DESIGNER", "/F", str(ib), "/DisableStartupDialogs", "/DisableStartupMessages", "/LoadExternalDataProcessorOrReportFromFiles", str(source), str(destination), "/Out", str(root / "build.log"), "/DumpResult", str(root / "build.result")],
        )
        for argv in commands:
            completed = subprocess.run(argv, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90, check=False, start_new_session=True)
            if completed.returncode != 0:
                raise ExportFailure("build_failed")
        try:
            dump_result = (root / "build.result").read_text(encoding="utf-8-sig").strip()
        except OSError:
            raise ExportFailure("build_failed") from None
        if dump_result != "0" or not _plain_file(destination):
            raise ExportFailure("build_failed")
        return {"status": "ok", "epfBytes": destination.stat().st_size}


def _write_failure_receipt(reason_code: str, diagnostic: dict[str, object] | None = None) -> None:
    raw = os.environ.get("ONE_C_HARNESS_EVENTLOG_METRICS")
    if not raw:
        return
    path = Path(raw)
    parent = path.parent
    if not path.is_absolute() or path.is_symlink() or not parent.is_dir() or parent.is_symlink():
        return
    temporary = path.with_suffix(".tmp")
    try:
        receipt: dict[str, object] = {"reasonCode": reason_code, "status": "failed"}
        if diagnostic is not None:
            receipt["diagnostic"] = diagnostic
        temporary.write_text(
            json.dumps(receipt, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        os.replace(temporary, path)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _public_failure(reason_code: str, diagnostic: dict[str, object] | None) -> dict[str, object]:
    result: dict[str, object] = {"reasonCode": reason_code}
    if not isinstance(diagnostic, dict) or diagnostic.get("stage") != "enterprise_process":
        return result
    result["stage"] = "enterprise_process"
    for name in ("runtimeLog", "stderr", "dumpResult"):
        value = diagnostic.get(name)
        if isinstance(value, dict) and isinstance(value.get("message"), str):
            result["message"] = value["message"]
            break
    return result


def main() -> int:
    diagnostic: dict[str, object] | None = None
    try:
        if len(sys.argv) == 3 and sys.argv[1] == "--build":
            result = build_epf(Path(sys.argv[2]))
            sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")
            return 0
        if len(sys.argv) != 1:
            raise ExportFailure("invalid_arguments")
        request = json.loads(sys.stdin.buffer.read(65537))
        xml, _metrics = run_once(request)
        sys.stdout.buffer.write(xml)
        return 0
    except (json.JSONDecodeError, UnicodeDecodeError):
        failure = "invalid_request"
    except ExportFailure as exc:
        failure = str(exc)
        diagnostic = exc.diagnostic
    _write_failure_receipt(failure, diagnostic)
    sys.stderr.write(json.dumps(_public_failure(failure, diagnostic), sort_keys=True, separators=(",", ":")) + "\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
