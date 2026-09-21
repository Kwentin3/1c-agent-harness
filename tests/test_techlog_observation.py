from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time
import unittest

from one_c_harness import techlog_observation


class TechLogObservationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"; self.project.mkdir()
        self.source = self.root / "techlog"; self.source.mkdir()
        self.previous_root = os.environ.get("ONE_C_HARNESS_TECHLOG_ROOT")
        self.previous_zone = os.environ.get("ONE_C_HARNESS_TECHLOG_TIME_ZONE")
        os.environ["ONE_C_HARNESS_TECHLOG_ROOT"] = str(self.source)
        os.environ["ONE_C_HARNESS_TECHLOG_TIME_ZONE"] = "UTC"

    def tearDown(self) -> None:
        if self.previous_root is None: os.environ.pop("ONE_C_HARNESS_TECHLOG_ROOT", None)
        else: os.environ["ONE_C_HARNESS_TECHLOG_ROOT"] = self.previous_root
        if self.previous_zone is None: os.environ.pop("ONE_C_HARNESS_TECHLOG_TIME_ZONE", None)
        else: os.environ["ONE_C_HARNESS_TECHLOG_TIME_ZONE"] = self.previous_zone
        self.temporary.cleanup()

    def _log(self, directory: str, hour: str, lines: list[str]) -> None:
        path = self.source / directory / f"{hour}.log"; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _observe(self, start: str, end: str, limit: int = 20) -> dict[str, object]:
        return techlog_observation.observe(self.project, start, end, ["EXCP"], limit)

    def test_calendar_interval_groups_distinct_errors_and_hides_secret_text(self) -> None:
        self._log("first", "26091812", [
            '00:00.000001-1,EXCP,1,Exception=DataError,Descr="Cannot post document, customer=Alice token=private",SrcName=core',
            '00:00.000002-1,EXCP,1,Exception=DataError,Descr="Cannot post document, customer=Bob token=other",SrcName=core',
            '00:00.000003-1,EXCP,1,Exception=TransportError,Descr="password=secret",SrcName=net',
        ])
        observed = self._observe("2026-09-18T12:00:00", "2026-09-18T12:00:01")
        self.assertEqual(observed["status"], "ok")
        self.assertEqual(observed["summary"]["window"]["sourceTimeZone"], "UTC")
        self.assertEqual(len(observed["groups"]), 3)  # descriptions distinguish same exception type
        pages = [techlog_observation.expand(self.project, group["ref"], 0, 20) for group in observed["groups"]]
        rendered = json.dumps([observed, pages])
        self.assertNotIn("Alice", rendered); self.assertNotIn("secret", rendered)
        self.assertIn("exceptionType", rendered); self.assertIn("description", rendered)
        self.assertIn("fingerprint", rendered)
        self.assertIn("Cannot post document", rendered)
        self.assertIn("<redacted:value>", rendered)

    def test_quoted_description_keeps_meaning_after_comma_and_newline(self) -> None:
        self._log("first", "26091812", [
            '00:00.000001-1,EXCP,1,Exception=DatabaseError,Descr="Transaction failed,',
            'deadlock detected; retry operation",SrcName=core',
        ])
        observed = self._observe("2026-09-18T12:00:00", "2026-09-18T12:00:01")
        page = techlog_observation.expand(self.project, observed["groups"][0]["ref"], 0, 20)
        description = page["records"][0]["error"]["description"]
        self.assertEqual(description["status"], "projected")
        self.assertEqual(description["fragment"], "Transaction failed, deadlock detected; retry operation")
        self.assertFalse(description["redacted"])
        self.assertFalse(description["truncated"])

    def test_description_reports_bounded_truncation(self) -> None:
        self._log("first", "26091812", [
            '00:00.000001-1,EXCP,1,Exception=DataError,Descr="Technical assertion ' + "x" * 600 + '",SrcName=core',
        ])
        observed = self._observe("2026-09-18T12:00:00", "2026-09-18T12:00:01")
        page = techlog_observation.expand(self.project, observed["groups"][0]["ref"], 0, 20)
        description = page["records"][0]["error"]["description"]
        self.assertTrue(description["truncated"])
        self.assertLessEqual(len(description["fragment"]), 480)

    def test_relative_platform_path_is_hidden_without_losing_error_meaning(self) -> None:
        self._log("first", "26091812", [
            "00:00.000001-1,EXCP,1,Exception=FileError,"
            "Descr=src/core/File.cpp(42): File not found, fio_manager_exception type: 1",
        ])
        observed = self._observe("2026-09-18T12:00:00", "2026-09-18T12:00:01")
        page = techlog_observation.expand(self.project, observed["groups"][0]["ref"], 0, 20)
        fragment = page["records"][0]["error"]["description"]["fragment"]
        self.assertNotIn("src/core/File.cpp", fragment)
        self.assertIn("<redacted:path>", fragment)
        self.assertIn("File not found", fragment)

    def test_hour_files_do_not_mix_same_source_token_and_interval_boundary_is_inclusive(self) -> None:
        self._log("one", "26091812", ["59:59.000000-1,EXCP,1,Exception=AtTwelve,Descr=one"])
        self._log("two", "26091813", ["00:00.000000-1,EXCP,1,Exception=AtThirteen,Descr=two"])
        self._log("three", "26091900", ["00:00.000000-1,EXCP,1,Exception=NextDay,Descr=three"])
        first = self._observe("2026-09-18T12:59:59", "2026-09-18T13:00:00")
        second = self._observe("2026-09-19T00:00:00", "2026-09-19T00:00:00")
        self.assertEqual(first["summary"]["recordCount"], 2)
        self.assertEqual(second["summary"]["recordCount"], 1)
        records = techlog_observation.expand(self.project, first["groups"][0]["ref"], 0, 20)["records"]
        self.assertTrue(all("2026-09-18" in item["occurredAt"] for item in records))

    def test_snapshot_is_stable_paged_and_expired_snapshot_is_not_reused(self) -> None:
        self._log("one", "26091812", [
            f"00:00.00000{i}-1,EXCP,1,Exception=DataError,Descr=item" for i in range(1, 4)
        ])
        observed = self._observe("2026-09-18T12:00:00", "2026-09-18T12:00:01")
        ref = observed["groups"][0]["ref"]
        self._log("one", "26091812", ["00:00.000009-1,EXCP,1,Exception=Changed,Descr=new"])
        page_one = techlog_observation.expand(self.project, ref, 0, 1)
        page_two = techlog_observation.expand(self.project, ref, 1, 1)
        self.assertEqual(page_one["total"], 3); self.assertEqual(page_two["offset"], 1)
        self.assertTrue(page_one["truncated"])
        self.assertEqual(page_one["records"][0]["error"]["description"]["fragment"], "item")
        snapshot = self.project / ".local/runs/techlog-observations" / f"{observed['snapshot']['ref']}.json"
        value = json.loads(snapshot.read_text()); value["expiresAt"] = time.time() - 1; snapshot.write_text(json.dumps(value))
        self.assertEqual(techlog_observation.expand(self.project, ref, 0, 1)["reasonCode"], "evidence_not_found")

    def test_budgets_report_partial_without_claiming_complete_incident(self) -> None:
        self._log("one", "26091812", [
            f"00:00.{i:06d}-1,EXCP,1,Exception=E{i},Descr={'x' * 128}" for i in range(220)
        ])
        observed = self._observe("2026-09-18T12:00:00", "2026-09-18T12:01:00")
        self.assertEqual(observed["status"], "partial")
        coverage = observed["summary"]["coverage"]
        self.assertTrue(coverage["partial"])
        self.assertIn(coverage["reasonCode"], {"record_budget", "read_budget", "time_budget"})
        self.assertLessEqual(observed["summary"]["recordCount"], 200)

    def test_unavailable_empty_and_invalid_timezone_are_distinct(self) -> None:
        self.assertEqual(self._observe("2026-09-18T12:00:00", "2026-09-18T12:00:01")["status"], "ok")
        os.environ.pop("ONE_C_HARNESS_TECHLOG_ROOT")
        self.assertEqual(self._observe("2026-09-18T12:00:00", "2026-09-18T12:00:01")["reasonCode"], "source_unavailable")
        os.environ["ONE_C_HARNESS_TECHLOG_ROOT"] = str(self.source)
        os.environ["ONE_C_HARNESS_TECHLOG_TIME_ZONE"] = "Bad/Zone"
        self.assertEqual(self._observe("2026-09-18T12:00:00", "2026-09-18T12:00:01")["reasonCode"], "source_unavailable")


if __name__ == "__main__":
    unittest.main()
