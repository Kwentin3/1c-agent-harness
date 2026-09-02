#!/usr/bin/env python3
"""Business oracle for the SupplierInvoice warehouse-deletion scenario."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

IDENTITY_FIELDS = ("runId", "deletedCaseId", "activeCaseId", "nonce")
REGISTERS = ("Purchases", "InventoryInWarehouses", "SupplierBalance", "InventoryCost")


def _expected() -> dict[str, str]:
    result = {
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
            result[f"{prefix}{register}Count"] = "0"
            result[f"{prefix}{register}Quantity"] = "0"
            result[f"{prefix}{register}Amount"] = "0"
    for register in REGISTERS:
        result[f"activeAfter{register}Count"] = "1"
        result[f"activeAfter{register}Quantity"] = "0"
        result[f"activeAfter{register}Amount"] = "0"
    result.update({
        "activeAfterPurchasesQuantity": "2",
        "activeAfterPurchasesAmount": "20",
        "activeAfterInventoryInWarehousesQuantity": "2",
        "activeAfterSupplierBalanceAmount": "20",
        "activeAfterInventoryCostAmount": "20",
    })
    return result


def _rows(payload: bytes) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in payload.decode("utf-8-sig").splitlines():
        key, separator, value = line.partition("###")
        if not separator or not key or key in rows:
            raise ValueError("malformed or duplicate business row")
        rows[key] = value
    return rows


def evaluate(request: dict[str, object], client_bytes: bytes, server_bytes: bytes) -> dict[str, str]:
    client = _rows(client_bytes)
    server = _rows(server_bytes)
    for field in IDENTITY_FIELDS:
        expected = request.get(field)
        if client.get(field) != expected or server.get(field) != expected:
            raise ValueError(f"foreign {field}")
    token = client.get("responseToken")
    if not token or token != server.get("responseToken"):
        raise ValueError("client/server response token mismatch")
    if token == request.get("nonce"):
        raise ValueError("response token echoes nonce")
    if client.get("complete") != "true":
        raise ValueError("client receipt is incomplete")
    excluded = {*IDENTITY_FIELDS, "responseToken"}
    business = {key: value for key, value in server.items() if key not in excluded}
    if business != _expected():
        raise ValueError("wrong business payload")
    return business


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--client-receipt", type=Path, required=True)
    parser.add_argument("--server-receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        business = evaluate(request, args.client_receipt.read_bytes(), args.server_receipt.read_bytes())
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "status": "PASS",
        "task": "supplier-invoice-warehouse-deletion",
        "businessPayload": business,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
