#!/usr/bin/env python3
"""Fail-closed validator for the bounded Issue #43 evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import uuid

EXPECTED_RULE = {
    "seedFromState": "10|10|50",
    "seedToState": "0|0|0",
    "sameDraftSucceeded": "Yes",
    "sameDraftPersisted": "Yes",
    "samePostingSucceeded": "No",
    "samePostingErrorPresent": "Yes",
    "samePosted": "No",
    "sameInventoryMovementCount": "0",
    "sameCostMovementCount": "0",
    "sameStateAfterPosting": "10|10|50",
    "validPosted": "Yes",
    "validInventoryMovementCount": "2",
    "validCostMovementCount": "2",
    "validFromState": "7|7|35",
    "validToState": "3|3|15",
    "complete": "true",
}
EXPECTED_REQUEST_KEYS = {
    "protocolVersion", "operation", "scenario", "runId", "caseId", "nonce"
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_receipt(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        assert raw, "empty receipt record"
        key, separator, value = raw.partition("###")
        assert separator and key and value, f"invalid receipt record: {raw!r}"
        assert key not in rows, f"duplicate receipt key: {key}"
        rows[key] = value
    return rows


def validate_request(request: dict[str, str], expected_scenario: str) -> None:
    assert set(request) == EXPECTED_REQUEST_KEYS
    assert request["protocolVersion"] == "issue43-v1"
    assert request["operation"] == "inventoryTransferSameWarehouseRule"
    assert request["scenario"] == expected_scenario
    for key in ("runId", "caseId", "nonce"):
        value = uuid.UUID(request[key])
        assert value.version == 4 and str(value) == request[key]
    assert len({request["runId"], request["caseId"], request["nonce"]}) == 3


def validate_receipt(
    path: Path,
    request: dict[str, str],
    *,
    expected_scenario: str,
    expect_rule: bool,
) -> dict[str, str]:
    validate_request(request, expected_scenario)
    actual = parse_receipt(path)
    expected = {
        "scenario": expected_scenario,
        "protocolVersion": request["protocolVersion"],
        "runId": request["runId"],
        "caseId": request["caseId"],
        "nonce": request["nonce"],
        **(EXPECTED_RULE if expect_rule else {}),
    }
    assert actual == expected, f"receipt mismatch: {actual!r}"
    return actual


def validate_runner_result(path: Path, receipt_path: Path) -> dict:
    result = json.loads(path.read_text(encoding="utf-8"))
    assert result["status"] == "runtime_contract_completed"
    assert result["runtime"]["completed"] is True
    assert result["runtime"]["completeMarker"] == "complete###true"
    assert result["runtime"]["stableReads"] == 2
    assert result["runtime"]["receipt"]["terminalMarker"] is True
    assert result["runtime"]["receipt"]["sha256"] == sha256(receipt_path)
    assert result["runtime"]["receiptSha256"] == sha256(receipt_path)
    assert result["input"]["sourceTreeSha256"] == result["input"]["copiedTreeSha256"]
    assert result["input"]["sourceTreeSha256"] == result["inputAfter"]["sha256"]
    assert result["preparedInvocation"]["sourceBefore"] == result["preparedInvocation"]["sourceAfter"]
    compaction = result["storageCompaction"]
    assert compaction["status"] == "completed"
    assert compaction["manualCleanupActions"] == 0
    assert set(compaction["completedRemovedPaths"]) == {
        "frozen-input", "run/work-copy", "run/ib", "run/home", "run/tmp"
    }
    return result


def validate_package(root: Path) -> None:
    manifest_path = root / "package-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual_files = sorted(
        p.relative_to(root).as_posix()
        for p in root.iterdir()
        if p.is_file() and p.name != manifest_path.name
    )
    assert actual_files == sorted(manifest["files"])
    assert manifest["sha256"] == {name: sha256(root / name) for name in manifest["files"]}

    contract = json.loads((root / "contract-identity.json").read_text(encoding="utf-8"))
    assert contract["baseCommit"] == "5c6b0e9c2b20a1fb15aa69ae49539b9786cf816b"
    assert contract["baseTree"] == "03407c6c5fbcac550db3f5a2ea48bbdac0a791a3"
    assert contract["sourceCfSha256"] == "5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a"
    assert contract["snapshotManifestSha256"] == "70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691"
    assert contract["snapshotFileCount"] == 5099

    production = (root / "production.patch").read_text(encoding="utf-8")
    assert production.count("--- a/") == production.count("+++ b/") == 1
    assert "Documents/InventoryTransfer/Ext/ObjectModule.bsl" in production
    assert "If Warehouse = WarehouseReceiver Then" in production
    assert "Cancel = True;" in production and "Return;" in production

    requests = []
    for lane in (1, 2):
        scenario = f"issue43-bound-green-{lane}"
        request = json.loads((root / f"bound-green-{lane}-request.json").read_text(encoding="utf-8"))
        prepare = json.loads((root / f"bound-green-{lane}-prepare.json").read_text(encoding="utf-8"))
        assert prepare["request"] == request
        assert prepare["files"] == 5099
        patch = (root / f"bound-green-{lane}-instrumentation.patch").read_text(encoding="utf-8")
        assert patch.count("--- a/") == patch.count("+++ b/") == 2
        for value in (scenario, request["runId"], request["caseId"], request["nonce"]):
            assert value in patch
        receipt = root / f"bound-green-{lane}-receipt.txt"
        validate_receipt(receipt, request, expected_scenario=scenario, expect_rule=True)
        result = validate_runner_result(root / f"bound-green-{lane}-result.json", receipt)
        meta = json.loads((root / f"bound-green-{lane}-meta.json").read_text(encoding="utf-8"))
        assert meta["wallNs"] > 0
        assert result["totalDurationSeconds"] > 0
        requests.append(request)

    for key in ("runId", "caseId", "nonce"):
        assert requests[0][key] != requests[1][key]


if __name__ == "__main__":
    validate_package(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent)
    print("PASS issue43 package: exact business semantics, identity binding, native repeat, and closure")
