from __future__ import annotations

import base64
import importlib.util
import json
import os
from pathlib import Path
import shlex
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from one_c_harness import logging_control

ROOT = Path(__file__).resolve().parents[1]
TARGET = "target:" + "a" * 64
CAPTURE = "capture:" + "b" * 32


def _plugin():
    name = "logging_control_test_plugin"
    spec = importlib.util.spec_from_file_location(name, ROOT / "hermes-plugin/__init__.py",
                                                submodule_search_locations=[str(ROOT / "hermes-plugin")])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class LoggingBoundaryTests(unittest.TestCase):
    def test_diagnosis_is_closed_bounded_and_cannot_turn_unknown_save_into_success(self):
        diagnosis = {'operationOutcome': 'unknown', 'saveAttempted': True,
                     'primaryReasonCode': 'source_timeout', 'platformReasonCode': 'training_connection_limit',
                     'exitReasonCode': 'native_exit_unproven', 'cleanupReasonCode': None}
        response = dict(status='blocked', state='unknown', journal='registration', reasonCode='source_timeout',
                        capabilities=dict(status=False, start=False, stop=False), diagnosis=diagnosis)
        request = {'action': 'status', 'journal': 'registration'}
        self.assertEqual(logging_control._project(json.dumps(response).encode(), request)['diagnosis'], diagnosis)
        for field, value in [('operationOutcome', 'refused'), ('saveAttempted', False),
                             ('platformReasonCode', 'inferred_from_timeout'), ('primaryReasonCode', '/private/secret'),
                             ('cleanupReasonCode', 'x' * 10000), ('private', 'customer data')]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                logging_control._project(json.dumps({**response, 'diagnosis': {**diagnosis, field: value}}).encode(), request)
        with self.assertRaises(ValueError):
            logging_control._project(json.dumps({**response, 'status': 'ok', 'targetRef': TARGET}).encode(), request)
        with self.assertRaises(ValueError):
            logging_control._project(json.dumps({**response, 'journal': 'technological'}).encode(),
                                     {'action': 'status', 'journal': 'technological'})

    def test_confirmed_set_with_shutdown_failure_stays_blocked_but_keeps_completed_fact(self):
        diagnosis = {'operationOutcome': 'completed', 'saveAttempted': True,
                     'primaryReasonCode': None, 'platformReasonCode': None,
                     'exitReasonCode': None, 'cleanupReasonCode': 'browser_cleanup_failed'}
        response = {'status': 'blocked', 'state': 'unknown', 'journal': 'registration', 'reasonCode': 'browser_cleanup_failed',
                    'capabilities': {'start': False, 'stop': False, 'status': False}, 'diagnosis': diagnosis}
        result = logging_control._project(json.dumps(response).encode(), {'action': 'status', 'journal': 'registration'})
        self.assertEqual(result['diagnosis'], diagnosis)
        self.assertEqual((result['status'], result['reasonCode']), ('blocked', 'browser_cleanup_failed'))
        self.assertFalse(any(result['capabilities'].values()))

    def test_successful_projection_requires_exact_request_refs(self):
        response = dict(status="ok", state="configured", journal="technological", targetRef=TARGET,
                        captureRef=CAPTURE, capabilities=dict(status=True, start=True, stop=True))
        start = dict(action="start", journal="technological", targetRef=TARGET, profile="errors")
        stop = dict(action="stop", journal="technological", targetRef=TARGET, captureRef=CAPTURE)
        for request, changed in ((start, {"targetRef": "target:" + "c" * 64}),
                                 (stop, {"targetRef": "target:" + "c" * 64}),
                                 (stop, {"captureRef": "capture:" + "c" * 32})):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                logging_control._project(json.dumps({**response, **changed}).encode(), request)
        missing_capture = dict(response); missing_capture.pop("captureRef")
        with self.assertRaises(ValueError):
            logging_control._project(json.dumps(missing_capture).encode(), stop)
        self.assertEqual(logging_control._project(json.dumps(response).encode(), stop)["captureRef"], CAPTURE)

    def test_missing_backend_is_truthfully_unavailable(self):
        with patch.dict(os.environ, {}, clear=True):
            result = logging_control.execute({"action": "status", "journal": "technological"})
        self.assertEqual((result["status"], result["state"], result["reasonCode"]),
                         ("unavailable", "unknown", "source_unavailable"))
        self.assertFalse(any(result["capabilities"].values()))

    def test_invalid_closed_requests_do_not_execute(self):
        invalid = [{}, {"action": "enable", "journal": "technological"},
                   {"action": "status", "journal": "other"},
                   {"action": "status", "journal": "registration", "path": "/tmp/source"},
                   {"action": "start", "journal": "registration", "profile": "verbose", "targetRef": TARGET},
                   {"action": "start", "journal": "technological", "profile": "errors", "targetRef": "/tmp/target"},
                   {"action": "stop", "journal": "technological", "captureRef": CAPTURE},
                   {"action": "stop", "journal": "technological", "captureRef": CAPTURE + "\n", "targetRef": TARGET},
                   {"action": "status", "journal": "technological", "command": "x" * 4097}]
        with patch.object(logging_control.subprocess, "Popen") as spawn:
            for request in invalid:
                with self.subTest(request=str(request)[:100]):
                    result = logging_control.execute(request)
                    self.assertEqual((result["status"], result["reasonCode"]), ("blocked", "invalid_request"))
            spawn.assert_not_called()

    def test_plugin_schema_manifest_and_existing_tools_match_wire(self):
        module = _plugin()
        calls, tools = [], {}
        class Context:
            def register_tool(self, **kwargs):
                tools[kwargs["name"]] = kwargs
            def register_skill(self, *args):
                pass
            def register_system_prompt_section(self, *args, **kwargs):
                pass
            def dispatch_tool(self, name, arguments):
                calls.append((name, arguments))
                return json.dumps({"exit_code": 0, "output": json.dumps({
                    "artifactId": module.ARTIFACT_ID, "capabilityVersion": module.CAPABILITY_VERSION,
                    "schemaVersion": 1, "operation": "logging_control", "status": "unavailable"})})
        module.register(Context())
        existing = {"one_c_open", "one_c_narrow_context", "one_c_native_verify", "one_c_observation_info",
                    "one_c_observe", "one_c_expand_observation", "one_c_select_registration_log",
                    "one_c_page_registration_log", "one_c_read_registration_log_record", "one_c_stage_task"}
        self.assertEqual(set(tools), existing | {"one_c_logging"})
        manifest = (ROOT / "hermes-plugin/plugin.yaml").read_text(encoding="utf-8")
        self.assertEqual({line.strip()[2:] for line in manifest.splitlines() if line.startswith("  - ")}, set(tools))
        variants = tools["one_c_logging"]["schema"]["parameters"]["oneOf"]
        requests = [{"action": "status", "journal": "technological"},
                    {"action": "start", "journal": "technological", "profile": "errors", "targetRef": TARGET},
                    {"action": "stop", "journal": "technological", "captureRef": CAPTURE, "targetRef": TARGET}]
        for schema, request in zip(variants, requests):
            self.assertFalse(schema["additionalProperties"])
            self.assertEqual(set(schema["required"]), set(request))
            self.assertEqual(schema["properties"]["action"]["const"], request["action"])
            logging_control.validate_request(request)
            tools["one_c_logging"]["handler"](request)
            name, terminal = calls[-1]
            self.assertEqual(name, "terminal")
            token = shlex.split(terminal["command"])[-1]
            self.assertEqual(json.loads(base64.b64decode(token)),
                             {"schemaVersion": 1, "operation": "logging_control", "arguments": request})
            self.assertEqual(terminal["timeout"], 75)


@unittest.skipUnless(sys.platform.startswith("linux"), "real executable/process-group fixtures require Linux")
class LoggingExecutableTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.command = self.root / "native-owner"

    def tearDown(self):
        self.temporary.cleanup()

    def backend(self, source):
        self.command.write_text("#!" + sys.executable + "\n" + source, encoding="utf-8")
        self.command.chmod(0o700)
        return patch.dict(os.environ, {"ONE_C_HARNESS_LOGGING_COMMAND": str(self.command)})

    def test_actual_owner_roundtrip_projection_and_configured_not_observed(self):
        request_file = self.root / "request.json"
        with self.backend("import json,sys\nfrom pathlib import Path\n"
                          "r=json.load(sys.stdin)\nPath(" + repr(str(request_file)) + ").write_text(json.dumps(r))\n"
                          "print(json.dumps(dict(status='ok',state='configured',journal=r['journal'],targetRef=" + repr(TARGET) +
                          ",captureRef=" + repr(CAPTURE) + ",capabilities=dict(status=True,start=True,stop=True),"
                          "configurationState='applied',platformState='unknown',stderr='/private/secret',password='hidden')))\n"):
            for action in ("status", "start", "stop"):
                request = {"action": action, "journal": "technological"}
                if action != "status": request["targetRef"] = TARGET
                if action == "start": request["profile"] = "diagnostic"
                if action == "stop": request["captureRef"] = CAPTURE
                result = logging_control.execute(request)
                self.assertEqual(json.loads(request_file.read_text()), {"schemaVersion": 1, **request})
                self.assertEqual((result["state"], result["platformState"]), ("configured", "unknown"))
                self.assertNotIn("stderr", result)
                self.assertNotIn("password", result)
                self.assertEqual(result["targetRef"], TARGET)

    def test_ref_identity_conflict_remains_native_owner_decision(self):
        with self.backend("import json,sys\nr=json.load(sys.stdin)\n"
                          "print(json.dumps(dict(status='conflict',state='configured',journal=r['journal'],"
                          "targetRef=" + repr(TARGET) + ",reasonCode='target_ref_mismatch',"
                          "capabilities=dict(status=True,start=False,stop=False))))\n"):
            result = logging_control.execute({"action": "start", "journal": "registration", "profile": "errors",
                                              "targetRef": "target:" + "c" * 64})
        self.assertEqual((result["status"], result["reasonCode"]), ("conflict", "target_ref_mismatch"))

    def test_symlink_nonexecutable_relative_and_shell_command_rejected_before_spawn(self):
        self.command.write_text("not executable")
        alias = self.root / "alias"; alias.symlink_to(self.command)
        with patch.object(logging_control.subprocess, "Popen") as spawn:
            for value in (str(alias), str(self.command), "relative/backend", "/bin/true --flag"):
                with patch.dict(os.environ, {"ONE_C_HARNESS_LOGGING_COMMAND": value}):
                    self.assertEqual(logging_control.execute({"action": "status", "journal": "registration"})["reasonCode"], "source_unavailable")
            spawn.assert_not_called()

    def test_output_caps_and_nonzero_exit_do_not_disclose_stderr(self):
        cases = [("import os\nos.write(1,b'x'*20000)\n", "source_byte_limit"),
                 ("import os\nos.write(2,b'private-secret'*1000)\n", "source_byte_limit"),
                 ("import sys\nsys.stderr.write('/private/secret');sys.exit(3)\n", "source_unavailable"),
                 ("print('not json')\n", "source_invalid_response")]
        for source, reason in cases:
            with self.subTest(reason=reason), self.backend(source):
                result = logging_control.execute({"action": "status", "journal": "registration"})
                self.assertEqual(result["reasonCode"], reason)
                self.assertNotIn("private", json.dumps(result))

    def test_timeout_reaps_parent_and_its_real_child(self):
        pids = self.root / "pids.json"
        source = ("import json,os,signal,subprocess,sys,time\nfrom pathlib import Path\n"
                  "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)'])\n"
                  "def stop(*args):\n child.terminate();child.wait();sys.exit(0)\n"
                  "signal.signal(signal.SIGTERM,stop)\n"
                  "Path(" + repr(str(pids)) + ").write_text(json.dumps([os.getpid(),child.pid]))\n"
                  "time.sleep(20)\n")
        started = time.monotonic()
        with self.backend(source), patch.object(logging_control, "_TIMEOUT_SECONDS", .25):
            result = logging_control.execute({"action": "status", "journal": "technological"})
        self.assertEqual(result["reasonCode"], "source_timeout")
        self.assertLess(time.monotonic() - started, 2)
        for pid in json.loads(pids.read_text()):
            with self.assertRaises(ProcessLookupError): os.kill(pid, 0)

    def test_actual_companion_envelope_keeps_logging_owner_result(self):
        from one_c_harness import ARTIFACT_ID, CAPABILITY_VERSION, companion
        with patch.dict(os.environ, {}, clear=True):
            response = companion.execute(json.dumps({"schemaVersion": 1, "operation": "logging_control",
                                                      "arguments": {"action": "status", "journal": "registration"}}).encode(), self.root)
        self.assertEqual(response["artifactId"], ARTIFACT_ID)
        self.assertEqual(response["capabilityVersion"], CAPABILITY_VERSION)
        self.assertEqual(response["operation"], "logging_control")
        self.assertEqual(response["reasonCode"], "source_unavailable")

    def test_real_backend_pipe_and_companion_preserve_separate_failed_operation_diagnosis(self):
        from one_c_harness import companion
        diagnosis = {'operationOutcome': 'unknown', 'saveAttempted': True,
                     'primaryReasonCode': 'source_timeout', 'platformReasonCode': 'training_connection_limit',
                     'exitReasonCode': 'native_exit_unproven', 'cleanupReasonCode': None}
        failed = {'status': 'blocked', 'state': 'unknown', 'journal': 'registration', 'reasonCode': 'source_timeout',
                  'capabilities': {'start': False, 'stop': False, 'status': False}, 'diagnosis': diagnosis}
        # Only the external fixed owner is replaced; real subprocess pipes,
        # bounds, projection and companion envelope remain on the product route.
        with self.backend('import json,sys\njson.load(sys.stdin)\nprint(' + repr(json.dumps(failed)) + ')\n'):
            response = companion.execute(json.dumps({'schemaVersion': 1, 'operation': 'logging_control',
                                                      'arguments': {'action': 'status', 'journal': 'registration'}}).encode(), self.root)
        self.assertEqual(response['diagnosis'], diagnosis)
        self.assertEqual((response['status'], response['state'], response['reasonCode']), ('blocked', 'unknown', 'source_timeout'))


if __name__ == "__main__":
    unittest.main()
