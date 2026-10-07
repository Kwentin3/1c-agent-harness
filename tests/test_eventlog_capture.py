from __future__ import annotations
import base64
import hashlib
import json
import sys
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'one_c_harness'))
import eventlog_file_exporter as exporter
import eventlog_exporter as base
BINDING = {'schemaVersion': 1, 'name': 'Admitted demo', 'referenceId': 'a' * 64, 'referenceImage': 'sha256:' + 'b' * 64, 'vrdSha256': 'c' * 64, 'binarySha256': 'd' * 64}
REQUEST = {'schemaVersion': 1, 'operation': 'unloadEventLog', 'start': '2026-10-07T10:00:00', 'end': '2026-10-07T10:15:00', 'filters': {}, 'columns': list(base.COLUMNS), 'maximumCount': 100, 'maximumBytes': 1048576}
NOW = 1791368110.0

def receipt():
    payload = json.dumps({'Date': '2026-10-07T10:14:59', 'Level': 'Information', 'Event': '_$Session$_.Start', 'User': 'alice', 'UserName': 'Alice', 'Comment': 'observed comment'}).encode()
    directory = {'device': 71, 'inode': 12}
    return {'schemaVersion': 1, 'status': 'EXPORTED', 'nativeInvocations': 1, 'exitCode': 0, 'startedAtUnix': NOW - 2, 'durationSeconds': 1.0, 'uid': 10001, 'gid': 33, 'groups': [33], 'timeZone': 'UTC', 'binarySha256': BINDING['binarySha256'], 'sourceMountedReadOnly': True, 'rootFilesystemReadOnly': True, 'sourceDirectory': directory, 'sourceBefore': [{'name': '1Cv8.lgf', 'device': 71, 'inode': 13, 'bytes': 2, 'mtimeNs': 100, 'readProbeBytes': 2}, {'name': 'current.lgp', 'device': 71, 'inode': 14, 'bytes': 2, 'mtimeNs': 100, 'readProbeBytes': 2}], 'sourceBinding': {'referenceId': BINDING['referenceId'], 'referenceImage': BINDING['referenceImage'], 'vrdSha256': BINDING['vrdSha256'], 'currentIbPath': '/private/ib', 'journalPath': '/private/ib/1Cv8Log', 'sourceProbe': {'ibBindings': ['/private/ib'], 'journalDirectory': directory}}, 'outputBytes': len(payload), 'outputSha256': hashlib.sha256(payload).hexdigest(), 'outputBase64': base64.b64encode(payload).decode(), 'acquisitionConsistency': 'NOT_PROVEN_BY_ACCESS_CAPABILITY', 'argv': ['/opt/admitted-ibcmd/ibcmd', 'eventlog', 'export', '--format=json', '--skip-root', '--from=' + REQUEST['start'], '--to=' + REQUEST['end'], '--out=/work/eventlog.json', '/source/journal']}

class CaptureTests(unittest.TestCase):

    def test_valid_capture_carries_safe_provenance_but_not_temporal_completeness(self):
        self.assertTrue(callable(getattr(exporter, 'capture_to_xml', None)), 'capture adapter not implemented')
        value = receipt()
        value['sourceAfter'] = value['sourceBefore']
        xml = exporter.capture_to_xml(value, BINDING, REQUEST, now=NOW)
        root = ET.fromstring(xml)
        meta = json.loads(root.find('{urn:one-c-harness:eventlog-capture:1}Capture').text)
        self.assertEqual(meta['sourceIdentity']['name'], 'Admitted demo')
        self.assertEqual(meta['capture']['outputSha256'], value['outputSha256'])
        self.assertFalse(meta['temporalCoverage']['complete'])
        self.assertEqual(meta['temporalCoverage']['reasonCode'], 'capture_consistency_unproven')
        self.assertEqual(meta['freshness']['completeThrough'], None)
        self.assertNotIn('/private', xml.decode())
        self.assertNotIn('outputBase64', xml.decode())
        self.assertEqual(len(root.findall('{http://v8.1c.ru/eventLog}Event')), 1)

    def test_requested_end_aliases_are_compared_by_datetime_not_spelling(self):
        from datetime import datetime
        from one_c_harness import eventlog_observation
        for end in ('2026-10-07 10:15:00', '2026-10-07T10:15:00.000', '2026-10-07T10:15:00.5', '2026-10-07T10:15:00.123'):
            with self.subTest(end=end):
                request = {**REQUEST, 'end': end}
                value = receipt()
                value['sourceAfter'] = value['sourceBefore']
                value['argv'][6] = '--to=' + end
                try:
                    parsed_end = datetime.fromisoformat(end)
                except ValueError:
                    # Older Python ISO parsers reject single-digit fractions;
                    # do not widen the product timestamp contract for CI.
                    with self.assertRaisesRegex(base.ExportFailure, '^invalid_request$'):
                        exporter.capture_to_xml(value, BINDING, request, now=NOW)
                    continue
                xml = exporter.capture_to_xml(value, BINDING, request, now=NOW)
                count, records, metadata = eventlog_observation._parse(xml, datetime.fromisoformat(request['start']), parsed_end, {})
                self.assertEqual(count, 1)
                self.assertIsNotNone(metadata)
                with self.assertRaises(ValueError):
                    eventlog_observation._parse(xml, datetime.fromisoformat(request['start']), datetime.fromisoformat('2026-10-07T10:16:00'), {})

class CaptureAdmissionTests(unittest.TestCase):

    def test_actual_stale_capture_failure_survives_exporter_to_reader_boundary(self):
        from one_c_harness import eventlog_observation
        value = receipt()
        value['sourceAfter'] = value['sourceBefore']
        value['startedAtUnix'] = NOW - 61
        with self.assertRaises(base.ExportFailure) as raised:
            exporter.capture_to_xml(value, BINDING, REQUEST, now=NOW)
        result = eventlog_observation._source_error(exporter._failure_line(str(raised.exception), {}))
        self.assertEqual(result['reasonCode'], 'source_stale_capture')
        self.assertEqual(result['status'], 'unavailable')

    def test_malformed_binding_shape_is_a_binding_mismatch(self):
        for actual in (None, [], 'foreign', {}, {'referenceId': BINDING['referenceId']}):
            with self.subTest(actual=actual):
                value = receipt()
                value['sourceAfter'] = value['sourceBefore']
                value['sourceBinding'] = actual
                with self.assertRaisesRegex(base.ExportFailure, '^source_binding_mismatch$'):
                    exporter.capture_to_xml(value, BINDING, REQUEST, now=NOW)

    def test_wrong_binding_is_rejected_before_conversion(self):
        for field in ['referenceId', 'referenceImage', 'vrdSha256']:
            with self.subTest(field=field):
                value = receipt()
                value['sourceAfter'] = value['sourceBefore']
                value['sourceBinding'][field] = 'foreign'
                with self.assertRaisesRegex(base.ExportFailure, 'source_binding_mismatch'):
                    exporter.capture_to_xml(value, BINDING, REQUEST, now=NOW)

    def test_invalid_runtime_receipt_and_corrupt_output_fail_closed(self):
        mutations = [('binarySha256', 'f' * 64), ('uid', 0), ('groups', [0]), ('timeZone', 'Europe/Moscow'), ('exitCode', 1), ('nativeInvocations', 0), ('sourceMountedReadOnly', False), ('outputSha256', 'f' * 64), ('outputBytes', 1), ('outputBase64', '%%%'), ('durationSeconds', float('nan')), ('startedAtUnix', NOW - 61), ('startedAtUnix', NOW + 6), ('acquisitionConsistency', 'COMPLETE')]
        for key, new in mutations:
            with self.subTest(key=key, new=new):
                value = receipt()
                value['sourceAfter'] = value['sourceBefore']
                value[key] = new
                with self.assertRaises(base.ExportFailure):
                    exporter.capture_to_xml(value, BINDING, REQUEST, now=NOW)

    def test_foreign_window_and_directory_are_rejected(self):
        for key in ['argv', 'sourceDirectory', 'sourceProbe']:
            with self.subTest(key=key):
                value = receipt()
                value['sourceAfter'] = value['sourceBefore']
                if key == 'argv':
                    value['argv'][5] = '--from=2020-01-01T00:00:00'
                elif key == 'sourceDirectory':
                    value['sourceDirectory'] = {'device': 99, 'inode': 99}
                else:
                    value['sourceBinding']['sourceProbe']['ibBindings'] = ['/foreign']
                with self.assertRaises(base.ExportFailure):
                    exporter.capture_to_xml(value, BINDING, REQUEST, now=NOW)

    def test_deployment_capture_command_is_consumed_without_native_or_source_paths_in_request(self):
        import os, tempfile, textwrap, time
        from unittest import mock
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            command = root / 'capture'
            capture = root / 'requested.json'
            value = receipt()
            value['sourceAfter'] = value['sourceBefore']
            command.write_text('#!' + sys.executable + '\nimport pathlib,json,sys,time\nr=json.load(sys.stdin);pathlib.Path(' + repr(str(capture)) + ').write_text(json.dumps(r))\nv=json.loads(' + repr(json.dumps(value)) + ');v["startedAtUnix"]=time.time()-2;print(json.dumps(v))\n')
            command.chmod(493)
            binding = root / 'binding.json'
            binding.write_text(json.dumps(BINDING))
            with mock.patch.dict(os.environ, {'ONE_C_HARNESS_EVENTLOG_CAPTURE_COMMAND': str(command), 'ONE_C_HARNESS_EVENTLOG_CAPTURE_BINDING': str(binding), 'ONE_C_HARNESS_EVENTLOG_WORK_ROOT': str(root / 'work')}, clear=True):
                xml, metrics = exporter.run_once(REQUEST)
            self.assertEqual(json.loads(capture.read_text()), {'schemaVersion': 1, 'operation': 'export', 'start': REQUEST['start'], 'end': REQUEST['end'], 'format': 'json', 'followMilliseconds': 0})
            self.assertIn(b'urn:one-c-harness:eventlog-capture:1', xml)
            self.assertEqual(metrics['backend'], 'current_journal_capture')
            saved = list((root / 'work' / '.evidence').glob('capture-*.json'))
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0].stat().st_mode & 511, 384)
            self.assertNotIn(str(command), xml.decode())

    def test_capture_process_failures_and_invalid_binding_do_not_fallback(self):
        import os, tempfile
        from unittest import mock
        cases = [('unavailable', 'import sys;sys.stderr.write("/private/password=secret");sys.exit(2)', 'source_unavailable'), ('bytes', 'import sys;sys.stdout.write("x"*2200000)', 'source_byte_limit'), ('timeout', 'import time;time.sleep(2)', 'source_timeout'), ('binding', 'raise SystemExit("must not run")', 'configuration_invalid')]
        for name, body, reason in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                command = root / 'capture'
                command.write_text('#!' + sys.executable + '\n' + body + '\n')
                command.chmod(493)
                binding = root / 'binding'
                binding.write_text(json.dumps({} if name == 'binding' else BINDING))
                env = {'ONE_C_HARNESS_EVENTLOG_CAPTURE_COMMAND': str(command), 'ONE_C_HARNESS_EVENTLOG_CAPTURE_BINDING': str(binding), 'ONE_C_HARNESS_EVENTLOG_WORK_ROOT': str(root / 'work')}
                with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(exporter, '_CAPTURE_TIMEOUT_SECONDS', 0.05 if name == 'timeout' else 5):
                    with self.assertRaisesRegex(base.ExportFailure, reason):
                        exporter.run_once(REQUEST)
                self.assertFalse((root / 'work' / '.evidence').exists())
    def test_capture_evidence_symlink_is_refused_before_command(self):
        import os
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            marker = root / 'invoked'
            command = root / 'capture'
            command.write_text('#!' + sys.executable + '\nimport pathlib\npathlib.Path(' + repr(str(marker)) + ').write_text("called")\n')
            command.chmod(0o755)
            binding = root / 'binding'
            binding.write_text(json.dumps(BINDING))
            work = root / 'work'
            work.mkdir()
            (work / '.evidence').symlink_to(root)
            env = {'ONE_C_HARNESS_EVENTLOG_CAPTURE_COMMAND': str(command), 'ONE_C_HARNESS_EVENTLOG_CAPTURE_BINDING': str(binding), 'ONE_C_HARNESS_EVENTLOG_WORK_ROOT': str(work)}
            with mock.patch.dict(os.environ, env, clear=True):
                with self.assertRaisesRegex(base.ExportFailure, 'configuration_invalid'):
                    exporter.run_once(REQUEST)
            self.assertFalse(marker.exists())

if __name__ == '__main__':
    unittest.main()
