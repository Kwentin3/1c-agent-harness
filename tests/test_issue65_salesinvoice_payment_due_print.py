from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "experiments" / "issue65-salesinvoice-payment-due-print" / "print-form.patch"


class SalesInvoicePaymentDuePrintPatchTests(unittest.TestCase):
    def test_patch_is_limited_to_existing_print_data_and_layout_boundaries(self) -> None:
        text = PATCH.read_text(encoding="utf-8")
        paths = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(
            paths,
            [
                "Documents/SalesInvoice/Templates/PF_MXL_SalesInvoice/Ext/Template.xml",
                "Documents/SalesInvoice/Templates/PrintData/Ext/Template.xml",
            ],
        )
        self.assertNotIn("ObjectModule.bsl", text)
        self.assertNotIn("ManagerModule.bsl", text)
        self.assertNotIn("Documents/SalesInvoice.xml", text)

    def test_print_data_exposes_existing_due_date_and_title_is_empty_when_unfilled(self) -> None:
        text = PATCH.read_text(encoding="utf-8")
        self.assertIn("<dataPath>PaymentDueDate</dataPath>", text)
        self.assertIn("SalesInvoice.PaymentDueDate AS PaymentDueDate", text)
        self.assertIn("ValueIsFilled(PaymentDueDate)", text)
        self.assertIn("Format(PaymentDueDate, \"DF='d'\")", text)
        self.assertIn("Payment due:", text)
        self.assertIn("Ödeme vadesi:", text)
        self.assertIn(", \"\")]", text)


if __name__ == "__main__":
    unittest.main()
