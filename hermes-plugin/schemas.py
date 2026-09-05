"""Closed tool schemas for the terminal-bound 1C Harness plugin."""
from __future__ import annotations

import json
from pathlib import Path

CAPABILITY_VERSION = "0.1.0"
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
)
