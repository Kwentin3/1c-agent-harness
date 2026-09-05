#!/usr/bin/env python3
"""Client-neutral, read-only evidence harness for 1C snapshot experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
import sys
from typing import Any, Iterable


class ContractError(RuntimeError):
    pass


def is_json_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def strict_json_loads(data: str) -> Any:
    def object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ContractError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_non_finite(value: str) -> Any:
        raise ContractError(f"non-finite JSON number is not allowed: {value}")

    return json.loads(
        data,
        object_pairs_hook=object_without_duplicates,
        parse_constant=reject_non_finite,
    )


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _stable_stat_key(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _open_path_fd(path: Path, *, directory: bool, label: str) -> int:
    absolute = path.absolute()
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    directory_flags = flags | getattr(os, "O_DIRECTORY", 0)
    fd = os.open(absolute.anchor, directory_flags)
    try:
        for index, part in enumerate(absolute.parts[1:]):
            next_fd = os.open(part, directory_flags if index < len(absolute.parts[1:]) - 1 or directory else flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        mode = os.fstat(fd).st_mode
        if directory and not stat.S_ISDIR(mode):
            raise ContractError(f"{label} is not a directory: {path}")
        if not directory and not stat.S_ISREG(mode):
            raise ContractError(f"{label} is not a regular file: {path}")
        return fd
    except (OSError, ContractError) as exc:
        os.close(fd)
        if isinstance(exc, ContractError):
            raise
        raise ContractError(f"cannot safely open {label}: {path}: {exc}") from exc


def _read_fd_stable(fd: int, label: str) -> bytes:
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode):
        raise ContractError(f"{label} is not a regular file")
    os.lseek(fd, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while True:
        chunk = os.read(fd, 1024 * 1024)
        if not chunk:
            break
        chunks.append(chunk)
    after = os.fstat(fd)
    if _stable_stat_key(before) != _stable_stat_key(after):
        raise ContractError(f"{label} changed while it was read")
    return b"".join(chunks)


def read_file_stable_identity(path: Path, label: str) -> tuple[bytes, tuple[int, int, int, int, int, int]]:
    fd = _open_path_fd(path, directory=False, label=label)
    try:
        data = _read_fd_stable(fd, label)
        return data, _stable_stat_key(os.fstat(fd))
    finally:
        os.close(fd)


def read_file_stable(path: Path, label: str) -> bytes:
    return read_file_stable_identity(path, label)[0]


def verify_path_identity(path: Path, expected: tuple[int, int, int, int, int, int], label: str) -> None:
    fd = _open_path_fd(path, directory=False, label=label)
    try:
        if _stable_stat_key(os.fstat(fd)) != expected:
            raise ContractError(f"{label} pathname identity changed: {path}")
    finally:
        os.close(fd)


def _open_relative_fd(root_fd: int, rel: PurePosixPath, *, directory: bool, label: str) -> int:
    fd = os.dup(root_fd)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    directory_flags = flags | getattr(os, "O_DIRECTORY", 0)
    try:
        for index, part in enumerate(rel.parts):
            next_fd = os.open(part, directory_flags if index < len(rel.parts) - 1 or directory else flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except OSError as exc:
        os.close(fd)
        raise ContractError(f"cannot safely open {label}: {rel.as_posix()}: {exc}") from exc


def read_snapshot_bytes(root: Path, rel: PurePosixPath, expected_sha256: str, label: str) -> bytes:
    root_fd = _open_path_fd(root, directory=True, label="snapshot root")
    try:
        fd = _open_relative_fd(root_fd, rel, directory=False, label=label)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ContractError(f"{label} must be a regular file with one link: {rel.as_posix()}")
            data = _read_fd_stable(fd, label)
        finally:
            os.close(fd)
    finally:
        os.close(root_fd)
    if digest_bytes(data) != expected_sha256:
        raise ContractError(f"{label} no longer matches admitted snapshot bytes: {rel.as_posix()}")
    return data


def read_json_hashed(path: Path, label: str) -> tuple[dict[str, Any], str]:
    try:
        data = read_file_stable(path, label)
        value = strict_json_loads(data.decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError, ContractError) as exc:
        raise ContractError(f"invalid {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be a JSON object")
    return value, digest_bytes(data)


def read_json(path: Path, label: str) -> dict[str, Any]:
    return read_json_hashed(path, label)[0]


def reject_symlink_path(path: Path, label: str) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            return
        if stat.S_ISLNK(mode):
            raise ContractError(f"{label} contains a symlink: {current}")


def resolved_path(base: Path, raw: Any, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ContractError(f"{label} must be a non-empty path string")
    path = Path(raw)
    if not path.is_absolute():
        path = base / path
    return Path(os.path.abspath(path))


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def require_keys(value: dict[str, Any], keys: Iterable[str], label: str) -> None:
    if any(not isinstance(key, str) for key in value):
        raise ContractError(f"{label} keys must be strings")
    missing = sorted(set(keys) - value.keys())
    if missing:
        raise ContractError(f"{label} missing keys: {', '.join(missing)}")


def require_contract_keys(
    value: dict[str, Any], required: Iterable[str], allowed: Iterable[str], label: str,
) -> None:
    require_keys(value, required, label)
    unexpected = sorted(value.keys() - set(allowed))
    if unexpected:
        raise ContractError(f"{label} has unexpected keys: {', '.join(unexpected)}")


def load_experiment(path: Path) -> dict[str, Any]:
    spec = read_json(path, "experiment")
    required = ("schemaVersion", "id", "snapshot", "questions", "outputRoot", "cacheRoot", "evaluation")
    require_contract_keys(spec, required, (*required, "clients"), "experiment")
    if not is_json_integer(spec["schemaVersion"]) or spec["schemaVersion"] != 1:
        raise ContractError("unsupported experiment schemaVersion")
    if not isinstance(spec["id"], str) or re.fullmatch(r"[a-z0-9][a-z0-9._-]*", spec["id"]) is None:
        raise ContractError("experiment id must match ^[a-z0-9][a-z0-9._-]*$")
    if not isinstance(spec["snapshot"], dict) or not isinstance(spec["questions"], dict) or not isinstance(spec["evaluation"], dict):
        raise ContractError("snapshot, questions, and evaluation must be objects")
    require_contract_keys(spec["snapshot"], ("root", "manifest", "contentId"), ("root", "manifest", "contentId"), "snapshot")
    require_contract_keys(spec["questions"], ("path", "sha256"), ("path", "sha256"), "questions")
    evaluation_keys = ("minimumFactAccuracy", "maxDangerousFalseClaims", "maximumInvalidLocators")
    require_contract_keys(spec["evaluation"], evaluation_keys, evaluation_keys, "evaluation")
    minimum = spec["evaluation"]["minimumFactAccuracy"]
    dangerous = spec["evaluation"]["maxDangerousFalseClaims"]
    invalid = spec["evaluation"]["maximumInvalidLocators"]
    if not isinstance(minimum, (int, float)) or isinstance(minimum, bool) or not 0 <= minimum <= 1:
        raise ContractError("minimumFactAccuracy must be between 0 and 1")
    if not isinstance(dangerous, int) or isinstance(dangerous, bool) or dangerous < 0:
        raise ContractError("maxDangerousFalseClaims must be a non-negative integer")
    if invalid != 0 or isinstance(invalid, bool):
        raise ContractError("maximumInvalidLocators must be 0 in fail-closed schemaVersion 1")
    if "clients" in spec and (
        not isinstance(spec["clients"], list)
        or not spec["clients"]
        or any(not isinstance(client, str) or not client for client in spec["clients"])
        or len(set(spec["clients"])) != len(spec["clients"])
    ):
        raise ContractError("clients must be a non-empty array of unique strings")
    base = path.absolute().parent
    spec["_path"] = path.absolute()
    spec["_snapshotRoot"] = resolved_path(base, spec["snapshot"]["root"], "snapshot root")
    spec["_manifestPath"] = resolved_path(base, spec["snapshot"]["manifest"], "snapshot manifest")
    spec["_questionsPath"] = resolved_path(base, spec["questions"]["path"], "questions path")
    spec["_outputRoot"] = resolved_path(base, spec["outputRoot"], "outputRoot")
    spec["_cacheRoot"] = resolved_path(base, spec["cacheRoot"], "cacheRoot")
    return spec


def safe_relative(raw: str, label: str) -> PurePosixPath:
    if not isinstance(raw, str) or not raw:
        raise ContractError(f"{label} must be a non-empty relative POSIX path")
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts or "." in path.parts or "" in path.parts:
        raise ContractError(f"unsafe {label}: {raw}")
    if "\x00" in raw:
        raise ContractError(f"unsafe {label} contains NUL")
    if "?" in raw:
        raise ContractError(f"lossy {label} contains '?': {raw}")
    return path


def snapshot_inventory(root_fd: int) -> dict[str, str]:
    result: dict[str, str] = {}

    def visit(directory_fd: int, prefix: tuple[str, ...]) -> None:
        try:
            names = sorted(os.listdir(directory_fd))
        except OSError as exc:
            raise ContractError(f"cannot enumerate snapshot: {exc}") from exc
        for name in names:
            if not name or name in (".", "..") or "/" in name or "\x00" in name:
                raise ContractError("snapshot contains an unsafe directory entry")
            rel = PurePosixPath(*prefix, name)
            try:
                info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except OSError as exc:
                raise ContractError(f"cannot stat snapshot entry {rel.as_posix()}: {exc}") from exc
            if stat.S_ISLNK(info.st_mode):
                raise ContractError(f"snapshot contains a symlink: {rel.as_posix()}")
            if stat.S_ISDIR(info.st_mode):
                child_fd = _open_relative_fd(directory_fd, PurePosixPath(name), directory=True, label="snapshot directory")
                try:
                    visit(child_fd, (*prefix, name))
                finally:
                    os.close(child_fd)
            elif stat.S_ISREG(info.st_mode):
                if info.st_nlink != 1:
                    raise ContractError(f"snapshot contains a hard link: {rel.as_posix()}")
                fd = _open_relative_fd(directory_fd, PurePosixPath(name), directory=False, label="snapshot file")
                try:
                    data = _read_fd_stable(fd, f"snapshot file {rel.as_posix()}")
                    after = os.fstat(fd)
                    if after.st_nlink != 1:
                        raise ContractError(f"snapshot contains a hard link: {rel.as_posix()}")
                finally:
                    os.close(fd)
                result[rel.as_posix()] = digest_bytes(data)
            else:
                raise ContractError(f"snapshot contains a non-regular entry: {rel.as_posix()}")

    visit(root_fd, ())
    return result


def verify_snapshot(spec: dict[str, Any]) -> dict[str, Any]:
    root: Path = spec["_snapshotRoot"]
    manifest: Path = spec["_manifestPath"]
    questions: Path = spec["_questionsPath"]
    manifest_bytes = read_file_stable(manifest, "snapshot manifest")
    questions_bytes = read_file_stable(questions, "questions path")
    expected_content_id = spec["snapshot"]["contentId"]
    actual_content_id = f"sha256:{digest_bytes(manifest_bytes)}"
    if expected_content_id != actual_content_id:
        raise ContractError(f"snapshot manifest content ID mismatch: expected {expected_content_id}, got {actual_content_id}")
    expected_questions = spec["questions"]["sha256"]
    actual_questions = digest_bytes(questions_bytes)
    if expected_questions != actual_questions:
        raise ContractError(f"question set hash mismatch: expected {expected_questions}, got {actual_questions}")
    entries: dict[str, str] = {}
    try:
        lines = manifest_bytes.decode("utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ContractError(f"cannot read snapshot manifest: {exc}") from exc
    for number, line in enumerate(lines, 1):
        parts = line.split("  ", 1)
        if len(parts) != 2 or len(parts[0]) != 64 or any(c not in "0123456789abcdef" for c in parts[0]):
            raise ContractError(f"malformed snapshot manifest line {number}")
        rel = safe_relative(parts[1], f"manifest path at line {number}").as_posix()
        if rel in entries:
            raise ContractError(f"duplicate snapshot manifest path: {rel}")
        entries[rel] = parts[0]
    required_roots = {"Configuration.xml", "ConfigDumpInfo.xml"}
    missing_roots = sorted(required_roots - entries.keys())
    if missing_roots:
        raise ContractError(f"snapshot missing required root files: {missing_roots}")
    root_fd = _open_path_fd(root, directory=True, label="snapshot root")
    try:
        inventory = snapshot_inventory(root_fd)
    finally:
        os.close(root_fd)
    actual_files = set(inventory)
    if actual_files != set(entries):
        missing = sorted(set(entries) - actual_files)[:3]
        extra = sorted(actual_files - set(entries))[:3]
        raise ContractError(f"snapshot manifest file set mismatch; missing={missing}, extra={extra}")
    for rel, expected in entries.items():
        if inventory[rel] != expected:
            raise ContractError(f"snapshot manifest hash mismatch: {rel}")
    for path, label in ((spec["_outputRoot"], "outputRoot"), (spec["_cacheRoot"], "cacheRoot")):
        reject_symlink_path(path, label)
        if is_within(path, root) or is_within(root, path):
            raise ContractError(f"{label} must be outside and disjoint from snapshot")
    try:
        questions_doc = strict_json_loads(questions_bytes.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError, ContractError) as exc:
        raise ContractError(f"invalid questions: {exc}") from exc
    if not isinstance(questions_doc, dict):
        raise ContractError("questions must be a JSON object")
    if not is_json_integer(questions_doc.get("schemaVersion")) or questions_doc.get("schemaVersion") != 1 or not isinstance(questions_doc.get("questions"), list) or not questions_doc["questions"]:
        raise ContractError("questions must contain a non-empty schemaVersion 1 question list")
    question_ids = []
    for question in questions_doc["questions"]:
        if not isinstance(question, dict) or not isinstance(question.get("id"), str) or not question["id"]:
            raise ContractError("each question must have a non-empty id")
        question_ids.append(question["id"])
    if len(set(question_ids)) != len(question_ids):
        raise ContractError("question ids must be unique")
    return {
        "snapshotRoot": str(root),
        "manifestPath": str(manifest),
        "snapshotContentId": actual_content_id,
        "snapshotFileCount": len(entries),
        "questionSetSha256": actual_questions,
        "questionIds": question_ids,
        "_manifestEntries": entries,
    }


def public_snapshot_state(state: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in state.items() if not key.startswith("_")}


def claim_ids(items: Any, label: str) -> set[str]:
    if not isinstance(items, list):
        raise ContractError(f"{label} must be an array")
    result: set[str] = set()
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"] or not isinstance(item.get("text"), str):
            raise ContractError(f"each {label} item must have string id and text")
        require_contract_keys(item, ("id", "text"), ("id", "text"), f"{label} item")
        if item["id"] in result:
            raise ContractError(f"duplicate claim id in {label}: {item['id']}")
        result.add(item["id"])
    return result


def verify_answer_doc(spec: dict[str, Any], answer_path: Path) -> dict[str, Any]:
    state = verify_snapshot(spec)
    doc, answer_sha256 = read_json_hashed(answer_path, "answer")
    answer_keys = ("schemaVersion", "experimentId", "snapshotContentId", "questionSetSha256", "client", "answers", "metrics")
    require_contract_keys(doc, answer_keys, answer_keys, "answer")
    if not is_json_integer(doc["schemaVersion"]) or doc["schemaVersion"] != 1:
        raise ContractError("unsupported answer schemaVersion")
    if doc["experimentId"] != spec["id"]:
        raise ContractError("answer experiment mismatch")
    if doc["snapshotContentId"] != state["snapshotContentId"]:
        raise ContractError("answer snapshot content ID mismatch")
    if doc["questionSetSha256"] != state["questionSetSha256"]:
        raise ContractError("answer question set hash mismatch")
    if (
        not isinstance(doc["client"], dict)
        or not isinstance(doc["client"].get("name"), str)
        or not doc["client"]["name"]
        or not isinstance(doc["client"].get("version"), str)
        or not doc["client"]["version"]
    ):
        raise ContractError("answer client must include non-empty name and version")
    require_contract_keys(doc["client"], ("name", "version"), ("name", "version"), "answer client")
    if not isinstance(doc["answers"], list):
        raise ContractError("answers must be an array")
    seen_questions: list[str] = []
    locator_count = 0
    root: Path = spec["_snapshotRoot"]
    for entry in doc["answers"]:
        if not isinstance(entry, dict):
            raise ContractError("each answer entry must be an object")
        entry_keys = ("questionId", "answer", "facts", "inferences", "assumptions", "unknowns", "locators")
        require_contract_keys(entry, entry_keys, entry_keys, "answer entry")
        if not isinstance(entry["questionId"], str) or not isinstance(entry["answer"], str):
            raise ContractError("answer questionId and answer must be strings")
        seen_questions.append(entry["questionId"])
        ids: set[str] = set()
        claims_by_kind: dict[str, set[str]] = {}
        for label in ("facts", "inferences", "assumptions", "unknowns"):
            current = claim_ids(entry[label], label)
            duplicate = ids & current
            if duplicate:
                raise ContractError(f"claim ids must be unique within an answer: {sorted(duplicate)}")
            ids |= current
            claims_by_kind[label] = current
        if not isinstance(entry["locators"], list):
            raise ContractError("locators must be an array")
        located_claim_ids: set[str] = set()
        for locator in entry["locators"]:
            if not isinstance(locator, dict):
                raise ContractError("each locator must be an object")
            locator_keys = ("path", "startLine", "endLine", "claimIds")
            require_contract_keys(locator, locator_keys, locator_keys, "locator")
            rel = safe_relative(locator["path"], "locator path")
            expected_hash = state["_manifestEntries"].get(rel.as_posix())
            if expected_hash is None:
                raise ContractError(f"locator file does not exist inside snapshot: {rel.as_posix()}")
            start, end = locator["startLine"], locator["endLine"]
            if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool) or start < 1 or end < start:
                raise ContractError(f"invalid locator line range: {rel.as_posix()}:{start}-{end}")
            try:
                locator_bytes = read_snapshot_bytes(root, rel, expected_hash, "locator file")
                line_count = len(locator_bytes.decode("utf-8-sig").splitlines())
            except (OSError, UnicodeError, ContractError) as exc:
                raise ContractError(f"locator file is not readable UTF-8 text: {rel.as_posix()}: {exc}") from exc
            if end > line_count:
                raise ContractError(f"locator line range exceeds file: {rel.as_posix()}:{start}-{end}, lines={line_count}")
            claim_ids_value = locator["claimIds"]
            if (
                not isinstance(claim_ids_value, list)
                or not claim_ids_value
                or any(not isinstance(x, str) or not x for x in claim_ids_value)
                or any(x not in ids for x in claim_ids_value)
            ):
                raise ContractError(f"locator claimIds must reference claims in the same answer: {rel.as_posix()}")
            if len(claim_ids_value) != len(set(claim_ids_value)):
                raise ContractError(f"locator claimIds must be unique: {rel.as_posix()}")
            located_claim_ids.update(claim_ids_value)
            locator_count += 1
        for label in ("facts", "inferences"):
            missing_evidence = sorted(claims_by_kind[label] - located_claim_ids)
            if missing_evidence:
                raise ContractError(f"{label} claims require at least one locator: {missing_evidence}")
    if seen_questions != state["questionIds"]:
        raise ContractError(f"answer question order/set mismatch: expected {state['questionIds']}, got {seen_questions}")
    if not isinstance(doc["metrics"], dict):
        raise ContractError("answer metrics must be an object")
    after = verify_snapshot(spec)
    if public_snapshot_state(after) != public_snapshot_state(state) or after["_manifestEntries"] != state["_manifestEntries"]:
        raise ContractError("snapshot changed while answer evidence was verified")
    return {"document": doc, "state": state, "locatorCount": locator_count, "answerSha256": answer_sha256}


def output_relative(path: Path, output_root: Path) -> PurePosixPath:
    try:
        normalized_path = Path(os.path.abspath(path))
        normalized_root = Path(os.path.abspath(output_root))
        raw = normalized_path.relative_to(normalized_root).as_posix()
    except ValueError as exc:
        raise ContractError(f"output must be inside declared outputRoot: {output_root}") from exc
    rel = safe_relative(raw, "output path")
    if len(rel.parts) < 1:
        raise ContractError("output path must name a file below outputRoot")
    return rel


def write_new_json(path: Path, value: dict[str, Any], output_root: Path) -> None:
    rel = output_relative(path, output_root)
    try:
        data = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ContractError(f"output is not strict JSON: {exc}") from exc
    root_fd = _open_path_fd(output_root, directory=True, label="outputRoot")
    parent_fd = os.dup(root_fd)
    try:
        for part in rel.parts[:-1]:
            next_fd = os.open(
                part,
                os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_DIRECTORY", 0),
                dir_fd=parent_fd,
            )
            os.close(parent_fd)
            parent_fd = next_fd
        temporary_name = f".{rel.parts[-1]}.tmp-{os.getpid()}-{secrets.token_hex(8)}"
        temporary_fd: int | None = None
        temporary_created = False
        published = False
        try:
            temporary_fd = os.open(
                temporary_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=parent_fd,
            )
            temporary_created = True
            offset = 0
            while offset < len(data):
                written = os.write(temporary_fd, data[offset:])
                if written <= 0:
                    raise OSError("short output write")
                offset += written
            os.fsync(temporary_fd)
            os.link(
                temporary_name, rel.parts[-1],
                src_dir_fd=parent_fd, dst_dir_fd=parent_fd, follow_symlinks=False,
            )
            published = True
            os.fsync(parent_fd)
        except FileExistsError as exc:
            raise ContractError(f"refusing existing output: {path}") from exc
        except OSError as exc:
            raise ContractError(f"cannot safely publish output: {path}: {exc}") from exc
        finally:
            if temporary_fd is not None:
                os.close(temporary_fd)
            if temporary_created:
                try:
                    os.unlink(temporary_name, dir_fd=parent_fd)
                except FileNotFoundError:
                    pass
                except OSError:
                    if not published:
                        raise
    except OSError as exc:
        raise ContractError(f"cannot safely open output parent: {path.parent}: {exc}") from exc
    finally:
        os.close(parent_fd)
        os.close(root_fd)


def preflight(args: argparse.Namespace) -> dict[str, Any]:
    spec = load_experiment(args.experiment)
    state = verify_snapshot(spec)
    return {"schemaVersion": 1, "status": "ok", "experimentId": spec["id"], **public_snapshot_state(state)}


def verify_answer(args: argparse.Namespace) -> dict[str, Any]:
    spec = load_experiment(args.experiment)
    checked = verify_answer_doc(spec, args.answer)
    return {
        "schemaVersion": 1,
        "status": "ok",
        "experimentId": spec["id"],
        "client": checked["document"]["client"],
        "questionCount": len(checked["document"]["answers"]),
        "locatorCount": checked["locatorCount"],
        "answerSha256": checked["answerSha256"],
        "snapshotContentId": checked["state"]["snapshotContentId"],
        "questionSetSha256": checked["state"]["questionSetSha256"],
    }


def require_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ContractError(f"{label} must be an array of non-empty strings")
    return value


def answer_locator_strings(answer: dict[str, Any]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for entry in answer["answers"]:
        result[entry["questionId"]] = {
            f"{locator['path']}:{locator['startLine']}-{locator['endLine']}"
            for locator in entry["locators"]
        }
    return result


def validate_oracle_locator(root: Path, state: dict[str, Any], raw: str) -> None:
    match = re.fullmatch(r"(.+):([1-9][0-9]*)-([1-9][0-9]*)", raw)
    if match is None:
        raise ContractError(f"invalid oracle locator: {raw}")
    rel = safe_relative(match.group(1), "oracle locator path")
    expected_hash = state["_manifestEntries"].get(rel.as_posix())
    if expected_hash is None:
        raise ContractError(f"oracle locator path is absent from snapshot manifest: {rel.as_posix()}")
    start, end = int(match.group(2)), int(match.group(3))
    if end < start:
        raise ContractError(f"invalid oracle locator line range: {raw}")
    try:
        locator_bytes = read_snapshot_bytes(root, rel, expected_hash, "oracle locator file")
        line_count = len(locator_bytes.decode("utf-8-sig").splitlines())
    except (OSError, UnicodeError, ContractError) as exc:
        raise ContractError(f"oracle locator file is not readable admitted UTF-8 text: {rel.as_posix()}: {exc}") from exc
    if end > line_count:
        raise ContractError(f"oracle locator line range exceeds file: {raw}, lines={line_count}")


def verify_oracle_ledger(
    spec: dict[str, Any], state: dict[str, Any], oracle_path: Path, ledger_path: Path,
    baseline_answer: dict[str, Any], candidate_answer: dict[str, Any],
) -> dict[str, Any]:
    oracle, oracle_sha256 = read_json_hashed(oracle_path, "oracle")
    oracle_keys = ("schemaVersion", "experimentId", "preparedBeforeRuns", "independentSources", "answers")
    require_contract_keys(oracle, oracle_keys, oracle_keys, "oracle")
    if not is_json_integer(oracle["schemaVersion"]) or oracle["schemaVersion"] != 1 or oracle["experimentId"] != spec["id"] or oracle["preparedBeforeRuns"] is not True:
        raise ContractError("oracle contract mismatch")
    if not isinstance(oracle["independentSources"], list) or any(not isinstance(source, dict) for source in oracle["independentSources"]) or not isinstance(oracle["answers"], dict):
        raise ContractError("oracle independentSources and answers must be arrays/objects")
    if list(oracle["answers"]) != state["questionIds"]:
        raise ContractError("oracle question order/set mismatch")

    oracle_items: dict[str, list[str]] = {}
    for question_id, value in oracle["answers"].items():
        if not isinstance(value, dict):
            raise ContractError(f"oracle answer {question_id} must be an object")
        required = ("expected", "locators")
        allowed = (*required, "dangerousFalseClaims")
        require_contract_keys(value, required, allowed, f"oracle answer {question_id}")
        expected = require_string_list(value["expected"], f"oracle expected items for {question_id}")
        if not expected:
            raise ContractError(f"oracle expected items for {question_id} must not be empty")
        locators = require_string_list(value["locators"], f"oracle locators for {question_id}")
        if not locators:
            raise ContractError(f"oracle locators for {question_id} must not be empty")
        for locator in locators:
            validate_oracle_locator(spec["_snapshotRoot"], state, locator)
        if "dangerousFalseClaims" in value:
            require_string_list(value["dangerousFalseClaims"], f"oracle dangerous claims for {question_id}")
        oracle_items[question_id] = expected

    ledger, ledger_sha256 = read_json_hashed(ledger_path, "adjudication ledger")
    ledger_keys = ("schemaVersion", "experimentId", "reviewer", "questions", "dangerousClaims")
    require_contract_keys(ledger, ledger_keys, ledger_keys, "adjudication ledger")
    if not is_json_integer(ledger["schemaVersion"]) or ledger["schemaVersion"] != 1 or ledger["experimentId"] != spec["id"]:
        raise ContractError("adjudication ledger contract mismatch")
    if not isinstance(ledger["reviewer"], str) or not ledger["reviewer"]:
        raise ContractError("adjudication ledger reviewer must be non-empty")
    if not isinstance(ledger["questions"], list):
        raise ContractError("adjudication ledger questions must be an array")

    locator_sets = {
        "baseline": answer_locator_strings(baseline_answer),
        "candidate": answer_locator_strings(candidate_answer),
    }
    totals = {
        "baseline": {"factsCorrect": 0, "factsTotal": 0},
        "candidate": {"factsCorrect": 0, "factsTotal": 0},
    }
    ledger_question_ids: list[str] = []
    for question in ledger["questions"]:
        if not isinstance(question, dict):
            raise ContractError("each adjudication ledger question must be an object")
        require_contract_keys(question, ("questionId", "items"), ("questionId", "items"), "adjudication ledger question")
        question_id = question["questionId"]
        if not isinstance(question_id, str) or not question_id or not isinstance(question["items"], list):
            raise ContractError("adjudication ledger questionId/items are invalid")
        ledger_question_ids.append(question_id)
        expected = oracle_items.get(question_id)
        if expected is None or len(question["items"]) != len(expected):
            raise ContractError(f"oracle/ledger item mismatch for {question_id}")
        for offset, item in enumerate(question["items"], 1):
            if not isinstance(item, dict):
                raise ContractError("each adjudication ledger item must be an object")
            require_contract_keys(item, ("index", "expected", "arms"), ("index", "expected", "arms"), "adjudication ledger item")
            if not is_json_integer(item["index"]) or item["index"] != offset or not isinstance(item["expected"], str) or item["expected"] != expected[offset - 1]:
                raise ContractError(f"oracle/ledger item mismatch for {question_id} item {offset}")
            arms = item["arms"]
            if not isinstance(arms, dict) or set(arms) != {"baseline", "candidate"}:
                raise ContractError("adjudication ledger item arms must be baseline and candidate")
            for name in ("baseline", "candidate"):
                verdict = arms[name]
                if not isinstance(verdict, dict):
                    raise ContractError(f"adjudication ledger {name} verdict must be an object")
                verdict_keys = ("correct", "rationale", "citedLocators")
                require_contract_keys(verdict, verdict_keys, verdict_keys, f"adjudication ledger {name} verdict")
                if not isinstance(verdict["correct"], bool) or not isinstance(verdict["rationale"], str) or not verdict["rationale"]:
                    raise ContractError(f"adjudication ledger {name} verdict is invalid")
                cited = require_string_list(verdict["citedLocators"], f"adjudication ledger {name} citedLocators")
                if not cited:
                    raise ContractError(f"adjudication ledger {name} citedLocators must not be empty")
                unknown = sorted(set(cited) - locator_sets[name][question_id])
                if unknown:
                    raise ContractError(f"adjudication ledger {name} cites locators absent from answer {question_id}: {unknown}")
                totals[name]["factsTotal"] += 1
                totals[name]["factsCorrect"] += int(verdict["correct"])
    if ledger_question_ids != state["questionIds"]:
        raise ContractError("adjudication ledger question order/set mismatch")

    dangerous = ledger["dangerousClaims"]
    if not isinstance(dangerous, dict) or set(dangerous) != {"baseline", "candidate"}:
        raise ContractError("adjudication ledger dangerousClaims must contain baseline and candidate")
    for name in ("baseline", "candidate"):
        value = dangerous[name]
        if not isinstance(value, dict):
            raise ContractError(f"adjudication ledger dangerousClaims {name} must be an object")
        keys = ("count", "claims", "rationale")
        require_contract_keys(value, keys, keys, f"adjudication ledger dangerousClaims {name}")
        claims = require_string_list(value["claims"], f"adjudication ledger dangerous claims for {name}")
        if not isinstance(value["count"], int) or isinstance(value["count"], bool) or value["count"] != len(claims):
            raise ContractError(f"adjudication ledger dangerous claim count mismatch for {name}")
        if not isinstance(value["rationale"], str) or not value["rationale"]:
            raise ContractError(f"adjudication ledger dangerous claim rationale is required for {name}")
        totals[name]["dangerousFalseClaims"] = value["count"]

    return {
        "oracleSha256": oracle_sha256,
        "ledgerSha256": ledger_sha256,
        "reviewer": ledger["reviewer"],
        "totals": totals,
    }


def compare(args: argparse.Namespace) -> dict[str, Any]:
    spec = load_experiment(args.experiment)
    baseline = verify_answer_doc(spec, args.baseline)
    candidate = verify_answer_doc(spec, args.candidate)
    frozen = verify_oracle_ledger(
        spec, baseline["state"], args.oracle, args.ledger,
        baseline["document"], candidate["document"],
    )
    adjudication, adjudication_sha256 = read_json_hashed(args.adjudication, "adjudication")
    adjudication_keys = ("schemaVersion", "experimentId", "identity", "arms", "reviewer")
    require_contract_keys(adjudication, adjudication_keys, adjudication_keys, "adjudication")
    if not is_json_integer(adjudication["schemaVersion"]) or adjudication["schemaVersion"] != 2 or adjudication["experimentId"] != spec["id"]:
        raise ContractError("adjudication contract mismatch")
    if not isinstance(adjudication["reviewer"], str) or not adjudication["reviewer"] or adjudication["reviewer"] != frozen["reviewer"]:
        raise ContractError("adjudication reviewer must be non-empty")
    identity = adjudication["identity"]
    identity_keys = (
        "snapshotContentId", "questionSetSha256", "oracleSha256", "ledgerSha256",
        "baselineAnswerSha256", "candidateAnswerSha256",
    )
    if not isinstance(identity, dict):
        raise ContractError("adjudication identity must be an object")
    require_contract_keys(identity, identity_keys, identity_keys, "adjudication identity")
    expected_identity = {
        "snapshotContentId": baseline["state"]["snapshotContentId"],
        "questionSetSha256": baseline["state"]["questionSetSha256"],
        "oracleSha256": frozen["oracleSha256"],
        "ledgerSha256": frozen["ledgerSha256"],
        "baselineAnswerSha256": baseline["answerSha256"],
        "candidateAnswerSha256": candidate["answerSha256"],
    }
    if identity != expected_identity:
        mismatches = sorted(key for key in identity_keys if identity.get(key) != expected_identity[key])
        labels = {
            "baselineAnswerSha256": "baseline answer SHA-256",
            "candidateAnswerSha256": "candidate answer SHA-256",
        }
        detail = ", ".join(labels.get(key, key) for key in mismatches)
        raise ContractError(f"adjudication identity mismatch: {detail}")
    if not isinstance(adjudication["arms"], dict) or set(adjudication["arms"]) != {"baseline", "candidate"}:
        raise ContractError("adjudication arms must be baseline and candidate")
    scores: dict[str, Any] = {}
    minimum = spec["evaluation"]["minimumFactAccuracy"]
    if not isinstance(minimum, (int, float)) or isinstance(minimum, bool) or not 0 <= minimum <= 1:
        raise ContractError("minimumFactAccuracy must be between 0 and 1")
    for name in ("baseline", "candidate"):
        arm = adjudication["arms"][name]
        if not isinstance(arm, dict):
            raise ContractError(f"adjudication arm {name} must be an object")
        arm_keys = ("factsCorrect", "factsTotal", "dangerousFalseClaims")
        require_contract_keys(arm, arm_keys, arm_keys, f"adjudication arm {name}")
        correct, total, dangerous = arm["factsCorrect"], arm["factsTotal"], arm["dangerousFalseClaims"]
        if any(not isinstance(x, int) or isinstance(x, bool) for x in (correct, total, dangerous)) or total <= 0 or correct < 0 or correct > total or dangerous < 0:
            raise ContractError(f"invalid adjudication counts for {name}")
        if arm != frozen["totals"][name]:
            raise ContractError(f"adjudication arm {name} totals do not match recomputed ledger totals")
        exact_oracle_coverage = correct / total
        scores[name] = {
            **arm,
            "exactOracleCoverage": exact_oracle_coverage,
            "accepted": exact_oracle_coverage >= minimum and dangerous <= spec["evaluation"]["maxDangerousFalseClaims"],
        }
    bmetrics, cmetrics = baseline["document"]["metrics"], candidate["document"]["metrics"]
    return {
        "schemaVersion": 1,
        "status": "ok",
        "experimentId": spec["id"],
        "snapshotContentId": baseline["state"]["snapshotContentId"],
        "questionSetSha256": baseline["state"]["questionSetSha256"],
        "reviewer": adjudication["reviewer"],
        "oracleSha256": frozen["oracleSha256"],
        "ledgerSha256": frozen["ledgerSha256"],
        "adjudicationSha256": adjudication_sha256,
        "scores": scores,
        "metrics": {"baseline": bmetrics, "candidate": cmetrics},
        "answerSha256": {"baseline": baseline["answerSha256"], "candidate": candidate["answerSha256"]},
    }


def seal(args: argparse.Namespace) -> dict[str, Any]:
    spec = load_experiment(args.experiment)
    state = verify_snapshot(spec)
    artifacts = []
    path_identity_checks = []
    seen: set[Path] = set()
    for raw in args.artifact:
        path = raw.absolute()
        if is_within(path, spec["_snapshotRoot"]):
            raise ContractError(f"artifact must be outside snapshot: {path}")
        if path in seen:
            raise ContractError(f"duplicate artifact: {path}")
        seen.add(path)
        data, identity = read_file_stable_identity(path, "artifact")
        verify_path_identity(path, identity, "artifact")
        path_identity_checks.append((path, identity, "artifact"))
        artifacts.append({"path": str(path), "sha256": digest_bytes(data), "bytes": len(data)})
    if not artifacts:
        raise ContractError("seal requires at least one artifact")
    return {
        "schemaVersion": 1,
        "status": "sealed",
        "experimentId": spec["id"],
        "snapshotContentId": state["snapshotContentId"],
        "questionSetSha256": state["questionSetSha256"],
        "artifacts": artifacts,
        "_pathIdentityChecks": path_identity_checks,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("preflight", "verify-answer", "compare", "seal"):
        command = commands.add_parser(name)
        command.add_argument("--experiment", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
    commands.choices["verify-answer"].add_argument("--answer", type=Path, required=True)
    commands.choices["compare"].add_argument("--baseline", type=Path, required=True)
    commands.choices["compare"].add_argument("--candidate", type=Path, required=True)
    commands.choices["compare"].add_argument("--oracle", type=Path, required=True)
    commands.choices["compare"].add_argument("--ledger", type=Path, required=True)
    commands.choices["compare"].add_argument("--adjudication", type=Path, required=True)
    commands.choices["seal"].add_argument("--artifact", type=Path, action="append", required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    handlers = {"preflight": preflight, "verify-answer": verify_answer, "compare": compare, "seal": seal}
    try:
        spec = load_experiment(args.experiment)
        output_relative(args.output.absolute(), spec["_outputRoot"])
        value = handlers[args.command](args)
        for path, identity, label in value.pop("_pathIdentityChecks", []):
            verify_path_identity(path, identity, label)
        write_new_json(args.output.absolute(), value, spec["_outputRoot"])
    except ContractError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
