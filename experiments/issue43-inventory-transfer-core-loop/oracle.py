#!/usr/bin/env python3
"""Small CLI oracle retained for direct RED/GREEN receipt checks."""
from pathlib import Path
import sys


def parse(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        key, separator, value = raw.partition("###")
        if not separator or not key or not value or key in rows:
            raise RuntimeError(f"invalid receipt row: {raw!r}")
        rows[key] = value
    return rows


common = {
    "seedFromState": "10|10|50", "seedToState": "0|0|0",
    "sameDraftSucceeded": "Yes", "sameDraftPersisted": "Yes",
    "validPosted": "Yes", "validInventoryMovementCount": "2",
    "validCostMovementCount": "2", "validFromState": "7|7|35",
    "validToState": "3|3|15", "complete": "true",
}
red = {
    **common, "scenario": "issue43-red", "samePostingSucceeded": "Yes",
    "samePostingErrorPresent": "No", "samePosted": "Yes",
    "sameInventoryMovementCount": "2", "sameCostMovementCount": "2",
    "sameStateAfterPosting": "10|10|50",
}
green = {
    **common, "samePostingSucceeded": "No", "samePostingErrorPresent": "Yes",
    "samePosted": "No", "sameInventoryMovementCount": "0",
    "sameCostMovementCount": "0", "sameStateAfterPosting": "10|10|50",
}
mode, receipt = sys.argv[1:3]
expected = red if mode == "red" else {**green, "scenario": f"issue43-{mode}"}
actual = parse(Path(receipt))
if actual != expected:
    raise RuntimeError(f"{mode.upper()} mismatch: {actual!r}")
print(f"PASS issue43 {mode}: exact server-side posting and persisted-state contract")
