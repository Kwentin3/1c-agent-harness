from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from one_c_harness import native_run_history


UTC = timezone.utc


def _receipt(root: Path, run: str, *, status: str, seconds: float, occurred_at: datetime) -> None:
    path = root / ".local/runs/native-cycle" / run / "run/result.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "schemaVersion": 1,
        "status": status,
        "totalDurationSeconds": seconds,
        "environment": {"HOME": "/private/source/path"},
        "resultPath": "/private/source/path/result.json",
    }), encoding="utf-8")
    timestamp = occurred_at.timestamp()
    path.touch()
    import os
    os.utime(path, (timestamp, timestamp))


class NativeRunHistoryTests(unittest.TestCase):
    def test_investigate_finds_real_timeout_history_and_expand_keeps_safe_source_record(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            start = datetime(2026, 9, 18, 8, 0, tzinfo=UTC)
            _receipt(project, "run-a", status="runtime_contract_completed", seconds=71.5, occurred_at=start)
            _receipt(project, "run-b", status="runtime_timeout", seconds=245.7, occurred_at=start)
            _receipt(project, "run-c", status="runtime_timeout", seconds=383.3, occurred_at=start)

            result = native_run_history.investigate(project, start, start, limit=10)
            finding = result["findings"][0]
            expanded = native_run_history.expand(project, finding["evidenceRefs"][0], limit=10)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["summary"]["recordCount"], 3)
        self.assertEqual(result["summary"]["statusCounts"], {
            "runtime_contract_completed": 1,
            "runtime_timeout": 2,
        })
        self.assertEqual(finding["classification"], "derived_deterministically")
        self.assertEqual(finding["observed"], {
            "status": "runtime_timeout",
            "runCount": 2,
            "durationMaxSeconds": 383.3,
        })
        self.assertEqual(expanded["status"], "ok")
        self.assertEqual(len(expanded["records"]), 2)
        self.assertEqual(
            {record["raw"] ["status"] for record in expanded["records"]},
            {"runtime_timeout"},
        )
        self.assertNotIn("/private/source/path", json.dumps(expanded))
        self.assertNotIn(str(project), json.dumps(expanded))

    def test_investigate_rejects_invalid_window_and_expand_rejects_unknown_ref(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            point = datetime(2026, 9, 18, 8, 0, tzinfo=UTC)
            _receipt(project, "run-a", status="runtime_timeout", seconds=245.7, occurred_at=point)

            invalid = native_run_history.investigate(project, point, point.replace(tzinfo=None), limit=10)
            missing = native_run_history.expand(project, "evidence:native-run-history:not-real", limit=10)

        self.assertEqual(invalid["reasonCode"], "invalid_request")
        self.assertEqual(missing["reasonCode"], "evidence_not_found")


if __name__ == "__main__":
    unittest.main()
