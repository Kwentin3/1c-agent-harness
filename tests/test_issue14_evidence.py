from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from issue14_evidence_validator import rewrite_manifest, validate_package

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments" / "issue14-business-rule-20260827"


class Issue14EvidencePackageTests(unittest.TestCase):
    """Validates the bounded issue #14 evidence package.

    The owner reproduced a false positive where changing a GREEN summary value
    such as ``inventoryAfterA`` to ``999`` still left the suite green. These
    tests make the package fail closed: hashes/manifest closure are necessary
    but not sufficient; receipt semantics and summary values are revalidated.
    """

    def test_package_manifest_and_semantics_validate(self) -> None:
        validate_package(PACKAGE)

    def test_negative_green_summary_inventory_after_mutation_rejected_even_with_refreshed_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "pkg"
            shutil.copytree(PACKAGE, dst)
            summary_path = dst / "green-production-summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["observations"]["invalidCasesRejectedAtomically"]["negative_single"]["inventoryAfterA"] = "999"
            summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            rewrite_manifest(dst)
            with self.assertRaises(AssertionError):
                validate_package(dst)

    def test_negative_unlisted_file_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "pkg"
            shutil.copytree(PACKAGE, dst)
            (dst / "unlisted.txt").write_text("smuggled", encoding="utf-8")
            with self.assertRaises(AssertionError):
                validate_package(dst)

    def test_negative_native_output_hash_mutation_rejected_even_with_refreshed_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "pkg"
            shutil.copytree(PACKAGE, dst)
            native_path = dst / "native-invocations.json"
            native = json.loads(native_path.read_text(encoding="utf-8"))
            native["runs"]["canonical-green-2"]["outputs"]["runtimeResultJsonSha256"] = "0" * 64
            native_path.write_text(json.dumps(native, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            rewrite_manifest(dst)
            with self.assertRaises(AssertionError):
                validate_package(dst)

    def test_negative_native_argv_mutations_rejected_even_with_refreshed_manifest(self) -> None:
        mutators = {
            "remove_update_db_cfg": lambda native: native["runs"]["canonical-green-2"]["commands"]["load"].remove("/UpdateDBCfg"),
            "redirect_runtime_out": lambda native: native["runs"]["canonical-green-2"]["commands"]["runtime"].__setitem__(
                native["runs"]["canonical-green-2"]["commands"]["runtime"].index("<RUN_DIR>/logs/run.log"),
                "<RUN_DIR>/logs/other.log",
            ),
            "insert_unexpected_runtime_flag": lambda native: native["runs"]["canonical-green-2"]["commands"]["runtime"].insert(
                native["runs"]["canonical-green-2"]["commands"]["runtime"].index("ENTERPRISE") + 1,
                "/UnexpectedFlag",
            ),
        }
        for name, mutate in mutators.items():
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as td:
                    dst = Path(td) / "pkg"
                    shutil.copytree(PACKAGE, dst)
                    native_path = dst / "native-invocations.json"
                    native = json.loads(native_path.read_text(encoding="utf-8"))
                    mutate(native)
                    native_path.write_text(json.dumps(native, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    rewrite_manifest(dst)
                    with self.assertRaises(AssertionError):
                        validate_package(dst)

    def test_negative_extra_receipt_line_rejected_even_with_refreshed_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "pkg"
            shutil.copytree(PACKAGE, dst)
            receipt_path = dst / "canonical-green-2-receipt.txt"
            receipt_path.write_text(receipt_path.read_text(encoding="utf-8-sig") + "extra###boom\n", encoding="utf-8")
            rewrite_manifest(dst)
            with self.assertRaises(AssertionError):
                validate_package(dst)


if __name__ == "__main__":
    unittest.main()
