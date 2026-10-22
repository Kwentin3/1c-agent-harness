"""Real ledger/lock regression; only Docker/native process boundaries are replaced."""
import ast
import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock


SOURCE = Path(__file__).resolve().parents[1] / 'deployment/goal91/current-journal.py'
REQUEST = {'schemaVersion': 1, 'operation': 'export', 'start': '2026-10-21T00:00:00',
           'end': '2026-10-21T01:00:00', 'format': 'json', 'followMilliseconds': 0}


@unittest.skipUnless(os.name == 'posix', 'real Linux flock and file ownership semantics')
class CurrentJournalBudgetTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('current_journal_budget', SOURCE)
        self.handler = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.handler)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.contract = {'limits': {'help': 3, 'export': 16, 'sessionCycles': 2,
                                    'callSeconds': 30, 'nativeTotalSeconds': 900}}
        self.contract_bytes = json.dumps(self.contract).encode()
        (self.root / 'contract.json').write_bytes(self.contract_bytes)
        self.pin = hashlib.sha256(self.contract_bytes).hexdigest()
        self.handler.CONTRACT_SHA256 = self.pin
        self.ledger = self.root / 'ledger.json'
        self.write_rows([])
        (self.root / 'issue94-ledger.lock').touch(mode=0o600)
        self.commands = []
        self.accounting_input_bytes = []
        self.launched_rows = []
        self.result = {'schemaVersion': 1, 'status': 'EXPORTED', 'nativeInvocations': 1,
                       'exitCode': 0, 'durationSeconds': 0.25, 'outputBytes': 2,
                       'outputSha256': hashlib.sha256(b'[]').hexdigest(), 'outputBase64': 'W10=',
                       'sourceDirectory': {'device': 7, 'inode': 8}}
        self.boundary = mock.patch.object(self.handler.subprocess, 'run', side_effect=self.docker_run)
        self.boundary.start()
        self.addCleanup(self.boundary.stop)

    def write_rows(self, rows):
        self.ledger.write_text(json.dumps(rows), encoding='utf8')
        self.ledger.chmod(0o600)

    def rows(self):
        return json.loads(self.ledger.read_bytes())

    def owner(self):
        namespace = {'__name__': 'accounting_fixture'}
        exec(compile(self.handler.ACCOUNTING, str(SOURCE) + ':ACCOUNTING', 'exec'), namespace)
        namespace['ROOT'] = self.root
        return namespace['transaction']

    def docker_run(self, args, **kwargs):
        if args[:3] == ['/usr/bin/docker', 'exec', '-i']:
            self.assertEqual(args[3:6], ['--user', '10001:10001', self.handler.ACCOUNTING_EXECUTOR])
            self.assertEqual(args[-1], self.handler.ACCOUNTING)
            self.assertEqual(kwargs['timeout'], 5)
            command = json.loads(kwargs['input'])
            self.commands.append(command)
            self.accounting_input_bytes.append(len(kwargs['input']))
            # Execute the actual entrypoint too: its bounded stdin read must not be bypassed.
            entry = ast.get_source_segment(self.handler.ACCOUNTING, ast.parse(self.handler.ACCOUNTING).body[-1])
            namespace = {'__name__': '__main__', 'transaction': self.owner(), 'json': json, 'sys': sys}
            output = io.StringIO()
            code = 0
            with mock.patch.object(sys, 'stdin', io.TextIOWrapper(io.BytesIO(kwargs['input']))), contextlib.redirect_stdout(output):
                try:
                    exec(compile(entry, str(SOURCE) + ':ACCOUNTING_ENTRY', 'exec'), namespace)
                except SystemExit as error:
                    code = error.code
            return subprocess.CompletedProcess(args, code, output.getvalue().encode(), b'')
        # Existing source service check and owned Docker cleanup only.
        self.assertTrue(args[:2] in (['/usr/bin/systemctl', 'is-active'], ['/usr/bin/docker', 'rm']))
        return subprocess.CompletedProcess(args, 0, b'', b'')

    def invoke(self, request=REQUEST):
        command = 'current-journal-v1 ' + base64.b64encode(json.dumps(request).encode()).decode()
        output = io.StringIO()
        with mock.patch.dict(os.environ, {'SSH_ORIGINAL_COMMAND': command}), contextlib.redirect_stdout(output):
            self.handler.main()
        return json.loads(output.getvalue())

    def invoke_envelope(self):
        command = 'current-journal-v1 ' + base64.b64encode(json.dumps(REQUEST).encode()).decode()
        entry = ast.get_source_segment(SOURCE.read_text(), ast.parse(SOURCE.read_text()).body[-1])
        output, errors = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {'SSH_ORIGINAL_COMMAND': command}), \
                mock.patch.object(self.handler, '__name__', '__main__'), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            with self.assertRaises(SystemExit) as exit:
                exec(compile(entry, str(SOURCE), 'exec'), self.handler.__dict__)
        self.assertEqual(exit.exception.code, 2)
        self.assertEqual(output.getvalue(), '')
        return json.loads(errors.getvalue())

    def capture(self, value):
        rows = self.rows()
        self.launched_rows.append(rows)
        self.assertTrue(rows, 'native worker launched without a durable budget reservation')
        self.assertEqual(rows[-1]['status'], 'STARTED')
        self.assertEqual(rows[-1]['nativeBudgetReservedSeconds'], 30)
        self.assertEqual(rows[-1]['request'], value)
        return dict(self.result)

    def invoke_native_boundary(self, *, envelope=False):
        self.handler.RUNTIME_HOST = '/trusted/runtime'
        access = self.root / 'access.lock'
        access.touch(mode=0o600)
        self.handler.LOCK_FILE = str(access)
        original_open = os.open
        descriptors = []

        def tracked_open(path, *args, **kwargs):
            fd = original_open(path, *args, **kwargs)
            if str(path) == str(access):
                descriptors.append(fd)
            return fd

        def check_output(args, **kwargs):
            if args[1] == 'inspect':
                return json.dumps([{'Id': self.handler.REFERENCE, 'Image': self.handler.REFERENCE_IMAGE,
                                    'State': {'Running': True, 'Pid': 42, 'StartedAt': 'accepted'},
                                    'GraphDriver': {'Name': 'overlay2', 'Data': {'MergedDir': '/merged'}}}]).encode()
            return json.dumps({'vrdSha256': self.handler.VRD_SHA256, 'ibBindings': ['/var/lib/1c/ib'],
                               'timeZonePath': '/usr/share/zoneinfo/Etc/UTC',
                               'journalDirectory': {'device': 7, 'inode': 8}}).encode()

        test = self

        class Worker:
            returncode = 0

            def communicate(self, payload, timeout):
                test.capture(json.loads(payload))
                test.assertEqual(timeout, 40)
                return json.dumps(test.result).encode(), b''

            def poll(self):
                return 0

        try:
            with mock.patch.object(os, 'open', side_effect=tracked_open), \
                    mock.patch.object(self.handler.subprocess, 'check_output', side_effect=check_output), \
                    mock.patch.object(self.handler.subprocess, 'Popen', return_value=Worker()):
                result = self.invoke_envelope() if envelope else self.invoke()
        finally:
            for fd in descriptors:
                os.close(fd)
        return result

    def test_main_reserves_before_native_launch_and_preserves_receipt(self):
        """Same main/native boundary works on unguarded PR98 too: its ledger is empty."""
        result = self.invoke_native_boundary()
        self.assertEqual(result['sourceBinding']['referenceId'], self.handler.REFERENCE)
        self.assertEqual({k: result[k] for k in self.result}, self.result)
        row = self.rows()[-1]
        self.assertEqual(row['status'], 'COMPLETED')
        self.assertEqual(row['durationSeconds'], 0.25)
        self.assertEqual(row['receiptSha256'], hashlib.sha256((json.dumps(result, sort_keys=True) + '\n').encode()).hexdigest())
        self.assertEqual([c['action'] for c in self.commands], ['reserve', 'settle'])
        self.assertEqual(self.ledger.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.ledger.stat().st_uid, os.getuid())

    def test_large_native_receipt_preserved_with_bounded_accounting_summary(self):
        payload = json.dumps({'Date': '2026-10-21T00:00:00', 'Event': 'Fixture',
                              'Comment': 'safe fixture ' * 11000}).encode()
        self.assertGreaterEqual(len(payload), 130666)
        self.result.update(outputBytes=len(payload), outputSha256=hashlib.sha256(payload).hexdigest(),
                           outputBase64=base64.b64encode(payload).decode(),
                           sourceBefore=[{'name': '1Cv8.lgf', 'bytes': 2}],
                           sourceAfter=[{'name': '1Cv8.lgf', 'bytes': 2}],
                           stdout={'bytes': 0, 'payloadBase64': '', 'truncated': False},
                           stderr={'bytes': 0, 'payloadBase64': '', 'truncated': False})
        self.test_main_reserves_before_native_launch_and_preserves_receipt()
        self.assertLess(max(self.accounting_input_bytes), 16384)
        summary = self.commands[-1]['result']
        self.assertEqual(set(summary), {'status', 'nativeInvocations', 'exitCode', 'durationSeconds',
                                        'outputBytes', 'outputSha256'})
        self.assertNotIn('outputBase64', json.dumps(self.rows()))
        self.assertNotIn('sourceBefore', json.dumps(self.rows()))

    def test_failed_native_and_unknown_timeout_spend_slot_and_seconds(self):
        for failure in ('native', 'timeout'):
            with self.subTest(failure=failure):
                self.write_rows([])
                if failure == 'native':
                    self.result.update(status='NATIVE_FAILED', exitCode=124, durationSeconds=30.01)
                    capture = self.capture
                else:
                    def capture(value):
                        self.capture(value)
                        raise subprocess.TimeoutExpired(['/PRIVATE/DO_NOT_LEAK'], 40)
                with mock.patch.object(self.handler, '_capture', side_effect=capture):
                    if failure == 'timeout':
                        with self.assertRaises(subprocess.TimeoutExpired):
                            self.invoke()
                    else:
                        self.assertEqual(self.invoke()['status'], 'NATIVE_FAILED')
                row = self.rows()[-1]
                self.assertEqual(row['status'], 'FAILED_NO_RETRY')
                self.assertEqual(row['nativeBudgetReservedSeconds'], 0)
                self.assertEqual(row['durationSeconds'], 30.01 if failure == 'native' else 30)
                self.assertNotIn('PRIVATE', json.dumps(row))

    def test_probe_does_not_read_or_debit_budget(self):
        self.ledger.unlink()
        with mock.patch.object(self.handler, '_capture', return_value={'status': 'ACCESS_PROBE_PASS'}) as capture:
            self.assertEqual(self.invoke({'schemaVersion': 1, 'operation': 'probe'})['status'], 'ACCESS_PROBE_PASS')
        capture.assert_called_once()
        self.assertEqual(self.commands, [])
        self.assertFalse(self.ledger.exists())

    def test_budget_rejections_precede_capture_and_do_not_leak(self):
        terminal = {'n': 1, 'kind': 'export', 'status': 'FAILED', 'durationSeconds': 0}
        cases = [('count', [dict(terminal, n=n) for n in range(1, 17)], 'budget_exhausted'),
                 ('seconds', [dict(terminal, durationSeconds=871)], 'budget_exhausted'),
                 ('pending', [dict(terminal, status='STARTED', nativeBudgetReservedSeconds=30)], 'budget_busy'),
                 ('negative', [dict(terminal, durationSeconds=-1)], 'budget_unavailable'),
                 ('nan', [dict(terminal, durationSeconds=float('nan'))], 'budget_unavailable'),
                 ('unaccounted', [dict(terminal, nativeBudgetReservedSeconds=30)], 'budget_unavailable')]
        cases.append(('missing-duration', [{'n': 1, 'kind': 'export', 'status': 'COMPLETED'}], 'budget_unavailable'))
        for name, rows, reason in cases:
            with self.subTest(case=name), mock.patch.object(self.handler, '_capture') as capture:
                self.write_rows(rows)
                before = self.ledger.read_bytes()
                with self.assertRaisesRegex(ValueError, '^' + reason + '$'):
                    self.invoke()
                capture.assert_not_called()
                self.assertEqual(self.ledger.read_bytes(), before)
        for corruption in ('{PRIVATE', '{}'):
            self.ledger.write_text(corruption)
            with mock.patch.object(self.handler, '_capture') as capture:
                with self.assertRaisesRegex(ValueError, '^budget_unavailable$'):
                    self.invoke()
                capture.assert_not_called()

    def test_existing_lock_and_contract_mutation_fail_closed(self):
        import fcntl
        with (self.root / 'issue94-ledger.lock').open('r+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with mock.patch.object(self.handler, '_capture') as capture:
                with self.assertRaisesRegex(ValueError, '^budget_busy$'):
                    self.invoke()
                capture.assert_not_called()
        (self.root / 'contract.json').write_bytes(self.contract_bytes + b' ')
        with mock.patch.object(self.handler, '_capture') as capture:
            with self.assertRaisesRegex(ValueError, '^budget_unavailable$'):
                self.invoke()
            capture.assert_not_called()

    def test_one_remaining_slot_concurrently_reserves_only_once(self):
        self.write_rows([{'n': n, 'kind': 'export', 'status': 'COMPLETED', 'durationSeconds': 1}
                         for n in range(1, 16)])
        barrier = threading.Barrier(2)
        results = []

        def reserve():
            barrier.wait(timeout=2)
            try:
                result = self.owner()({'action': 'reserve', 'kind': 'export', 'request': REQUEST,
                                       'contractSha256': self.pin})
                results.append(result['attemptId'])
            except ValueError as error:
                results.append(str(error))

        workers = [threading.Thread(target=reserve) for _ in range(2)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=3)
            self.assertFalse(worker.is_alive())
        self.assertEqual(len(results), 2)
        self.assertEqual(sum(value == 'budget_busy' for value in results), 1)
        self.assertEqual(len(self.rows()), 16)
        self.assertEqual(self.rows()[-1]['status'], 'STARTED')
        self.assertEqual(self.rows()[-1]['nativeBudgetReservedSeconds'], 30)

    def test_settle_failure_retains_reservation_and_does_not_emit_success(self):
        real_transaction = self.owner()

        def transaction(command):
            if command['action'] == 'settle':
                raise OSError('PRIVATE failure')
            return real_transaction(command)

        with mock.patch.object(self, 'owner', return_value=transaction), \
                mock.patch.object(self.handler, '_capture', side_effect=self.capture):
            envelope = self.invoke_envelope()
        self.assertEqual(envelope, {'schemaVersion': 1, 'status': 'blocked',
                                    'reasonCode': 'capability_failed',
                                    'nativeInvocations': 'UNKNOWN_IF_EXPORT_REQUESTED'})
        self.assertEqual(self.rows()[-1]['status'], 'STARTED')
        self.assertEqual(self.rows()[-1]['nativeBudgetReservedSeconds'], 30)

    def test_reservation_rejection_envelope_truthfully_reports_no_native(self):
        self.ledger.write_text('{PRIVATE')
        with mock.patch.object(self.handler, '_capture') as capture:
            self.assertEqual(self.invoke_envelope(), {'schemaVersion': 1, 'status': 'blocked',
                                                      'reasonCode': 'budget_unavailable',
                                                      'nativeInvocations': 0})
            capture.assert_not_called()

    def test_reserved_capture_failure_does_not_claim_zero_native_invocations(self):
        # Change the actual worker receipt against the independent source probe.
        self.result['sourceDirectory'] = {'device': 9, 'inode': 10}
        envelope = self.invoke_native_boundary(envelope=True)
        self.assertEqual(len(self.launched_rows), 1)
        self.assertEqual(envelope, {'schemaVersion': 1, 'status': 'blocked',
                                    'reasonCode': 'binding_unavailable',
                                    'nativeInvocations': 'UNKNOWN_IF_EXPORT_REQUESTED'})
        self.assertEqual(self.rows()[-1]['status'], 'FAILED_NO_RETRY')
        self.assertEqual(self.rows()[-1]['durationSeconds'], 30)

    def test_settlement_rejects_invalid_receipt_hash_without_refund(self):
        attempt = self.handler.reserve_budget('export', REQUEST)
        for digest in ('', 'A' * 64, 'x' * 64, '0' * 63, None):
            with self.subTest(digest=digest):
                with self.assertRaisesRegex(ValueError, '^budget_unavailable$'):
                    self.handler._budget_transaction({'action': 'settle', 'attemptId': attempt,
                                                      'result': None, 'wallSeconds': 0,
                                                      'completed': False, 'receiptSha256': digest})
        self.assertEqual(self.rows()[-1]['status'], 'STARTED')
        self.assertEqual(self.rows()[-1]['nativeBudgetReservedSeconds'], 30)

    def test_operator_sessions_reuse_same_owner_and_exact_limit(self):
        for completed in (True, False):
            attempt = self.handler.reserve_budget('session')
            self.handler.settle_budget(attempt, wall_seconds=2, completed=completed)
        rows = self.rows()
        self.assertEqual([row['kind'] for row in rows], ['session', 'session'])
        self.assertEqual([row['status'] for row in rows], ['COMPLETED', 'FAILED_NO_RETRY'])
        self.assertEqual([row['durationSeconds'] for row in rows], [0, 0])
        self.assertEqual([row['nativeInvocations'] for row in rows], [0, 0])
        with self.assertRaisesRegex(ValueError, '^budget_exhausted$'):
            self.handler.reserve_budget('session')
        with self.assertRaisesRegex(ValueError, '^budget_unavailable$'):
            self.handler.settle_budget(attempt, completed=True)
        self.assertEqual(self.rows(), rows)


if __name__ == '__main__':
    unittest.main()
