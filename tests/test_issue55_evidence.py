"""Replay exact retained issue55 bytes; reject concrete false-PASS mutations without 1C."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'experiments/issue55-supplier-document-number'


class SupplierDocumentReceiptTests(unittest.TestCase):
    def invoke(self, replacements=None):
        receipt = json.loads((PACKAGE / 'receipt.json').read_text())
        server = base64.b64decode(receipt['result']['server']['base64'])
        if replacements:
            text = server.decode('utf-8-sig')
            for old, new in replacements.items():
                self.assertIn(old, text)
                text = text.replace(old, new)
            server = text.encode('utf-8')
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder / 'client.txt').write_bytes(base64.b64decode(receipt['result']['client']['base64']))
            (folder / 'server.txt').write_bytes(server)
            return subprocess.run([sys.executable, str(PACKAGE / 'oracle.py'),
                '--request', str(PACKAGE / 'request.json'),
                '--client-receipt', str(folder / 'client.txt'),
                '--server-receipt', str(folder / 'server.txt')], capture_output=True, text=True)

    def test_retained_packet_passes_and_hashes_bind_exact_artifacts(self):
        receipt = json.loads((PACKAGE / 'receipt.json').read_text())
        for role in ('client', 'server'):
            data = base64.b64decode(receipt['result'][role]['base64'])
            self.assertEqual(hashlib.sha256(data).hexdigest(), receipt['result'][role]['sha256'])
            self.assertEqual(len(data), receipt['result'][role]['bytes'])
        for patch in receipt['patches']:
            self.assertEqual(hashlib.sha256((PACKAGE / ('exact-' + patch['role'] + '.patch')).read_bytes()).hexdigest(), patch['sha256'])
        request = json.loads((PACKAGE / 'request.json').read_text())
        self.assertEqual(request, receipt['request']['payload'])
        canonical = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), receipt['request']['sha256'])
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'PASS')

    def test_unknown_negative_case_boolean_is_not_false(self):
        result = self.invoke({'missing_number###No': 'missing_number###garbage'})
        self.assertNotEqual(result.returncode, 0)

    def test_unknown_concurrent_loser_boolean_is_not_false(self):
        result = self.invoke({'concurrent.b.succeeded###No': 'concurrent.b.succeeded###garbage'})
        self.assertNotEqual(result.returncode, 0)

    def test_winner_and_loser_movements_cannot_be_swapped(self):
        replacements = {}
        for index in range(1, 5):
            replacements[f'concurrent.a.movement{index}###1'] = f'concurrent.a.movement{index}###0'
            replacements[f'concurrent.b.movement{index}###0'] = f'concurrent.b.movement{index}###1'
        self.assertNotEqual(self.invoke(replacements).returncode, 0)

    def test_concurrent_winner_must_have_each_declared_register_movement(self):
        self.assertNotEqual(self.invoke({'concurrent.a.movement2###1': 'concurrent.a.movement2###0'}).returncode, 0)


if __name__ == '__main__':
    unittest.main()
