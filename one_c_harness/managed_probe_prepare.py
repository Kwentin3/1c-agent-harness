#!/usr/bin/env python3
"""Copy, apply exact patches, audit and freeze one disposable input tree."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import stat
from subprocess import PIPE, run


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _child(repo: Path, value: Path, field: str, inside: Path) -> Path:
    candidate = value if value.is_absolute() else repo / value
    try:
        relative = candidate.relative_to(repo)
    except ValueError as exc:
        raise ValueError(f"{field} must be inside repository") from exc
    if not relative.parts or ".." in relative.parts:
        raise ValueError(f"{field} must be a repository descendant")
    current = repo
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"{field} contains a symlink")
    try:
        candidate.resolve(strict=False).relative_to(inside.resolve())
    except ValueError as exc:
        raise ValueError(f"{field} must be inside {inside}") from exc
    return candidate


def _disjoint(first: Path, second: Path) -> bool:
    first = first.resolve(strict=False)
    second = second.resolve(strict=False)
    try:
        first.relative_to(second)
    except ValueError:
        try:
            second.relative_to(first)
        except ValueError:
            return True
    return False


def _hashes(root: Path) -> dict[str, str]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("tree must be a non-symlink directory")
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"tree contains symlink: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f"tree contains non-regular entry: {path}")
        result[path.relative_to(root).as_posix()] = _sha(path.read_bytes())
    return result


def _identity(hashes: dict[str, str]) -> dict[str, object]:
    digest = hashlib.sha256()
    for relative, value in sorted(hashes.items()):
        digest.update(relative.encode("utf-8") + b"\0" + bytes.fromhex(value))
    return {"files": len(hashes), "sha256": digest.hexdigest()}


def _remove(root: Path) -> None:
    if not root.exists():
        return
    if root.is_symlink() or not root.is_dir():
        raise ValueError("refusing to remove non-directory preparedRoot")
    for path in sorted((root, *root.rglob("*")), key=lambda item: len(item.parts), reverse=True):
        if path.is_symlink():
            raise ValueError(f"refusing to remove prepared tree containing symlink: {path}")
        mode = path.stat().st_mode
        path.chmod(mode | (stat.S_IRWXU if path.is_dir() else stat.S_IWUSR))
    shutil.rmtree(root)


def discard_prepared_tree(*, repo_root: Path, prepared_root: Path) -> None:
    repo = repo_root.resolve()
    base = repo / ".local/prepared"
    prepared = _child(repo, prepared_root, "preparedRoot", base)
    if prepared == base:
        raise ValueError("preparedRoot must be a strict child of .local/prepared")
    _remove(prepared)


def prepare_patched_tree(
    *,
    repo_root: Path,
    snapshot_root: Path,
    prepared_root: Path,
    patches: list[tuple[str, bytes]],
) -> dict[str, object]:
    """Apply supplied bytes once and return only preparation-owned facts."""
    repo = repo_root.resolve()
    source = _child(repo, snapshot_root, "snapshotRoot", repo)
    base = repo / ".local/prepared"
    prepared = _child(repo, prepared_root, "preparedRoot", base)
    if prepared == base:
        raise ValueError("preparedRoot must be a strict child of .local/prepared")
    if not _disjoint(source, prepared):
        raise ValueError("snapshotRoot and preparedRoot must be disjoint")
    if source.is_symlink() or not source.is_dir():
        raise ValueError("snapshotRoot must be a non-symlink directory")
    if prepared.exists() or prepared.is_symlink():
        raise FileExistsError(f"preparedRoot already exists: {prepared}")
    if not patches:
        raise ValueError("patches must be a non-empty ordered list")
    roles: set[str] = set()
    for role, payload in patches:
        if not isinstance(role, str) or not role or role in roles:
            raise ValueError("patch roles must be unique non-empty strings")
        if not isinstance(payload, bytes) or not payload or b"\0" in payload:
            raise ValueError(f"{role} patch must be non-empty bytes without NUL")
        roles.add(role)

    source_hashes = _hashes(source)
    prepared.parent.mkdir(parents=True, exist_ok=True)
    if prepared.parent.is_symlink():
        raise ValueError("preparedRoot parent must not be a symlink")
    prepared.mkdir()
    try:
        shutil.copytree(source, prepared, copy_function=shutil.copy2, dirs_exist_ok=True)
        directories = (prepared, *sorted(path for path in prepared.rglob("*") if path.is_dir()))
        for directory in directories:
            directory.chmod(directory.stat().st_mode | stat.S_IRWXU)
        for role, payload in patches:
            for check in (True, False):
                command = ["git", "apply", "--no-index", "--whitespace=nowarn"]
                if check:
                    command.append("--check")
                completed = run(
                    command,
                    cwd=prepared,
                    env={**os.environ, "GIT_CEILING_DIRECTORIES": str(prepared.parent)},
                    input=payload, stdout=PIPE, stderr=PIPE,
                )
                if completed.returncode:
                    detail = completed.stderr.decode("utf-8", errors="replace").strip()
                    raise ValueError(f"{role} patch does not apply exactly: {detail}")
        prepared_hashes = _hashes(prepared)
        changed = sorted(
            path for path in set(source_hashes) | set(prepared_hashes)
            if source_hashes.get(path) != prepared_hashes.get(path)
        )
        if not changed:
            raise ValueError("patch set produced no changed paths")
        for path in sorted((prepared, *prepared.rglob("*")), key=lambda item: len(item.parts), reverse=True):
            path.chmod(path.stat().st_mode & ~0o222)
    except BaseException as primary:
        try:
            _remove(prepared)
        except BaseException as cleanup:
            raise RuntimeError(f"preparation failed: {primary}; cleanup failed: {cleanup}") from cleanup
        raise
    return {
        "canonicalBase": _identity(source_hashes),
        "preparedInput": _identity(prepared_hashes),
        "patches": [{"role": role, "sha256": _sha(payload)} for role, payload in patches],
        "changedPaths": changed,
    }
