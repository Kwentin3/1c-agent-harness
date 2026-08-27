from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

MANIFEST = "package-manifest.json"
REQUIRED = {
    ".gitattributes",
    "README.md",
    "candidate-code-identity.json",
    "cost-ledger.json",
    "native-results.json",
    "success-result.json",
    "success-result.raw.json.gz",
    "success-receipt.native",
    "success-receipt.txt",
    "success-create-log.txt",
    "success-create-result.native",
    "success-load-log.native",
    "success-load-result.native",
    "success-process-check.native",
    "repeat-result.json",
    "repeat-result.raw.json.gz",
    "repeat-receipt.native",
    "repeat-receipt.txt",
    "repeat-create-log.txt",
    "repeat-create-result.native",
    "repeat-load-log.native",
    "repeat-load-result.native",
    "repeat-process-check.native",
    "timeout-result.json",
    "timeout-result.raw.json.gz",
    "timeout-create-log.txt",
    "timeout-create-result.native",
    "timeout-load-log.native",
    "timeout-load-result.native",
    "timeout-process-check.native",
    "process-cleanup-checks.json",
}
SNAPSHOT_MANIFEST_SHA256 = "70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691"
RESULT_ZERO_SHA256 = "e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083"
LOAD_LOG_SHA256 = "4d841be04b71dd0ee7cfebcfa7af194d74902e2ec1c213987889d7d3940c0f86"
RAW_RESULT_SHA256 = {
    "success": "3b84303e3607b1c838f1466aa29e7f28f27b8050a91d60930ca36104b37e5079",
    "repeat": "64ec288dabd0cf2260137af769a7213333d74b8f58b149394d54d9d717927d6e",
    "timeout": "c9e6979681edda15d8889514edc40fbdaf45b3ce193c8ce8b7513c3f73ddc7c3",
}
RAW_RECEIPT_SHA256 = {
    "success": "4328d31ca02b67ae13e41f5858f2f39ca2540752c0ce4c576f0706fe89ebca36",
    "repeat": "65ec08a188ec21323616ed45b7f3ba919f7f68c7d09a5e1a52bcc34bbdf1f1a4",
}
CREATE_LOG_SHA256 = {
    "success": "630b1dc9705de66f860aa33f4295b1d13d0867b1c76b792d7d6601a62b54aa4c",
    "repeat": "4931f445ecba23a23c31219c3a6c1a6c1a00cfad16e865ae11cccd17007b9df5",
    "timeout": "ce7af1c039293a4af2171ebeb879f099b4f84eea00e7572a3140116d120b2b34",
}
PROCESS_CHECKS_SHA256 = "5576ddac44f12816c16b5f9a5ffadb88f893b37517fcd8cba43791858f972eec"
REPO_ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rewrite_manifest(package: Path) -> None:
    artifacts = {
        path.relative_to(package).as_posix(): sha256(path)
        for path in sorted(package.rglob("*"))
        if path.is_file() and path.name != MANIFEST
    }
    (package / MANIFEST).write_text(
        json.dumps({"schemaVersion": 1, "artifacts": artifacts}, indent=2) + "\n",
        encoding="utf-8",
    )


def sanitize_result(value: object) -> object:
    if isinstance(value, dict):
        return {key: sanitize_result(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_result(item) for item in value]
    if isinstance(value, str):
        return value.replace("/workspace/1c-agent-harness", "<REPO_ROOT>").replace(
            "/home/hermeswebui", "<USER_HOME>"
        )
    return value


def load_sanitized_result(package: Path, name: str, run_name: str) -> dict[str, object]:
    envelope = json.loads((package / name).read_text(encoding="utf-8"))
    assert envelope["schemaVersion"] == 1
    assert envelope["sourceKind"] == "deterministically path-sanitized machine-produced result.json"
    raw_file = package / f"{run_name}-result.raw.json.gz"
    raw_payload = gzip.decompress(raw_file.read_bytes())
    assert hashlib.sha256(raw_payload).hexdigest() == RAW_RESULT_SHA256[run_name]
    assert envelope["rawLocalSha256"] == RAW_RESULT_SHA256[run_name]
    raw_result = json.loads(raw_payload.decode("utf-8"))
    assert envelope["sanitizedResult"] == sanitize_result(raw_result)
    return envelope["sanitizedResult"]


def validate_package(package: Path) -> None:
    actual = {
        path.relative_to(package).as_posix()
        for path in package.rglob("*")
        if path.is_file()
    }
    assert actual == REQUIRED | {MANIFEST}
    manifest = json.loads((package / MANIFEST).read_text(encoding="utf-8"))
    assert manifest["schemaVersion"] == 1
    assert set(manifest["artifacts"]) == REQUIRED
    for relative, expected in manifest["artifacts"].items():
        assert sha256(package / relative) == expected

    for path in package.rglob("*"):
        if path.is_file():
            payload = path.read_bytes()
            assert b"/workspace/" not in payload
            assert b"/home/hermeswebui" not in payload

    code_identity = json.loads((package / "candidate-code-identity.json").read_text(encoding="utf-8"))
    assert code_identity["schemaVersion"] == 1
    assert code_identity["nativeRunsExecutedAfterTheseBytesWereFrozen"] is True
    assert code_identity["codeIdentity"] == {
        "scripts/native_cycle.py": sha256(REPO_ROOT / "scripts/native_cycle.py"),
        "tests/test_native_cycle.py": sha256(REPO_ROOT / "tests/test_native_cycle.py"),
    }

    native = json.loads((package / "native-results.json").read_text(encoding="utf-8"))
    assert native["schemaVersion"] == 2
    assert native["snapshot"]["manifestSha256"] == SNAPSHOT_MANIFEST_SHA256
    assert native["snapshot"]["declaredFiles"] == native["snapshot"]["actualFiles"] == 5099
    for key in ("missing", "extra", "mismatch", "symlinks"):
        assert native["snapshot"][key] == []

    artifacts = native["machineProducedArtifacts"]
    assert native["rawResultSha256Anchors"] == RAW_RESULT_SHA256
    assert artifacts["codeIdentityFile"] == "candidate-code-identity.json"
    assert artifacts["codeIdentityFileSha256"] == sha256(package / artifacts["codeIdentityFile"])
    assert artifacts["processCleanupChecksFile"] == "process-cleanup-checks.json"
    assert artifacts["processCleanupChecksFileSha256"] == PROCESS_CHECKS_SHA256

    for name in ("success", "repeat"):
        declaration = artifacts[name]
        assert declaration["resultFileSha256"] == sha256(package / declaration["resultFile"])
        assert declaration["rawResultFileSha256"] == sha256(package / declaration["rawResultFile"])
        assert declaration["processCheckFile"] == f"{name}-process-check.native"
        assert declaration["receiptFileSha256"] == sha256(package / declaration["receiptFile"])
        run = load_sanitized_result(package, declaration["resultFile"], name)
        receipt = (package / declaration["receiptFile"]).read_bytes()
        assert sha256(package / declaration["receiptFile"]) == RAW_RECEIPT_SHA256[name]
        readable = (package / declaration["readableReceiptFile"]).read_text(encoding="utf-8")
        assert readable == "\n".join(receipt.decode("utf-8-sig", errors="strict").splitlines())
        assert declaration["readableReceiptFileSha256"] == sha256(package / declaration["readableReceiptFile"])
        assert (package / declaration["createResultFile"]).read_bytes().decode("utf-8-sig").strip() == "0"
        assert sha256(package / declaration["createResultFile"]) == RESULT_ZERO_SHA256
        assert (package / declaration["loadResultFile"]).read_bytes().decode("utf-8-sig").strip() == "0"
        assert sha256(package / declaration["loadResultFile"]) == RESULT_ZERO_SHA256
        assert sha256(package / declaration["loadLogFile"]) == LOAD_LOG_SHA256
        create_log = (package / declaration["createLogFile"]).read_text(encoding="utf-8-sig").splitlines()
        assert create_log == ['Creation of infobase ("File=<RUN_ROOT>/ib;Locale = "en_US_POSIX";") completed successfully']
        assert run["create"]["logSha256"] == CREATE_LOG_SHA256[name]
        lines = receipt.decode("utf-8-sig", errors="strict").splitlines()
        assert lines[-1] == "complete###true"
        assert run["status"] == "runtime_contract_completed"
        assert run["specSha256"] and len(run["specSha256"]) == 64
        assert run["input"]["sourceTreeSha256"] == run["input"]["workCopyTreeSha256"]
        assert run["input"]["sourceTreeSha256"] == run["inputAfter"]["sha256"]
        assert run["input"]["directories"] == run["inputAfter"]["directories"] == 4847
        assert run["create"]["dumpResult"] == "0"
        assert run["create"]["resultSha256"] == RESULT_ZERO_SHA256
        assert run["load"]["dumpResult"] == "0"
        assert run["load"]["resultSha256"] == RESULT_ZERO_SHA256
        assert run["load"]["logSha256"] == LOAD_LOG_SHA256
        assert run["runtime"]["completeMarker"] == "complete###true"
        assert run["runtime"]["stableReads"] >= 2
        assert run["runtime"]["receiptSha256"] == RAW_RECEIPT_SHA256[name]
        assert run["runtime"]["receiptBytes"] == len(receipt)
        commands = run["commands"]
        assert "CREATEINFOBASE" in commands["create"]
        assert "/LoadConfigFromFiles" in commands["load"]
        assert "/UpdateDBCfg" in commands["load"]
        assert "ENTERPRISE" in commands["runtime"]
        assert all("<REPO_ROOT>" in argument for argument in (
            commands["create"][0], commands["create"][4],
            commands["load"][0], commands["runtime"][0],
        ))

    timeout_declaration = artifacts["timeout"]
    assert timeout_declaration["resultFileSha256"] == sha256(package / timeout_declaration["resultFile"])
    assert timeout_declaration["rawResultFileSha256"] == sha256(package / timeout_declaration["rawResultFile"])
    assert timeout_declaration["processCheckFile"] == "timeout-process-check.native"
    assert timeout_declaration["receiptExpected"] is False
    timeout = load_sanitized_result(package, timeout_declaration["resultFile"], "timeout")
    assert (package / timeout_declaration["createResultFile"]).read_bytes().decode("utf-8-sig").strip() == "0"
    assert sha256(package / timeout_declaration["createResultFile"]) == RESULT_ZERO_SHA256
    assert (package / timeout_declaration["loadResultFile"]).read_bytes().decode("utf-8-sig").strip() == "0"
    assert sha256(package / timeout_declaration["loadResultFile"]) == RESULT_ZERO_SHA256
    assert sha256(package / timeout_declaration["loadLogFile"]) == LOAD_LOG_SHA256
    timeout_create_log = (package / timeout_declaration["createLogFile"]).read_text(encoding="utf-8-sig").splitlines()
    assert timeout_create_log == ['Creation of infobase ("File=<RUN_ROOT>/ib;Locale = "en_US_POSIX";") completed successfully']
    assert timeout["create"]["logSha256"] == CREATE_LOG_SHA256["timeout"]
    assert timeout["status"] == "runtime_timeout"
    assert timeout["failedStage"] == "runtime"
    assert timeout["errorType"] == "TimeoutError"
    assert timeout["error"] == "runtime completion marker not observed within 3s"
    assert timeout["create"]["dumpResult"] == timeout["load"]["dumpResult"] == "0"
    assert timeout["input"]["sourceTreeSha256"] == timeout["inputAfter"]["sha256"]

    cleanup_path = package / "process-cleanup-checks.json"
    assert sha256(cleanup_path) == PROCESS_CHECKS_SHA256
    cleanup = json.loads(cleanup_path.read_text(encoding="utf-8"))
    assert cleanup["schemaVersion"] == 1
    assert cleanup["sourceKind"] == "summary bound to exact post-run /proc scanner stdout artifacts"
    assert set(cleanup["runs"]) == {"success", "repeat", "timeout"}
    for name, run in cleanup["runs"].items():
        artifact = package / run["artifactFile"]
        assert run["artifactFile"] == f"{name}-process-check.native"
        assert run["artifactSha256"] == sha256(artifact)
        assert artifact.read_bytes() == b"[]\n"
        assert run["activeNativeProcessesAfterRun"] == []

    repeat = native["repeatComparison"]
    assert repeat["exactKeyOrderParity"] is True
    assert repeat["unexpectedBehaviorDifferences"] == []
    assert repeat["meaningfulObservationParity"] is True

    cost = json.loads((package / "cost-ledger.json").read_text(encoding="utf-8"))
    assert cost["afterTaskPreparation"]["stableEntrypointsPerRun"] == 1
    assert cost["afterTaskPreparation"]["manualPathSubstitutionsPerRun"] == 0
    assert cost["afterTaskPreparation"]["manualProcessCleanupOperationsOnSuccess"] == 0
    assert cost["nativeAttempts"] == {"success": 1, "repeat": 1, "timeout": 1}
    assert cost["verdict"] == "LOW-COST LIFECYCLE LOOP / END-TO-END TASK COST NOT CLAIMED"
