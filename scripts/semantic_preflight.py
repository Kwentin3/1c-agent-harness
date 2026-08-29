#!/usr/bin/env python3
"""Fail-closed semantic/oracle preflight; never invokes 1C."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
from typing import Any


REPO = Path(__file__).resolve().parents[1]
TOP = {"schemaVersion", "task", "clauses", "observations", "cases",
       "countermodels", "closureExplanation", "receipts"}


def finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **details}


def obj(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        actual = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise ValueError(f"{label} keys mismatch: expected {sorted(keys)}, got {actual}")
    return value


def items(value: Any, label: str, empty: bool = False) -> list[Any]:
    if not isinstance(value, list) or (not value and not empty):
        raise ValueError(f"{label} must be {'a list' if empty else 'a non-empty list'}")
    return value


def text(value: Any, label: str, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise ValueError(f"{label} must be {'a string' if empty else 'a non-empty string'}")
    return value


def load_json(payload: str) -> Any:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result: raise ValueError(f"duplicate JSON key: {key!r}")
            result[key] = value
        return result
    return json.loads(payload, object_pairs_hook=unique)


def safe_read(root: Path, relative: Any, label: str) -> str:
    value = text(relative, label)
    path = Path(value)
    if path.is_absolute(): raise ValueError(f"{label} must be relative")
    if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{label} escapes its approved root")
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    descriptor = os.open(root, flags | os.O_DIRECTORY)
    try:
        for part in path.parts[:-1]:
            child = os.open(part, flags | os.O_DIRECTORY, dir_fd=descriptor)
            os.close(descriptor); descriptor = child
        file_descriptor = os.open(path.parts[-1], flags, dir_fd=descriptor)
        try:
            metadata = os.fstat(file_descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_size > 1_000_000:
                raise ValueError(f"{label} must be a small singly linked regular file")
            payload = bytearray()
            while chunk := os.read(file_descriptor, 65536): payload.extend(chunk)
            after = os.fstat(file_descriptor)
            if (len(payload), metadata.st_ino, metadata.st_mtime_ns) != (after.st_size, after.st_ino, after.st_mtime_ns): raise ValueError(f"{label} changed while reading")
            return payload.decode("utf-8-sig")
        finally:
            os.close(file_descriptor)
    finally:
        os.close(descriptor)


def pairs(value: Any, label: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for index, pair in enumerate(items(value, label)):
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError(f"{label}[{index}] must be [string, string]")
        key, expected = pair
        text(key, f"{label}[{index}][0]"); text(expected, f"{label}[{index}][1]")
        if key in result: raise ValueError(f"{label} has a duplicate key")
        result[key] = expected
    return result


def receipt(payload: str, delimiter: str, phase: str) -> tuple[dict[str, str], list[dict[str, Any]]]:
    rows: dict[str, str] = {}; found: list[dict[str, Any]] = []
    for number, raw in enumerate(payload.splitlines(), 1):
        if not raw: continue
        key, separator, value = raw.partition(delimiter)
        if not separator or not key or not value: raise ValueError(f"receipt {phase} has invalid row {number}")
        if key in rows:
            found.append(finding("RECEIPT_DUPLICATE_OBSERVATION", f"receipt {phase} repeats a key", phase=phase))
        else: rows[key] = value
    return rows, found


def validate(plan_path: Path) -> dict[str, Any]:
    plan_path = Path(os.path.abspath(plan_path))
    if not plan_path.is_relative_to(REPO):
        raise ValueError("plan must be a regular file inside the repository")
    plan_relative = plan_path.relative_to(REPO)
    plan = obj(load_json(safe_read(REPO, plan_relative.as_posix(), "plan")), TOP, "plan")
    if type(plan["schemaVersion"]) is not int or plan["schemaVersion"] != 1: raise ValueError("schemaVersion must be integer 1")
    text(plan["task"], "task"); findings: list[dict[str, Any]] = []

    clause_ids: set[str] = set()
    for index, raw in enumerate(items(plan["clauses"], "clauses")):
        clause = obj(raw, {"id", "statement", "basis"}, f"clauses[{index}]")
        identifier = text(clause["id"], f"clauses[{index}].id"); text(clause["statement"], f"clauses[{index}].statement")
        if identifier in clause_ids or clause["basis"] not in {"user-task", "established-domain", "unknown"}:
            raise ValueError("clause ids must be unique and bases declared")
        clause_ids.add(identifier)
        if clause["basis"] == "unknown":
            findings.append(finding("UNSUPPORTED_ACCEPTANCE_CLAUSE", f"clause {identifier!r} promotes unknown behavior", clause=identifier))

    observations: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(items(plan["observations"], "observations")):
        observation = obj(raw, {"id", "description", "externallyCheckable", "scalar"}, f"observations[{index}]")
        identifier = text(observation["id"], f"observations[{index}].id"); text(observation["description"], f"observations[{index}].description")
        if identifier in observations or type(observation["scalar"]) is not bool or type(observation["externallyCheckable"]) is not bool:
            raise ValueError("observation ids must be unique and flags boolean")
        observations[identifier] = observation
        if not observation["externallyCheckable"]: findings.append(finding("UNVERIFIABLE_OBSERVATION", f"{identifier!r} is not externally checkable", observation=identifier))
        if not observation["scalar"]: findings.append(finding("NON_SCALAR_OBSERVATION", f"{identifier!r} is not scalar", observation=identifier))

    cases: dict[str, dict[str, str]] = {}
    for index, raw in enumerate(items(plan["cases"], "cases")):
        case = obj(raw, {"id", "expected"}, f"cases[{index}]"); identifier = text(case["id"], f"cases[{index}].id")
        expected = case["expected"]
        if identifier in cases or not isinstance(expected, dict) or set(expected) != set(observations):
            raise ValueError("each unique case must declare the complete observation vector")
        for value in expected.values(): text(value, "case expected value")
        cases[identifier] = expected

    survivors: list[str] = []; model_ids: set[str] = set()
    for index, raw in enumerate(items(plan["countermodels"], "countermodels", empty=True)):
        model = obj(raw, {"id", "rationale", "predictions"}, f"countermodels[{index}]")
        identifier = text(model["id"], f"countermodels[{index}].id"); text(model["rationale"], f"countermodels[{index}].rationale")
        if identifier in model_ids: raise ValueError("countermodel ids must be unique")
        model_ids.add(identifier)
        predictions = model["predictions"]
        if not isinstance(predictions, dict) or set(predictions) != set(cases): raise ValueError("countermodel must predict every case")
        for predicted in predictions.values():
            if not isinstance(predicted, dict) or set(predicted) != set(observations): raise ValueError("countermodel must predict every observation")
            for value in predicted.values(): text(value, "countermodel predicted value")
        if all(predictions[case_id] == expected for case_id, expected in cases.items()):
            survivors.append(identifier); findings.append(finding("SURVIVING_COUNTERMODEL", f"{identifier!r} matches every observation", countermodel=identifier))
    closure = plan["closureExplanation"]
    if not isinstance(closure, str): raise ValueError("closureExplanation must be a string")
    if not survivors and not closure.strip(): findings.append(finding("MISSING_CLOSURE_EXPLANATION", "no survivor and no closure explanation"))

    receipts = obj(plan["receipts"], {"policy", "delimiter", "phases"}, "receipts"); delimiter = text(receipts["delimiter"], "delimiter")
    if receipts["policy"] != "exact" or not isinstance(receipts["phases"], dict) or set(receipts["phases"]) != {"red", "green"}:
        raise ValueError("receipts require exact policy and exactly red/green phases")
    required = {(case_id, observation_id) for case_id in cases for observation_id in observations}; vectors: dict[str, dict[tuple[str, str], str]] = {}
    for phase, raw in receipts["phases"].items():
        declared = obj(raw, {"path", "expected", "bindings", "controls"}, f"phase {phase}"); expected = pairs(declared["expected"], f"phase {phase} expected")
        vector: dict[tuple[str, str], str] = {}; bound_keys: set[str] = set()
        for binding in items(declared["bindings"], f"phase {phase} bindings"):
            if not isinstance(binding, list) or len(binding) != 3 or not all(isinstance(v, str) for v in binding): raise ValueError("binding must be [case, observation, key]")
            cell = (binding[0], binding[1]); key = binding[2]
            if cell not in required or cell in vector or key not in expected or key in bound_keys: raise ValueError("bindings must uniquely cover declared cells and keys")
            vector[cell] = expected[key]; bound_keys.add(key)
        controls = items(declared["controls"], f"phase {phase} controls", empty=True)
        if not all(isinstance(key, str) for key in controls) or len(set(controls)) != len(controls) or bound_keys & set(controls) or set(expected) != bound_keys | set(controls):
            raise ValueError("every receipt key must be one binding or control")
        if set(vector) != required: findings.append(finding("INCOMPLETE_RECEIPT_BINDINGS", f"receipt {phase} has incomplete semantic bindings", phase=phase))
        vectors[phase] = vector
        receipt_relative = plan_relative.parent / text(declared["path"], f"receipt {phase} path")
        actual, parsed = receipt(safe_read(REPO, receipt_relative.as_posix(), f"receipt {phase}"), delimiter, phase); findings.extend(parsed)
        missing, extra = set(expected) - set(actual), set(actual) - set(expected); wrong = {key for key in set(expected) & set(actual) if expected[key] != actual[key]}
        if missing: findings.append(finding("RECEIPT_MISSING_OBSERVATIONS", f"receipt {phase} is missing {len(missing)} key(s)", phase=phase))
        if extra: findings.append(finding("RECEIPT_EXTRA_OBSERVATIONS", f"receipt {phase} has {len(extra)} extra key(s)", phase=phase))
        if wrong: findings.append(finding("RECEIPT_WRONG_VALUE", f"receipt {phase} has {len(wrong)} wrong value(s)", phase=phase))
    if vectors["green"] != {(case_id, observation_id): cases[case_id][observation_id] for case_id, observation_id in required}:
        findings.append(finding("GREEN_SEMANTIC_MISMATCH", "GREEN bindings contradict the semantic case matrix"))
    if vectors["red"] == vectors["green"]: findings.append(finding("RED_NOT_DISTINGUISHING", "RED semantic vector does not differ from GREEN"))
    return {"verdict": "CONTRACT BLOCKED" if findings else "READY FOR NATIVE", "findings": findings, "survivingCountermodels": survivors, "nativeRun": False}


def main(argv: list[str]) -> int:
    try:
        if len(argv) != 2: raise ValueError("usage: semantic_preflight.py PLAN.json")
        result = validate(Path(argv[1]))
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError, json.JSONDecodeError) as error:
        result = {"verdict": "CONTRACT BLOCKED", "findings": [finding("INVALID_PLAN", str(error))], "survivingCountermodels": [], "nativeRun": False}
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["verdict"] == "READY FOR NATIVE" else 1


if __name__ == "__main__": raise SystemExit(main(sys.argv))
