from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments" / "issue43-inventory-transfer-core-loop"
sys.path.insert(0, str(PACKAGE))

from validate import validate_package, validate_receipt  # type: ignore  # noqa: E402


class Issue43EvidenceTests(unittest.TestCase):
    def assert_patch_substitution_rejected(self, patch_name: str) -> None:
        with tempfile.TemporaryDirectory() as td:
            package = Path(td) / "package"
            manifest = json.loads((PACKAGE / "package-manifest.json").read_text(encoding="utf-8"))
            package.mkdir()
            for name in manifest["files"]:
                shutil.copy2(PACKAGE / name, package / name)
            target = package / patch_name
            target.write_bytes(target.read_bytes() + b"\n")
            manifest["sha256"][patch_name] = hashlib.sha256(target.read_bytes()).hexdigest()
            (package / "package-manifest.json").write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(AssertionError):
                validate_package(package)

    def test_complete_package_validates(self) -> None:
        validate_package(PACKAGE)

    def test_foreign_run_identity_is_rejected(self) -> None:
        request = json.loads((PACKAGE / "bound-green-1-request.json").read_text(encoding="utf-8"))
        receipt = (PACKAGE / "bound-green-1-receipt.txt").read_text(encoding="utf-8-sig")
        receipt = receipt.replace(request["runId"], "00000000-0000-4000-8000-000000000000", 1)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "receipt.txt"
            path.write_text(receipt, encoding="utf-8")
            with self.assertRaises(AssertionError):
                validate_receipt(path, request, expected_scenario="issue43-bound-green-1", expect_rule=True)

    def test_nonce_echo_cannot_become_success(self) -> None:
        request = json.loads((PACKAGE / "bound-green-1-request.json").read_text(encoding="utf-8"))
        forged = copy.deepcopy(request)
        forged["caseId"] = forged["nonce"]
        with self.assertRaises(AssertionError):
            validate_receipt(
                PACKAGE / "bound-green-1-receipt.txt",
                forged,
                expected_scenario="issue43-bound-green-1",
                expect_rule=True,
            )

    def test_partial_receipt_is_rejected(self) -> None:
        request = json.loads((PACKAGE / "bound-green-1-request.json").read_text(encoding="utf-8"))
        lines = (PACKAGE / "bound-green-1-receipt.txt").read_text(encoding="utf-8-sig").splitlines()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "receipt.txt"
            path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
            with self.assertRaises(AssertionError):
                validate_receipt(path, request, expected_scenario="issue43-bound-green-1", expect_rule=True)

    def test_business_wrong_receipt_is_rejected(self) -> None:
        request = json.loads((PACKAGE / "bound-green-1-request.json").read_text(encoding="utf-8"))
        receipt = (PACKAGE / "bound-green-1-receipt.txt").read_text(encoding="utf-8-sig")
        receipt = receipt.replace("sameInventoryMovementCount###0", "sameInventoryMovementCount###2", 1)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "receipt.txt"
            path.write_text(receipt, encoding="utf-8")
            with self.assertRaises(AssertionError):
                validate_receipt(path, request, expected_scenario="issue43-bound-green-1", expect_rule=True)

    def test_production_patch_substitution_survives_manifest_but_is_rejected(self) -> None:
        self.assert_patch_substitution_rejected("production.patch")

    def test_instrumentation_patch_substitution_survives_manifest_but_is_rejected(self) -> None:
        for lane in (1, 2):
            with self.subTest(lane=lane):
                self.assert_patch_substitution_rejected(
                    f"bound-green-{lane}-instrumentation.patch"
                )


if __name__ == "__main__":
    unittest.main()
