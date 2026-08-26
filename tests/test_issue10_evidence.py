from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments" / "issue10-write-cycle-20260826"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_receipt(path: Path) -> dict:
    """Parse a probe receipt: label -> (value, type)."""
    out = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if "###" not in line:
            continue
        parts = line.split("###")
        if len(parts) < 3:
            raise AssertionError(f"malformed receipt line: {line!r}")
        label = parts[0].strip()
        value = parts[1]
        typ = parts[2]
        if label in out:
            raise AssertionError(f"duplicate label {label!r} in receipt")
        out[label] = (value, typ)
    return out


# Exact expected semantics from the frozen task contract.
EXPECTED_CASES = {
    "tab":    {"red": ("", "Undefined"), "green": ("1234", "Number")},
    "nbsp":   {"red": ("", "Undefined"), "green": ("1234", "Number")},
    "invalid": {"red": ("", "Undefined"), "green": ("", "Undefined")},
    "decimal": {"red": ("1234.56", "Number"), "green": ("1234.56", "Number")},
    "space":  {"red": ("567", "Number"), "green": ("567", "Number")},
}
EXPECTED_LABELS = set(EXPECTED_CASES)


class Issue10EvidencePackageTests(unittest.TestCase):
    """Validates the frozen issue #10 evidence package and closes the
    documented fail-closed cases of the 2026-08-26 owner review:

    - exact RED/GREEN value AND type (Undefined is a type marker, not "");
    - complete label set, no duplicates/extras;
    - source CF and snapshot-manifest identities must match the documented ones;
    - production patch must be exactly +4/-0 and instrumentation +35/-0;
    - no private absolute paths in the package (sanitized evidence);
    - package manifest hashes must match the committed files.
    """

    def test_manifest_hashes_match_files(self) -> None:
        manifest = json.loads((PACKAGE / "package-manifest.json").read_text())
        for relative, expected in manifest["artifacts"].items():
            self.assertEqual(sha256(PACKAGE / relative), expected, relative)

    def test_source_immutable_identities_match(self) -> None:
        manifest = json.loads((PACKAGE / "package-manifest.json").read_text())
        ids = manifest["sourceImmutableIdentities"]
        self.assertEqual(ids["sourceCfSha256"],
                         "5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a")
        self.assertEqual(ids["manifestIdentitySha256"],
                         "70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691")

    def test_receipts_have_exact_value_and_type_per_case(self) -> None:
        green = read_receipt(PACKAGE / "evidence" / "green-receipt.txt")
        red = read_receipt(PACKAGE / "evidence" / "red-receipt.txt")
        self.assertEqual(set(green), EXPECTED_LABELS)
        self.assertEqual(set(red), EXPECTED_LABELS)
        for case, expected in EXPECTED_CASES.items():
            self.assertEqual(red[case], expected["red"], case)
            self.assertEqual(green[case], expected["green"], case)

    def test_mutation_power_is_real(self) -> None:
        """Feature cases flip (tab/nbsp), control cases do NOT flip."""
        green = read_receipt(PACKAGE / "evidence" / "green-receipt.txt")
        red = read_receipt(PACKAGE / "evidence" / "red-receipt.txt")
        flipped = [c for c in EXPECTED_LABELS if green[c] != red[c]]
        self.assertEqual(set(flipped), {"tab", "nbsp"})

    def test_receipt_distinguishes_undefined_from_empty_string(self) -> None:
        """Undefined must be encoded by a type marker, never by blank alone."""
        for fname in ("green-receipt.txt", "red-receipt.txt"):
            for line in (PACKAGE / "evidence" / fname).read_text(
                    encoding="utf-8-sig").splitlines():
                if "###" not in line:
                    continue
                parts = line.split("###")
                self.assertGreaterEqual(len(parts), 3, line)
                value, typ = parts[1], parts[2]
                self.assertIn(typ, {"Undefined", "Number"}, line)
                if typ == "Undefined":
                    self.assertEqual(value, "", line)
                else:
                    self.assertNotEqual(value, "", line)

    def test_production_patch_statistics_exact(self) -> None:
        diff = (PACKAGE / "production-patch.diff").read_text().splitlines()
        added = [l for l in diff if l.startswith("+") and not l.startswith("+++")]
        removed = [l for l in diff if l.startswith("-") and not l.startswith("---")]
        self.assertEqual((len(removed), len(added)), (0, 4))
        self.assertTrue(any("Chars.Tab" in l for l in added))
        self.assertTrue(any("Chars.NBSp" in l for l in added))

    def test_instrumentation_statistics_exact(self) -> None:
        diff = (PACKAGE / "instrumentation.diff").read_text().splitlines()
        added = [l for l in diff if l.startswith("+") and not l.startswith("+++")]
        removed = [l for l in diff if l.startswith("-") and not l.startswith("---")]
        self.assertEqual((len(removed), len(added)), (0, 35))

    def test_full_work_copy_diff_matches_parts(self) -> None:
        full = (PACKAGE / "full-work-copy.diff").read_text().splitlines()
        prod = (PACKAGE / "production-patch.diff").read_text().splitlines()
        inst = (PACKAGE / "instrumentation.diff").read_text().splitlines()
        # The full diff is the concatenation of both parts (headers included).
        self.assertEqual(full, prod + [""] + inst)

    def test_no_private_paths_in_package(self) -> None:
        for p in PACKAGE.rglob("*"):
            if not p.is_file():
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            hits = re.findall(r"/workspace/[^\s\"']+", text)
            self.assertEqual(hits, [], f"private path in {p.name}")


if __name__ == "__main__":
    unittest.main()
