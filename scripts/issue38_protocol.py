#!/usr/bin/env python3
"""Portable request/response primitives for Issue #38 transport experiments."""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Final


PROTOCOL_VERSION: Final = "issue38-v5"
OPERATION: Final = "serverWitness"
_DELIMITER: Final = "###"
_SAFE_VALUE: Final = re.compile(r"^[A-Za-z0-9._:-]+$")
_HEADERS: Final = ("protocolVersion", "runId", "caseId", "nonce", "operation")
_CLIENT_ROWS: Final = (
    ("runtimeStarted", "true", "Boolean"),
    ("probeEntered", "true", "Boolean"),
    ("serverCallIssued", "true", "Boolean"),
    ("serverReached", "true", "Boolean"),
    ("caseStarted", "true", "Boolean"),
)
_SERVER_ROWS: Final = (
    ("serverReached", "true", "Boolean"),
    ("caseStarted", "true", "Boolean"),
)
_CLIENT_FAILURE_MILESTONES: Final = {
    "serverCallFailure": _CLIENT_ROWS[:3],
    "taskException": _CLIENT_ROWS,
}


class ProtocolError(ValueError):
    """A receipt cannot prove the frozen Issue #38 protocol result."""


def _unique_request_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    request: dict[str, object] = {}
    for key, value in pairs:
        if key in request:
            raise ProtocolError(f"duplicate request key: {key}")
        request[key] = value
    return request


def new_request() -> dict[str, object]:
    """Create one fresh, transport-neutral server witness request."""
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "runId": str(uuid.uuid4()),
        "caseId": str(uuid.uuid4()),
        "nonce": str(uuid.uuid4()),
        "operation": OPERATION,
        "requiresServer": True,
    }


def _decode_receipt(label: str, payload: bytes | None) -> list[tuple[str, str, str]]:
    if payload is None:
        raise ProtocolError(f"{label} receipt is absent")
    try:
        text = payload.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise ProtocolError(f"{label} receipt is not UTF-8") from exc
    if not text or not text.endswith("\n") or "\r" in text.replace("\r\n", ""):
        raise ProtocolError(f"{label} receipt has invalid line delimiters")
    normalized = text.replace("\r\n", "\n")
    lines = normalized[:-1].split("\n")
    if not lines or any(not line for line in lines):
        raise ProtocolError(f"{label} receipt is empty")
    rows: list[tuple[str, str, str]] = []
    for line in lines:
        parts = line.split(_DELIMITER)
        if len(parts) != 3 or not all(parts):
            raise ProtocolError(f"{label} receipt has malformed record")
        if not all(_SAFE_VALUE.fullmatch(part) for part in parts):
            raise ProtocolError(f"{label} receipt has unsafe record value")
        rows.append((parts[0], parts[1], parts[2]))
    return rows


def _identity_rows(request: dict[str, object]) -> tuple[tuple[str, str, str], ...]:
    values: list[tuple[str, str, str]] = []
    expected = {
        "protocolVersion": PROTOCOL_VERSION,
        "operation": OPERATION,
    }
    for key in _HEADERS:
        value = request.get(key)
        if not isinstance(value, str) or not value or not _SAFE_VALUE.fullmatch(value):
            raise ProtocolError(f"request has invalid {key}")
        if key in ("runId", "caseId", "nonce"):
            try:
                parsed = uuid.UUID(value)
            except ValueError as exc:
                raise ProtocolError(f"request has invalid {key}") from exc
            if parsed.version != 4:
                raise ProtocolError(f"request has invalid {key}")
        if key in expected and value != expected[key]:
            raise ProtocolError(f"request has unsupported {key}")
        values.append((key, value, "String"))
    if request.get("requiresServer") is not True:
        raise ProtocolError("request must require server")
    return tuple(values)


def _validate_receipt(
    label: str,
    payload: bytes | None,
    identity: tuple[tuple[str, str, str], ...],
    milestones: tuple[tuple[str, str, str], ...],
) -> str:
    rows = _decode_receipt(label, payload)
    expected_prefix = identity + milestones
    expected_suffix = (("complete", "true", "Boolean"),)
    if len(rows) != len(expected_prefix) + 2:
        raise ProtocolError(f"{label} receipt has unexpected record count")
    if tuple(rows[:len(expected_prefix)]) != expected_prefix:
        raise ProtocolError(f"{label} receipt has foreign identity or invalid milestone sequence")
    result = rows[len(expected_prefix)]
    if result[0] != "businessResult" or result[2] != "String" or not _SAFE_VALUE.fullmatch(result[1]):
        raise ProtocolError(f"{label} receipt has invalid business result")
    if tuple(rows[-1:]) != expected_suffix:
        raise ProtocolError(f"{label} receipt has invalid completion")
    return result[1]


def validate_terminal(
    request: dict[str, object], client_receipt: bytes | None, server_receipt: bytes | None,
) -> dict[str, str]:
    """Validate either the sole success result or a typed client-side failure."""
    identity = _identity_rows(request)
    client_rows = _decode_receipt("client", client_receipt)
    prefix_size = len(identity)
    if tuple(client_rows[:prefix_size]) != identity:
        raise ProtocolError("client receipt has foreign identity")
    remaining = client_rows[prefix_size:]
    reached: list[tuple[str, str, str]] = []
    for milestone in _CLIENT_ROWS:
        if remaining and remaining[0] == milestone:
            reached.append(remaining.pop(0))
        else:
            break
    if not remaining:
        raise ProtocolError("client receipt has no terminal result")
    if remaining[0][0] == "businessResult":
        return validate_success(request, client_receipt, server_receipt)
    if remaining[0][0] != "failureClass" or remaining[0][2] != "String":
        raise ProtocolError("client receipt has no typed failure class")
    failure_class = remaining.pop(0)[1]
    required_milestones = _CLIENT_FAILURE_MILESTONES.get(failure_class)
    if required_milestones is None:
        raise ProtocolError("client receipt has unsupported failure class")
    if tuple(reached) != required_milestones:
        raise ProtocolError(f"{failure_class} has invalid milestone stage")
    detail: str | None = None
    if remaining and remaining[0][0] == "failureDetail" and remaining[0][2] == "String":
        detail = remaining.pop(0)[1]
    if remaining != [("complete", "true", "Boolean")]:
        raise ProtocolError("client receipt has invalid typed failure completion")
    if server_receipt is not None:
        raise ProtocolError("server receipt is forbidden on typed client failure")
    response = {"status": "failure", "failureClass": failure_class}
    if detail is not None:
        response["failureDetail"] = detail
    return response


def validate_success(
    request: dict[str, object], client_receipt: bytes | None, server_receipt: bytes | None,
) -> dict[str, str]:
    """Validate both current-run receipts for the sole success protocol outcome."""
    identity = _identity_rows(request)
    client_token = _validate_receipt("client", client_receipt, identity, _CLIENT_ROWS)
    server_token = _validate_receipt("server", server_receipt, identity, _SERVER_ROWS)
    if client_token != server_token:
        raise ProtocolError("client and server receipts have different server tokens")
    if client_token == request["nonce"]:
        raise ProtocolError("server token must differ from request nonce")
    return {"status": "success", "serverToken": client_token}


def main(argv: list[str] | None = None) -> int:
    """Validate one frozen request against its client/server receipts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--client-receipt", required=True, type=Path)
    parser.add_argument("--server-receipt", type=Path)
    args = parser.parse_args(argv)
    try:
        try:
            request_text = args.request.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ProtocolError("request is not UTF-8") from exc
        request = json.loads(request_text, object_pairs_hook=_unique_request_object)
        if not isinstance(request, dict):
            raise ProtocolError("request must be a JSON object")
        client = args.client_receipt.read_bytes()
        server = args.server_receipt.read_bytes() if args.server_receipt is not None else None
        response = validate_terminal(request, client, server)
    except (OSError, json.JSONDecodeError, ProtocolError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(response, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
