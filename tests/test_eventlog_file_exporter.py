from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "one_c_harness"))
import eventlog_file_exporter as exporter
import eventlog_exporter as base


REQUEST = {
    "schemaVersion": 1,
    "operation": "unloadEventLog",
    "start": "2026-09-23T00:00:00",
    "end": "2026-09-23T23:59:59",
    "filters": {"event": "Issue80.Lab.Page"},
    "columns": list(base.COLUMNS),
    "maximumCount": 100,
    "maximumBytes": 1048576,
}


class FileJournalExporterTests(unittest.TestCase):
    def test_streamed_digest_keeps_original_tree_identity(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "a").write_bytes(b"x" * 70000)
            (root / "b").write_bytes(b"y")
            digest = hashlib.sha256()
            for path in sorted(root.rglob("*")):
                rel = path.relative_to(root).as_posix().encode()
                data = path.read_bytes()
                digest.update(len(rel).to_bytes(4, "big"))
                digest.update(rel)
                digest.update(len(data).to_bytes(8, "big"))
                digest.update(data)
            self.assertEqual(exporter._digest_tree(root), (2, digest.hexdigest()))
            with self.assertRaises(base.ExportFailure) as caught:
                exporter._digest_tree(root, max_bytes=100)
            self.assertEqual(str(caught.exception), "source_byte_limit")

    def test_json_sequence_maps_ibcmd_fields_to_existing_xml_contract(self) -> None:
        payload = (
            '{"Date":"2026-09-23T18:22:32","Level":"Information",'
            '"Event":"Issue80.Lab.Page","EventPresentation":"Issue80.Lab.Page",'
            '"User":"071523a4-516f-4fce-ba4b-0d11ab7a1893","UserName":"",'
            '"Metadata":"02d54a8a-5f19-4d56-acb8-daf2360b9f53",'
            '"MetadataPresentation":"Document.SalesInvoice",'
            '"TransactionStatus":"NotApplicable","Comment":"Page event 01"}\n'
            '{"Date":"2026-09-23T18:22:33","Level":"Warning",'
            '"Event":"Issue80.Lab.Page","EventPresentation":"Issue80.Lab.Page",'
            '"User":"user-id","UserName":"Alice",'
            '"Metadata":"metadata-id","MetadataPresentation":"Catalog.Companies",'
            '"TransactionStatus":"RolledBack","Comment":"Page event 02"}\n'
        ).encode()

        xml = exporter._json_sequence_to_xml(payload, 1048576)
        root = ET.fromstring(xml)
        self.assertEqual(root.tag.rsplit("}", 1)[-1], "EventLog")
        records = list(root)
        self.assertEqual(len(records), 2)
        first = {child.tag.rsplit("}", 1)[-1]: child.text or "" for child in records[0]}
        second = {child.tag.rsplit("}", 1)[-1]: child.text or "" for child in records[1]}
        self.assertEqual(first["Metadata"], "Document.SalesInvoice")
        self.assertEqual(first["MetadataPresentation"], "Document.SalesInvoice")
        self.assertEqual(first["User"], "071523a4-516f-4fce-ba4b-0d11ab7a1893")
        self.assertNotIn("UserPresentation", first)
        self.assertEqual(second["UserPresentation"], "Alice")
        self.assertEqual(second["TransactionStatus"], "RolledBack")
        self.assertEqual(second["Comment"], "Page event 02")

    def test_invalid_json_or_missing_required_field_fails_closed(self) -> None:
        for payload in (b"not json", b'{"Date":"2026-09-23T18:22:32"}'):
            with self.subTest(payload=payload):
                with self.assertRaises(base.ExportFailure) as caught:
                    exporter._json_sequence_to_xml(payload, 1048576)
                self.assertEqual(str(caught.exception), "source_incomplete_receipt")

    def test_run_once_invokes_one_fixed_ibcmd_export_and_preserves_journal(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal = root / "journal"
            journal.mkdir()
            (journal / "1Cv8.lgf").write_bytes(b"index")
            (journal / "segment.lgp").write_bytes(b"segment")
            work = root / "work"
            metrics = root / "metrics.json"
            argv_receipt = root / "argv.json"
            ibcmd = root / "ibcmd"
            ibcmd.write_text(textwrap.dedent(f"""\
                #!{sys.executable}
                import json, pathlib, sys
                pathlib.Path({str(argv_receipt)!r}).write_text(json.dumps(sys.argv[1:]))
                out = next(value.split('=', 1)[1] for value in sys.argv if value.startswith('--out='))
                pathlib.Path(out).write_text(json.dumps({{
                    'Date':'2026-09-23T18:22:32','Level':'Information',
                    'Event':'Issue80.Lab.Page','EventPresentation':'Issue80.Lab.Page',
                    'User':'user-id','UserName':'Alice','Metadata':'metadata-id',
                    'MetadataPresentation':'Document.SalesInvoice',
                    'TransactionStatus':'NotApplicable','Comment':'Page event 01'
                }}))
            """), encoding="utf-8")
            ibcmd.chmod(ibcmd.stat().st_mode | stat.S_IXUSR)
            before = exporter._digest_tree(journal)
            environment = {
                exporter.IBCMD_ENV: str(ibcmd),
                exporter.JOURNAL_ENV: str(journal),
                exporter.WORK_ROOT_ENV: str(work),
                exporter.METRICS_ENV: str(metrics),
            }

            with mock.patch.dict("os.environ", environment, clear=True), \
                 mock.patch.object(exporter.subprocess, "Popen", wraps=subprocess.Popen) as popen:
                xml, result = exporter.run_once(REQUEST)

            self.assertEqual(exporter._digest_tree(journal), before)
            self.assertEqual(len(ET.fromstring(xml)), 1)
            argv = json.loads(argv_receipt.read_text())
            self.assertEqual(argv[:4], ["eventlog", "export", "--format=json", "--skip-root"])
            self.assertIn("--from=2026-09-23T00:00:00", argv)
            self.assertIn("--to=2026-09-23T23:59:59", argv)
            self.assertEqual(argv[-1], str(journal))
            self.assertEqual(result["backend"], "ibcmd")
            self.assertEqual(result["nativeExportSessions"], 1)
            self.assertEqual(json.loads(metrics.read_text())["recordCount"], 1)
            self.assertEqual(list(work.iterdir()), [])
            self.assertIs(popen.call_args.kwargs["stderr"], subprocess.DEVNULL)

    def test_post_exit_byte_limit_is_checked_before_reading_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal = root / "journal"
            journal.mkdir()
            (journal / "1Cv8.lgf").write_bytes(b"index")
            (journal / "segment.lgp").write_bytes(b"segment")
            ibcmd = root / "ibcmd"
            ibcmd.write_text(textwrap.dedent(f"""\
                #!{sys.executable}
                import pathlib, sys
                out = next(value.split('=', 1)[1] for value in sys.argv if value.startswith('--out='))
                pathlib.Path(out).write_bytes(b'x' * 4096)
            """), encoding="utf-8")
            ibcmd.chmod(ibcmd.stat().st_mode | stat.S_IXUSR)
            settings = exporter.Settings(ibcmd, journal, root / "work", None)
            settings.work_root.mkdir()
            request = {"start": REQUEST["start"], "end": REQUEST["end"], "maximumBytes": 32}

            with tempfile.TemporaryDirectory(dir=settings.work_root) as work:
                work_path = Path(work)
                process = mock.Mock(returncode=0)
                process.poll.return_value = 0

                def launch(argv, **_kwargs):
                    output = Path(next(value.split("=", 1)[1] for value in argv if value.startswith("--out=")))
                    output.write_bytes(b"x" * 4096)
                    return process

                with mock.patch.object(exporter.subprocess, "Popen", side_effect=launch), \
                     mock.patch.object(Path, "read_bytes", side_effect=AssertionError("oversized output was read")):
                    with self.assertRaises(base.ExportFailure) as caught:
                        exporter._run_ibcmd(settings, request, work_path, exporter.time.monotonic() + 5)

            self.assertEqual(str(caught.exception), "source_byte_limit")

    def test_symlink_ibcmd_and_overlapping_work_root_are_rejected_before_process(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal = root / "journal"
            journal.mkdir()
            (journal / "1Cv8.lgf").write_bytes(b"index")
            (journal / "segment.lgp").write_bytes(b"segment")
            binary = root / "binary"
            binary.write_text("x")
            binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
            link = root / "ibcmd"
            link.symlink_to(binary)
            environment = {
                exporter.IBCMD_ENV: str(link),
                exporter.JOURNAL_ENV: str(journal),
                exporter.WORK_ROOT_ENV: str(journal / "work"),
            }
            with mock.patch.dict("os.environ", environment, clear=True), \
                 mock.patch.object(exporter.subprocess, "Popen") as process:
                with self.assertRaises(base.ExportFailure) as caught:
                    exporter.run_once(REQUEST)
            self.assertEqual(str(caught.exception), "configuration_invalid")
            process.assert_not_called()
            self.assertFalse((journal / "work").exists())

    def test_metrics_hardlink_to_journal_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal = root / "journal"
            journal.mkdir()
            (journal / "1Cv8.lgf").write_bytes(b"index")
            segment = journal / "segment.lgp"
            segment.write_bytes(b"segment")
            ibcmd = root / "ibcmd"
            ibcmd.write_text("#!/bin/sh\nexit 0\n")
            ibcmd.chmod(ibcmd.stat().st_mode | stat.S_IXUSR)
            metrics = root / "metrics.json"
            os.link(segment, metrics)
            environment = {
                exporter.IBCMD_ENV: str(ibcmd),
                exporter.JOURNAL_ENV: str(journal),
                exporter.WORK_ROOT_ENV: str(root / "work"),
                exporter.METRICS_ENV: str(metrics),
            }

            with mock.patch.dict("os.environ", environment, clear=True):
                with self.assertRaises(base.ExportFailure) as caught:
                    exporter._settings()

            self.assertEqual(str(caught.exception), "configuration_invalid")
            self.assertEqual(segment.read_bytes(), b"segment")

    def test_symlinked_ancestor_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            real = root / "real"
            real.mkdir()
            alias = root / "alias"
            alias.symlink_to(real, target_is_directory=True)
            ibcmd = real / "ibcmd"
            ibcmd.write_text("#!/bin/sh\nexit 0\n")
            ibcmd.chmod(ibcmd.stat().st_mode | stat.S_IXUSR)
            journal = root / "journal"
            journal.mkdir()
            (journal / "1Cv8.lgf").write_bytes(b"index")
            (journal / "segment.lgp").write_bytes(b"segment")
            environment = {
                exporter.IBCMD_ENV: str(alias / "ibcmd"),
                exporter.JOURNAL_ENV: str(journal),
                exporter.WORK_ROOT_ENV: str(root / "work"),
            }

            with mock.patch.dict("os.environ", environment, clear=True):
                with self.assertRaises(base.ExportFailure) as caught:
                    exporter._settings()

            self.assertEqual(str(caught.exception), "configuration_invalid")

    def test_metrics_hardlink_to_ibcmd_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal = root / "journal"
            journal.mkdir()
            (journal / "1Cv8.lgf").write_bytes(b"index")
            (journal / "segment.lgp").write_bytes(b"segment")
            ibcmd = root / "ibcmd"
            ibcmd.write_text("#!/bin/sh\nexit 0\n")
            ibcmd.chmod(ibcmd.stat().st_mode | stat.S_IXUSR)
            metrics = root / "metrics.json"
            os.link(ibcmd, metrics)
            environment = {
                exporter.IBCMD_ENV: str(ibcmd),
                exporter.JOURNAL_ENV: str(journal),
                exporter.WORK_ROOT_ENV: str(root / "work"),
                exporter.METRICS_ENV: str(metrics),
            }

            with mock.patch.dict("os.environ", environment, clear=True):
                with self.assertRaises(base.ExportFailure) as caught:
                    exporter._settings()

            self.assertEqual(str(caught.exception), "configuration_invalid")


if __name__ == "__main__":
    unittest.main()
