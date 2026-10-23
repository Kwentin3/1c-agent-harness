"""Disposable root-owned install files; no real system paths or sudo invocation."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
INSTALL = None
if os.name == 'posix':
    spec = importlib.util.spec_from_file_location('relay_install_local', ROOT / 'deployment/relay/install-local.py')
    INSTALL = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(INSTALL)


@unittest.skipUnless(os.name == 'posix' and getattr(os, 'geteuid', lambda: -1)() == 0,
                     'disposable actual root ownership and chown on Linux')
class LocalInstallTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.root.chmod(0o700)
        self.config = self.root / 'etc/relay-local.json'
        self.sudoers = self.root / 'sudoers/relay-local'
        self.controller = self.root / 'libexec/controller'
        self.executables = [self.root / 'bin' / name for name in ('local', 'capture', 'logging', 'exporter')] + [self.controller]
        for key, value in (('CONFIG', self.config), ('SUDOERS', self.sudoers),
                           ('CONTROLLER', self.controller), ('EXECUTABLES', self.executables)):
            patch = mock.patch.object(INSTALL, key, value)
            patch.start()
            self.addCleanup(patch.stop)

    def receipt(self):
        desired = {str(path): INSTALL.image(b'#!/usr/bin/python3\n# same bytes\n', 0o555) for path in self.executables}
        desired[str(self.config)] = INSTALL.image(b'{}\n', 0o444)
        desired[str(self.sudoers)] = INSTALL.image(b'account ALL=(root) NOPASSWD: /fixed/controller ""\n', 0o440)
        return {'schemaVersion': 1, 'status': 'PREVIEW', 'sourceCommit': 'a' * 40,
                'adapterSha256': INSTALL.sha(b'candidate'), 'relayUser': 'account',
                'cache': {'path': str(self.root / 'state/cache'), 'uid': 10001, 'gid': 10001, 'created': True},
                'entries': [{'path': path, 'before': INSTALL.state(Path(path)), 'after': item} for path, item in desired.items()],
                'createdDirectories': []}

    def test_apply_readback_and_inverse_rollback_preserve_cache_results(self):
        self.config.parent.mkdir()
        self.config.write_bytes(b'previous config')
        self.config.chmod(0o440)
        before = INSTALL.state(self.config)
        receipt = self.receipt()
        path = self.root / 'receipt.json'
        INSTALL.apply(receipt, path)
        self.assertEqual(receipt['status'], 'APPLIED')
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        for entry in receipt['entries']:
            self.assertEqual(INSTALL.state(Path(entry['path'])), entry['after'])
        cache = Path(receipt['cache']['path'])
        self.assertEqual((cache.stat().st_uid, cache.stat().st_gid, stat.S_IMODE(cache.stat().st_mode)), (10001, 10001, 0o700))
        retained = cache / 'retained-selection.json'
        retained.write_bytes(b'protected result')
        preview = INSTALL.rollback(receipt)
        self.assertEqual(preview['status'], 'ROLLBACK_PREVIEW')
        self.assertEqual(INSTALL.state(self.config), receipt['entries'][-2]['after'])
        result = INSTALL.rollback(receipt, True)
        self.assertEqual(result['status'], 'ROLLED_BACK')
        self.assertEqual(INSTALL.state(self.config), before)
        self.assertFalse(self.controller.exists())
        self.assertEqual(retained.read_bytes(), b'protected result')

    def test_rollback_refuses_actual_foreign_edit_and_leaves_everything(self):
        receipt = self.receipt()
        INSTALL.apply(receipt, self.root / 'receipt.json')
        self.controller.chmod(0o644)
        self.controller.write_bytes(b'foreign edit')
        before = self.config.read_bytes()
        with self.assertRaisesRegex(ValueError, 'target changed'):
            INSTALL.rollback(receipt, True)
        self.assertEqual(self.controller.read_bytes(), b'foreign edit')
        self.assertEqual(self.config.read_bytes(), before)
        self.assertTrue(self.sudoers.exists())

    def test_partial_apply_receipt_can_restore_only_task_changed_files(self):
        receipt = self.receipt()
        first = receipt['entries'][0]
        Path(first['path']).parent.mkdir()
        INSTALL.write(Path(first['path']), first['after'])
        self.assertEqual(INSTALL.rollback(receipt, True)['status'], 'ROLLED_BACK')
        self.assertFalse(Path(first['path']).exists())

    def test_preview_checks_locked_real_bytes_and_installed_config_without_writes(self):
        bundle = self.root / 'bundle'
        (bundle / 'deployment/relay').mkdir(parents=True)
        script = bundle / INSTALL.SCRIPT
        script.write_bytes((ROOT / INSTALL.SCRIPT).read_bytes())
        source = self.root / 'source'
        (source / 'one_c_harness').mkdir(parents=True)
        artifact = 'sha256:' + 'c' * 64
        (source / 'one_c_harness/release.json').write_text(json.dumps({'artifactId': artifact}))
        files = {INSTALL.SCRIPT: INSTALL.sha(script.read_bytes())}
        config = {'schemaVersion': 1, 'source': str(source), 'workspace': str(self.root / 'cache'),
                  'captureBinding': str(self.root / 'binding.json'), 'journalController': str(self.root / 'journal.py'),
                  'engineeringController': str(self.root / 'engineering.py'), 'engineeringContainer': 'b' * 64,
                  'codingSource': '/workspace/fixed/source', 'codingRuntime': '/workspace/runtime.json',
                  'codingOracleRoot': '.local/accepted-oracle', 'journalRuntimeRoot': str(self.root / 'runtime')}
        Path(config['journalRuntimeRoot']).mkdir()
        for key, relative in (('journalController', 'deployment/goal91/current-journal.py'),
                              ('engineeringController', 'deployment/goal91/engineering-shell.py')):
            Path(config[key]).write_bytes(b'# installed owner')
            Path(config[key]).chmod(0o555)
            config[key + 'Sha256'] = INSTALL.sha(Path(config[key]).read_bytes())
            files[relative] = config[key + 'Sha256']
        Path(config['captureBinding']).write_bytes(b'{}')
        Path(config['captureBinding']).chmod(0o444)
        candidate = self.root / 'candidate.json'
        candidate.write_text(json.dumps(config))
        candidate.chmod(0o444)
        lock = self.root / 'lock.json'
        lock.write_text(json.dumps({'repository': 'https://github.com/Kwentin3/1c-agent-harness.git',
                                   'commit': 'a' * 40, 'artifact_id': artifact, 'files': files}))
        with mock.patch.object(INSTALL.pwd, 'getpwnam', return_value=types.SimpleNamespace(pw_uid=10001, pw_gid=10001)), \
                mock.patch.object(INSTALL, 'validate_sudoers') as check:
            receipt = INSTALL.plan(bundle, lock, candidate, 'relayaccount')
            self.assertEqual(receipt['status'], 'PREVIEW')
            rule = check.call_args.args[0].decode()
            self.assertEqual(rule, 'relayaccount ALL=(root) NOPASSWD: NOSETENV: ' + str(self.controller) + ' ""\n')
            self.assertFalse(self.config.exists())
            self.assertFalse(Path(config['workspace']).exists())
            script.write_bytes(script.read_bytes() + b'\n# real mutation')
            with self.assertRaisesRegex(ValueError, 'adapter differs'):
                INSTALL.plan(bundle, lock, candidate, 'relayaccount')


if __name__ == '__main__':
    unittest.main()
