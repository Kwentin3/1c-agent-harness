from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

MANIFEST_SELF = "package-manifest.json"
PACKAGE_NAME = "issue14-business-rule-20260827"
EXPECTED_SOURCE_CF_SHA256 = "5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a"
EXPECTED_SNAPSHOT_MANIFEST_SHA256 = "70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691"
EXPECTED_BASE_PRODUCTION_FILE_SHA256 = "86f383323de83d4912c99854ec6db7cbf59e2265d62a97d8143a46eacba07d9c"
EXPECTED_PATCH_SHA256 = "73d484d337c320f45204fbd0c95940c9d5ead1922f7cb4b88f2229c32e6c43e3"
EXPECTED_CANONICAL_PATCHED_FILE_SHA256 = "d8124e2942426edf82394673561f96d914c8cf35503ccdc0048eb613e801ea3a"
EXPECTED_PRIMARY_HISTORICAL_PATCHED_FILE_SHA256 = "aac9b1b60a16c3aa57cab1e5e050e0cf526d9d941cc43c2a079269e72ae4f3ef"

REQUIRED_ARTIFACTS = {
    "ATTRIBUTION.md",
    "README.md",
    "canonical-green-2-evidence.md",
    "canonical-green-2-receipt.txt",
    "canonical-green-2-summary.json",
    "green-production-evidence.md",
    "green-production-receipt.txt",
    "green-production-summary.json",
    "instrumentation.diff",
    "native-invocations.json",
    "pre-production-review-1.md",
    "pre-production-review-2.md",
    "production-patch.diff",
    "red-source-evidence.md",
    "red-source-receipt.txt",
    "red-source-summary.json",
    "repeat-green-evidence.md",
    "repeat-green-receipt.txt",
    "repeat-green-summary.json",
    "runtime-entrypoint-gap.md",
    "semantic-contract-checklist.md",
    "task-contract-amendment-1.json",
    "task-contract-amendment-2.json",
    "task-contract.json",
}

CASES = [
    "negative_single",
    "zero_single",
    "mixed_same_product",
    "insufficient_stock_positive",
    "normal_positive",
    "minimum_positive",
    "all_positive_multi_duplicate",
]
INVALID_QUANTITY_CASES = ["negative_single", "zero_single", "mixed_same_product"]
VALID_CASES = ["normal_positive", "minimum_positive", "all_positive_multi_duplicate"]
CASE_KEYS = [
    "begin",
    "rowCount",
    "draftSucceeded",
    "draftError",
    "postCallSucceeded",
    "postError",
    "postedAfter",
    "inventoryBeforeA",
    "inventoryAfterA",
    "costQuantityBeforeA",
    "costQuantityAfterA",
    "costAmountBeforeA",
    "costAmountAfterA",
    "inventoryBeforeB",
    "inventoryAfterB",
    "costQuantityBeforeB",
    "costQuantityAfterB",
    "costAmountBeforeB",
    "costAmountAfterB",
    "inventoryMovementRowsA",
    "inventoryMovementQuantityA",
    "costMovementRowsA",
    "costMovementQuantityA",
    "costMovementAmountA",
    "inventoryMovementRowsB",
    "inventoryMovementQuantityB",
    "costMovementRowsB",
    "costMovementQuantityB",
    "costMovementAmountB",
    "end",
]

EXPECTED_ROW_COUNTS = {
    "negative_single": "1",
    "zero_single": "1",
    "mixed_same_product": "3",
    "insufficient_stock_positive": "1",
    "normal_positive": "1",
    "minimum_positive": "1",
    "all_positive_multi_duplicate": "3",
}

GREEN_EXPECTED = {
    "negative_single": {
        "draftSucceeded": "true",
        "postCallSucceeded": "false",
        "postedAfter": "false",
        "inventoryAfterA": "10",
        "inventoryAfterB": "10",
        "costQuantityAfterA": "10",
        "costAmountAfterA": "10",
        "inventoryMovementRowsA": "0",
        "inventoryMovementQuantityA": "0",
        "costMovementRowsA": "0",
        "costMovementQuantityA": "0",
        "costMovementAmountA": "0",
    },
    "zero_single": {
        "draftSucceeded": "true",
        "postCallSucceeded": "false",
        "postedAfter": "false",
        "inventoryAfterA": "10",
        "inventoryAfterB": "10",
        "costQuantityAfterA": "10",
        "costAmountAfterA": "10",
        "inventoryMovementRowsA": "0",
        "inventoryMovementQuantityA": "0",
        "costMovementRowsA": "0",
        "costMovementQuantityA": "0",
        "costMovementAmountA": "0",
    },
    "mixed_same_product": {
        "draftSucceeded": "true",
        "postCallSucceeded": "false",
        "postedAfter": "false",
        "inventoryAfterA": "10",
        "inventoryAfterB": "10",
        "costQuantityAfterA": "10",
        "costAmountAfterA": "10",
        "inventoryMovementRowsA": "0",
        "inventoryMovementQuantityA": "0",
        "costMovementRowsA": "0",
        "costMovementQuantityA": "0",
        "costMovementAmountA": "0",
    },
    "insufficient_stock_positive": {
        "draftSucceeded": "true",
        "postCallSucceeded": "false",
        "postedAfter": "false",
        "inventoryAfterA": "10",
        "inventoryMovementRowsA": "0",
    },
    "normal_positive": {
        "draftSucceeded": "true",
        "postCallSucceeded": "true",
        "postedAfter": "true",
        "inventoryAfterA": "6",
        "inventoryAfterB": "10",
        "costQuantityAfterA": "6",
        "costAmountAfterA": "6",
        "inventoryMovementRowsA": "1",
        "inventoryMovementQuantityA": "4",
        "inventoryMovementRowsB": "0",
    },
    "minimum_positive": {
        "draftSucceeded": "true",
        "postCallSucceeded": "true",
        "postedAfter": "true",
        "inventoryAfterA": "9.999",
        "inventoryAfterB": "10",
        "costQuantityAfterA": "9.999",
        "costAmountAfterA": "10",
        "inventoryMovementRowsA": "1",
        "inventoryMovementQuantityA": "0.001",
        "inventoryMovementRowsB": "0",
    },
    "all_positive_multi_duplicate": {
        "draftSucceeded": "true",
        "postCallSucceeded": "true",
        "postedAfter": "true",
        "inventoryAfterA": "6",
        "inventoryAfterB": "8",
        "costQuantityAfterA": "6",
        "costQuantityAfterB": "8",
        "costAmountAfterA": "6",
        "costAmountAfterB": "8",
        "inventoryMovementRowsA": "1",
        "inventoryMovementQuantityA": "4",
        "inventoryMovementRowsB": "1",
        "inventoryMovementQuantityB": "2",
    },
}

RED_EXPECTED = {
    "negative_single": {
        "draftSucceeded": "true",
        "postCallSucceeded": "true",
        "postedAfter": "true",
        "inventoryAfterA": "11",
        "costQuantityAfterA": "11",
        "inventoryMovementRowsA": "1",
        "inventoryMovementQuantityA": "-1",
    },
    "zero_single": {
        "draftSucceeded": "true",
        "postCallSucceeded": "true",
        "postedAfter": "true",
        "inventoryAfterA": "10",
        "inventoryMovementRowsA": "1",
        "inventoryMovementQuantityA": "0",
    },
    "mixed_same_product": {
        "draftSucceeded": "true",
        "postCallSucceeded": "true",
        "postedAfter": "true",
        "inventoryAfterA": "7",
        "inventoryMovementRowsA": "1",
        "inventoryMovementQuantityA": "3",
    },
    "insufficient_stock_positive": {
        "draftSucceeded": "true",
        "postCallSucceeded": "false",
        "postedAfter": "false",
        "inventoryAfterA": "10",
        "inventoryMovementRowsA": "0",
    },
    "normal_positive": GREEN_EXPECTED["normal_positive"],
    "minimum_positive": GREEN_EXPECTED["minimum_positive"],
    "all_positive_multi_duplicate": GREEN_EXPECTED["all_positive_multi_duplicate"],
}

SUMMARY_TO_RECEIPT = {
    "green-production-summary.json": "green-production-receipt.txt",
    "repeat-green-summary.json": "repeat-green-receipt.txt",
    "canonical-green-2-summary.json": "canonical-green-2-receipt.txt",
    "red-source-summary.json": "red-source-receipt.txt",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_files(package: Path) -> set[str]:
    return {
        p.relative_to(package).as_posix()
        for p in package.rglob("*")
        if p.is_file()
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rewrite_manifest(package: Path) -> None:
    """Refresh only hash/size fields; used by negative tests.

    This simulates an attacker who changes an artifact and then updates the
    manifest. Semantic validation must still catch wrong evidence values.
    """
    manifest_path = package / MANIFEST_SELF
    manifest = load_json(manifest_path)
    manifest["artifacts"] = {}
    manifest["artifactStats"] = {}
    for path in sorted(package.rglob("*")):
        if not path.is_file() or path.name == MANIFEST_SELF:
            continue
        rel = path.relative_to(package).as_posix()
        manifest["artifacts"][rel] = sha256(path)
        manifest["artifactStats"][rel] = path.stat().st_size
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def validate_manifest(package: Path) -> dict[str, Any]:
    manifest = load_json(package / MANIFEST_SELF)
    if manifest.get("schemaVersion") != 1:
        raise AssertionError("manifest schemaVersion mismatch")
    if manifest.get("package") != PACKAGE_NAME:
        raise AssertionError("manifest package mismatch")
    expected = set(manifest["artifacts"])
    actual = package_files(package) - {MANIFEST_SELF}
    if actual != expected:
        raise AssertionError(
            f"package/manifest closure broken: unlisted={sorted(actual - expected)} missing={sorted(expected - actual)}"
        )
    if expected != REQUIRED_ARTIFACTS:
        raise AssertionError(
            f"artifact set mismatch: extra={sorted(expected - REQUIRED_ARTIFACTS)} missing={sorted(REQUIRED_ARTIFACTS - expected)}"
        )
    for rel, expected_hash in manifest["artifacts"].items():
        path = package / rel
        if sha256(path) != expected_hash:
            raise AssertionError(f"artifact hash mismatch: {rel}")
        if manifest["artifactStats"].get(rel) != path.stat().st_size:
            raise AssertionError(f"artifact size mismatch: {rel}")
    ids = manifest["sourceImmutableIdentities"]
    if ids["sourceCfSha256"] != EXPECTED_SOURCE_CF_SHA256:
        raise AssertionError("source CF hash mismatch")
    if ids["manifestIdentitySha256"] != EXPECTED_SNAPSHOT_MANIFEST_SHA256:
        raise AssertionError("snapshot manifest hash mismatch")
    if ids["snapshotFileCount"] != 5099:
        raise AssertionError("snapshot file count mismatch")
    cpb = manifest["canonicalProductionBytes"]
    if cpb["baseFileSha256"] != EXPECTED_BASE_PRODUCTION_FILE_SHA256:
        raise AssertionError("base production file hash mismatch")
    if cpb["productionPatchSha256"] != EXPECTED_PATCH_SHA256:
        raise AssertionError("production patch hash mismatch")
    if cpb["patchedFileSha256"] != EXPECTED_CANONICAL_PATCHED_FILE_SHA256:
        raise AssertionError("canonical patched file hash mismatch")
    return manifest


def validate_no_private_paths(package: Path) -> None:
    # Placeholders such as ``<RUN_DIR>/home`` are intentional. What must not
    # appear in committed evidence is a real host absolute path.
    private_path = re.compile(r"(?<!>)/(workspace|home)/")
    for rel in package_files(package):
        if rel == MANIFEST_SELF:
            continue
        text = (package / rel).read_text(encoding="utf-8", errors="replace")
        if private_path.search(text):
            raise AssertionError(f"private absolute path leaked in {rel}")


def parse_receipt(path: Path) -> dict[str, list[str]]:
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    lines = text.splitlines()
    if len(lines) != 214:
        raise AssertionError(f"{path.name}: expected exactly 214 lines, got {len(lines)}")
    parsed: dict[str, list[str]] = defaultdict(list)
    for line in lines:
        if not line.strip():
            raise AssertionError(f"{path.name}: empty line")
        if "###" not in line:
            raise AssertionError(f"{path.name}: malformed line {line!r}")
        key, value = line.split("###", 1)
        if not key or "#" in key:
            raise AssertionError(f"{path.name}: malformed key {key!r}")
        parsed[key].append(value)
    expected_keys = {"nonce", "mode", "complete"}
    expected_keys.update(f"{case}.{key}" for case in CASES for key in CASE_KEYS)
    if set(parsed) != expected_keys:
        raise AssertionError(
            f"{path.name}: key mismatch missing={sorted(expected_keys - set(parsed))} unknown={sorted(set(parsed) - expected_keys)}"
        )
    for key, values in parsed.items():
        if key == "complete":
            if values != ["false", "true"]:
                raise AssertionError(f"{path.name}: complete marker sequence mismatch {values!r}")
        elif len(values) != 1:
            raise AssertionError(f"{path.name}: duplicate key {key}")
    return parsed


def scalar(rows: dict[str, list[str]], key: str) -> str:
    values = rows.get(key)
    if values is None or len(values) != 1:
        raise AssertionError(f"missing scalar receipt key {key}")
    return values[0]


def validate_receipt_expectations(path: Path, expected: dict[str, dict[str, str]]) -> dict[str, list[str]]:
    rows = parse_receipt(path)
    for case in CASES:
        if scalar(rows, f"{case}.begin") != "true" or scalar(rows, f"{case}.end") != "true":
            raise AssertionError(f"{path.name}: case boundary mismatch {case}")
        if scalar(rows, f"{case}.rowCount") != EXPECTED_ROW_COUNTS[case]:
            raise AssertionError(f"{path.name}: rowCount mismatch {case}")
        for before_key in [
            "inventoryBeforeA",
            "costQuantityBeforeA",
            "costAmountBeforeA",
            "inventoryBeforeB",
            "costQuantityBeforeB",
            "costAmountBeforeB",
        ]:
            if scalar(rows, f"{case}.{before_key}") != "10":
                raise AssertionError(f"{path.name}: opening balance mismatch {case}.{before_key}")
        for metric, expected_value in expected[case].items():
            actual = scalar(rows, f"{case}.{metric}")
            if actual != expected_value:
                raise AssertionError(f"{path.name}: {case}.{metric} expected {expected_value!r}, got {actual!r}")
    return rows


def validate_summary_observations(package: Path, summary_name: str, receipt_rows: dict[str, list[str]]) -> None:
    summary = load_json(package / summary_name)
    receipt_name = SUMMARY_TO_RECEIPT[summary_name]
    if summary.get("receiptSha256") != sha256(package / receipt_name):
        raise AssertionError(f"{summary_name}: receiptSha256 mismatch")
    obs = summary["observations"]

    def assert_case_values(case: str, values: dict[str, Any], location: str) -> None:
        for metric, expected_value in values.items():
            if metric == "case":
                continue
            receipt_key = f"{case}.{metric}"
            actual_from_receipt = scalar(receipt_rows, receipt_key)
            if str(expected_value) != actual_from_receipt:
                raise AssertionError(
                    f"{summary_name}: {location}.{metric}={expected_value!r} differs from receipt {receipt_key}={actual_from_receipt!r}"
                )

    if summary_name == "red-source-summary.json":
        for case, values in obs["redFailures"].items():
            assert_case_values(case, values, f"redFailures.{case}")
        assert_case_values(obs["negativeControl"]["case"], obs["negativeControl"], "negativeControl")
        for case, values in obs["validPreservation"].items():
            assert_case_values(case, values, f"validPreservation.{case}")
    else:
        for case, values in obs["invalidCasesRejectedAtomically"].items():
            assert_case_values(case, values, f"invalidCasesRejectedAtomically.{case}")
        assert_case_values(obs["existingNegativeControl"]["case"], obs["existingNegativeControl"], "existingNegativeControl")
        for case, values in obs["validPreservation"].items():
            assert_case_values(case, values, f"validPreservation.{case}")


def validate_production_patch(package: Path) -> None:
    lines = (package / "production-patch.diff").read_text(encoding="utf-8").splitlines()
    if lines[:3] != [
        "--- a/Documents/InventoryWriteOff/Ext/ObjectModule.bsl",
        "+++ b/Documents/InventoryWriteOff/Ext/ObjectModule.bsl",
        "@@ -11,0 +12,6 @@",
    ]:
        raise AssertionError("production patch target/hunk mismatch")
    if sum(1 for line in lines if line.startswith("--- ")) != 1 or sum(1 for line in lines if line.startswith("+++ ")) != 1:
        raise AssertionError("production patch must touch exactly one file")
    added = [line[1:] for line in lines if line.startswith("+") and not line.startswith("+++")]
    removed = [line for line in lines if line.startswith("-") and not line.startswith("---")]
    expected_added = [
        "\tFor Each InventoryRow In Inventory Do",
        "\t\tIf InventoryRow.Quantity <= 0 Then",
        "\t\t\tCancel = True;",
        "\t\t\tReturn;",
        "\t\tEndIf;",
        "\tEndDo;",
    ]
    if removed:
        raise AssertionError(f"production patch must be additive only, removed={removed!r}")
    if added != expected_added:
        raise AssertionError(f"production patch added lines mismatch: {added!r}")
    if sha256(package / "production-patch.diff") != EXPECTED_PATCH_SHA256:
        raise AssertionError("production patch SHA mismatch")


def validate_instrumentation_and_native_binding(package: Path) -> None:
    inst = (package / "instrumentation.diff").read_text(encoding="utf-8")
    if "Documents/InventoryWriteOff/Ext/ObjectModule.bsl" in inst:
        raise AssertionError("instrumentation diff must not include production patch target")
    if "<RUN_DIR>" not in inst or "<RUN_NONCE>" not in inst:
        raise AssertionError("instrumentation diff must use sanitized run placeholders")
    added = [line for line in inst.splitlines() if line.startswith("+") and not line.startswith("+++")]
    removed = [line for line in inst.splitlines() if line.startswith("-") and not line.startswith("---")]
    if len(added) < 300 or removed:
        raise AssertionError("instrumentation size/shape mismatch")
    native = load_json(package / "native-invocations.json")
    if native["instrumentation"]["sha256"] != sha256(package / "instrumentation.diff"):
        raise AssertionError("native binding instrumentation hash mismatch")
    expected_runs = {"red-source", "green-production-historical", "canonical-green-1", "canonical-green-2"}
    if set(native["runs"]) != expected_runs:
        raise AssertionError("native binding run set mismatch")
    for label, run in native["runs"].items():
        outputs = run["outputs"]
        if outputs["createDumpResult"] != "0" or outputs["loadDumpResult"] != "0":
            raise AssertionError(f"{label}: native DumpResult mismatch")
        if outputs["loadSuccessMarker"] != "Configuration successfully updated":
            raise AssertionError(f"{label}: missing load success marker")
        if outputs["runtimeReceiptCompleteMarker"] != "complete###true":
            raise AssertionError(f"{label}: missing runtime complete marker binding")
        if outputs.get("runtimeCompletionObserved") is not True:
            raise AssertionError(f"{label}: runtime completion was not observed")
        commands = run["commands"]
        expected_modes = {"create": "CREATEINFOBASE", "load": "DESIGNER", "runtime": "ENTERPRISE"}
        for command_name, expected_mode in expected_modes.items():
            command = commands[command_name]
            if command[:4] != ["xvfb-run", "-a", "-s", "-screen 0 1280x1024x8 -nolisten tcp"]:
                raise AssertionError(f"{label}: xvfb prefix mismatch in {command_name}")
            if command[4] != ".local/platform/1cv8t/x86_64/8.5.1.1150/1cv8t" or command[5] != expected_mode:
                raise AssertionError(f"{label}: native command mode mismatch in {command_name}")
        for command in commands.values():
            joined = " ".join(command)
            if "<RUN_DIR>" not in joined:
                raise AssertionError(f"{label}: command lacks run-root placeholder")


def observation_vector(rows: dict[str, list[str]]) -> dict[str, str]:
    comparison_keys = [
        "rowCount",
        "draftSucceeded",
        "postCallSucceeded",
        "postedAfter",
        "inventoryAfterA",
        "inventoryAfterB",
        "costQuantityAfterA",
        "costQuantityAfterB",
        "costAmountAfterA",
        "costAmountAfterB",
        "inventoryMovementRowsA",
        "inventoryMovementQuantityA",
        "inventoryMovementRowsB",
        "inventoryMovementQuantityB",
        "costMovementRowsA",
        "costMovementQuantityA",
        "costMovementAmountA",
        "costMovementRowsB",
        "costMovementQuantityB",
        "costMovementAmountB",
    ]
    return {f"{case}.{key}": scalar(rows, f"{case}.{key}") for case in CASES for key in comparison_keys}


def validate_canonical_green(package: Path, receipt_rows_by_name: dict[str, dict[str, list[str]]]) -> None:
    repeat = load_json(package / "repeat-green-summary.json")
    canon2 = load_json(package / "canonical-green-2-summary.json")
    if repeat["inputs"]["patchedProductionFileSha256"] != EXPECTED_CANONICAL_PATCHED_FILE_SHA256:
        raise AssertionError("canonical GREEN #1 patched hash mismatch")
    if canon2["inputs"]["patchedProductionFileSha256"] != EXPECTED_CANONICAL_PATCHED_FILE_SHA256:
        raise AssertionError("canonical GREEN #2 patched hash mismatch")
    if not canon2["canonicalization"]["byteIdenticalPatchedProductionFile"]:
        raise AssertionError("canonical GREEN byte equality flag is false")
    if canon2["canonicalization"]["canonicalGreen1PatchedProductionFileSha256"] != EXPECTED_CANONICAL_PATCHED_FILE_SHA256:
        raise AssertionError("canonicalization green1 hash mismatch")
    if canon2["canonicalization"]["primaryGreenHistoricalPatchedProductionFileSha256"] != EXPECTED_PRIMARY_HISTORICAL_PATCHED_FILE_SHA256:
        raise AssertionError("historical primary GREEN hash mismatch")
    if observation_vector(receipt_rows_by_name["repeat-green-receipt.txt"]) != observation_vector(receipt_rows_by_name["canonical-green-2-receipt.txt"]):
        raise AssertionError("canonical GREEN observation vectors differ")


def validate_report(package: Path) -> None:
    text = (package / "README.md").read_text(encoding="utf-8")
    required_snippets = [
        "Cost was dominated by finding a reliable data-backed posting entrypoint",
        "Reused from issue #10",
        "Manual steps that remain",
        "Instrumentation size:",
        "No claim is made for empty documents, UI validation/messages, imports, undo-posting, reposting",
    ]
    for snippet in required_snippets:
        if snippet not in text:
            raise AssertionError(f"README missing report snippet: {snippet}")


def validate_package(package: Path) -> None:
    validate_manifest(package)
    validate_no_private_paths(package)
    validate_production_patch(package)
    rows_by_receipt = {
        "red-source-receipt.txt": validate_receipt_expectations(package / "red-source-receipt.txt", RED_EXPECTED),
        "green-production-receipt.txt": validate_receipt_expectations(package / "green-production-receipt.txt", GREEN_EXPECTED),
        "repeat-green-receipt.txt": validate_receipt_expectations(package / "repeat-green-receipt.txt", GREEN_EXPECTED),
        "canonical-green-2-receipt.txt": validate_receipt_expectations(package / "canonical-green-2-receipt.txt", GREEN_EXPECTED),
    }
    for summary_name, receipt_name in SUMMARY_TO_RECEIPT.items():
        validate_summary_observations(package, summary_name, rows_by_receipt[receipt_name])
    validate_instrumentation_and_native_binding(package)
    validate_canonical_green(package, rows_by_receipt)
    validate_report(package)
