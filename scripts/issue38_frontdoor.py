#!/usr/bin/env python3
"""Prepare or run the bounded Issue #38 A-baseline request/response path.

`prepare` is deliberately non-native. It owns the Issue #38 request and receipt
shape, then delegates all disposable-tree copying, splice, closure and freeze
work to `managed_probe_prepare`. `run` remains separately owner-gated while the
Issue #38 HOLD is active.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Final

import issue38_protocol
import managed_probe_prepare


_COMPLETE_MARKER: Final = "complete###true"
_TIMEOUT_SECONDS: Final = 120


class FrontDoorError(ValueError):
    """The A-baseline request/response path could not be prepared or run safely."""


def _bsl_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not issue38_protocol._SAFE_VALUE.fullmatch(value):
        raise FrontDoorError(f"request has unsafe {field}")
    return value


def _request_headers(request: dict[str, object]) -> list[tuple[str, str]]:
    issue38_protocol._identity_rows(request)
    return [(key, _bsl_string(request[key], key)) for key in issue38_protocol._HEADERS]


def _client_probe(request: dict[str, object]) -> bytes:
    rows = "\n".join(
        f'\t\tWriter.WriteLine("{key}###{value}###String");'
        for key, value in _request_headers(request)
    )
    probe = f'''\n\tIf Not IsBlankString(LaunchParameter) Then

\t\tWriter = New TextWriter(LaunchParameter, TextEncoding.UTF8);
{rows}
\t\tWriter.WriteLine("runtimeStarted###true###Boolean");
\t\tWriter.WriteLine("probeEntered###true###Boolean");
\t\tWriter.WriteLine("serverCallIssued###true###Boolean");
\t\tWriter.Close();
\t\tServerToken = JetServerCall.Issue38ServerWitness(
\t\t\tLaunchParameter + ".server",
\t\t\t"{_bsl_string(request['runId'], 'runId')}",
\t\t\t"{_bsl_string(request['caseId'], 'caseId')}",
\t\t\t"{_bsl_string(request['nonce'], 'nonce')}");
\t\tWriter = New TextWriter(LaunchParameter, TextEncoding.UTF8, Chars.LF, True);
\t\tWriter.WriteLine("serverReached###true###Boolean");
\t\tWriter.WriteLine("caseStarted###true###Boolean");
\t\tWriter.WriteLine("businessResult###" + ServerToken + "###String");
\t\tWriter.WriteLine("complete###true###Boolean");
\t\tWriter.Close();
\t\tReturn;
\tEndIf;
'''
    return probe.encode("ascii")


def _server_probe(request: dict[str, object]) -> bytes:
    rows = "\n".join(
        f'\tWriter.WriteLine("{key}###" + {key[0].upper() + key[1:]} + "###String");'
        for key, _ in _request_headers(request)
    )
    rows = rows.replace(
        '\tWriter.WriteLine("protocolVersion###" + ProtocolVersion + "###String");',
        '\tWriter.WriteLine("protocolVersion###issue38-v5###String");',
    ).replace(
        '\tWriter.WriteLine("operation###" + Operation + "###String");',
        '\tWriter.WriteLine("operation###serverWitness###String");',
    )
    probe = f'''\n#Region Issue38FrontDoorProbe
Function Issue38ServerWitness(ServerWitnessPath, RunId, CaseId, Nonce) Export
\tServerToken = String(New UUID);
\tWriter = New TextWriter(ServerWitnessPath, TextEncoding.UTF8);
{rows}
\tWriter.WriteLine("serverReached###true###Boolean");
\tWriter.WriteLine("caseStarted###true###Boolean");
\tWriter.WriteLine("businessResult###" + ServerToken + "###String");
\tWriter.WriteLine("complete###true###Boolean");
\tWriter.Close();
\tReturn ServerToken;
EndFunction
#EndRegion
'''
    return probe.encode("ascii")


def _write_json_new(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FrontDoorError(f"refusing to replace existing request: {path}")
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def prepare(repo_root: Path, source_tree: Path, prepared_tree: Path, request_path: Path) -> dict[str, object]:
    repo_root = repo_root.resolve()
    source_tree = source_tree.resolve()
    prepared_tree = prepared_tree.resolve()
    request_path = request_path.resolve()
    if not source_tree.is_dir():
        raise FrontDoorError(f"input tree is absent: {source_tree}")
    if request_path == source_tree or source_tree in request_path.parents:
        raise FrontDoorError("request must be outside input tree")
    if request_path == prepared_tree or prepared_tree in request_path.parents:
        raise FrontDoorError("request must be outside prepared tree")
    if request_path.exists():
        raise FrontDoorError(f"refusing to replace existing request: {request_path}")

    request = issue38_protocol.new_request()
    _request_headers(request)
    try:
        preparation_audit = managed_probe_prepare.prepare_probe(
            repo_root=repo_root,
            snapshot_root=source_tree,
            prepared_root=prepared_tree,
            client_block=_client_probe(request),
            server_block=_server_probe(request),
        )
        _write_json_new(request_path, request)
    except (OSError, ValueError, RuntimeError) as exc:
        try:
            managed_probe_prepare.discard_prepared_tree(repo_root=repo_root, prepared_root=prepared_tree)
        except (OSError, ValueError):
            pass
        raise FrontDoorError(str(exc)) from exc

    return {
        "status": "prepared",
        "requestPath": str(request_path),
        "requestSha256": hashlib.sha256(request_path.read_bytes()).hexdigest(),
        "preparedTree": str(prepared_tree),
        "changedFiles": preparation_audit["changedPaths"],
        "preparationAudit": preparation_audit,
        "completeMarker": _COMPLETE_MARKER,
        "timeoutSeconds": _TIMEOUT_SECONDS,
    }


def _native_command(repo_root: Path, prepared_tree: Path) -> list[str]:
    return [
        sys.executable,
        str(repo_root / "scripts/native_cycle.py"),
        "run-prepared",
        "--repo-root", str(repo_root),
        "--input-tree", str(prepared_tree),
        "--complete-marker", _COMPLETE_MARKER,
        "--timeout-seconds", str(_TIMEOUT_SECONDS),
    ]


def run(repo_root: Path, source_tree: Path, prepared_tree: Path, request_path: Path) -> dict[str, object]:
    prepared = prepare(repo_root, source_tree, prepared_tree, request_path)
    completed = subprocess.run(
        _native_command(repo_root, prepared_tree), text=True, capture_output=True, timeout=_TIMEOUT_SECONDS + 90,
    )
    try:
        runner_result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise FrontDoorError("native cycle did not return one JSON result") from exc
    if completed.returncode != 0:
        return {"status": "runnerFailure", "prepared": prepared, "runner": runner_result}
    invocation = runner_result.get("preparedInvocation", {}).get("invocationRoot")
    if not isinstance(invocation, str):
        raise FrontDoorError("native result omitted prepared invocation root")
    receipt = repo_root / invocation / "run/evidence/receipt.txt"
    server = receipt.with_name(receipt.name + ".server")
    request = json.loads(request_path.read_text(encoding="utf-8"))
    response = issue38_protocol.validate_terminal(request, receipt.read_bytes(), server.read_bytes())
    return {"status": "validated", "prepared": prepared, "runner": runner_result, "response": response}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run"))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--input-tree", required=True, type=Path)
    parser.add_argument("--prepared-tree", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args.repo_root, args.input_tree, args.prepared_tree, args.request)
        else:
            result = run(args.repo_root.resolve(), args.input_tree, args.prepared_tree, args.request)
    except (OSError, json.JSONDecodeError, FrontDoorError, issue38_protocol.ProtocolError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
