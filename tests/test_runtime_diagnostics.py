from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from one_c_harness import runtime_diagnostics


UTC = timezone.utc


def record(source: str, record_id: str, timestamp: datetime, kind: str, **attributes: object) -> dict[str, object]:
    return {
        "source": source,
        "recordId": record_id,
        "occurredAt": timestamp.isoformat().replace("+00:00", "Z"),
        "kind": kind,
        "attributes": attributes,
    }


class RuntimeDiagnosticsTests(unittest.TestCase):
    def test_investigate_groups_correlated_anomaly_and_keeps_evidence_refs(self) -> None:
        start = datetime(2026, 9, 18, 8, 12, tzinfo=UTC)
        end = datetime(2026, 9, 18, 9, 47, tzinfo=UTC)
        records = []
        for number in range(37):
            records.append(record(
                "rac", f"session-{number}", start + timedelta(minutes=number), "session",
                job="HonestMarkExchange", pid="8420",
            ))
        for number, cpu in enumerate((68, 72, 73)):
            records.append(record(
                "os", f"sample-{number}", start + timedelta(minutes=20 * number), "process_sample",
                pid="8420", cpuPercent=cpu,
            ))
        for number in range(19):
            records.append(record(
                "techlog", f"timeout-{number}", start + timedelta(minutes=number), "timeout",
                pid="8420", job="HonestMarkExchange",
            ))

        result = runtime_diagnostics.investigate(records, start, end)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["summary"]["recordCount"], 59)
        finding = result["findings"][0]
        self.assertEqual(finding["kind"], "job_runtime_anomaly")
        self.assertEqual(finding["observed"]["job"], "HonestMarkExchange")
        self.assertEqual(finding["observed"]["sessionCount"], 37)
        self.assertEqual(finding["observed"]["pid"], "8420")
        self.assertEqual(finding["observed"]["cpuAvgPercent"], 71)
        self.assertEqual(finding["observed"]["timeoutCount"], 19)
        self.assertEqual(finding["classification"], "derived_deterministically")
        self.assertNotIn("cause", finding)
        self.assertTrue(finding["evidenceRefs"])
        groups = {item["ref"]: item for item in result["evidenceGroups"]}
        self.assertTrue(all(ref in groups for ref in finding["evidenceRefs"]))
        self.assertEqual(sum(len(groups[ref]["recordRefs"]) for ref in finding["evidenceRefs"]), 59)

    def test_investigate_fails_closed_on_invalid_or_out_of_window_record(self) -> None:
        start = datetime(2026, 9, 18, 8, 12, tzinfo=UTC)
        end = datetime(2026, 9, 18, 9, 47, tzinfo=UTC)
        malformed = {
            "source": "rac", "recordId": "session-1", "occurredAt": "not-a-time",
            "kind": "session", "attributes": {},
        }

        result = runtime_diagnostics.investigate([malformed], start, end)

        self.assertEqual(result, {
            "status": "blocked",
            "reasonCode": "provider_record_invalid",
            "message": "runtime provider returned an invalid record",
        })


if __name__ == "__main__":
    unittest.main()
