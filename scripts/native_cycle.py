#!/usr/bin/env python3
"""Run one prepared 1C native lifecycle without owning its oracle."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import tempfile
import time
from types import SimpleNamespace
from typing import Optional


XVFB_SCREEN = "-screen 0 1280x1024x8 -nolisten tcp"
PR_SET_CHILD_SUBREAPER = 36


class _ReceiptChangedDuringRead(RuntimeError):
    """The admitted receipt changed while one observation was in flight."""


def _reject_symlink_components(repo_root: Path, candidate: Path, *, field: str) -> None:
    current = repo_root
    for part in candidate.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"{field} contains symlink path component: {current}")


def _repo_path(repo_root: Path, value: str, *, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty repository-relative path")
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"{field} must stay within the repository")
    _reject_symlink_components(repo_root, candidate, field=field)
    resolved = (repo_root / candidate).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ValueError(f"{field} escapes the repository") from exc
    return resolved


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_plan(
    spec_path: Path,
    repo_root: Path,
    *,
    bind_receipt_launch_parameter: bool = False,
) -> SimpleNamespace:
    data = json.loads(
        spec_path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_json_object,
    )
    if not isinstance(data, dict):
        raise ValueError("spec must be a JSON object")
    if type(data.get("schemaVersion")) is not int or data["schemaVersion"] != 1:
        raise ValueError("unsupported schemaVersion")

    allowed_keys = {
        "schemaVersion", "inputTree", "inputTreeSha256", "runRoot",
        "receipt", "completeMarker", "timeoutSeconds",
    }
    if set(data) != allowed_keys:
        raise ValueError(f"spec keys mismatch: expected {sorted(allowed_keys)}, got {sorted(data)}")
    expected_input_tree_sha256 = data.get("inputTreeSha256")
    if (
        not isinstance(expected_input_tree_sha256, str)
        or len(expected_input_tree_sha256) != 64
        or any(character not in "0123456789abcdef" for character in expected_input_tree_sha256)
    ):
        raise ValueError("inputTreeSha256 must be a lowercase SHA-256 hex digest")
    input_tree = _repo_path(repo_root, data.get("inputTree"), field="inputTree")
    run_root = _repo_path(repo_root, data.get("runRoot"), field="runRoot")
    allowed_runs = (repo_root / ".local" / "runs").resolve()
    try:
        run_root.relative_to(allowed_runs)
    except ValueError as exc:
        raise ValueError("runRoot must be inside .local/runs") from exc
    if run_root == allowed_runs:
        raise ValueError("runRoot must be inside .local/runs")
    platform = repo_root / ".local/platform/1cv8t/x86_64/8.5.1.1150/1cv8t"
    xvfb_run = repo_root / ".local/platform/libs/usr/bin/xvfb-run"
    fontconfig = repo_root / ".local/platform/fonts.conf"
    receipt_relative = Path(data.get("receipt", ""))
    if (
        receipt_relative.is_absolute()
        or len(receipt_relative.parts) < 2
        or receipt_relative.parts[0] != "evidence"
        or ".." in receipt_relative.parts
    ):
        raise ValueError("receipt must be a file inside runRoot/evidence")
    receipt = run_root / receipt_relative
    work_copy = run_root / "work-copy"
    infobase = run_root / "ib"
    logs = run_root / "logs"

    ld_paths = [
        repo_root / ".local/platform/1cv8t/x86_64/8.5.1.1150",
        repo_root / ".local/platform/libs/usr/lib/x86_64-linux-gnu",
    ]

    common = [str(xvfb_run), "-a", "-s", XVFB_SCREEN, str(platform)]
    create_argv = common + [
        "CREATEINFOBASE", f"File={infobase}",
        "/DisableStartupDialogs", "/DisableStartupMessages",
        "/Out", str(logs / "create.log"),
        "/DumpResult", str(logs / "create.result"),
    ]
    load_argv = common + [
        "DESIGNER", "/F", str(infobase),
        "/LoadConfigFromFiles", str(work_copy), "/UpdateDBCfg",
        "/DisableStartupDialogs", "/DisableStartupMessages",
        "/Out", str(logs / "load.log"),
        "/DumpResult", str(logs / "load.result"),
    ]
    runtime_argv = common + ["ENTERPRISE", "/F", str(infobase)]
    if bind_receipt_launch_parameter:
        runtime_argv += ["/C", str(receipt)]
    runtime_argv += [
        "/DisableStartupDialogs", "/DisableStartupMessages",
        "/Out", str(logs / "run.log"),
        "/DumpResult", str(logs / "run.result"),
    ]
    environment = {
        "HOME": str(run_root / "home"),
        "TMPDIR": str(run_root / "tmp"),
        "XDG_CACHE_HOME": str(run_root / "home" / "xdg-cache"),
        "XDG_CONFIG_HOME": str(run_root / "home" / "xdg-config"),
        "XDG_DATA_HOME": str(run_root / "home" / "xdg-data"),
        "FONTCONFIG_FILE": str(fontconfig),
        "LD_LIBRARY_PATH": ":".join(map(str, ld_paths)),
        "PATH": f"{xvfb_run.parent}:{os.environ.get('PATH', '')}",
    }
    complete_marker = data.get("completeMarker")
    if not isinstance(complete_marker, str) or not complete_marker:
        raise ValueError("completeMarker must be a non-empty string")
    if "\n" in complete_marker or "\r" in complete_marker:
        raise ValueError("completeMarker must be a single line")
    timeout_seconds = data.get("timeoutSeconds")
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 3600:
        raise ValueError("timeoutSeconds must be an integer from 1 to 3600")
    batch_timeout_seconds = 600
    create_success_marker = "completed successfully"
    load_success_marker = "Configuration successfully updated"
    return SimpleNamespace(
        spec=data,
        input_tree=input_tree,
        expected_input_tree_sha256=expected_input_tree_sha256,
        run_root=run_root,
        work_copy=work_copy,
        infobase=infobase,
        receipt=receipt,
        create_argv=create_argv,
        load_argv=load_argv,
        runtime_argv=runtime_argv,
        environment=environment,
        complete_marker=complete_marker,
        timeout_seconds=timeout_seconds,
        batch_timeout_seconds=batch_timeout_seconds,
        create_success_marker=create_success_marker,
        load_success_marker=load_success_marker,
    )


def tree_identity(root: Path) -> dict[str, object]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"input tree is not a non-symlink directory: {root}")
    digest = hashlib.sha256()
    files = 0
    directories = 1
    total_bytes = 0

    def bind_entry(entry_type: bytes, relative: bytes, mode: int) -> None:
        digest.update(entry_type)
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(stat.S_IMODE(mode).to_bytes(4, "big"))

    bind_entry(b"D", b".", root.lstat().st_mode)
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlink is not allowed in input tree: {path}")
        relative = path.relative_to(root).as_posix().encode("utf-8")
        path_stat = path.lstat()
        if path.is_dir():
            bind_entry(b"D", relative, path_stat.st_mode)
            directories += 1
            continue
        if not path.is_file():
            raise ValueError(f"non-regular input entry is not allowed: {path}")
        payload = path.read_bytes()
        bind_entry(b"F", relative, path_stat.st_mode)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
        files += 1
        total_bytes += len(payload)
    return {
        "files": files,
        "directories": directories,
        "bytes": total_bytes,
        "sha256": digest.hexdigest(),
    }


def _require_read_only_tree(root: Path) -> None:
    writable = [
        path
        for path in (root, *sorted(root.rglob("*")))
        if path.stat().st_mode & 0o222
    ]
    if writable:
        rendered = ", ".join(str(path) for path in writable[:3])
        raise ValueError(f"input tree must be read-only; writable path: {rendered}")


def prepare_run(plan: SimpleNamespace) -> dict[str, object]:
    source_identity = tree_identity(plan.input_tree)
    if source_identity["sha256"] != plan.expected_input_tree_sha256:
        raise ValueError(
            f"input tree identity mismatch: expected {plan.expected_input_tree_sha256}, "
            f"got {source_identity['sha256']}"
        )
    _require_read_only_tree(plan.input_tree)
    try:
        plan.run_root.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise FileExistsError(f"runRoot already exists: {plan.run_root}") from exc
    shutil.copytree(plan.input_tree, plan.work_copy, copy_function=shutil.copy2)
    copied_identity = tree_identity(plan.work_copy)
    if copied_identity != source_identity:
        raise RuntimeError("work-copy identity differs from immutable input")
    for path in (plan.work_copy, *plan.work_copy.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"copied work tree contains a symlink: {path}")
        path.chmod(path.stat().st_mode | stat.S_IWUSR)
    load_identity = tree_identity(plan.work_copy)
    return {
        "files": source_identity["files"],
        "directories": source_identity["directories"],
        "bytes": source_identity["bytes"],
        "sourceTreeSha256": source_identity["sha256"],
        "copiedTreeSha256": copied_identity["sha256"],
        "loadTreeSha256": load_identity["sha256"],
    }


def _new_invocation_root(repo_root: Path) -> Path:
    invocation_parent_relative = Path(".local/runs/native-cycle")
    _reject_symlink_components(
        repo_root,
        invocation_parent_relative,
        field="invocationRoot",
    )
    invocation_parent = repo_root / invocation_parent_relative
    invocation_parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="run-", dir=invocation_parent))


def prepare_invocation(
    repo_root: Path,
    input_tree_value: str,
    complete_marker: str,
    timeout_seconds: int,
    invocation_root: Optional[Path] = None,
) -> SimpleNamespace:
    repo_root = repo_root.resolve()
    if invocation_root is None:
        invocation_root = _new_invocation_root(repo_root)
    input_tree = _repo_path(repo_root, input_tree_value, field="inputTree")
    prepared_root = (repo_root / ".local" / "prepared").resolve()
    try:
        input_tree.relative_to(prepared_root)
    except ValueError as exc:
        raise ValueError("inputTree must be inside .local/prepared") from exc
    if input_tree == prepared_root:
        raise ValueError("inputTree must be inside .local/prepared")
    if not isinstance(complete_marker, str) or not complete_marker:
        raise ValueError("completeMarker must be a non-empty string")
    if "\n" in complete_marker or "\r" in complete_marker:
        raise ValueError("completeMarker must be a single line")
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 3600:
        raise ValueError("timeoutSeconds must be an integer from 1 to 3600")

    source_identity = tree_identity(input_tree)
    frozen_input = invocation_root / "frozen-input"
    spec_path = invocation_root / "spec.json"
    run_root = invocation_root / "run"
    invocation = SimpleNamespace(
        invocation_root=invocation_root,
        input_tree=input_tree,
        source_identity=source_identity,
        copied_identity=None,
        frozen_input=frozen_input,
        frozen_identity=None,
        spec_path=spec_path,
        run_root=run_root,
        receipt=run_root / "evidence" / "receipt.txt",
        runtime_argv_sha256=None,
    )
    try:
        shutil.copytree(input_tree, frozen_input, copy_function=shutil.copy2)
        copied_identity = tree_identity(frozen_input)
        invocation.copied_identity = copied_identity
        if copied_identity != source_identity:
            raise RuntimeError("generated input copy differs from prepared source")
        for path in sorted(frozen_input.rglob("*"), reverse=True):
            if path.is_symlink():
                raise ValueError(f"generated frozen input contains a symlink: {path}")
            path.chmod(path.lstat().st_mode & ~0o222)
        frozen_input.chmod(frozen_input.lstat().st_mode & ~0o222)
        frozen_identity = tree_identity(frozen_input)
        invocation.frozen_identity = frozen_identity

        spec = {
            "schemaVersion": 1,
            "inputTree": frozen_input.relative_to(repo_root).as_posix(),
            "inputTreeSha256": frozen_identity["sha256"],
            "runRoot": run_root.relative_to(repo_root).as_posix(),
            "receipt": "evidence/receipt.txt",
            "completeMarker": complete_marker,
            "timeoutSeconds": timeout_seconds,
        }
        _write_json_atomic(spec_path, spec)
    except Exception as exc:
        setattr(exc, "partial_invocation", invocation)
        raise
    return invocation


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_batch_step(
    label: str,
    argv: list[str],
    environment: dict[str, str],
    result_path: Path,
    log_path: Path,
    success_marker: str,
    timeout_seconds: int,
) -> dict[str, object]:
    if result_path.exists() or log_path.exists():
        raise RuntimeError(f"stale {label} result or log exists")
    baseline_children = _prepare_process_ownership()
    process = subprocess.Popen(
        argv,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        process_return = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        _stop_process_group(process, baseline_children)
        raise TimeoutError(f"{label} timed out after {timeout_seconds}s") from exc
    _stop_process_group(process, baseline_children)
    if not result_path.is_file() or not log_path.is_file():
        raise RuntimeError(f"{label} did not produce result and log")
    dump_result = result_path.read_bytes().decode("utf-8-sig").strip()
    log_lines = log_path.read_text(encoding="utf-8-sig", errors="strict").splitlines()
    marker_present = any(
        line == success_marker
        or (
            success_marker == "completed successfully"
            and line.startswith("Creation of infobase (")
            and line.endswith(") completed successfully")
        )
        for line in log_lines
    )
    if process_return != 0 or dump_result != "0" or not marker_present:
        raise RuntimeError(
            f"{label} failed: process={process_return}, DumpResult={dump_result!r}, "
            f"successMarker={marker_present}"
        )
    return {
        "processReturn": process_return,
        "dumpResult": dump_result,
        "resultSha256": _file_sha256(result_path),
        "logSha256": _file_sha256(log_path),
        "successMarker": success_marker,
    }


def _enable_child_subreaper() -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) != 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number))


def _proc_children_path() -> Path:
    return Path(f"/proc/{os.getpid()}/task/{os.getpid()}/children")


def _direct_children() -> set[int]:
    text = _proc_children_path().read_text(encoding="ascii").strip()
    return {int(value) for value in text.split()} if text else set()


def _prepare_process_ownership() -> set[int]:
    try:
        _enable_child_subreaper()
        return _direct_children()
    except (OSError, ValueError) as exc:
        detail = (
            "procfs children interface unavailable"
            if isinstance(exc, FileNotFoundError)
            else str(exc)
        )
        raise RuntimeError(f"process ownership preflight failed: {detail}") from exc


def _preflight_process_ownership() -> None:
    _prepare_process_ownership()


def _reap_owned_children(baseline_children: set[int], grace_seconds: float) -> None:
    deadline = time.monotonic() + grace_seconds
    signalled: set[int] = set()
    while time.monotonic() < deadline:
        owned = _direct_children() - baseline_children
        if not owned:
            return
        for pid in owned - signalled:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            signalled.add(pid)
        for pid in tuple(owned):
            try:
                os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                pass
        time.sleep(0.025)
    owned = _direct_children() - baseline_children
    for pid in owned:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    for pid in owned:
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass


def _process_group_exists(process_group_id: int) -> bool:
    try:
        os.killpg(process_group_id, 0)
    except ProcessLookupError:
        return False
    return True


def _stop_process_group(
    process: subprocess.Popen[bytes],
    baseline_children: set[int],
    grace_seconds: float = 2.0,
) -> int:
    if _process_group_exists(process.pid):
        os.killpg(process.pid, signal.SIGTERM)
    deadline = time.monotonic() + grace_seconds
    while _process_group_exists(process.pid) and time.monotonic() < deadline:
        time.sleep(0.025)
    if _process_group_exists(process.pid):
        os.killpg(process.pid, signal.SIGKILL)
    if process.poll() is None:
        try:
            process.wait(timeout=grace_seconds)
        except subprocess.TimeoutExpired:
            pass
    _reap_owned_children(baseline_children, grace_seconds)
    return process.returncode


def _read_receipt_channel(receipt_root: Path, receipt_path: Path) -> Optional[bytes]:
    try:
        relative = receipt_path.relative_to(receipt_root)
    except ValueError as exc:
        raise RuntimeError("runtime receipt channel escapes evidence root") from exc
    if not relative.parts:
        raise RuntimeError("runtime receipt channel must name a file")

    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    file_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
    descriptors: list[int] = []
    try:
        descriptors.append(os.open(receipt_root, directory_flags))
        for component in relative.parts[:-1]:
            descriptors.append(os.open(component, directory_flags, dir_fd=descriptors[-1]))
        file_descriptor = os.open(relative.parts[-1], file_flags, dir_fd=descriptors[-1])
        descriptors.append(file_descriptor)
        before = os.fstat(file_descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise RuntimeError("runtime receipt channel is not a single-link regular file")
        with os.fdopen(os.dup(file_descriptor), "rb") as stream:
            payload = stream.read()
        after = os.fstat(file_descriptor)
        if after.st_nlink != 1:
            raise RuntimeError("runtime receipt channel is not a single-link regular file")
        if (
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        ):
            raise _ReceiptChangedDuringRead("runtime receipt channel changed during read")
        return payload
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise RuntimeError("runtime receipt channel contains a symlink or invalid entry") from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _artifact_diagnostic(path: Optional[Path]) -> dict[str, object]:
    if path is None or not os.path.lexists(path):
        return {"state": "absent"}
    path_stat = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(path_stat.st_mode):
        return {"state": "invalid", "mode": stat.S_IFMT(path_stat.st_mode)}
    payload = path.read_bytes()
    return {
        "state": "regular",
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _receipt_diagnostic(
    receipt_root: Path,
    receipt_path: Path,
    complete_marker: str,
) -> dict[str, object]:
    try:
        payload = _read_receipt_channel(receipt_root, receipt_path)
    except Exception as exc:
        return {
            "state": "invalid",
            "errorType": type(exc).__name__,
            "error": str(exc),
        }
    if payload is None:
        return {"state": "absent"}
    try:
        lines = payload.decode("utf-8-sig", errors="strict").splitlines()
        terminal_marker = bool(lines) and lines[-1] == complete_marker
    except UnicodeDecodeError:
        terminal_marker = False
    return {
        "state": "regular",
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "terminalMarker": terminal_marker,
    }


def _runtime_failure_kind(error: Exception) -> str:
    if isinstance(error, TimeoutError):
        return "timeout"
    if str(error).startswith("runtime exited before completion"):
        return "exited_before_completion"
    if "receipt channel" in str(error):
        return "invalid_receipt"
    return "runtime_error"


def run_runtime(
    argv: list[str],
    environment: dict[str, str],
    receipt_path: Path,
    complete_marker: str,
    *,
    timeout_seconds: int,
    receipt_root: Path,
    log_path: Optional[Path] = None,
    result_path: Optional[Path] = None,
    poll_seconds: float = 0.25,
    stable_reads: int = 2,
) -> dict[str, object]:
    if os.path.lexists(receipt_path):
        raise RuntimeError("stale runtime receipt exists")
    baseline_children = _prepare_process_ownership()
    process = subprocess.Popen(
        argv,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    deadline = time.monotonic() + timeout_seconds
    stable_hash: Optional[str] = None
    stable_count = 0
    completed = False
    failure: Optional[Exception] = None
    try:
        try:
            while time.monotonic() < deadline:
                try:
                    payload = _read_receipt_channel(receipt_root, receipt_path)
                except _ReceiptChangedDuringRead:
                    stable_hash = None
                    stable_count = 0
                    time.sleep(min(poll_seconds, 0.01))
                    continue
                if payload is not None:
                    current_hash = hashlib.sha256(payload).hexdigest()
                    decoded_lines = payload.decode("utf-8-sig", errors="strict").splitlines()
                    marker_present = bool(decoded_lines) and decoded_lines[-1] == complete_marker
                    if marker_present and current_hash == stable_hash:
                        stable_count += 1
                    elif marker_present:
                        stable_hash = current_hash
                        stable_count = 1
                    else:
                        stable_hash = None
                        stable_count = 0
                    if stable_count >= stable_reads:
                        completed = True
                        break
                if process.poll() is not None:
                    failure = RuntimeError(f"runtime exited before completion: {process.returncode}")
                    break
                time.sleep(poll_seconds)
            if not completed and failure is None:
                failure = TimeoutError(
                    f"runtime completion marker not observed within {timeout_seconds}s"
                )
        except Exception as exc:
            failure = exc
    finally:
        process_return = _stop_process_group(process, baseline_children)

    diagnostic: dict[str, object] = {
        "completed": completed,
        "completeMarker": complete_marker,
        "stableReads": stable_count,
        "processReturn": process_return,
        "receipt": _receipt_diagnostic(receipt_root, receipt_path, complete_marker),
        "outputs": {
            "log": _artifact_diagnostic(log_path),
            "result": _artifact_diagnostic(result_path),
        },
    }
    if failure is not None:
        diagnostic["failureKind"] = _runtime_failure_kind(failure)
        failure.runtime_diagnostic = diagnostic
        raise failure
    if stable_hash is None:
        failure = RuntimeError("runtime completed without a stable receipt hash")
        diagnostic["failureKind"] = _runtime_failure_kind(failure)
        failure.runtime_diagnostic = diagnostic
        raise failure
    final_receipt = diagnostic["receipt"]
    if (
        final_receipt.get("state") != "regular"
        or not final_receipt.get("terminalMarker")
        or final_receipt.get("sha256") != stable_hash
    ):
        failure = RuntimeError("runtime receipt changed after completion during process cleanup")
        diagnostic["failureKind"] = _runtime_failure_kind(failure)
        failure.runtime_diagnostic = diagnostic
        raise failure
    diagnostic["receiptSha256"] = final_receipt["sha256"]
    diagnostic["receiptBytes"] = final_receipt["bytes"]
    return diagnostic


def _write_json_atomic(path: Path, value: object) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def run_cycle(plan: SimpleNamespace, spec_path: Path) -> dict[str, object]:
    for label, path, kind in (
        ("inputTree", plan.input_tree, "directory"),
        ("platform", Path(plan.create_argv[4]), "file"),
        ("xvfbRun", Path(plan.create_argv[0]), "file"),
    ):
        valid = path.is_dir() if kind == "directory" else path.is_file()
        if not valid:
            raise ValueError(f"{label} is not an existing {kind}: {path}")
    if plan.receipt == plan.run_root or plan.run_root not in plan.receipt.parents:
        raise ValueError("receipt must be inside runRoot")
    _preflight_process_ownership()
    started = time.monotonic()
    input_identity = prepare_run(plan)
    for directory in (
        plan.run_root / "logs",
        plan.run_root / "evidence",
        plan.run_root / "home",
        plan.run_root / "tmp",
        plan.run_root / "home" / "xdg-cache",
        plan.run_root / "home" / "xdg-config",
        plan.run_root / "home" / "xdg-data",
    ):
        directory.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update(plan.environment)
    logs = plan.run_root / "logs"
    result: dict[str, object] = {
        "schemaVersion": 1,
        "status": "RUNNING",
        "durationSeconds": 0.0,
        "specSha256": _file_sha256(spec_path),
        "input": input_identity,
        "commands": {
            "create": plan.create_argv,
            "load": plan.load_argv,
            "runtime": plan.runtime_argv,
        },
        "environment": plan.environment,
    }
    failed_stage = "create"
    try:
        result["create"] = run_batch_step(
            "create", plan.create_argv, environment,
            logs / "create.result", logs / "create.log",
            plan.create_success_marker, plan.batch_timeout_seconds,
        )
        failed_stage = "load"
        result["load"] = run_batch_step(
            "load", plan.load_argv, environment,
            logs / "load.result", logs / "load.log",
            plan.load_success_marker, plan.batch_timeout_seconds,
        )
        failed_stage = "runtime"
        result["runtime"] = run_runtime(
            plan.runtime_argv, environment, plan.receipt, plan.complete_marker,
            timeout_seconds=plan.timeout_seconds,
            receipt_root=plan.run_root / "evidence",
            log_path=logs / "run.log",
            result_path=logs / "run.result",
        )
        failed_stage = "input-reverify"
        input_after = tree_identity(plan.input_tree)
        result["inputAfter"] = input_after
        if input_after["sha256"] != plan.expected_input_tree_sha256:
            raise RuntimeError("immutable input tree changed during lifecycle")
    except Exception as exc:
        runtime_diagnostic = getattr(exc, "runtime_diagnostic", None)
        if failed_stage == "runtime" and runtime_diagnostic is not None:
            result["runtime"] = runtime_diagnostic
        if "inputAfter" not in result:
            try:
                result["inputAfter"] = tree_identity(plan.input_tree)
            except Exception as identity_exc:
                result["inputAfterError"] = f"{type(identity_exc).__name__}: {identity_exc}"
        if failed_stage == "runtime":
            failure_status = (
                "runtime_timeout" if isinstance(exc, TimeoutError)
                else "runtime_exited_before_completion"
                if str(exc).startswith("runtime exited before completion")
                else "internal_error"
            )
        elif failed_stage == "input-reverify":
            failure_status = "input_changed"
        else:
            failure_status = f"{failed_stage}_failed"
        result.update({
            "status": failure_status,
            "failedStage": failed_stage,
            "durationSeconds": round(time.monotonic() - started, 3),
            "errorType": type(exc).__name__,
            "error": str(exc),
        })
        _write_json_atomic(plan.run_root / "result.json", result)
        raise
    result.update({
        "status": "runtime_contract_completed",
        "durationSeconds": round(time.monotonic() - started, 3),
    })
    _write_json_atomic(plan.run_root / "result.json", result)
    return result


def _prepared_source_after(invocation: SimpleNamespace) -> dict[str, object]:
    try:
        return tree_identity(invocation.input_tree)
    except Exception as exc:
        return {
            "errorType": type(exc).__name__,
            "error": str(exc),
        }


def _partial_prepared_invocation_fields(
    invocation: SimpleNamespace,
    repo_root: Path,
    source_after: dict[str, object],
) -> dict[str, object]:
    prepared: dict[str, object] = {
        "invocationRoot": invocation.invocation_root.relative_to(repo_root).as_posix(),
        "sourcePath": invocation.input_tree.relative_to(repo_root).as_posix(),
        "sourceBefore": invocation.source_identity,
        "sourceAfter": source_after,
        "copiedBeforeFreeze": invocation.copied_identity,
        "frozenInput": {
            "path": invocation.frozen_input.relative_to(repo_root).as_posix(),
            "identity": invocation.frozen_identity,
        },
        "generatedBinding": {
            "kind": "1c-enterprise-launch-parameter",
            "status": (
                "generated" if invocation.runtime_argv_sha256 is not None
                else "not-generated"
            ),
            "receipt": invocation.receipt.relative_to(repo_root).as_posix(),
            "runtimeArgvSha256": invocation.runtime_argv_sha256,
        },
    }
    if invocation.spec_path.is_file():
        prepared["generatedSpec"] = {
            "path": invocation.spec_path.relative_to(repo_root).as_posix(),
            "sha256": _file_sha256(invocation.spec_path),
        }
    else:
        prepared["generatedSpec"] = {
            "path": invocation.spec_path.relative_to(repo_root).as_posix(),
            "status": "absent",
        }
    return {
        "resultPath": (invocation.run_root / "result.json").relative_to(repo_root).as_posix(),
        "preparedInvocation": prepared,
    }


def _prepared_invocation_fields(
    invocation: SimpleNamespace,
    repo_root: Path,
    source_after: dict[str, object],
) -> dict[str, object]:
    result_path = invocation.run_root / "result.json"
    return {
        "resultPath": result_path.relative_to(repo_root).as_posix(),
        "preparedInvocation": {
            "invocationRoot": invocation.invocation_root.relative_to(repo_root).as_posix(),
            "sourcePath": invocation.input_tree.relative_to(repo_root).as_posix(),
            "sourceBefore": invocation.source_identity,
            "sourceAfter": source_after,
            "copiedBeforeFreeze": invocation.copied_identity,
            "frozenInput": {
                "path": invocation.frozen_input.relative_to(repo_root).as_posix(),
                "identity": invocation.frozen_identity,
            },
            "generatedSpec": {
                "path": invocation.spec_path.relative_to(repo_root).as_posix(),
                "sha256": _file_sha256(invocation.spec_path),
            },
            "generatedBinding": {
                "kind": "1c-enterprise-launch-parameter",
                "status": (
                    "generated" if invocation.runtime_argv_sha256 is not None
                    else "not-generated"
                ),
                "receipt": invocation.receipt.relative_to(repo_root).as_posix(),
                "runtimeArgvSha256": invocation.runtime_argv_sha256,
            },
        },
    }


def run_prepared(
    repo_root: Path,
    input_tree_value: str,
    complete_marker: str,
    timeout_seconds: int,
) -> dict[str, object]:
    repo_root = repo_root.resolve()
    started = time.monotonic()
    invocation_root = _new_invocation_root(repo_root)
    try:
        invocation = prepare_invocation(
            repo_root,
            input_tree_value,
            complete_marker,
            timeout_seconds,
            invocation_root=invocation_root,
        )
    except Exception as exc:
        partial = getattr(exc, "partial_invocation", None)
        if partial is not None:
            source_after = _prepared_source_after(partial)
            result_path = partial.run_root / "result.json"
            result_path.parent.mkdir(parents=True, exist_ok=True)
            failure = {
                "schemaVersion": 1,
                "status": "precheck_failed",
                "failedStage": "generated-input-freeze",
                "durationSeconds": round(time.monotonic() - started, 3),
                "totalDurationSeconds": round(time.monotonic() - started, 3),
                "errorType": type(exc).__name__,
                "error": str(exc),
            }
            failure.update(_partial_prepared_invocation_fields(partial, repo_root, source_after))
            if source_after != partial.source_identity:
                failure.update({
                    "status": "input_changed",
                    "failedStage": "prepared-input-reverify",
                })
            _write_json_atomic(result_path, failure)
            setattr(exc, "result_path", result_path)
            raise
        result_path = invocation_root / "result.json"
        failure = {
            "schemaVersion": 1,
            "status": "precheck_failed",
            "durationSeconds": round(time.monotonic() - started, 3),
            "errorType": type(exc).__name__,
            "error": str(exc),
            "resultPath": result_path.relative_to(repo_root).as_posix(),
            "preparedInvocation": {
                "invocationRoot": invocation_root.relative_to(repo_root).as_posix(),
                "requestedSourcePath": input_tree_value,
            },
        }
        _write_json_atomic(result_path, failure)
        setattr(exc, "result_path", result_path)
        raise
    invocation.receipt = invocation.run_root / "evidence" / "receipt.txt"
    invocation.runtime_argv_sha256 = None
    try:
        plan = load_plan(
            invocation.spec_path,
            repo_root,
            bind_receipt_launch_parameter=True,
        )
        invocation.receipt = plan.receipt
        invocation.runtime_argv_sha256 = hashlib.sha256(
            json.dumps(
                plan.runtime_argv,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
    except Exception as exc:
        source_after = _prepared_source_after(invocation)
        result_path = invocation.run_root / "result.json"
        result_path.parent.mkdir(parents=True, exist_ok=True)
        failure = {
            "schemaVersion": 1,
            "status": "precheck_failed",
            "failedStage": "generated-plan-preflight",
            "durationSeconds": round(time.monotonic() - started, 3),
            "totalDurationSeconds": round(time.monotonic() - started, 3),
            "errorType": type(exc).__name__,
            "error": str(exc),
        }
        failure.update(_prepared_invocation_fields(invocation, repo_root, source_after))
        if source_after != invocation.source_identity:
            failure.update({
                "status": "input_changed",
                "failedStage": "prepared-input-reverify",
            })
        _write_json_atomic(result_path, failure)
        setattr(exc, "result_path", result_path)
        raise
    try:
        result = run_cycle(plan, invocation.spec_path)
    except Exception as exc:
        source_after = _prepared_source_after(invocation)
        result_path = invocation.run_root / "result.json"
        if result_path.is_file():
            result = json.loads(result_path.read_text(encoding="utf-8"))
        else:
            invocation.run_root.mkdir(parents=True, exist_ok=True)
            result = {
                "schemaVersion": 1,
                "status": "copy_failed" if any(invocation.run_root.iterdir()) else "precheck_failed",
                "durationSeconds": round(time.monotonic() - started, 3),
                "errorType": type(exc).__name__,
                "error": str(exc),
            }
        result.update(_prepared_invocation_fields(invocation, repo_root, source_after))
        result["totalDurationSeconds"] = round(time.monotonic() - started, 3)
        if source_after != invocation.source_identity:
            result.update({
                "status": "input_changed",
                "failedStage": "prepared-input-reverify",
                "errorType": "RuntimeError",
                "error": "prepared input tree changed during lifecycle",
            })
        _write_json_atomic(result_path, result)
        setattr(exc, "result_path", result_path)
        raise

    source_after = _prepared_source_after(invocation)
    result.update(_prepared_invocation_fields(invocation, repo_root, source_after))
    result["totalDurationSeconds"] = round(time.monotonic() - started, 3)
    result_path = invocation.run_root / "result.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    if source_after != invocation.source_identity:
        result.update({
            "status": "input_changed",
            "failedStage": "prepared-input-reverify",
            "errorType": "RuntimeError",
            "error": "prepared input tree changed during lifecycle",
        })
        _write_json_atomic(result_path, result)
        exc = RuntimeError("prepared input tree changed during lifecycle")
        setattr(exc, "result_path", result_path)
        raise exc
    _write_json_atomic(result_path, result)
    return result


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="run one frozen native lifecycle spec")
    run_parser.add_argument("--spec", required=True, type=Path)
    run_parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    prepared_parser = subparsers.add_parser(
        "run-prepared",
        help="freeze, fingerprint, bind, and run one prepared tree",
    )
    prepared_parser.add_argument("--input-tree", required=True)
    prepared_parser.add_argument("--complete-marker", required=True)
    prepared_parser.add_argument("--timeout-seconds", required=True, type=int)
    prepared_parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    if args.command == "run-prepared":
        try:
            result = run_prepared(
                repo_root,
                args.input_tree,
                args.complete_marker,
                args.timeout_seconds,
            )
        except Exception as exc:
            result_path = getattr(exc, "result_path", None)
            if result_path is not None and Path(result_path).is_file():
                failure = json.loads(Path(result_path).read_text(encoding="utf-8"))
            else:
                failure = {
                    "schemaVersion": 1,
                    "status": "precheck_failed",
                    "errorType": type(exc).__name__,
                    "error": str(exc),
                }
            print(json.dumps(failure, ensure_ascii=False))
            return 1
        print(json.dumps(result, ensure_ascii=False))
        return 0

    spec_path = args.spec if args.spec.is_absolute() else repo_root / args.spec
    plan: Optional[SimpleNamespace] = None
    run_root_existed = False
    started = time.monotonic()
    try:
        plan = load_plan(spec_path, repo_root)
        run_root_existed = plan.run_root.exists()
        result = run_cycle(plan, spec_path)
    except Exception as exc:
        if plan is not None and (plan.run_root / "result.json").is_file():
            failure = json.loads((plan.run_root / "result.json").read_text(encoding="utf-8"))
            print(json.dumps(failure, ensure_ascii=False))
            return 1
        failure_status = "precheck_failed"
        if plan is not None and not run_root_existed and plan.run_root.is_dir():
            failure_status = "copy_failed"
        failure = {
            "schemaVersion": 1,
            "status": failure_status,
            "durationSeconds": round(time.monotonic() - started, 3),
            "errorType": type(exc).__name__,
            "error": str(exc),
        }
        if (
            plan is not None
            and not run_root_existed
            and plan.run_root.is_dir()
            and not (plan.run_root / "result.json").exists()
        ):
            _write_json_atomic(plan.run_root / "result.json", failure)
        print(json.dumps(failure, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
