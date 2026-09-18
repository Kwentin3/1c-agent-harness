from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path
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
    def test_registers_one_skill_and_three_closed_tools(self) -> None:
        plugin = _plugin_module()
        context = _Context({"output": "{}", "exit_code": 1})

        plugin.register(context)

        self.assertEqual(set(context.tools), {"one_c_open", "one_c_narrow_context", "one_c_native_verify"})
        self.assertIsNotNone(context.skill)
        assert context.skill is not None
        self.assertEqual(context.skill[0], "one-c-harness")
        self.assertTrue(context.skill[1].is_file())

    def test_open_dispatches_only_the_public_terminal_tool_and_checks_version(self) -> None:
        plugin = _plugin_module()
        result = {
            "artifactId": _artifact_id(),
            "capabilityVersion": "0.1.0", "status": "ok", "operation": "open",
            "snapshotRef": {"schemaVersion": 1, "status": "ready"},
        }
        context = _Context({"output": json.dumps(result) + "\n", "exit_code": 0})
        plugin.register(context)

        response = json.loads(context.tools["one_c_open"]({}))

        self.assertEqual(response, result)
        self.assertEqual(context.calls[0][0], "terminal")
        command = context.calls[0][1]["command"]
        self.assertIn("one-c-harness --request-base64", command)
        encoded = command.rsplit(" ", 1)[1]
        payload = json.loads(base64.b64decode(encoded))
        self.assertEqual(payload, {"schemaVersion": 1, "operation": "open", "arguments": {}})
        self.assertNotIn("ssh", command.lower())
        self.assertNotIn("known_hosts", command.lower())

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
            "capabilityVersion": "0.1.0", "status": "blocked", "reasonCode": "snapshot_invalid",
        }
        context = _Context({"output": json.dumps(result) + "\n", "exit_code": 0})
        plugin.register(context)
        hostile = "$(touch pwned); 'quoted'\nnext"

        response = json.loads(context.tools["one_c_narrow_context"]({
            "snapshotRef": {"token": hostile}, "query": hostile,
        }))

        self.assertEqual(response, result)
        command = context.calls[0][1]["command"]
        self.assertIn("one-c-harness --request-base64", command)
        self.assertNotIn(hostile, command)
        self.assertNotIn("printf", command)
        self.assertTrue(all(character.isalnum() or character in "-_=+/ " for character in command))

    def test_same_version_with_different_companion_artifact_is_a_stable_blocker(self) -> None:
        plugin = _plugin_module()
        context = _Context({"output": json.dumps({
            "capabilityVersion": "0.1.0", "releaseId": "wrong-artifact", "status": "ok",
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
