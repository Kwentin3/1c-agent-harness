"""Harness boundary tests: substitute Relay, retain handler/JSON/ref admission."""
from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
NAME = "relay_test_one_c_plugin"
spec = importlib.util.spec_from_file_location(NAME, ROOT / "hermes-plugin/__init__.py",
    submodule_search_locations=[str(ROOT / "hermes-plugin")])
PLUGIN = importlib.util.module_from_spec(spec)
sys.modules[NAME] = PLUGIN
spec.loader.exec_module(PLUGIN)
TRANSPORT = sys.modules[NAME + ".relay_transport"]
SCHEMAS = sys.modules[NAME + ".schemas"]


class State:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return copy.deepcopy(self.values.get(key))

    def set(self, key, value):
        self.values[key] = copy.deepcopy(value)


class Relay:
    """Only the external Relay service is substituted, including its native envelopes."""
    def __init__(self, response=None, state=None):
        self.state = state or State()
        self.settings = {"transport": "relay", "relay_command": "/usr/local/bin/one-c-harness-local --request-stdin"}
        self.device = "linux-a"
        self.tools = {}
        self.calls = []
        self.response = response or {"status": "ok", "operation": "observation_info"}
        self.output = None
        self.request = None
        self.fail_at = None
        self.native_target = None
        self.log_patch = {}
        self.switch_after_start = False
        self.job_id = None
        self.job_state = "exited"
        self.exit_code = 0

    def get_config(self, key, default=None):
        return self.settings.get(key, default)

    def register_tool(self, **kwargs):
        self.tools[kwargs["name"]] = kwargs["handler"]

    def register_skill(self, *args, **kwargs):
        pass

    def register_system_prompt_section(self, *args, **kwargs):
        pass

    def dispatch_tool(self, name, args, **kwargs):
        self.calls.append((name, copy.deepcopy(args), kwargs))
        if name != "relay_dispatch":
            raise AssertionError("Relay mode reached a server tool")
        native = args["tool_name"]
        if args.get("expected_device_id", self.device) != self.device:
            return json.dumps({"device_id": self.device, "result": {"ok": False,
                "error": "Selected computer changed"}})
        if native == "desktop_job_start":
            self.job_id = args["arguments"]["job_id"]
        if self.fail_at == native:
            return json.dumps({"device_id": self.device,
                "result": {"error": "Desktop client disconnected"},
                "relay_outcome": TRANSPORT._unknown()})
        if native == "desktop_job_start":
            self.request = json.loads(args["arguments"]["stdin"])
            payload = {"job_id": self.job_id, "pid": 123}
            device = self.device
            if self.switch_after_start:
                self.device = "linux-b"
        elif native == "desktop_job_status":
            payload = {"job_id": self.job_id, "state": self.job_state, "exit_code": self.exit_code}
            device = self.device
        elif native == "desktop_job_logs":
            response = {"artifactId": SCHEMAS.ARTIFACT_ID,
                "capabilityVersion": SCHEMAS.CAPABILITY_VERSION, **self.response}
            output = self.output if self.output is not None else json.dumps(response, ensure_ascii=False)
            length = len(output.encode("utf-8"))
            payload = {"job_id": self.job_id, "state": "exited", "exit_code": 0,
                "stdout": {"content": output, "total_bytes": length, "offset": length,
                           "truncated": False, **self.log_patch}}
            device = self.device
        else:
            raise AssertionError(native)
        return json.dumps({"device_id": device, "result": {"request_id": "native-request",
            "ok": True, "target": {"device_id": self.native_target or device}, "result": payload}})


class RelayTransportTests(unittest.TestCase):
    def call(self, relay, tool="one_c_observation_info", arguments=None, **kwargs):
        PLUGIN.register(relay)
        return json.loads(relay.tools[tool]({} if arguments is None else arguments,
            session_id="actual-session", task_id="actual-task", **kwargs))

    def test_success_uses_native_full_output_and_trusted_call_context(self):
        relay = Relay({"status": "ok", "operation": "observation_info", "message": "\u0416\u0443\u0440\u043d\u0430\u043b"})
        result = self.call(relay)
        self.assertEqual(result["message"], "\u0416\u0443\u0440\u043d\u0430\u043b")
        self.assertEqual(relay.request, {"schemaVersion": 1, "operation": "observation_info", "arguments": {}})
        self.assertEqual([args["tool_name"] for _, args, _ in relay.calls],
            ["desktop_job_start", "desktop_job_status", "desktop_job_logs"])
        for _, args, context in relay.calls:
            self.assertEqual(context, {"session_id": "actual-session", "task_id": "actual-task"})
            if args["tool_name"] != "desktop_job_start":
                self.assertEqual(args["expected_device_id"], "linux-a")
        self.assertEqual(relay.calls[-1][1]["arguments"]["offset"], 0)
        self.assertEqual(result["relay_source"], {"job_id": relay.job_id, "device_id": "linux-a"})

    def test_unicode_request_roundtrips_through_real_child_stdin(self):
        # A real process consumes exactly the bytes handed to Relay's stdin contract.
        relay = Relay()
        ref = {"sourceIdentity": "sha256:source", "snapshot": {"contentId": "sha256:config"}}
        TRANSPORT.bind_refs(relay, {"snapshotRef": ref}, "linux-a")
        args = {"snapshotRef": ref, "query": "\u0414\u043e\u043a\u0443\u043c\u0435\u043d\u0442"}
        result = self.call(relay, "one_c_narrow_context", args)
        self.assertEqual(result["status"], "ok")
        wire = relay.calls[0][1]["arguments"]["stdin"]
        child = subprocess.run([sys.executable, "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"],
            input=wire.encode("utf-8"), capture_output=True, check=True)
        self.assertEqual(json.loads(child.stdout)["arguments"], args)

    def test_unknown_start_is_not_retried_and_marker_survives_outer_tool(self):
        relay = Relay()
        relay.fail_at = "desktop_job_start"
        result = self.call(relay)
        self.assertEqual(result["reasonCode"], "relay_outcome_unknown")
        self.assertFalse(result["relay_outcome"]["automatic_retry"])
        self.assertEqual(len(relay.calls), 1)
        self.assertEqual(result["relay_job"], {"job_id": relay.job_id, "device_id": "linux-a"})

    def test_switch_during_job_cannot_read_other_computer_or_fallback(self):
        relay = Relay()
        relay.switch_after_start = True
        result = self.call(relay)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["relay_job"], {"job_id": relay.job_id, "device_id": "linux-a"})
        self.assertTrue(result["relay_outcome"]["may_have_run"])
        self.assertEqual([args["tool_name"] for _, args, _ in relay.calls],
            ["desktop_job_start", "desktop_job_status"])

    def test_native_target_must_match_relay_selection(self):
        relay = Relay()
        relay.native_target = "foreign-device"
        result = self.call(relay)
        self.assertEqual(result["reasonCode"], "relay_device_mismatch")
        self.assertEqual(len(relay.calls), 1)

    def test_identical_snapshot_on_second_device_is_rejected_and_original_survives(self):
        ref = {"sourceIdentity": "sha256:source", "snapshot": {"contentId": "sha256:config"}}
        relay = Relay({"status": "ok", "operation": "open", "snapshotRef": ref})
        self.assertEqual(self.call(relay, "one_c_open")["snapshotRef"], ref)
        relay.device = "linux-b"
        blocked = self.call(relay, "one_c_open")
        self.assertEqual(blocked["reasonCode"], "relay_reference_target_mismatch")
        before = len(relay.calls)
        blocked = self.call(relay, "one_c_narrow_context", {"snapshotRef": ref, "query": "x"})
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(len(relay.calls), before + 1)
        self.assertEqual(relay.calls[-1][1]["expected_device_id"], "linux-a")
        self.assertEqual(TRANSPORT.expected_device(relay, {"snapshotRef": ref}), "linux-a")

    def test_missing_or_mixed_reference_binding_refuses_before_job_start(self):
        relay = Relay()
        result = self.call(relay, "one_c_read_registration_log_record", {"recordRef": "eventlog:missing"})
        self.assertEqual(result["reasonCode"], "relay_reference_unbound")
        self.assertEqual(relay.calls, [])
        TRANSPORT.bind_refs(relay, {"targetRef": "target:a"}, "linux-a")
        TRANSPORT.bind_refs(relay, {"captureRef": "capture:b"}, "linux-b")
        result = self.call(relay, "one_c_logging", {"action": "stop", "journal": "registration",
            "targetRef": "target:a", "captureRef": "capture:b"})
        self.assertEqual(result["reasonCode"], "relay_reference_target_mismatch")
        self.assertEqual(relay.calls, [])

    def test_journal_refs_survive_new_handler_context_and_keep_foreign_data_out(self):
        snapshot = "a" * 32
        group = f"snapshot:{snapshot}:group:EXCP:abc"
        record = f"snapshot:{snapshot}:record:0:abc"
        state = State()
        first = Relay({"status": "ok", "observationRef": "snapshot:" + snapshot,
            "snapshot": {"ref": snapshot}, "groups": [{"ref": group}],
            "records": [{"recordRef": record, "data": {"ref": "business-value"}}]}, state)
        self.assertEqual(self.call(first)["status"], "ok")
        second = Relay(state=state)
        result = self.call(second, "one_c_expand_observation", {"groupRef": group, "offset": 0, "limit": 1})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(second.calls[0][1]["expected_device_id"], "linux-a")
        self.assertNotIn(TRANSPORT._ref_key("business-value"), state.values)
        second.device = "linux-b"
        result = self.call(second, "one_c_expand_observation", {"recordRef": record, "before": 0, "after": 0})
        self.assertEqual(result["reasonCode"], "relay_dispatch_refused")

    def test_actual_techlog_owner_refs_can_continue_through_relay(self):
        from one_c_harness import techlog_observation

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, project = root / "source", root / "project"
            source.mkdir()
            project.mkdir()
            (source / "26091812.log").write_text(
                "00:00.000001-1,EXCP,1,Exception=DataError,Descr=bounded detail,SrcName=core\n",
                encoding="utf-8")
            with patch.dict("os.environ", {"ONE_C_HARNESS_TECHLOG_ROOT": str(source),
                    "ONE_C_HARNESS_TECHLOG_TIME_ZONE": "UTC"}):
                observed = techlog_observation.observe(project, "2026-09-18T12:00:00",
                    "2026-09-18T12:00:01", ["EXCP"], 1)
                self.assertEqual(observed["status"], "ok")
                first = Relay({"operation": "observe", "schemaVersion": 1, **observed})
                result = self.call(first, "one_c_observe", {"start": "2026-09-18T12:00:00",
                    "end": "2026-09-18T12:00:01", "events": ["EXCP"], "limit": 1})
                group = result["groups"][0]["ref"]
                expanded = techlog_observation.expand(project, group, 0, 1)
                self.assertEqual(expanded["status"], "ok")
                first.response = {"operation": "expand_observation", "schemaVersion": 1, **expanded}
                result = self.call(first, "one_c_expand_observation", {"groupRef": group, "offset": 0, "limit": 1})
                self.assertEqual(result["status"], "ok")
                self.assertEqual(result["records"][0]["event"], "EXCP")
                self.assertEqual(TRANSPORT.expected_device(first, {"recordRef": result["records"][0]["recordRef"]}), "linux-a")

    def test_concurrent_duplicate_ref_keeps_one_device_owner_in_agent_process(self):
        state = State()
        response = {"status": "ok", "snapshotRef": {"sourceIdentity": "same"}}
        first, second = Relay(response, state), Relay(response, state)
        second.device = "linux-b"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda ctx: self.call(ctx, "one_c_open"), [first, second]))
        self.assertEqual(sorted(result["status"] for result in results), ["blocked", "ok"])
        self.assertEqual(next(result["reasonCode"] for result in results if result["status"] == "blocked"),
            "relay_reference_target_mismatch")

    def test_timeout_after_start_preserves_job_without_cancel_or_retry(self):
        relay = Relay()
        relay.job_state = "running"
        with patch.object(TRANSPORT.time, "monotonic", side_effect=[0.0, 61.0]):
            result = self.call(relay)
        self.assertEqual(result["reasonCode"], "relay_job_pending")
        self.assertEqual(result["relay_job"]["job_id"], relay.job_id)
        self.assertEqual(len(relay.calls), 2)
        self.assertFalse(result["relay_outcome"]["automatic_retry"])

    def test_process_failure_and_verified_domain_block_are_distinct(self):
        relay = Relay()
        relay.exit_code = 7
        result = self.call(relay)
        self.assertEqual(result["reasonCode"], "relay_job_failed")
        self.assertEqual(result["relay_job"]["exit_code"], 7)
        relay = Relay({"status": "blocked", "reasonCode": "source_unavailable"})
        result = self.call(relay)
        self.assertEqual(result["reasonCode"], "source_unavailable")
        self.assertNotIn("relay_outcome", result)
        self.assertEqual(result["relay_source"]["device_id"], "linux-a")

    def test_stage_task_uses_json_stdin_without_server_write_file(self):
        relay = Relay({"status": "ok", "taskRef": {"taskId": "new-task"}})
        ref = {"sourceIdentity": "sha256:source"}
        TRANSPORT.bind_refs(relay, {"snapshotRef": ref}, "linux-a")
        args = {"snapshotRef": ref, "request": {"message": "\u0411\u0430\u0437\u0430", "businessRef": "domain-data"},
            "productionPatch": "patch", "instrumentationPatch": "instrumentation", "oracle": "experiments/task/oracle.py"}
        result = self.call(relay, "one_c_stage_task", args)
        self.assertEqual(result["taskRef"], {"taskId": "new-task"})
        self.assertEqual(relay.request["arguments"], args)
        self.assertEqual(TRANSPORT.expected_device(relay, result), "linux-a")

    def test_oversized_unicode_request_refuses_before_dispatch(self):
        relay = Relay()
        result = self.call(relay, "one_c_narrow_context", {"query": "\u0410" * 9000})
        self.assertEqual(result["reasonCode"], "invalid_request")
        self.assertEqual(relay.calls, [])

    def test_incomplete_or_malformed_output_is_not_domain_success(self):
        for update in ({"truncated": True}, {"offset": 1}, {"total_bytes": 1}, {"truncated": None}):
            with self.subTest(update=update):
                relay = Relay()
                relay.log_patch = update
                result = self.call(relay)
                self.assertEqual(result["reasonCode"], "relay_job_output_incomplete")
                self.assertTrue(result["relay_outcome"]["may_have_run"])
        relay = Relay()
        relay.output = "{} trailing shell output"
        result = self.call(relay)
        self.assertEqual(result["reasonCode"], "relay_job_output_invalid")
        self.assertFalse(result["relay_outcome"]["automatic_retry"])

    def test_bad_artifact_is_rejected_before_refs_are_bound(self):
        relay = Relay({"status": "ok", "artifactId": "sha256:wrong", "captureRef": "capture:bad"})
        result = self.call(relay)
        self.assertEqual(result["reasonCode"], "companion_artifact_mismatch")
        self.assertEqual(relay.state.values, {})
        self.assertTrue(result["relay_outcome"]["may_have_run"])

    def test_unknown_transport_and_missing_session_have_no_fallback(self):
        relay = Relay()
        relay.settings["transport"] = "typo"
        self.assertEqual(self.call(relay)["reasonCode"], "transport_unconfigured")
        relay.settings["transport"] = "relay"
        PLUGIN.register(relay)
        result = json.loads(relay.tools["one_c_observation_info"]({}))
        self.assertEqual(result["reasonCode"], "relay_session_missing")
        self.assertEqual(relay.calls, [])


if __name__ == "__main__":
    unittest.main()
