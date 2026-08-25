#!/usr/bin/env python3
"""Client-neutral, read-only evidence harness for 1C snapshot experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from typing import Any, Iterable


class ContractError(RuntimeError):
    pass


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json_hashed(path: Path, label: str) -> tuple[dict[str, Any], str]:
    reject_symlink_path(path, label)
    if not path.is_file():
        raise ContractError(f"{label} is not a regular file: {path}")
    try:
        data = path.read_bytes()
        value = json.loads(data.decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
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
    return path.absolute()


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def require_keys(value: dict[str, Any], keys: Iterable[str], label: str) -> None:
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
    if spec["schemaVersion"] != 1:
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


def verify_snapshot(spec: dict[str, Any]) -> dict[str, Any]:
    root: Path = spec["_snapshotRoot"]
    manifest: Path = spec["_manifestPath"]
    questions: Path = spec["_questionsPath"]
    for path, label in ((root, "snapshot root"), (manifest, "snapshot manifest"), (questions, "questions path")):
        reject_symlink_path(path, label)
    if not root.is_dir():
        raise ContractError(f"snapshot root is not a directory: {root}")
    for node in root.rglob("*"):
        mode = node.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise ContractError(f"snapshot contains a symlink: {node.relative_to(root).as_posix()}")
        if stat.S_ISREG(mode) and node.stat().st_nlink != 1:
            raise ContractError(f"snapshot contains a hard link: {node.relative_to(root).as_posix()}")
    if not manifest.is_file():
        raise ContractError(f"snapshot manifest is not a file: {manifest}")
    expected_content_id = spec["snapshot"]["contentId"]
    actual_content_id = f"sha256:{digest_file(manifest)}"
    if expected_content_id != actual_content_id:
        raise ContractError(f"snapshot manifest content ID mismatch: expected {expected_content_id}, got {actual_content_id}")
    expected_questions = spec["questions"]["sha256"]
    actual_questions = digest_file(questions)
    if expected_questions != actual_questions:
        raise ContractError(f"question set hash mismatch: expected {expected_questions}, got {actual_questions}")
    entries: dict[str, str] = {}
    try:
        lines = manifest.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ContractError(f"cannot read snapshot manifest: {exc}") from exc
    for number, line in enumerate(lines, 1):
        parts = line.split("  ", 1)
        if len(parts) != 2 or len(parts[0]) != 64 or any(c not in "0123456789abcdef" for c in parts[0]):
            raise ContractError(f"malformed snapshot manifest line {number}")
        rel = safe_relative(parts[1], f"manifest path at line {number}").as_posix()
        if rel in entries:
            raise ContractError(f"duplicate snapshot manifest path: {rel}")
        target = root.joinpath(*PurePosixPath(rel).parts)
        reject_symlink_path(target, f"snapshot manifest path {rel}")
        if not target.is_file():
            raise ContractError(f"snapshot manifest file is missing: {rel}")
        actual = digest_file(target)
        if actual != parts[0]:
            raise ContractError(f"snapshot manifest hash mismatch: {rel}")
        entries[rel] = actual
    required_roots = {"Configuration.xml", "ConfigDumpInfo.xml"}
    missing_roots = sorted(required_roots - entries.keys())
    if missing_roots:
        raise ContractError(f"snapshot missing required root files: {missing_roots}")
    actual_files = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and not p.is_symlink()
    }
    if actual_files != set(entries):
        missing = sorted(set(entries) - actual_files)[:3]
        extra = sorted(actual_files - set(entries))[:3]
        raise ContractError(f"snapshot manifest file set mismatch; missing={missing}, extra={extra}")
    for path, label in ((spec["_outputRoot"], "outputRoot"), (spec["_cacheRoot"], "cacheRoot")):
        reject_symlink_path(path, label)
        if is_within(path, root) or is_within(root, path):
            raise ContractError(f"{label} must be outside and disjoint from snapshot")
    questions_doc = read_json(questions, "questions")
    if questions_doc.get("schemaVersion") != 1 or not isinstance(questions_doc.get("questions"), list) or not questions_doc["questions"]:
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
    }


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
    if doc["schemaVersion"] != 1:
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
        for label in ("facts", "inferences", "assumptions", "unknowns"):
            current = claim_ids(entry[label], label)
            duplicate = ids & current
            if duplicate:
                raise ContractError(f"claim ids must be unique within an answer: {sorted(duplicate)}")
            ids |= current
        if not isinstance(entry["locators"], list):
            raise ContractError("locators must be an array")
        for locator in entry["locators"]:
            if not isinstance(locator, dict):
                raise ContractError("each locator must be an object")
            locator_keys = ("path", "startLine", "endLine", "claimIds")
            require_contract_keys(locator, locator_keys, locator_keys, "locator")
            rel = safe_relative(locator["path"], "locator path")
            target = root.joinpath(*rel.parts)
            reject_symlink_path(target, f"locator {rel.as_posix()}")
            if not target.is_file() or not is_within(target, root):
                raise ContractError(f"locator file does not exist inside snapshot: {rel.as_posix()}")
            start, end = locator["startLine"], locator["endLine"]
            if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool) or start < 1 or end < start:
                raise ContractError(f"invalid locator line range: {rel.as_posix()}:{start}-{end}")
            try:
                line_count = len(target.read_text(encoding="utf-8-sig").splitlines())
            except (OSError, UnicodeError) as exc:
                raise ContractError(f"locator file is not readable UTF-8 text: {rel.as_posix()}: {exc}") from exc
            if end > line_count:
                raise ContractError(f"locator line range exceeds file: {rel.as_posix()}:{start}-{end}, lines={line_count}")
            claim_ids_value = locator["claimIds"]
            if not isinstance(claim_ids_value, list) or not claim_ids_value or any(x not in ids for x in claim_ids_value):
                raise ContractError(f"locator claimIds must reference claims in the same answer: {rel.as_posix()}")
            if len(claim_ids_value) != len(set(claim_ids_value)):
                raise ContractError(f"locator claimIds must be unique: {rel.as_posix()}")
            locator_count += 1
    if seen_questions != state["questionIds"]:
        raise ContractError(f"answer question order/set mismatch: expected {state['questionIds']}, got {seen_questions}")
    if not isinstance(doc["metrics"], dict):
        raise ContractError("answer metrics must be an object")
    return {"document": doc, "state": state, "locatorCount": locator_count, "answerSha256": answer_sha256}


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    reject_symlink_path(path, "output")
    if path.exists() or path.is_symlink():
        raise ContractError(f"refusing existing output: {path}")
    parent = path.parent
    reject_symlink_path(parent, "output parent")
    if not parent.is_dir():
        raise ContractError(f"output parent must already exist: {parent}")
    data = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(data)
    except FileExistsError as exc:
        raise ContractError(f"refusing existing output: {path}") from exc


def preflight(args: argparse.Namespace) -> dict[str, Any]:
    spec = load_experiment(args.experiment)
    state = verify_snapshot(spec)
    return {"schemaVersion": 1, "status": "ok", "experimentId": spec["id"], **state}


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


def compare(args: argparse.Namespace) -> dict[str, Any]:
    spec = load_experiment(args.experiment)
    baseline = verify_answer_doc(spec, args.baseline)
    candidate = verify_answer_doc(spec, args.candidate)
    adjudication = read_json(args.adjudication, "adjudication")
    adjudication_keys = ("schemaVersion", "experimentId", "arms", "reviewer")
    require_contract_keys(adjudication, adjudication_keys, adjudication_keys, "adjudication")
    if adjudication["schemaVersion"] != 1 or adjudication["experimentId"] != spec["id"]:
        raise ContractError("adjudication contract mismatch")
    if not isinstance(adjudication["reviewer"], str) or not adjudication["reviewer"]:
        raise ContractError("adjudication reviewer must be non-empty")
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
        accuracy = correct / total
        scores[name] = {
            **arm,
            "factAccuracy": accuracy,
            "accepted": accuracy >= minimum and dangerous <= spec["evaluation"]["maxDangerousFalseClaims"],
        }
    bmetrics, cmetrics = baseline["document"]["metrics"], candidate["document"]["metrics"]
    return {
        "schemaVersion": 1,
        "status": "ok",
        "experimentId": spec["id"],
        "snapshotContentId": baseline["state"]["snapshotContentId"],
        "questionSetSha256": baseline["state"]["questionSetSha256"],
        "reviewer": adjudication["reviewer"],
        "scores": scores,
        "metrics": {"baseline": bmetrics, "candidate": cmetrics},
        "answerSha256": {"baseline": baseline["answerSha256"], "candidate": candidate["answerSha256"]},
    }


def seal(args: argparse.Namespace) -> dict[str, Any]:
    spec = load_experiment(args.experiment)
    state = verify_snapshot(spec)
    artifacts = []
    seen: set[Path] = set()
    for raw in args.artifact:
        path = raw.absolute()
        reject_symlink_path(path, "artifact")
        if not path.is_file():
            raise ContractError(f"artifact is not a regular file: {path}")
        if is_within(path, spec["_snapshotRoot"]):
            raise ContractError(f"artifact must be outside snapshot: {path}")
        if path in seen:
            raise ContractError(f"duplicate artifact: {path}")
        seen.add(path)
        artifacts.append({"path": str(path), "sha256": digest_file(path), "bytes": path.stat().st_size})
    if not artifacts:
        raise ContractError("seal requires at least one artifact")
    return {
        "schemaVersion": 1,
        "status": "sealed",
        "experimentId": spec["id"],
        "snapshotContentId": state["snapshotContentId"],
        "questionSetSha256": state["questionSetSha256"],
        "artifacts": artifacts,
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
    commands.choices["compare"].add_argument("--adjudication", type=Path, required=True)
    commands.choices["seal"].add_argument("--artifact", type=Path, action="append", required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    handlers = {"preflight": preflight, "verify-answer": verify_answer, "compare": compare, "seal": seal}
    try:
        spec = load_experiment(args.experiment)
        if not is_within(args.output.absolute(), spec["_outputRoot"]):
            raise ContractError(f"output must be inside declared outputRoot: {spec['_outputRoot']}")
        value = handlers[args.command](args)
        write_new_json(args.output.absolute(), value)
    except ContractError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
