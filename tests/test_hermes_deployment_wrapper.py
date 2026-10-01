from __future__ import annotations

import base64
import json
import os
import shlex
import sys
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "hermes-plugin" / "deployment" / "one-c-harness"


class HermesDeploymentWrapperTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[dict[str, str], Path]:
        fake_bin = root / "bin"
        fake_bin.mkdir()
        capture = root / "ssh-argv"
        fake_ssh = fake_bin / "ssh"
        fake_ssh.write_text(
            "#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$SSH_ARGV_CAPTURE\"\nprintf '%s\\n' '{\"status\":\"ok\"}'\n",
            encoding="utf-8",
        )
        fake_ssh.chmod(0o700)

        home = root / "home"
        ssh_dir = home / ".ssh"
        ssh_dir.mkdir(parents=True)
        (ssh_dir / "known_hosts").write_text("fixture\n", encoding="utf-8")
        key = root / "executor-key"
        key.write_text("fixture\n", encoding="utf-8")

        env = {
            **os.environ,
            "HOME": str(home),
            "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}",
            "SSH_ARGV_CAPTURE": str(capture),
            "TERMINAL_SSH_HOST": "executor.example.invalid",
            "TERMINAL_SSH_USER": "executor",
            "TERMINAL_SSH_PORT": "2222",
            "TERMINAL_SSH_KEY": str(key),
        }
        return env, capture

    def test_coding_uses_deployment_project_binding_not_companion_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            env, capture = self._fixture(Path(temporary))
            env["ONE_C_HARNESS_PROJECT_CWD"] = "/workspace/business-task"
            token = base64.b64encode(json.dumps({
                "schemaVersion": 1, "operation": "open", "arguments": {},
            }).encode()).decode()
            result = subprocess.run(
                [str(WRAPPER), "--request-base64", token],
                capture_output=True, text=True, timeout=10, env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            command = capture.read_text().splitlines()[-1]
            self.assertTrue(command.startswith("cd /workspace/business-task && "), command)
            self.assertIn('sys.path.insert(0, "/workspace/1c-agent-harness/.local/issue80-companion/source")', command)
            self.assertIn("exec python3 -I -c ", command)
            self.assertTrue(command.endswith("--request-base64 " + token), command)

    def test_wrapper_uses_fixed_strict_openssh_route(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            env, capture = self._fixture(Path(temporary))
            token = "eyJvcGVyYXRpb24iOiJvYnNlcnZlIn0="

            result = subprocess.run(
                [str(WRAPPER), "--request-base64", token],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, '{"status":"ok"}\n')
            argv = capture.read_text(encoding="utf-8").splitlines()
            self.assertIn("BatchMode=yes", argv)
            self.assertIn("IdentitiesOnly=yes", argv)
            self.assertIn("StrictHostKeyChecking=yes", argv)
            self.assertIn(f"UserKnownHostsFile={Path(env['HOME']) / '.ssh' / 'known_hosts'}", argv)
            self.assertIn(env["TERMINAL_SSH_KEY"], argv)
            self.assertIn("2222", argv)
            self.assertIn("executor@executor.example.invalid", argv)
            self.assertEqual(
                argv[-1],
                "cd /workspace/1c-agent-harness/.local/issue80-companion/source "
                "&& ONE_C_HARNESS_RUNTIME_CONFIG=/workspace/1c-agent-harness/.local/one-c-runtime.json "
                "exec ../bin/one-c-harness --request-base64 " + token,
            )

    def test_business_binding_is_required_and_shell_safe_before_ssh(self) -> None:
        for binding in (None, "", "relative", "/workspace/../other", "/workspace/task;touch-pwned", "/workspace/task\nother", "/workspace/$(id)"):
            with self.subTest(binding=binding), tempfile.TemporaryDirectory() as temporary:
                env, capture = self._fixture(Path(temporary))
                env.pop("ONE_C_HARNESS_PROJECT_CWD", None)
                if binding is not None:
                    env["ONE_C_HARNESS_PROJECT_CWD"] = binding
                token = base64.b64encode(json.dumps({
                    "schemaVersion": 1, "operation": "open", "arguments": {},
                }).encode()).decode()
                result = subprocess.run(
                    [str(WRAPPER), "--request-base64", token],
                    capture_output=True, text=True, timeout=10, env=env,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(capture.exists())

    @unittest.skipUnless(sys.version_info >= (3, 11), "fixed deployment requires safe-path Python 3.11+")
    def test_source_route_open_narrow_verify_and_diagnostics_keep_distinct_roots(self) -> None:
        from tests.test_companion import _project

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            env, capture = self._fixture(root)
            business = root / "business"
            business.mkdir()
            _project(business)
            # Business files must not shadow the installed product namespace.
            shadow = business / "one_c_harness"
            shadow.mkdir()
            (shadow / "__init__.py").write_text("raise RuntimeError('project import shadow')\n")
            decoy = root / "vps-workspace"
            decoy.mkdir()
            source = root / "installed/source"
            source.mkdir(parents=True)
            (source / "one_c_harness").symlink_to(ROOT / "one_c_harness", target_is_directory=True)
            launcher = root / "installed/bin/one-c-harness"
            launcher.parent.mkdir()
            log_root = root / "techlog"
            log = log_root / "1cv8t_1/26091812.log"
            log.parent.mkdir(parents=True)
            log.write_text("00:00.000001-0,EXCP,1,process=1,Descr='fixture'\n")
            launcher.write_text(
                "#!/bin/sh\nset -eu\ncd " + shlex.quote(str(source)) + "\n"
                "export ONE_C_HARNESS_TECHLOG_ROOT=" + shlex.quote(str(log_root)) + "\n"
                "export ONE_C_HARNESS_TECHLOG_TIME_ZONE=UTC\n"
                "exec python3 -m one_c_harness.companion \"$@\"\n"
            )
            launcher.chmod(0o700)
            # Only the transport is substituted. Execute the real remote shell,
            # deployment wrapper, package CLI, admission and source search.
            (root / "bin/ssh").write_text(
                "#!" + sys.executable + "\n"
                "import os, subprocess, sys\n"
                "command = sys.argv[-1].replace('/workspace/1c-agent-harness/.local/issue80-companion/source', os.environ['TEST_REMOTE_SOURCE'])\n"
                "raise SystemExit(subprocess.call(command, shell=True))\n"
            )
            env["TEST_REMOTE_SOURCE"] = str(source)
            env["ONE_C_HARNESS_PROJECT_CWD"] = str(business)

            def call(operation: str, arguments: dict) -> dict:
                token = base64.b64encode(json.dumps({
                    "schemaVersion": 1, "operation": operation, "arguments": arguments,
                }).encode()).decode()
                result = subprocess.run(
                    [str(WRAPPER), "--request-base64", token], cwd=decoy,
                    capture_output=True, text=True, timeout=10, env=env,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(len(result.stdout.splitlines()), 1)
                return json.loads(result.stdout)

            opened = call("open", {})
            self.assertEqual(opened["status"], "ok", opened)
            reference = opened["snapshotRef"]
            warm = call("open", {})["snapshotRef"]
            self.assertEqual(warm["action"], "reused")
            self.assertEqual(warm["snapshot"], reference["snapshot"])
            narrowed = call("narrow", {"snapshotRef": reference, "query": "Procedure Posting"})
            self.assertEqual(narrowed["status"], "ok", narrowed)
            self.assertEqual(narrowed["results"][0]["path"], "Documents/Order/Ext/ObjectModule.bsl")
            rejected = call("verify", {
                "snapshotRef": {"path": "not-admitted"}, "request": "task/request.json",
                "productionPatch": "task/production.patch", "instrumentationPatch": "task/probe.patch",
                "oracle": "task/oracle.py", "receipt": ".local/receipt.json", "timeoutSeconds": 60,
            })
            self.assertEqual(rejected["reasonCode"], "snapshot_invalid")
            # Exercise the actual runner subprocess import, without 1C. An
            # incomplete fixture may block admission, but must reach the runner.
            request = business / ".local/request.json"
            request.write_text('{}')
            oracle = business / ".local/oracle.py"
            oracle.write_text('raise SystemExit(1)')
            for name, value in (("prod", "product"), ("probe", "instrumentation")):
                (business / (".local/" + name + ".patch")).write_text(
                    "diff --git a/Documents/Order/Ext/ObjectModule.bsl b/Documents/Order/Ext/ObjectModule.bsl\n"
                    "--- a/Documents/Order/Ext/ObjectModule.bsl\n"
                    "+++ b/Documents/Order/Ext/ObjectModule.bsl\n"
                    "@@ -1,2 +1,2 @@\n-" + ("Procedure Posting(Cancel)" if name == "prod" else "// product")
                    + "\n+// " + value + "\n EndProcedure\n"
                )
            runner_admission = call("verify", {
                "snapshotRef": reference, "request": ".local/request.json",
                "productionPatch": ".local/prod.patch", "instrumentationPatch": ".local/probe.patch",
                "oracle": ".local/oracle.py", "receipt": ".local/receipt.json", "timeoutSeconds": 1,
            })
            self.assertNotEqual(runner_admission["status"], "ok")
            # Result persisted by the unchanged runner proves its module loaded;
            # a native-cycle-failed envelope alone does not prove subprocess reach.
            results = list((business / ".local/runs/native-cycle").glob("run-*/**/result.json"))
            self.assertTrue(results, (runner_admission, [str(p.relative_to(business)) for p in business.rglob('*')]))
            self.assertIn('precheck_failed', {json.loads(p.read_text()).get('status') for p in results})
            observed = call("observe", {
                "start": "2026-09-18T12:00:00", "end": "2026-09-18T12:00:01", "events": ["EXCP"], "limit": 10,
            })
            self.assertEqual(observed["status"], "ok", observed)
            expanded = call("expand_observation", {
                "groupRef": observed["groups"][0]["ref"], "offset": 0, "limit": 10,
            })
            self.assertEqual(expanded["records"][0]["event"], "EXCP")
            self.assertTrue((business / ".local/targets").is_dir())
            self.assertFalse((source / ".local/targets").exists())
            self.assertFalse((business / ".local/runs/techlog-observations").exists())
            self.assertFalse((business / "scripts").exists())
            self.assertEqual(list(decoy.iterdir()), [])

    def test_wrapper_rejects_option_shaped_ssh_user_before_ssh(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            env, capture = self._fixture(Path(temporary))
            env["TERMINAL_SSH_USER"] = "-malicious"

            result = subprocess.run(
                [str(WRAPPER), "--request-base64", "e30="],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(capture.exists())

    def test_wrapper_rejects_shell_syntax_before_ssh(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            env, capture = self._fixture(Path(temporary))

            result = subprocess.run(
                [str(WRAPPER), "--request-base64", "$(touch pwned)"],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(capture.exists())


if __name__ == "__main__":
    unittest.main()
