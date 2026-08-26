from __future__ import annotations

import hashlib
import json
import re
import tempfile
import shutil
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments" / "issue10-write-cycle-20260826"

# The package manifest itself is the only package file that is not listed in
# its own "artifacts" map (self-reference). Everything else must appear exactly
# once, and nothing that is not listed may exist.
MANIFEST_SELF = "package-manifest.json"

# Receipt contract: exactly five non-empty lines, each of the exact form
#   label###VALUE###TYPE
# where TYPE is the 1C type name. Undefined is encoded by the type marker, so
# it is distinguishable from an empty string and from a formatting error.
RECEIPT_LINE_RE = re.compile(r"^([a-z]+)###([^#]*)###(Number|Undefined)$")

EXPECTED_CASES = {
    "tab":    {"red": ("", "Undefined"), "green": ("1234", "Number")},
    "nbsp":   {"red": ("", "Undefined"), "green": ("1234", "Number")},
    "invalid": {"red": ("", "Undefined"), "green": ("", "Undefined")},
    "decimal": {"red": ("1234.56", "Number"), "green": ("1234.56", "Number")},
    "space":  {"red": ("567", "Number"), "green": ("567", "Number")},
}
EXPECTED_LABELS = set(EXPECTED_CASES)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_receipt(path: Path) -> dict:
    """Strict receipt parser.

    Fail-closed: any line that is not exactly ``label###VALUE###TYPE`` (three
    fields), any empty line, any duplicate, unknown or missing label, and any
    line count other than exactly five raises AssertionError. Nothing is
    silently ignored.
    """
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise AssertionError(f"receipt {path.name} is not decodable")
    lines = text.splitlines()
    if len(lines) != len(EXPECTED_CASES):
        raise AssertionError(
            f"receipt {path.name}: expected exactly {len(EXPECTED_CASES)} lines, got {len(lines)}"
        )
    parsed = {}
    for line in lines:
        if not line.strip():
            raise AssertionError(f"receipt {path.name}: empty line")
        m = RECEIPT_LINE_RE.match(line)
        if not m:
            raise AssertionError(f"receipt {path.name}: malformed line {line!r}")
        label, value, typ = m.group(1), m.group(2), m.group(3)
        if label in parsed:
            raise AssertionError(f"receipt {path.name}: duplicate label {label!r}")
        parsed[label] = (value, typ)
    if set(parsed) != EXPECTED_LABELS:
        missing = EXPECTED_LABELS - set(parsed)
        unknown = set(parsed) - EXPECTED_LABELS
        raise AssertionError(
            f"receipt {path.name}: label mismatch, missing={sorted(missing)} unknown={sorted(unknown)}"
        )
    return parsed


def load_manifest() -> dict:
    return json.loads((PACKAGE / MANIFEST_SELF).read_text(encoding="utf-8"))


def package_files() -> set:
    return {
        p.relative_to(PACKAGE).as_posix()
        for p in PACKAGE.rglob("*")
        if p.is_file()
    }


def validate_manifest(manifest: dict, files: set, root: Path = PACKAGE) -> None:
    """Exact package/manifest closure.

    The set of files on disk minus the manifest itself must equal the set of
    manifest artifact keys. Every listed artifact must exist with a matching
    hash; a missing, changed or unlisted artifact raises AssertionError.
    """
    expected = set(manifest["artifacts"])
    actual = files - {MANIFEST_SELF}
    if actual != expected:
        unlisted = actual - expected
        missing = expected - actual
        raise AssertionError(
            f"package/manifest closure broken: unlisted={sorted(unlisted)} missing={sorted(missing)}"
        )
    for rel, expected_hash in manifest["artifacts"].items():
        path = root / rel
        if not path.is_file():
            raise AssertionError(f"artifact missing: {rel}")
        if sha256(path) != expected_hash:
            raise AssertionError(f"artifact hash mismatch: {rel}")


class Issue10EvidencePackageTests(unittest.TestCase):
    """Validates the frozen issue #10 evidence package.

    Closes the fail-closed gaps reproduced in the 2026-08-26 owner review:
    a receipt with a sixth arbitrary line or a fourth field must FAIL; an
    extra file missing from package-manifest.json must FAIL; a missing or
    changed artifact must FAIL; exact values AND types are required for all
    five cases; Undefined is a type marker, never a blank line alone.
    """

    def test_manifest_closure_exact(self) -> None:
        validate_manifest(load_manifest(), package_files())

    def test_manifest_hashes_match_files(self) -> None:
        manifest = load_manifest()
        for rel, expected in manifest["artifacts"].items():
            self.assertEqual(sha256(PACKAGE / rel), expected, rel)

    def test_source_immutable_identities_match(self) -> None:
        ids = load_manifest()["sourceImmutableIdentities"]
        self.assertEqual(ids["sourceCfSha256"],
                         "5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a")
        self.assertEqual(ids["manifestIdentitySha256"],
                         "70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691")

    def test_receipts_have_exact_value_and_type_per_case(self) -> None:
        green = parse_receipt(PACKAGE / "evidence" / "green-receipt.txt")
        red = parse_receipt(PACKAGE / "evidence" / "red-receipt.txt")
        for case, expected in EXPECTED_CASES.items():
            self.assertEqual(red[case], expected["red"], case)
            self.assertEqual(green[case], expected["green"], case)

    def test_mutation_power_is_real(self) -> None:
        green = parse_receipt(PACKAGE / "evidence" / "green-receipt.txt")
        red = parse_receipt(PACKAGE / "evidence" / "red-receipt.txt")
        flipped = [c for c in EXPECTED_LABELS if green[c] != red[c]]
        self.assertEqual(set(flipped), {"tab", "nbsp"})

    def test_undefined_is_a_type_marker_not_an_empty_string(self) -> None:
        for fname in ("green-receipt.txt", "red-receipt.txt"):
            parsed = parse_receipt(PACKAGE / "evidence" / fname)
            for case, (value, typ) in parsed.items():
                if typ == "Undefined":
                    self.assertEqual(value, "", f"{fname}:{case}")
                else:
                    self.assertNotEqual(value, "", f"{fname}:{case}")

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
        self.assertEqual(full, prod + inst)

    def test_no_private_paths_in_package(self) -> None:
        for p in PACKAGE.rglob("*"):
            if not p.is_file():
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            hits = re.findall(r"/workspace/[^\s\"']+", text)
            self.assertEqual(hits, [], f"private path in {p.name}")

    # ------------------------------------------------------------------
    # Negative regression tests: the two bypasses reproduced by the owner
    # review must now FAIL. They operate on disposable copies in a temp dir,
    # never on the committed package.
    # ------------------------------------------------------------------

    def _copy_package(self, into: Path) -> Path:
        shutil.copytree(PACKAGE, into)
        return into

    def test_negative_extra_receipt_line_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_package(Path(td) / "pkg")
            r = dst / "evidence" / "green-receipt.txt"
            r.write_text(r.read_text(encoding="utf-8-sig") +
                         "extra###boom###Number\n", encoding="utf-8-sig")
            with self.assertRaises(AssertionError):
                parse_receipt(r)

    def test_negative_fourth_field_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_package(Path(td) / "pkg")
            r = dst / "evidence" / "red-receipt.txt"
            content = r.read_text(encoding="utf-8-sig")
            content = content.replace(
                "tab######Undefined", "tab######Undefined###junk", 1)
            r.write_text(content, encoding="utf-8-sig")
            with self.assertRaises(AssertionError):
                parse_receipt(r)

    def test_negative_unlisted_extra_file_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_package(Path(td) / "pkg")
            (dst / "smuggled.txt").write_text("x", encoding="utf-8")
            files = {p.relative_to(dst).as_posix()
                     for p in dst.rglob("*") if p.is_file()}
            manifest = json.loads((dst / MANIFEST_SELF).read_text())
            with self.assertRaises(AssertionError):
                validate_manifest(manifest, files, root=dst)

    def test_negative_missing_artifact_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_package(Path(td) / "pkg")
            (dst / "evidence" / "green-receipt.txt").unlink()
            files = {p.relative_to(dst).as_posix()
                     for p in dst.rglob("*") if p.is_file()}
            manifest = json.loads((dst / MANIFEST_SELF).read_text())
            with self.assertRaises(AssertionError):
                validate_manifest(manifest, files, root=dst)

    def test_negative_changed_artifact_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dst = self._copy_package(Path(td) / "pkg")
            r = dst / "evidence" / "green-receipt.txt"
            r.write_text(r.read_text(encoding="utf-8-sig")
                         .replace("1234", "9999", 1), encoding="utf-8-sig")
            files = {p.relative_to(dst).as_posix()
                     for p in dst.rglob("*") if p.is_file()}
            manifest = json.loads((dst / MANIFEST_SELF).read_text())
            with self.assertRaises(AssertionError):
                validate_manifest(manifest, files, root=dst)


if __name__ == "__main__":
    unittest.main()
