#!/usr/bin/env python3
"""Prepare or run the bounded Issue #38 A-baseline request/response path.

`prepare` is deliberately non-native: it creates one fresh request outside the
prepared configuration copy and writes only the two declared probe closures into
that copy. `run` performs the existing `native_cycle.py run-prepared` lifecycle
and validates its bound receipts. It is intentionally not invoked by tests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
from typing import Final

import issue38_protocol


_CLIENT_MODULE: Final = Path("Ext/ManagedApplicationModule.bsl")
_SERVER_MODULE: Final = Path("CommonModules/JetServerCall/Ext/Module.bsl")
_ALLOWED_CHANGED: Final = frozenset((_CLIENT_MODULE, _SERVER_MODULE))
_COMPLETE_MARKER: Final = "complete###true"
_TIMEOUT_SECONDS: Final = 120


class FrontDoorError(ValueError):
    """The A-baseline source closure could not be prepared or run safely."""


def _bsl_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not issue38_protocol._SAFE_VALUE.fullmatch(value):
        raise FrontDoorError(f"request has unsafe {field}")
    return value


def _request_headers(request: dict[str, object]) -> list[tuple[str, str]]:
    issue38_protocol._identity_rows(request)
    return [(key, _bsl_string(request[key], key)) for key in issue38_protocol._HEADERS]


def _client_probe(request: dict[str, object]) -> str:
    rows = "\n".join(
        f'		Writer.WriteLine("{key}###{value}###String");'
        for key, value in _request_headers(request)
    )
    return f'''\n	If Not IsBlankString(LaunchParameter) Then
		Writer = New TextWriter(LaunchParameter, TextEncoding.UTF8);
{rows}
		Writer.WriteLine("runtimeStarted###true###Boolean");
		Writer.WriteLine("probeEntered###true###Boolean");
		Writer.WriteLine("serverCallIssued###true###Boolean");
		Writer.Close();
		ServerToken = JetServerCall.Issue38ServerWitness(
			LaunchParameter + ".server",
			"{_bsl_string(request['runId'], 'runId')}",
			"{_bsl_string(request['caseId'], 'caseId')}",
			"{_bsl_string(request['nonce'], 'nonce')}");
		Writer = New TextWriter(LaunchParameter, TextEncoding.UTF8, Chars.LF, True);
		Writer.WriteLine("serverReached###true###Boolean");
		Writer.WriteLine("caseStarted###true###Boolean");
		Writer.WriteLine("businessResult###" + ServerToken + "###String");
		Writer.WriteLine("complete###true###Boolean");
		Writer.Close();
		Return;
	EndIf;
'''


def _server_probe(request: dict[str, object]) -> str:
    rows = "\n".join(
        f'\tWriter.WriteLine("{key}###" + {key[0].upper() + key[1:]} + "###String");'
        for key, _ in _request_headers(request)
    )
    # protocolVersion and operation are fixed BSL literals; identity values are supplied by client.
    rows = rows.replace(
        '\tWriter.WriteLine("protocolVersion###" + ProtocolVersion + "###String");',
        '\tWriter.WriteLine("protocolVersion###issue38-v5###String");',
    ).replace(
        '\tWriter.WriteLine("operation###" + Operation + "###String");',
        '\tWriter.WriteLine("operation###serverWitness###String");',
    )
    return f'''\n#Region Issue38FrontDoorProbe
Function Issue38ServerWitness(ServerWitnessPath, RunId, CaseId, Nonce) Export
	ServerToken = String(New UUID);
	Writer = New TextWriter(ServerWitnessPath, TextEncoding.UTF8);
{rows}
	Writer.WriteLine("serverReached###true###Boolean");
	Writer.WriteLine("caseStarted###true###Boolean");
	Writer.WriteLine("businessResult###" + ServerToken + "###String");
	Writer.WriteLine("complete###true###Boolean");
	Writer.Close();
	Return ServerToken;
EndFunction
#EndRegion
'''


def _insert_on_start_probe(source: str, probe: str) -> str:
    anchor = "Procedure OnStart()"
    start = source.find(anchor)
    if start < 0:
        raise FrontDoorError("managed application OnStart anchor is absent")
    end = source.find("EndProcedure", start)
    if end < 0:
        raise FrontDoorError("managed application OnStart end anchor is absent")
    original = source[start:end]
    if "// StandardSubsystems" not in original:
        raise FrontDoorError("managed application OnStart has unexpected shape")
    insertion = start + len(anchor)
    return source[:insertion] + probe + source[insertion:]


def _changed_files(source_tree: Path, prepared_tree: Path) -> set[Path]:
    changed: set[Path] = set()
    for path in prepared_tree.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(prepared_tree)
        source = source_tree / relative
        if not source.is_file() or path.read_bytes() != source.read_bytes():
            changed.add(relative)
    return changed


def _write_json_new(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FrontDoorError(f"refusing to replace existing request: {path}")
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def prepare(source_tree: Path, prepared_tree: Path, request_path: Path) -> dict[str, object]:
    source_tree = source_tree.resolve()
    prepared_tree = prepared_tree.resolve()
    request_path = request_path.resolve()
    if not source_tree.is_dir():
        raise FrontDoorError(f"input tree is absent: {source_tree}")
    if prepared_tree.exists():
        raise FrontDoorError(f"prepared tree already exists: {prepared_tree}")
    if prepared_tree == source_tree or source_tree in prepared_tree.parents:
        raise FrontDoorError("prepared tree must be outside input tree")
    if request_path == source_tree or source_tree in request_path.parents:
        raise FrontDoorError("request must be outside input tree")
    if request_path == prepared_tree or prepared_tree in request_path.parents:
        raise FrontDoorError("request must be outside prepared tree")

    request = issue38_protocol.new_request()
    _request_headers(request)
    try:
        shutil.copytree(source_tree, prepared_tree)
        client_path = prepared_tree / _CLIENT_MODULE
        server_path = prepared_tree / _SERVER_MODULE
        for path in (client_path, server_path):
            if not path.is_file():
                raise FrontDoorError(f"required module is absent: {path.relative_to(prepared_tree)}")
            os.chmod(path, path.stat().st_mode | stat.S_IWUSR)
        client_path.write_text(
            _insert_on_start_probe(client_path.read_text(encoding="utf-8-sig"), _client_probe(request)),
            encoding="utf-8",
        )
        server_path.write_text(
            server_path.read_text(encoding="utf-8-sig") + _server_probe(request), encoding="utf-8",
        )
        changed = _changed_files(source_tree, prepared_tree)
        if changed != _ALLOWED_CHANGED:
            raise FrontDoorError(f"prepared tree changed outside closure: {sorted(map(str, changed))}")
        for path in (client_path, server_path):
            text = path.read_text(encoding="utf-8")
            if "BankReceipt" in text or "Issue36" in text:
                raise FrontDoorError("generated closure mentions forbidden business scope")
        _write_json_new(request_path, request)
    except Exception:
        if prepared_tree.exists():
            shutil.rmtree(prepared_tree)
        raise

    return {
        "status": "prepared",
        "requestPath": str(request_path),
        "requestSha256": hashlib.sha256(request_path.read_bytes()).hexdigest(),
        "preparedTree": str(prepared_tree),
        "changedFiles": sorted(map(str, changed)),
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
    prepared = prepare(source_tree, prepared_tree, request_path)
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
            result = prepare(args.input_tree, args.prepared_tree, args.request)
        else:
            result = run(args.repo_root.resolve(), args.input_tree, args.prepared_tree, args.request)
    except (OSError, json.JSONDecodeError, FrontDoorError, issue38_protocol.ProtocolError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
