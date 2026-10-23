"""Coordinate native Relay jobs; Relay owns selection, permissions and execution.

Only deployment chooses the launcher. Harness owns affinity of its opaque refs;
the plugin state stores no device selection, credentials or job queue.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from typing import Any
from uuid import uuid4

_OUTPUT_LIMIT = 40 * 1024
_REF_LOCK = threading.RLock()
_REF_FIELDS = frozenset({"snapshotRef", "taskRef", "targetRef", "captureRef", "selectionRef",
                         "recordRef", "observationRef", "groupRef", "findingRef", "evidenceRef"})


class RelayFailure(Exception):
    def __init__(self, reason: str, *, outcome: object = None, job: object = None, device: object = None):
        super().__init__(reason)
        self.reason, self.outcome, self.job = reason, outcome, job
        self.device = device


def _unknown() -> dict[str, object]:
    return {"status": "unknown", "may_have_run": True, "automatic_retry": False,
            "absence_established": False,
            "message": "The Harness job may have run. Reconcile the exact Relay job; do not repeat the operation."}


def setting(ctx: Any, key: str, default: object = None) -> object:
    """Use native plugin settings; old contexts retain only the legacy default."""
    try:
        getter = getattr(ctx, "get_config", None)
        return getter(key, default) if callable(getter) else default
    except Exception:
        raise RelayFailure("transport_configuration_unavailable") from None


def _refs(value: object):
    """Read only declared Harness reference positions, never journal/user data."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _REF_FIELDS and isinstance(item, (str, dict)):
                # Whole structured refs are one immutable value, not a path.
                yield item
            elif key in {"records", "before", "after", "record", "diagnostic"}:
                yield from _refs(item)
            elif key == "groups" and isinstance(item, list):
                for group in item:
                    if not isinstance(group, dict):
                        continue
                    ref = group.get("ref")
                    if isinstance(ref, str) and re.fullmatch(r"snapshot:[a-f0-9]{32}:group:[A-Za-z0-9:._-]+", ref):
                        yield ref
                    yield from _refs(group)
            elif key == "snapshot" and isinstance(item, dict):
                ref = item.get("ref")
                if isinstance(ref, str) and re.fullmatch(r"[a-f0-9]{32}", ref):
                    yield ref
    elif isinstance(value, list):
        for item in value:
            yield from _refs(item)


def _ref_key(value: object) -> str:
    wire = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "relay-ref." + hashlib.sha256(wire.encode("utf-8")).hexdigest()


def expected_device(ctx: Any, arguments: object) -> str | None:
    devices = set()
    try:
        with _REF_LOCK:
            for ref in _refs(arguments):
                device = ctx.state.get(_ref_key(ref))
                if not isinstance(device, str) or not device:
                    raise RelayFailure("relay_reference_unbound")
                devices.add(device)
    except RelayFailure:
        raise
    except Exception:
        raise RelayFailure("relay_reference_state_unavailable") from None
    if len(devices) > 1:
        raise RelayFailure("relay_reference_target_mismatch")
    return next(iter(devices), None)


def bind_refs(ctx: Any, response: dict[str, object], device: str) -> None:
    try:
        with _REF_LOCK:
            keys = {_ref_key(ref) for ref in _refs(response)}
            for key in keys:
                existing = ctx.state.get(key)
                if existing is not None and existing != device:
                    raise RelayFailure("relay_reference_target_mismatch")
            for key in keys:
                ctx.state.set(key, device)
                if ctx.state.get(key) != device:
                    raise RelayFailure("relay_reference_target_mismatch")
    except RelayFailure:
        raise
    except Exception:
        raise RelayFailure("relay_reference_state_unavailable") from None


def _dispatch(ctx: Any, name: str, arguments: dict[str, object], context: dict[str, object],
              expected: str | None) -> tuple[str, dict[str, object]]:
    args: dict[str, object] = {"tool_name": name, "arguments": arguments}
    if expected is not None:
        args["expected_device_id"] = expected
    try:
        envelope = json.loads(ctx.dispatch_tool("relay_dispatch", args, **context))
    except Exception:
        raise RelayFailure("relay_dispatch_failed", outcome=_unknown()) from None
    if not isinstance(envelope, dict):
        raise RelayFailure("relay_response_invalid", outcome=_unknown())
    marker = envelope.get("relay_outcome")
    device, result = envelope.get("device_id"), envelope.get("result")
    if marker is not None:
        raise RelayFailure("relay_outcome_unknown", outcome=marker, device=device)
    if not isinstance(device, str) or not device or not isinstance(result, dict):
        raise RelayFailure("relay_dispatch_refused")
    if result.get("ok") is not True or result.get("error"):
        raise RelayFailure("relay_dispatch_refused")
    if expected is not None and device != expected:
        raise RelayFailure("relay_device_mismatch", outcome=_unknown())
    target = result.get("target")
    if not isinstance(target, dict) or target.get("device_id") != device:
        raise RelayFailure("relay_device_mismatch", outcome=_unknown())
    payload = result.get("result")
    if not isinstance(payload, dict):
        raise RelayFailure("relay_response_invalid", outcome=_unknown())
    return device, payload


def execute(ctx: Any, request: bytes, arguments: object, timeout: int,
            kwargs: dict[str, object]) -> tuple[str, str, dict[str, object]]:
    """Start exactly once, then read status/output from the same selected device."""
    session = kwargs.get("session_id")
    if not isinstance(session, str) or not session:
        raise RelayFailure("relay_session_missing")
    context = {key: kwargs[key] for key in ("session_id", "task_id") if key in kwargs}
    command = setting(ctx, "relay_command", "")
    if (not isinstance(command, str) or not command or len(command.encode("utf-8")) > 4096
            or any(ord(c) < 32 for c in command)):
        raise RelayFailure("relay_launcher_unconfigured")
    # Check native PluginState before dispatch, even when this operation has no refs.
    if not hasattr(getattr(ctx, "state", None), "get") or not hasattr(ctx.state, "set"):
        raise RelayFailure("relay_reference_state_unavailable")
    device = expected_device(ctx, arguments)
    deadline = time.monotonic() + timeout
    job_id = str(uuid4())
    job = {"job_id": job_id, "device_id": device}
    started_confirmed = False
    try:
        device, started = _dispatch(ctx, "desktop_job_start", {"command": command,
            "stdin": request.decode("utf-8"), "job_id": job_id}, context, device)
        started_confirmed = True
        job["device_id"] = device
        if started.get("job_id") != job_id:
            raise RelayFailure("relay_job_invalid", outcome=_unknown())
        while True:
            _, status = _dispatch(ctx, "desktop_job_status", {"job_id": job_id}, context, device)
            if status.get("job_id") != job_id:
                raise RelayFailure("relay_job_invalid", outcome=_unknown())
            state = status.get("state")
            if state == "exited" and type(status.get("exit_code")) is int:
                break
            if state != "running":
                raise RelayFailure("relay_job_outcome_unknown", outcome=_unknown())
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RelayFailure("relay_job_pending", outcome=_unknown())
            time.sleep(min(1.0, remaining))
        if status["exit_code"] != 0:
            job["exit_code"] = status["exit_code"]
            raise RelayFailure("relay_job_failed", outcome=_unknown())
        _, logs = _dispatch(ctx, "desktop_job_logs", {"job_id": job_id, "stream": "stdout",
            "offset": 0, "limit": _OUTPUT_LIMIT + 1}, context, device)
        if logs.get("job_id") != job_id or logs.get("state") != "exited" or logs.get("exit_code") != 0:
            raise RelayFailure("relay_job_output_invalid", outcome=_unknown())
        output = logs.get("stdout")
        if not isinstance(output, dict) or not isinstance(output.get("content"), str):
            raise RelayFailure("relay_job_output_invalid", outcome=_unknown())
        content = output["content"]
        length = len(content.encode("utf-8"))
        if (output.get("truncated") is not False or type(output.get("total_bytes")) is not int
                or type(output.get("offset")) is not int or length > _OUTPUT_LIMIT
                or output["total_bytes"] != length or output["offset"] != length):
            raise RelayFailure("relay_job_output_incomplete", outcome=_unknown())
        return device, content, job
    except RelayFailure as exc:
        if isinstance(exc.device, str) and exc.device:
            job["device_id"] = exc.device
        if started_confirmed or exc.outcome is not None:
            exc.job = job
            if exc.outcome is None:
                exc.outcome = _unknown()
        raise
