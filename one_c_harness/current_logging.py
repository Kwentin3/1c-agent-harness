"""Fixed-container product backend; deployment owns all paths and target identity."""
import json
import os
from pathlib import Path
import re
import signal
import stat
import sys

from . import ARTIFACT_ID, CAPABILITY_VERSION, eventlog_exporter, logging_control, registration_logging
from .techlog_config import TechlogConfig, TechlogConfigError

_MAX_BYTES = 16384
_READS = ('observation_info', 'observe', 'expand_observation')
_PATHS = ('techlogConfig', 'techlogDirectory', 'techlogState', 'registrationState',
          'workDirectory', 'observationRoot', 'runtimeProfile')


def _path(value, *, directory=False, optional=False, trusted=False):
    if not isinstance(value, str):
        raise ValueError('configuration_invalid')
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('configuration_invalid')
    if optional and not path.exists():
        if not path.parent.is_dir():
            raise ValueError('configuration_unavailable')
        return path
    info = path.stat()
    if not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
        raise ValueError('configuration_invalid')
    if trusted and os.name == 'posix' and (info.st_uid != 0 or info.st_mode & 0o022):
        raise ValueError('configuration_invalid')
    return path


def _json_file(path):
    with path.open('rb') as stream:
        raw = stream.read(_MAX_BYTES + 1)
    if len(raw) > _MAX_BYTES:
        raise ValueError('configuration_invalid')
    return json.loads(raw, object_pairs_hook=_unique)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('invalid_request')
        result[key] = value
    return result


def _configuration():
    source = _path(os.environ.get('ONE_C_HARNESS_CURRENT_SOURCE'), directory=True, trusted=True)
    target = os.environ.get('ONE_C_HARNESS_CURRENT_TARGET_REF', '')
    if re.fullmatch(r'target:[0-9a-f]{64}', target) is None:
        raise ValueError('binding_unavailable')
    infobase = _path(os.environ.get('ONE_C_HARNESS_CURRENT_IB_PATH'), directory=True)
    config = _json_file(_path(str(source / 'deployment/goal91/current-logging.json'), trusted=True))
    if (not isinstance(config, dict) or set(config) != {'schemaVersion', *_PATHS, 'settingsEpf', 'timeZone'}
            or type(config['schemaVersion']) is not int or config['schemaVersion'] != 1 or config['timeZone'] != 'UTC'):
        raise ValueError('configuration_invalid')
    paths = {key: _path(config[key], directory=key not in ('techlogConfig', 'runtimeProfile'),
                         optional=key == 'techlogConfig', trusted=key == 'runtimeProfile') for key in _PATHS}
    relative = Path(config['settingsEpf'])
    if relative.is_absolute() or '..' in relative.parts or str(relative) != 'one_c_harness' + os.sep + 'logging.epf':
        raise ValueError('configuration_invalid')
    paths['settingsEpf'] = _path(str(source / relative))
    return config, paths, target, infobase


def _settings(paths, infobase):
    for key in eventlog_exporter.ENVIRONMENT_KEYS:
        os.environ.pop(key, None)
    os.environ.update(ONE_C_HARNESS_EVENTLOG_RUNTIME_PROFILE=str(paths['runtimeProfile']),
                      ONE_C_HARNESS_EVENTLOG_INFOBASE=str(infobase),
                      ONE_C_HARNESS_EVENTLOG_EPF=str(paths['settingsEpf']),
                      ONE_C_HARNESS_EVENTLOG_WORK_ROOT=str(paths['workDirectory']))
    return eventlog_exporter.load_settings()


def _drop_privileges():
    if os.name != 'posix' or os.geteuid() not in (0, 33):
        raise ValueError('configuration_unavailable')
    if os.geteuid() == 0:
        os.setgroups([])
        os.setgid(33)
        os.setuid(33)
    if os.geteuid() != 33 or os.getegid() != 33:
        raise ValueError('configuration_unavailable')


def _techlog(arguments, paths, target):
    manager = TechlogConfig(paths['techlogConfig'], paths['techlogDirectory'], paths['techlogState'], target_ref=target)
    action = arguments['action']
    if action == 'start':
        value = manager.start(arguments['profile'])
    elif action == 'stop':
        value = manager.stop(capture_ref=arguments['captureRef'])
    else:
        value = manager.status()
    conflict = value['status'] == 'conflict'
    result = {'status': 'conflict' if conflict else 'ok', 'journal': 'technological', 'targetRef': target,
              'state': 'unknown' if conflict else 'configured' if value['configurationApplied'] else 'inactive', 'platformState': 'unknown',
              'configurationState': 'conflict' if conflict else 'applied' if value['configurationApplied'] else 'restored' if action == 'stop' else 'unchanged',
              'capabilities': {'status': True, 'start': True, 'stop': True}}
    for key in ('captureRef', 'profile', 'reasonCode'):
        if key in value:
            result[key] = value[key]
    if action == 'stop':
        result['captureRef'] = arguments['captureRef']
    return result


def execute(raw):
    if len(raw) > _MAX_BYTES:
        raise ValueError('invalid_request')
    value = json.loads(raw, object_pairs_hook=_unique)
    if (not isinstance(value, dict) or set(value) != {'schemaVersion', 'operation', 'arguments'}
            or type(value['schemaVersion']) is not int or value['schemaVersion'] != 1
            or value['operation'] not in ('logging_control', *_READS) or not isinstance(value['arguments'], dict)):
        raise ValueError('invalid_request')
    operation, arguments = value['operation'], value['arguments']
    if operation == 'logging_control':
        logging_control.validate_request(arguments)
    config, paths, target, infobase = _configuration()
    if operation == 'logging_control':
        if arguments.get('targetRef', target) != target:
            raise ValueError('target_mismatch')
        if arguments['journal'] == 'technological':
            result = _techlog(arguments, paths, target)
        else:
            settings = _settings(paths, infobase)
            _drop_privileges()
            result = registration_logging.control(arguments['action'], settings, paths['registrationState'], target,
                profile=arguments.get('profile'), capture_ref=arguments.get('captureRef'))
        return {'artifactId': ARTIFACT_ID, 'capabilityVersion': CAPABILITY_VERSION,
                'schemaVersion': 1, 'operation': operation, **result}
    os.environ['ONE_C_HARNESS_TECHLOG_ROOT'] = str(paths['techlogDirectory'])
    os.environ['ONE_C_HARNESS_TECHLOG_TIME_ZONE'] = config['timeZone']
    _drop_privileges()
    from . import companion
    return companion.execute(raw, paths['observationRoot'])


def _timeout(signum, frame):
    raise TimeoutError('source_timeout')


def main():
    previous = {}
    raw = b''
    try:
        if len(sys.argv) != 1:
            raise ValueError('invalid_request')
        for name in ('SIGALRM', 'SIGTERM', 'SIGHUP'):
            signum = getattr(signal, name, None)
            if signum is not None:
                previous[signum] = signal.signal(signum, _timeout)
        if hasattr(signal, 'alarm'):
            signal.alarm(40)
        raw = sys.stdin.buffer.read(_MAX_BYTES + 1)
        result = execute(raw)
        output = json.dumps(result, ensure_ascii=True, separators=(',', ':'), allow_nan=False)
        if len(output.encode()) + 1 > _MAX_BYTES:
            raise ValueError('source_byte_limit')
    except (ValueError, TypeError, OSError, TimeoutError, eventlog_exporter.ExportFailure) as error:
        reason = str(error)
        if reason not in {'invalid_request', 'configuration_invalid', 'configuration_unavailable', 'binding_unavailable',
                          'target_mismatch', 'capture_not_found', 'profile_in_use', 'configuration_changed',
                          'busy', 'source_timeout', 'source_byte_limit'}:
            reason = 'source_unavailable'
        failure = {'schemaVersion': 1, 'status': 'blocked', 'reasonCode': reason}
        # Preserve only public error context, never raw arguments.
        try:
            value = json.loads(raw, object_pairs_hook=_unique) if len(raw) <= _MAX_BYTES else None
            if isinstance(value, dict) and value.get('operation') == 'logging_control':
                journal = value.get('arguments', {}).get('journal')
                if journal in ('registration', 'technological'):
                    failure.update(journal=journal, state='unknown', capabilities={'status': False, 'start': False, 'stop': False})
        except (ValueError, TypeError, AttributeError):
            pass
        output = json.dumps(failure)
    finally:
        if hasattr(signal, 'alarm'):
            signal.alarm(0)
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    print(output)
