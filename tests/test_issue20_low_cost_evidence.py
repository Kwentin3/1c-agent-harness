from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import issue20_low_cost_evidence_validator as evidence_validator
from issue20_low_cost_evidence_validator import rewrite_manifest, validate_package

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments" / "issue20-low-cost-native-cycle-20260828"


class Issue20LowCostEvidenceTests(unittest.TestCase):
    def test_package_manifest_and_claims_validate(self) -> None:
        validate_package(PACKAGE)

    def test_raw_sanitization_uses_native_root_not_checkout_root(self) -> None:
        result = json.loads(gzip.decompress((PACKAGE / "success-result.raw.json.gz").read_bytes()))
        envelope = json.loads((PACKAGE / "success-result.json").read_text(encoding="utf-8"))
        with mock.patch.object(evidence_validator, "REPO_ROOT", Path("/different/checkout")):
            native_root = evidence_validator._native_repo_root(result)
            self.assertEqual(
                evidence_validator.sanitize(result, native_root=native_root),
                envelope["sanitizedResult"],
            )

    def test_unlisted_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "package"
            shutil.copytree(PACKAGE, package)
            (package / "unlisted.txt").write_text("unexpected\n", encoding="utf-8")
            with self.assertRaises(AssertionError):
                validate_package(package)

    def test_changed_cost_claim_is_rejected_after_manifest_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "package"
            shutil.copytree(PACKAGE, package)
            path = package / "cost-ledger.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["manualBindingActionsPerRun"] = 1
            path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
            rewrite_manifest(package)
            with self.assertRaises(AssertionError):
                validate_package(package)

    def test_coordinated_result_and_acceptance_forgery_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "package"
            shutil.copytree(PACKAGE, package)
            raw_path = package / "success-result.raw.json.gz"
            raw = json.loads(gzip.decompress(raw_path.read_bytes()))
            raw["status"] = "PASS"
            forged = json.dumps(raw, separators=(",", ":")).encode("utf-8")
            raw_path.write_bytes(gzip.compress(forged, mtime=0))
            envelope_path = package / "success-result.json"
            envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
            envelope["rawSha256"] = hashlib.sha256(forged).hexdigest()
            envelope["sanitizedResult"]["status"] = "PASS"
            envelope_path.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
            acceptance_path = package / "success-acceptance.json"
            acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
            acceptance["status"] = "PASS"
            acceptance_path.write_text(json.dumps(acceptance, indent=2) + "\n", encoding="utf-8")
            rewrite_manifest(package)
            with self.assertRaises(AssertionError):
                validate_package(package)

    def test_coordinated_receipt_terminal_marker_forgery_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "package"
            shutil.copytree(PACKAGE, package)
            raw_path = package / "repeat-receipt.raw.gz"
            payload = gzip.decompress(raw_path.read_bytes()).replace(
                b"complete###true", b"complete###forged"
            )
            raw_path.write_bytes(gzip.compress(payload, mtime=0))
            readable = payload.decode("utf-8-sig").replace(str(ROOT), "<REPO_ROOT>")
            (package / "repeat-receipt.txt").write_text(
                readable.rstrip("\n") + "\n", encoding="utf-8"
            )
            rewrite_manifest(package)
            with self.assertRaises(AssertionError):
                validate_package(package)

    def test_machine_artifact_linkage_forgery_is_rejected_after_manifest_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "package"
            shutil.copytree(PACKAGE, package)
            validate_package(package)
            native_path = package / "native-results.json"
            native = json.loads(native_path.read_text(encoding="utf-8"))
            receipt = native["machineProducedArtifacts"]["success"]["receipt"]
            receipt["rawFile"] = "nonexistent-forged.raw.gz"
            receipt["rawSha256"] = "0" * 64
            native_path.write_text(json.dumps(native, indent=2) + "\n", encoding="utf-8")
            rewrite_manifest(package)
            with self.assertRaises(AssertionError):
                validate_package(package)

    def test_process_cleanup_forgery_is_rejected_after_manifest_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "package"
            shutil.copytree(PACKAGE, package)
            process_path = package / "post-repeat-process-check.native"
            process_path.write_text('[{"pid":123,"comm":"1cv8t"}]\n', encoding="utf-8")
            cleanup_path = package / "process-cleanup-check.json"
            cleanup = json.loads(cleanup_path.read_text(encoding="utf-8"))
            cleanup["artifactSha256"] = hashlib.sha256(process_path.read_bytes()).hexdigest()
            cleanup["activeNativeProcessesAfterRepeat"] = [{"pid": 123, "comm": "1cv8t"}]
            cleanup_path.write_text(json.dumps(cleanup, indent=2) + "\n", encoding="utf-8")
            rewrite_manifest(package)
            with self.assertRaises(AssertionError):
                validate_package(package)


if __name__ == "__main__":
    unittest.main()
