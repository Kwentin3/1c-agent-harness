from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "package-manifest.json"
CANDIDATE_COMMIT = "4ef4bf3b6e3ce1cd74316d3a35a3ab69476ad330"
CANDIDATE_TREE = "47fa6aa5e2f89bd70373f9e42e5e44567fb0a3e7"
CODE_IDENTITY = {
    "scripts/native_cycle.py": "6141447edced9c69cee970bbe145e3ff1a38e880f9c807d5e6e736a62f5660be",
    "tests/test_native_cycle.py": "d8ba432c2b4cf09c0aa37537f2ed31e723fc4808b30d32e3a65d952b3ff42888",
}
SNAPSHOT_MANIFEST_SHA256 = "70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691"
BASELINE_RECEIPT_SHA256 = "bc7d3f5c31de4bd291b6939d1a24ce206b8fd65d045ca2fb6797e53ff42fa77a"
PROCESS_CHECK_SHA256 = "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"
RAW_SHA256 = {
    "success": {
        "result": "33798e5f285a9932283d0c38e226cc5894eadd57585110776e8790f4e4114765",
        "receipt": "57b05be591de2c6f6166e647f8850705a93d28154a7a38795be645af631a4533",
        "spec": "e29b331ddf7569cae7feb6a32d599f7929f1a4c93c2076032c3230457e9e1e92",
        "createLog": "5cc557e5f1f15222f707feb0558182ec8fb1f5112da775cf5d28918047afa873",
        "createResult": "e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083",
        "loadLog": "4d841be04b71dd0ee7cfebcfa7af194d74902e2ec1c213987889d7d3940c0f86",
        "loadResult": "e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083",
        "runLog": "e8d8977dd4eafc3aed5271e9fd63591f0f3bd23cdb157a9bfe6e581bd3a9c149",
    },
    "repeat": {
        "result": "e31b2f7418d718ea36ce4da70e50988f1839927ee821828aeb6dd6b0108259d1",
        "receipt": "796a37919af796ded650bae0d434d241357c773993788cd1d5ac68629f771719",
        "spec": "678e86210fbd2cdbe1b44bb395405c505c5d93769c71faa25b33e0a5ae393bd5",
        "createLog": "7bea655e6b2752973bff2afe431d012bb879b3ec4f51f7e88ea009f850481777",
        "createResult": "e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083",
        "loadLog": "4d841be04b71dd0ee7cfebcfa7af194d74902e2ec1c213987889d7d3940c0f86",
        "loadResult": "e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083",
        "runLog": "e8d8977dd4eafc3aed5271e9fd63591f0f3bd23cdb157a9bfe6e581bd3a9c149",
    },
}
RAW_SUFFIX = {
    "result": "result.raw.json.gz",
    "receipt": "receipt.raw.gz",
    "spec": "spec.raw.json.gz",
    "createLog": "createLog.raw.gz",
    "createResult": "createResult.raw.gz",
    "loadLog": "loadLog.raw.gz",
    "loadResult": "loadResult.raw.gz",
    "runLog": "runLog.raw.gz",
}
REQUIRED_COMMON = {
    ".gitattributes", "README.md", "candidate-code-identity.json", "cost-ledger.json",
    "native-results.json", "post-repeat-process-check.native", "process-cleanup-check.json",
    "snapshot-verification.json",
}
REQUIRED_PER_RUN = {
    "acceptance.json", "createLog.raw.gz", "createLog.txt", "createResult.raw.gz",
    "createResult.txt", "loadLog.raw.gz", "loadLog.txt", "loadResult.raw.gz",
    "loadResult.txt", "receipt.raw.gz", "receipt.txt", "result.json",
    "result.raw.json.gz", "runLog.raw.gz", "runLog.txt", "spec.json", "spec.raw.json.gz",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sanitize(value: object) -> object:
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        return value.replace(str(REPO_ROOT), "<REPO_ROOT>").replace(
            "/home/hermeswebui", "<USER_HOME>"
        )
    return value


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


def _rows(payload: bytes) -> list[tuple[str, str]]:
    rows = []
    for line in payload.decode("utf-8-sig", errors="strict").splitlines():
        parts = line.split("###", 1)
        assert len(parts) == 2
        rows.append((parts[0], parts[1]))
    return rows


def validate_package(package: Path) -> None:
    required = REQUIRED_COMMON | {
        f"{label}-{suffix}" for label in ("success", "repeat") for suffix in REQUIRED_PER_RUN
    }
    actual = {
        path.relative_to(package).as_posix()
        for path in package.rglob("*")
        if path.is_file()
    }
    assert actual == required | {MANIFEST}
    manifest = json.loads((package / MANIFEST).read_text(encoding="utf-8"))
    assert manifest["schemaVersion"] == 1
    assert set(manifest["artifacts"]) == required
    for relative, expected in manifest["artifacts"].items():
        assert sha256(package / relative) == expected

    for path in package.rglob("*"):
        if path.is_file() and path.suffix != ".gz":
            payload = path.read_bytes()
            assert b"/workspace/" not in payload
            assert b"/home/hermeswebui" not in payload

    identity = json.loads((package / "candidate-code-identity.json").read_text(encoding="utf-8"))
    assert identity == {
        "schemaVersion": 1,
        "candidateCommit": CANDIDATE_COMMIT,
        "candidateTree": CANDIDATE_TREE,
        "nativeRunsExecutedAfterTheseBytesWereCommitted": True,
        "codeIdentity": CODE_IDENTITY,
    }
    assert CODE_IDENTITY == {
        relative: sha256(REPO_ROOT / relative) for relative in CODE_IDENTITY
    }

    snapshot = json.loads((package / "snapshot-verification.json").read_text(encoding="utf-8"))
    assert snapshot == {
        "schemaVersion": 1,
        "manifestSha256": SNAPSHOT_MANIFEST_SHA256,
        "declaredFiles": 5099,
        "actualFiles": 5099,
        "missing": [], "extra": [], "mismatch": [], "symlinks": [],
    }

    process_path = package / "post-repeat-process-check.native"
    assert sha256(process_path) == PROCESS_CHECK_SHA256
    assert process_path.read_bytes() == b"[]\n"
    cleanup = json.loads((package / "process-cleanup-check.json").read_text(encoding="utf-8"))
    assert cleanup["artifactFile"] == process_path.name
    assert cleanup["artifactSha256"] == PROCESS_CHECK_SHA256
    assert cleanup["activeNativeProcessesAfterRepeat"] == []

    baseline_path = REPO_ROOT / "experiments/issue18-sales-invoice-calculation-20260827/green-receipt.txt"
    assert sha256(baseline_path) == BASELINE_RECEIPT_SHA256
    baseline = _rows(baseline_path.read_bytes())
    excluded = {"nonce", "mode", "existing_insufficient_stock.postError"}
    results: dict[str, dict[str, object]] = {}
    for label in ("success", "repeat"):
        raw_payloads = {
            key: gzip.decompress((package / f"{label}-{suffix}").read_bytes())
            for key, suffix in RAW_SUFFIX.items()
        }
        assert {
            key: hashlib.sha256(payload).hexdigest()
            for key, payload in raw_payloads.items()
        } == RAW_SHA256[label]

        result_envelope = json.loads((package / f"{label}-result.json").read_text(encoding="utf-8"))
        assert result_envelope["rawSha256"] == RAW_SHA256[label]["result"]
        result = json.loads(raw_payloads["result"])
        assert result_envelope["sanitizedResult"] == sanitize(result)
        results[label] = result

        spec_envelope = json.loads((package / f"{label}-spec.json").read_text(encoding="utf-8"))
        assert spec_envelope["rawSha256"] == RAW_SHA256[label]["spec"]
        assert spec_envelope["sanitizedSpec"] == sanitize(json.loads(raw_payloads["spec"]))

        receipt = _rows(raw_payloads["receipt"])
        assert (package / f"{label}-receipt.txt").read_bytes().decode("utf-8") == (
            sanitize(raw_payloads["receipt"].decode("utf-8-sig"))
            .replace("\r\n", "\n")
            .rstrip("\n") + "\n"
        )
        assert [key for key, _ in receipt] == [key for key, _ in baseline]
        differences = [
            (old[0], old[1], new[1]) for old, new in zip(baseline, receipt) if old != new
        ]
        assert all(key in excluded for key, _, _ in differences)
        assert [value for key, value in receipt if key == "complete"] == ["false", "true"]

        acceptance = json.loads((package / f"{label}-acceptance.json").read_text(encoding="utf-8"))
        assert acceptance["status"] == "runtime_contract_completed"
        assert acceptance["rows"] == 320
        assert acceptance["uniqueKeys"] == 319
        assert acceptance["keyOrderParityWithIssue18Green"] is True
        assert acceptance["completeProgression"] == ["false", "true"]
        assert acceptance["unexpectedBehaviorDifferences"] == []
        assert acceptance["sourceStable"] is True
        assert acceptance["generatedBindingStatus"] == "generated"
        assert acceptance["runtimeCCount"] == 1

        assert result["status"] == "runtime_contract_completed"
        assert result["preparedInvocation"]["sourceBefore"] == result["preparedInvocation"]["sourceAfter"]
        assert result["preparedInvocation"]["copiedBeforeFreeze"] == result["preparedInvocation"]["sourceBefore"]
        assert result["preparedInvocation"]["generatedBinding"]["status"] == "generated"
        assert result["commands"]["runtime"].count("/C") == 1
        c_index = result["commands"]["runtime"].index("/C")
        assert result["commands"]["runtime"][c_index + 1].endswith("/run/evidence/receipt.txt")
        assert result["runtime"]["receiptSha256"] == RAW_SHA256[label]["receipt"]
        assert result["runtime"]["receipt"]["terminalMarker"] is True
        assert result["input"]["sourceTreeSha256"] == result["input"]["copiedTreeSha256"]
        assert result["input"]["sourceTreeSha256"] == result["inputAfter"]["sha256"]
        assert result["input"]["loadTreeSha256"] == result["preparedInvocation"]["sourceBefore"]["sha256"]
        assert result["totalDurationSeconds"] >= result["durationSeconds"]
        for key in ("createLog", "createResult", "loadLog", "loadResult", "runLog"):
            expected_text = raw_payloads[key].decode("utf-8-sig", errors="strict").replace(
                str(REPO_ROOT), "<REPO_ROOT>"
            ).replace("/home/hermeswebui", "<USER_HOME>").replace("\r\n", "\n")
            assert (package / f"{label}-{key}.txt").read_bytes().decode("utf-8") == expected_text

    native = json.loads((package / "native-results.json").read_text(encoding="utf-8"))
    assert native["schemaVersion"] == 1 and native["issue"] == 20
    assert native["candidateCodeIdentityFileSha256"] == sha256(package / "candidate-code-identity.json")
    assert native["snapshotVerificationFileSha256"] == sha256(package / "snapshot-verification.json")
    comparison = native["repeatComparison"]
    assert all(comparison[key] is True for key in (
        "differentInvocationRoots", "differentSpecSha256", "differentBindingArgvSha256",
        "samePreparedSourceIdentity", "sameFrozenInputIdentity", "semanticKeyOrderParity",
    ))
    assert comparison["unexpectedBehaviorDifferences"] == []

    cost = json.loads((package / "cost-ledger.json").read_text(encoding="utf-8"))
    assert cost["supportedPreparedTreeEntrypoint"] is True
    assert cost["callerCommandBlocksPerRun"] == 1
    assert cost["manualBindingActionsPerRun"] == 0
    assert cost["manualPathSubstitutionsPerRun"] == 0
    assert cost["sameCommandUsedForRepeat"] is True
    assert cost["nativeAttempts"] == {"success": 1, "repeat": 1}
    assert cost["fullWallSeconds"] == {
        label: results[label]["totalDurationSeconds"] for label in results
    }
    assert cost["executorSeconds"] == {
        label: results[label]["durationSeconds"] for label in results
    }
    assert cost["verdict"] == (
        "LOW-COST PREPARED-TREE LIFECYCLE PASS; "
        "TASK-SPECIFIC PREPARATION AND SEMANTIC ORACLE REMAIN OUTSIDE THE CAPABILITY"
    )
