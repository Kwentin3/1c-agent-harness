#!/usr/bin/env python3
"""Open this repository's declared 1C configuration as an admitted SnapshotRef."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import uuid

from cf_materializer import MaterializationFailed, MaterializerUnavailable, materialize_cf
from target_admission import (
    TargetBlocked, admit_snapshot, admit_target, binding_bytes, freeze, load_contract,
    manifest_entries, paths, remove_owned, repo_path, require_one_link, sha256,
    snapshot_ref, source_identity, tree_manifest,
)


def _source(repo_root: Path, contract: dict[str, object]) -> Path:
    source = contract["source"]
    assert isinstance(source, dict)
    path = repo_path(repo_root, source["path"], field="source path")
    if not path.exists():
        raise TargetBlocked("source_missing", "declared source does not exist")
    if source["kind"] == "cf":
        if path.is_symlink() or not path.is_file():
            raise TargetBlocked("source_mismatch", "declared CF source is not a regular file")
        require_one_link(path)
        if sha256(path) != source["sha256"]:
            raise TargetBlocked("source_mismatch", "declared CF source identity mismatch")
    else:
        try:
            manifest = tree_manifest(path)
        except Exception as exc:
            raise TargetBlocked("source_mismatch", "declared hierarchical source failed validation") from exc
        if (len(manifest_entries(manifest)) != source["fileCount"] or
                hashlib.sha256(manifest).hexdigest() != str(source["contentId"])[7:]):
            raise TargetBlocked("source_mismatch", "declared hierarchical source identity mismatch")
    return path


def _source_unchanged(source: Path, contract: dict[str, object]) -> None:
    definition = contract["source"]
    assert isinstance(definition, dict)
    actual = sha256(source) if definition["kind"] == "cf" else hashlib.sha256(tree_manifest(source)).hexdigest()
    expected = definition["sha256"] if definition["kind"] == "cf" else str(definition["contentId"])[7:]
    if actual != expected:
        raise TargetBlocked("source_mismatch", "declared source changed during open")


def open_target(repo_root: Path) -> dict[str, object]:
    try:
        contract, contract_bytes = load_contract(repo_root)
        base, target, snapshot, manifest, binding = paths(repo_root, contract)
        base.mkdir(parents=True, exist_ok=True)
        if base.is_symlink():
            raise ValueError("retained target base is invalid")
        fd = os.open(base, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            if (repo_root / "project-target.json").read_bytes() != contract_bytes:
                raise TargetBlocked("snapshot_invalid", "project target contract changed during open")
            if os.path.lexists(target):
                try:
                    admit_target(target, snapshot, manifest, binding, contract)
                except Exception as exc:
                    raise TargetBlocked("snapshot_invalid", "retained snapshot failed admission") from exc
                return snapshot_ref(contract, "reused")
            source = _source(repo_root, contract)
            staging = base / f".{target.name}.staging-{uuid.uuid4().hex}"
            staging.mkdir()
            staged_snapshot, staged_manifest, staged_binding = staging / snapshot.name, staging / manifest.name, staging / binding.name
            work = staging / "work"
            try:
                definition = contract["source"]
                assert isinstance(definition, dict)
                if definition["kind"] == "hierarchical":
                    shutil.copytree(source, staged_snapshot, copy_function=shutil.copy2)
                else:
                    try:
                        materialize_cf(repo_root=repo_root, source=source, output=staged_snapshot, work_root=work)
                    except MaterializerUnavailable as exc:
                        raise TargetBlocked("materializer_unavailable", "1C training runtime is unavailable", locator="docs/lab-bootstrap.md") from exc
                    except MaterializationFailed as exc:
                        raise TargetBlocked("materialization_failed", "CF materialization failed") from exc
                remove_owned(work)
                generated = tree_manifest(staged_snapshot)
                expected = contract["snapshot"]
                assert isinstance(expected, dict)
                if hashlib.sha256(generated).hexdigest() != str(expected["contentId"])[7:] or len(manifest_entries(generated)) != expected["fileCount"]:
                    raise TargetBlocked("source_mismatch" if definition["kind"] == "hierarchical" else "materialization_failed", "materialized snapshot identity mismatch")
                _source_unchanged(source, contract)
                staged_manifest.write_bytes(generated)
                staged_binding.write_bytes(binding_bytes(contract))
                freeze(staged_snapshot, staged_manifest, staged_binding)
                admit_target(staging, staged_snapshot, staged_manifest, staged_binding, contract)
                if (repo_root / "project-target.json").read_bytes() != contract_bytes:
                    raise TargetBlocked("snapshot_invalid", "project target contract changed during open")
                staging.rename(target)
                admit_target(target, snapshot, manifest, binding, contract)
                return snapshot_ref(contract, "materialized")
            except BaseException:
                remove_owned(staging)
                raise
        finally:
            os.close(fd)
    except TargetBlocked:
        raise
    except Exception as exc:
        raise TargetBlocked("snapshot_invalid", "project target contract or retained snapshot is invalid") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", default="open", choices=("open",))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        result = open_target(args.repo_root.resolve())
    except TargetBlocked as exc:
        result: dict[str, object] = {"schemaVersion": 1, "status": "blocked", "reasonCode": exc.reason_code, "message": exc.message}
        if exc.locator: result["locator"] = exc.locator
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
