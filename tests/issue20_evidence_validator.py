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
    "success-run-log.native",
    "success-process-check.native",
    "repeat-result.json",
    "repeat-result.raw.json.gz",
    "repeat-receipt.native",
    "repeat-receipt.txt",
    "repeat-create-log.txt",
    "repeat-create-result.native",
    "repeat-load-log.native",
    "repeat-load-result.native",
    "repeat-run-log.native",
    "repeat-process-check.native",
    "timeout-result.json",
    "timeout-result.raw.json.gz",
    "timeout-create-log.txt",
    "timeout-create-result.native",
    "timeout-load-log.native",
    "timeout-load-result.native",
    "timeout-run-log.native",
    "timeout-process-check.native",
    "process-cleanup-checks.json",
}
SNAPSHOT_MANIFEST_SHA256 = "70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691"
RESULT_ZERO_SHA256 = "e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083"
LOAD_LOG_SHA256 = "4d841be04b71dd0ee7cfebcfa7af194d74902e2ec1c213987889d7d3940c0f86"
RAW_RESULT_SHA256 = {
    "success": "51ce62a3e5af1f637639ede5520ed20b0c85a2caaabd76fada22f6b9ed11d850",
    "repeat": "c62286068ebbe0df51d4f86d1b41b9ca3300a454c24c5964001016905a3d100b",
    "timeout": "854dd6bee25722a2a50699e784b569e241e47f303a632f9c736744d798beabc2",
}
RAW_RECEIPT_SHA256 = {
    "success": "ff421393ffbce2bee31fe682310c90fc91f5e9a07256111e834ff9879b3ba04e",
    "repeat": "02e9054091e7ab3ba9297b6ec02a60b29253b272905b0f190e86cabc153aa524",
}
CREATE_LOG_SHA256 = {
    "success": "8b9f50c80935f9651474120bd47bb54e8f2c15166cc22ca668734dd9e8d5e59b",
    "repeat": "714f1178f1a2d13c512dc0afeec054553ae3b28fbf1313f0d3f36974b61d8708",
    "timeout": "9d861e72e19fe2189fe601cf3bf5609e093ce9789728cf47c9432f96a670883d",
}
PROCESS_CHECKS_SHA256 = "3c52361bc98454b9f3848995042d8f6e749956c7ad92402a4582c5513c9ed78d"
CANDIDATE_CODE_IDENTITY = {
    "scripts/native_cycle.py": "e8671770ff6941088c11d173b6303b8997ffaa672b672dcb532abbe3a3eac998",
    "tests/test_native_cycle.py": "e998cff2f9d5d81af2393b279085a5601fee3848d78a74316374bb5960a890c2",
}
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
    assert code_identity["codeIdentity"] == CANDIDATE_CODE_IDENTITY

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
        assert declaration["runLogFile"] == f"{name}-run-log.native"
        assert declaration["runLogFileSha256"] == sha256(package / declaration["runLogFile"])
        assert declaration["runResultExpected"] is False
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
        assert run["input"]["sourceTreeSha256"] == run["input"]["copiedTreeSha256"]
        assert run["input"]["loadTreeSha256"] != run["input"]["sourceTreeSha256"]
        assert len(run["input"]["loadTreeSha256"]) == 64
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
        assert run["runtime"]["receipt"]["state"] == "regular"
        assert run["runtime"]["receipt"]["terminalMarker"] is True
        log_output = run["runtime"]["outputs"]["log"]
        log_artifact = package / declaration["runLogFile"]
        assert log_output["state"] == "regular"
        assert log_output["bytes"] == log_artifact.stat().st_size
        assert log_output["sha256"] == sha256(log_artifact)
        assert run["runtime"]["outputs"]["result"] == {"state": "absent"}
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
    assert timeout_declaration["runLogFile"] == "timeout-run-log.native"
    assert timeout_declaration["runLogFileSha256"] == sha256(
        package / timeout_declaration["runLogFile"]
    )
    assert timeout_declaration["runResultExpected"] is False
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
    assert timeout["input"]["sourceTreeSha256"] == timeout["input"]["copiedTreeSha256"]
    assert timeout["input"]["loadTreeSha256"] != timeout["input"]["sourceTreeSha256"]
    assert timeout["input"]["sourceTreeSha256"] == timeout["inputAfter"]["sha256"]
    runtime = timeout["runtime"]
    assert runtime["completed"] is False
    assert runtime["failureKind"] == "timeout"
    assert isinstance(runtime["processReturn"], int)
    assert runtime["receipt"] == {"state": "absent"}
    log_output = runtime["outputs"]["log"]
    log_artifact = package / timeout_declaration["runLogFile"]
    assert log_output["state"] == "regular"
    assert log_output["bytes"] == log_artifact.stat().st_size
    assert log_output["sha256"] == sha256(log_artifact)
    assert runtime["outputs"]["result"] == {"state": "absent"}

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
    preparation = cost["callerOwnedPreparationPerNewBinding"]
    assert preparation["supportedEntrypoint"] is False
    assert preparation["measuredWallSeconds"] is None
    assert preparation["manualActionsCount"] == len(preparation["manualActions"]) == 3
    assert preparation["repeatRequiresNewBinding"] is True
    execution = cost["nativeExecutionAfterBinding"]
    assert execution["stableEntrypointsPerRun"] == 1
    assert execution["manualPathSubstitutionsPerRun"] == 0
    assert execution["manualProcessCleanupOperationsOnSuccess"] == 0
    assert cost["nativeAttempts"] == {"success": 1, "repeat": 1, "timeout": 1}
    assert cost["verdict"] == (
        "BOUNDED NATIVE EXECUTOR / PREPARATION REMAINS MANUAL / LOW-COST NOT CLAIMED"
    )
