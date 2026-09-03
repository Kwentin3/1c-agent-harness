"""Repo-owned CF → hierarchical snapshot materializer.

The 1C platform and GUI runtime are external prerequisites. This module owns the
fixed native algorithm; it never installs or downloads a runtime.
"""
from __future__ import annotations

import os
import json
from pathlib import Path
import shutil
import signal
import stat
import subprocess
from typing import Callable

XVFB_SCREEN = "-screen 0 1280x1024x8 -nolisten tcp"
TIMEOUT_SECONDS = 600


class MaterializerUnavailable(RuntimeError):
    pass


class MaterializationFailed(RuntimeError):
    pass


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate runtime contract key")
        result[key] = value
    return result


def runtime_paths(repo_root: Path) -> dict[str, Path]:
    """Load the one executor-owned runtime locator, never project metadata."""
    contract = repo_root / ".local/one-c-runtime.json"
    if contract.is_symlink() or not contract.is_file():
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


def _remove_owned_tree(path: Path) -> None:
    if not path.exists():
        return
    if path.is_symlink() or not path.is_dir():
        raise MaterializationFailed("owned cleanup target is not a directory")
    for item in (path, *path.rglob("*")):
        mode = item.lstat().st_mode
        if stat.S_ISDIR(mode):
            item.chmod(mode | stat.S_IRWXU)
        elif stat.S_ISREG(mode):
            item.chmod(mode | stat.S_IRUSR | stat.S_IWUSR)
        else:
            raise MaterializationFailed("owned cleanup target contains a special entry")
    shutil.rmtree(path)


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
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.communicate(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.communicate()
                raise MaterializationFailed("native materialization timed out")
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                pass
            else:
                os.killpg(process.pid, signal.SIGKILL)
                raise MaterializationFailed("native materialization left a running process")
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
        _remove_owned_tree(output)
        raise
