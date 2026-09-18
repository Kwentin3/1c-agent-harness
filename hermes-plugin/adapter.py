"""Thin adapter: closed JSON request -> public Hermes terminal tool -> closed JSON response."""
from __future__ import annotations

import base64
import json
from typing import Any, Callable

from .schemas import ARTIFACT_ID, CAPABILITY_VERSION

SCHEMA_VERSION = 1
MAX_TERMINAL_OUTPUT_BYTES = 40 * 1024


def _blocked(reason_code: str, message: str) -> str:
    return json.dumps({
        "artifactId": ARTIFACT_ID,
        "capabilityVersion": CAPABILITY_VERSION,
        "message": message,
        "reasonCode": reason_code,
        "schemaVersion": SCHEMA_VERSION,
        "status": "blocked",
    }, ensure_ascii=False, sort_keys=True)


def _request(operation: str, arguments: object) -> bytes:
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be an object")
    return json.dumps({
        "schemaVersion": SCHEMA_VERSION,
        "operation": operation,
        "arguments": arguments,
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _parse_terminal(raw: object) -> str:
    if not isinstance(raw, str):
        raise ValueError("terminal response is invalid")
    try:
        outer = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("terminal response is invalid") from exc
    if not isinstance(outer, dict) or outer.get("exit_code") != 0:
        raise RuntimeError("terminal command failed")
    output = outer.get("output")
    if not isinstance(output, str) or len(output.encode("utf-8")) > MAX_TERMINAL_OUTPUT_BYTES:
        raise ValueError("terminal output is invalid")
    lines = output.splitlines()
    if len(lines) != 1:
        raise ValueError("companion output is ambiguous")
    return lines[0]


def _call(ctx: Any, operation: str, arguments: object, timeout: int) -> str:
    try:
        request = _request(operation, arguments)
        encoded = base64.b64encode(request).decode("ascii")
        command = f"one-c-harness --request-base64 {encoded}"
        raw = ctx.dispatch_tool("terminal", {"command": command, "timeout": timeout})
        response = json.loads(_parse_terminal(raw))
        if not isinstance(response, dict) or response.get("capabilityVersion") != CAPABILITY_VERSION:
            return _blocked("companion_version_mismatch", "installed executor companion version does not match plugin")
        if response.get("artifactId") != ARTIFACT_ID:
            return _blocked("companion_artifact_mismatch", "installed executor companion artifact does not match plugin")
        return json.dumps(response, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except ValueError as exc:
        return _blocked("invalid_request", str(exc))
    except (OSError, RuntimeError, json.JSONDecodeError):
        return _blocked("terminal_failed", "terminal-bound companion command could not complete")
    except Exception:
        return _blocked("terminal_failed", "terminal-bound companion command could not complete")


def open_target(ctx: Any) -> Callable[[object], str]:
    def handler(arguments: object, **_kwargs: object) -> str:
        if arguments != {}:
            return _blocked("invalid_request", "open does not accept arguments")
        return _call(ctx, "open", arguments, 60)
    return handler


def narrow_context(ctx: Any) -> Callable[[object], str]:
    def handler(arguments: object, **_kwargs: object) -> str:
        return _call(ctx, "narrow", arguments, 90)
    return handler


def native_verify(ctx: Any) -> Callable[[object], str]:
    def handler(arguments: object, **_kwargs: object) -> str:
        if not isinstance(arguments, dict) or type(arguments.get("timeoutSeconds")) is not int:
            return _blocked("invalid_request", "verify timeoutSeconds is invalid")
        timeout = arguments["timeoutSeconds"] + 90
        if timeout > 600:
            return _blocked("invalid_request", "verify timeoutSeconds is invalid")
        return _call(ctx, "verify", arguments, timeout)
    return handler
