"""Real-file/CLI checks of the task oracle; no 1C, network or frozen-call proof."""
from __future__ import annotations

import codecs
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / "experiments/hermes-browser-dev-marker/oracle.py"
RUN_ID = "2bb6499d-dff2-49d6-b46b-9dbb38f644b7"
NONCE = "5e6b820c-3f4d-47d8-9773-5e5c2d0ab423"
OTHER_ID = "f8af46b5-097f-4c7a-a42d-8a013892592e"
MARKER = "HERMES_BROWSER_DEV_" + NONCE
TOKEN = "native witness need not be a UUID"


class BrowserDevMarkerOracleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="marker-oracle-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.paths = {name: self.directory / (name + ".txt") for name in ("request", "client", "server")}

    def fixtures(self, *, token: str = TOKEN, ending: str = "\n", bom: bool = False) -> dict[str, bytes]:
        prefix = codecs.BOM_UTF8 if bom else b""
        client = ["run###" + RUN_ID, "nonce###" + NONCE, "token###" + token,
                  "marker###" + MARKER, "returned###true", "complete###true"]
        server = ["run###" + RUN_ID, "nonce###" + NONCE, "token###" + token,
                  "marker###" + MARKER, "serverComplete###true"]
        return {
            "request": prefix + json.dumps({"runId": RUN_ID, "nonce": NONCE}).encode("utf-8"),
            "client": prefix + (ending.join(client) + ending).encode("utf-8"),
            "server": prefix + (ending.join(server) + ending).encode("utf-8"),
        }

    def cli(self, files: dict[str, bytes]) -> subprocess.CompletedProcess[str]:
        for name, payload in files.items():
            self.paths[name].write_bytes(payload)
        return subprocess.run(
            [sys.executable, "-I", "-B", str(ORACLE), "--request", str(self.paths["request"]),
             "--client-receipt", str(self.paths["client"]), "--server-receipt", str(self.paths["server"])],
            cwd=self.directory, capture_output=True, text=True, encoding="utf-8", timeout=10,
        )

    def assert_pass(self, files: dict[str, bytes]) -> None:
        result = self.cli(files)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(len(result.stdout.splitlines()), 1)
        self.assertEqual(json.loads(result.stdout), {
            "status": "PASS",
            "businessPayload": {
                "marker": MARKER, "clientServerWitnessMatched": True,
                "scope": "private managed-application marker in disposable IB",
            },
        })

    def assert_fail(self, files: dict[str, bytes]) -> None:
        result = self.cli(files)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "", "invalid data must not emit success JSON")
        self.assertTrue(result.stderr.startswith("FAIL:"))
        self.assertNotIn("Traceback", result.stderr)

    def test_success_supports_bom_lf_crlf_and_non_uuid_server_token(self) -> None:
        for ending in ("\n", "\r\n"):
            for bom in (False, True):
                with self.subTest(ending=repr(ending), bom=bom):
                    self.assert_pass(self.fixtures(ending=ending, bom=bom))

    def test_request_is_exactly_two_distinct_canonical_uuid4_fields(self) -> None:
        valid = {"runId": RUN_ID, "nonce": NONCE}
        invalid = [[], {}, {"runId": RUN_ID}, dict(valid, extra="no"), dict(valid, nonce=RUN_ID)]
        for field in valid:
            for value in (True, 1, None, [], {}, "", valid[field].upper(), valid[field] + "\n",
                          valid[field].replace("-4", "-1", 1), valid[field].replace("-", "")):
                invalid.append(dict(valid, **{field: value}))
        for request in invalid:
            with self.subTest(request=request):
                files = self.fixtures()
                files["request"] = json.dumps(request).encode("utf-8")
                self.assert_fail(files)
        for request in (b'{"runId":"' + RUN_ID.encode() + b'","nonce":"' + NONCE.encode()
                        + b'","nonce":"' + NONCE.encode() + b'"}', b'{"runId":', b'null'):
            with self.subTest(raw=request):
                files = self.fixtures(); files["request"] = request
                self.assert_fail(files)

    def test_missing_extra_duplicate_reordered_or_ambiguous_rows_fail(self) -> None:
        for name in ("client", "server"):
            baseline = self.fixtures()[name].decode().splitlines()
            mutations = [baseline[:-1], baseline + ["extra###true"],
                         baseline + [baseline[0]], [baseline[0], baseline[0], *baseline[2:]],
                         [baseline[1], baseline[0], *baseline[2:]], ["", *baseline],
                         [*baseline, ""], [line.replace("token###", "token###extra###") for line in baseline],
                         [line.replace("token###" + TOKEN, "token###") for line in baseline],
                         [line.replace("token###", "token##") for line in baseline]]
            for rows in mutations:
                with self.subTest(channel=name, rows=rows):
                    files = self.fixtures(); files[name] = ("\n".join(rows) + "\n").encode()
                    self.assert_fail(files)

    def test_stale_or_foreign_request_binding_and_marker_fail_on_either_channel(self) -> None:
        for name in ("client", "server"):
            for old, new in ((RUN_ID, OTHER_ID), (NONCE, OTHER_ID), (MARKER, "fabricated-marker")):
                with self.subTest(channel=name, old=old):
                    files = self.fixtures(); files[name] = files[name].replace(old.encode(), new.encode())
                    self.assert_fail(files)
        files = self.fixtures()
        files["request"] = json.dumps({"runId": RUN_ID, "nonce": OTHER_ID}).encode()
        self.assert_fail(files)

    def test_returned_and_completion_flags_are_exact(self) -> None:
        for name, key in (("client", "returned"), ("client", "complete"), ("server", "serverComplete")):
            for value in ("false", "True", "1", "true "):
                with self.subTest(channel=name, key=key, value=value):
                    files = self.fixtures(); files[name] = files[name].replace((key + "###true").encode(), (key + "###" + value).encode())
                    self.assert_fail(files)

    def test_token_mismatch_and_identity_or_marker_echo_fail(self) -> None:
        files = self.fixtures(); files["client"] = files["client"].replace(TOKEN.encode(), b"foreign token")
        self.assert_fail(files)
        for token in ("", RUN_ID, NONCE, MARKER):
            with self.subTest(token=token):
                self.assert_fail(self.fixtures(token=token))

    def test_invalid_utf8_or_line_framing_fail(self) -> None:
        for name in ("request", "client", "server"):
            files = self.fixtures(); files[name] += b"\xff"
            with self.subTest(channel=name):
                self.assert_fail(files)
        for name in ("client", "server"):
            for mutate in (lambda value: value.rstrip(b"\n"),
                           lambda value: value.replace(b"\n", b"\r"),
                           lambda value: value.replace(b"token###", b"\rtoken###")):
                files = self.fixtures(); files[name] = mutate(files[name])
                with self.subTest(channel=name, payload=files[name]):
                    self.assert_fail(files)

    def test_request_byte_boundary_is_inclusive(self) -> None:
        files = self.fixtures()
        files["request"] += b" " * (4096 - len(files["request"]))
        self.assertEqual(len(files["request"]), 4096)
        self.assert_pass(files)
        files["request"] += b" "
        self.assert_fail(files)

    def test_receipt_byte_boundary_bounds_opaque_token_without_extra_uuid_policy(self) -> None:
        empty_token_overhead = len(self.fixtures(token="")["client"])
        files = self.fixtures(token="x" * (4096 - empty_token_overhead))
        self.assertEqual(len(files["client"]), 4096)
        self.assertLess(len(files["server"]), 4096)
        self.assert_pass(files)
        self.assert_fail(self.fixtures(token="x" * (4097 - empty_token_overhead)))
        server_overhead = len(self.fixtures(token="")["server"])
        self.assert_fail(self.fixtures(token="x" * (4097 - server_overhead)))

    def test_multibyte_receipt_limit_counts_bytes_not_characters(self) -> None:
        token = "\u044f" * 2000
        files = self.fixtures(token=token)
        self.assertLess(len(files["client"].decode()), 4096)
        self.assertGreater(len(files["client"]), 4096)
        self.assert_fail(files)

    def test_token_is_only_data_and_cli_works_without_repository_imports(self) -> None:
        attempted_output = self.directory / "payload-executed.txt"
        token = "__import__('pathlib').Path(" + repr(str(attempted_output)) + ").write_text('bad')"
        self.assert_pass(self.fixtures(token=token))
        self.assertFalse(attempted_output.exists())

    def test_missing_input_file_is_a_clean_failure(self) -> None:
        files = self.fixtures()
        for name, payload in files.items():
            self.paths[name].write_bytes(payload)
        self.paths["server"].unlink()
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(ORACLE), "--request", str(self.paths["request"]),
             "--client-receipt", str(self.paths["client"]), "--server-receipt", str(self.paths["server"])],
            cwd=self.directory, capture_output=True, text=True, encoding="utf-8", timeout=10,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.startswith("FAIL:"))


if __name__ == "__main__":
    unittest.main()
