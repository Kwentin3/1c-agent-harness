#!/usr/bin/env python3
"""External oracle for issue #29 receipts; the BSL probe emits no PASS."""
from pathlib import Path


def parse(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        if not raw:
            continue
        key, separator, value = raw.partition("###")
        if not separator or key in rows:
            raise RuntimeError(f"invalid receipt row: {raw!r}")
        rows[key] = value
    return rows


root = Path(__file__).resolve().parent
red = parse(root / "red-receipt.txt")
green = parse(root / "green-receipt.txt")
expected_red = {
    "scenario": "issue29",
    "zeroDraftSucceeded": "Yes",
    "zeroPostingSucceeded": "Yes",
    "zeroPosted": "Yes",
    "negativeDraftSucceeded": "Yes",
    "negativePostingSucceeded": "Yes",
    "negativePosted": "Yes",
    "complete": "true",
}
expected_green = {
    "scenario": "issue29",
    "zeroDraftSucceeded": "Yes",
    "zeroPostingSucceeded": "No",
    "zeroPostingErrorPresent": "No",
    "zeroPosted": "No",
    "zeroMovementCount": "0",
    "zeroBalanceUnchanged": "Yes",
    "negativeDraftSucceeded": "Yes",
    "negativePostingSucceeded": "No",
    "negativePostingErrorPresent": "No",
    "negativePosted": "No",
    "negativeMovementCount": "0",
    "negativeBalanceUnchanged": "Yes",
    "validPosted": "Yes",
    "validMovementCount": "4",
    "validQuantityDelta": "5",
    "validAmountDelta": "31",
    "complete": "true",
}
if red != expected_red:
    raise RuntimeError(f"RED mismatch: {red!r}")
if green != expected_green:
    raise RuntimeError(f"GREEN mismatch: {green!r}")
print("PASS issue29 external oracle: honest RED and server-side GREEN behavior")
