"""Replay retained real #69 evidence. No 1C or network side effects."""
import importlib.util
import json
from pathlib import Path
import hashlib
import base64
import re
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'experiments/issue69-transfer-basis'
spec = importlib.util.spec_from_file_location('issue69_oracle', ROOT / 'oracle.py')
assert spec and spec.loader
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)


class Issue69EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.receipt = json.loads((ROOT / 'receipt1.json').read_text())
        self.request = json.loads((ROOT / 'request.json').read_text())
        self.client = oracle.rows(ROOT / 'client-receipt.txt')
        self.server = oracle.rows(ROOT / 'server-receipt.txt')
        self.native = json.loads((ROOT / 'native-result.json').read_text())

    def test_real_client_server_replay(self):
        decision = oracle.validate(self.request, self.client, self.server)
        self.assertEqual(decision['status'], 'PASS')
        self.assertEqual(decision['businessPayload'], self.receipt['result']['business'])
        self.assertEqual(set(decision['businessPayload']['observations']), set(oracle.CASES))
        self.assertEqual(len(oracle.CASES), 13)

    def test_false_missing_stale_and_mismatched_evidence_fail(self):
        for case in oracle.CASES:
            wrong = dict(self.server, **{case: 'false'})
            with self.subTest(case=case), self.assertRaises(ValueError):
                oracle.validate(self.request, self.client, wrong)
        wrong = dict(self.server)
        wrong.pop('filledDraft')
        with self.assertRaises(ValueError):
            oracle.validate(self.request, self.client, wrong)
        with self.assertRaises(ValueError):
            oracle.validate(self.request, self.client, dict(self.server, run='stale'))
        with self.assertRaises(ValueError):
            oracle.validate(self.request, dict(self.client, token='not-server-witness'), self.server)
        with self.assertRaises(ValueError):
            oracle.validate(self.request, dict(self.client, error='client-error'), self.server)

    def test_bytes_bound_to_the_actual_shared_route(self):
        digest = lambda name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        self.assertEqual(digest('receipt1.json'), 'f0e00ea86ce16b3dff292f1852774e69f1bb1054aec5b1156e99a9533950eac6')
        normalized_request = json.dumps(self.request, sort_keys=True, separators=(',', ':')).encode('utf-8')
        self.assertEqual(hashlib.sha256(normalized_request).hexdigest(), self.receipt['request']['sha256'])
        self.assertEqual(self.request, self.receipt['request']['payload'])
        for patch in self.receipt['patches']:
            self.assertEqual(digest('exact-' + patch['role'] + '.patch'), patch['sha256'])
        self.assertEqual(digest('client-receipt.txt'), self.native['runtime']['receiptSha256'])
        self.assertEqual(digest('server-receipt.txt'), self.receipt['result']['server']['sha256'])
        for role in ('client', 'server'):
            self.assertEqual((ROOT / (role + '-receipt.txt')).read_bytes(),
                             base64.b64decode(self.receipt['result'][role]['base64'], validate=True))
        production_paths = set(re.findall(rb'^\+\+\+ b/(.+)$', (ROOT / 'exact-production.patch').read_bytes(), re.M))
        self.assertEqual(production_paths, {b'Documents/InventoryTransfer.xml',
                         b'Documents/InventoryTransfer/Forms/DocumentForm/Ext/Form.xml'})
        self.assertIn('String(New UUID)', (ROOT / 'exact-instrumentation.patch').read_bytes().decode('utf-8-sig'))

    def test_input_integrity_and_standard_cleanup(self):
        r = self.receipt
        self.assertEqual(r['canonical']['files'], 5099)
        self.assertEqual(r['input']['prepared'], r['input']['frozen'])
        self.assertEqual(r['input']['prepared'], r['input']['runner'])
        self.assertEqual(self.native['inputAfter']['sha256'], r['input']['frozen']['sha256'])
        self.assertEqual(self.native['status'], 'runtime_contract_completed')
        self.assertTrue(self.native['runtime']['completed'])
        cleanup = r['cleanup']
        self.assertEqual(cleanup['prepared'], 'discarded')
        self.assertEqual(cleanup['runner']['status'], 'completed')
        self.assertEqual(cleanup['runner']['manualCleanupActions'], 0)
        self.assertEqual(set(cleanup['runner']['completedRemovedPaths']), set(cleanup['runner']['configuredTargets']))
        after = json.loads((ROOT / 'post-run-check.json').read_text())
        self.assertEqual(after['processes'], [])
        self.assertEqual(after['preparedChildren'], [])


if __name__ == '__main__':
    unittest.main()
