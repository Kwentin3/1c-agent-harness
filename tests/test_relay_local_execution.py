"""Local deployment boundary: real JSON/controller admission, no Docker or 1C."""
import base64
import contextlib
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    loader = importlib.machinery.SourceFileLoader(name, str(ROOT / relative))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


LOCAL = load('relay_local_execution', 'deployment/relay/one-c-harness-local')
JOURNAL = load('relay_current_journal', 'deployment/goal91/current-journal.py')
ENGINEERING = load('relay_engineering', 'deployment/goal91/engineering-shell.py')
CID = 'a' * 64


def envelope(operation='observation_info', arguments=None):
    return json.dumps({'schemaVersion': 1, 'operation': operation,
                       'arguments': {} if arguments is None else arguments}).encode()


class LocalExecutionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.config = {'schemaVersion': 1, 'source': str(self.root / 'source'),
                       'workspace': '/private/cache', 'captureBinding': str(self.root / 'binding.json'),
                       'journalController': str(self.root / 'journal.py'),
                       'engineeringController': str(self.root / 'engineering.py'),
                       'engineeringContainer': CID, 'codingSource': '/workspace/source/generation',
                       'codingRuntime': '/workspace/one-c-runtime.json',
                       'codingOracleRoot': '.local/oracles/accepted',
                       'journalRuntimeRoot': str(self.root / 'runtime')}
        for field in ('source', 'journalRuntimeRoot'):
            Path(self.config[field]).mkdir()
        for field in ('captureBinding', 'journalController', 'engineeringController'):
            Path(self.config[field]).write_bytes(b'# trusted fixture')
        for field in ('journalController', 'engineeringController'):
            self.config[field + 'Sha256'] = hashlib.sha256(Path(self.config[field]).read_bytes()).hexdigest()

    def test_closed_request_rejects_foreign_paths_extra_keys_duplicates_and_oversize(self):
        for raw in (b'{' , b'[]', envelope('shell'), envelope() + b'x',
                    b'{"schemaVersion":1,"schemaVersion":1,"operation":"open","arguments":{}}',
                    json.dumps({'schemaVersion': 1, 'operation': 'open', 'arguments': {}, 'source': '/evil'}).encode(),
                    b' ' * 16385):
            with self.subTest(raw=raw[:70]), self.assertRaises(ValueError):
                LOCAL.request(raw)

    def test_controller_uses_same_public_stdin_owner_and_scrubs_poisoned_environment(self):
        poison = {'CURRENT_HARNESS_SOURCE': '/evil', 'PYTHONPATH': '/evil',
                  'DOCKER_HOST': 'tcp://evil', 'SSH_ORIGINAL_COMMAND': 'shell'}
        with mock.patch.dict(os.environ, poison), mock.patch.object(LOCAL.subprocess, 'run',
                return_value=subprocess.CompletedProcess([], 0)) as execution:
            self.assertEqual(LOCAL.broker(envelope(), self.config), 0)
        call = execution.call_args
        self.assertEqual(call.args[0], ['/usr/bin/python3', '-I', '-B', self.config['journalController'], '--request-stdin'])
        self.assertEqual(call.kwargs['input'], envelope())
        for key in poison:
            self.assertNotIn(key, call.kwargs['env'])
        self.assertNotIn('ssh', ' '.join(call.args[0]))

    def test_stage_task_keeps_exact_utf8_stdin_outside_shell(self):
        raw = envelope('stage_task', {'productionPatch': 'Кириллица; $(id)\ncontent'})
        with mock.patch.object(LOCAL.runpy, 'run_path', return_value={'execute': mock.Mock(return_value=0)}) as loaded:
            self.assertEqual(LOCAL.broker(raw, self.config), 0)
            execute = loaded.return_value['execute']
            command, container = execute.call_args.args
            self.assertEqual(container, CID)
            self.assertEqual(execute.call_args.kwargs['input'], raw)
            self.assertIn('--request-stdin', command)
            self.assertNotIn('productionPatch', command)
            self.assertNotIn('$(id)', command)
            self.assertNotIn('ssh', command)
            self.assertNotIn('CURRENT_HARNESS_SOURCE', execute.call_args.kwargs['env'])

    def test_cached_selection_stays_local_and_names_only_local_acquisition(self):
        workspace = self.root / 'cache'
        workspace.mkdir(mode=0o700)
        self.config['workspace'] = str(workspace)
        info = types.SimpleNamespace(st_uid=42, st_mode=0o40700)
        with mock.patch.object(LOCAL, 'path', return_value=workspace), \
                mock.patch.object(Path, 'stat', return_value=info), \
                mock.patch.object(LOCAL.os, 'geteuid', return_value=42, create=True), \
                mock.patch.object(LOCAL.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as execute:
            LOCAL.execute('request', envelope('eventlog_page'), self.config)
        call = execute.call_args
        self.assertEqual(call.kwargs['cwd'], str(workspace))
        env = call.kwargs['env']
        self.assertEqual(env['ONE_C_HARNESS_EVENTLOG_CAPTURE_COMMAND'], str(LOCAL.BIN / 'one-c-harness-local-capture'))
        self.assertEqual(env['ONE_C_HARNESS_LOGGING_COMMAND'], str(LOCAL.BIN / 'one-c-harness-local-logging'))
        self.assertNotIn('SSH', ' '.join(env))
        self.assertNotIn('ssh', ' '.join(call.args[0]))

    def test_adapters_only_wrap_existing_contract_then_use_exact_no_argument_sudo(self):
        for role, value, operation in (
                ('capture', {'schemaVersion': 1, 'operation': 'export'}, 'eventlog_capture'),
                ('logging', {'schemaVersion': 1, 'journal': 'technological', 'action': 'status'}, 'logging_control')):
            with self.subTest(role=role), mock.patch.object(LOCAL.subprocess, 'run',
                    return_value=subprocess.CompletedProcess([], 0)) as execute:
                LOCAL.execute(role, json.dumps(value).encode(), self.config)
            self.assertEqual(execute.call_args.args[0], ['/usr/bin/sudo', '-n', LOCAL.CONTROLLER])
            result = json.loads(execute.call_args.kwargs['input'])
            self.assertEqual(result['operation'], operation)
            self.assertEqual(result['arguments'], {k: v for k, v in value.items() if role == 'capture' or k != 'schemaVersion'})
        with self.assertRaises(ValueError):
            LOCAL.execute('logging', b'{"schemaVersion":2}', self.config)

    def test_privileged_role_cannot_be_used_by_unprivileged_caller(self):
        with mock.patch.object(LOCAL.os, 'geteuid', return_value=1000, create=True), \
                mock.patch.object(LOCAL, 'broker') as broker:
            with self.assertRaisesRegex(ValueError, 'access_denied'):
                LOCAL.execute('controller', envelope(), self.config)
            broker.assert_not_called()

    def test_configuration_checks_actual_controller_bytes_not_only_expected_hash(self):
        config = self.root / 'config.json'
        config.write_text(json.dumps(self.config), encoding='utf8')
        original_path = LOCAL.path
        # Exercise real paths and files on Windows/unprivileged CI; separately
        # verify the root owner/mode predicate below with actual stat mutation.
        def fixture_path(value, **kwargs):
            return original_path(value, **{**kwargs, 'trusted': False})
        with mock.patch.object(LOCAL, 'CONFIG', config), mock.patch.object(LOCAL, 'path', side_effect=fixture_path):
            # Deployment/container locators are Linux paths; host fixture paths
            # are only the file-bearing fields above.
            LOCAL.configuration()
            Path(self.config['journalController']).write_bytes(b'# changed real artifact')
            with self.assertRaisesRegex(ValueError, 'configuration_invalid'):
                LOCAL.configuration()

    def test_trusted_path_refuses_foreign_owner_and_writable_file(self):
        for uid, mode in ((1000, 0o100444), (0, 0o100666)):
            with mock.patch.object(Path, 'stat', return_value=types.SimpleNamespace(st_uid=uid, st_mode=mode)):
                with self.assertRaisesRegex(ValueError, 'configuration_invalid'):
                    LOCAL.path(str(self.root / 'binding.json'), trusted=True)


class JournalPublicSeamTests(unittest.TestCase):
    def lock_patches(self):
        fake = types.SimpleNamespace(flock=mock.Mock(), LOCK_EX=2, LOCK_NB=4)
        return mock.patch.dict(sys.modules, {'fcntl': fake}), mock.patch.object(JOURNAL.os, 'open', return_value=73), mock.patch.object(JOURNAL.os, 'close')

    def test_local_stdin_and_ssh_envelope_use_identical_owner_output(self):
        binding = ({}, {}, '', {'journalDirectory': {'device': 1, 'inode': 2}, 'ibBindings': ['/var/lib/1c/ib']})
        reply = subprocess.CompletedProcess([], 0, stdout=b'{"status":"ok","operation":"observation_info"}', stderr=b'')
        for mode in ('stdin', 'ssh'):
            modules, opened, closed = self.lock_patches()
            with self.subTest(mode=mode), modules, opened, closed, \
                    mock.patch.object(JOURNAL, '_product_source', return_value='/opt/one-c-harness/accepted'), \
                    mock.patch.object(JOURNAL, '_binding', return_value=binding), \
                    mock.patch.object(JOURNAL.subprocess, 'run', return_value=reply) as execute, \
                    mock.patch.object(JOURNAL.sys, 'stdin', types.SimpleNamespace(buffer=io.BytesIO(envelope()))), \
                    mock.patch.dict(os.environ, {'SSH_ORIGINAL_COMMAND': 'current-harness-v1 ' + base64.b64encode(envelope()).decode()}), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                JOURNAL.main(['--request-stdin'] if mode == 'stdin' else [])
            self.assertEqual(json.loads(output.getvalue()), {'status': 'ok', 'operation': 'observation_info'})
            argv = execute.call_args.args[0]
            self.assertEqual(argv[:5], ['/usr/bin/docker', 'exec', '-i', '--user', '0:0'])
            self.assertIn(JOURNAL.REFERENCE, argv)
            self.assertIn('ONE_C_HARNESS_CURRENT_SOURCE=/opt/one-c-harness/accepted', argv)
            self.assertEqual(execute.call_args.kwargs['input'], envelope())

    def test_wrong_demo_binding_fails_at_existing_owner_before_backend(self):
        modules, opened, closed = self.lock_patches()
        inspected = {'Id': 'b' * 64, 'Image': JOURNAL.REFERENCE_IMAGE, 'State': {'Running': True}}
        with modules, opened, closed, mock.patch.object(JOURNAL, '_product_source', return_value='/opt/accepted'), \
                mock.patch.object(JOURNAL.subprocess, 'check_output', return_value=json.dumps([inspected])), \
                mock.patch.object(JOURNAL.subprocess, 'run') as backend:
            with self.assertRaisesRegex(ValueError, 'binding_unavailable'):
                JOURNAL.execute_product(envelope())
            backend.assert_not_called()

    def test_local_malformed_request_refuses_before_binding_or_docker(self):
        for raw in (b'{', envelope('shell'), b' ' * 16385):
            with self.subTest(raw=raw[:30]), mock.patch.object(JOURNAL, '_binding') as binding:
                with self.assertRaisesRegex(ValueError, 'invalid_request'):
                    JOURNAL.execute_product(raw)
                binding.assert_not_called()


if __name__ == '__main__':
    unittest.main()
