"""Canonical deterministic implementation of the installed 1C Harness core."""
from __future__ import annotations

import json
from pathlib import Path

CAPABILITY_VERSION = "0.1.0"

_release = json.loads((Path(__file__).with_name("release.json")).read_text(encoding="utf-8"))
if set(_release) != {"schemaVersion", "artifactId"} or _release["schemaVersion"] != 1 or not isinstance(_release["artifactId"], str):
    raise RuntimeError("invalid one-c-harness release manifest")
ARTIFACT_ID = _release["artifactId"]
