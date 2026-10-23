"""Native DOM fact projection and adapter protocol checks, not browser acceptance."""
from pathlib import Path
import sys
import time
import types
import unittest
from unittest import mock

from one_c_harness import registration_web as web

URL = 'http://127.0.0.1:18090/jetcontrol/ru/?C=DisableSystemStartupLogic&DisableHomePageForms#e1cib/system/EventLogSettings'
RADIOS = ['form0_FollowingEvents', 'form0_FollowingEvents#1#radio', 'form0_FollowingEvents#2#radio',
          'form0_FollowingEvents#3#radio', 'form0_FollowingEvents#4#radio']
LABELS = ['Do not register', 'Register errors', 'Register errors and warnings',
          'Register errors, warnings, and information', 'Register errors, warnings, information, and comments']


class RegistrationWebTests(unittest.TestCase):
    def setUp(self):
        # These five classes/labels and Week are reduced facts from the actual
        # native-web-dom.private.json capture, not a fabricated HTML page.
        self.classes = {identifier: 'radio zoomI' for identifier in RADIOS}
        self.classes[RADIOS[4]] = 'radio zoomI select'
        self.adapter = web.RegistrationWeb(web.BrowserSettings(URL, Path(__file__).resolve()))

    def test_actual_custom_radio_fact_projects_all_levels_and_period(self):
        value = web._project_form(self.classes, LABELS, 'Week')
        self.assertEqual(value, {'levels': ['Error', 'Information', 'Note', 'Warning'], 'period': 'Week'})
        for count, expected in enumerate(([], ['Error'], ['Error', 'Warning'],
                                          ['Error', 'Information', 'Warning'], ['Error', 'Information', 'Note', 'Warning'])):
            classes = {identifier: 'radio zoomI' for identifier in RADIOS}
            classes[RADIOS[count]] += ' select'
            self.assertEqual(web._project_form(classes, LABELS, 'Week')['levels'], expected)

    def test_absent_ambiguous_or_wrong_form_is_rejected_not_checked_defaulted(self):
        none = {key: 'radio zoomI' for key in RADIOS}
        two = {**self.classes, RADIOS[0]: 'radio zoomI select'}
        substring = {**none, RADIOS[4]: 'radio zoomI unselected'}
        for classes, labels, period in ((none, LABELS, 'Week'), (two, LABELS, 'Week'),
                                        (substring, LABELS, 'Week'), ({}, LABELS, 'Week'),
                                        (self.classes, LABELS[:-1] + ['different'], 'Week'), (self.classes, LABELS, '')):
            with self.subTest(classes=classes), self.assertRaises(ValueError):
                web._project_form(classes, labels, period)

    def test_persisted_fresh_read_must_match_levels_and_original_period(self):
        saved = {'levels': ['Error'], 'period': 'Week'}
        for persisted in ({'levels': [], 'period': 'Week'}, {'levels': ['Error'], 'period': 'Day'}):
            with self.assertRaisesRegex(ValueError, '^native_readback_mismatch$'):
                web._confirmed(saved, persisted, ['Error'])
        self.assertEqual(web._confirmed(saved, dict(saved), ['Error']), saved)

    def test_nonprefix_levels_and_open_requests_are_refused_before_any_browser_import(self):
        for request in ({'action': 'set', 'levels': ['Warning'], 'expectedLevels': []},
                        {'action': 'set', 'levels': ['Error'], 'expectedLevels': ['Note']},
                        {'action': 'get', 'url': 'http://foreign/'}, {'action': 'set', 'levels': ['Error', 'Error'], 'expectedLevels': []}):
            with mock.patch.object(self.adapter, '_visit') as visit, self.assertRaises(ValueError):
                self.adapter(request)
            visit.assert_not_called()

    def test_native_exit_protocol_cancels_form_and_proves_login_without_clicking_login(self):
        page = mock.Mock()
        calls = []
        items = {}
        def locator(selector):
            item = items.setdefault(selector, mock.Mock())
            item.click.side_effect = lambda **kw: calls.append(('click', selector))
            item.wait_for.side_effect = lambda **kw: calls.append((kw['state'], selector))
            item.is_visible.return_value = selector == "[id='form0_FormCancel']"
            item.inner_text.return_value = 'Log in'
            return item
        page.locator.side_effect = locator
        web._normal_exit(page, time.monotonic() + 5)
        self.assertEqual(calls, [('click', "[id='form0_FormCancel']"), ('hidden', "[id='form0_FormCancel']"),
                                ('click', "[id='captionbarMore']"), ('click', "[id='FileButton']"),
                                ('visible', "[id='fileExit']"), ('click', "[id='fileExit']"), ('visible', "[id='okButton']")])
        self.assertNotIn(('click', "[id='okButton']"), calls)

    def test_visit_conflict_never_saves_and_attempts_one_native_exit_then_closes_both(self):
        chromium, browser, context, page = (mock.Mock() for _ in range(4))
        chromium.launch.return_value = browser
        browser.new_context.return_value = context
        context.new_page.return_value = page
        current = {'levels': ['Error', 'Warning'], 'period': 'Week'}
        with mock.patch.object(web, '_read_form', return_value=current), mock.patch.object(web, '_normal_exit') as exit_ui:
            value = self.adapter._visit(chromium, time.monotonic() + 30, ['Error'], [])
        self.assertEqual(value['status'], 'conflict')
        self.assertFalse(any(call.args == ("[id='form0_FormOK']",) for call in page.locator.call_args_list))
        exit_ui.assert_called_once()
        context.close.assert_called_once()
        browser.close.assert_called_once()

    def test_save_targets_exact_choice_checks_period_and_cleanup_failures_are_not_success(self):
        chromium, browser, context, page = (mock.Mock() for _ in range(4))
        chromium.launch.return_value = browser
        browser.new_context.return_value = context
        context.new_page.return_value = page
        before = {'levels': [], 'period': 'Week'}
        changed_period = {'levels': ['Error'], 'period': 'Day'}
        with mock.patch.object(web, '_read_form', side_effect=[before, changed_period]), \
                mock.patch.object(web, '_normal_exit') as exit_ui, self.assertRaisesRegex(ValueError, '^native_form_invalid$'):
            self.adapter._visit(chromium, time.monotonic() + 30, ['Error'], [])
        self.assertIn(mock.call("[id='form0_FollowingEvents#1#radio']"), page.locator.call_args_list)
        self.assertNotIn(mock.call("[id='form0_FormOK']"), page.locator.call_args_list)
        exit_ui.assert_called_once()
        context.close.assert_called_once()
        browser.close.assert_called_once()

        context.close.side_effect = RuntimeError('private error')
        with mock.patch.object(web, '_read_form', return_value=before), \
                mock.patch.object(web, '_normal_exit'), self.assertRaisesRegex(ValueError, '^browser_cleanup_failed$'):
            self.adapter._visit(chromium, time.monotonic() + 30)
        self.assertEqual(browser.close.call_count, 2)

    def test_primary_failure_is_preserved_separately_from_failed_exit_and_cleanup(self):
        chromium, browser, context, page = (mock.Mock() for _ in range(4))
        chromium.launch.return_value = browser
        browser.new_context.return_value = context
        context.new_page.return_value = page
        page.goto.side_effect = TimeoutError('source_timeout')
        context.close.side_effect = RuntimeError('private cleanup secret')
        def failed_exit(actual_page, cleanup_deadline):
            self.assertIs(actual_page, page)
            self.assertGreater(cleanup_deadline, time.monotonic())
            raise TimeoutError('exit timeout')
        with mock.patch.object(web, '_normal_exit', side_effect=failed_exit) as exit_ui, \
                self.assertRaisesRegex(ValueError, '^source_timeout$') as raised:
            self.adapter._visit(chromium, time.monotonic() + 1)
        self.assertEqual(raised.exception.diagnosis, {
            'operationOutcome': 'not_completed', 'saveAttempted': False,
            'primaryReasonCode': 'source_timeout', 'platformReasonCode': None,
            'exitReasonCode': 'native_exit_unproven', 'cleanupReasonCode': 'browser_cleanup_failed',
        })
        self.assertIsInstance(raised.exception.__cause__, TimeoutError)
        exit_ui.assert_called_once()
        context.close.assert_called_once()
        browser.close.assert_called_once()

    def test_native_save_can_persist_baseline_before_exit_failure(self):
        chromium, browser, context, page = (mock.Mock() for _ in range(4))
        chromium.launch.return_value = browser
        browser.new_context.return_value = context
        context.new_page.return_value = page
        baseline = {'levels': ['Error', 'Warning'], 'period': 'Week'}
        active = {'levels': ['Error', 'Information', 'Note', 'Warning'], 'period': 'Week'}
        persisted = dict(active)
        items = {}
        def locator(selector):
            item = items.setdefault(selector, mock.Mock())
            if selector == "[id='form0_FormOK']":
                item.click.side_effect = lambda **kw: persisted.update(baseline)
            return item
        page.locator.side_effect = locator
        with mock.patch.object(web, '_read_form', side_effect=[active, baseline]), \
                mock.patch.object(web, '_normal_exit', side_effect=TimeoutError('lost exit confirmation')), \
                self.assertRaisesRegex(ValueError, '^native_exit_unproven$') as raised:
            self.adapter._visit(chromium, time.monotonic() + 30, baseline['levels'], active['levels'])
        self.assertEqual(persisted, baseline)
        self.assertEqual(raised.exception.diagnosis['operationOutcome'], 'unknown')
        self.assertTrue(raised.exception.diagnosis['saveAttempted'])
        self.assertIsNone(raised.exception.diagnosis['primaryReasonCode'])
        self.assertEqual(raised.exception.diagnosis['exitReasonCode'], 'native_exit_unproven')
        items["[id='form0_FormOK']"].click.assert_called_once()
        context.close.assert_called_once()
        browser.close.assert_called_once()

    def test_cas_refusal_and_observed_get_are_not_labeled_unknown_save_when_exit_fails(self):
        for desired, expected, outcome in ((None, None, 'completed'), (['Error'], [], 'refused')):
            with self.subTest(outcome=outcome):
                chromium, browser, context, page = (mock.Mock() for _ in range(4))
                chromium.launch.return_value = browser
                browser.new_context.return_value = context
                context.new_page.return_value = page
                with mock.patch.object(web, '_read_form', return_value={'levels': ['Error', 'Warning'], 'period': 'Week'}), \
                        mock.patch.object(web, '_normal_exit', side_effect=TimeoutError('private exit failure')), \
                        self.assertRaisesRegex(ValueError, '^native_exit_unproven$') as raised:
                    self.adapter._visit(chromium, time.monotonic() + 30, desired, expected)
                self.assertEqual(raised.exception.diagnosis['operationOutcome'], outcome)
                self.assertFalse(raised.exception.diagnosis['saveAttempted'])
                self.assertNotIn(mock.call("[id='form0_FormOK']"), page.locator.call_args_list)

    def test_actual_native_training_refusal_is_observed_not_inferred_from_timeout(self):
        # Exact reduced facts retained by the actual native diagnostic receipt:
        # one visible Show details and one TEXTAREA carrying these two lines.
        for detail, expected_reason in (
                ('Training version limitation reached\nInfobase connections limitation reached', 'training_connection_limit'),
                ('The application is unavailable now, try to sign in later', None),
                ('Training version limitation reached', None)):
            with self.subTest(platformReason=expected_reason):
                chromium, browser, context, page = (mock.Mock() for _ in range(4))
                chromium.launch.return_value = browser
                browser.new_context.return_value = context
                context.new_page.return_value = page
                cancel = mock.Mock()
                cancel.wait_for.side_effect = TimeoutError('source_timeout')
                details = page.get_by_text.return_value
                details.count.return_value = 1
                details.is_visible.return_value = True
                fields = mock.Mock()
                fields.count.return_value = 1
                fields.nth.return_value.input_value.return_value = detail
                page.locator.side_effect = lambda selector: (fields if selector == 'textarea' else cancel
                    if selector == "[id='form0_FormCancel']" else mock.Mock(count=mock.Mock(return_value=0)))
                with mock.patch.object(web, '_normal_exit', side_effect=TimeoutError('private exit failure')), \
                        self.assertRaisesRegex(ValueError, '^source_timeout$') as raised:
                    self.adapter._visit(chromium, time.monotonic() + 30)
                diagnosis = raised.exception.diagnosis
                self.assertEqual(diagnosis['platformReasonCode'], expected_reason)
                self.assertEqual(diagnosis['primaryReasonCode'], 'source_timeout')
                self.assertEqual(diagnosis['operationOutcome'], 'refused' if expected_reason else 'not_completed')
                self.assertFalse(diagnosis['saveAttempted'])
                page.get_by_text.assert_called_once_with('Show details', exact=True)
                details.click.assert_called_once()
                self.assertNotIn(detail, str(raised.exception))

    def test_failed_fresh_get_after_save_keeps_the_enclosing_set_unknown_without_retry(self):
        failed_get = web.NativeWebError('source_timeout', {
            'operationOutcome': 'refused', 'saveAttempted': False,
            'primaryReasonCode': 'source_timeout', 'platformReasonCode': 'training_connection_limit',
            'exitReasonCode': 'native_exit_unproven', 'cleanupReasonCode': None,
        })
        api = types.ModuleType('playwright.sync_api')
        api.sync_playwright = mock.MagicMock()
        with mock.patch.dict(sys.modules, {'playwright': types.ModuleType('playwright'), 'playwright.sync_api': api}), \
                mock.patch.object(self.adapter, '_visit', side_effect=[{'status': 'ok', 'levels': ['Error'], 'period': 'Week'}, failed_get]) as visit, \
                self.assertRaisesRegex(web.NativeWebError, '^source_timeout$') as raised:
            self.adapter({'action': 'set', 'expectedLevels': [], 'levels': ['Error']})
        self.assertEqual(visit.call_count, 2)
        self.assertEqual(raised.exception.diagnosis['operationOutcome'], 'unknown')
        self.assertTrue(raised.exception.diagnosis['saveAttempted'])
        self.assertEqual(raised.exception.diagnosis['platformReasonCode'], 'training_connection_limit')

    def test_failure_inspection_has_one_total_deadline_and_never_retries_settings(self):
        page = mock.Mock()
        page.get_by_text.return_value.count.return_value = 1
        page.get_by_text.return_value.is_visible.return_value = True
        fields = page.locator.return_value
        fields.count.return_value = 3
        fields.nth.return_value.input_value.return_value = 'private unrecognized error'
        with mock.patch.object(web.time, 'monotonic', side_effect=[10, 10, 10.8, 11.1]):
            self.assertIsNone(web._platform_reason(page))
        fields.nth.return_value.input_value.assert_called_once()
        self.assertEqual(page.locator.call_args_list, [mock.call('textarea')])
        page.get_by_text.return_value.click.assert_called_once()

    def test_platform_markers_in_an_arbitrary_field_are_not_a_native_refusal(self):
        for count, visible in ((0, True), (2, True), (1, False)):
            with self.subTest(count=count, visible=visible):
                page = mock.Mock()
                details = page.get_by_text.return_value
                details.count.return_value = count
                details.is_visible.return_value = visible
                page.locator.return_value.nth.return_value.input_value.return_value = (
                    'Training version limitation reached\nInfobase connections limitation reached')
                self.assertIsNone(web._platform_reason(page))
                page.locator.assert_not_called()
                details.click.assert_not_called()


if __name__ == '__main__':
    unittest.main()
