from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "package-manifest.json"
CANDIDATE_COMMIT = "41ced17f3f01c0661bb50dfa69bcd36ca3bfb109"
CANDIDATE_TREE = "12e34ae765628954cc7f1895ceab1e3d76cd26d1"
CODE_IDENTITY = {
    "scripts/native_cycle.py": "f1dfe8a774f3093ae5e4ea479309e10b1dfaf3384c771dcdfdcf2a810c93fd91",
    "tests/test_native_cycle.py": "72af3ef7520417f9284e24bceb1c9dbc19f529d4b743ce1e25ca5388b598f2be",
}
SNAPSHOT_MANIFEST_SHA256 = "70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691"
BASELINE_RECEIPT_SHA256 = "bc7d3f5c31de4bd291b6939d1a24ce206b8fd65d045ca2fb6797e53ff42fa77a"
PROCESS_CHECK_SHA256 = "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"
RAW_SHA256 = {
    "success": {
        "result": "e14e63a8eda7a5a90b1a88b5db8c345f923e6dd958a8b7c8698af4d96bb9a279",
        "receipt": "f0ce4f134f857a9b07fbdc266c75108f478b1c332c5dfc937ddc94168604e5ac",
        "spec": "6c91251fb33d61c53cabfb7ead16bdb9707da3be970bb08ea79365ac24bcb755",
        "createLog": "7690d1096d3951cfb553a61fd0c83fd008e7c0d59dc039d0f4e3f421a0e9f347",
        "createResult": "e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083",
        "loadLog": "4d841be04b71dd0ee7cfebcfa7af194d74902e2ec1c213987889d7d3940c0f86",
        "loadResult": "e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083",
        "runLog": "e8d8977dd4eafc3aed5271e9fd63591f0f3bd23cdb157a9bfe6e581bd3a9c149",
    },
    "repeat": {
        "result": "4ef45ad614789c2686f3b9d0bd1e8c990222b18d5c48a6a6143cb0b2785e63b4",
        "receipt": "525e1af3f27ac54b1caa6ac8c303fa1249116b39859858f9b2ca9420ab334394",
        "spec": "bcada580a1fd6e925610e686777cffcbd03287c7838d4e4c9caa1b69a8b9543c",
        "createLog": "96e2e9a90744582bde9ff6b3287dceffd1e77a81a5b73a79d118206bf6b16b41",
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


def _native_repo_root(result: dict[str, object]) -> str:
    commands = result.get("commands")
    assert isinstance(commands, dict)
    runtime = commands.get("runtime")
    assert isinstance(runtime, list)
    roots = {
        value.split("/.local/", 1)[0]
        for value in runtime
        if isinstance(value, str) and value.startswith("/") and "/.local/" in value
    }
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
        native_root = _native_repo_root(result)
        assert result_envelope["sanitizedResult"] == sanitize(result, native_root=native_root)
        results[label] = result

        spec_envelope = json.loads((package / f"{label}-spec.json").read_text(encoding="utf-8"))
        assert spec_envelope["rawSha256"] == RAW_SHA256[label]["spec"]
        assert spec_envelope["sanitizedSpec"] == sanitize(
            json.loads(raw_payloads["spec"]), native_root=native_root
        )

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
