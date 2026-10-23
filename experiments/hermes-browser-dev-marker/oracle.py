"""Task-only marker assertion over bound native client/server receipt data.

PASS does not prove the private function call by itself. Root must also review
the frozen patches/call site and their binding to the native receipts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import uuid

MAX_BYTES = 4096
MARKER_PREFIX = "HERMES_BROWSER_DEV_"
SCOPE = "private managed-application marker in disposable IB"
CLIENT_KEYS = ("run", "nonce", "token", "marker", "returned", "complete")
SERVER_KEYS = ("run", "nonce", "token", "marker", "serverComplete")


def _read(path: Path) -> bytes:
    with path.open("rb") as stream:
        payload = stream.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("input byte limit exceeded")
    return payload


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate request key")
        result[key] = value
    return result


def _request(payload: bytes) -> dict[str, str]:
    request = json.loads(payload.decode("utf-8-sig"), object_pairs_hook=_unique_object)
    if not isinstance(request, dict) or set(request) != {"runId", "nonce"}:
        raise ValueError("request must contain only runId and nonce")
    for value in request.values():
        if not isinstance(value, str):
            raise ValueError("request identity must be a canonical UUID4")
        parsed = uuid.UUID(value)
        if str(parsed) != value or parsed.version != 4 or parsed.variant != uuid.RFC_4122:
            raise ValueError("request identity must be a canonical UUID4")
    if request["runId"] == request["nonce"]:
        raise ValueError("request identities must differ")
    return request


def _receipt(payload: bytes, keys: tuple[str, ...]) -> dict[str, str]:
    text = payload.decode("utf-8-sig")
    if not text.endswith("\n"):
        raise ValueError("receipt needs a final newline")
    text = text.replace("\r\n", "\n")
    if "\r" in text:
        raise ValueError("receipt has an invalid line delimiter")
    lines = text[:-1].split("\n")
    if len(lines) != len(keys):
        raise ValueError("receipt row count is invalid")
    result: dict[str, str] = {}
    for key, line in zip(keys, lines):
        fields = line.split("###")
        if len(fields) != 2 or fields[0] != key or not fields[1]:
            raise ValueError("receipt has an invalid, duplicate or out-of-order row")
        result[key] = fields[1]
    return result


def evaluate(request_path: Path, client_path: Path, server_path: Path) -> dict[str, object]:
    request = _request(_read(request_path))
    client = _receipt(_read(client_path), CLIENT_KEYS)
    server = _receipt(_read(server_path), SERVER_KEYS)
    marker = MARKER_PREFIX + request["nonce"]
    for receipt in (client, server):
        if receipt["run"] != request["runId"] or receipt["nonce"] != request["nonce"]:
            raise ValueError("receipt has stale or foreign request identity")
        if receipt["marker"] != marker:
            raise ValueError("native marker mismatch")
    # The enclosing 4 KiB receipt bounds this opaque nonempty token. Its native
    # generator has no additional character or UUID-version contract here.
    token = server["token"]
    if token != client["token"] or token in {request["runId"], request["nonce"], marker}:
        raise ValueError("native server witness mismatch")
    if client["returned"] != "true" or client["complete"] != "true" or server["serverComplete"] != "true":
        raise ValueError("native call is incomplete")
    return {
        "status": "PASS",
        "businessPayload": {
            "marker": marker,
            "clientServerWitnessMatched": True,
            "scope": SCOPE,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--client-receipt", type=Path, required=True)
    parser.add_argument("--server-receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = evaluate(args.request, args.client_receipt, args.server_receipt)
    except (OSError, UnicodeError, ValueError, RecursionError):
        # No untrusted payload or raw path/exception is echoed.
        print("FAIL: invalid marker request or native receipt data", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
