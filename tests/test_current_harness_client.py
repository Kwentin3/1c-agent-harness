"""Fixed product transport and shared native binding, with no live SSH/1C."""
import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
EXPORT = {'schemaVersion': 1, 'operation': 'export', 'start': '2026-10-22T00:00:00',
          'end': '2026-10-22T00:01:00', 'format': 'json', 'followMilliseconds': 0}


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'deployment/goal91' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def envelope(operation='logging_control', arguments=None):
    return {'schemaVersion': 1, 'operation': operation,
            'arguments': {'action': 'status', 'journal': 'technological'} if arguments is None else arguments}


def wire(value):
    return 'current-harness-v1 ' + base64.b64encode(json.dumps(value).encode()).decode()


class CurrentHarnessClientTests(unittest.TestCase):
    def setUp(self):
        self.client = load('product_client', 'current-harness-client.py')
        self.handler = load('product_handler', 'current-journal.py')
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.config = self.root / 'ssh-config'
        self.config.write_text('# fixed fixture')

    def test_all_closed_operations_use_only_existing_alias_and_new_prefix(self):
        with mock.patch.dict(os.environ, {'ONE_C_HARNESS_CURRENT_JOURNAL_SSH_CONFIG': str(self.config)}):
            for operation in self.client.OPERATIONS:
                request = envelope(operation, EXPORT if operation == 'eventlog_capture' else {})
                argv = self.client.command(request)
                self.assertEqual(argv[:5], ['/usr/bin/ssh', '-F', str(self.config), '-T', 'current-journal'])
                self.assertTrue(argv[-1].startswith('current-harness-v1 '))
                self.assertEqual(json.loads(base64.b64decode(argv[-1].split(' ')[1])), request)

    def test_request_and_base64_limits_are_bounded_and_not_legacy_4096(self):
        with mock.patch.dict(os.environ, {'ONE_C_HARNESS_CURRENT_JOURNAL_SSH_CONFIG': str(self.config)}):
            argv = self.client.command(envelope('observe', {'query': 'x' * 8000}))
            self.assertGreater(len(argv[-1]), 4096)
            self.assertLess(len(argv[-1].split(' ')[1]), 24576)
            with self.assertRaises(ValueError):
                self.client.command(envelope('observe', {'query': 'x' * 16384}))
            for request in (envelope('shell'), {**envelope(), 'source': '/tmp/evil'},
                            {**envelope(), 'arguments': []}, {**envelope(), 'schemaVersion': True}):
                with self.assertRaises(ValueError):
                    self.client.command(request)

    def test_absent_source_and_invalid_envelope_never_reach_binding_capture_or_ledger(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch.object(self.handler, '_binding') as binding, \
                mock.patch.object(self.handler, '_capture') as capture, \
                mock.patch.object(self.handler, 'reserve_budget') as reserve:
            for command in (wire(envelope()), wire(envelope('shell')), wire({**envelope(), 'source': '/evil'}),
                            'current-harness-v1 ' + 'A' * 24577):
                with self.assertRaises(ValueError):
                    self.handler._product_command(command)
            binding.assert_not_called()
            capture.assert_not_called()
            reserve.assert_not_called()

    def test_product_export_reuses_exact_capture_without_legacy_budget_and_refuses_probe(self):
        result = {'status': 'EXPORTED', 'outputSha256': 'a' * 64}
        with mock.patch.dict(os.environ, {'CURRENT_HARNESS_SOURCE': '/opt/one-c-harness/revision'}), \
                mock.patch.object(self.handler, '_capture', return_value=result) as capture, \
                mock.patch.object(self.handler, 'reserve_budget') as reserve, \
                mock.patch.object(self.handler, 'settle_budget') as settle:
            self.assertEqual(self.handler._product_command(wire(envelope('eventlog_capture', EXPORT))), result)
            capture.assert_called_once_with(EXPORT)
            for arguments in ({'schemaVersion': 1, 'operation': 'probe'}, {**EXPORT, 'source': '/evil'}):
                with self.assertRaises(ValueError):
                    self.handler._product_command(wire(envelope('eventlog_capture', arguments)))
            reserve.assert_not_called()
            settle.assert_not_called()

    def test_legacy_main_still_reserves_captures_settles_and_preserves_receipt(self):
        calls = []
        result = {'status': 'EXPORTED', 'outputBase64': 'YQ=='}
        legacy = 'current-journal-v1 ' + base64.b64encode(json.dumps(EXPORT).encode()).decode()
        with mock.patch.dict(os.environ, {'SSH_ORIGINAL_COMMAND': legacy}, clear=True), \
                mock.patch.object(self.handler, 'reserve_budget', side_effect=lambda *a: calls.append(('reserve', a)) or 'attempt'), \
                mock.patch.object(self.handler, '_capture', side_effect=lambda v: calls.append(('capture', v)) or result), \
                mock.patch.object(self.handler, 'settle_budget', side_effect=lambda *a: calls.append(('settle', a))), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.handler.main()
        self.assertEqual(json.loads(output.getvalue()), result)
        self.assertEqual([call[0] for call in calls], ['reserve', 'capture', 'settle'])
        self.assertEqual(calls[0][1], ('export', EXPORT))
        self.assertEqual(calls[2][1][:2], ('attempt', result))

    @unittest.skipUnless(os.name == 'posix', 'existing forced handler native Linux flock')
    def test_product_native_boundary_uses_verified_binding_and_fixed_source_not_caller(self):
        self.handler.LOCK_FILE = str(self.root / 'access.lock')
        Path(self.handler.LOCK_FILE).touch()
        source = {'vrdSha256': self.handler.VRD_SHA256, 'ibBindings': ['/var/lib/1c/ib'],
                  'timeZonePath': '/usr/share/zoneinfo/Etc/UTC', 'journalDirectory': {'device': 17, 'inode': 23}}
        inspected = {'Id': self.handler.REFERENCE, 'Image': self.handler.REFERENCE_IMAGE,
                     'State': {'Running': True, 'Pid': 123},
                     'GraphDriver': {'Name': 'overlay2', 'Data': {'MergedDir': '/var/lib/docker/overlay2/reference/merged'}}}
        commands = []

        def check_output(argv, **kwargs):
            commands.append(argv)
            if argv[1] == 'inspect':
                return json.dumps([inspected]).encode()
            self.assertEqual(argv[:5], ['/usr/bin/docker', 'exec', '--user', '33:33', self.handler.REFERENCE])
            return json.dumps(source).encode()

        def run(argv, **kwargs):
            commands.append(argv)
            if argv[0] == '/usr/bin/systemctl':
                return subprocess.CompletedProcess(argv, 0, b'', b'')
            self.assertEqual(argv[:6], ['/usr/bin/docker', 'exec', '-i', '--user', '0:0', '--env'])
            identity = {'referenceId': self.handler.REFERENCE, 'image': self.handler.REFERENCE_IMAGE,
                        'vrd': self.handler.VRD_SHA256, 'ibPath': '/var/lib/1c/ib', 'journalDevice': 17, 'journalInode': 23}
            expected = 'target:' + hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            self.assertEqual(argv[6], 'ONE_C_HARNESS_CURRENT_TARGET_REF=' + expected)
            self.assertEqual(argv[8], 'ONE_C_HARNESS_CURRENT_SOURCE=/opt/one-c-harness/revision')
            self.assertEqual(argv[10], 'ONE_C_HARNESS_CURRENT_IB_PATH=/var/lib/1c/ib')
            self.assertEqual(argv[-1], '/opt/one-c-harness/revision')
            self.assertEqual(json.loads(kwargs['input']), envelope())
            self.assertLessEqual(kwargs['timeout'], 60)
            return subprocess.CompletedProcess(argv, 0, b'{"status":"ok"}', b'')

        with mock.patch.dict(os.environ, {'CURRENT_HARNESS_SOURCE': '/opt/one-c-harness/revision'}), \
                mock.patch.object(self.handler.subprocess, 'check_output', side_effect=check_output), \
                mock.patch.object(self.handler.subprocess, 'run', side_effect=run):
            self.assertEqual(self.handler._product_command(wire(envelope())), {'status': 'ok'})
            inspected['Image'] = 'foreign'
            commands.clear()
            with self.assertRaises(ValueError):
                self.handler._product_command(wire(envelope()))
            self.assertEqual(len(commands), 1)


if __name__ == '__main__':
    unittest.main()
