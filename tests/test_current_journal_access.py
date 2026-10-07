"""Exercise the forced-command denial boundary without any platform invocation."""
import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'hermes-plugin/deployment/current-journal.py'
SPEC = importlib.util.spec_from_file_location('current_journal_access', SCRIPT)
ACCESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ACCESS)


class CurrentJournalAccessTests(unittest.TestCase):
    def reject_command(self, command):
        environment = {**os.environ, 'SSH_ORIGINAL_COMMAND': command}
        result = subprocess.run([sys.executable, '-I', '-B', str(SCRIPT)],
            env=environment, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, b'')
        denied = json.loads(result.stderr)
        self.assertEqual(denied['reasonCode'], 'invalid_request')
        self.assertEqual(denied['nativeInvocations'], 0)

    def reject_request(self, value):
        token = base64.b64encode(json.dumps(value).encode()).decode()
        self.reject_command('current-journal-v1 ' + token)

    def test_probe_has_no_source_argument(self):
        self.assertEqual(ACCESS.admit({'schemaVersion': 1, 'operation': 'probe'}),
            {'schemaVersion': 1, 'operation': 'probe'})
        self.reject_request({'schemaVersion': 1, 'operation': 'probe',
            'source': '/other/1Cv8Log'})

    def test_bounded_export_admission(self):
        request = {'schemaVersion': 1, 'operation': 'export',
            'start': '2026-10-07T09:00:00', 'end': '2026-10-07T09:15:00',
            'format': 'json', 'followMilliseconds': 0}
        self.assertEqual(ACCESS.admit(request), request)

    def test_arbitrary_shell_and_extra_argv_are_rejected(self):
        for command in ['', 'bash', 'docker ps', 'current-journal-v1 e30=; id',
            'current-journal-v1 e30= extra', 'current-journal-v1 e30=\nid']:
            with self.subTest(command=command):
                self.reject_command(command)

    def test_malformed_json_and_token_are_rejected(self):
        for command in ['current-journal-v1 @@@', 'current-journal-v1 a',
            'current-journal-v1 ' + base64.b64encode(b'{').decode()]:
            with self.subTest(command=command):
                self.reject_command(command)

    def test_unknown_operations_and_schema_are_rejected(self):
        for value in [{'schemaVersion': 1, 'operation': 'shell'},
            {'schemaVersion': True, 'operation': 'probe'},
            {'schemaVersion': 2, 'operation': 'probe'}, ['probe'], None]:
            with self.subTest(value=value):
                self.reject_request(value)

    def test_foreign_source_output_and_runtime_are_rejected(self):
        request = {'schemaVersion': 1, 'operation': 'export',
            'start': '2026-10-07T09:00:00', 'end': '2026-10-07T09:15:00',
            'format': 'json', 'followMilliseconds': 0}
        for key, value in [('source', '/other/1Cv8Log'), ('out', '/var/lib/1c/ib/1Cv8.1CD'),
            ('binary', '/bin/sh'), ('argv', ['--remote=http://other'])]:
            with self.subTest(key=key):
                self.reject_request({**request, key: value})

    def test_invalid_bounds_are_rejected(self):
        request = {'schemaVersion': 1, 'operation': 'export',
            'start': '2026-10-07T09:00:00', 'end': '2026-10-07T09:15:00',
            'format': 'json', 'followMilliseconds': 0}
        for overrides in [{'end': '2026-10-09T09:00:00'}, {'end': '2026-10-07T08:59:59'},
            {'end': '2026-02-30T09:00:00'}, {'format': 'json; id'},
            {'start': '$(id)'}, {'followMilliseconds': True},
            {'followMilliseconds': -1}, {'followMilliseconds': 1001}]:
            with self.subTest(overrides=overrides):
                self.reject_request({**request, **overrides})


if __name__ == '__main__':
    unittest.main()
