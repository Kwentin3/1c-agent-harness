#!/usr/bin/env python3
"""Verify this repository's one declared 1C target before native work."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _one_child(element: ET.Element, name: str) -> ET.Element:
    matches = [child for child in element if _local_name(child.tag) == name]
    if len(matches) != 1:
        raise ValueError(f"Configuration.xml must contain exactly one {name} at the declared locator")
    return matches[0]


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _repo_path(repo_root: Path, value: object, *, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty repository-relative path")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{field} must stay within repository")
    current = repo_root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"{field} contains a symlink component")
    resolved = current.resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ValueError(f"{field} must stay within repository") from exc
    return resolved


def _require_single_link(path: Path, *, field: str) -> None:
    if path.stat().st_nlink != 1:
        raise ValueError(f"{field} must have exactly one hard link")


def _manifest_entries(payload: bytes) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line_number, line in enumerate(payload.decode("utf-8").splitlines(), 1):
        digest, separator, relative = line.partition("  ")
        if (
            separator != "  "
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            or not relative
            or relative.startswith("/")
            or ".." in Path(relative).parts
        ):
            raise ValueError(f"invalid snapshot manifest line: {line_number}")
        if relative in entries:
            raise ValueError(f"duplicate snapshot manifest path: {relative}")
        entries[relative] = digest
    return entries


def _verify_snapshot(snapshot: Path, manifest_entries: dict[str, str], expected_count: int) -> int:
    snapshot_entries = list(snapshot.rglob("*"))
    for path in snapshot_entries:
        relative = path.relative_to(snapshot).as_posix()
        if path.is_symlink():
            raise ValueError(f"snapshot contains symlink: {relative}")
        if not path.is_dir() and not path.is_file():
            raise ValueError(f"snapshot contains non-regular entry: {relative}")
        if path.is_file() and path.stat().st_nlink != 1:
            raise ValueError(f"snapshot contains multiply-linked file: {relative}")
    snapshot_files = {
        path.relative_to(snapshot).as_posix(): path
        for path in snapshot_entries
        if path.is_file()
    }
    file_count = len(snapshot_files)
    if file_count != expected_count:
        raise ValueError(
            f"snapshot file count mismatch: expected {expected_count}, got {file_count}"
        )
    if set(snapshot_files) != set(manifest_entries):
        raise ValueError("snapshot paths do not match manifest")
    for relative, path in sorted(snapshot_files.items()):
        if _sha256(path) != manifest_entries[relative]:
            raise ValueError(f"snapshot content mismatch: {relative}")
    return file_count


def verify(repo_root: Path) -> dict[str, object]:
    contract_path = _repo_path(
        repo_root,
        "project-target.json",
        field="project-target.json",
    )
    _require_single_link(contract_path, field="project-target.json")
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(
        contract_bytes.decode("utf-8"),
        object_pairs_hook=_unique_json_object,
    )
    expected_keys = {
        "schemaVersion", "configuration", "sourceCf", "snapshot", "dailyNativeRoute"
    }
    if not isinstance(contract, dict) or set(contract) != expected_keys:
        raise ValueError(
            "contract keys mismatch: expected configuration, dailyNativeRoute, schemaVersion, snapshot, sourceCf"
        )
    schema_version = contract["schemaVersion"]
    if type(schema_version) is not int:
        raise ValueError("schemaVersion must be integer 1")
    if schema_version != 1:
        raise ValueError(f"unsupported schemaVersion: {schema_version}")
    nested_shapes = {
        "configuration": {"name", "version"},
        "sourceCf": {"path", "sha256"},
        "snapshot": {"path", "manifestPath", "manifestSha256", "fileCount"},
    }
    for field, keys in nested_shapes.items():
        value = contract[field]
        if not isinstance(value, dict) or set(value) != keys:
            raise ValueError(f"{field} keys mismatch: expected {', '.join(sorted(keys))}")
    file_count_contract = contract["snapshot"]["fileCount"]
    if type(file_count_contract) is not int or file_count_contract < 1:
        raise ValueError("snapshot.fileCount must be a positive integer")
    if contract["dailyNativeRoute"] != "scripts/shared_task_route.py run":
        raise ValueError("dailyNativeRoute must be scripts/shared_task_route.py run")
    source = _repo_path(repo_root, contract["sourceCf"]["path"], field="sourceCf.path")
    snapshot = _repo_path(repo_root, contract["snapshot"]["path"], field="snapshot.path")
    manifest = _repo_path(
        repo_root,
        contract["snapshot"]["manifestPath"],
        field="snapshot.manifestPath",
    )
    _require_single_link(source, field="source CF")
    _require_single_link(manifest, field="snapshot manifest")

    source_actual = _sha256(source)
    if source_actual != contract["sourceCf"]["sha256"]:
        raise ValueError("source CF SHA-256 mismatch")
    manifest_bytes = manifest.read_bytes()
    manifest_actual = hashlib.sha256(manifest_bytes).hexdigest()
    if manifest_actual != contract["snapshot"]["manifestSha256"]:
        raise ValueError("snapshot manifest SHA-256 mismatch")
    manifest_entries = _manifest_entries(manifest_bytes)
    file_count = _verify_snapshot(snapshot, manifest_entries, file_count_contract)

    configuration_bytes = (snapshot / "Configuration.xml").read_bytes()
    if hashlib.sha256(configuration_bytes).hexdigest() != manifest_entries["Configuration.xml"]:
        raise ValueError("snapshot content mismatch: Configuration.xml")
    root = ET.fromstring(configuration_bytes)
    configuration = _one_child(root, "Configuration")
    properties = _one_child(configuration, "Properties")
    name = _one_child(properties, "Name").text or ""
    version = _one_child(properties, "Version").text or ""
    actual_configuration = {"name": name, "version": version}
    if actual_configuration != contract["configuration"]:
        raise ValueError("configuration name/version mismatch")

    if contract_path.read_bytes() != contract_bytes:
        raise ValueError("project target contract changed during verification")
    if _sha256(source) != source_actual:
        raise ValueError("source CF changed during verification")
    final_manifest_bytes = manifest.read_bytes()
    if final_manifest_bytes != manifest_bytes:
        raise ValueError("snapshot manifest changed during verification")
    final_manifest_entries = _manifest_entries(final_manifest_bytes)
    if final_manifest_entries != manifest_entries:
        raise ValueError("snapshot manifest entries changed during verification")
    _verify_snapshot(snapshot, final_manifest_entries, file_count_contract)

    return {
        "status": "ready",
        "configuration": actual_configuration,
        "sourceCf": {
            "path": contract["sourceCf"]["path"],
            "expectedSha256": contract["sourceCf"]["sha256"],
            "actualSha256": source_actual,
        },
        "snapshot": {
            "path": contract["snapshot"]["path"],
            "manifestPath": contract["snapshot"]["manifestPath"],
            "expectedManifestSha256": contract["snapshot"]["manifestSha256"],
            "actualManifestSha256": manifest_actual,
            "expectedFileCount": contract["snapshot"]["fileCount"],
            "actualFileCount": file_count,
        },
        "dailyNativeRoute": contract["dailyNativeRoute"],
    }


class TargetBlocked(Exception):
    def __init__(self, reason_code: str, message: str, *, locator: str | None = None) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.message = message
        self.locator = locator


def _digest_value(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        raise ValueError(f"{field} must be sha256:<64 lowercase hex characters>")
    digest = value.removeprefix("sha256:")
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError(f"{field} must be sha256:<64 lowercase hex characters>")
    return digest


def _load_open_contract(repo_root: Path) -> tuple[dict[str, object], bytes]:
    contract_path = _repo_path(repo_root, "project-target.json", field="project-target.json")
    _require_single_link(contract_path, field="project-target.json")
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(
        contract_bytes.decode("utf-8"), object_pairs_hook=_unique_json_object
    )
    expected_keys = {
        "schemaVersion", "configuration", "source", "snapshot", "dailyNativeRoute"
    }
    if not isinstance(contract, dict) or set(contract) != expected_keys:
        raise ValueError(
            "contract keys mismatch: expected configuration, dailyNativeRoute, schemaVersion, snapshot, source"
        )
    if type(contract["schemaVersion"]) is not int or contract["schemaVersion"] != 2:
        raise ValueError("open requires project-target schemaVersion 2")
    configuration = contract["configuration"]
    if not isinstance(configuration, dict) or set(configuration) != {"name", "version"}:
        raise ValueError("configuration keys mismatch: expected name, version")
    if not all(isinstance(configuration[key], str) for key in ("name", "version")):
        raise ValueError("configuration name and version must be strings")
    if not all(configuration[key] for key in ("name", "version")):
        raise ValueError("configuration name and version must be non-empty")
    snapshot = contract["snapshot"]
    if not isinstance(snapshot, dict) or set(snapshot) != {
        "root", "manifest", "contentId", "fileCount"
    }:
        raise ValueError("snapshot keys mismatch: expected contentId, fileCount, manifest, root")
    _digest_value(snapshot["contentId"], field="snapshot.contentId")
    if type(snapshot["fileCount"]) is not int or snapshot["fileCount"] < 1:
        raise ValueError("snapshot.fileCount must be a positive integer")
    source = contract["source"]
    if not isinstance(source, dict) or not isinstance(source.get("kind"), str):
        raise ValueError("source.kind must be a string")
    kind = source["kind"]
    if kind == "cf":
        if set(source) != {"kind", "path", "sha256"}:
            raise ValueError("cf source keys mismatch: expected kind, path, sha256")
        _digest_value(f"sha256:{source['sha256']}", field="source.sha256")
    elif kind == "hierarchical":
        if set(source) != {"kind", "path", "contentId", "fileCount"}:
            raise ValueError(
                "hierarchical source keys mismatch: expected contentId, fileCount, kind, path"
            )
        _digest_value(source["contentId"], field="source.contentId")
        if type(source["fileCount"]) is not int or source["fileCount"] < 1:
            raise ValueError("source.fileCount must be a positive integer")
    else:
        raise TargetBlocked("unsupported_source", "source kind is unsupported")
    if contract["dailyNativeRoute"] != "scripts/shared_task_route.py run":
        raise ValueError("dailyNativeRoute must be scripts/shared_task_route.py run")
    return contract, contract_bytes


def _tree_manifest(root: Path) -> bytes:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("tree must be a non-symlink directory")
    entries: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise ValueError(f"tree contains symlink: {relative}")
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode):
            raise ValueError(f"tree contains non-regular entry: {relative}")
        if path.stat().st_nlink != 1:
            raise ValueError(f"tree contains multiply-linked file: {relative}")
        entries.append((relative, _sha256(path)))
    return "".join(f"{digest}  {relative}\n" for relative, digest in entries).encode("utf-8")


def _admit_snapshot(
    snapshot: Path,
    manifest: Path,
    *,
    expected_content_id: str,
    expected_count: int,
    expected_configuration: dict[str, object],
    require_read_only: bool,
) -> dict[str, object]:
    if snapshot.is_symlink() or not snapshot.is_dir():
        raise ValueError("snapshot root must be a non-symlink directory")
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError("snapshot manifest must be a non-symlink regular file")
    _require_single_link(manifest, field="snapshot manifest")
    manifest_bytes = manifest.read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != expected_content_id:
        raise ValueError("snapshot manifest SHA-256 mismatch")
    entries = _manifest_entries(manifest_bytes)
    file_count = _verify_snapshot(snapshot, entries, expected_count)
    configuration_path = snapshot / "Configuration.xml"
    if "Configuration.xml" not in entries or not configuration_path.is_file():
        raise ValueError("snapshot Configuration.xml is missing")
    root = ET.fromstring(configuration_path.read_bytes())
    configuration = _one_child(root, "Configuration")
    properties = _one_child(configuration, "Properties")
    actual_configuration = {
        "name": _one_child(properties, "Name").text or "",
        "version": _one_child(properties, "Version").text or "",
    }
    if actual_configuration != expected_configuration:
        raise ValueError("configuration name/version mismatch")
    if require_read_only:
        for path in (snapshot, manifest, *snapshot.rglob("*")):
            if path.lstat().st_mode & 0o222:
                relative = path.name if path == manifest else path.relative_to(snapshot).as_posix()
                raise ValueError(f"retained snapshot entry is writable: {relative}")
    final_manifest_bytes = manifest.read_bytes()
    if final_manifest_bytes != manifest_bytes:
        raise ValueError("snapshot manifest changed during admission")
    _verify_snapshot(snapshot, _manifest_entries(final_manifest_bytes), expected_count)
    return {"configuration": actual_configuration, "fileCount": file_count}


def _source_binding(source_identity: str, content_id: object) -> bytes:
    return (
        json.dumps(
            {
                "schemaVersion": 1,
                "snapshotContentId": content_id,
                "sourceIdentity": source_identity,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _admit_binding(
    target: Path,
    snapshot: Path,
    manifest: Path,
    binding: Path,
    expected: bytes,
) -> None:
    expected_entries = {snapshot.name, manifest.name, binding.name}
    if target.is_symlink() or not target.is_dir():
        raise ValueError("retained target must be a non-symlink directory")
    if {path.name for path in target.iterdir()} != expected_entries:
        raise ValueError("retained target entries do not match its closed contract")
    if binding.is_symlink() or not binding.is_file():
        raise ValueError("retained source binding must be a non-symlink regular file")
    _require_single_link(binding, field="retained source binding")
    if binding.read_bytes() != expected:
        raise ValueError("retained source identity binding mismatch")
    if binding.lstat().st_mode & 0o222:
        raise ValueError("retained source identity binding is writable")


def _freeze_snapshot(snapshot: Path, manifest: Path, binding: Path) -> None:
    for path in sorted((snapshot, *snapshot.rglob("*")), key=lambda item: len(item.parts), reverse=True):
        path.chmod(path.lstat().st_mode & ~0o222)
    manifest.chmod(manifest.lstat().st_mode & ~0o222)
    binding.chmod(binding.lstat().st_mode & ~0o222)


def _remove_staging(path: Path) -> None:
    if not path.exists():
        return
    if path.is_symlink() or not path.is_dir():
        raise RuntimeError("staging cleanup target is not a directory")
    for candidate in (path, *path.rglob("*")):
        mode = candidate.lstat().st_mode
        if stat.S_ISDIR(mode):
            candidate.chmod(mode | stat.S_IRWXU)
        elif stat.S_ISREG(mode):
            candidate.chmod(mode | stat.S_IRUSR | stat.S_IWUSR)
        else:
            raise RuntimeError("staging cleanup target contains a special entry")
    shutil.rmtree(path)


def _run_materializer(capability: Path, source: Path, output: Path, work_root: Path) -> None:
    work_root.mkdir(parents=True)
    environment = os.environ.copy()
    environment.update({
        "HOME": str(work_root / "home"),
        "TMPDIR": str(work_root / "tmp"),
        "XDG_CACHE_HOME": str(work_root / "xdg-cache"),
        "XDG_CONFIG_HOME": str(work_root / "xdg-config"),
        "XDG_DATA_HOME": str(work_root / "xdg-data"),
    })
    for value in environment.values():
        if value.startswith(str(work_root)):
            Path(value).mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        [
            str(capability),
            "--source", str(source),
            "--output", str(output),
            "--work-root", str(work_root),
        ],
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    timed_out = False
    try:
        process.communicate(timeout=900)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
    lingering = False
    try:
        os.killpg(process.pid, 0)
        lingering = True
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    if timed_out:
        raise RuntimeError("materializer timed out")
    if process.returncode != 0:
        raise RuntimeError(f"materializer exited with code {process.returncode}")
    if lingering:
        raise RuntimeError("materializer left a running process")


def _ready_result(
    contract: dict[str, object], *, action: str, source_identity: str
) -> dict[str, object]:
    snapshot = contract["snapshot"]
    assert isinstance(snapshot, dict)
    configuration = contract["configuration"]
    assert isinstance(configuration, dict)
    return {
        "schemaVersion": 1,
        "status": "ready",
        "action": action,
        "sourceIdentity": source_identity,
        "snapshot": {
            "kind": "1c-configuration-files",
            "format": "hierarchical",
            "root": snapshot["root"],
            "manifest": snapshot["manifest"],
            "contentId": snapshot["contentId"],
            "fileCount": snapshot["fileCount"],
            "configuration": configuration,
        },
    }


def open_target(repo_root: Path) -> dict[str, object]:
    try:
        contract, contract_bytes = _load_open_contract(repo_root)
        source_contract = contract["source"]
        snapshot_contract = contract["snapshot"]
        configuration = contract["configuration"]
        assert isinstance(source_contract, dict)
        assert isinstance(snapshot_contract, dict)
        assert isinstance(configuration, dict)
        source_kind = source_contract["kind"]
        source_identity = (
            f"sha256:{source_contract['sha256']}"
            if source_kind == "cf"
            else str(source_contract["contentId"])
        )
        snapshot = _repo_path(repo_root, snapshot_contract["root"], field="snapshot.root")
        manifest = _repo_path(repo_root, snapshot_contract["manifest"], field="snapshot.manifest")
        retained_base = repo_root / ".local/targets"
        if snapshot.parent != manifest.parent or snapshot.parent.parent != retained_base:
            raise ValueError("snapshot root and manifest must share one retained target under .local/targets")
        target = snapshot.parent
        binding = target / "source.json"
        if len({snapshot.name, manifest.name, binding.name}) != 3:
            raise ValueError("snapshot root, manifest and source binding names must be distinct")
        binding_bytes = _source_binding(source_identity, snapshot_contract["contentId"])
        expected_content_id = _digest_value(
            snapshot_contract["contentId"], field="snapshot.contentId"
        )
        expected_count = snapshot_contract["fileCount"]
        assert isinstance(expected_count, int)

        retained_base.mkdir(parents=True, exist_ok=True)
        if retained_base.is_symlink():
            raise ValueError(".local/targets must not be a symlink")
        lock_fd = os.open(
            retained_base,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            if (repo_root / "project-target.json").read_bytes() != contract_bytes:
                raise TargetBlocked("snapshot_invalid", "project target contract changed during open")
            if os.path.lexists(target):
                try:
                    _admit_snapshot(
                        snapshot,
                        manifest,
                        expected_content_id=expected_content_id,
                        expected_count=expected_count,
                        expected_configuration=configuration,
                        require_read_only=True,
                    )
                    _admit_binding(target, snapshot, manifest, binding, binding_bytes)
                except Exception as exc:
                    raise TargetBlocked(
                        "snapshot_invalid", "retained snapshot failed admission"
                    ) from exc
                if (repo_root / "project-target.json").read_bytes() != contract_bytes:
                    raise TargetBlocked("snapshot_invalid", "project target contract changed during open")
                return _ready_result(
                    contract, action="reused", source_identity=source_identity
                )

            source = _repo_path(repo_root, source_contract["path"], field="source.path")
            if not source.exists():
                raise TargetBlocked("source_missing", "declared source does not exist")
            if source == target or source in target.parents or target in source.parents:
                raise ValueError("source and retained target must be disjoint")
            if source_kind == "cf":
                if source.is_symlink() or not source.is_file():
                    raise TargetBlocked("source_mismatch", "declared CF source is not a regular file")
                _require_single_link(source, field="source CF")
                if _sha256(source) != source_contract["sha256"]:
                    raise TargetBlocked("source_mismatch", "declared CF SHA-256 mismatch")
                source_before = source_contract["sha256"]
            else:
                try:
                    source_manifest = _tree_manifest(source)
                except Exception as exc:
                    raise TargetBlocked(
                        "source_mismatch", "declared hierarchical source failed validation"
                    ) from exc
                if len(_manifest_entries(source_manifest)) != source_contract["fileCount"]:
                    raise TargetBlocked("source_mismatch", "hierarchical source file count mismatch")
                if hashlib.sha256(source_manifest).hexdigest() != _digest_value(
                    source_contract["contentId"], field="source.contentId"
                ):
                    raise TargetBlocked("source_mismatch", "hierarchical source content identity mismatch")
                source_before = hashlib.sha256(source_manifest).hexdigest()

            staging = retained_base / f".{target.name}.staging-{uuid.uuid4().hex}"
            staging.mkdir()
            staged_snapshot = staging / snapshot.name
            staged_manifest = staging / manifest.name
            staged_binding = staging / binding.name
            try:
                if source_kind == "hierarchical":
                    shutil.copytree(source, staged_snapshot, copy_function=shutil.copy2)
                else:
                    try:
                        capability = _repo_path(
                            repo_root,
                            ".local/capabilities/cf_to_hierarchical_snapshot",
                            field="cf_to_hierarchical_snapshot capability",
                        )
                    except Exception as exc:
                        raise TargetBlocked(
                            "materializer_unavailable",
                            "local cf_to_hierarchical_snapshot capability is unavailable",
                            locator="docs/lab-bootstrap.md",
                        ) from exc
                    if (
                        not capability.is_file()
                        or capability.is_symlink()
                        or not os.access(capability, os.X_OK)
                    ):
                        raise TargetBlocked(
                            "materializer_unavailable",
                            "local cf_to_hierarchical_snapshot capability is unavailable",
                            locator="docs/lab-bootstrap.md",
                        )
                    _require_single_link(capability, field="cf_to_hierarchical_snapshot capability")
                    try:
                        _run_materializer(capability, source, staged_snapshot, staging / "work")
                    except Exception as exc:
                        raise TargetBlocked("materialization_failed", str(exc)) from exc
                    _remove_staging(staging / "work")

                generated_manifest = _tree_manifest(staged_snapshot)
                generated_id = hashlib.sha256(generated_manifest).hexdigest()
                generated_count = len(_manifest_entries(generated_manifest))
                if generated_id != expected_content_id or generated_count != expected_count:
                    reason = "source_mismatch" if source_kind == "hierarchical" else "materialization_failed"
                    raise TargetBlocked(reason, "materialized snapshot does not match declared identity")
                try:
                    source_after = (
                        _sha256(source)
                        if source_kind == "cf"
                        else hashlib.sha256(_tree_manifest(source)).hexdigest()
                    )
                except Exception as exc:
                    raise TargetBlocked("source_mismatch", "declared source changed during open") from exc
                if source_after != source_before:
                    raise TargetBlocked("source_mismatch", "declared source changed during open")
                staged_manifest.write_bytes(generated_manifest)
                staged_binding.write_bytes(binding_bytes)
                _freeze_snapshot(staged_snapshot, staged_manifest, staged_binding)
                _admit_snapshot(
                    staged_snapshot,
                    staged_manifest,
                    expected_content_id=expected_content_id,
                    expected_count=expected_count,
                    expected_configuration=configuration,
                    require_read_only=True,
                )
                _admit_binding(
                    staging,
                    staged_snapshot,
                    staged_manifest,
                    staged_binding,
                    binding_bytes,
                )
                if (repo_root / "project-target.json").read_bytes() != contract_bytes:
                    raise TargetBlocked("snapshot_invalid", "project target contract changed during open")
                staging.rename(target)
            except BaseException as primary:
                try:
                    _remove_staging(staging)
                except BaseException as cleanup:
                    raise TargetBlocked(
                        "materialization_failed",
                        "materialization failed and staging cleanup failed",
                    ) from primary
                if isinstance(primary, (KeyboardInterrupt, SystemExit, TargetBlocked)):
                    raise
                reason = "source_mismatch" if source_kind == "hierarchical" else "materialization_failed"
                raise TargetBlocked(reason, "materialized snapshot failed admission") from primary

            _admit_snapshot(
                snapshot,
                manifest,
                expected_content_id=expected_content_id,
                expected_count=expected_count,
                expected_configuration=configuration,
                require_read_only=True,
            )
            _admit_binding(target, snapshot, manifest, binding, binding_bytes)
            return _ready_result(
                contract, action="materialized", source_identity=source_identity
            )
        finally:
            os.close(lock_fd)
    except TargetBlocked:
        raise
    except Exception as exc:
        raise TargetBlocked(
            "snapshot_invalid", "project target contract or retained snapshot is invalid"
        ) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("open",))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    if args.command == "open":
        try:
            result = open_target(repo_root)
        except TargetBlocked as exc:
            result = {
                "schemaVersion": 1,
                "status": "blocked",
                "reasonCode": exc.reason_code,
                "message": exc.message,
            }
            if exc.locator is not None:
                result["locator"] = exc.locator
            print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            return 1
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0
    try:
        result = verify(repo_root)
    except Exception as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
