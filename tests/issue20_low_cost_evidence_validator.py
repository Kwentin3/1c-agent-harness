from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "package-manifest.json"
CANDIDATE_COMMIT = "a4e1509d44147229b4a515c7cd0013efba34762b"
CANDIDATE_TREE = "070ac2fe8e93fce22a8771989e56dad8e9531457"
CODE_IDENTITY = {
    "scripts/native_cycle.py": "9afc9e99c6ae3bf853113605c2c4b3be8e049240c46256b196a45062e7678ad1",
    "tests/test_native_cycle.py": "a5dc624045f111f6f1eb9b8fca3499887a671897d8aafad4bd70e751ab369f26",
}
SNAPSHOT_MANIFEST_SHA256 = "70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691"
BASELINE_RECEIPT_SHA256 = "bc7d3f5c31de4bd291b6939d1a24ce206b8fd65d045ca2fb6797e53ff42fa77a"
PROCESS_CHECK_SHA256 = "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"
RAW_SHA256 = {
    "success": {
        "result": "eced70bff9a249f4ca86c3a187b7deb9a88fd3fa6a50d010563bffc29d91bb7b",
        "receipt": "0ee86024bac073c92b7d63f3d5a0d07ebcf9ece8d879a9da3d03bca5818fa9b1",
        "spec": "e981201bce74c0571cbae5457ecad4a11fdd6ca60918dae966078506c4be2371",
        "createLog": "f590e66b1c633fb87c790cbc2d1a1eb40249aff5539e76620546c3ef95a09350",
        "createResult": "e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083",
        "loadLog": "4d841be04b71dd0ee7cfebcfa7af194d74902e2ec1c213987889d7d3940c0f86",
        "loadResult": "e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083",
        "runLog": "e8d8977dd4eafc3aed5271e9fd63591f0f3bd23cdb157a9bfe6e581bd3a9c149",
        "storageMeasurement": "26712a2afc77cff1fd942def6af59dc8c85dca904419ef8d993c88ab5995722d",
    },
    "repeat": {
        "result": "a2e82a6636b643184d23521fd45739449f00dcf00697678ad8312fa44b207a06",
        "receipt": "f32dfbd3c686da074152aeb6b161976f3433a5e4e8c1fe1a4f03650ba3888b3a",
        "spec": "1e3b331395df311db43dd6795447fd08767dfc0f006a8a1b490e0743c8d6f61b",
        "createLog": "30f76cf5260527cc3dd69e9e317f1d9f3ca09fc875a4b2c7b7120182a04780a2",
        "createResult": "e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083",
        "loadLog": "4d841be04b71dd0ee7cfebcfa7af194d74902e2ec1c213987889d7d3940c0f86",
        "loadResult": "e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083",
        "runLog": "e8d8977dd4eafc3aed5271e9fd63591f0f3bd23cdb157a9bfe6e581bd3a9c149",
        "storageMeasurement": "bcf274c088581e0034d349b7683955927f289554b7630901c661587561b8cfd3",
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
    "storageMeasurement": "storage-measurement.raw.json.gz",
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
    "storage-measurement.json", "storage-measurement.raw.json.gz",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _candidate_file_sha256(relative: str) -> str:
    tree = subprocess.run(
        ["git", "rev-parse", f"{CANDIDATE_COMMIT}^{{tree}}"],
        cwd=REPO_ROOT, text=True, capture_output=True,
    )
    assert tree.returncode == 0 and tree.stdout.strip() == CANDIDATE_TREE
    source = subprocess.run(
        ["git", "show", f"{CANDIDATE_COMMIT}:{relative}"],
        cwd=REPO_ROOT, capture_output=True,
    )
    assert source.returncode == 0
    return hashlib.sha256(source.stdout).hexdigest()


def _native_repo_root(result: dict[str, object]) -> str:
    commands = result.get("commands")
    assert isinstance(commands, dict)
    runtime = commands.get("runtime")
    assert isinstance(runtime, list)
    roots = set()
    for value in runtime:
        if isinstance(value, str) and value.startswith("/") and "/.local/" in value:
            root = value.split("/.local/", 1)[0]
            assert root
            roots.add(root)
    assert len(roots) == 1
    return roots.pop()


def sanitize(value: object, *, native_root: Optional[str] = None) -> object:
    if isinstance(value, dict):
        return {key: sanitize(item, native_root=native_root) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item, native_root=native_root) for item in value]
    if isinstance(value, str):
        if native_root is not None:
            value = value.replace(native_root, "<REPO_ROOT>")
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
        relative: _candidate_file_sha256(relative) for relative in CODE_IDENTITY
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
        native_root = _native_repo_root(result)
        assert result_envelope["sanitizedResult"] == sanitize(result, native_root=native_root)
        results[label] = result

        spec_envelope = json.loads((package / f"{label}-spec.json").read_text(encoding="utf-8"))
        assert spec_envelope["rawSha256"] == RAW_SHA256[label]["spec"]
        assert spec_envelope["sanitizedSpec"] == sanitize(
            json.loads(raw_payloads["spec"]), native_root=native_root
        )

        measurement_envelope = json.loads(
            (package / f"{label}-storage-measurement.json").read_text(encoding="utf-8")
        )
        assert measurement_envelope["rawSha256"] == RAW_SHA256[label]["storageMeasurement"]
        measurement = json.loads(raw_payloads["storageMeasurement"])
        assert measurement_envelope["sanitizedMeasurement"] == sanitize(
            measurement, native_root=native_root
        )
        assert measurement["returnCode"] == 0
        assert measurement["stdoutResult"] == result
        assert measurement["postCommandRetainedLogicalBytes"] > 0
        assert measurement["sampledPeakLogicalBytes"] >= result["storageCompaction"][
            "preCompactionLogicalBytes"
        ]

        receipt = _rows(raw_payloads["receipt"])
        assert (package / f"{label}-receipt.txt").read_bytes().decode("utf-8") == (
            sanitize(raw_payloads["receipt"].decode("utf-8-sig"), native_root=native_root)
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
        assert acceptance["storageCompactionStatus"] == "completed"
        assert acceptance["manualCleanupActions"] == 0

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
        storage = result["storageCompaction"]
        assert storage["status"] == "completed"
        assert storage["manualCleanupActions"] == 0
        assert storage["configuredTargets"] == storage["completedRemovedPaths"] == [
            "frozen-input", "run/work-copy", "run/ib", "run/home", "run/tmp",
        ]
        assert storage["removedLogicalBytes"] > 0
        assert storage["preCompactionLogicalBytes"] > storage["removedLogicalBytes"]
        assert measurement["postCommandRetainedLogicalBytes"] == (
            storage["retainedLogicalBytesExcludingResult"] + len(raw_payloads["result"])
        )
        for key in ("createLog", "createResult", "loadLog", "loadResult", "runLog"):
            expected_text = raw_payloads[key].decode("utf-8-sig", errors="strict").replace(
                native_root, "<REPO_ROOT>"
            ).replace(str(REPO_ROOT), "<REPO_ROOT>").replace(
                "/home/hermeswebui", "<USER_HOME>"
            ).replace("\r\n", "\n")
            assert (package / f"{label}-{key}.txt").read_bytes().decode("utf-8") == expected_text

    native = json.loads((package / "native-results.json").read_text(encoding="utf-8"))
    assert native["schemaVersion"] == 1 and native["issue"] == 20
    assert native["candidateCodeIdentityFileSha256"] == sha256(package / "candidate-code-identity.json")
    assert native["snapshotVerificationFileSha256"] == sha256(package / "snapshot-verification.json")

    primary_files = {
        "result": ("result.raw.json.gz", "result.json"),
        "receipt": ("receipt.raw.gz", "receipt.txt"),
        "spec": ("spec.raw.json.gz", "spec.json"),
        "storageMeasurement": (
            "storage-measurement.raw.json.gz", "storage-measurement.json"
        ),
    }
    expected_machine_artifacts = {}
    for label, result in results.items():
        primary = {
            key: {
                "rawFile": f"{label}-{raw_suffix}",
                "rawSha256": RAW_SHA256[label][key],
                "sanitizedFile": f"{label}-{sanitized_suffix}",
                "sanitizedSha256": sha256(package / f"{label}-{sanitized_suffix}"),
            }
            for key, (raw_suffix, sanitized_suffix) in primary_files.items()
        }
        expected_machine_artifacts[label] = {
            "invocationLabel": Path(
                result["preparedInvocation"]["invocationRoot"]
            ).name,
            **primary,
            "acceptanceFile": f"{label}-acceptance.json",
            "acceptanceSha256": sha256(package / f"{label}-acceptance.json"),
            "artifacts": {
                key: {
                    "rawFile": f"{label}-{RAW_SUFFIX[key]}",
                    "rawSha256": RAW_SHA256[label][key],
                    "sanitizedFile": f"{label}-{key}.txt",
                    "sanitizedSha256": sha256(package / f"{label}-{key}.txt"),
                }
                for key in ("createLog", "createResult", "loadLog", "loadResult", "runLog")
            },
        }
    assert native["machineProducedArtifacts"] == expected_machine_artifacts

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
    assert cost["manualCleanupActionsPerRun"] == 0
    assert cost["sameCommandUsedForRepeat"] is True
    assert cost["nativeAttempts"] == {"success": 1, "repeat": 1}
    assert cost["fullWallSeconds"] == {
        label: results[label]["totalDurationSeconds"] for label in results
    }
    assert cost["executorSeconds"] == {
        label: results[label]["durationSeconds"] for label in results
    }
    measurements = {
        label: json.loads(gzip.decompress(
            (package / f"{label}-storage-measurement.raw.json.gz").read_bytes()
        ))
        for label in results
    }
    assert cost["externalWallSeconds"] == {
        label: measurements[label]["externalWallSeconds"] for label in results
    }
    assert cost["sampledPeakLogicalBytes"] == {
        label: measurements[label]["sampledPeakLogicalBytes"] for label in results
    }
    assert cost["postCommandRetainedLogicalBytes"] == {
        label: measurements[label]["postCommandRetainedLogicalBytes"] for label in results
    }
    assert cost["preCompactionLogicalBytes"] == {
        label: results[label]["storageCompaction"]["preCompactionLogicalBytes"]
        for label in results
    }
    assert cost["removedLogicalBytes"] == {
        label: results[label]["storageCompaction"]["removedLogicalBytes"]
        for label in results
    }
    assert cost["compactionSeconds"] == {
        label: results[label]["storageCompaction"]["durationSeconds"]
        for label in results
    }
    assert cost["codeCostBoundary"] == {
        "baselineCommit": "c4e40ff96a36c709cab46df651ee0564647f3146",
        "candidateCommit": CANDIDATE_COMMIT,
        "candidateTree": CANDIDATE_TREE,
        "measuredPaths": ["scripts/native_cycle.py", "tests/test_native_cycle.py"],
        "rationale": (
            "The full PR delta is measured from the issue #20 low-cost goal-loop base "
            "through the exact native runner bytes used for fresh success/repeat. Later "
            "evidence-only publication commits do not change either measured path."
        ),
    }
    assert cost["fullPrCommonCodeDiff"] == {
        "scripts/native_cycle.py": {
            "added": 530, "removed": 8, "baselineLines": 744, "candidateLines": 1266,
        },
        "tests/test_native_cycle.py": {
            "added": 681, "removed": 0, "baselineLines": 873, "candidateLines": 1554,
        },
    }
    assert cost["boundedStorageCorrectionDiff"] == {
        "baselineCommit": "a3527412118f2c5dc608b0c549a5f4ff0c308d8b",
        "candidateCommit": CANDIDATE_COMMIT,
        "scripts/native_cycle.py": {"added": 157, "removed": 5},
        "tests/test_native_cycle.py": {"added": 271, "removed": 0},
    }
    assert cost["kissAssessment"] == {
        "answer": (
            "The full +530/-8 common runner delta is larger than the original three manual "
            "binding actions but is justified by reproduced lifecycle gaps rather than "
            "speculative framework surface."
        ),
        "justifiedBy": [
            "one supported run-prepared boundary replacing manual freeze, fingerprint, spec, run-root and receipt binding",
            "persisted resultPath and terminal source recheck across preparation, native and failure paths",
            "receipt observation races and detached native descendant cleanup reproduced during exact-tree review",
            "bounded current-invocation storage after owner reproduced unbounded retained artifacts and disk exhaustion",
            "fail-closed partial cleanup, result finalization and native Unix-socket cleanup reproduced by tests or fresh native execution",
        ],
        "scopeControls": [
            "run_cycle remains the only native lifecycle implementation",
            "legacy run --spec behavior is unchanged",
            "no task-specific BSL, semantic oracle, arbitrary command, general cleaner, cross-run retention scan, GUI, RAG, MCP or deployment surface was added",
        ],
    }
    assert cost["verdict"] == (
        "LOW-COST PREPARED-TREE LIFECYCLE PASS; "
        "TASK-SPECIFIC PREPARATION AND SEMANTIC ORACLE REMAIN OUTSIDE THE CAPABILITY"
    )
