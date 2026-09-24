"""Thin adapter: closed JSON request -> public Hermes terminal tool -> closed JSON response."""
from __future__ import annotations

import base64
import copy
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


def _all_have_equal(items: list[dict[str, Any]], key: str) -> bool:
    return bool(items) and all(key in item for item in items) and all(
        item[key] == items[0][key] for item in items[1:]
    )


def _compact_groups(groups: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    compact = copy.deepcopy(groups)
    common: dict[str, Any] = {}
    for key in ("event", "countScope"):
        if _all_have_equal(compact, key):
            common[key] = compact[0][key]
            for group in compact:
                del group[key]
    summaries = [group.get("summary") for group in compact]
    if all(isinstance(summary, dict) for summary in summaries) and _all_have_equal(summaries, "meaning"):
        common["summary"] = {"meaning": summaries[0]["meaning"]}
        for group in compact:
            del group["summary"]["meaning"]
            if not group["summary"]:
                del group["summary"]
    return common, compact


def _compact_records(records: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    compact = copy.deepcopy(records)
    common: dict[str, Any] = {}
    for key in ("event", "errorSignature", "technical"):
        if _all_have_equal(compact, key):
            common[key] = compact[0][key]
            for record in compact:
                del record[key]
    errors = [record.get("error") for record in compact]
    if all(isinstance(error, dict) for error in errors):
        error_common: dict[str, Any] = {}
        if _all_have_equal(errors, "exceptionType"):
            error_common["exceptionType"] = errors[0]["exceptionType"]
            for error in errors:
                del error["exceptionType"]
        descriptions = [error.get("description") for error in errors]
        if all(isinstance(description, dict) for description in descriptions):
            description_common: dict[str, Any] = {}
            for key in ("fragment", "redacted", "truncated", "status", "fingerprint"):
                if _all_have_equal(descriptions, key):
                    description_common[key] = descriptions[0][key]
                    for description in descriptions:
                        del description[key]
            if description_common:
                error_common["description"] = description_common
        if error_common:
            common["error"] = error_common
        for record in compact:
            error = record.get("error")
            if isinstance(error, dict):
                if error.get("description") == {}:
                    del error["description"]
                if not error:
                    del record["error"]
    return common, compact


def _has_incomplete_read(value: object) -> bool:
    if isinstance(value, dict):
        if value.get("partial") is True or value.get("complete") is False:
            return True
        return any(_has_incomplete_read(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_incomplete_read(item) for item in value)
    return False


def _is_known_diagnostic_form(response: dict[str, Any], operation: str) -> bool:
    if operation == "observation_info":
        return (
            isinstance(response.get("coverage"), dict)
            and isinstance(response.get("observedInterval"), dict)
            and isinstance(response.get("observedEvents"), list)
            and isinstance(response.get("source"), str)
            and isinstance(response.get("sourceTimeZone"), str)
        )
    if operation == "observe":
        groups = response.get("groups")
        return (
            isinstance(groups, list)
            and all(isinstance(group, dict) for group in groups)
            and isinstance(response.get("groupsTruncated"), bool)
            and isinstance(response.get("observationRef"), str)
            and isinstance(response.get("snapshot"), dict)
            and isinstance(response.get("summary"), dict)
        )
    if operation != "expand_observation" or not isinstance(response.get("snapshot"), dict):
        return False
    level = response.get("level")
    if level == "observation":
        groups = response.get("groups")
        return (
            isinstance(groups, list) and all(isinstance(group, dict) for group in groups)
            and isinstance(response.get("total"), int)
        )
    if level == "group":
        records = response.get("records")
        return (
            isinstance(records, list) and all(isinstance(record, dict) for record in records)
            and isinstance(response.get("total"), int)
        )
    if level == "record":
        before = response.get("before")
        after = response.get("after")
        return (
            isinstance(before, list) and all(isinstance(record, dict) for record in before)
            and isinstance(response.get("record"), dict)
            and isinstance(after, list) and all(isinstance(record, dict) for record in after)
            and isinstance(response.get("scope"), str)
            and isinstance(response.get("relation"), str)
        )
    return False


def _compact_diagnostic_response(response: dict[str, Any], operation: str) -> dict[str, Any]:
    if (
        operation not in {"observation_info", "observe", "expand_observation"}
        or response.get("operation") != operation
        or response.get("status") != "ok"
        or not _is_known_diagnostic_form(response, operation)
        or _has_incomplete_read(response)
    ):
        return response
    compact = copy.deepcopy(response)
    for key in ("artifactId", "capabilityVersion", "schemaVersion", "operation"):
        compact.pop(key, None)
    groups = compact.get("groups")
    if isinstance(groups, list) and len(groups) > 1 and all(isinstance(group, dict) for group in groups):
        common, compact_groups = _compact_groups(groups)
        compact["groups"] = compact_groups
        if common:
            compact["groupCommon"] = common
            compact["groupCommonAppliesTo"] = "every item in groups in this response"
    records = compact.get("records")
    if isinstance(records, list) and len(records) > 1 and all(isinstance(record, dict) for record in records):
        common, compact_records = _compact_records(records)
        compact["records"] = compact_records
        if common:
            compact["recordCommon"] = common
            compact["recordCommonAppliesTo"] = "every item in records in this response"
    if compact.get("level") == "record":
        before = compact.get("before")
        target = compact.get("record")
        after = compact.get("after")
        if (
            isinstance(before, list) and isinstance(target, dict) and isinstance(after, list)
            and all(isinstance(record, dict) for record in [*before, target, *after])
            and len(before) + 1 + len(after) > 1
        ):
            common, compact_records = _compact_records([*before, target, *after])
            before_count = len(before)
            compact["before"] = compact_records[:before_count]
            compact["record"] = compact_records[before_count]
            compact["after"] = compact_records[before_count + 1:]
            if common:
                compact["recordCommon"] = common
                compact["recordCommonAppliesTo"] = "every item in before, record and after in this response"
    return compact


def _call(ctx: Any, operation: str, arguments: object, timeout: int) -> str:
    try:
        request = _request(operation, arguments)
        encoded = base64.b64encode(request).decode("ascii")
        command = f'"$HERMES_HOME/bin/one-c-harness" --request-base64 {encoded}'
        raw = ctx.dispatch_tool("terminal", {"command": command, "timeout": timeout})
        response = json.loads(_parse_terminal(raw))
        if not isinstance(response, dict) or response.get("capabilityVersion") != CAPABILITY_VERSION:
            return _blocked("companion_version_mismatch", "installed executor companion version does not match plugin")
        if response.get("artifactId") != ARTIFACT_ID:
            return _blocked("companion_artifact_mismatch", "installed executor companion artifact does not match plugin")
        response = _compact_diagnostic_response(response, operation)
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


def observation_info(ctx: Any) -> Callable[[object], str]:
    def handler(arguments: object, **_kwargs: object) -> str:
        if arguments != {}:
            return _blocked("invalid_request", "observation_info does not accept arguments")
        return _call(ctx, "observation_info", arguments, 60)
    return handler


def observe(ctx: Any) -> Callable[[object], str]:
    def handler(arguments: object, **_kwargs: object) -> str:
        return _call(ctx, "observe", arguments, 60)
    return handler


def expand_observation(ctx: Any) -> Callable[[object], str]:
    def handler(arguments: object, **_kwargs: object) -> str:
        return _call(ctx, "expand_observation", arguments, 60)
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
