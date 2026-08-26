from __future__ import annotations

from pathlib import Path
import unittest

import importlib.util

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "scripts" / "issue10_write_cycle.py"


def load_driver():
    spec = importlib.util.spec_from_file_location("issue10_write_cycle", DRIVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Issue10WriteCycleLogicTests(unittest.TestCase):
    """Tests the pure (non-1C) logic of the reproduce driver.

    These run without the platform: they cover the receipt parsing, mutation-power
    analysis, snapshot verification, and the patch/probe idempotence guards. The
    actual CREATEINFOBASE / DESIGNER / ENTERPRISE steps are exercised by the
    end-to-end `run` command on a lab with the platform present, and are not
    expected to pass in a plain CI environment without 1C.
    """

    @classmethod
    def setUpClass(cls):
        cls.d = load_driver()

    # -- receipt parsing -----------------------------------------------------------------

    def test_parse_receipt_extracts_label_value(self):
        import tempfile
        content = "tab###1234\nnbsp###1234\ninvalid###\ndecimal###1234.56\nspace###567\n"
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
            fh.write(content)
            path = Path(fh.name)
        try:
            r = self.d.parse_receipt(path)
        finally:
            path.unlink()
        self.assertEqual(r["tab"], "1234")
        self.assertEqual(r["nbsp"], "1234")
        self.assertEqual(r["invalid"], "")
        self.assertEqual(r["decimal"], "1234.56")
        self.assertEqual(r["space"], "567")

    def test_parse_receipt_tolerates_bom_and_crlf(self):
        import tempfile
        # The platform writes a single UTF-8 BOM then CRLF lines.
        content = "tab###1234\r\ninvalid###\r\n"
        with tempfile.NamedTemporaryFile("wb", suffix=".txt", delete=False) as fh:
            fh.write(b"\xef\xbb\xbf" + content.encode("utf-8"))
            path = Path(fh.name)
        try:
            r = self.d.parse_receipt(path)
        finally:
            path.unlink()
        self.assertEqual(r["tab"], "1234")
        self.assertEqual(r["invalid"], "")

    # -- mutation power -----------------------------------------------------------------

    def test_mutation_power_true_when_tab_nbsp_flip(self):
        green = {"tab": "1234", "nbsp": "1234", "invalid": "",
                 "decimal": "1234.56", "space": "567"}
        red = {"tab": "", "nbsp": "", "invalid": "",
               "decimal": "1234.56", "space": "567"}
        a = self.d.analyze_mutation(green, red)
        self.assertTrue(a["feature_flipped"])
        self.assertFalse(a["control_changed"])
        self.assertTrue(a["mutation_power"])

    def test_no_mutation_power_if_everything_identical(self):
        green = {"tab": "", "nbsp": "", "invalid": "",
                 "decimal": "1234.56", "space": "567"}
        red = {"tab": "", "nbsp": "", "invalid": "",
               "decimal": "1234.56", "space": "567"}
        a = self.d.analyze_mutation(green, red)
        self.assertFalse(a["feature_flipped"])
        self.assertFalse(a["mutation_power"])

    def test_no_mutation_power_if_control_also_changes(self):
        # A test that also flips the controls is tautologically weak -> no power.
        green = {"tab": "1234", "nbsp": "1234", "invalid": "9",
                 "decimal": "1234.56", "space": "567"}
        red = {"tab": "", "nbsp": "", "invalid": "",
               "decimal": "1234.56", "space": "567"}
        a = self.d.analyze_mutation(green, red)
        self.assertTrue(a["feature_flipped"])
        self.assertTrue(a["control_changed"])
        self.assertFalse(a["mutation_power"])

    # -- snapshot verification ----------------------------------------------------------

    def test_verify_snapshot_counts_mismatch(self):
        import tempfile
        import hashlib
        with tempfile.TemporaryDirectory() as td:
            snap = Path(td) / "snap"
            snap.mkdir()
            (snap / "a.xml").write_bytes(b"hello")
            (snap / "b.bsl").write_bytes(b"world")
            digest_a = hashlib.sha256(b"hello").hexdigest()
            digest_b = hashlib.sha256(b"WORLD").hexdigest()  # wrong hash on purpose
            mani = Path(td) / "snapshot.manifest"
            mani.write_text(f"{digest_a}  a.xml\n{digest_b}  b.bsl\n")
            res = self.d.verify_snapshot(snap, mani)
            self.assertEqual(res["entries"], 2)
            self.assertEqual(res["ok"], 1)
            self.assertEqual(res["mismatch"], 1)
            self.assertEqual(res["missing"], 0)

    def test_verify_snapshot_counts_missing(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            snap = Path(td) / "snap"
            snap.mkdir()
            mani = Path(td) / "snapshot.manifest"
            mani.write_text(f"{'0' * 64}  a.xml\n")
            res = self.d.verify_snapshot(snap, mani)
            self.assertEqual(res["entries"], 1)
            self.assertEqual(res["missing"], 1)
            self.assertEqual(res["ok"], 0)

    # -- patch / probe idempotence ------------------------------------------------------

    def test_apply_production_patch_is_not_pseudo_double(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            mod = Path(td) / "Module.bsl"
            mod.write_bytes(b"Function StringToNumber(Val Value) Export\r\n"
                            b'\tValue  = StrReplace(Value, " ", "");\r\n'
                            b"EndFunction\r\n")
            self.d.apply_production_patch(mod)
            text = self.d.read_bsl(mod)
            self.assertIn("Chars.Tab", text)
            self.assertIn("Chars.NBSp", text)
            # Second apply must fail (idempotence guard).
            with self.assertRaises(self.d.DriverError):
                self.d.apply_production_patch(mod)

    def test_inject_probe_inserts_call_and_procedure(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            mod = Path(td) / "ManagedApplicationModule.bsl"
            mod.write_bytes(b"Procedure OnStart()\r\n\t\r\n\t// StandardSubsystems\r\nEndProcedure\r\n"
                            b"#Region EventHandlers\r\n#EndRegion\r\n")
            self.d.inject_probe(mod, Path("/tmp/receipt.txt"))
            text = self.d.read_bsl(mod)
            self.assertIn("Issue10WriteRuntimeReceipt();", text)
            self.assertIn("Procedure Issue10WriteRuntimeReceipt()", text)
            # The probe call must sit inside OnStart, before StandardSubsystems.
            self.assertLess(text.index("Issue10WriteRuntimeReceipt();"),
                            text.index("// StandardSubsystems"))
            # The procedure must be defined once and the OnStart guard still intact.
            self.assertEqual(text.count("Issue10WriteRuntimeReceipt();"), 1)
            self.assertEqual(text.count("Procedure Issue10WriteRuntimeReceipt()"), 1)


if __name__ == "__main__":
    unittest.main()
