"""Actual fixed-config loading and TechLog files; no native 1C or UID changes."""
import contextlib
import io
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest import mock

from one_c_harness import current_logging as backend
from one_c_harness import techlog_config

TARGET = 'target:' + 'a' * 64


def request(action='status', journal='technological', **fields):
    return json.dumps({'schemaVersion': 1, 'operation': 'logging_control',
                       'arguments': {'action': action, 'journal': journal, **fields}}).encode()


class CurrentLoggingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.source = self.root / 'source'
        (self.source / 'deployment/goal91').mkdir(parents=True)
        (self.source / 'one_c_harness').mkdir()
        (self.source / 'one_c_harness/logging.epf').write_bytes(b'not executed')
        self.ib = self.root / 'infobase'
        self.ib.mkdir()
        self.config = {'schemaVersion': 1, 'settingsEpf': 'one_c_harness/logging.epf', 'timeZone': 'UTC'}
        for key in backend._PATHS:
            path = self.root / key
            if key == 'techlogConfig':
                path.write_bytes(b'<config><dump create="false"/></config>')
            elif key == 'runtimeProfile':
                path.write_text('{}')
            else:
                path.mkdir(mode=0o700)
            self.config[key] = str(path)
        self.config_path = self.source / 'deployment/goal91/current-logging.json'
        self.config_path.write_text(json.dumps(self.config), encoding='utf8')
        self.raw_path = backend._path
        self.addCleanup(mock.patch.stopall)
        mock.patch.dict(os.environ, {'ONE_C_HARNESS_CURRENT_SOURCE': str(self.source),
            'ONE_C_HARNESS_CURRENT_TARGET_REF': TARGET, 'ONE_C_HARNESS_CURRENT_IB_PATH': str(self.ib)}).start()
        # CI runs an unprivileged disposable test user. Keep real path/file checks;
        # privilege metadata validation is covered separately, never chmod/chown fixtures.
        if os.name == 'posix' and os.geteuid() != 0:
            real_path = backend._path
            mock.patch.object(backend, '_path', side_effect=lambda value, **kwargs:
                              real_path(value, **{**kwargs, 'trusted': False})).start()

    def test_wrong_target_is_blocked_before_either_mutator_or_uid_drop(self):
        with mock.patch.object(backend, '_techlog') as tech, \
                mock.patch.object(backend.registration_logging, 'control') as registration, \
                mock.patch.object(backend, '_drop_privileges') as drop:
            for journal in ('registration', 'technological'):
                with self.assertRaisesRegex(ValueError, '^target_mismatch$'):
                    backend.execute(request('start', journal, profile='errors', targetRef='target:' + 'b' * 64))
            tech.assert_not_called()
            registration.assert_not_called()
            drop.assert_not_called()

    def test_real_techlog_start_is_configured_not_observed_and_only_own_ref_stops(self):
        path = Path(self.config['techlogConfig'])
        original = path.read_bytes()
        started = backend.execute(request('start', profile='errors', targetRef=TARGET))
        self.assertEqual((started['status'], started['state'], started['platformState']), ('ok', 'configured', 'unknown'))
        self.assertEqual(started['configurationState'], 'applied')
        capture = started['captureRef']
        self.assertRegex(capture, r'^capture:[0-9a-f]{32}$')
        applied = path.read_bytes()
        repeated = backend.execute(request('start', profile='errors', targetRef=TARGET))
        self.assertEqual(repeated['captureRef'], capture)
        self.assertEqual(backend.execute(request())['captureRef'], capture)
        with self.assertRaisesRegex(ValueError, '^capture_not_found$'):
            backend.execute(request('stop', targetRef=TARGET, captureRef='capture:' + 'f' * 32))
        self.assertEqual(path.read_bytes(), applied)
        stopped = backend.execute(request('stop', targetRef=TARGET, captureRef=capture))
        self.assertEqual((stopped['state'], stopped['configurationState'], stopped['captureRef']), ('inactive', 'restored', capture))
        self.assertEqual(path.read_bytes(), original)
        with self.assertRaisesRegex(ValueError, '^capture_not_found$'):
            backend.execute(request('stop', targetRef=TARGET, captureRef=capture))

    def test_config_is_fixed_source_owned_not_argv_or_request_paths(self):
        for raw in (request(source='/evil'), json.dumps({'schemaVersion': 1, 'operation': 'shell', 'arguments': {}}).encode(),
                    b'{"schemaVersion":1,"schemaVersion":1,"operation":"observe","arguments":{}}'):
            with self.assertRaises(ValueError):
                backend.execute(raw)
        self.config['settingsEpf'] = '../foreign.epf'
        self.config_path.write_text(json.dumps(self.config))
        with self.assertRaises(ValueError):
            backend.execute(request())

    def test_missing_precreated_directory_does_not_create_or_modify_anything(self):
        Path(self.config['techlogState']).rmdir()
        before = Path(self.config['techlogConfig']).read_bytes()
        with self.assertRaises(OSError):
            backend.execute(request('start', profile='errors', targetRef=TARGET))
        self.assertFalse(Path(self.config['techlogState']).exists())
        self.assertEqual(Path(self.config['techlogConfig']).read_bytes(), before)

    def test_registration_drops_uid_before_existing_control_and_uses_fixed_settings(self):
        paths = {'runtimeProfile': self.root / 'profile', 'settingsEpf': self.source / 'one_c_harness/logging.epf',
                 'workDirectory': Path(self.config['workDirectory'])}
        for name in ('platform', 'xvfb', 'fontconfig'):
            path = self.root / name
            path.write_bytes(b'not executed')
            path.chmod(0o700)
        paths['runtimeProfile'].write_text(json.dumps({name: str(self.root / name) for name in ('platform', 'xvfb', 'fontconfig')} | {'libs': '/fixed/libs'}))
        self.config['runtimeProfile'] = str(paths['runtimeProfile'])
        self.config_path.write_text(json.dumps(self.config))
        calls = []
        def control(action, settings, state, target, **kwargs):
            calls.append('control')
            self.assertEqual(calls, ['drop', 'control'])
            self.assertEqual((settings.infobase, settings.epf, state, target),
                             (self.ib, paths['settingsEpf'], Path(self.config['registrationState']), TARGET))
            return {'status': 'ok', 'journal': 'registration'}
        with mock.patch.object(backend, '_drop_privileges', side_effect=lambda: calls.append('drop')), \
                mock.patch.object(backend.registration_logging, 'control', side_effect=control):
            self.assertEqual(backend.execute(request(journal='registration'))['status'], 'ok')

    def test_uid_transition_clears_groups_before_fixed_gid_and_uid(self):
        calls = []
        with mock.patch.object(backend.os, 'name', 'posix'), \
                mock.patch.object(backend.os, 'geteuid', side_effect=[0, 0, 33], create=True), \
                mock.patch.object(backend.os, 'getegid', return_value=33, create=True), \
                mock.patch.object(backend.os, 'setgroups', side_effect=lambda v: calls.append(('groups', v)), create=True), \
                mock.patch.object(backend.os, 'setgid', side_effect=lambda v: calls.append(('gid', v)), create=True), \
                mock.patch.object(backend.os, 'setuid', side_effect=lambda v: calls.append(('uid', v)), create=True):
            backend._drop_privileges()
        self.assertEqual(calls, [('groups', []), ('gid', 33), ('uid', 33)])

    @unittest.skipUnless(os.name == 'posix', 'production companion imports Linux file locking')
    def test_three_reads_reuse_actual_companion_and_fixed_source_with_uid_drop(self):
        logs = Path(self.config['techlogDirectory']) / 'server'
        logs.mkdir()
        (logs / '26102210.log').write_text('00:00.000001-1,EXCP,1,Exception=TestError,Descr="safe diagnostic",SrcName=core\n')
        before = Path(self.config['techlogConfig']).read_bytes()
        def call(operation, arguments):
            return backend.execute(json.dumps({'schemaVersion': 1, 'operation': operation, 'arguments': arguments}).encode())
        with mock.patch.object(backend, '_drop_privileges') as drop:
            info = call('observation_info', {})
            self.assertEqual(info['observedEvents'], ['EXCP'])
            selected = call('observe', {'start': '2026-10-22T10:00:00', 'end': '2026-10-22T10:01:00',
                                        'events': ['EXCP'], 'limit': 20})
            self.assertEqual(selected['summary']['recordCount'], 1)
            expanded = call('expand_observation', {'observationRef': selected['observationRef'], 'offset': 0, 'limit': 20})
            self.assertEqual(expanded['total'], 1)
            self.assertEqual(expanded['groups'][0]['ref'], selected['groups'][0]['ref'])
            self.assertEqual(drop.call_count, 3)
        self.assertEqual(Path(self.config['techlogConfig']).read_bytes(), before)

    @unittest.skipUnless(os.name == 'posix', 'trusted native source mode and owner')
    def test_writable_or_nonroot_fixed_config_is_refused(self):
        self.config_path.chmod(0o666)
        with self.assertRaisesRegex(ValueError, '^configuration_invalid$'):
            self.raw_path(str(self.config_path), trusted=True)

    def test_main_rejects_argv_paths_and_outputs_bounded_safe_failure(self):
        for argv, effect in ((['backend', '--source', '/private/path'], None),
                             (['backend'], ValueError('/private/path password=secret')),
                             (['backend'], TimeoutError('source_timeout')),
                             (['backend'], {'status': 'ok', 'raw': 'x' * 16384})):
            with mock.patch.object(sys, 'argv', argv), \
                    mock.patch.object(sys, 'stdin', io.TextIOWrapper(io.BytesIO(request()))), \
                    mock.patch.object(backend, 'execute', side_effect=effect if isinstance(effect, Exception) else None,
                                      return_value=effect), contextlib.redirect_stdout(io.StringIO()) as output:
                backend.main()
            raw = output.getvalue()
            self.assertLessEqual(len(raw.encode()), 16384)
            self.assertEqual(json.loads(raw)['status'], 'blocked')
            self.assertNotIn('/private', raw)
            self.assertNotIn('secret', raw)
            if len(argv) == 1:
                public = backend.logging_control._project(raw.encode(), {'action': 'status', 'journal': 'technological'})
                self.assertEqual(public['state'], 'unknown')
                self.assertFalse(any(public['capabilities'].values()))


if __name__ == '__main__':
    unittest.main()
