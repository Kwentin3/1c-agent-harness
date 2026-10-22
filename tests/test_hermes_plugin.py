from __future__ import annotations

import base64
import copy
import importlib.util
import hashlib
import json
from pathlib import Path
import re
import shlex
import sys
import unittest
from unittest.mock import patch

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
        self.prompt_sections = []

    def register_tool(self, **kwargs):
        self.tools[kwargs["name"]] = kwargs["handler"]

    def register_skill(self, name: str, path: Path, description: str):
        self.skill = (name, path, description)

    def register_system_prompt_section(self, *args, **kwargs):
        self.prompt_sections.append((args, kwargs))

    def dispatch_tool(self, name: str, args: dict[str, object]) -> str:
        self.calls.append((name, args))
        if name == 'write_file':
            return json.dumps({'verified': True, 'resolved_path': '/workspace/project/' + args['path']})
        return json.dumps(self.terminal_response)


class HermesPluginTests(unittest.TestCase):
    def test_coding_terminal_budget_covers_full_lifecycle_not_only_runtime(self) -> None:
        plugin = _plugin_module()
        context = _Context({"output": "{}", "exit_code": 0})
        plugin.register(context)
        context.tools["one_c_open"]({})
        self.assertEqual(context.calls[-1][1]["timeout"], 2160)
        for seconds in (1, 300, 480):
            with self.subTest(seconds=seconds):
                context.tools["one_c_native_verify"]({"timeoutSeconds": seconds})
                self.assertEqual(context.calls[-1][1]["timeout"], 2160)
                request = json.loads(base64.b64decode(context.calls[-1][1]["command"].rsplit(" ", 1)[1]))
                self.assertEqual(request["arguments"]["timeoutSeconds"], seconds)
        for seconds in (0, -1, 481, True, "300"):
            with self.subTest(invalid=seconds):
                before = len(context.calls)
                result = json.loads(context.tools["one_c_native_verify"]({"timeoutSeconds": seconds}))
                self.assertEqual(result["reasonCode"], "invalid_request")
                self.assertEqual(len(context.calls), before)
        context.tools["one_c_observation_info"]({})
        self.assertEqual(context.calls[-1][1]["timeout"], 60)
        context.tools["one_c_narrow_context"]({})
        self.assertEqual(context.calls[-1][1]["timeout"], 90)

    def test_release_artifact_binds_companion_plugin_and_skill_closure(self) -> None:
        paths = []
        for pattern in ("one_c_harness/*.py", "hermes-plugin/*.py"):
            paths.extend(ROOT.glob(pattern))
        for pattern in ("one_c_harness/eventlog_epf/**/*", "one_c_harness/logging_epf/**/*"):
            paths.extend(path for path in ROOT.glob(pattern) if path.is_file())
        paths += [ROOT / 'deployment/goal91' / name for name in (
            'current-journal.py', 'current-harness-client.py', 'current-capture-client.py',
            'current-logging-client.py', 'current-logging.json')]
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

    def test_registers_one_skill_and_eleven_closed_tools(self) -> None:
        plugin = _plugin_module()
        context = _Context({"output": "{}", "exit_code": 1})

        plugin.register(context)

        self.assertEqual(set(context.tools), {"one_c_open", "one_c_narrow_context", "one_c_native_verify", "one_c_observation_info", "one_c_logging", "one_c_observe", "one_c_expand_observation", "one_c_select_registration_log", "one_c_page_registration_log", "one_c_read_registration_log_record", "one_c_stage_task"})
        manifest = (PLUGIN / "plugin.yaml").read_text(encoding="utf-8")
        declared = re.findall(r"^  - (one_c_\w+)$", manifest, re.MULTILINE)
        self.assertEqual(len(declared), 11)
        self.assertEqual(set(declared), set(context.tools))
        self.assertIsNotNone(context.skill)
        assert context.skill is not None
        self.assertEqual(context.skill[0], "one-c-harness")
        self.assertTrue(context.skill[1].is_file())
        self.assertEqual(len(context.prompt_sections), 1)
        args, options = context.prompt_sections[0]
        self.assertLessEqual(len(args[1]), options['max_chars'],
            'Hermes drops an oversized section rather than truncating it')
        self.assertIn('one-c-harness:one-c-harness', args[1])
        self.assertIn('one_c_open first for configuration work', args[1])
        self.assertEqual(options['max_chars'], 1000)
        self.assertIn('one_c_stage_task stages data only', args[1])
        self.assertIn('workcopy/apply/freeze/native/discard', args[1])
        self.assertIn('existing read-only experiments/<single-task>/oracle.py', args[1])

    def test_stage_task_schema_is_closed_and_keeps_byte_validation_with_owner(self) -> None:
        plugin = _plugin_module()
        schemas = {tool['name']: tool['parameters'] for tool in sys.modules[plugin.__name__ + '.schemas'].TOOLS}
        schema = schemas['one_c_stage_task']
        fields = {'snapshotRef', 'request', 'productionPatch', 'instrumentationPatch', 'oracle'}
        self.assertEqual(schema['type'], 'object')
        self.assertFalse(schema['additionalProperties'])
        self.assertEqual(set(schema['required']), fields)
        self.assertEqual(set(schema['properties']), fields)
        self.assertEqual(schema['properties']['request']['type'], 'object')
        for name in ('productionPatch', 'instrumentationPatch'):
            self.assertEqual(schema['properties'][name]['type'], 'string')
            self.assertEqual(schema['properties'][name]['minLength'], 1)
            self.assertNotIn('maxLength', schema['properties'][name], 'UTF-8 byte limits belong to the companion')
        pattern = schema['properties']['oracle']['pattern']
        self.assertIsNotNone(re.search(pattern, 'experiments/synthetic-task/oracle.py'))
        for invalid in ('oracle.py', '/experiments/task/oracle.py', 'experiments/../oracle.py',
                        'experiments/./oracle.py', 'experiments/a/b/oracle.py',
                        'experiments/a\\b/oracle.py', 'experiments/a:task/oracle.py',
                        'experiments/task/oracle.py\n', 'print("inline oracle")'):
            with self.subTest(invalid=invalid):
                self.assertIsNone(re.search(pattern, invalid))

    def test_native_verify_has_two_closed_forms_and_canonical_task_ref(self) -> None:
        plugin = _plugin_module()
        schema = next(tool['parameters'] for tool in sys.modules[plugin.__name__ + '.schemas'].TOOLS
                      if tool['name'] == 'one_c_native_verify')
        self.assertEqual(schema['type'], 'object')
        self.assertEqual(len(schema['oneOf']), 2)
        legacy, staged = schema['oneOf']
        old_fields = {'snapshotRef', 'request', 'productionPatch', 'instrumentationPatch', 'oracle', 'receipt', 'timeoutSeconds'}
        new_fields = {'snapshotRef', 'taskRef', 'timeoutSeconds'}
        for form, fields in ((legacy, old_fields), (staged, new_fields)):
            self.assertFalse(form['additionalProperties'])
            self.assertEqual(set(form['properties']), fields)
            self.assertEqual(set(form['required']), fields)
            self.assertEqual(form['properties']['timeoutSeconds'], {'type': 'integer', 'minimum': 1, 'maximum': 480})
        # A mixed request cannot match either closed branch; no caller paths in taskRef form.
        for keys, expected_matches in ((old_fields, 1), (new_fields, 1),
                                       (old_fields | new_fields, 0), (new_fields - {'taskRef'}, 0),
                                       (new_fields | {'receipt'}, 0)):
            matches = sum(set(form['required']) <= keys <= set(form['properties']) for form in schema['oneOf'])
            self.assertEqual(matches, expected_matches)
        ref = staged['properties']['taskRef']
        self.assertEqual(ref['type'], 'object')
        self.assertFalse(ref['additionalProperties'])
        self.assertEqual(set(ref['required']), {'schemaVersion', 'taskId', 'manifestSha256'})
        self.assertEqual(set(ref['properties']), set(ref['required']))
        self.assertEqual(ref['properties']['schemaVersion'], {'type': 'integer', 'const': 1})
        uuid_pattern = ref['properties']['taskId']['pattern']
        valid_id = 'b4a514b2-84af-4d19-a06b-f33dcc0e6176'
        self.assertIsNotNone(re.search(uuid_pattern, valid_id))
        for invalid in (valid_id.upper(), valid_id + '\n', valid_id.replace('-4d19-', '-1d19-'),
                        valid_id.replace('-a06b-', '-706b-'), valid_id.replace('-', '')):
            self.assertIsNone(re.search(uuid_pattern, invalid))
        digest_pattern = ref['properties']['manifestSha256']['pattern']
        self.assertIsNotNone(re.search(digest_pattern, 'a' * 64))
        for invalid in ('A' * 64, 'a' * 63, 'g' * 64, 'a' * 64 + '\n', 'sha256:' + 'a' * 64):
            self.assertIsNone(re.search(digest_pattern, invalid))

    def test_stage_task_returns_owner_task_ref_without_claiming_verification(self) -> None:
        plugin = _plugin_module()
        task_ref = {'schemaVersion': 1, 'taskId': 'b4a514b2-84af-4d19-a06b-f33dcc0e6176', 'manifestSha256': 'a' * 64}
        response = {'artifactId': _artifact_id(), 'capabilityVersion': '0.3.0', 'schemaVersion': 1,
                    'operation': 'stage_task', 'status': 'ok', 'taskRef': task_ref}
        context = _Context({'output': json.dumps(response) + '\n', 'exit_code': 0})
        plugin.register(context)
        arguments = {'snapshotRef': {'schemaVersion': 1, 'token': 'synthetic'}, 'request': {},
                     'productionPatch': 'production data', 'instrumentationPatch': 'instrumentation data',
                     'oracle': 'experiments/synthetic-task/oracle.py'}
        actual = json.loads(context.tools['one_c_stage_task'](arguments))
        self.assertEqual(actual, response)
        self.assertEqual(actual['taskRef'], task_ref)
        self.assertNotIn('receipt', actual)
        self.assertNotIn('verified', actual)

    def test_stage_task_passes_data_and_owner_refusal_through_terminal(self) -> None:
        plugin = _plugin_module()
        response = {'artifactId': _artifact_id(), 'capabilityVersion': '0.3.0', 'schemaVersion': 1,
                    'operation': 'stage_task', 'status': 'blocked', 'reasonCode': 'synthetic_owner_refusal'}
        context = _Context({'output': json.dumps(response) + '\n', 'exit_code': 0})
        plugin.register(context)
        patch_data = '\u044f' * 2049 + '\n$(never execute); quoted'
        arguments = {'snapshotRef': {'schemaVersion': 1, 'token': 'synthetic'},
                     'request': {'nested': {'businessValue': '\u0434\u0430\u043d\u043d\u044b\u0435'}},
                     'productionPatch': patch_data, 'instrumentationPatch': 'instrumentation data',
                     'oracle': 'experiments/synthetic-task/oracle.py'}
        self.assertGreater(len(patch_data.encode('utf-8')), 4096)
        actual = json.loads(context.tools['one_c_stage_task'](arguments))
        self.assertEqual(actual, response)
        self.assertEqual(len(context.calls), 2)
        write_name, written = context.calls[0]
        self.assertEqual(write_name, 'write_file')
        self.assertRegex(written['path'], r'\A\.one-c-harness-transport/[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\.json\Z')
        wire = written['content'].encode('utf-8')
        self.assertNotIn('\n', written['content'])
        self.assertEqual(json.loads(wire), {'schemaVersion': 1, 'operation': 'stage_task', 'arguments': arguments})
        name, dispatched = context.calls[1]
        self.assertEqual(name, 'terminal')
        self.assertEqual(dispatched['timeout'], 60)
        self.assertEqual(shlex.split(dispatched['command']), [
            '$HERMES_HOME/bin/one-c-harness', '--request-file', '/workspace/project/' + written['path'],
            '--sha256', hashlib.sha256(wire).hexdigest(),
        ])
        self.assertLess(len(dispatched['command']), 250)
        self.assertNotIn('never execute', dispatched['command'])
        self.assertNotIn(base64.b64encode(wire).decode(), dispatched['command'])

    def test_stage_file_write_failures_are_safe_and_never_dispatch_terminal(self) -> None:
        plugin = _plugin_module()
        for raw in ('not-json private detail', '[]', '{"verified":false}', '{"verified":1}',
                    '{"verified":true,"error":"private detail"}', '{"verified":true}'):
            with self.subTest(raw=raw):
                context = _Context({})
                plugin.register(context)
                with patch.object(context, 'dispatch_tool', return_value=raw) as dispatch:
                    result = json.loads(context.tools['one_c_stage_task']({'productionPatch': 'private detail'}))
                self.assertEqual(result['reasonCode'], 'request_file_failed')
                self.assertNotIn('private detail', json.dumps(result))
                self.assertEqual(dispatch.call_count, 1)
                self.assertEqual(dispatch.call_args.args[0], 'write_file')
        context = _Context({})
        plugin.register(context)
        with patch.object(context, 'dispatch_tool', side_effect=RuntimeError('private detail')) as dispatch:
            result = json.loads(context.tools['one_c_stage_task']({}))
        self.assertEqual(result['reasonCode'], 'request_file_failed')
        self.assertNotIn('private detail', json.dumps(result))
        self.assertEqual(dispatch.call_count, 1)

    def test_stage_rejects_misbound_or_unsafe_resolved_path(self) -> None:
        plugin = _plugin_module()
        for prefix, suffix in (('', ''), ('/workspace/../', ''), ('//workspace/', ''),
                               ('/workspace/./', ''), ('/workspace/\n', ''), ('/workspace/\\', ''),
                               ('/' + 'x' * 512 + '/', ''), ('/workspace/', '.extra'),
                               ('/workspace/foreign/', '/other.json')):
            with self.subTest(prefix=prefix, suffix=suffix):
                context = _Context({})
                plugin.register(context)
                def dispatch(name, args):
                    self.assertEqual(name, 'write_file')
                    return json.dumps({'verified': True, 'resolved_path': prefix + args['path'] + suffix})
                with patch.object(context, 'dispatch_tool', side_effect=dispatch) as called:
                    result = json.loads(context.tools['one_c_stage_task']({}))
                self.assertEqual(result['reasonCode'], 'request_file_failed')
                self.assertEqual(called.call_count, 1)

    def test_stage_transport_caps_complete_utf8_wire_before_file_write(self) -> None:
        plugin = _plugin_module()
        adapter = sys.modules[plugin.__name__ + '.adapter']
        response = {'artifactId': _artifact_id(), 'capabilityVersion': '0.3.0', 'status': 'ok'}
        arguments = {'productionPatch': ''}
        budget = 16384 - len(adapter._request('stage_task', arguments))
        arguments['productionPatch'] = '\u044f' * (budget // 2) + 'x' * (budget % 2)
        self.assertEqual(len(adapter._request('stage_task', arguments)), 16384)
        context = _Context({'output': json.dumps(response), 'exit_code': 0})
        plugin.register(context)
        self.assertEqual(json.loads(context.tools['one_c_stage_task'](arguments)), response)
        self.assertEqual([name for name, _ in context.calls], ['write_file', 'terminal'])
        context.calls.clear()
        arguments['productionPatch'] += 'x'
        result = json.loads(context.tools['one_c_stage_task'](arguments))
        self.assertEqual(result['reasonCode'], 'invalid_request')
        self.assertEqual(context.calls, [])

    def test_native_verify_forwards_both_argument_forms_without_rewriting_refs(self) -> None:
        plugin = _plugin_module()
        response = {'artifactId': _artifact_id(), 'capabilityVersion': '0.3.0',
                    'operation': 'verify', 'status': 'ok', 'receipt': {'synthetic': True}}
        task_ref = {'schemaVersion': 1, 'taskId': 'b4a514b2-84af-4d19-a06b-f33dcc0e6176', 'manifestSha256': 'a' * 64}
        common = {'snapshotRef': {'schemaVersion': 1, 'token': 'synthetic'}, 'timeoutSeconds': 300}
        for arguments in (dict(common, taskRef=task_ref), dict(common, request='experiments/task/request.json',
                          productionPatch='experiments/task/production.patch', instrumentationPatch='experiments/task/instrumentation.patch',
                          oracle='experiments/task/oracle.py', receipt='.local/task/receipt.json')):
            with self.subTest(fields=sorted(arguments)):
                context = _Context({'output': json.dumps(response) + '\n', 'exit_code': 0})
                plugin.register(context)
                self.assertEqual(json.loads(context.tools['one_c_native_verify'](arguments)), response)
                self.assertEqual(context.calls[0][0], 'terminal')
                self.assertEqual(context.calls[0][1]['timeout'], 2160)
                payload = json.loads(base64.b64decode(context.calls[0][1]['command'].rsplit(' ', 1)[1]))
                self.assertEqual(payload, {'schemaVersion': 1, 'operation': 'verify', 'arguments': arguments})

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
        self.assertEqual(continuation["properties"]["commentMaxBytes"]["minimum"], 4)

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
            "offset": 0, "total": 2, "truncated": True, "nextOffset": 1,
            "display": {
                "complete": False, "partial": True, "reasonCode": "response_byte_limit",
                "returnedCount": 1, "requestedLimit": 20, "nextOffset": 1,
            },
            "summary": {
                "source": "1c_registration_log", "window": {"start": "a", "end": "b", "sourceTimeZone": "UTC"},
                "filters": {"event": "_$Session$_.Start"}, "baseSelectionRef": "eventlog:abc",
                "recordCount": 2, "countScope": "refinedRetainedSelection",
                "coverage": {"complete": False, "partial": True, "reasonCode": "maximum_count_boundary", "limitedToRetainedSelection": True},
            },
            "coverage": {"complete": False, "partial": True, "reasonCode": "maximum_count_boundary", "limitedToRetainedSelection": True},
            "records": [
                {**common, "occurredAt": "2026-09-22T09:00:00", "recordRef": "eventlog:abc:record:0:x", "selectionIndex": 0, "eventPresentation": "Start"},
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
        self.assertEqual(response["display"]["reasonCode"], "response_byte_limit")
        self.assertEqual(response["nextOffset"], 1)
        self.assertEqual(response["records"][0]["event"], "_$Session$_.Start")
        self.assertIn("recordRef", response["records"][0])

    def test_narrow_context_preserves_line_endings_and_rejects_invalid_json_output(self) -> None:
        plugin = _plugin_module()
        result = {
            "artifactId": _artifact_id(), "capabilityVersion": "0.3.0",
            "schemaVersion": 1, "status": "ok", "truncated": False,
            "results": [{
                "fragment": "Procedure Posting(Cancel)", "fragmentTruncated": False,
                "line": 1, "lineEnding": "", "utf8Bom": True,
                "path": "Documents/Order/Ext/ObjectModule.bsl",
            }],
        }
        arguments = {"snapshotRef": {"token": "synthetic"}, "query": "Posting"}
        for line_ending in ("\u0085", "\u2028", "\u2029", "\n", "\r\n", ""):
            result["results"][0]["lineEnding"] = line_ending
            for terminal_ending in ("\n", "\r\n", ""):
                with self.subTest(lineEnding=repr(line_ending), terminalEnding=repr(terminal_ending)):
                    output = json.dumps(result, ensure_ascii=False) + terminal_ending
                    context = _Context({"output": output, "exit_code": 0})
                    plugin.register(context)
                    response = json.loads(context.tools["one_c_narrow_context"](arguments))
                    self.assertEqual(response, result, response)
        document = json.dumps(result, ensure_ascii=False)
        invalid_outputs = {
            "second_document": document + "\n" + document,
            "concatenated_documents": document + document,
            "prefix_noise": "noise " + document,
            "suffix_noise": document + " noise",
            "prefix_noise_line": "noise\n" + document,
            "suffix_noise_line": document + "\nnoise",
            "malformed_document": document[:-1],
        }
        for case, output in invalid_outputs.items():
            with self.subTest(invalid=case):
                context = _Context({"output": output, "exit_code": 0})
                plugin.register(context)
                response = json.loads(context.tools["one_c_narrow_context"](arguments))
                self.assertEqual(response["status"], "blocked")
                self.assertEqual(response["reasonCode"], "invalid_request")

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
