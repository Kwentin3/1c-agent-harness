from __future__ import annotations

import os
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
                "cd /workspace/1c-agent-harness/.local/issue75-companion/source "
                "&& exec ../bin/one-c-harness --request-base64 " + token,
            )

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
