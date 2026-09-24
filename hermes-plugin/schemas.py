"""Closed tool schemas for the terminal-bound 1C Harness plugin."""
from __future__ import annotations

import json
from pathlib import Path

CAPABILITY_VERSION = "0.3.0"
_release = json.loads((Path(__file__).with_name("release.json")).read_text(encoding="utf-8"))
if set(_release) != {"schemaVersion", "artifactId"} or _release["schemaVersion"] != 1 or not isinstance(_release["artifactId"], str):
    raise RuntimeError("invalid one-c-harness plugin release manifest")
ARTIFACT_ID = _release["artifactId"]

_SNAPSHOT_REF = {
    "type": "object",
    "description": "Exact SnapshotRef object returned by one_c_open; not a filesystem path.",
}
_RELATIVE_FILE = {
    "type": "string",
    "minLength": 1,
    "maxLength": 512,
    "description": "Project-relative task artifact path. Absolute and parent paths are rejected by the companion.",
}


def _tool(name: str, properties: dict[str, object], required: list[str], description: str) -> dict[str, object]:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    }


def _eventlog_filters() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            name: {"type": "string", "minLength": 1, "maxLength": 128}
            for name in ("event", "level", "user", "metadata")
        },
        "additionalProperties": False,
    }


TOOLS = (
    _tool("one_c_open", {}, [], "Open the admitted target in the currently selected Hermes terminal workspace."),
    _tool(
        "one_c_narrow_context",
        {
            "snapshotRef": _SNAPSHOT_REF,
            "query": {"type": "string", "minLength": 1, "maxLength": 4096},
            "mode": {"type": "string", "enum": ["literal", "regex"]},
            "pathPrefix": {"type": "string", "maxLength": 512},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            "maxBytes": {"type": "integer", "minimum": 256, "maximum": 32768},
        },
        ["snapshotRef", "query"],
        "Search only the admitted SnapshotRef and return bounded matches with stable source locators.",
    ),
    _tool(
        "one_c_native_verify",
        {
            "snapshotRef": _SNAPSHOT_REF,
            "request": _RELATIVE_FILE,
            "productionPatch": _RELATIVE_FILE,
            "instrumentationPatch": _RELATIVE_FILE,
            "oracle": _RELATIVE_FILE,
            "receipt": _RELATIVE_FILE,
            "timeoutSeconds": {"type": "integer", "minimum": 1, "maximum": 480},
        },
        ["snapshotRef", "request", "productionPatch", "instrumentationPatch", "oracle", "receipt", "timeoutSeconds"],
        "Run the canonical one-call native route on the admitted SnapshotRef and return a bounded receipt summary.",
    ),
    _tool(
        "one_c_observation_info", {}, [],
        "Inspect bounded technological-journal coverage and report the source timezone, observed interval, events and filters. For a later observe call in that same source timezone, preserve the returned calendar date/time and fractional seconds but omit its Z or numeric offset.",
    ),
    _tool(
        "one_c_observe",
        {
            "start": {"type": "string", "description": "Inclusive calendar start in the configured source timezone, without Z or a numeric offset; preserve fractional seconds, e.g. 2026-09-18T15:25:00.123456."},
            "end": {"type": "string", "description": "Inclusive calendar end in that same source timezone, without Z or a numeric offset; preserve fractional seconds."},
            "events": {"type": "array", "minItems": 1, "maxItems": 8, "items": {"type": "string", "minLength": 1, "maxLength": 32}},
            "filters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "minLength": 1, "maxLength": 120, "pattern": "[^\\u0009-\\u000D\\u001C-\\u0020\\u0085\\u00A0\\u1680\\u2000-\\u200A\\u2028\\u2029\\u202F\\u205F\\u3000]"},
                    "sourceComponent": {"type": "string", "pattern": "^[A-Za-z0-9_.:-]{1,128}(?![\\s\\S])"},
                    "process": {"type": "string", "pattern": "^[A-Za-z0-9_.:-]{1,128}(?![\\s\\S])"},
                },
                "additionalProperties": False,
                "description": "Optional AND filters over the safe projected technical content only.",
            },
            "limit": {"type": "integer", "minimum": 1, "maximum": 20},
        }, ["start", "end", "events", "limit"],
        "Summarize platform-authored technological-journal errors in one source-local calendar interval. Successful complete pages may use groupCommon for fields shared by every returned group.",
    ),
    {
        "name": "one_c_expand_observation",
        "description": "Page groups or records from one retained observation, or show bounded time-adjacent records around one exact retained record. On successful complete pages, groupCommon applies to every returned group and recordCommon to every returned record named by the response.",
        "parameters": {
            "type": "object",
            "oneOf": [
                {"properties": {"observationRef": {"type": "string", "minLength": 1, "maxLength": 256}, "offset": {"type": "integer", "minimum": 0}, "limit": {"type": "integer", "minimum": 1, "maximum": 20}}, "required": ["observationRef", "offset", "limit"], "additionalProperties": False},
                {"properties": {"groupRef": {"type": "string", "minLength": 1, "maxLength": 256}, "offset": {"type": "integer", "minimum": 0}, "limit": {"type": "integer", "minimum": 1, "maximum": 20}}, "required": ["groupRef", "offset", "limit"], "additionalProperties": False},
                {"properties": {"recordRef": {"type": "string", "minLength": 1, "maxLength": 256}, "before": {"type": "integer", "minimum": 0, "maximum": 5}, "after": {"type": "integer", "minimum": 0, "maximum": 5}}, "required": ["recordRef", "before", "after"], "additionalProperties": False},
            ],
        },
    },
    _tool(
        "one_c_select_registration_log",
        {
            "start": {"type": "string", "description": "Inclusive source-local calendar start without an offset."},
            "end": {"type": "string", "description": "Inclusive source-local calendar end without an offset; at most 24 hours after start."},
            "filters": _eventlog_filters(),
            "maximumCount": {"type": "integer", "minimum": 1, "maximum": 100},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        ["start", "end", "filters", "maximumCount", "limit"],
        "Create one bounded retained selection from the configured 1C registration log source. At the maximum-count boundary the result is partial, never complete; an unavailable source is not an empty journal.",
    ),
    _tool(
        "one_c_page_registration_log",
        {
            "selectionRef": {"type": "string", "minLength": 1, "maxLength": 128},
            "offset": {"type": "integer", "minimum": 0},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20},
            "filters": _eventlog_filters(),
        },
        ["selectionRef", "offset", "limit"],
        "Page one exact retained registration-log selection. If display.partial is true, continue at the returned nextOffset; this does not re-export.",
    ),
    {
        "name": "one_c_read_registration_log_record",
        "description": (
            "Read one exact retained registration-log record. If commentContinuation is incomplete, "
            "repeat with its nextOffsetBytes as commentOffset to read the next UTF-8-safe chunk without re-exporting."
        ),
        "parameters": {
            "type": "object",
            "oneOf": [
                {
                    "properties": {
                        "recordRef": {"type": "string", "minLength": 1, "maxLength": 192},
                    },
                    "required": ["recordRef"], "additionalProperties": False,
                },
                {
                    "properties": {
                        "recordRef": {"type": "string", "minLength": 1, "maxLength": 192},
                        "commentOffset": {"type": "integer", "minimum": 0},
                        "commentMaxBytes": {"type": "integer", "minimum": 4, "maximum": 16384},
                    },
                    "required": ["recordRef", "commentOffset", "commentMaxBytes"],
                    "additionalProperties": False,
                },
            ],
        },
    },
)
