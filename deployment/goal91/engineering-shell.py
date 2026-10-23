#!/usr/bin/python3
"""SSH shell in the fixed, isolated #97 engineering or browser container."""
import json
import os
import re
import subprocess
import sys

IMAGE = 'sha256:036a932ca78ec1f161b83fc3d26d663d950a8e845002c160771950ec72ce6488'
NETWORKS = {'issue97-engineering': 'none', 'issue97-browser': 'bridge'}


def main():
    container = os.environ.get('ONE_C_ENGINEERING_CONTAINER', '')
    command = os.environ.get('SSH_ORIGINAL_COMMAND', '')
    return execute(command, container)


def execute(command, container, *, input=None, env=None):
    """Reuse the admitted local executor without manufacturing SSH state."""
    if not re.fullmatch(r'[0-9a-f]{64}', container):
        raise ValueError('binding_unavailable')
    if not command or len(command.encode()) > 32768 or '\0' in command:
        raise ValueError('command_required')
    inspect_options = {'timeout': 5}
    if env is not None:
        inspect_options['env'] = env
    inspected = json.loads(subprocess.check_output(
        ['/usr/bin/docker', 'inspect', container], **inspect_options))[0]
    host = inspected['HostConfig']
    config = inspected['Config']
    purpose = config['Labels'].get('one-c-access')
    if (inspected['Id'] != container or inspected['Image'] != IMAGE
            or not inspected['State']['Running']
            or config['User'] != '10001:10001'
            or purpose not in NETWORKS
            or not host['ReadonlyRootfs'] or host['Privileged']
            or host['NetworkMode'] != NETWORKS[purpose] or host['PidMode']
            or (purpose == 'issue97-browser' and host.get('Init') is not True)
            or host['IpcMode'] != 'private'
            or host['CapAdd'] or host['CapDrop'] != ['ALL']
            or 'no-new-privileges' not in host['SecurityOpt']
            or host['Memory'] != 1073741824
            or host['NanoCpus'] != 1000000000 or host['PidsLimit'] != 128):
        raise ValueError('binding_unavailable')
    # All persistent mounts are read-only. Mutable storage is bounded tmpfs;
    # no caller can supply a mount, container identity, user or Docker option.
    if any(mount['RW'] or mount['Type'] != 'bind'
           or mount['Destination'] in ('/var/run/docker.sock', '/run/docker.sock', '/host')
           for mount in inspected['Mounts']):
        raise ValueError('binding_unavailable')
    if set(host['Tmpfs']) != {'/workspace/1c-agent-harness/.local', '/tmp'}:
        raise ValueError('binding_unavailable')
    options = {}
    if input is not None:
        options['input'] = input
    if env is not None:
        options['env'] = env
    result = subprocess.run([
        '/usr/bin/docker', 'exec', '-i', '--user', '10001:10001',
        '--workdir', '/workspace/1c-agent-harness', container,
        '/bin/bash', '-c', command,
    ], **options)
    return result.returncode


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        reason = str(error) if isinstance(error, ValueError) else 'capability_unavailable'
        print(json.dumps({'status': 'blocked', 'reasonCode': reason}), file=sys.stderr)
        sys.exit(2)
