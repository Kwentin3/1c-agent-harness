#!/usr/bin/env python3
"""Product envelope over the existing fixed current-journal SSH capability."""
import base64
import json
import os
from pathlib import Path
import sys

OPERATIONS = ('logging_control', 'observation_info', 'observe', 'expand_observation', 'eventlog_capture')
MAX_REQUEST_BYTES = 16384


def command(value):
    if (not isinstance(value, dict) or set(value) != {'schemaVersion', 'operation', 'arguments'}
            or type(value['schemaVersion']) is not int or value['schemaVersion'] != 1
            or value['operation'] not in OPERATIONS or not isinstance(value['arguments'], dict)):
        raise ValueError('invalid_request')
    raw = json.dumps(value, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('utf-8')
    if len(raw) > MAX_REQUEST_BYTES:
        raise ValueError('invalid_request')
    config = Path(os.environ.get('ONE_C_HARNESS_CURRENT_JOURNAL_SSH_CONFIG', ''))
    if not config.is_absolute() or config.is_symlink() or not config.is_file():
        raise ValueError('configuration_invalid')
    return ['/usr/bin/ssh', '-F', str(config), '-T', 'current-journal',
            'current-harness-v1 ' + base64.b64encode(raw).decode('ascii')]


if __name__ == '__main__':
    try:
        raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
        if len(raw) > MAX_REQUEST_BYTES:
            raise ValueError('invalid_request')
        argv = command(json.loads(raw))
        os.execv(argv[0], argv)
    except (ValueError, TypeError, OSError):
        sys.stderr.write('{"reasonCode":"source_unavailable"}\n')
        raise SystemExit(2)
