"""Static dashboard contract and isolated oracle tests (not native evidence)."""
import hashlib
from html.parser import HTMLParser
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

    def test_full_attempt3_replays_and_keeps_production_unchanged(self):
        observed = json.loads((ROOT / "OBSERVED.json").read_text())
        receipt = json.loads((ROOT / "receipt3.json").read_text())
        request = json.loads((ROOT / "request.json").read_text())
        evidence = ROOT / "evidence/attempt3"
        client = ORACLE.rows(evidence / "run--evidence--receipt.txt")
        server = ORACLE.rows(evidence / "run--evidence--receipt.txt.server")
        answer = ORACLE.validate(request, client, server)
        self.assertEqual(answer["status"], "PASS")
        self.assertEqual(receipt["result"]["business"], answer["businessPayload"])
        self.assertEqual(observed["fullOracleStatus"], "PASS")
        self.assertEqual((observed["nativeAttemptsUsed"], observed["nativeAttemptsBudget"]), (3, 4))
        self.assertEqual(observed["nativeObservations"], {x: "true" for x in ORACLE.OBSERVATIONS})
        self.assertEqual(receipt["cleanup"]["prepared"], "discarded")
        self.assertEqual(receipt["cleanup"]["runner"]["status"], "completed")
        for name in ("exact-production.patch", "exact-instrumentation.patch", "request.json", "oracle.py", "receipt3.json"):
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), observed[name + "Sha256"])
        self.assertEqual((ROOT / "exact-production.patch").read_bytes(), (ROOT / "evidence/attempt2/exact-production.patch").read_bytes())
        self.assertEqual((ROOT / "oracle.py").read_bytes(), (ROOT / "evidence/attempt2/oracle.py").read_bytes())
        historical = json.loads((ROOT / "evidence/attempt2/request.json").read_text())
        self.assertNotEqual(request["runId"], historical["runId"])
        self.assertNotEqual(request["nonce"], historical["nonce"])
        for patch, name in zip(receipt["patches"], ("exact-production.patch", "exact-instrumentation.patch")):
            self.assertEqual(patch["sha256"], observed[name + "Sha256"])
        normalized = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        self.assertEqual(receipt["request"]["sha256"], hashlib.sha256(normalized).hexdigest())
        for key, name in (("client", "receipt.txt"), ("server", "receipt.txt.server")):
            raw = (evidence / ("run--evidence--" + name)).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), receipt["result"][key]["sha256"])
        result = json.loads((evidence / "run--result.json").read_text())
        self.assertEqual(result["preparedInvocation"]["sourceBefore"], result["preparedInvocation"]["sourceAfter"])
        before = json.loads((ROOT / "evidence/preflight-v3.json").read_text())
        after = json.loads((ROOT / "evidence/post-v3-preflight.json").read_text())
        self.assertEqual(before["audit"], after["audit"])
        self.assertEqual(before["audit"]["canonicalBase"], receipt["canonical"])
        self.assertTrue(after["cleanup"])

    def test_current_probe_has_no_training_blocked_export(self):
        patch = (ROOT / "exact-instrumentation.patch").read_bytes().decode("utf-8-sig")
        self.assertNotIn("SpreadsheetDocumentFileType.HTML", patch)
        for key in ORACLE.OBSERVATIONS:
            self.assertIn('"' + key + '"', patch)

    def test_preview_displays_actual_receipt_metrics_and_five_products(self):
        class PreviewParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.metrics = {}
                self.products = []
                self.active_metric = None
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if "data-metric" in attrs:
                    self.active_metric = attrs["data-metric"]
                if "data-product" in attrs:
                    self.products.append(attrs["data-product"])
            def handle_data(self, data):
                if self.active_metric:
                    self.metrics[self.active_metric] = data
                    self.active_metric = None
        preview = (ROOT / "preview.html").read_text()
        parser = PreviewParser()
        parser.feed(preview)
        observed = json.loads((ROOT / "OBSERVED.json").read_text())
        self.assertEqual(len(parser.metrics), 7)
        for key, text in parser.metrics.items():
            self.assertEqual(text, observed["actualMetrics"][key])
        self.assertEqual(parser.products, [row[0] for row in ORACLE.PRODUCTS[:5]])
        self.assertIn(observed["actualDay"], preview)
        self.assertIn("не скриншот", preview)
        self.assertIn("не данные предприятия", preview)

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
