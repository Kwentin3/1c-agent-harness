"""Temporary registration-log levels, owned by the native Get/Set API.

Deployment supplies the fixed Settings, state directory and validated target.
The model cannot select a database, processing file or state path. Starting a
profile adds required levels; it never disables pre-existing registration.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import secrets
import stat
import tempfile

from . import eventlog_exporter

_LEVELS = {"Error", "Warning", "Information", "Note"}
_PROFILES = {"errors": {"Error"}, "diagnostic": _LEVELS}


def _levels(value: object) -> list[str]:
    if (not isinstance(value, list) or any(not isinstance(v, str) or v not in _LEVELS for v in value)
            or len(value) != len(set(value))):
        raise ValueError("native_settings_invalid")
    return sorted(value)


def native(settings: eventlog_exporter.Settings, request: dict[str, object]) -> dict[str, object]:
    """Get, or compare then set, levels through the repository-owned native EPF."""
    if request == {"action": "get"}:
        admitted = request
    elif set(request) == {"action", "levels", "expectedLevels"} and request["action"] == "set":
        admitted = {"action": "set", "levels": _levels(request["levels"]),
                    "expectedLevels": _levels(request["expectedLevels"])}
    else:
        raise ValueError("invalid_request")
    raw, _ = eventlog_exporter.run_epf(settings, admitted, settings_request=True)
    value = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(value, dict) or set(value) - {"status", "levels", "reasonCode"}:
        raise ValueError("native_settings_invalid")
    if value.get("status") not in {"ok", "conflict"}:
        raise ValueError("native_settings_failed")
    if admitted["action"] == "get" and value["status"] != "ok":
        raise ValueError("native_settings_invalid")
    current = _levels(value.get("levels"))
    if value["status"] == "ok" and admitted["action"] == "set" and current != admitted["levels"]:
        raise ValueError("native_readback_mismatch")
    return {"status": value["status"], "levels": current}


@contextmanager
def _locked(root: Path):
    # Only deployment chooses this single persistent per-target directory.
    if not root.is_absolute() or any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError("configuration_invalid")
    root.mkdir(mode=0o700, exist_ok=True)
    if not root.is_dir():
        raise ValueError("configuration_invalid")
    import fcntl
    fd = os.open(root / "control.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("configuration_invalid")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("access_busy") from None
        yield
    finally:
        os.close(fd)


def _load(root: Path, target_ref: str) -> dict[str, object] | None:
    path = root / "registration.json"
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return None
    with os.fdopen(fd, "rb") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ValueError("configuration_invalid")
        raw = source.read(4097)
    if len(raw) > 4096:
        raise ValueError("configuration_invalid")
    state = json.loads(raw)
    if (not isinstance(state, dict)
            or set(state) != {"targetRef", "captureRef", "profile", "before", "applied", "phase"}
            or state["targetRef"] != target_ref or state["profile"] not in _PROFILES
            or state["phase"] not in {"prepared", "applied", "restored"}
            or not isinstance(state["captureRef"], str)
            or not re.fullmatch(r"capture:[0-9a-f]{32}", state["captureRef"])):
        raise ValueError("configuration_conflict")
    state["before"] = _levels(state["before"])
    state["applied"] = _levels(state["applied"])
    if state["applied"] != sorted(set(state["before"]) | _PROFILES[state["profile"]]):
        raise ValueError("configuration_invalid")
    return state


def _store(root: Path, state: dict[str, object]) -> None:
    fd, name = tempfile.mkstemp(prefix=".registration-", dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(state, output, sort_keys=True)
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, root / "registration.json")
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def control(
    action: str, settings: eventlog_exporter.Settings, state_directory: Path,
    target_ref: str, *, profile: str | None = None, capture_ref: str | None = None,
) -> dict[str, object]:
    """One native configuration transaction; keep a recoverable baseline first."""
    if (not isinstance(target_ref, str) or not re.fullmatch(r"target:[0-9a-f]{64}", target_ref)
            or action not in {"status", "start", "stop"}
            or (action == "start" and profile not in _PROFILES)
            or (action == "stop" and not isinstance(capture_ref, str))):
        raise ValueError("invalid_request")
    with _locked(state_directory):
        state = _load(state_directory, target_ref)
        current = native(settings, {"action": "get"})["levels"]
        result: dict[str, object] = {
            "status": "ok", "journal": "registration", "targetRef": target_ref,
            "state": "configured" if current else "inactive", "platformState": "observed",
            "configurationState": "unchanged", "capabilities": {"status": True, "start": True, "stop": True},
        }
        active = state is not None and state["phase"] != "restored"
        if action == "status":
            if active:
                result.update(captureRef=state["captureRef"], profile=state["profile"])
                expected = (state["before"], state["applied"]) if state["phase"] == "prepared" else (state["applied"],)
                if current not in expected:
                    result.update(status="conflict", configurationState="conflict", reasonCode="configuration_conflict")
            return result
        if action == "start":
            if active and state["profile"] != profile:
                return {**result, "status": "conflict", "reasonCode": "collection_active"}
            if not active:
                state = {"targetRef": target_ref, "captureRef": "capture:" + secrets.token_hex(16),
                         "profile": profile, "before": current,
                         "applied": sorted(set(current) | _PROFILES[profile]), "phase": "prepared"}
                _store(state_directory, state)
            assert state is not None
            result.update(captureRef=state["captureRef"], profile=state["profile"])
            if current == state["applied"]:
                state["phase"] = "applied"
                _store(state_directory, state)
                return {**result, "configurationState": "applied"}
            if current != state["before"] or state["phase"] == "applied":
                return {**result, "status": "conflict", "configurationState": "conflict", "reasonCode": "configuration_conflict"}
            changed = native(settings, {"action": "set", "expectedLevels": current, "levels": state["applied"]})
            if changed["status"] != "ok":
                return {**result, "status": "conflict", "configurationState": "conflict", "reasonCode": "configuration_conflict"}
            state["phase"] = "applied"
            _store(state_directory, state)
            return {**result, "state": "configured", "configurationState": "applied"}
        if state is None or state["captureRef"] != capture_ref:
            return {**result, "status": "blocked", "reasonCode": "capture_not_found"}
        result.update(captureRef=state["captureRef"], profile=state["profile"])
        if state["phase"] == "restored" and current != state["before"]:
            return {**result, "status": "conflict", "configurationState": "conflict", "reasonCode": "configuration_conflict"}
        if state["phase"] == "restored" or (state["phase"] == "prepared" and current == state["before"]):
            state["phase"] = "restored"
            _store(state_directory, state)
            return {**result, "configurationState": "restored"}
        if current != state["applied"]:
            return {**result, "status": "conflict", "configurationState": "conflict", "reasonCode": "configuration_conflict"}
        restored = native(settings, {"action": "set", "expectedLevels": current, "levels": state["before"]})
        if restored["status"] != "ok":
            return {**result, "status": "conflict", "configurationState": "conflict", "reasonCode": "configuration_conflict"}
        state["phase"] = "restored"
        _store(state_directory, state)
        return {**result, "state": "configured" if state["before"] else "inactive", "configurationState": "restored"}
