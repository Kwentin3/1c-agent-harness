"""Repo-owned CF → hierarchical snapshot materializer.

The 1C platform and GUI runtime are external prerequisites. This module owns the
fixed native algorithm; it never installs or downloads a runtime.
"""
from __future__ import annotations

import os
import json
from pathlib import Path
import signal
import subprocess
import time
from typing import Callable

try:  # Installed companion package.
    from .target_admission import remove_owned
except ImportError:  # ``python scripts/...`` remains a supported local entrypoint.
    from target_admission import remove_owned

XVFB_SCREEN = "-screen 0 1280x1024x8 -nolisten tcp"
TIMEOUT_SECONDS = 600


class MaterializerUnavailable(RuntimeError):
    pass


class MaterializationFailed(RuntimeError):
    pass


def _process_group_exists(process_group_id: int) -> bool:
    try:
        os.killpg(process_group_id, 0)
    except ProcessLookupError:
        return False
    return True


def _stop_process_group(process_group_id: int) -> None:
    """Reap the Xvfb wrapper's residual group before accepting a step."""
    if not _process_group_exists(process_group_id):
        return
    os.killpg(process_group_id, signal.SIGTERM)
    deadline = time.monotonic() + 2
    while _process_group_exists(process_group_id) and time.monotonic() < deadline:
        time.sleep(0.025)
    if _process_group_exists(process_group_id):
        os.killpg(process_group_id, signal.SIGKILL)
    if _process_group_exists(process_group_id):
        raise MaterializationFailed("native materialization left a running process")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate runtime contract key")
        result[key] = value
    return result


def runtime_paths(_project_root: Path | None = None) -> dict[str, Path]:
    """Load one executor-owned runtime locator, never project metadata.

    The executor launch environment sets ``ONE_C_HARNESS_RUNTIME_CONFIG`` once.
    It is deliberately not inferred from the terminal cwd, project contract, or
    model arguments.
    """
    configured = os.environ.get("ONE_C_HARNESS_RUNTIME_CONFIG", "")
    contract = Path(configured) if configured else None
    if contract is None or not contract.is_absolute() or contract.is_symlink() or not contract.is_file():
        raise MaterializerUnavailable("1C runtime contract is unavailable")
    try:
        value = json.loads(contract.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
        if not isinstance(value, dict) or set(value) != {"schemaVersion", "platform", "xvfb", "fontconfig", "libs"}:
            raise ValueError("runtime contract keys")
        if value["schemaVersion"] != 1:
            raise ValueError("runtime contract schema")
        paths = {name: Path(value[name]) for name in ("platform", "xvfb", "fontconfig", "libs")}
        if any(not path.is_absolute() for path in paths.values()):
            raise ValueError("runtime paths must be absolute")
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise MaterializerUnavailable("1C runtime contract is invalid") from exc
    return paths


def require_runtime(repo_root: Path) -> dict[str, Path]:
    paths = runtime_paths(repo_root)
    required = ("platform", "xvfb", "fontconfig")
    if any(not paths[name].is_file() or paths[name].is_symlink() for name in required):
        raise MaterializerUnavailable("1C runtime is unavailable")
    if not os.access(paths["platform"], os.X_OK) or not os.access(paths["xvfb"], os.X_OK):
        raise MaterializerUnavailable("1C runtime is unavailable")
    if not paths["libs"].is_dir() or paths["libs"].is_symlink():
        raise MaterializerUnavailable("1C runtime is unavailable")
    return paths


def _run_step(
    argv: list[str], environment: dict[str, str], result: Path, *, runner: Callable[..., subprocess.CompletedProcess[bytes]]
) -> None:
    try:
        if runner is not subprocess.run:
            completed = runner(argv, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=TIMEOUT_SECONDS, start_new_session=True, check=False)
        else:
            process = subprocess.Popen(argv, env=environment, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            try:
                process.communicate(timeout=TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                _stop_process_group(process.pid)
                process.communicate()
                raise MaterializationFailed("native materialization timed out")
            _stop_process_group(process.pid)
            completed = subprocess.CompletedProcess(argv, process.returncode)
    except subprocess.TimeoutExpired as exc:
        raise MaterializationFailed("native materialization timed out") from exc
    if completed.returncode != 0:
        raise MaterializationFailed("native materialization command failed")
    if not result.is_file() or result.read_text(encoding="utf-8-sig").strip() != "0":
        raise MaterializationFailed("native materialization reported a nonzero result")


def materialize_cf(
    *, repo_root: Path,
    source: Path,
    output: Path,
    work_root: Path,
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> None:
    """Create a new hierarchical export from one immutable CF.

    `output` and `work_root` must not exist. All created transient state is below
    `work_root`; the caller owns its final removal after this function returns.
    """
    runtime = require_runtime(repo_root)
    if source.is_symlink() or not source.is_file():
        raise MaterializationFailed("CF source is not a regular file")
    if output.exists() or output.is_symlink() or work_root.exists() or work_root.is_symlink():
        raise MaterializationFailed("materializer output or work root already exists")
    work_root.mkdir(parents=True)
    logs = work_root / "logs"
    infobase = work_root / "ib"
    logs.mkdir()
    environment = os.environ.copy()
    environment.update({
        "HOME": str(work_root / "home"),
        "TMPDIR": str(work_root / "tmp"),
        "XDG_CACHE_HOME": str(work_root / "xdg-cache"),
        "XDG_CONFIG_HOME": str(work_root / "xdg-config"),
        "XDG_DATA_HOME": str(work_root / "xdg-data"),
        "FONTCONFIG_FILE": str(runtime["fontconfig"]),
        "LD_LIBRARY_PATH": f"{runtime['platform'].parent}:{runtime['libs']}",
        "PATH": f"{runtime['xvfb'].parent}:{environment.get('PATH', '')}",
    })
    for key in ("HOME", "TMPDIR", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME"):
        Path(environment[key]).mkdir()
    common = [str(runtime["xvfb"]), "-a", "-s", XVFB_SCREEN, str(runtime["platform"])]
    steps = (
        (common + ["CREATEINFOBASE", f"File={infobase}", "/DisableStartupDialogs", "/DisableStartupMessages", "/Out", str(logs / "create.log"), "/DumpResult", str(logs / "create.result")], logs / "create.result"),
        (common + ["DESIGNER", "/F", str(infobase), "/DisableStartupDialogs", "/DisableStartupMessages", "/LoadCfg", str(source), "/Out", str(logs / "load.log"), "/DumpResult", str(logs / "load.result")], logs / "load.result"),
        (common + ["DESIGNER", "/F", str(infobase), "/DisableStartupDialogs", "/DisableStartupMessages", "/DumpConfigToFiles", str(output), "-Format", "Hierarchical", "/Out", str(logs / "dump.log"), "/DumpResult", str(logs / "dump.result")], logs / "dump.result"),
    )
    try:
        for argv, result in steps:
            _run_step(argv, environment, result, runner=runner)
        if output.is_symlink() or not output.is_dir():
            raise MaterializationFailed("native materialization did not create a snapshot")
    except BaseException:
        remove_owned(output)
        raise
