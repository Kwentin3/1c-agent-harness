from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import textwrap
import time
import unittest
from unittest import mock

from one_c_harness import companion, eventlog_observation


XML = """<?xml version="1.0" encoding="UTF-8"?>
<v8e:EventLog xmlns:v8e="http://v8.1c.ru/eventLog">
  <v8e:Event><v8e:Level>Information</v8e:Level><v8e:Date>2026-09-22T06:44:15</v8e:Date><v8e:Event>_$Session$_.Start</v8e:Event><v8e:EventPresentation>Session. Beginning</v8e:EventPresentation><v8e:User>alice</v8e:User><v8e:UserPresentation>Alice</v8e:UserPresentation><v8e:Metadata>Document.Order</v8e:Metadata><v8e:MetadataPresentation>Order</v8e:MetadataPresentation><v8e:TransactionStatus>NotApplicable</v8e:TransactionStatus></v8e:Event>
  <v8e:Event><v8e:Level>Error</v8e:Level><v8e:Date>2026-09-22T06:44:16</v8e:Date><v8e:Event>_$Data$_.Update</v8e:Event><v8e:EventPresentation>Data. Change</v8e:EventPresentation><v8e:User>bob</v8e:User><v8e:UserPresentation>Bob</v8e:UserPresentation><v8e:Metadata>Document.Invoice</v8e:Metadata><v8e:MetadataPresentation>Invoice</v8e:MetadataPresentation><v8e:TransactionStatus>Committed</v8e:TransactionStatus><v8e:Comment>Invoice changed</v8e:Comment></v8e:Event>
  <v8e:Event><v8e:Level>Error</v8e:Level><v8e:Date>2026-09-22T06:44:17</v8e:Date><v8e:Event>_$Data$_.Update</v8e:Event><v8e:EventPresentation>Data. Change</v8e:EventPresentation><v8e:User>alice</v8e:User><v8e:UserPresentation>Alice</v8e:UserPresentation><v8e:Metadata>Document.Invoice</v8e:Metadata><v8e:MetadataPresentation>Invoice</v8e:MetadataPresentation><v8e:TransactionStatus>Committed</v8e:TransactionStatus></v8e:Event>
</v8e:EventLog>
"""


class EventLogObservationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"; self.project.mkdir()
        self.xml = self.root / "source.xml"; self.xml.write_text(XML, encoding="utf-8")
        self.request_capture = self.root / "request.json"
        self.command = self.root / "exporter.py"
        self.command.write_text(textwrap.dedent(f"""\
            #!/usr/bin/env python3
            import os, pathlib, sys
            raw = sys.stdin.buffer.read()
            pathlib.Path(os.environ['CAPTURE']).write_bytes(raw)
            sys.stdout.buffer.write(pathlib.Path(os.environ['SOURCE_XML']).read_bytes())
        """), encoding="utf-8")
        self.command.chmod(0o755)
        self.previous = {key: os.environ.get(key) for key in (
            "ONE_C_HARNESS_EVENTLOG_COMMAND", "ONE_C_HARNESS_EVENTLOG_TIME_ZONE", "SOURCE_XML", "CAPTURE",
        )}
        os.environ.update({
            "ONE_C_HARNESS_EVENTLOG_COMMAND": str(self.command),
            "ONE_C_HARNESS_EVENTLOG_TIME_ZONE": "UTC",
            "SOURCE_XML": str(self.xml), "CAPTURE": str(self.request_capture),
        })

    def tearDown(self) -> None:
        for key, value in self.previous.items():
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value
        self.temporary.cleanup()

    def _select(self, **overrides: object) -> dict[str, object]:
        arguments: dict[str, object] = {
            "start": "2026-09-22T06:44:00", "end": "2026-09-22T06:45:00",
            "filters": {}, "maximumCount": 100, "limit": 20,
        }
        arguments.update(overrides)
        return eventlog_observation.select(self.project, **arguments)

    def test_select_invokes_fixed_command_and_returns_bounded_facets(self) -> None:
        selected = self._select(filters={"event": "_$Data$_.Update", "level": "Error", "user": "alice", "metadata": "Document.Invoice"})
        captured = json.loads(self.request_capture.read_text())

        self.assertEqual(selected["status"], "ok")
        self.assertEqual(selected["summary"]["recordCount"], 1)
        self.assertEqual(selected["summary"]["coverage"]["complete"], True)
        self.assertEqual(selected["summary"]["facets"]["events"], [{"value": "_$Data$_.Update", "count": 1}])
        self.assertEqual(captured["operation"], "unloadEventLog")
        self.assertEqual(captured["maximumCount"], 100)
        self.assertEqual(captured["filters"]["metadata"], "Document.Invoice")
        self.assertNotIn(str(self.command), json.dumps(selected))
        self.assertNotIn(str(self.xml), json.dumps(selected))

    def test_page_and_record_use_stable_selection_refs_not_live_source(self) -> None:
        selected = self._select()
        self.xml.write_text("broken", encoding="utf-8")
        page = eventlog_observation.page(self.project, selected["selectionRef"], 1, 1)
        record = eventlog_observation.record(self.project, page["records"][0]["recordRef"])

        self.assertEqual(page["status"], "ok")
        self.assertEqual(page["total"], 3)
        self.assertEqual(page["records"][0]["event"], "_$Data$_.Update")
        self.assertEqual(record["record"]["user"]["presentation"], "Bob")
        self.assertEqual(record["record"]["comment"], "Invoice changed")
        self.assertEqual(record["record"]["metadata"]["name"], "Document.Invoice")
        self.assertNotIn("broken", json.dumps([page, record]))

    def test_page_can_refine_retained_selection_without_exporting_again(self) -> None:
        selected = self._select()
        self.request_capture.unlink()
        refined = eventlog_observation.page(
            self.project, selected["selectionRef"], 0, 20,
            {"level": "Error", "user": "alice", "metadata": "Document.Invoice"},
        )

        self.assertFalse(self.request_capture.exists())
        self.assertEqual(refined["status"], "ok")
        self.assertEqual(refined["total"], 1)
        self.assertEqual(refined["records"][0]["user"]["name"], "alice")
        self.assertEqual(refined["summary"]["countScope"], "refinedRetainedSelection")
        self.assertEqual(refined["summary"]["filters"], {"level": "Error", "user": "alice", "metadata": "Document.Invoice"})
        self.assertEqual(refined["summary"]["baseSelectionRef"], selected["selectionRef"])
        self.assertEqual(refined["summary"]["window"]["sourceTimeZone"], "UTC")
        self.assertTrue(refined["summary"]["coverage"]["limitedToRetainedSelection"])

    def test_record_is_self_describing_without_repeating_runtime_packaging(self) -> None:
        selected = self._select()
        record = eventlog_observation.record(self.project, selected["records"][1]["recordRef"])
        self.assertEqual(record["source"], "1c_registration_log")
        self.assertEqual(record["selectionRef"], selected["selectionRef"])
        self.assertEqual(record["window"]["sourceTimeZone"], "UTC")
        self.assertEqual(record["filters"], {})
        self.assertNotIn("artifactId", record)

    def test_exact_filters_are_reapplied_to_xml_in_domain_code(self) -> None:
        selected = self._select(filters={"user": "alice"})
        page = eventlog_observation.page(self.project, selected["selectionRef"], 0, 20)
        self.assertEqual(selected["summary"]["recordCount"], 2)
        self.assertEqual({item["user"]["name"] for item in page["records"]}, {"alice"})

    def test_maximum_boundary_and_platform_over_return_are_partial(self) -> None:
        boundary = self._select(maximumCount=3)
        over = self._select(maximumCount=2)
        self.assertEqual(boundary["status"], "partial")
        self.assertEqual(boundary["summary"]["coverage"]["reasonCode"], "maximum_count_boundary")
        self.assertEqual(over["status"], "partial")
        self.assertEqual(over["summary"]["coverage"]["reasonCode"], "maximum_count_exceeded")
        self.assertEqual(over["summary"]["recordCount"], 2)

    def test_ignored_source_filter_cannot_turn_maximum_boundary_into_complete(self) -> None:
        selected = self._select(filters={"user": "alice"}, maximumCount=3)
        self.assertEqual(selected["status"], "partial")
        self.assertEqual(selected["summary"]["recordCount"], 2)
        self.assertEqual(selected["summary"]["sourceRecordCount"], 3)
        self.assertEqual(selected["summary"]["matchedRecordCount"], 2)
        self.assertEqual(selected["summary"]["coverage"]["reasonCode"], "maximum_count_boundary")

    def test_unconfigured_source_is_distinct_from_valid_empty_selection(self) -> None:
        os.environ.pop("ONE_C_HARNESS_EVENTLOG_COMMAND")
        unavailable = self._select()
        os.environ["ONE_C_HARNESS_EVENTLOG_COMMAND"] = str(self.command)
        self.xml.write_text('<?xml version="1.0"?><v8e:EventLog xmlns:v8e="http://v8.1c.ru/eventLog"/>', encoding="utf-8")
        empty = self._select()
        self.assertEqual(unavailable["status"], "unavailable")
        self.assertEqual(unavailable["reasonCode"], "source_unavailable")
        self.assertEqual(empty["status"], "ok")
        self.assertEqual(empty["summary"]["recordCount"], 0)

    def test_only_closed_safe_exporter_failure_is_exposed(self) -> None:
        self.command.write_text(textwrap.dedent("""\
            #!/usr/bin/env python3
            import json, sys
            sys.stderr.write(json.dumps({
                "reasonCode": "source_process_failed", "stage": "enterprise_process",
                "message": "External data processor could not be opened",
            }))
            raise SystemExit(2)
        """), encoding="utf-8")
        result = self._select()
        self.assertEqual(result, {
            "status": "unavailable", "reasonCode": "source_process_failed",
            "stage": "enterprise_process", "message": "External data processor could not be opened",
        })

        self.command.write_text("#!/usr/bin/env python3\nimport sys; sys.stderr.write('/private/token'); raise SystemExit(2)\n", encoding="utf-8")
        result = self._select()
        self.assertEqual(result, {
            "status": "unavailable", "reasonCode": "source_failed", "message": "registration log source failed",
        })

    def test_invalid_request_is_blocked_before_command(self) -> None:
        cases = [
            {"start": "bad"},
            {"end": "2026-09-24T06:45:00"},
            {"maximumCount": 101},
            {"limit": 21},
            {"filters": {"unknown": "x"}},
            {"filters": {"event": ""}},
            {"filters": {"level": "Critical"}},
        ]
        for values in cases:
            with self.subTest(values=values):
                self.request_capture.unlink(missing_ok=True)
                result = self._select(**values)
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(result["reasonCode"], "invalid_request")
                self.assertFalse(self.request_capture.exists())

    def test_tampered_and_expired_selections_fail_closed(self) -> None:
        selected = self._select()
        path = self.project / ".local/runs/eventlog-selections" / f"{selected['selectionRef'].split(':', 1)[1]}.json"
        value = json.loads(path.read_text()); value["records"][0]["event"] = "tampered"; path.write_text(json.dumps(value))
        self.assertEqual(eventlog_observation.page(self.project, selected["selectionRef"], 0, 1)["reasonCode"], "evidence_not_found")
        selected = self._select()
        path = self.project / ".local/runs/eventlog-selections" / f"{selected['selectionRef'].split(':', 1)[1]}.json"
        value = json.loads(path.read_text()); value["expiresAt"] = time.time() - 1; path.write_text(json.dumps(value))
        self.assertEqual(eventlog_observation.record(self.project, f"{selected['selectionRef']}:record:0:any")["reasonCode"], "evidence_not_found")

    def test_malformed_xml_is_not_reported_as_empty(self) -> None:
        self.xml.write_text("not xml", encoding="utf-8")
        result = self._select()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reasonCode"], "source_invalid")

    def test_timeout_nonzero_and_byte_limit_are_typed_failures(self) -> None:
        survivor = self.root / "survivor"
        self.command.write_text(textwrap.dedent(f"""\
            #!/usr/bin/env python3
            import subprocess, sys, time
            subprocess.Popen([sys.executable, '-c', "import time,pathlib; time.sleep(.2); pathlib.Path({str(survivor)!r}).write_text('late')"])
            time.sleep(1)
        """), encoding="utf-8")
        with mock.patch.object(eventlog_observation, "_TIMEOUT_SECONDS", 0.02):
            timed_out = self._select()
        time.sleep(.3)
        self.assertEqual(timed_out["status"], "unavailable")
        self.assertEqual(timed_out["reasonCode"], "source_timeout")
        self.assertFalse(survivor.exists())

        self.command.write_text("#!/usr/bin/env python3\nraise SystemExit(2)\n", encoding="utf-8")
        failed = self._select()
        self.assertEqual(failed["reasonCode"], "source_failed")

        completed = self.root / "completed"
        self.command.write_text(textwrap.dedent(f"""\
            #!/usr/bin/env python3
            import pathlib, sys, time
            sys.stdin.buffer.read()
            for _ in range(100):
                sys.stdout.buffer.write(b'x' * 1024); sys.stdout.buffer.flush(); time.sleep(.01)
            pathlib.Path({str(completed)!r}).write_text('unbounded')
        """), encoding="utf-8")
        with mock.patch.object(eventlog_observation, "_MAX_XML_BYTES", 4096):
            too_large = self._select()
        self.assertEqual(too_large["status"], "blocked")
        self.assertEqual(too_large["reasonCode"], "source_byte_limit")
        self.assertFalse(completed.exists())

    def test_unsafe_xml_and_symlinked_cache_fail_closed(self) -> None:
        self.xml.write_text('<!DOCTYPE x [<!ENTITY y "z">]><v8e:EventLog xmlns:v8e="http://v8.1c.ru/eventLog"/>', encoding="utf-8")
        unsafe = self._select()
        self.assertEqual(unsafe["reasonCode"], "source_invalid")

        cache = self.project / ".local/runs/eventlog-selections"
        if cache.exists():
            for child in cache.iterdir(): child.unlink()
            cache.rmdir()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.symlink_to(self.root)
        linked = self._select()
        self.assertEqual(linked["status"], "blocked")
        self.assertEqual(linked["reasonCode"], "source_invalid")

    def test_maximum_first_page_stays_inside_companion_output_budget(self) -> None:
        event = (
            "<v8e:Event><v8e:Level>" + "L" * 32 + "</v8e:Level>"
            "<v8e:Date>2026-09-22T06:44:16</v8e:Date>"
            "<v8e:Event>" + "E" * 128 + "</v8e:Event>"
            "<v8e:EventPresentation>" + "P" * 160 + "</v8e:EventPresentation>"
            "<v8e:User>" + "U" * 80 + "</v8e:User><v8e:UserPresentation>" + "Q" * 160 + "</v8e:UserPresentation>"
            "<v8e:Metadata>" + "M" * 128 + "</v8e:Metadata><v8e:MetadataPresentation>" + "N" * 160 + "</v8e:MetadataPresentation>"
            "<v8e:TransactionStatus>" + "T" * 32 + "</v8e:TransactionStatus>"
            "<v8e:Comment>" + "Ж" * 512 + "</v8e:Comment></v8e:Event>"
        )
        self.xml.write_text('<?xml version="1.0"?><v8e:EventLog xmlns:v8e="http://v8.1c.ru/eventLog">' + event * 20 + '</v8e:EventLog>', encoding="utf-8")
        selected = self._select()
        serialized = companion._dump({
            "artifactId": companion.ARTIFACT_ID,
            "capabilityVersion": companion.CAPABILITY_VERSION,
            "operation": "eventlog_select", "schemaVersion": 1, **selected,
        }).encode("utf-8")
        self.assertEqual(selected["summary"]["recordCount"], 20)
        self.assertLessEqual(len(serialized), 32 * 1024)
        self.assertNotEqual(json.loads(serialized)["status"], "blocked")

    def test_comment_continuation_rejects_a_chunk_too_small_for_one_codepoint(self) -> None:
        self.xml.write_text(
            '<?xml version="1.0"?><v8e:EventLog xmlns:v8e="http://v8.1c.ru/eventLog">'
            '<v8e:Event><v8e:Level>Error</v8e:Level><v8e:Date>2026-09-22T06:44:00</v8e:Date>'
            '<v8e:Event>Unicode</v8e:Event><v8e:Comment>Я😀Я</v8e:Comment></v8e:Event></v8e:EventLog>',
            encoding="utf-8",
        )
        selected = self._select(limit=1)
        result = eventlog_observation.record(
            self.project, selected["records"][0]["recordRef"], 0, 1,
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reasonCode"], "invalid_request")
        pieces: list[str] = []
        offset = 0
        while True:
            result = eventlog_observation.record(
                self.project, selected["records"][0]["recordRef"], offset, 4,
            )
            self.assertNotEqual(result["status"], "blocked")
            pieces.append(result["record"]["comment"])
            continuation = result["record"]["commentContinuation"]
            if continuation["complete"]:
                break
            self.assertGreater(continuation["nextOffsetBytes"], offset)
            offset = continuation["nextOffsetBytes"]
        self.assertEqual("".join(pieces), "Я😀Я")


if __name__ == "__main__":
    unittest.main()
