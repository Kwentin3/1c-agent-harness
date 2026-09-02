#!/usr/bin/env python3
"""Shared task-owned patch → native runner → oracle → receipt boundary.

The caller supplies an opaque request, ordered exact patch files, one task oracle,
and the runner completion marker. This module owns orchestration and generic
provenance only; it never interprets task business fields.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Callable

import managed_probe_prepare
import native_cycle


class SharedRouteError(ValueError):
    """The generic route could not complete its fail-closed contract."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_copy(value: object) -> object:
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return _sha256(payload.encode("utf-8"))


def _require_sha256(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise SharedRouteError(f"{field} must be a lowercase SHA-256")
    return value


def _require_tree_identity(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != {
        "files", "directories", "bytes", "sha256",
    }:
        raise SharedRouteError(f"{field} must be one complete tree identity")
    if any(
        type(value[key]) is not int or value[key] < 0
        for key in ("files", "directories", "bytes")
    ):
        raise SharedRouteError(f"{field} counters must be non-negative integers")
    _require_sha256(value["sha256"], f"{field}.sha256")
    return value


def _raw_receipt(payload: bytes) -> dict[str, object]:
    if not isinstance(payload, bytes) or not payload:
        raise SharedRouteError("raw receipt must be non-empty bytes")
    return {
        "bytes": len(payload),
        "sha256": _sha256(payload),
        "base64": base64.b64encode(payload).decode("ascii"),
    }


def build_provenance_receipt(
    *,
    preparation: dict[str, object],
    request: dict[str, object],
    runner: dict[str, object],
    client_receipt: bytes,
    server_receipt: bytes,
    business_payload: object,
    oracle: dict[str, object],
    prepared_cleanup: str,
) -> dict[str, object]:
    """Issue one generic receipt after a task oracle accepts opaque bytes."""
    prepared = _require_tree_identity(
        preparation.get("runnerInput"), "preparation.runnerInput",
    )
    invocation = runner.get("preparedInvocation")
    if not isinstance(invocation, dict):
        raise SharedRouteError("runner omitted preparedInvocation")
    frozen = invocation.get("frozenInput")
    input_chain = {
        "prepared": _json_copy(prepared),
        "sourceBefore": _json_copy(invocation.get("sourceBefore")),
        "sourceAfter": _json_copy(invocation.get("sourceAfter")),
        "copiedBeforeFreeze": _json_copy(invocation.get("copiedBeforeFreeze")),
        "frozen": _json_copy(frozen.get("identity")) if isinstance(frozen, dict) else None,
        "inputAfter": _json_copy(runner.get("inputAfter")),
    }
    if any(
        _require_tree_identity(value, f"input.{key}") != prepared
        for key, value in input_chain.items()
    ):
        raise SharedRouteError("prepared/frozen runner input identity mismatch")

    runtime = runner.get("runtime")
    cleanup = runner.get("storageCompaction")
    if runner.get("status") != "runtime_contract_completed" or not isinstance(runtime, dict):
        raise SharedRouteError("runner did not complete the runtime contract")
    if not isinstance(cleanup, dict):
        raise SharedRouteError("runner omitted cleanup result")

    client = _raw_receipt(client_receipt)
    server = _raw_receipt(server_receipt)
    request_sha = _canonical_sha256(request)
    payload_sha = _canonical_sha256(business_payload)
    oracle_binding = dict(oracle)
    oracle_binding.update({
        "requestSha256": request_sha,
        "businessPayloadSha256": payload_sha,
        "serverReceiptSha256": server["sha256"],
    })
    receipt = {
        "schemaVersion": 1,
        "canonicalBase": _json_copy(preparation.get("canonicalBase")),
        "patches": _json_copy(preparation.get("patches")),
        "changedPaths": sorted(preparation.get("changedPaths", [])),
        "input": input_chain,
        "request": {"payload": _json_copy(request), "sha256": request_sha},
        "runtime": {
            "status": runner.get("status"),
            "completed": runtime.get("completed"),
            "clientReceipt": client,
        },
        "cleanup": {
            "runner": _json_copy(cleanup),
            "preparedTree": prepared_cleanup,
        },
        "business": {
            "rawReceipt": server,
            "payload": _json_copy(business_payload),
            "payloadSha256": payload_sha,
        },
        "oracle": oracle_binding,
    }
    validate_provenance_receipt(receipt)
    return receipt


def validate_provenance_receipt(receipt: dict[str, object]) -> dict[str, object]:
    expected = {
        "schemaVersion", "canonicalBase", "patches", "changedPaths", "input",
        "request", "runtime", "cleanup", "business", "oracle",
    }
    if not isinstance(receipt, dict) or set(receipt) != expected:
        raise SharedRouteError("provenance receipt schema mismatch")
    if receipt.get("schemaVersion") != 1:
        raise SharedRouteError("provenance receipt schema mismatch")

    canonical = receipt["canonicalBase"]
    if (
        not isinstance(canonical, dict)
        or set(canonical) != {"files", "sha256"}
        or type(canonical["files"]) is not int
        or canonical["files"] <= 0
    ):
        raise SharedRouteError("canonical base identity mismatch")
    _require_sha256(canonical["sha256"], "canonicalBase.sha256")

    patches = receipt["patches"]
    if not isinstance(patches, list) or not patches:
        raise SharedRouteError("patch set is empty")
    roles: set[str] = set()
    for patch in patches:
        if (
            not isinstance(patch, dict)
            or set(patch) != {"role", "sha256"}
            or not isinstance(patch["role"], str)
            or not patch["role"]
            or patch["role"] in roles
        ):
            raise SharedRouteError("patch binding mismatch")
        roles.add(patch["role"])
        _require_sha256(patch["sha256"], "patch.sha256")

    changed = receipt["changedPaths"]
    if (
        not isinstance(changed, list)
        or not changed
        or changed != sorted(set(changed))
        or not all(
            isinstance(path, str)
            and path
            and not Path(path).is_absolute()
            and ".." not in Path(path).parts
            for path in changed
        )
    ):
        raise SharedRouteError("changed-path closure mismatch")

    input_chain = receipt["input"]
    if not isinstance(input_chain, dict) or set(input_chain) != {
        "prepared", "sourceBefore", "sourceAfter", "copiedBeforeFreeze",
        "frozen", "inputAfter",
    }:
        raise SharedRouteError("input chain mismatch")
    prepared = _require_tree_identity(input_chain["prepared"], "input.prepared")
    if any(
        _require_tree_identity(value, f"input.{key}") != prepared
        for key, value in input_chain.items()
    ):
        raise SharedRouteError("prepared/frozen input mismatch")

    request = receipt["request"]
    if (
        not isinstance(request, dict)
        or set(request) != {"payload", "sha256"}
        or request["sha256"] != _canonical_sha256(request["payload"])
    ):
        raise SharedRouteError("request binding mismatch")

    runtime = receipt["runtime"]
    if (
        not isinstance(runtime, dict)
        or set(runtime) != {"status", "completed", "clientReceipt"}
        or runtime["status"] != "runtime_contract_completed"
        or runtime["completed"] is not True
    ):
        raise SharedRouteError("runtime is incomplete")

    cleanup = receipt["cleanup"]
    if (
        not isinstance(cleanup, dict)
        or set(cleanup) != {"runner", "preparedTree"}
        or cleanup.get("preparedTree") != "discarded"
    ):
        raise SharedRouteError("prepared cleanup is incomplete")
    runner_cleanup = cleanup["runner"]
    if (
        not isinstance(runner_cleanup, dict)
        or runner_cleanup.get("status") != "completed"
        or runner_cleanup.get("manualCleanupActions") != 0
    ):
        raise SharedRouteError("runner cleanup is incomplete")

    business = receipt["business"]
    if (
        not isinstance(business, dict)
        or set(business) != {"rawReceipt", "payload", "payloadSha256"}
        or business["payloadSha256"] != _canonical_sha256(business["payload"])
    ):
        raise SharedRouteError("business payload binding mismatch")
    for label, raw in (
        ("client", runtime["clientReceipt"]),
        ("server", business["rawReceipt"]),
    ):
        if not isinstance(raw, dict) or set(raw) != {"bytes", "sha256", "base64"}:
            raise SharedRouteError(f"{label} receipt binding mismatch")
        decoded = base64.b64decode(raw["base64"], validate=True)
        if raw["bytes"] != len(decoded) or raw["sha256"] != _sha256(decoded):
            raise SharedRouteError(f"{label} receipt byte/hash mismatch")

    oracle = receipt["oracle"]
    bindings = {
        "requestSha256": request["sha256"],
        "businessPayloadSha256": business["payloadSha256"],
        "serverReceiptSha256": business["rawReceipt"]["sha256"],
    }
    if (
        not isinstance(oracle, dict)
        or oracle.get("status") != "PASS"
        or any(oracle.get(key) != value for key, value in bindings.items())
    ):
        raise SharedRouteError("task oracle binding mismatch")
    return {"status": "PASS", "schemaVersion": 1}


def _repository_child(repo_root: Path, value: Path, field: str) -> Path:
    candidate = value if value.is_absolute() else repo_root / value
    try:
        relative = candidate.relative_to(repo_root)
    except ValueError as exc:
        raise SharedRouteError(f"{field} must be inside repository") from exc
    if not relative.parts or ".." in relative.parts:
        raise SharedRouteError(f"{field} must be a repository descendant")
    current = repo_root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise SharedRouteError(f"{field} contains a symlink: {current}")
    return candidate


def _regular_file(repo_root: Path, value: Path, field: str) -> Path:
    candidate = _repository_child(repo_root, value, field)
    if not candidate.is_file():
        raise SharedRouteError(f"{field} must be a regular file")
    return candidate


def _write_json_new(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise SharedRouteError(f"refusing to replace existing output: {path}")
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _runner_command(
    repo_root: Path,
    prepared_tree: Path,
    complete_marker: str,
    timeout_seconds: int,
) -> list[str]:
    return [
        sys.executable,
        str(repo_root / "scripts/native_cycle.py"),
        "run-prepared",
        "--repo-root", str(repo_root),
        "--input-tree", prepared_tree.relative_to(repo_root).as_posix(),
        "--complete-marker", complete_marker,
        "--timeout-seconds", str(timeout_seconds),
    ]


def _runner_receipts(repo_root: Path, runner: object) -> tuple[Path, Path]:
    if not isinstance(runner, dict):
        raise SharedRouteError("native result must be a JSON object")
    invocation = runner.get("preparedInvocation")
    root_value = invocation.get("invocationRoot") if isinstance(invocation, dict) else None
    if not isinstance(root_value, str):
        raise SharedRouteError("native result omitted invocationRoot")
    relative = Path(root_value)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or len(relative.parts) != 4
        or relative.parts[:3] != (".local", "runs", "native-cycle")
        or not relative.name.startswith("run-")
    ):
        raise SharedRouteError("native result has unsafe invocationRoot")
    invocation_root = _repository_child(repo_root, relative, "invocationRoot")
    if not invocation_root.is_dir():
        raise SharedRouteError("native invocationRoot must be a directory")
    client = _regular_file(
        repo_root, relative / "run/evidence/receipt.txt", "client receipt",
    )
    server = _regular_file(
        repo_root, relative / "run/evidence/receipt.txt.server", "server receipt",
    )
    return client, server


def _run_oracle(
    oracle_path: Path,
    request_path: Path,
    client_path: Path,
    server_path: Path,
    run_command: Callable[..., subprocess.CompletedProcess[str]],
) -> tuple[dict[str, object], object]:
    completed = run_command(
        [
            sys.executable,
            str(oracle_path),
            "--request", str(request_path),
            "--client-receipt", str(client_path),
            "--server-receipt", str(server_path),
        ],
        text=True,
        capture_output=True,
        timeout=60,
    )
    if completed.returncode != 0:
        raise SharedRouteError(f"task oracle failed: {completed.stderr.strip()}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SharedRouteError("task oracle did not return one JSON object") from exc
    if not isinstance(result, dict) or result.get("status") != "PASS":
        raise SharedRouteError("task oracle did not return PASS")
    if "businessPayload" not in result:
        raise SharedRouteError("task oracle omitted businessPayload")
    binding = {key: value for key, value in result.items() if key != "businessPayload"}
    return binding, result["businessPayload"]


def run_task(
    *,
    repo_root: Path,
    input_tree: Path,
    prepared_tree: Path,
    request_path: Path,
    patch_paths: list[tuple[str, Path]],
    complete_marker: str,
    oracle_path: Path,
    receipt_path: Path,
    timeout_seconds: int,
    run_command: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    """Run the complete shared route for one opaque task contract."""
    repo_root = repo_root.resolve()
    input_tree = _repository_child(repo_root, input_tree, "inputTree")
    prepared_tree = _repository_child(repo_root, prepared_tree, "preparedTree")
    request_path = _regular_file(repo_root, request_path, "request")
    oracle_path = _regular_file(repo_root, oracle_path, "oracle")
    receipt_path = _repository_child(repo_root, receipt_path, "receipt")
    if receipt_path.exists() or receipt_path.is_symlink():
        raise SharedRouteError("receipt output already exists")
    if not complete_marker or "\n" in complete_marker or "\r" in complete_marker:
        raise SharedRouteError("completeMarker must be one non-empty line")
    if timeout_seconds <= 0:
        raise SharedRouteError("timeoutSeconds must be positive")

    request = json.loads(request_path.read_text(encoding="utf-8"))
    if not isinstance(request, dict):
        raise SharedRouteError("request must be a JSON object")
    patches = [
        (role, _regular_file(repo_root, path, f"{role} patch").read_bytes())
        for role, path in patch_paths
    ]
    preparation: dict[str, object] | None = None
    terminal_error: BaseException | None = None
    context: tuple[dict[str, object], bytes, bytes, object, dict[str, object]] | None = None
    try:
        preparation = managed_probe_prepare.prepare_patched_tree(
            repo_root=repo_root,
            snapshot_root=input_tree,
            prepared_root=prepared_tree,
            patches=patches,
        )
        preparation["runnerInput"] = native_cycle.tree_identity(prepared_tree)
        expected_tree = prepared_tree.relative_to(repo_root).as_posix()
        if request.get("preparedTree") != expected_tree:
            raise SharedRouteError("request preparedTree does not match shared route")
        if request.get("changedPaths") != preparation["changedPaths"]:
            raise SharedRouteError("request changedPaths do not match exact patches")
        if request.get("treeIdentity") != preparation["runnerInput"]["sha256"]:
            raise SharedRouteError("request treeIdentity does not match prepared input")

        completed = run_command(
            _runner_command(repo_root, prepared_tree, complete_marker, timeout_seconds),
            text=True,
            capture_output=True,
            timeout=timeout_seconds + 90,
        )
        try:
            runner = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise SharedRouteError("native cycle did not return one JSON object") from exc
        if completed.returncode != 0:
            raise SharedRouteError("native cycle failed")
        client_path, server_path = _runner_receipts(repo_root, runner)
        client_bytes = client_path.read_bytes()
        server_bytes = server_path.read_bytes()
        oracle_binding, business_payload = _run_oracle(
            oracle_path,
            request_path,
            client_path,
            server_path,
            run_command,
        )
        context = (
            runner, client_bytes, server_bytes, business_payload, oracle_binding,
        )
    except BaseException as exc:
        terminal_error = exc
        raise
    finally:
        if preparation is not None:
            try:
                managed_probe_prepare.discard_prepared_tree(
                    repo_root=repo_root,
                    prepared_root=prepared_tree,
                )
            except BaseException as cleanup_exc:
                if terminal_error is None:
                    raise SharedRouteError(
                        f"prepared cleanup failed: {cleanup_exc}",
                    ) from cleanup_exc
                raise SharedRouteError(
                    f"route failed: {terminal_error}; prepared cleanup failed: {cleanup_exc}",
                ) from cleanup_exc

    if context is None or preparation is None:
        raise SharedRouteError("shared route completed without validated context")
    runner, client_bytes, server_bytes, business_payload, oracle_binding = context
    receipt = build_provenance_receipt(
        preparation=preparation,
        request=request,
        runner=runner,
        client_receipt=client_bytes,
        server_receipt=server_bytes,
        business_payload=business_payload,
        oracle=oracle_binding,
        prepared_cleanup="discarded",
    )
    _write_json_new(receipt_path, receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run",))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--input-tree", type=Path, required=True)
    parser.add_argument("--prepared-tree", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--production-patch", type=Path, required=True)
    parser.add_argument("--instrumentation-patch", type=Path, required=True)
    parser.add_argument("--complete-marker", required=True)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=300)
    args = parser.parse_args(argv)
    try:
        receipt = run_task(
            repo_root=args.repo_root,
            input_tree=args.input_tree,
            prepared_tree=args.prepared_tree,
            request_path=args.request,
            patch_paths=[
                ("production", args.production_patch),
                ("instrumentation", args.instrumentation_patch),
            ],
            complete_marker=args.complete_marker,
            oracle_path=args.oracle,
            receipt_path=args.receipt,
            timeout_seconds=args.timeout_seconds,
        )
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
