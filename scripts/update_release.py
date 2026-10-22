#!/usr/bin/env python3
"""Refresh the existing matched core/plugin artifact ID after source changes."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
paths = []
for pattern in ('one_c_harness/*.py', 'hermes-plugin/*.py',
                'one_c_harness/eventlog_epf/**/*'):
    paths += [path for path in root.glob(pattern) if path.is_file()]
paths += [root/'hermes-plugin/plugin.yaml', root/'hermes-plugin/skills/one-c-harness/SKILL.md', root/'pyproject.toml']
paths += [root/'deployment/goal91'/name for name in (
    'current-journal.py', 'current-harness-client.py', 'current-capture-client.py',
    'current-logging-client.py', 'current-logging.json')]
digest = hashlib.sha256()
for path in sorted(paths):
    relative, payload = path.relative_to(root).as_posix().encode(), path.read_bytes()
    digest.update(len(relative).to_bytes(4, 'big')); digest.update(relative)
    digest.update(len(payload).to_bytes(8, 'big')); digest.update(payload)
value = {'schemaVersion': 1, 'artifactId': 'sha256:' + digest.hexdigest()}
for path in (root/'one_c_harness/release.json', root/'hermes-plugin/release.json'):
    path.write_bytes((json.dumps(value, indent=2) + '\n').encode('utf-8'))
print(value['artifactId'])
