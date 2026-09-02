#!/usr/bin/env python3
"""Business oracle for the representative SupplierInvoice task."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import shared_task_route

IDENTITY_FIELDS = (
    "runId",
    "deletedCaseId",
    "activeCaseId",
    "nonce",
)
RESPONSE_FIELD = "responseToken"
REGISTERS = (
    "Purchases",
    "InventoryInWarehouses",
    "SupplierBalance",
    "InventoryCost",
)


def expected_payload() -> dict[str, str]:
    payload = {
        "deletedWarehouseMarked": "Yes",
        "deletedDraftSucceeded": "Yes",
        "deletedDraftRefFilled": "Yes",
        "deletedPostingSucceeded": "No",
        "deletedPostingErrorPresent": "Yes",
        "deletedPosted": "No",
        "activeWarehouseMarked": "No",
        "activePostingSucceeded": "Yes",
        "activePostingErrorPresent": "No",
        "activePosted": "Yes",
        "complete": "true",
    }
    for prefix in ("deletedBefore", "deletedAfter", "activeBefore"):
        for register in REGISTERS:
            payload[f"{prefix}{register}Count"] = "0"
            payload[f"{prefix}{register}Quantity"] = "0"
            payload[f"{prefix}{register}Amount"] = "0"
    for register in REGISTERS:
        payload[f"activeAfter{register}Count"] = "1"
        payload[f"activeAfter{register}Quantity"] = "0"
        payload[f"activeAfter{register}Amount"] = "0"
    payload.update({
        "activeAfterPurchasesQuantity": "2",
        "activeAfterPurchasesAmount": "20",
        "activeAfterInventoryInWarehousesQuantity": "2",
        "activeAfterSupplierBalanceAmount": "20",
        "activeAfterInventoryCostAmount": "20",
    })
    return payload


def _rows(raw_receipt: bytes) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in raw_receipt.decode("utf-8-sig").splitlines():
        key, separator, value = line.partition("###")
        if not separator or not key or key in rows:
            raise ValueError("malformed or duplicate business row")
        rows[key] = value
    return rows


def evaluate(
    request: dict[str, object],
    client_receipt: bytes,
    server_receipt: bytes,
) -> dict[str, str]:
    client = _rows(client_receipt)
    server = _rows(server_receipt)
    for field in IDENTITY_FIELDS:
        expected = request.get(field)
        if client.get(field) != expected or server.get(field) != expected:
            raise ValueError(f"foreign {field}")
    client_token = client.get(RESPONSE_FIELD)
    server_token = server.get(RESPONSE_FIELD)
    if not client_token or client_token != server_token:
        raise ValueError("client/server response token mismatch")
    if client_token == request.get("nonce"):
        raise ValueError("response token echoes nonce")
    if client.get("complete") != "true":
        raise ValueError("client receipt is incomplete")

    excluded = {*IDENTITY_FIELDS, RESPONSE_FIELD}
    payload = {key: value for key, value in server.items() if key not in excluded}
    if payload != expected_payload():
        raise ValueError("wrong business payload")
    return payload


def _verify_patch_bytes(receipt: dict[str, object]) -> None:
    expected = {
        item["role"]: item["sha256"]
        for item in receipt["patches"]
    }
    for role in ("production", "instrumentation"):
        payload = Path(__file__).with_name(f"exact-{role}.patch").read_bytes()
        actual = hashlib.sha256(payload).hexdigest()
        if expected.get(role) != actual:
            raise ValueError(f"{role} patch bytes do not match receipt")


def validate(receipt: dict[str, object]) -> None:
    shared_task_route.validate_provenance_receipt(receipt)
    _verify_patch_bytes(receipt)
    request = receipt["request"]["payload"]
    client = base64.b64decode(
        receipt["runtime"]["clientReceipt"]["base64"],
        validate=True,
    )
    server = base64.b64decode(
        receipt["business"]["rawReceipt"]["base64"],
        validate=True,
    )
    payload = evaluate(request, client, server)
    if payload != receipt["business"]["payload"]:
        raise ValueError("receipt business payload differs from raw bytes")


def _route_result(args: argparse.Namespace) -> dict[str, object]:
    request = json.loads(args.request.read_text(encoding="utf-8"))
    payload = evaluate(
        request,
        args.client_receipt.read_bytes(),
        args.server_receipt.read_bytes(),
    )
    return {
        "status": "PASS",
        "task": "supplier-invoice-warehouse-deletion",
        "businessPayload": payload,
    }


def _frozen_result() -> dict[str, object]:
    receipt_path = Path(__file__).with_name("receipt.json")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    validate(receipt)
    return {
        "status": "PASS",
        "task": "issue46-green-on-standard-receipt",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--client-receipt", type=Path)
    parser.add_argument("--server-receipt", type=Path)
    args = parser.parse_args(argv)
    route_mode = any((args.request, args.client_receipt, args.server_receipt))
    if route_mode and not all((args.request, args.client_receipt, args.server_receipt)):
        parser.error("all three route receipt arguments are required together")
    try:
        result = _route_result(args) if route_mode else _frozen_result()
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
