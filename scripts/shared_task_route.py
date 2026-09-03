#!/usr/bin/env python3
"""One task request + exact patches + 1C + oracle -> receipt + cleanup."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Callable
import uuid

import managed_probe_prepare
import native_cycle


class SharedRouteError(ValueError):
    pass


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_sha(value: object) -> str:
    return _sha(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8"))


def _inside(repo: Path, value: Path, field: str) -> Path:
    candidate = value if value.is_absolute() else repo / value
    try:
        relative = candidate.relative_to(repo)
    except ValueError as exc:
        raise SharedRouteError(f"{field} must be inside repository") from exc
    if not relative.parts or ".." in relative.parts:
        raise SharedRouteError(f"{field} must be a repository descendant")
    current = repo
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise SharedRouteError(f"{field} contains a symlink")
    return candidate


def _file(repo: Path, value: Path, field: str) -> Path:
    candidate = _inside(repo, value, field)
    if not candidate.is_file():
        raise SharedRouteError(f"{field} must be a regular file")
    return candidate


def _raw(payload: bytes) -> dict[str, object]:
    if not payload:
        raise SharedRouteError("1C receipt is empty")
    return {
        "bytes": len(payload),
        "sha256": _sha(payload),
        "base64": base64.b64encode(payload).decode("ascii"),
    }


def _runner_command(repo: Path, prepared: Path, timeout: int) -> list[str]:
    return [
        sys.executable, str(repo / "scripts/native_cycle.py"), "run-prepared",
        "--repo-root", str(repo),
        "--input-tree", prepared.relative_to(repo).as_posix(),
        "--timeout-seconds", str(timeout),
    ]


def _runner_receipts(repo: Path, runner: dict[str, object]) -> tuple[Path, Path]:
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
    root = _inside(repo, relative, "invocationRoot")
    if not root.is_dir():
        raise SharedRouteError("native invocationRoot is absent")
    return (
        _file(repo, relative / "run/evidence/receipt.txt", "client receipt"),
        _file(repo, relative / "run/evidence/receipt.txt.server", "server receipt"),
    )


def _oracle(
    oracle: Path,
    request: Path,
    client: Path,
    server: Path,
    execute: Callable[..., subprocess.CompletedProcess[str]],
) -> tuple[dict[str, object], object]:
    completed = execute(
        [
            sys.executable, str(oracle),
            "--request", str(request),
            "--client-receipt", str(client),
            "--server-receipt", str(server),
        ],
        text=True, capture_output=True, timeout=60,
    )
    if completed.returncode != 0:
        raise SharedRouteError(f"task oracle failed: {completed.stderr.strip()}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SharedRouteError("task oracle returned invalid JSON") from exc
    if not isinstance(result, dict) or result.get("status") != "PASS":
        raise SharedRouteError("task oracle did not return PASS")
    if "businessPayload" not in result:
        raise SharedRouteError("task oracle omitted businessPayload")
    return ({key: value for key, value in result.items() if key != "businessPayload"}, result["businessPayload"])


def _runner_input(runner: dict[str, object], prepared: dict[str, object]) -> dict[str, object]:
    invocation = runner.get("preparedInvocation")
    frozen = invocation.get("frozenInput") if isinstance(invocation, dict) else None
    values = [
        invocation.get("sourceBefore") if isinstance(invocation, dict) else None,
        invocation.get("sourceAfter") if isinstance(invocation, dict) else None,
        invocation.get("copiedBeforeFreeze") if isinstance(invocation, dict) else None,
        frozen.get("identity") if isinstance(frozen, dict) else None,
        runner.get("inputAfter"),
    ]
    if any(value != prepared for value in values):
        raise SharedRouteError("prepared/frozen runner input mismatch")
    return prepared


def validate_receipt(receipt: dict[str, object]) -> None:
    if set(receipt) != {"version", "canonical", "patches", "input", "request", "result", "cleanup"}:
        raise SharedRouteError("receipt is partial or foreign")
    if receipt["version"] != 1:
        raise SharedRouteError("unknown receipt version")
    patches = receipt["patches"]
    if not isinstance(patches, list) or len(patches) != 2:
        raise SharedRouteError("exact patch binding is incomplete")
    identities = receipt["input"]
    if (
        not isinstance(identities, dict)
        or set(identities) != {"prepared", "runner", "frozen"}
        or identities["prepared"] != identities["runner"]
        or identities["prepared"] != identities["frozen"]
    ):
        raise SharedRouteError("prepared/frozen input mismatch")
    request = receipt["request"]
    if not isinstance(request, dict) or request.get("sha256") != _json_sha(request.get("payload")):
        raise SharedRouteError("request binding mismatch")
    result = receipt["result"]
    if not isinstance(result, dict) or result.get("oracle", {}).get("status") != "PASS":
        raise SharedRouteError("oracle result is incomplete")
    for label in ("client", "server"):
        raw = result.get(label)
        if not isinstance(raw, dict):
            raise SharedRouteError(f"{label} receipt is absent")
        decoded = base64.b64decode(raw.get("base64", ""), validate=True)
        if raw.get("bytes") != len(decoded) or raw.get("sha256") != _sha(decoded):
            raise SharedRouteError(f"{label} receipt binding mismatch")
    cleanup = receipt["cleanup"]
    if (
        not isinstance(cleanup, dict)
        or cleanup.get("prepared") != "discarded"
        or cleanup.get("runner", {}).get("status") != "completed"
        or cleanup.get("runner", {}).get("manualCleanupActions") != 0
    ):
        raise SharedRouteError("cleanup is incomplete")


def run_task(
    *,
    repo_root: Path,
    input_tree: Path,
    request_path: Path,
    patch_paths: list[tuple[str, Path]],
    oracle_path: Path,
    receipt_path: Path,
    timeout_seconds: int,
    execute: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    """Own preparation, native execution, oracle, receipt and cleanup."""
    repo = repo_root.resolve()
    source = _inside(repo, input_tree, "inputTree")
    request_file = _file(repo, request_path, "request")
    oracle_file = _file(repo, oracle_path, "oracle")
    output = _inside(repo, receipt_path, "receipt")
    if output.exists() or output.is_symlink():
        raise SharedRouteError("receipt output already exists")
    if timeout_seconds <= 0:
        raise SharedRouteError("timeoutSeconds must be positive")
    request = json.loads(request_file.read_text(encoding="utf-8"))
    if not isinstance(request, dict):
        raise SharedRouteError("request must be a JSON object")
    patches = [
        (role, _file(repo, path, f"{role} patch").read_bytes())
        for role, path in patch_paths
    ]
    prepared = repo / ".local/prepared" / f"shared-task-{uuid.uuid4()}"
    audit: dict[str, object] | None = None
    terminal: BaseException | None = None
    context: tuple[dict[str, object], dict[str, object], bytes, bytes, dict[str, object], object] | None = None
    try:
        audit = managed_probe_prepare.prepare_patched_tree(
            repo_root=repo, snapshot_root=source, prepared_root=prepared, patches=patches,
        )
        prepared_identity = native_cycle.tree_identity(prepared)
        completed = execute(
            _runner_command(repo, prepared, timeout_seconds),
            text=True, capture_output=True, timeout=timeout_seconds + 90,
        )
        try:
            runner = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise SharedRouteError("native cycle returned invalid JSON") from exc
        if completed.returncode != 0 or not isinstance(runner, dict):
            raise SharedRouteError("native cycle failed")
        if runner.get("status") != "runtime_contract_completed":
            raise SharedRouteError("native runtime contract is incomplete")
        _runner_input(runner, prepared_identity)
        client_path, server_path = _runner_receipts(repo, runner)
        oracle, business = _oracle(oracle_file, request_file, client_path, server_path, execute)
        context = (
            runner, prepared_identity, client_path.read_bytes(), server_path.read_bytes(),
            oracle, business,
        )
    except BaseException as exc:
        terminal = exc
        raise
    finally:
        if audit is not None:
            try:
                managed_probe_prepare.discard_prepared_tree(repo_root=repo, prepared_root=prepared)
            except BaseException as cleanup:
                if terminal is None:
                    raise SharedRouteError(f"prepared cleanup failed: {cleanup}") from cleanup
                raise SharedRouteError(f"route failed: {terminal}; prepared cleanup failed: {cleanup}") from cleanup
    if audit is None or context is None:
        raise SharedRouteError("route completed without validated result")
    runner, prepared_identity, client, server, oracle, business = context
    runner_cleanup = runner.get("storageCompaction")
    receipt = {
        "version": 1,
        "canonical": audit["canonicalBase"],
        "patches": audit["patches"],
        "input": {
            "prepared": prepared_identity,
            "runner": _runner_input(runner, prepared_identity),
            "frozen": runner["preparedInvocation"]["frozenInput"]["identity"],
        },
        "request": {"sha256": _json_sha(request), "payload": request},
        "result": {
            "client": _raw(client), "server": _raw(server),
            "business": business, "oracle": oracle,
        },
        "cleanup": {"runner": runner_cleanup, "prepared": "discarded"},
    }
    validate_receipt(receipt)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run",))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--input-tree", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--production-patch", type=Path, required=True)
    parser.add_argument("--instrumentation-patch", type=Path, required=True)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=300)
    args = parser.parse_args(argv)
    try:
        receipt = run_task(
            repo_root=args.repo_root, input_tree=args.input_tree,
            request_path=args.request,
            patch_paths=[("production", args.production_patch), ("instrumentation", args.instrumentation_patch)],
            oracle_path=args.oracle,
            receipt_path=args.receipt, timeout_seconds=args.timeout_seconds,
        )
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
