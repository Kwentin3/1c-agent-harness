from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest import mock
PATH = Path(__file__).resolve().parents[1] / 'hermes-plugin/deployment/current-journal-client.py'

class CurrentJournalClientTests(unittest.TestCase):

    def test_closed_request_becomes_only_encoded_fixed_ssh_command(self):
        self.assertTrue(PATH.is_file(), 'fixed current-journal client is missing')
        spec = importlib.util.spec_from_file_location('journal_client', PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        request = {'schemaVersion': 1, 'operation': 'export', 'start': '2026-10-07T00:00:00', 'end': '2026-10-07T01:00:00', 'format': 'json', 'followMilliseconds': 0}
        import tempfile, base64
        with tempfile.TemporaryDirectory() as raw:
            config = Path(raw) / 'config'
            config.write_text('# admitted fixture')
            with mock.patch.dict(os.environ, {'ONE_C_HARNESS_CURRENT_JOURNAL_SSH_CONFIG': str(config)}):
                argv = module.command(request)
                self.assertEqual(argv[:5], ['/usr/bin/ssh', '-F', str(config), '-T', 'current-journal'])
                self.assertEqual(json.loads(base64.b64decode(argv[-1].split(' ')[1])), request)
                for key in ['source', 'output', 'command']:
                    with self.assertRaises(ValueError):
                        module.command({**request, key: 'unadmitted'})
if __name__ == '__main__':
    unittest.main()
