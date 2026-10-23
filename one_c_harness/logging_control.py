"""Bounded transport to the deployment-owned native logging controller."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import time

_COMMAND_ENV = "ONE_C_HARNESS_LOGGING_COMMAND"
_TIMEOUT_SECONDS = 60
_MAX_REQUEST_BYTES = 4096
_MAX_STDOUT_BYTES = 16 * 1024
_MAX_STDERR_BYTES = 1024
_TARGET = re.compile(r"target:[0-9a-f]{64}\Z")
_CAPTURE = re.compile(r"capture:[0-9a-f]{32}\Z")


def validate_request(arguments: object) -> dict[str, object]:
    """Validate only the public wire shape; the native owner checks ref identity."""
    if not isinstance(arguments, dict):
        raise ValueError("invalid_request")
    action, journal = arguments.get("action"), arguments.get("journal")
    keys = {"action", "journal"}
    if action == "start":
        keys |= {"profile", "targetRef"}
    elif action == "stop":
        keys |= {"captureRef", "targetRef"}
    elif action != "status":
        raise ValueError("invalid_request")
    if set(arguments) != keys or journal not in ("registration", "technological"):
        raise ValueError("invalid_request")
    if action == "start" and arguments["profile"] not in ("errors", "diagnostic"):
        raise ValueError("invalid_request")
    for name, pattern in (("targetRef", _TARGET), ("captureRef", _CAPTURE)):
        if name in arguments and (not isinstance(arguments[name], str) or not pattern.fullmatch(arguments[name])):
            raise ValueError("invalid_request")
    request = {"schemaVersion": 1, **arguments}
    if len(json.dumps(request, separators=(",", ":")).encode("utf-8")) > _MAX_REQUEST_BYTES:
        raise ValueError("invalid_request")
    return request


def _failure(journal: object, reason: str, status: str = "unavailable") -> dict[str, object]:
    result: dict[str, object] = {"status": status, "state": "unknown", "reasonCode": reason,
                                "capabilities": {"status": False, "start": False, "stop": False}}
    if journal in ("registration", "technological"):
        result["journal"] = journal
    return result


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate_key")
        value[key] = item
    return value


def _project(raw: bytes, request: dict[str, object]) -> dict[str, object]:
    value = json.loads(raw, object_pairs_hook=_unique_object)
    if not isinstance(value, dict) or value.get("status") not in ("ok", "blocked", "unavailable", "conflict"):
        raise ValueError("invalid_response")
    if value.get("state") not in ("inactive", "configured", "collecting", "unknown") or value.get("journal") != request["journal"]:
        raise ValueError("invalid_response")
    capabilities = value.get("capabilities")
    if not isinstance(capabilities, dict) or set(capabilities) != {"status", "start", "stop"} or any(type(v) is not bool for v in capabilities.values()):
        raise ValueError("invalid_response")
    result = {name: value[name] for name in ("status", "state", "journal")}
    result["capabilities"] = dict(capabilities)
    for name, pattern in (("targetRef", _TARGET), ("captureRef", _CAPTURE)):
        if name in value:
            if not isinstance(value[name], str) or not pattern.fullmatch(value[name]):
                raise ValueError("invalid_response")
            result[name] = value[name]
    if value["status"] == "ok" and ("targetRef" not in result or (request["action"] == "start" and "captureRef" not in result)):
        raise ValueError("invalid_response")
    if value["status"] == "ok" and request["action"] in ("start", "stop"):
        if result["targetRef"] != request["targetRef"]:
            raise ValueError("invalid_response")
        if request["action"] == "stop" and result.get("captureRef") != request["captureRef"]:
            raise ValueError("invalid_response")
    choices = {"profile": ("errors", "diagnostic"),
               "configurationState": ("absent", "unchanged", "applied", "restored", "conflict"),
               "platformState": ("unknown", "observed")}
    for name, allowed in choices.items():
        if name in value:
            if value[name] not in allowed:
                raise ValueError("invalid_response")
            result[name] = value[name]
    if "reasonCode" in value:
        if not isinstance(value["reasonCode"], str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,79}", value["reasonCode"]):
            raise ValueError("invalid_response")
        result["reasonCode"] = value["reasonCode"]
    if "diagnosis" in value:
        diagnosis = value["diagnosis"]
        reasons = {
            "primaryReasonCode": (None, "source_timeout", "native_form_invalid", "native_readback_mismatch", "native_web_unavailable"),
            "platformReasonCode": (None, "training_connection_limit"),
            "exitReasonCode": (None, "native_exit_unproven"),
            "cleanupReasonCode": (None, "browser_cleanup_failed"),
        }
        if (value["status"] != "blocked" or request["journal"] != "registration"
                or not isinstance(diagnosis, dict) or set(diagnosis) != {"operationOutcome", "saveAttempted", *reasons}
                or type(diagnosis["saveAttempted"]) is not bool
                or diagnosis["operationOutcome"] not in ("completed", "refused", "unknown", "not_completed")
                or diagnosis["saveAttempted"] != (diagnosis["operationOutcome"] == "unknown")
                or any(diagnosis[key] not in allowed for key, allowed in reasons.items())):
            raise ValueError("invalid_response")
        result["diagnosis"] = dict(diagnosis)
    return result


def _stop(process: subprocess.Popen[bytes]) -> None:
    # The child owns this new process group; never signal another process group.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=.5)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=1)


def execute(arguments: object) -> dict[str, object]:
    try:
        request = validate_request(arguments)
    except (ValueError, TypeError):
        return _failure(None, "invalid_request", "blocked")
    journal = request["journal"]
    command = Path(os.environ.get(_COMMAND_ENV, ""))
    if not command.is_absolute() or command.is_symlink() or not command.is_file() or command.resolve() != command or not os.access(command, os.X_OK):
        return _failure(journal, "source_unavailable")
    process = None
    started = time.monotonic()
    stdout, stderr = bytearray(), bytearray()
    try:
        with selectors.DefaultSelector() as streams:
            process = subprocess.Popen([str(command)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, start_new_session=True)
            assert process.stdin is not None and process.stdout is not None and process.stderr is not None
            encoded = json.dumps(request, separators=(",", ":")).encode("utf-8")
            sent = 0
            os.set_blocking(process.stdin.fileno(), False)
            streams.register(process.stdin, selectors.EVENT_WRITE, None)
            streams.register(process.stdout, selectors.EVENT_READ, stdout)
            streams.register(process.stderr, selectors.EVENT_READ, stderr)
            stdout_eof = False
            while streams.get_map():
                if stdout_eof and process.poll() is not None:
                    break
                remaining = _TIMEOUT_SECONDS - (time.monotonic() - started)
                if remaining <= 0:
                    return _failure(journal, "source_timeout")
                for key, _ in streams.select(min(.05, remaining)):
                    if key.fileobj is process.stdin:
                        try:
                            sent += os.write(key.fd, encoded[sent:])
                        except BlockingIOError:
                            continue
                        if sent == len(encoded):
                            streams.unregister(process.stdin)
                            process.stdin.close()
                        continue
                    chunk = os.read(key.fd, 4096)
                    if not chunk:
                        stdout_eof |= key.fileobj is process.stdout
                        streams.unregister(key.fileobj)
                        continue
                    key.data.extend(chunk)
                    if len(stdout) > _MAX_STDOUT_BYTES or len(stderr) > _MAX_STDERR_BYTES:
                        return _failure(journal, "source_byte_limit")
            process.wait(timeout=max(.001, _TIMEOUT_SECONDS - (time.monotonic() - started)))
            if process.returncode or sent != len(encoded):
                return _failure(journal, "source_unavailable")
            return _project(bytes(stdout), request)
    except subprocess.TimeoutExpired:
        return _failure(journal, "source_timeout")
    except OSError:
        return _failure(journal, "source_unavailable")
    except (ValueError, TypeError, subprocess.SubprocessError):
        return _failure(journal, "source_invalid_response")
    finally:
        if process is not None:
            _stop(process)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
