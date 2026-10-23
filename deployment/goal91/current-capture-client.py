#!/usr/bin/env python3
"""Adapt the existing export request; capture/admission stay with their owners."""
import json
import os
from pathlib import Path
import runpy
import sys

try:
    raw = sys.stdin.buffer.read(4097)
    if len(raw) > 4096:
        raise ValueError('invalid_request')
    client = runpy.run_path(str(Path(__file__).with_name('current-harness-client.py')))
    argv = client['command']({'schemaVersion': 1, 'operation': 'eventlog_capture', 'arguments': json.loads(raw)})
    os.execv(argv[0], argv)
except (ValueError, TypeError, OSError):
    sys.stderr.write('{"reasonCode":"source_unavailable"}\n')
    raise SystemExit(2)
