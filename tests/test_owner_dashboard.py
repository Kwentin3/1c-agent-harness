"""Static dashboard contract and isolated oracle tests (not native evidence)."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "experiments/issue85-owner-dashboard"
SPEC = importlib.util.spec_from_file_location("dashboard_oracle", ROOT / "oracle.py")
ORACLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ORACLE)


class OwnerDashboardTests(unittest.TestCase):
    def test_new_readonly_report_entry_exists(self):
        path = ROOT / "product/ObjectModule.bsl"
        self.assertTrue(path.is_file(), "Yesterday report object implementation is absent")
        code = path.read_text(encoding="utf-8-sig")
        self.assertIn("Function GetYesterdaySummary(AsOfDate = Undefined) Export", code)
        self.assertIn("CurrentSessionDate()", code)
        self.assertIn("BegOfDay(AsOfDate)", code)
        self.assertIn("86400", code)
        self.assertNotIn("SetPrivilegedMode", code)
        for forbidden in (".Write(", "Eval(", "SetPrivilegedMode"):
            self.assertNotIn(forbidden, code)

    def test_retained_calculation_is_not_promoted_to_complete_pass(self):
        evidence = ROOT / "evidence/attempt2"
        observed = json.loads((evidence / "OBSERVED.json").read_text())
        self.assertEqual(observed["fullOracleStatus"], "FAIL")
        self.assertTrue(observed["coreCalculationMatchesExpected"])
        self.assertTrue(observed["nativeFormCreationObserved"])
        request = json.loads((evidence / "request.json").read_text())
        client = ORACLE.rows(evidence / "run--evidence--receipt.txt")
        server = ORACLE.rows(evidence / "run--evidence--receipt.txt.server")
        with self.assertRaisesRegex(ValueError, "incomplete server receipt"):
            ORACLE.validate(request, client, server)
        for row in (client, server):
            self.assertEqual(row["run"], request["runId"])
            self.assertEqual(row["nonce"], request["nonce"])
        self.assertEqual(client["token"], server["token"])
        self.assertEqual(client["formCreated"], "true")
        for key, expected in ORACLE.EXPECTED.items():
            self.assertEqual(ORACLE.number(server[key]), ORACLE.number(expected))
        for name in ("exact-production.patch", "exact-instrumentation.patch", "request.json"):
            self.assertEqual(hashlib.sha256((evidence / name).read_bytes()).hexdigest(), observed[name + "Sha256"])
        for attempt in ("attempt1", "attempt2"):
            result = json.loads((ROOT / "evidence" / attempt / "run--result.json").read_text())
            self.assertEqual(result["preparedInvocation"]["sourceBefore"], result["preparedInvocation"]["sourceAfter"])
            self.assertEqual(result["storageCompaction"]["status"], "completed")
            raw_client = (ROOT / "evidence" / attempt / "run--evidence--receipt.txt").read_bytes()
            self.assertEqual(hashlib.sha256(raw_client).hexdigest(), result["runtime"]["receiptSha256"])
        before = json.loads((ROOT / "evidence/preflight.json").read_text())
        after = json.loads((ROOT / "evidence/post-readonly-preflight.json").read_text())
        self.assertEqual(before["audit"]["canonicalBase"], after["audit"]["canonicalBase"])
        preflight = json.loads((ROOT / "evidence/preflight-v2.json").read_text())
        self.assertTrue(preflight["cleanup"])
        self.assertEqual(len(preflight["audit"]["changedPaths"]), 6)
        self.assertEqual(preflight["audit"]["patches"][0]["sha256"], observed["exact-production.patchSha256"])
        self.assertEqual(preflight["audit"]["patches"][1]["sha256"], observed["exact-instrumentation.patchSha256"])

    def test_union_has_no_nested_allowed_keyword(self):
        code = (ROOT / "product/ObjectModule.bsl").read_text()
        self.assertNotIn("(SELECT ALLOWED", code,
                         "1C only admits ALLOWED on the first query; native #1 rejected nesting")
        self.assertNotIn("|  SELECT ALLOWED", code)
        self.assertIn('"SELECT ALLOWED', code)

    def test_strict_native_oracle_distinguishes_wrong_totals(self):
        request = {"runId": "unit-only-run", "nonce": "unit-only-nonce"}
        client = {"run": request["runId"], "nonce": request["nonce"], "token": "server-only-token",
                  "returned": "true", "formCreated": "true", "complete": "true"}
        server = {"run": request["runId"], "nonce": request["nonce"], "token": client["token"],
                  "day": "2026-04-01", "serverComplete": "true", **ORACLE.EXPECTED,
                  **{x: "true" for x in ORACLE.OBSERVATIONS}}
        server.update({"product" + str(i): "|".join(row) for i, row in enumerate(ORACLE.PRODUCTS, 1)})
        self.assertEqual(ORACLE.validate(request, client, server)["status"], "PASS")
        for name in ORACLE.EXPECTED:
            wrong = dict(server, **{name: "9999"})
            with self.subTest(name=name), self.assertRaises(ValueError):
                ORACLE.validate(request, client, wrong)
        for name in ORACLE.OBSERVATIONS:
            with self.subTest(name=name), self.assertRaises(ValueError):
                ORACLE.validate(request, client, dict(server, **{name: "false"}))
        for wrong in (dict(server, nonce="stale"), dict(server, token=request["nonce"]),
                      dict(server, product1=server["product2"]), dict(server, revenue="NaN")):
            with self.assertRaises(ValueError):
                ORACLE.validate(request, client, wrong)
        for name in server:
            wrong = dict(server)
            wrong.pop(name)
            with self.subTest(missing=name), self.assertRaises(ValueError):
                ORACLE.validate(request, client, wrong)
        with self.assertRaises(ValueError):
            ORACLE.validate(request, dict(client, formCreated="false"), server)


if __name__ == "__main__":
    unittest.main()
