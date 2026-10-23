"""Test SSH admission/argv; live namespace denials remain separate evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'deployment/goal91/engineering-shell.py'
SPEC = importlib.util.spec_from_file_location('engineering_access', SCRIPT)
ACCESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ACCESS)
CID = '1f3565421de9c18af24408e6a04db29297ba7c3dd61810ec8f6806fa77ffd5ba'

# Relevant fields from the actual HOME Docker admission. This fixture tests
# transport validation, not a claim that mocked Docker enforces isolation.
ADMITTED = {
    'Id': CID, 'Image': ACCESS.IMAGE, 'State': {'Running': True},
    'Config': {'User': '10001:10001', 'Labels': {'one-c-access': 'issue97-engineering'}},
    'HostConfig': {
        'ReadonlyRootfs': True, 'Privileged': False, 'NetworkMode': 'none',
        'PidMode': '', 'IpcMode': 'private', 'CapAdd': None, 'CapDrop': ['ALL'],
        'SecurityOpt': ['no-new-privileges'], 'Memory': 1073741824,
        'NanoCpus': 1000000000, 'PidsLimit': 128,
        'Tmpfs': {'/workspace/1c-agent-harness/.local': '', '/tmp': ''},
    },
    'Mounts': [{'Type': 'bind', 'RW': False, 'Destination': '/workspace/1c-agent-harness'}],
}


class EngineeringAccessTests(unittest.TestCase):
    def invoke(self, inspected, command='id', container=CID):
        return patch.object(ACCESS.os, 'environ', {
            'ONE_C_ENGINEERING_CONTAINER': container,
            'SSH_ORIGINAL_COMMAND': command,
        }), patch.object(ACCESS.subprocess, 'check_output', return_value=json.dumps([inspected])), patch.object(ACCESS.subprocess, 'run', return_value=subprocess.CompletedProcess([], 7))

    def reject_binding(self, inspected):
        environment, inspect, run = self.invoke(inspected)
        with environment, inspect, run as execution:
            with self.assertRaisesRegex(ValueError, 'binding_unavailable'):
                ACCESS.main()
            execution.assert_not_called()

    def test_command_stays_inside_fixed_unprivileged_docker_exec(self):
        command = 'printf "%s" "$(id)"; echo own-command'
        environment, inspect, run = self.invoke(ADMITTED, command)
        with environment, inspect as inspection, run as execution:
            self.assertEqual(ACCESS.main(), 7)
            inspection.assert_called_once_with(['/usr/bin/docker', 'inspect', CID], timeout=5)
            execution.assert_called_once_with([
                '/usr/bin/docker', 'exec', '-i', '--user', '10001:10001',
                '--workdir', '/workspace/1c-agent-harness', CID,
                '/bin/bash', '-c', command,
            ])

    def test_invalid_identity_and_command_refuse_before_docker(self):
        for container, command in [('', 'id'), ('other', 'id'), (CID, ''),
                (CID, 'a' * 32769), (CID, '\0'), (CID, '\u044f' * 16385)]:
            with self.subTest(container=container, command_length=len(command)):
                environment, inspect, run = self.invoke(ADMITTED, command, container)
                with environment, inspect as inspection, run as execution:
                    with self.assertRaises(ValueError):
                        ACCESS.main()
                    inspection.assert_not_called()
                    execution.assert_not_called()

    def test_foreign_or_stopped_container_refuses(self):
        for field, value in [('Id', 'a' * 64), ('Image', 'sha256:foreign'), ('State', {'Running': False})]:
            candidate = copy.deepcopy(ADMITTED)
            candidate[field] = value
            with self.subTest(field=field):
                self.reject_binding(candidate)
        candidate = copy.deepcopy(ADMITTED)
        candidate['Config']['User'] = '0:0'
        self.reject_binding(candidate)
        candidate['Config']['User'] = '10001:10001'
        candidate['Config']['Labels']['one-c-access'] = 'other'
        self.reject_binding(candidate)

    def test_namespace_privilege_and_resource_mutations_refuse(self):
        mutations = [('ReadonlyRootfs', False), ('Privileged', True),
            ('NetworkMode', 'host'), ('PidMode', 'host'), ('IpcMode', 'host'),
            ('CapAdd', ['SYS_ADMIN']), ('CapDrop', []), ('SecurityOpt', []),
            ('Memory', 0), ('NanoCpus', 0), ('PidsLimit', 0), ('Tmpfs', {'/tmp': ''})]
        for field, value in mutations:
            candidate = copy.deepcopy(ADMITTED)
            candidate['HostConfig'][field] = value
            with self.subTest(field=field):
                self.reject_binding(candidate)

    def test_browser_network_is_separate_from_offline_engineering(self):
        browser = copy.deepcopy(ADMITTED)
        browser['Config']['Labels']['one-c-access'] = 'issue97-browser'
        browser['HostConfig']['NetworkMode'] = 'bridge'
        browser['HostConfig']['Init'] = True
        environment, inspect, run = self.invoke(browser)
        with environment, inspect, run as execution:
            self.assertEqual(ACCESS.main(), 7)
            argv = execution.call_args.args[0]
            self.assertEqual(argv[argv.index('--user') + 1], '10001:10001')
        for network in ['none', 'host', 'container:foreign']:
            browser['HostConfig']['NetworkMode'] = network
            with self.subTest(browser_network=network):
                self.reject_binding(browser)
        engineering = copy.deepcopy(ADMITTED)
        engineering['HostConfig']['NetworkMode'] = 'bridge'
        self.reject_binding(engineering)
        browser['HostConfig']['NetworkMode'] = 'bridge'
        browser['HostConfig']['Init'] = False
        self.reject_binding(browser)

    def test_persistent_write_socket_or_host_mount_refuses(self):
        for mount in [{'Type': 'bind', 'RW': True, 'Destination': '/workspace'},
                {'Type': 'volume', 'RW': False, 'Destination': '/workspace'},
                *[{'Type': 'bind', 'RW': False, 'Destination': target}
                    for target in ['/host', '/run/docker.sock', '/var/run/docker.sock']]]:
            candidate = copy.deepcopy(ADMITTED)
            candidate['Mounts'].append(mount)
            with self.subTest(mount=mount):
                self.reject_binding(candidate)


if __name__ == '__main__':
    unittest.main()
