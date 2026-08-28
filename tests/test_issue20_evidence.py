from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from issue20_evidence_validator import rewrite_manifest, validate_package

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments" / "issue20-native-cycle-20260827"


class Issue20EvidencePackageTests(unittest.TestCase):
    def test_package_manifest_and_claims_validate(self) -> None:
        validate_package(PACKAGE)

    def test_historical_candidate_code_identity_forgery_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "package"
            shutil.copytree(PACKAGE, package)
            identity_path = package / "candidate-code-identity.json"
            identity = json.loads(identity_path.read_text(encoding="utf-8"))
            identity["codeIdentity"]["scripts/native_cycle.py"] = "0" * 64
            identity_path.write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
            rewrite_manifest(package)
            with self.assertRaises(AssertionError):
                validate_package(package)

    def test_changed_success_status_is_rejected_after_manifest_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "package"
            shutil.copytree(PACKAGE, package)
            result_path = package / "success-result.json"
            result = json.loads(result_path.read_text(encoding="utf-8"))
            result["sanitizedResult"]["status"] = "PASS"
            result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            rewrite_manifest(package)
            with self.assertRaises(AssertionError):
                validate_package(package)

    def test_coordinated_raw_digest_forgery_is_rejected_after_manifest_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "package"
            shutil.copytree(PACKAGE, package)
            forged = "0" * 64
            result_path = package / "success-result.json"
            result = json.loads(result_path.read_text(encoding="utf-8"))
            result["rawLocalSha256"] = forged
            result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            native_path = package / "native-results.json"
            native = json.loads(native_path.read_text(encoding="utf-8"))
            native["rawResultSha256Anchors"]["success"] = forged
            native["machineProducedArtifacts"]["success"]["resultFileSha256"] = (
                hashlib.sha256(result_path.read_bytes()).hexdigest()
            )
            native_path.write_text(json.dumps(native, indent=2) + "\n", encoding="utf-8")
            rewrite_manifest(package)
            with self.assertRaises(AssertionError):
                validate_package(package)

    def test_process_cleanup_claim_forgery_is_rejected_after_manifest_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "package"
            shutil.copytree(PACKAGE, package)
            checks_path = package / "process-cleanup-checks.json"
            checks = json.loads(checks_path.read_text(encoding="utf-8"))
            checks["runs"]["success"]["activeNativeProcessesAfterRun"] = [{"pid": 123, "name": "1cv8t"}]
            checks_path.write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
            rewrite_manifest(package)
            with self.assertRaises(AssertionError):
                validate_package(package)

    def test_private_path_is_rejected_after_manifest_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "package"
            shutil.copytree(PACKAGE, package)
            readme = package / "README.md"
            readme.write_text(readme.read_text(encoding="utf-8") + "\n/workspace/private\n", encoding="utf-8")
            rewrite_manifest(package)
            with self.assertRaises(AssertionError):
                validate_package(package)

    def test_unlisted_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "package"
            shutil.copytree(PACKAGE, package)
            (package / "unlisted.txt").write_text("unexpected\n", encoding="utf-8")
            with self.assertRaises(AssertionError):
                validate_package(package)


if __name__ == "__main__":
    unittest.main()
