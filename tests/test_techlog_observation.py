from __future__ import annotations

import json
import os
from pathlib import Path
import re
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

    def test_source_info_reports_bounded_observed_interval_and_filters(self) -> None:
        self._log("first", "26091812", [
            "00:00.000001-1,EXCP,1,Exception=DataError,Descr=first,SrcName=core",
            "00:00.000002-1,EXCPCNTX,1,Descr=context,process=rphost",
        ])
        self._log("second", "26091813", [
            "05:00.000001-1,EXCP,1,Exception=LaterError,Descr=later,SessionID=42",
        ])

        result = techlog_observation.source_info(self.project)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["source"], "1c_techlog")
        self.assertEqual(result["sourceTimeZone"], "UTC")
        self.assertEqual(result["observedInterval"], {
            "start": "2026-09-18T12:00:00.000001+00:00",
            "end": "2026-09-18T13:05:00.000001+00:00",
            "complete": True,
        })
        self.assertEqual(result["observedEvents"], ["EXCP", "EXCPCNTX"])
        self.assertEqual(result["supportedFilters"], [
            "events", "text", "sourceComponent", "process",
        ])
        self.assertFalse(result["coverage"]["partial"])

    def test_source_info_keeps_useful_bounded_results_when_file_inventory_is_partial(self) -> None:
        for hour in range(25):
            day = "260918" if hour < 24 else "260919"
            hour_token = hour if hour < 24 else 0
            self._log(f"node-{hour:02d}", f"{day}{hour_token:02d}", [
                f"00:00.000001-1,EXCP,1,Exception=E{hour},Descr=detail {hour}",
            ])

        result = techlog_observation.source_info(self.project)

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["coverage"]["reasonCode"], "file_budget")
        self.assertEqual(result["coverage"]["filesRead"], 24)
        self.assertIsNotNone(result["observedInterval"])
        self.assertFalse(result["observedInterval"]["complete"])

    def test_structured_filters_search_only_safe_projected_technical_content(self) -> None:
        self._log("first", "26091812", [
            '00:00.000001-1,EXCP,1,Exception=DatabaseError,Descr="deadlock detected",SrcName=db,process=rphost,SessionID=42',
            '00:00.000002-1,EXCP,1,Exception=FileError,Descr="file missing",SrcName=storage,process=1cv8,SessionID=99',
            '00:00.000003-1,EXCP,1,Exception=SecretError,Descr="customer=deadlock",SrcName=db,process=rphost,SessionID=42',
            '00:00.000004-1,EXCP,1,Exception=DatabaseError,Descr="deadlock detected",SrcName=db,process=rphost,SessionID=42',
        ])

        observed = techlog_observation.observe(
            self.project,
            "2026-09-18T12:00:00",
            "2026-09-18T12:00:01",
            ["EXCP"],
            20,
            {"text": "deadlock", "sourceComponent": "db", "process": "rphost"},
        )
        page = techlog_observation.expand(self.project, observed["groups"][0]["ref"], 0, 20)

        self.assertEqual(observed["status"], "ok")
        self.assertEqual(observed["summary"]["recordCount"], 2)
        self.assertEqual(observed["summary"]["countScope"], "retainedFilteredSelection")
        self.assertEqual(observed["summary"]["filters"], {
            "events": ["EXCP"], "text": "deadlock", "sourceComponent": "db", "process": "rphost",
        })
        self.assertEqual(observed["groups"][0]["summary"]["meaning"], "DatabaseError: deadlock detected")
        self.assertEqual(observed["groups"][0]["firstOccurredAt"], "2026-09-18T12:00:00.000001+00:00")
        self.assertEqual(observed["groups"][0]["lastOccurredAt"], "2026-09-18T12:00:00.000004+00:00")
        self.assertEqual(page["records"][0]["technical"]["process"], "rphost")
        self.assertRegex(page["records"][0]["technical"]["sessionFingerprint"], r"^hmac-sha256:[0-9a-f]{16}$")
        self.assertNotIn("SessionID", json.dumps([observed, page]))
        self.assertNotIn("customer", json.dumps([observed, page]))

    def test_null_text_filter_is_rejected_as_invalid_request(self) -> None:
        self._log("one", "26091812", [
            "00:00.000001-1,EXCP,1,Exception=DataError,Descr=detail",
        ])

        result = techlog_observation.observe(
            self.project, "2026-09-18T12:00:00", "2026-09-18T12:00:01",
            ["EXCP"], 20, {"text": None},
        )

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reasonCode"], "invalid_request")

    def test_text_filter_limit_counts_unicode_characters(self) -> None:
        self._log("one", "26091812", [
            "00:00.000001-1,EXCP,1,Exception=DataError,Descr=detail",
        ])

        result = techlog_observation.observe(
            self.project, "2026-09-18T12:00:00", "2026-09-18T12:00:01",
            ["EXCP"], 20, {"text": "я" * 120},
        )
        too_long = techlog_observation.observe(
            self.project, "2026-09-18T12:00:00", "2026-09-18T12:00:01",
            ["EXCP"], 20, {"text": "я" * 121},
        )

        self.assertNotEqual(result["reasonCode"] if result["status"] == "blocked" else None, "invalid_request")
        self.assertEqual(too_long["reasonCode"], "invalid_request")

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

    def test_standalone_opaque_description_stays_redacted(self) -> None:
        self._log("first", "26091812", [
            "00:00.000001-1,EXCP,1,Exception=DataError,Descr=private",
        ])
        observed = self._observe("2026-09-18T12:00:00", "2026-09-18T12:00:01")
        page = techlog_observation.expand(self.project, observed["groups"][0]["ref"], 0, 20)
        description = page["records"][0]["error"]["description"]
        self.assertEqual(description["status"], "redacted")
        self.assertNotIn("fragment", description)

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

    def test_snapshot_supports_group_pages_record_refs_and_retained_neighbors(self) -> None:
        self._log("one", "26091812", [
            "00:00.000001-1,EXCP,1,Exception=First,Descr=alpha",
            "00:00.000002-1,EXCP,1,Exception=Second,Descr=beta detail",
            "00:00.000003-1,EXCP,1,Exception=Third,Descr=gamma",
        ])
        observed = self._observe("2026-09-18T12:00:00", "2026-09-18T12:00:01", limit=1)
        self.assertTrue(observed["groupsTruncated"])
        observation_ref = observed["observationRef"]

        self._log("one", "26091812", ["00:00.000009-1,EXCP,1,Exception=Changed,Descr=new"])
        group_page = techlog_observation.expand_groups(self.project, observation_ref, 1, 1)
        record_page = techlog_observation.expand(self.project, group_page["groups"][0]["ref"], 0, 1)
        record_ref = record_page["records"][0]["recordRef"]
        neighbors = techlog_observation.expand_record(self.project, record_ref, 1, 1)

        self.assertEqual(group_page["level"], "observation")
        self.assertEqual(group_page["total"], 3)
        self.assertEqual(group_page["groups"][0]["summary"]["meaning"], "Second: beta detail")
        self.assertEqual(neighbors["level"], "record")
        self.assertEqual(neighbors["scope"], "retainedFilteredSelection")
        self.assertEqual(neighbors["record"]["error"]["exceptionType"], "Second")
        self.assertEqual([item["error"]["exceptionType"] for item in neighbors["before"]], ["First"])
        self.assertEqual([item["error"]["exceptionType"] for item in neighbors["after"]], ["Third"])
        self.assertEqual(neighbors["relation"], "time adjacency only; no causal relationship is implied")
        self.assertNotIn("Changed", json.dumps([group_page, record_page, neighbors]))

    def test_identical_records_have_distinct_occurrence_refs(self) -> None:
        line = "00:00.000001-1,EXCP,1,Exception=Same,Descr=same detail"
        self._log("one", "26091812", [line])
        self._log("two", "26091812", [line])
        observed = self._observe("2026-09-18T12:00:00", "2026-09-18T12:00:01")

        page = techlog_observation.expand(self.project, observed["groups"][0]["ref"], 0, 20)
        refs = [record["recordRef"] for record in page["records"]]
        second = techlog_observation.expand_record(self.project, refs[1], 1, 0)

        self.assertEqual(len(refs), 2)
        self.assertEqual(len(set(refs)), 2)
        self.assertEqual(second["record"]["selectionIndex"], 1)
        self.assertEqual([record["selectionIndex"] for record in second["before"]], [0])

    def test_group_ref_requires_exact_canonical_membership(self) -> None:
        self._log("one", "26091812", [
            "00:00.000001-1,EXCP,1,Exception=First,Descr=first detail",
            "00:00.000002-1,EXCP,1,Exception=Second,Descr=second detail",
        ])
        observed = self._observe("2026-09-18T12:00:00", "2026-09-18T12:00:01")
        canonical = observed["groups"][0]["ref"]
        snapshot_id = observed["snapshot"]["ref"]
        forged = [
            f"snapshot:{snapshot_id}:group:EXCP:",
            canonical[:-1],
            f"snapshot:{snapshot_id}:group:EXCP:{'0' * 16}",
        ]

        for reference in forged:
            result = techlog_observation.expand(self.project, reference, 0, 20)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["reasonCode"], "evidence_not_found")

    def test_session_fingerprint_is_selection_scoped_not_raw_hash(self) -> None:
        self._log("one", "26091812", [
            "00:00.000001-1,EXCP,1,Exception=Same,Descr=same detail,SessionID=42",
            "00:00.000002-1,EXCP,1,Exception=Same,Descr=same detail,SessionID=42",
        ])
        first = self._observe("2026-09-18T12:00:00", "2026-09-18T12:00:01")
        first_page = techlog_observation.expand(self.project, first["groups"][0]["ref"], 0, 20)
        second = self._observe("2026-09-18T12:00:00", "2026-09-18T12:00:01")
        second_page = techlog_observation.expand(self.project, second["groups"][0]["ref"], 0, 20)
        first_tokens = {record["technical"]["sessionFingerprint"] for record in first_page["records"]}
        second_tokens = {record["technical"]["sessionFingerprint"] for record in second_page["records"]}

        self.assertEqual(len(first_tokens), 1)
        self.assertEqual(len(second_tokens), 1)
        self.assertNotEqual(first_tokens, second_tokens)
        first_record_ids = {record["recordId"] for record in first_page["records"]}
        second_record_ids = {record["recordId"] for record in second_page["records"]}
        self.assertNotEqual(first_record_ids, second_record_ids)
        self.assertTrue(all(re.fullmatch(r"techlog:[0-9a-f]{24}", record_id) for record_id in first_record_ids | second_record_ids))
        self.assertNotIn("sha256:73475cb40a568e8d", first_tokens)
        for page in (first_page, second_page):
            for record in page["records"]:
                self.assertNotIn("_sessionValue", record["technical"])
                self.assertNotIn("SessionID", record["technical"])
                self.assertNotEqual(record["technical"]["sessionFingerprint"], "42")

    def test_redacted_description_fingerprint_is_selection_scoped(self) -> None:
        line = "00:00.000001-1,EXCP,1,Exception=SecretError,Descr=password=secret"
        self._log("one", "26091812", [line, line.replace("000001", "000002")])

        first = self._observe("2026-09-18T12:00:00", "2026-09-18T12:00:01")
        first_page = techlog_observation.expand(self.project, first["groups"][0]["ref"], 0, 20)
        second = self._observe("2026-09-18T12:00:00", "2026-09-18T12:00:01")
        second_page = techlog_observation.expand(self.project, second["groups"][0]["ref"], 0, 20)
        first_tokens = {record["error"]["description"]["fingerprint"] for record in first_page["records"]}
        second_tokens = {record["error"]["description"]["fingerprint"] for record in second_page["records"]}

        self.assertEqual(len(first_tokens), 1)
        self.assertEqual(len(second_tokens), 1)
        self.assertNotEqual(first_tokens, second_tokens)
        self.assertNotEqual(first["groups"][0]["ref"].split(":group:", 1)[1], second["groups"][0]["ref"].split(":group:", 1)[1])
        self.assertTrue(all(token.startswith("hmac-sha256:") for token in first_tokens | second_tokens))
        self.assertNotIn("secret", json.dumps([first, first_page, second, second_page]))

    def test_error_signature_is_selection_scoped_without_description(self) -> None:
        self._log("one", "26091812", ["00:00.000001-1,EXCP,1,Exception=NoDescription"])

        first = self._observe("2026-09-18T12:00:00", "2026-09-18T12:00:01")
        second = self._observe("2026-09-18T12:00:00", "2026-09-18T12:00:01")

        self.assertRegex(first["groups"][0]["errorSignature"], r"^hmac-sha256:[0-9a-f]{16}$")
        self.assertNotEqual(first["groups"][0]["errorSignature"], second["groups"][0]["errorSignature"])
        self.assertNotEqual(first["groups"][0]["ref"].split(":group:", 1)[1], second["groups"][0]["ref"].split(":group:", 1)[1])

    def test_altered_snapshot_is_rejected_instead_of_rebinding_existing_refs(self) -> None:
        self._log("one", "26091812", [
            "00:00.000001-1,EXCP,1,Exception=Original,Descr=original detail",
        ])
        observed = self._observe("2026-09-18T12:00:00", "2026-09-18T12:00:01")
        ref = observed["groups"][0]["ref"]
        snapshot = self.project / ".local/runs/techlog-observations" / f"{observed['snapshot']['ref']}.json"
        value = json.loads(snapshot.read_text())
        value["records"][0]["error"]["exceptionType"] = "Tampered"
        snapshot.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))

        result = techlog_observation.expand(self.project, ref, 0, 1)

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reasonCode"], "evidence_not_found")
        self.assertNotIn("Tampered", json.dumps(result))

    def test_snapshot_is_stable_paged_and_expired_snapshot_is_not_reused(self) -> None:
        self._log("one", "26091812", [
            f"00:00.00000{i}-1,EXCP,1,Exception=DataError,Descr=stable item" for i in range(1, 4)
        ])
        observed = self._observe("2026-09-18T12:00:00", "2026-09-18T12:00:01")
        ref = observed["groups"][0]["ref"]
        self._log("one", "26091812", ["00:00.000009-1,EXCP,1,Exception=Changed,Descr=new"])
        page_one = techlog_observation.expand(self.project, ref, 0, 1)
        page_two = techlog_observation.expand(self.project, ref, 1, 1)
        self.assertEqual(page_one["total"], 3); self.assertEqual(page_two["offset"], 1)
        self.assertTrue(page_one["truncated"])
        self.assertEqual(page_one["records"][0]["error"]["description"]["fragment"], "stable item")
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
