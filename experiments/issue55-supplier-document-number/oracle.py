#!/usr/bin/env python3
"""Fail-closed validator for the Issue #55 SupplierInvoice native receipts."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def rows(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        key, marker, value = line.partition("###")
        if not marker or not key or key in result:
            raise ValueError("malformed or duplicate receipt row")
        result[key] = value
    return result


def yes(value: str) -> bool:
    return value.lower() in {"yes", "true", "да"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--client-receipt", type=Path, required=True)
    parser.add_argument("--server-receipt", type=Path, required=True)
    args = parser.parse_args()
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        client, server = rows(args.client_receipt), rows(args.server_receipt)
        for key in ("runId", "caseId", "nonce"):
            if client.get(key) != request[key] or server.get(key) != request[key]:
                raise ValueError(f"foreign {key}")
        token = client.get("responseToken", "")
        if not token or token == request["nonce"] or server.get("responseToken") != token:
            raise ValueError("unbound server response")
        if client.get("complete") != "true" or server.get("complete") != "true":
            raise ValueError("incomplete receipt")
        expected = {
            "draft_blank": True,
            "missing_number": False,
            "first_same_supplier": True,
            "duplicate_same_supplier": False,
            "same_number_other_supplier": True,
            "repost_same_document": True,
            "existing_behavior": True,
        }
        for key, required in expected.items():
            if key not in server or yes(server[key]) != required:
                raise ValueError(f"business case failed: {key}")
        for prefix in ("missing", "duplicate"):
            for index in range(1, 5):
                if server.get(f"{prefix}.movement{index}") != "0":
                    raise ValueError(f"rejected posting has movements: {prefix}.{index}")
    except Exception as exc:
        print(f"FAIL: {exc}", file=__import__("sys").stderr)
        return 1
    print(json.dumps({"status": "PASS", "task": "supplier-document-number", "businessPayload": {"draftWithoutNumber": "saved", "missingNumber": "rejected-no-movements", "sameSupplierDuplicate": "rejected-no-movements", "otherSupplier": "posted", "selfRepost": "posted"}}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
