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


_COMPLETE_MARKER: Final = "complete###true###Boolean"
_TIMEOUT_SECONDS: Final = 120


class FrontDoorError(ValueError):
    """The A-baseline request/response path could not be prepared or run safely."""


def _lexical_absolute(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


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
    source_tree = _lexical_absolute(repo_root, source_tree)
    prepared_tree = _lexical_absolute(repo_root, prepared_tree)
    request_path = _lexical_absolute(repo_root, request_path).resolve()
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
    preparation_audit: dict[str, object] | None = None
    try:
        preparation_audit = managed_probe_prepare.prepare_probe(
            repo_root=repo_root,
            snapshot_root=source_tree,
            prepared_root=prepared_tree,
            client_block=_client_probe(request),
            server_block=_server_probe(request),
        )
        _write_json_new(request_path, request)
    except BaseException as exc:
        if preparation_audit is not None:
            try:
                managed_probe_prepare.discard_prepared_tree(repo_root=repo_root, prepared_root=prepared_tree)
            except BaseException as cleanup_exc:
                raise FrontDoorError(
                    f"preparation failed: {type(exc).__name__}: {exc}; "
                    f"prepared cleanup failed: {type(cleanup_exc).__name__}: {cleanup_exc}"
                ) from cleanup_exc
        if isinstance(exc, (OSError, ValueError, RuntimeError)):
            raise FrontDoorError(str(exc)) from exc
        raise

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
        "--input-tree", prepared_tree.relative_to(repo_root).as_posix(),
        "--complete-marker", _COMPLETE_MARKER,
        "--timeout-seconds", str(_TIMEOUT_SECONDS),
    ]


def _regular_child(root: Path, relative: Path, *, field: str) -> Path:
    candidate = root
    for part in relative.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise FrontDoorError(f"{field} contains a symlink: {candidate}")
    if not candidate.is_file():
        raise FrontDoorError(f"{field} must be a regular file: {candidate}")
    return candidate


def _runner_invocation_root(repo_root: Path, runner_result: object) -> Path:
    if not isinstance(runner_result, dict):
        raise FrontDoorError("native cycle result must be a JSON object")
    prepared_invocation = runner_result.get("preparedInvocation")
    if not isinstance(prepared_invocation, dict):
        raise FrontDoorError("native result omitted preparedInvocation object")
    invocation_value = prepared_invocation.get("invocationRoot")
    if not isinstance(invocation_value, str):
        raise FrontDoorError("native result omitted prepared invocationRoot")
    relative = Path(invocation_value)
    expected_parent = Path(".local/runs/native-cycle")
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or len(relative.parts) != 4
        or relative.parts[:3] != expected_parent.parts
        or not relative.name.startswith("run-")
    ):
        raise FrontDoorError("native result has unsafe invocationRoot")
    invocation_root = repo_root / relative
    if invocation_root.is_symlink() or not invocation_root.is_dir():
        raise FrontDoorError("native invocationRoot must be a non-symlink directory")
    candidate = repo_root
    for part in relative.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise FrontDoorError(f"native invocationRoot contains a symlink: {candidate}")
    return invocation_root


def _runner_receipts(repo_root: Path, runner_result: object) -> tuple[Path, Path]:
    invocation_root = _runner_invocation_root(repo_root, runner_result)
    receipt = _regular_child(invocation_root, Path("run/evidence/receipt.txt"), field="client receipt")
    server = _regular_child(invocation_root, Path("run/evidence/receipt.txt.server"), field="server receipt")
    return receipt, server


def _discard_after_run(repo_root: Path, prepared_tree: Path, terminal_error: BaseException | None) -> None:
    try:
        managed_probe_prepare.discard_prepared_tree(repo_root=repo_root, prepared_root=prepared_tree)
    except (OSError, ValueError) as cleanup_exc:
        if terminal_error is None:
            raise FrontDoorError(f"prepared cleanup failed: {cleanup_exc}") from cleanup_exc
        raise FrontDoorError(f"run failed: {terminal_error}; prepared cleanup failed: {cleanup_exc}") from cleanup_exc


def run(repo_root: Path, source_tree: Path, prepared_tree: Path, request_path: Path) -> dict[str, object]:
    repo_root = repo_root.resolve()
    prepared_tree = _lexical_absolute(repo_root, prepared_tree)
    prepared = prepare(repo_root, source_tree, prepared_tree, request_path)
    terminal_error: BaseException | None = None
    try:
        try:
            completed = subprocess.run(
                _native_command(repo_root, prepared_tree), text=True, capture_output=True, timeout=_TIMEOUT_SECONDS + 90,
            )
        except subprocess.TimeoutExpired as exc:
            raise FrontDoorError("native cycle timed out") from exc
        try:
            runner_result = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise FrontDoorError("native cycle did not return one JSON result") from exc
        if not isinstance(runner_result, dict):
            raise FrontDoorError("native cycle result must be a JSON object")
        if completed.returncode != 0:
            _runner_invocation_root(repo_root, runner_result)
            result: dict[str, object] = {"status": "runnerFailure", "prepared": prepared, "runner": runner_result}
        else:
            receipt, server = _runner_receipts(repo_root, runner_result)
            request = json.loads(request_path.read_text(encoding="utf-8"))
            response = issue38_protocol.validate_terminal(request, receipt.read_bytes(), server.read_bytes())
            result = {"status": "validated", "prepared": prepared, "runner": runner_result, "response": response}
    except BaseException as exc:
        terminal_error = exc
        raise
    finally:
        _discard_after_run(repo_root, prepared_tree, terminal_error)
    result["cleanup"] = "discarded"
    return result


def discard(repo_root: Path, prepared_tree: Path) -> dict[str, object]:
    repo_root = repo_root.resolve()
    prepared_tree = _lexical_absolute(repo_root, prepared_tree)
    try:
        managed_probe_prepare.discard_prepared_tree(repo_root=repo_root, prepared_root=prepared_tree)
    except (OSError, ValueError) as exc:
        raise FrontDoorError(f"prepared cleanup failed: {exc}") from exc
    return {"status": "discarded", "preparedTree": str(prepared_tree)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run", "discard"))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--input-tree", type=Path)
    parser.add_argument("--prepared-tree", required=True, type=Path)
    parser.add_argument("--request", type=Path)
    args = parser.parse_args(argv)
    if args.command in ("prepare", "run") and (args.input_tree is None or args.request is None):
        parser.error("--input-tree and --request are required for prepare and run")
    try:
        if args.command == "prepare":
            result = prepare(args.repo_root, args.input_tree, args.prepared_tree, args.request)
        elif args.command == "run":
            result = run(args.repo_root.resolve(), args.input_tree, args.prepared_tree, args.request)
        else:
            result = discard(args.repo_root, args.prepared_tree)
    except (OSError, json.JSONDecodeError, FrontDoorError, issue38_protocol.ProtocolError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
