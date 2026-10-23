"""Thin adapter to the admitted native EventLogSettings form, not a settings owner.

The radio IDs/classes and labels come from the actual 8.5.1.1150 form capture.
Playwright is optional and is imported only when this deployment invokes it.
"""
from dataclasses import dataclass
from pathlib import Path
import time
from urllib.parse import urlsplit

_LEVELS = ('Error', 'Warning', 'Information', 'Note')
_RADIOS = ('form0_FollowingEvents', *(f'form0_FollowingEvents#{n}#radio' for n in range(1, 5)))
_LABELS = ('Do not register', 'Register errors', 'Register errors and warnings',
           'Register errors, warnings, and information', 'Register errors, warnings, information, and comments')
_PRIMARY_REASONS = {'source_timeout', 'native_form_invalid', 'native_readback_mismatch', 'native_web_unavailable'}


class NativeWebError(ValueError):
    """One failed native request, with safe operation and cleanup facts separate."""
    def __init__(self, reason_code, diagnosis):
        super().__init__(reason_code)
        self.diagnosis = diagnosis


def _primary_reason(error):
    reason = str(error)
    if reason in _PRIMARY_REASONS:
        return reason
    # Playwright's TimeoutError is not Python's builtin TimeoutError.
    if isinstance(error, TimeoutError) or type(error).__name__ == 'TimeoutError':
        return 'source_timeout'
    return 'native_web_unavailable'


@dataclass(frozen=True)
class BrowserSettings:
    url: str
    browser: Path

    def __post_init__(self):
        url = urlsplit(self.url)
        if (url.scheme != 'http' or url.hostname != '127.0.0.1' or url.username or url.password
                or url.path != '/jetcontrol/ru/' or url.query != 'C=DisableSystemStartupLogic&DisableHomePageForms'
                or url.fragment != 'e1cib/system/EventLogSettings' or not self.browser.is_absolute()):
            raise ValueError('configuration_invalid')


def _index(levels):
    if not isinstance(levels, list) or any(not isinstance(v, str) for v in levels) or len(set(levels)) != len(levels):
        raise ValueError('invalid_request')
    for count in range(5):
        if set(levels) == set(_LEVELS[:count]):
            return count
    raise ValueError('unsupported_levels')


def _project_form(radios, labels, period):
    """Project only observed custom-radio classes; these are not HTML checked inputs."""
    if set(radios) != set(_RADIOS) or tuple(labels) != _LABELS or not isinstance(period, str) or not period:
        raise ValueError('native_form_invalid')
    selected = []
    for index, identifier in enumerate(_RADIOS):
        classes = radios[identifier]
        if not isinstance(classes, str) or 'radio' not in classes.split():
            raise ValueError('native_form_invalid')
        if 'select' in classes.split():
            selected.append(index)
    if len(selected) != 1:
        raise ValueError('native_form_invalid')
    return {'levels': sorted(_LEVELS[:selected[0]]), 'period': period}


def _confirmed(saved, persisted, desired):
    if persisted['levels'] != desired or persisted['period'] != saved['period']:
        raise ValueError('native_readback_mismatch')
    return persisted


def _selector(identifier):
    return "[id='" + identifier + "']"


def _read_form(page):
    radios, labels = {}, []
    for count, identifier in enumerate(_RADIOS):
        item = page.locator(_selector(identifier))
        if item.count() != 1 or not item.is_visible():
            raise ValueError('native_form_invalid')
        radios[identifier] = item.get_attribute('class')
        labels.append(page.locator(_selector(f'form0_FollowingEvents#{count}#title')).inner_text().strip())
    return _project_form(radios, labels, page.locator(_selector('form0_SplitLogByPeriod_i0')).input_value())


def _remaining(deadline, maximum=5000):
    remaining = int((deadline - time.monotonic()) * 1000)
    if remaining <= 0:
        raise TimeoutError('source_timeout')
    return min(maximum, remaining)


def _normal_exit(page, deadline):
    cancel = page.locator(_selector('form0_FormCancel'))
    if cancel.is_visible():
        cancel.click(timeout=_remaining(deadline))
        cancel.wait_for(state='hidden', timeout=_remaining(deadline))
    page.locator(_selector('captionbarMore')).click(timeout=_remaining(deadline))
    page.locator(_selector('FileButton')).click(timeout=_remaining(deadline))
    exit_item = page.locator(_selector('fileExit'))
    exit_item.wait_for(state='visible', timeout=_remaining(deadline))
    exit_item.click(timeout=_remaining(deadline))
    login = page.locator(_selector('okButton'))
    login.wait_for(state='visible', timeout=_remaining(deadline))
    if login.inner_text().strip() != 'Log in':
        raise ValueError('native_exit_unproven')


def _platform_reason(page):
    """Inspect only the observed error details, never retry/login/restart/Save.

    These exact two lines came from the admitted native error form. A timeout
    or the generic unavailable screen alone proves no platform cause. Keep all
    unknown text private, with a one-second total inspection allowance.
    """
    deadline = time.monotonic() + 1
    try:
        details = page.get_by_text('Show details', exact=True)
        if details.count() != 1 or not details.is_visible():
            return None
        details.click(timeout=_remaining(deadline, 300))
        expected = {'Training version limitation reached', 'Infobase connections limitation reached'}
        for selector in ('textarea', 'pre'):
            fields = page.locator(selector)
            for index in range(min(fields.count(), 3)):
                field = fields.nth(index)
                timeout = _remaining(deadline, 300)
                value = field.input_value(timeout=timeout) if selector == 'textarea' else field.inner_text(timeout=timeout)
                if len(value) <= 16384 and expected.issubset(value.splitlines()):
                    return 'training_connection_limit'
    except Exception:
        pass
    return None


class RegistrationWeb:
    def __init__(self, settings):
        self.settings = settings

    def _visit(self, chromium, deadline, desired=None, expected=None):
        browser = context = page = None
        primary = result = None
        save_attempted = False
        exit_reason = cleanup_reason = platform_reason = None
        try:
            browser = chromium.launch(executable_path=str(self.settings.browser), headless=True,
                                      args=['--no-sandbox', '--disable-dev-shm-usage'], timeout=_remaining(deadline))
            context = browser.new_context()
            page = context.new_page()
            page.set_default_timeout(3000)
            page.goto(self.settings.url, wait_until='domcontentloaded', timeout=_remaining(deadline, 12000))
            page.locator(_selector('form0_FormCancel')).wait_for(state='visible', timeout=_remaining(deadline, 12000))
            before = _read_form(page)
            result = {'status': 'ok', **before}
            if desired is not None:
                if before['levels'] != expected:
                    result['status'] = 'conflict'
                else:
                    choice = _selector(_RADIOS[_index(desired)])
                    page.locator(choice).click(timeout=_remaining(deadline))
                    page.locator(choice + '.select').wait_for(state='visible', timeout=_remaining(deadline))
                    selected = _read_form(page)
                    if selected['levels'] != desired or selected['period'] != before['period']:
                        raise ValueError('native_form_invalid')
                    # A click may reach the platform even if its reply is lost.
                    save_timeout = _remaining(deadline)
                    save_attempted = True
                    page.locator(_selector('form0_FormOK')).click(timeout=save_timeout)
                    page.locator(_selector('form0_FormCancel')).wait_for(state='hidden', timeout=_remaining(deadline))
                    result = {'status': 'ok', **selected}
        except Exception as error:
            primary = error
        finally:
            # Only this visit's normal Exit and resources; never another session.
            if page is not None:
                try:
                    # Keep an independent cleanup allowance after the 30s UI work
                    # deadline; the enclosing fixed backend bounds this at 40s.
                    _normal_exit(page, time.monotonic() + 5)
                except Exception:
                    exit_reason = 'native_exit_unproven'
                if primary is not None or exit_reason is not None:
                    platform_reason = _platform_reason(page)
            for resource in (context, browser):
                if resource is not None:
                    try:
                        resource.close()
                    except Exception:
                        cleanup_reason = 'browser_cleanup_failed'
        if primary is not None or exit_reason is not None or cleanup_reason is not None:
            primary_reason = _primary_reason(primary) if primary is not None else None
            outcome = ('unknown' if save_attempted else
                       'refused' if result is not None and result['status'] == 'conflict' else
                       'completed' if result is not None and primary is None else
                       'refused' if platform_reason else 'not_completed')
            raise NativeWebError(primary_reason or exit_reason or cleanup_reason, {
                'operationOutcome': outcome, 'saveAttempted': save_attempted,
                'primaryReasonCode': primary_reason, 'platformReasonCode': platform_reason,
                'exitReasonCode': exit_reason, 'cleanupReasonCode': cleanup_reason,
            }) from primary
        return result

    def __call__(self, request):
        if request == {'action': 'get'}:
            desired = expected = None
        elif isinstance(request, dict) and set(request) == {'action', 'levels', 'expectedLevels'} and request['action'] == 'set':
            desired = sorted(_LEVELS[:_index(request['levels'])])
            expected = sorted(_LEVELS[:_index(request['expectedLevels'])])
        else:
            raise ValueError('invalid_request')
        deadline = time.monotonic() + 30
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ValueError('browser_unavailable') from None
        primary = result = None
        try:
            with sync_playwright() as playwright:
                try:
                    result = self._visit(playwright.chromium, deadline, desired, expected)
                    if desired is not None and result['status'] == 'ok':
                        try:
                            persisted = self._visit(playwright.chromium, deadline)
                            result = _confirmed(result, persisted, desired)
                        except NativeWebError as error:
                            # This visit was a Get, but the enclosing request already
                            # attempted Save. Never report that Set as a safe refusal.
                            error.diagnosis.update(operationOutcome='unknown', saveAttempted=True)
                            raise
                        except ValueError as error:
                            reason = _primary_reason(error)
                            raise NativeWebError(reason, {
                                'operationOutcome': 'unknown', 'saveAttempted': True,
                                'primaryReasonCode': reason, 'platformReasonCode': None,
                                'exitReasonCode': None, 'cleanupReasonCode': None,
                            }) from error
                except NativeWebError as error:
                    # The framework's __exit__ can itself fail. Keep the native
                    # operation evidence before handing it that pending error.
                    primary = error
                    raise
        except Exception as error:
            if primary is not None:
                if error is not primary:
                    primary.diagnosis['cleanupReasonCode'] = 'browser_cleanup_failed'
                raise primary
            if result is not None:
                # Both visits and the required persisted check already finished.
                # A later driver shutdown failure does not undo that observation.
                raise NativeWebError('browser_cleanup_failed', {
                    'operationOutcome': 'refused' if result['status'] == 'conflict' else 'completed',
                    'saveAttempted': desired is not None and result['status'] == 'ok',
                    'primaryReasonCode': None, 'platformReasonCode': None,
                    'exitReasonCode': None, 'cleanupReasonCode': 'browser_cleanup_failed',
                }) from error
            if isinstance(error, (ValueError, TimeoutError)):
                raise
            raise ValueError('native_web_unavailable') from None
        if primary is not None:
            raise primary  # A context manager must not suppress an owned failure.
        return {'status': result['status'], 'levels': result['levels']}
