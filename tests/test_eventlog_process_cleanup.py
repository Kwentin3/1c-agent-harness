"""Real harmless child processes; only thread admission is fault-injected."""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from one_c_harness import eventlog_exporter as enterprise
from one_c_harness import eventlog_file_exporter as file_exporter
from one_c_harness import eventlog_observation as reader


@unittest.skipUnless(os.name == "posix", "Production subprocess groups require POSIX")
class ProcessAdmissionCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="eventlog-cleanup-")
        self.root = Path(self.temporary.name)
        self.processes: list[subprocess.Popen] = []
        self.real_popen = subprocess.Popen
        self.command = self.root / "harmless-python-child"
        self.command.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(60)\n", encoding="utf-8")
        self.command.chmod(0o755)
        xvfb = self.root / "argument-shim"
        xvfb.write_text(
            '#!/bin/sh\n[ "$1" = "-a" ] && shift\n'
            'if [ "$1" = "-e" ]; then shift 2; fi\n'
            'if [ "$1" = "-s" ]; then shift 2; fi\nexec "$@"\n', encoding="utf-8",
        )
        xvfb.chmod(0o755)
        libs = self.root / "libs"; libs.mkdir()
        fonts = self.root / "fonts.conf"; fonts.write_text("fixture", encoding="utf-8")
        profile = self.root / "runtime.json"
        profile.write_text(json.dumps({"platform": str(self.command), "xvfb": str(xvfb),
                                       "libs": str(libs), "fontconfig": str(fonts)}), encoding="utf-8")
        infobase = self.root / "empty-test-directory"; infobase.mkdir()
        epf = self.root / "never-executed.epf"; epf.write_bytes(b"test fixture")
        journal = self.root / "journal"; journal.mkdir()
        (journal / "1Cv8.lgf").write_bytes(b"test fixture")
        (journal / "segment.lgp").write_bytes(b"test fixture")
        work = self.root / "work"
        self.environment = mock.patch.dict(os.environ, {
            "PATH": str(Path(sys.executable).parent) + os.pathsep + os.defpath,
            "ONE_C_HARNESS_EVENTLOG_RUNTIME_PROFILE": str(profile),
            "ONE_C_HARNESS_EVENTLOG_INFOBASE": str(infobase),
            "ONE_C_HARNESS_EVENTLOG_EPF": str(epf),
            "ONE_C_HARNESS_EVENTLOG_WORK_ROOT": str(work),
            "ONE_C_HARNESS_EVENTLOG_IBCMD": str(self.command),
            "ONE_C_HARNESS_EVENTLOG_JOURNAL": str(journal),
            "ONE_C_HARNESS_EVENTLOG_COMMAND": str(self.command),
            "ONE_C_HARNESS_EVENTLOG_TIME_ZONE": "UTC",
        }, clear=True)
        self.environment.start()
        self.request = {
            "schemaVersion": 1, "operation": "unloadEventLog",
            "start": "2026-10-01T00:00:00", "end": "2026-10-01T00:01:00",
            "filters": {}, "columns": list(enterprise.COLUMNS),
            "maximumCount": 100, "maximumBytes": 1048576,
        }
        self.private_error = "password=TEST_ONLY_SECRET /private/test-admission"

    def tearDown(self) -> None:
        # RED must also leave no test-owned sleeper. This cleanup happens only
        # AFTER the assertions that prove whether production reaped its child.
        for process in self.processes:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=3)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
        self.environment.stop()
        self.temporary.cleanup()

    def launch(self, *args, **kwargs):
        self.assertTrue(kwargs.get("start_new_session"), "Fixture must own its process group")
        process = self.real_popen(*args, **kwargs)
        self.processes.append(process)
        return process

    def assert_reaped_and_closed(self) -> None:
        self.assertEqual(len(self.processes), 1)
        process = self.processes[0]
        self.assertIsNotNone(process.returncode, "Production left its actual child running or unreaped")
        with self.assertRaises(ChildProcessError):
            os.waitpid(process.pid, os.WNOHANG)
        with self.assertRaises(ProcessLookupError):
            os.killpg(process.pid, 0)
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                self.assertTrue(stream.closed, "Production leaked a pipe after admission failure")

    def run_failed_admission(self, operation, *, result_is_error=False) -> None:
        result = error = None
        with mock.patch.object(subprocess, "Popen", side_effect=self.launch), \
             mock.patch("threading.Thread.start", side_effect=RuntimeError(self.private_error)):
            try:
                result = operation()
            except Exception as exc:
                error = exc
        self.assert_reaped_and_closed()
        if result_is_error:
            self.assertIsNone(error)
            self.assertEqual(result["status"], "unavailable")
            self.assertEqual(result["reasonCode"], "source_unavailable")
            public = json.dumps(result)
        else:
            self.assertIsInstance(error, enterprise.ExportFailure)
            self.assertEqual(str(error), "source_unavailable")
            public = json.dumps({"reasonCode": str(error), "diagnostic": error.diagnostic})
        self.assertNotIn("TEST_ONLY_SECRET", public)
        self.assertNotIn("/private/test-admission", public)
        self.assertNotIn(str(self.root), public)

    def test_enterprise_exporter_reaps_actual_child_when_thread_start_fails(self) -> None:
        self.run_failed_admission(lambda: enterprise.run_once(self.request))
        self.assertEqual(list((self.root / "work").glob("request-*")), [])

    def test_ibcmd_exporter_reaps_actual_child_when_thread_start_fails(self) -> None:
        self.run_failed_admission(lambda: file_exporter.run_once(self.request))
        self.assertIsNone(file_exporter._active)

    def test_reader_reaps_actual_child_when_thread_start_fails(self) -> None:
        project = self.root / "project"; project.mkdir()
        self.run_failed_admission(
            lambda: reader.select(project, self.request["start"], self.request["end"], {}, 100, 10),
            result_is_error=True,
        )
        self.assertEqual(list(project.rglob("selection-*.json")), [])


if __name__ == "__main__":
    unittest.main()
