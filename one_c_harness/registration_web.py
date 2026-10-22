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


class RegistrationWeb:
    def __init__(self, settings):
        self.settings = settings

    def _visit(self, chromium, deadline, desired=None, expected=None):
        browser = context = page = None
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
                    page.locator(_selector('form0_FormOK')).click(timeout=_remaining(deadline))
                    page.locator(_selector('form0_FormCancel')).wait_for(state='hidden', timeout=_remaining(deadline))
                    result = {'status': 'ok', **selected}
            return result
        finally:
            # Only this visit's normal Exit and resources; never another session.
            cleanup_error = None
            if page is not None:
                try:
                    # Keep an independent cleanup allowance after the 30s UI work
                    # deadline; the enclosing fixed backend bounds this at 40s.
                    _normal_exit(page, time.monotonic() + 5)
                except Exception:
                    cleanup_error = 'native_exit_unproven'
            for resource in (context, browser):
                if resource is not None:
                    try:
                        resource.close()
                    except Exception:
                        cleanup_error = cleanup_error or 'browser_cleanup_failed'
            if cleanup_error is not None:
                raise ValueError(cleanup_error) from None

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
        try:
            with sync_playwright() as playwright:
                result = self._visit(playwright.chromium, deadline, desired, expected)
                if desired is not None and result['status'] == 'ok':
                    persisted = self._visit(playwright.chromium, deadline)
                    result = _confirmed(result, persisted, desired)
                return {'status': result['status'], 'levels': result['levels']}
        except (ValueError, TimeoutError):
            raise
        except Exception:
            raise ValueError('native_web_unavailable') from None
