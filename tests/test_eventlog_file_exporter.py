from __future__ import annotations

import json
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "one_c_harness"))
import eventlog_file_exporter as exporter
import eventlog_exporter as base


class FileJournalExporterTests(unittest.TestCase):
    def test_streamed_digest_keeps_original_tree_identity(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root/'a').write_bytes(b'x' * 70000)
            (root/'b').write_bytes(b'y')
            digest = hashlib.sha256()
            for path in sorted(root.rglob('*')):
                rel = path.relative_to(root).as_posix().encode()
                data = path.read_bytes()
                digest.update(len(rel).to_bytes(4, 'big'))
                digest.update(rel)
                digest.update(len(data).to_bytes(8, 'big'))
                digest.update(data)
            self.assertEqual(exporter._digest_tree(root), (2, digest.hexdigest()))
            with self.assertRaises(base.ExportFailure) as caught:
                exporter._digest_tree(root, max_bytes=100)
            self.assertEqual(str(caught.exception), 'source_byte_limit')
            with self.assertRaises(base.ExportFailure) as caught:
                exporter._digest_tree(root, max_files=1)
            self.assertEqual(str(caught.exception), 'source_byte_limit')
            with self.assertRaises(base.ExportFailure) as caught:
                exporter._digest_tree(root, deadline=0)
            self.assertEqual(str(caught.exception), 'source_timeout')

    def test_unavailable_columns_filter_is_refused_before_platform(self) -> None:
        request = {'schemaVersion':1, 'operation':'unloadEventLog',
                   'start':'2026-09-22T10:56:10', 'end':'2026-09-22T10:56:11',
                   'filters':{'user':'alice'}, 'columns':list(base.COLUMNS),
                   'maximumCount':10, 'maximumBytes':1048576}
        with mock.patch.object(exporter, '_settings') as settings:
            with self.assertRaises(base.ExportFailure) as caught:
                exporter.run_once(request)
        self.assertEqual(str(caught.exception), 'source_process_failed')
        settings.assert_not_called()

    def test_no_optional_filters_do_not_read_empty_files(self) -> None:
        generated = exporter._server_for({})
        self.assertIn('Root + "/1Cv8Log/1Cv8.lgf"', generated)
        self.assertEqual(generated.count('UnloadEventLog('), 1)
        self.assertNotIn('filter-event.txt', generated)
        self.assertNotIn('filter-level.txt', generated)
        self.assertNotIn('filter-user.txt', generated)
        self.assertNotIn('filter-metadata.txt', generated)

    def test_only_selected_fixed_filter_blocks_are_generated(self) -> None:
        for key in ('event', 'user', 'metadata', 'level'):
            with self.subTest(key=key):
                generated = exporter._server_for({key: 'x'})
                self.assertIn(f'filter-{key}.txt', generated)
                for other in {'event', 'user', 'metadata', 'level'} - {key}:
                    self.assertNotIn(f'filter-{other}.txt', generated)
        self.assertIn('ElsIf LevelName', exporter._server_for({'level': 'Error'}))

    def test_symlink_journal_is_rejected_before_platform(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            snapshot = root / 'snapshot'; snapshot.mkdir()
            (snapshot / 'Ext').mkdir(); (snapshot / 'Ext/ManagedApplicationModule.bsl').write_text(exporter.ANCHOR)
            journal = root / 'journal'; journal.mkdir()
            (journal / '1Cv8.lgf').write_bytes(b'index')
            (journal / 'segment.lgp').symlink_to(journal / '1Cv8.lgf')
            with mock.patch.dict('os.environ', {exporter.SNAPSHOT_ENV:str(snapshot),
                                               exporter.JOURNAL_ENV:str(journal)}), \
                 mock.patch.object(exporter, '_settings', return_value=base.Settings(
                     root/'binary', root/'xvfb', 'libs', root/'fonts', root/'ib', root/'epf',
                     root/'work', None, None, None)), \
                 mock.patch.object(exporter.subprocess, 'Popen') as process:
                request = {'schemaVersion':1, 'operation':'unloadEventLog',
                           'start':'2026-09-22T10:56:10', 'end':'2026-09-22T10:56:11',
                           'filters':{}, 'columns':list(base.COLUMNS),
                           'maximumCount':1, 'maximumBytes':1048576}
                with self.assertRaises(base.ExportFailure) as caught:
                    exporter.run_once(request)
                self.assertEqual(str(caught.exception), 'configuration_invalid')
                process.assert_not_called()

    def test_work_root_inside_source_is_refused_without_creating_it(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            snapshot = root/'snapshot'; snapshot.mkdir()
            journal = root/'journal'; journal.mkdir()
            (journal/'1Cv8.lgf').write_bytes(b'index')
            work = snapshot/'must-not-create'
            settings = base.Settings(root/'binary', root/'xvfb', 'libs', root/'fonts',
                                     root/'ib', root/'epf', work, None, None, None)
            with mock.patch.dict('os.environ', {exporter.SNAPSHOT_ENV:str(snapshot),
                                               exporter.JOURNAL_ENV:str(journal)}), \
                 mock.patch.object(exporter, '_settings', return_value=settings):
                request = {'schemaVersion':1, 'operation':'unloadEventLog',
                           'start':'2026-09-22T10:56:10', 'end':'2026-09-22T10:56:11',
                           'filters':{}, 'columns':list(base.COLUMNS),
                           'maximumCount':1, 'maximumBytes':1048576}
                with self.assertRaises(base.ExportFailure):
                    exporter.run_once(request)
            self.assertFalse(work.exists())

    def test_metrics_cannot_write_into_source(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            snapshot = root/'snapshot'; snapshot.mkdir()
            journal = root/'journal'; journal.mkdir()
            (journal/'1Cv8.lgf').write_bytes(b'index')
            metrics = journal/'metrics.json'
            settings = base.Settings(root/'binary', root/'xvfb', 'libs', root/'fonts',
                                     root/'ib', root/'epf', root/'work', None, None, metrics)
            with mock.patch.dict('os.environ', {exporter.SNAPSHOT_ENV:str(snapshot),
                                               exporter.JOURNAL_ENV:str(journal)}), \
                 mock.patch.object(exporter, '_settings', return_value=settings):
                request = {'schemaVersion':1, 'operation':'unloadEventLog',
                           'start':'2026-09-22T10:56:10', 'end':'2026-09-22T10:56:11',
                           'filters':{}, 'columns':list(base.COLUMNS),
                           'maximumCount':1, 'maximumBytes':1048576}
                with self.assertRaises(base.ExportFailure) as caught:
                    exporter.run_once(request)
            self.assertEqual(str(caught.exception), 'configuration_invalid')
            self.assertFalse(metrics.exists())


if __name__ == '__main__':
    unittest.main()
