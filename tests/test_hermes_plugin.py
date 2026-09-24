from __future__ import annotations

import base64
import copy
import importlib.util
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "hermes-plugin"


def _plugin_module():
    name = "issue35_one_c_plugin"
    spec = importlib.util.spec_from_file_location(
        name, PLUGIN / "__init__.py", submodule_search_locations=[str(PLUGIN)],
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _artifact_id() -> str:
    return json.loads((PLUGIN / "release.json").read_text(encoding="utf-8"))["artifactId"]


def _restore_common(common: dict[str, object], item: dict[str, object]) -> dict[str, object]:
    restored = copy.deepcopy(common)
    for key, value in copy.deepcopy(item).items():
        if isinstance(value, dict) and isinstance(restored.get(key), dict):
            restored[key] = _restore_common(restored[key], value)
        else:
            restored[key] = value
    return restored


class _Context:
    def __init__(self, terminal_response: dict[str, object]):
        self.tools: dict[str, object] = {}
        self.skill: tuple[str, Path, str] | None = None
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.terminal_response = terminal_response

    def register_tool(self, **kwargs):
        self.tools[kwargs["name"]] = kwargs["handler"]

    def register_skill(self, name: str, path: Path, description: str):
        self.skill = (name, path, description)

    def register_system_prompt_section(self, *args, **kwargs):
        return None

    def dispatch_tool(self, name: str, args: dict[str, object]) -> str:
        self.calls.append((name, args))
        return json.dumps(self.terminal_response)


class HermesPluginTests(unittest.TestCase):
    def test_release_artifact_binds_companion_plugin_and_skill_closure(self) -> None:
        paths = []
        for pattern in ("one_c_harness/*.py", "hermes-plugin/*.py"):
            paths.extend(ROOT.glob(pattern))
        paths += [PLUGIN / "plugin.yaml", PLUGIN / "skills/one-c-harness/SKILL.md", ROOT / "pyproject.toml"]
        digest = hashlib.sha256()
        for path in sorted(path for path in paths if path.name != "release.json"):
            relative = path.relative_to(ROOT).as_posix().encode()
            payload = path.read_bytes()
            digest.update(len(relative).to_bytes(4, "big")); digest.update(relative)
            digest.update(len(payload).to_bytes(8, "big")); digest.update(payload)
        expected = "sha256:" + digest.hexdigest()
        companion = json.loads((ROOT / "one_c_harness/release.json").read_text())["artifactId"]
        self.assertEqual(expected, companion)
        self.assertEqual(expected, _artifact_id())

    def test_registers_one_skill_and_nine_closed_tools(self) -> None:
        plugin = _plugin_module()
        context = _Context({"output": "{}", "exit_code": 1})

        plugin.register(context)

        self.assertEqual(set(context.tools), {"one_c_open", "one_c_narrow_context", "one_c_native_verify", "one_c_observation_info", "one_c_observe", "one_c_expand_observation", "one_c_select_registration_log", "one_c_page_registration_log", "one_c_read_registration_log_record"})
        self.assertIsNotNone(context.skill)
        assert context.skill is not None
        self.assertEqual(context.skill[0], "one-c-harness")
        self.assertTrue(context.skill[1].is_file())

    def test_manifest_schema_and_registration_agree_on_observation_tools(self) -> None:
        plugin = _plugin_module()
        context = _Context({"output": "{}", "exit_code": 1})
        plugin.register(context)
        manifest = (PLUGIN / "plugin.yaml").read_text(encoding="utf-8")
        for name in ("one_c_observation_info", "one_c_observe", "one_c_expand_observation"):
            self.assertIn(f"- {name}", manifest)
            self.assertIn(name, context.tools)
        schema = next(item for item in sys.modules[plugin.__name__ + ".schemas"].TOOLS if item["name"] == "one_c_observe")
        self.assertEqual(set(schema["parameters"]["properties"]), {"start", "end", "events", "filters", "limit"})
        filter_properties = schema["parameters"]["properties"]["filters"]["properties"]
        self.assertEqual(
            filter_properties["text"]["pattern"],
            "[^\\u0009-\\u000D\\u001C-\\u0020\\u0085\\u00A0\\u1680\\u2000-\\u200A\\u2028\\u2029\\u202F\\u205F\\u3000]",
        )
        self.assertEqual(filter_properties["sourceComponent"]["pattern"], r"^[A-Za-z0-9_.:-]{1,128}(?![\s\S])")
        self.assertEqual(filter_properties["process"]["pattern"], r"^[A-Za-z0-9_.:-]{1,128}(?![\s\S])")
        self.assertIsNone(re.search(filter_properties["text"]["pattern"], " "))
        self.assertIsNone(re.search(filter_properties["text"]["pattern"], "\u0085"))
        self.assertIsNotNone(re.search(filter_properties["text"]["pattern"], "\ufeff"))
        self.assertIsNone(re.search(filter_properties["sourceComponent"]["pattern"], "abc\n"))
        self.assertIsNone(re.search(filter_properties["process"]["pattern"], "a" * 128 + "\n"))
        expand_schema = next(item for item in sys.modules[plugin.__name__ + ".schemas"].TOOLS if item["name"] == "one_c_expand_observation")
        self.assertEqual(len(expand_schema["parameters"]["oneOf"]), 3)

    def test_registration_log_tools_have_closed_bounded_schemas_and_dispatch_operations(self) -> None:
        plugin = _plugin_module()
        result = {
            "artifactId": _artifact_id(), "capabilityVersion": "0.3.0",
            "schemaVersion": 1, "operation": "eventlog_select", "status": "ok",
            "selectionRef": "eventlog:abc", "records": [], "recordsTruncated": False,
            "summary": {"coverage": {"complete": True, "partial": False}},
            "snapshot": {"stable": True},
        }
        context = _Context({"output": json.dumps(result) + "\n", "exit_code": 0})
        plugin.register(context)
        schemas = {item["name"]: item for item in sys.modules[plugin.__name__ + ".schemas"].TOOLS}
        select_schema = schemas["one_c_select_registration_log"]["parameters"]
        self.assertEqual(select_schema["additionalProperties"], False)
        self.assertEqual(select_schema["properties"]["maximumCount"]["maximum"], 100)
        self.assertEqual(select_schema["properties"]["limit"]["maximum"], 20)
        self.assertEqual(set(select_schema["properties"]["filters"]["properties"]), {"event", "level", "user", "metadata"})
        page_schema = schemas["one_c_page_registration_log"]["parameters"]
        self.assertIn("filters", page_schema["properties"])
        self.assertNotIn("filters", page_schema["required"])
        record_schema = schemas["one_c_read_registration_log_record"]["parameters"]
        self.assertEqual(len(record_schema["oneOf"]), 2)
        continuation = record_schema["oneOf"][1]
        self.assertEqual(
            set(continuation["required"]),
            {"recordRef", "commentOffset", "commentMaxBytes"},
        )
        self.assertEqual(continuation["properties"]["commentMaxBytes"]["maximum"], 16384)

        response = json.loads(context.tools["one_c_select_registration_log"]({
            "start": "2026-09-22T06:44:00", "end": "2026-09-22T06:45:00",
            "filters": {}, "maximumCount": 100, "limit": 20,
        }))
        encoded = context.calls[-1][1]["command"].rsplit(" ", 1)[1]
        payload = json.loads(base64.b64decode(encoded))
        self.assertEqual(payload["operation"], "eventlog_select")
        self.assertEqual(response["selectionRef"], "eventlog:abc")

    def test_registration_log_compaction_preserves_scope_and_partial_coverage(self) -> None:
        plugin = _plugin_module()
        common = {
            "level": "Information", "event": "_$Session$_.Start",
            "user": {"name": "alice", "presentation": "Alice"},
            "metadata": {"name": None, "presentation": None}, "transactionStatus": "NotApplicable",
        }
        result = {
            "artifactId": _artifact_id(), "capabilityVersion": "0.3.0", "schemaVersion": 1,
            "operation": "eventlog_page", "status": "partial", "selectionRef": "eventlog:abc",
            "offset": 0, "total": 2, "truncated": False,
            "summary": {
                "source": "1c_registration_log", "window": {"start": "a", "end": "b", "sourceTimeZone": "UTC"},
                "filters": {"event": "_$Session$_.Start"}, "baseSelectionRef": "eventlog:abc",
                "recordCount": 2, "countScope": "refinedRetainedSelection",
                "coverage": {"complete": False, "partial": True, "reasonCode": "maximum_count_boundary", "limitedToRetainedSelection": True},
            },
            "coverage": {"complete": False, "partial": True, "reasonCode": "maximum_count_boundary", "limitedToRetainedSelection": True},
            "records": [
                {**common, "occurredAt": "2026-09-22T09:00:00", "recordRef": "eventlog:abc:record:0:x", "selectionIndex": 0, "eventPresentation": "Start"},
                {**common, "occurredAt": "2026-09-22T09:00:01", "recordRef": "eventlog:abc:record:1:y", "selectionIndex": 1, "eventPresentation": "Start"},
            ],
            "snapshot": {"stable": True},
        }
        context = _Context({"output": json.dumps(result) + "\n", "exit_code": 0})
        plugin.register(context)

        response = json.loads(context.tools["one_c_page_registration_log"]({
            "selectionRef": "eventlog:abc", "offset": 0, "limit": 20,
            "filters": {"event": "_$Session$_.Start"},
        }))

        self.assertNotIn("artifactId", response)
        self.assertNotIn("operation", response)
        self.assertEqual(response["status"], "partial")
        self.assertFalse(response["coverage"]["complete"])
        self.assertEqual(response["summary"]["countScope"], "refinedRetainedSelection")
        self.assertEqual(response["recordCommon"]["event"], "_$Session$_.Start")
        self.assertNotIn("event", response["records"][0])
        self.assertIn("recordRef", response["records"][0])

    def test_open_dispatches_only_the_public_terminal_tool_and_checks_version(self) -> None:
        plugin = _plugin_module()
        result = {
            "artifactId": _artifact_id(),
            "capabilityVersion": "0.3.0", "status": "ok", "operation": "open",
            "snapshotRef": {"schemaVersion": 1, "status": "ready"},
        }
        context = _Context({"output": json.dumps(result) + "\n", "exit_code": 0})
        plugin.register(context)

        response = json.loads(context.tools["one_c_open"]({}))

        self.assertEqual(response, result)
        self.assertEqual(context.calls[0][0], "terminal")
        command = context.calls[0][1]["command"]
        self.assertTrue(command.startswith('"$HERMES_HOME/bin/one-c-harness" --request-base64 '))
        encoded = command.rsplit(" ", 1)[1]
        payload = json.loads(base64.b64decode(encoded))
        self.assertEqual(payload, {"schemaVersion": 1, "operation": "open", "arguments": {}})
        self.assertNotIn("ssh", command.lower())
        self.assertNotIn("known_hosts", command.lower())

    def test_successful_complete_observation_moves_only_exact_group_common_fields(self) -> None:
        plugin = _plugin_module()
        first_ref = "snapshot:selection:group:EXCP:first"
        second_ref = "snapshot:selection:group:EXCP:second"
        result = {
            "artifactId": _artifact_id(),
            "capabilityVersion": "0.3.0",
            "schemaVersion": 1,
            "operation": "observe",
            "status": "ok",
            "groups": [
                {
                    "event": "EXCP", "countScope": "retainedFilteredSelection",
                    "errorSignature": "hmac-sha256:first", "ref": first_ref,
                    "summary": {"meaning": "File not found"}, "count": 2,
                },
                {
                    "event": "EXCP", "countScope": "retainedFilteredSelection",
                    "errorSignature": "hmac-sha256:second", "ref": second_ref,
                    "summary": {"meaning": "File not found"}, "count": 1,
                },
            ],
            "groupsTruncated": True,
            "observationRef": "snapshot:selection",
            "snapshot": {"partial": False, "stable": True, "expiresInSeconds": 3600},
            "summary": {
                "source": "1c_techlog",
                "window": {"start": "2026-09-18T15:25:00+00:00", "end": "2026-09-18T15:26:00+00:00", "sourceTimeZone": "UTC"},
                "filters": {"events": ["EXCP"]},
                "countScope": "retainedFilteredSelection",
                "recordCount": 3,
                "coverage": {"partial": False, "filesRead": 3, "bytesRead": 47170, "recordLimit": 200},
            },
        }
        context = _Context({"output": json.dumps(result) + "\n", "exit_code": 0})
        plugin.register(context)

        response = json.loads(context.tools["one_c_observe"]({
            "start": "2026-09-18T15:25:00", "end": "2026-09-18T15:26:00",
            "events": ["EXCP"], "limit": 2,
        }))

        self.assertEqual(response["status"], "ok")
        self.assertNotIn("artifactId", response)
        self.assertNotIn("capabilityVersion", response)
        self.assertNotIn("schemaVersion", response)
        self.assertNotIn("operation", response)
        self.assertEqual(response["groupCommon"], {
            "event": "EXCP", "countScope": "retainedFilteredSelection",
            "summary": {"meaning": "File not found"},
        })
        self.assertEqual(response["groupCommonAppliesTo"], "every item in groups in this response")
        self.assertEqual([group["ref"] for group in response["groups"]], [first_ref, second_ref])
        self.assertEqual(
            [group["errorSignature"] for group in response["groups"]],
            ["hmac-sha256:first", "hmac-sha256:second"],
        )
        self.assertEqual(
            [_restore_common(response["groupCommon"], group) for group in response["groups"]],
            result["groups"],
        )
        self.assertTrue(response["groupsTruncated"])
        self.assertEqual(response["summary"], result["summary"])

    def test_successful_complete_record_page_preserves_precise_time_and_distinct_fields(self) -> None:
        plugin = _plugin_module()
        result = {
            "artifactId": _artifact_id(), "capabilityVersion": "0.3.0",
            "schemaVersion": 1, "operation": "expand_observation", "status": "ok",
            "level": "group", "groupRef": "snapshot:selection:group:EXCP:one",
            "offset": 0, "total": 2, "truncated": False,
            "snapshot": {
                "stable": True,
                "coverage": {"partial": False, "filesRead": 3, "bytesRead": 47170},
                "window": {"start": "2026-09-18T15:25:00+00:00", "end": "2026-09-18T15:26:00+00:00", "sourceTimeZone": "UTC"},
            },
            "records": [
                {
                    "event": "EXCP", "occurredAt": "2026-09-18T15:25:27.123456+00:00",
                    "sourceTimeToken": "25:27.123456789", "recordId": "techlog:first",
                    "recordRef": "snapshot:selection:record:1:first", "selectionIndex": 1,
                    "errorSignature": "hmac-sha256:shared", "technical": {"process": "1cv8t"},
                    "error": {
                        "exceptionType": "FileError",
                        "description": {"fragment": "File not found", "fingerprint": "hmac-sha256:first", "redacted": True, "truncated": False, "status": "projected"},
                    },
                },
                {
                    "event": "EXCP", "occurredAt": "2026-09-18T15:25:27.123457+00:00",
                    "sourceTimeToken": "25:27.123457001", "recordId": "techlog:second",
                    "recordRef": "snapshot:selection:record:2:second", "selectionIndex": 2,
                    "errorSignature": "hmac-sha256:shared", "technical": {"process": "1cv8t"},
                    "error": {
                        "exceptionType": "FileError",
                        "description": {"fragment": "File not found", "fingerprint": "hmac-sha256:second", "redacted": True, "truncated": False, "status": "projected"},
                    },
                },
            ],
        }
        context = _Context({"output": json.dumps(result) + "\n", "exit_code": 0})
        plugin.register(context)

        response = json.loads(context.tools["one_c_expand_observation"]({
            "groupRef": result["groupRef"], "offset": 0, "limit": 2,
        }))

        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["recordCommon"], {
            "event": "EXCP", "errorSignature": "hmac-sha256:shared",
            "technical": {"process": "1cv8t"},
            "error": {
                "exceptionType": "FileError",
                "description": {"fragment": "File not found", "redacted": True, "truncated": False, "status": "projected"},
            },
        })
        self.assertEqual(response["recordCommonAppliesTo"], "every item in records in this response")
        self.assertEqual(
            [record["sourceTimeToken"] for record in response["records"]],
            ["25:27.123456789", "25:27.123457001"],
        )
        self.assertEqual(
            [record["error"]["description"]["fingerprint"] for record in response["records"]],
            ["hmac-sha256:first", "hmac-sha256:second"],
        )
        self.assertEqual(
            [record["recordRef"] for record in response["records"]],
            ["snapshot:selection:record:1:first", "snapshot:selection:record:2:second"],
        )
        self.assertEqual(
            [_restore_common(response["recordCommon"], record) for record in response["records"]],
            result["records"],
        )

    def test_exact_record_compacts_only_fields_common_to_record_and_neighbors(self) -> None:
        plugin = _plugin_module()
        shared = {
            "event": "EXCP", "technical": {"process": "1cv8t"},
            "error": {"exceptionType": "FileError", "description": {"fragment": "File not found", "redacted": True, "truncated": False, "status": "projected"}},
        }
        def record(index: int, signature: str) -> dict[str, object]:
            value = copy.deepcopy(shared)
            value.update({
                "occurredAt": f"2026-09-18T15:25:27.00000{index}+00:00",
                "sourceTimeToken": f"25:27.00000{index}123",
                "recordId": f"techlog:{index}",
                "recordRef": f"snapshot:selection:record:{index}:token",
                "selectionIndex": index,
                "errorSignature": signature,
            })
            return value
        target = record(2, "hmac-sha256:target")
        result = {
            "artifactId": _artifact_id(), "capabilityVersion": "0.3.0",
            "schemaVersion": 1, "operation": "expand_observation", "status": "ok",
            "level": "record", "recordRef": target["recordRef"],
            "before": [record(1, "hmac-sha256:before")], "record": target,
            "after": [record(3, "hmac-sha256:after")],
            "scope": "retainedFilteredSelection",
            "relation": "time adjacency only; no causal relationship is implied",
            "snapshot": {"stable": True, "coverage": {"partial": False}, "window": {"sourceTimeZone": "UTC"}},
        }
        context = _Context({"output": json.dumps(result) + "\n", "exit_code": 0})
        plugin.register(context)

        response = json.loads(context.tools["one_c_expand_observation"]({
            "recordRef": target["recordRef"], "before": 1, "after": 1,
        }))

        self.assertEqual(response["recordCommon"]["event"], "EXCP")
        self.assertEqual(response["recordCommon"]["technical"], {"process": "1cv8t"})
        self.assertNotIn("errorSignature", response["recordCommon"])
        self.assertEqual(
            response["recordCommonAppliesTo"],
            "every item in before, record and after in this response",
        )
        self.assertEqual(response["record"]["recordRef"], target["recordRef"])
        self.assertEqual(response["record"]["sourceTimeToken"], "25:27.000002123")
        self.assertEqual(response["before"][0]["errorSignature"], "hmac-sha256:before")
        self.assertEqual(response["after"][0]["errorSignature"], "hmac-sha256:after")
        self.assertEqual(
            [_restore_common(response["recordCommon"], item) for item in response["before"]],
            result["before"],
        )
        self.assertEqual(_restore_common(response["recordCommon"], response["record"]), result["record"])
        self.assertEqual(
            [_restore_common(response["recordCommon"], item) for item in response["after"]],
            result["after"],
        )
        self.assertEqual(response["scope"], "retainedFilteredSelection")
        self.assertEqual(response["relation"], "time adjacency only; no causal relationship is implied")

    def test_incomplete_and_blocked_diagnostic_responses_are_not_compacted(self) -> None:
        plugin = _plugin_module()
        cases = [
            {
                "artifactId": _artifact_id(), "capabilityVersion": "0.3.0", "schemaVersion": 1,
                "operation": "observe", "status": "ok", "groups": [], "groupsTruncated": False,
                "observationRef": "snapshot:partial", "snapshot": {"partial": True, "stable": True},
                "summary": {"coverage": {"partial": True, "reasonCode": "file_budget"}},
            },
            {
                "artifactId": _artifact_id(), "capabilityVersion": "0.3.0", "schemaVersion": 1,
                "operation": "observe", "status": "blocked", "reasonCode": "invalid_request",
                "message": "calendar interval is invalid for the configured source timezone",
            },
        ]
        for result in cases:
            with self.subTest(status=result["status"]):
                context = _Context({"output": json.dumps(result) + "\n", "exit_code": 0})
                plugin.register(context)
                response = json.loads(context.tools["one_c_observe"]({
                    "start": "2026-09-18T15:25:00", "end": "2026-09-18T15:26:00",
                    "events": ["EXCP"], "limit": 2,
                }))
                self.assertEqual(response, result)

    def test_empty_complete_page_has_no_invented_common_fields(self) -> None:
        plugin = _plugin_module()
        result = {
            "artifactId": _artifact_id(), "capabilityVersion": "0.3.0", "schemaVersion": 1,
            "operation": "expand_observation", "status": "ok", "level": "observation",
            "observationRef": "snapshot:empty", "offset": 0, "total": 0, "truncated": False,
            "groups": [], "snapshot": {"stable": True, "coverage": {"partial": False}, "window": {"sourceTimeZone": "UTC"}},
        }
        context = _Context({"output": json.dumps(result) + "\n", "exit_code": 0})
        plugin.register(context)

        response = json.loads(context.tools["one_c_expand_observation"]({
            "observationRef": "snapshot:empty", "offset": 0, "limit": 2,
        }))

        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["groups"], [])
        self.assertNotIn("groupCommon", response)
        self.assertNotIn("groupCommonAppliesTo", response)
        self.assertTrue(response["snapshot"]["stable"])
        self.assertFalse(response["snapshot"]["coverage"]["partial"])

    def test_heterogeneous_groups_reconstruct_without_treating_missing_as_common(self) -> None:
        plugin = _plugin_module()
        groups = [
            {"event": "EXCP", "countScope": "retainedFilteredSelection", "errorSignature": "one", "ref": "group:one", "summary": {"meaning": "same"}},
            {"event": "EXCPCNTX", "errorSignature": "two", "ref": "group:two", "summary": {"meaning": "same"}},
        ]
        result = {
            "artifactId": _artifact_id(), "capabilityVersion": "0.3.0", "schemaVersion": 1,
            "operation": "observe", "status": "ok", "groups": groups,
            "groupsTruncated": False, "observationRef": "snapshot:mixed",
            "snapshot": {"partial": False, "stable": True},
            "summary": {"source": "1c_techlog", "coverage": {"partial": False}, "filters": {"events": ["EXCP", "EXCPCNTX"]}},
        }
        context = _Context({"output": json.dumps(result) + "\n", "exit_code": 0})
        plugin.register(context)

        response = json.loads(context.tools["one_c_observe"]({
            "start": "2026-09-18T15:25:00", "end": "2026-09-18T15:26:00",
            "events": ["EXCP", "EXCPCNTX"], "limit": 2,
        }))
        reconstructed = [
            _restore_common(response.get("groupCommon", {}), item)
            for item in response["groups"]
        ]

        self.assertEqual(reconstructed, groups)
        self.assertNotIn("event", response.get("groupCommon", {}))
        self.assertNotIn("countScope", response.get("groupCommon", {}))
        self.assertEqual([item["ref"] for item in response["groups"]], ["group:one", "group:two"])

    def test_unknown_success_shape_is_returned_unchanged(self) -> None:
        plugin = _plugin_module()
        result = {
            "artifactId": _artifact_id(), "capabilityVersion": "0.3.0",
            "schemaVersion": 1, "operation": "observe", "status": "ok",
            "futureShape": {"value": 1},
        }
        context = _Context({"output": json.dumps(result) + "\n", "exit_code": 0})
        plugin.register(context)

        response = json.loads(context.tools["one_c_observe"]({
            "start": "2026-09-18T15:25:00", "end": "2026-09-18T15:26:00",
            "events": ["EXCP"], "limit": 2,
        }))

        self.assertEqual(response, result)

    def test_handler_rejects_undeclared_arguments_without_terminal_dispatch(self) -> None:
        plugin = _plugin_module()
        context = _Context({"output": "{}", "exit_code": 1})
        plugin.register(context)

        response = json.loads(context.tools["one_c_open"]({"workspace": "/wrong"}))

        self.assertEqual(response["status"], "blocked")
        self.assertEqual(response["reasonCode"], "invalid_request")
        self.assertEqual(context.calls, [])

    def test_shell_metacharacters_are_transport_data_not_terminal_syntax(self) -> None:
        plugin = _plugin_module()
        result = {
            "artifactId": _artifact_id(),
            "capabilityVersion": "0.3.0", "status": "blocked", "reasonCode": "snapshot_invalid",
        }
        context = _Context({"output": json.dumps(result) + "\n", "exit_code": 0})
        plugin.register(context)
        hostile = "$(touch pwned); 'quoted'\nnext"

        response = json.loads(context.tools["one_c_narrow_context"]({
            "snapshotRef": {"token": hostile}, "query": hostile,
        }))

        self.assertEqual(response, result)
        command = context.calls[0][1]["command"]
        self.assertTrue(command.startswith('"$HERMES_HOME/bin/one-c-harness" --request-base64 '))
        self.assertNotIn(hostile, command)
        self.assertNotIn("printf", command)
        self.assertTrue(all(character.isalnum() or character in '-_=+/. $"' for character in command))

    def test_same_version_with_different_companion_artifact_is_a_stable_blocker(self) -> None:
        plugin = _plugin_module()
        context = _Context({"output": json.dumps({
            "capabilityVersion": "0.3.0", "releaseId": "wrong-artifact", "status": "ok",
        }) + "\n", "exit_code": 0})
        plugin.register(context)

        response = json.loads(context.tools["one_c_open"]({}))

        self.assertEqual(response["status"], "blocked")
        self.assertEqual(response["reasonCode"], "companion_artifact_mismatch")

    def test_mismatched_companion_version_is_a_stable_blocker(self) -> None:
        plugin = _plugin_module()
        context = _Context({"output": json.dumps({"capabilityVersion": "9.9.9", "status": "ok"}), "exit_code": 0})
        plugin.register(context)

        response = json.loads(context.tools["one_c_open"]({}))

        self.assertEqual(response["status"], "blocked")
        self.assertEqual(response["reasonCode"], "companion_version_mismatch")


if __name__ == "__main__":
    unittest.main()
