#!/usr/bin/env python3
"""Deployment-only stdin/SSH encoding for the existing fixed access capability."""
from __future__ import annotations
import base64
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys


def command(value: object) -> list[str]:
    if (not isinstance(value, dict)
        or set(value) != {'schemaVersion', 'operation', 'start', 'end', 'format', 'followMilliseconds'}
        or type(value['schemaVersion']) is not int or value['schemaVersion'] != 1
        or value['operation'] != 'export' or value['format'] != 'json'
        or type(value['followMilliseconds']) is not int or value['followMilliseconds'] != 0):
        raise ValueError('invalid_request')
    times = []
    for key in ('start', 'end'):
        if not isinstance(value[key], str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', value[key]):
            raise ValueError('invalid_request')
        times.append(datetime.fromisoformat(value[key]))
    if not 0 <= (times[1] - times[0]).total_seconds() <= 86400:
        raise ValueError('invalid_request')
    config = Path(os.environ.get('ONE_C_HARNESS_CURRENT_JOURNAL_SSH_CONFIG', ''))
    if not config.is_absolute() or config.is_symlink() or not config.is_file():
        raise ValueError('configuration_invalid')
    token = base64.b64encode(json.dumps(value, separators=(',', ':')).encode()).decode()
    return ['/usr/bin/ssh', '-F', str(config), '-T', 'current-journal', 'current-journal-v1 ' + token]


if __name__ == '__main__':
    try:
        raw = sys.stdin.buffer.read(4097)
        if len(raw) > 4096:
            raise ValueError('invalid_request')
        argv = command(json.loads(raw))
        os.execv(argv[0], argv)
    except (ValueError, TypeError, OSError):
        sys.stderr.write('{"reasonCode":"source_unavailable"}\n')
        raise SystemExit(2)
