from __future__ import annotations

import base64
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "issue38_protocol.py"
FRONTDOOR_PATH = ROOT / "scripts" / "issue38_frontdoor.py"
NATIVE_CYCLE_PATH = ROOT / "scripts" / "native_cycle.py"


def load_module() -> object:
    spec = importlib.util.spec_from_file_location("issue38_protocol_under_test", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load Issue 38 protocol module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_frontdoor() -> object:
    scripts = str(ROOT / "scripts")
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location("issue38_frontdoor_under_test", FRONTDOOR_PATH)
        if spec is None or spec.loader is None:
            raise AssertionError("cannot load Issue 38 front door")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def write_frontdoor_snapshot(source: Path) -> None:
    (source / "Ext").mkdir(parents=True)
    (source / "CommonModules/JetServerCall/Ext").mkdir(parents=True)
    (source / "Ext/ManagedApplicationModule.bsl").write_text(_managed_module(), encoding="utf-8")
    (source / "CommonModules/JetServerCall/Ext/Module.bsl").write_text(
        "#Region Public\nEndRegion\n", encoding="utf-8",
    )
    (source / "CommonModules/JetServerCall.xml").write_text(
        "<CommonModule><Server>true</Server><ServerCall>true</ServerCall></CommonModule>\n",
        encoding="utf-8",
    )


class Issue38ProtocolTests(unittest.TestCase):
    def test_cli_returns_validated_success_from_bound_receipts(self) -> None:
        request = _request()
        client = _receipt([
            *_headers(request),
            ("runtimeStarted", "true", "Boolean"),
            ("probeEntered", "true", "Boolean"),
            ("serverCallIssued", "true", "Boolean"),
            ("serverReached", "true", "Boolean"),
            ("caseStarted", "true", "Boolean"),
            ("businessResult", "server-token-01", "String"),
            ("complete", "true", "Boolean"),
        ])
        server = _receipt([
            *_headers(request),
            ("serverReached", "true", "Boolean"),
            ("caseStarted", "true", "Boolean"),
            ("businessResult", "server-token-01", "String"),
            ("complete", "true", "Boolean"),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request_path = root / "request.json"
            client_path = root / "client.txt"
            server_path = root / "server.txt"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            client_path.write_bytes(client)
            server_path.write_bytes(server)

            completed = subprocess.run(
                [
                    sys.executable, str(MODULE_PATH),
                    "--request", str(request_path),
                    "--client-receipt", str(client_path),
                    "--server-receipt", str(server_path),
                ],
                text=True,
                capture_output=True,
                timeout=10,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout), {
            "status": "success", "serverToken": "server-token-01",
        })


    def test_cli_returns_nonzero_for_missing_server_receipt_on_success_claim(self) -> None:
        request = _request()
        client = _receipt([
            *_headers(request),
            ("runtimeStarted", "true", "Boolean"),
            ("probeEntered", "true", "Boolean"),
            ("serverCallIssued", "true", "Boolean"),
            ("serverReached", "true", "Boolean"),
            ("caseStarted", "true", "Boolean"),
            ("businessResult", "server-token-01", "String"),
            ("complete", "true", "Boolean"),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request_path = root / "request.json"
            client_path = root / "client.txt"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            client_path.write_bytes(client)

            completed = subprocess.run(
                [
                    sys.executable, str(MODULE_PATH),
                    "--request", str(request_path),
                    "--client-receipt", str(client_path),
                ],
                text=True,
                capture_output=True,
                timeout=10,
            )

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertIn("server receipt", completed.stderr)


    def test_cli_rejects_invalid_utf8_request_without_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request_path = root / "request.json"
            client_path = root / "client.txt"
            request_path.write_bytes(b"\xff\xfe\x00")
            client_path.write_bytes(b"not-used\n")

            completed = subprocess.run(
                [
                    sys.executable, str(MODULE_PATH),
                    "--request", str(request_path),
                    "--client-receipt", str(client_path),
                ],
                text=True,
                capture_output=True,
                timeout=10,
            )

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertIn("request is not UTF-8", completed.stderr)


    def test_cli_rejects_duplicate_request_identity_keys(self) -> None:
        request = _request()
        client = _receipt([
            *_headers(request),
            ("runtimeStarted", "true", "Boolean"),
            ("probeEntered", "true", "Boolean"),
            ("serverCallIssued", "true", "Boolean"),
            ("serverReached", "true", "Boolean"),
            ("caseStarted", "true", "Boolean"),
            ("businessResult", "server-token-01", "String"),
            ("complete", "true", "Boolean"),
        ])
        server = _receipt([
            *_headers(request),
            ("serverReached", "true", "Boolean"),
            ("caseStarted", "true", "Boolean"),
            ("businessResult", "server-token-01", "String"),
            ("complete", "true", "Boolean"),
        ])
        duplicate_request = (
            '{"protocolVersion":"issue38-v5",'
            '"runId":"00000000-0000-4000-8000-000000000001",'
            f'"runId":"{request["runId"]}",'
            f'"caseId":"{request["caseId"]}",'
            f'"nonce":"{request["nonce"]}",'
            '"operation":"serverWitness","requiresServer":true}'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request_path = root / "request.json"
            client_path = root / "client.txt"
            server_path = root / "server.txt"
            request_path.write_text(duplicate_request, encoding="utf-8")
            client_path.write_bytes(client)
            server_path.write_bytes(server)

            completed = subprocess.run(
                [
                    sys.executable, str(MODULE_PATH),
                    "--request", str(request_path),
                    "--client-receipt", str(client_path),
                    "--server-receipt", str(server_path),
                ],
                text=True,
                capture_output=True,
                timeout=10,
            )

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertIn("duplicate request key", completed.stderr)


    def test_retained_a_success_packet_validates_and_keeps_remote_hashes(self) -> None:
        packet = ROOT / "tests/fixtures/issue38-a-metadata-read-v1"
        request = json.loads((packet / "request.reconstructed.json").read_text(encoding="utf-8"))
        summary = json.loads((packet / "result-summary.json").read_text(encoding="utf-8"))
        client = base64.b64decode((packet / "client-receipt.base64").read_text(encoding="ascii"))
        server = base64.b64decode((packet / "server-receipt.base64").read_text(encoding="ascii"))

        self.assertEqual(hashlib.sha256(client).hexdigest(), summary["trackedPacket"]["clientReceiptSha256"])
        self.assertEqual(hashlib.sha256(server).hexdigest(), summary["trackedPacket"]["serverReceiptSha256"])
        self.assertEqual(load_module().validate_terminal(request, client, server), {
            "status": "success", "serverToken": "SalesInvoice",
        })

    def test_frontdoor_prepare_generates_one_request_and_two_file_closure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "snapshot"
            (source / "Ext").mkdir(parents=True)
            (source / "CommonModules/JetServerCall/Ext").mkdir(parents=True)
            (source / "Ext/ManagedApplicationModule.bsl").write_text(_managed_module(), encoding="utf-8")
            (source / "CommonModules/JetServerCall/Ext/Module.bsl").write_text(
                "#Region Public\nEndRegion\n", encoding="utf-8",
            )
            (source / "CommonModules/JetServerCall.xml").write_text(
                "<CommonModule><Server>true</Server><ServerCall>true</ServerCall></CommonModule>\n",
                encoding="utf-8",
            )
            prepared = root / ".local/prepared" / "issue38-a-next"
            request_path = root / "evidence/request.json"
            completed = subprocess.run(
                [
                    sys.executable, str(FRONTDOOR_PATH), "prepare",
                    "--repo-root", str(root),
                    "--input-tree", str(source),
                    "--prepared-tree", str(prepared),
                    "--request", str(request_path),
                ],
                text=True,
                capture_output=True,
                timeout=10,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            prepared_result = json.loads(completed.stdout)
            self.assertEqual(prepared_result["status"], "prepared")
            self.assertEqual(prepared_result["changedFiles"], [
                "CommonModules/JetServerCall/Ext/Module.bsl", "Ext/ManagedApplicationModule.bsl",
            ])
            self.assertEqual(prepared_result["preparationAudit"]["staticCheck"], "pass")
            self.assertEqual(prepared_result["preparationAudit"]["changedPaths"], prepared_result["changedFiles"])
            self.assertEqual(prepared_result["preparationAudit"]["forbiddenAddedMatches"], [])
            self.assertTrue(all(not (path.stat().st_mode & 0o222) for path in (prepared, *prepared.rglob("*"))))
            request = json.loads(request_path.read_text(encoding="utf-8"))
            self.assertEqual(set(request), {
                "protocolVersion", "runId", "caseId", "nonce", "operation", "requiresServer",
            })
            client = (prepared / "Ext/ManagedApplicationModule.bsl").read_text(encoding="utf-8")
            server = (prepared / "CommonModules/JetServerCall/Ext/Module.bsl").read_text(encoding="utf-8")
            self.assertIn('JetServerCall.Issue38ServerWitness(', client)
            self.assertIn('LaunchParameter + ".server"', client)
            self.assertIn("Function Issue38ServerWitness", server)
            self.assertNotIn("BankReceipt", client + server)
            self.assertNotIn("Issue36", client + server)
            generated_lines = "\n".join(
                line[1:] for line in difflib.ndiff(
                    (source / "Ext/ManagedApplicationModule.bsl").read_text(encoding="utf-8").splitlines(),
                    client.splitlines(),
                ) if line.startswith("+ ")
            ) + "\n".join(
                line[1:] for line in difflib.ndiff(
                    (source / "CommonModules/JetServerCall/Ext/Module.bsl").read_text(encoding="utf-8").splitlines(),
                    server.splitlines(),
                ) if line.startswith("+ ")
            )
            for forbidden in ("Execute(", "Eval(", "ErrorDescription", "ErrorInfo", "Chr("):
                self.assertNotIn(forbidden, generated_lines)

    def test_frontdoor_passes_the_terminal_literal_emitted_by_both_probes(self) -> None:
        frontdoor = load_frontdoor()
        request = _request()
        command = frontdoor._native_command(ROOT, ROOT / ".local/prepared/terminal-literal")
        marker = command[command.index("--complete-marker") + 1]

        for probe in (frontdoor._client_probe(request), frontdoor._server_probe(request)):
            lines = probe.decode("ascii").splitlines()
            terminal = next(
                line for line in reversed(lines)
                if 'Writer.WriteLine("complete###' in line
            )
            literal = terminal.split('Writer.WriteLine("', 1)[1].split('");', 1)[0]
            self.assertEqual(marker, literal)

    def test_frontdoor_prepare_discards_owned_tree_after_request_write_keyboard_interrupt(self) -> None:
        frontdoor = load_frontdoor()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "snapshot"
            prepared = root / ".local/prepared" / "request-write-interrupt"
            request_path = root / "evidence/request.json"
            write_frontdoor_snapshot(source)
            original_write = frontdoor._write_json_new
            frontdoor._write_json_new = lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt())
            try:
                with self.assertRaises(KeyboardInterrupt):
                    frontdoor.prepare(root, source, prepared, request_path)
            finally:
                frontdoor._write_json_new = original_write
            self.assertFalse(prepared.exists())
            self.assertFalse(request_path.exists())

    def test_frontdoor_prepare_discards_owned_tree_after_request_write_system_exit(self) -> None:
        frontdoor = load_frontdoor()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "snapshot"
            prepared = root / ".local/prepared" / "request-write-exit"
            request_path = root / "evidence/request.json"
            write_frontdoor_snapshot(source)
            original_write = frontdoor._write_json_new
            frontdoor._write_json_new = lambda *args, **kwargs: (_ for _ in ()).throw(SystemExit(9))
            try:
                with self.assertRaises(SystemExit) as raised:
                    frontdoor.prepare(root, source, prepared, request_path)
            finally:
                frontdoor._write_json_new = original_write
            self.assertEqual(raised.exception.code, 9)
            self.assertFalse(prepared.exists())
            self.assertFalse(request_path.exists())

    def test_frontdoor_prepare_reports_primary_and_cleanup_failure(self) -> None:
        frontdoor = load_frontdoor()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "snapshot"
            prepared = root / ".local/prepared" / "request-write-double-failure"
            request_path = root / "evidence/request.json"
            write_frontdoor_snapshot(source)
            original_write = frontdoor._write_json_new
            original_discard = frontdoor.managed_probe_prepare.discard_prepared_tree
            frontdoor._write_json_new = lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt())
            frontdoor.managed_probe_prepare.discard_prepared_tree = (
                lambda **kwargs: (_ for _ in ()).throw(SystemExit(7))
            )
            try:
                with self.assertRaisesRegex(
                    frontdoor.FrontDoorError,
                    "KeyboardInterrupt.*prepared cleanup failed: SystemExit",
                ):
                    frontdoor.prepare(root, source, prepared, request_path)
            finally:
                frontdoor._write_json_new = original_write
                frontdoor.managed_probe_prepare.discard_prepared_tree = original_discard
                original_discard(repo_root=root, prepared_root=prepared)
            self.assertFalse(prepared.exists())

    def test_frontdoor_run_handoffs_repo_relative_prepared_tree_to_real_runner_precheck_without_1c(self) -> None:
        frontdoor = load_frontdoor()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = root / "scripts/native_cycle.py"
            runner.parent.mkdir(parents=True)
            runner.write_bytes(NATIVE_CYCLE_PATH.read_bytes())
            source = root / "snapshot"
            prepared = root / ".local/prepared/real-seam"
            request_path = root / "evidence/request.json"
            write_frontdoor_snapshot(source)

            platform = root / ".local/platform/1cv8t/x86_64/8.5.1.1150/1cv8t"
            platform.parent.mkdir(parents=True)
            platform.write_text("must-not-run\n", encoding="utf-8")
            platform.chmod(0o644)
            xvfb = root / ".local/platform/libs/usr/bin/xvfb-run"
            xvfb.parent.mkdir(parents=True)
            xvfb.write_text(
                "#!/bin/sh\n"
                "set -eu\n"
                "printf '%s\\n' \"$@\" > \"$(dirname \"$0\")/../../../blocked-1c-argv.txt\"\n"
                "exit 97\n",
                encoding="utf-8",
            )
            xvfb.chmod(0o755)
            (root / ".local/platform/fonts.conf").write_text("fonts\n", encoding="utf-8")
            (root / ".local/platform/libs/usr/lib/x86_64-linux-gnu").mkdir(parents=True)

            result = frontdoor.run(root, source, prepared, request_path)

            runner_result = result["runner"]
            self.assertEqual(result["status"], "runnerFailure")
            self.assertEqual(runner_result["status"], "create_failed")
            self.assertEqual(runner_result["failedStage"], "create")
            self.assertEqual(
                runner_result["preparedInvocation"]["sourcePath"],
                ".local/prepared/real-seam",
            )
            blocked = root / ".local/platform/blocked-1c-argv.txt"
            self.assertTrue(blocked.is_file())
            self.assertIn("CREATEINFOBASE", blocked.read_text(encoding="utf-8"))
            self.assertFalse(platform.stat().st_mode & 0o111)
            self.assertFalse(prepared.exists())

    def test_frontdoor_run_discards_prepared_tree_after_runner_failure(self) -> None:
        frontdoor = load_frontdoor()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "snapshot"
            (source / "Ext").mkdir(parents=True)
            (source / "CommonModules/JetServerCall/Ext").mkdir(parents=True)
            (source / "Ext/ManagedApplicationModule.bsl").write_text(_managed_module(), encoding="utf-8")
            (source / "CommonModules/JetServerCall/Ext/Module.bsl").write_text(
                "#Region Public\nEndRegion\n", encoding="utf-8",
            )
            (source / "CommonModules/JetServerCall.xml").write_text(
                "<CommonModule><Server>true</Server><ServerCall>true</ServerCall></CommonModule>\n",
                encoding="utf-8",
            )
            prepared = root / ".local/prepared" / "runner-failure"
            request_path = root / "evidence/request.json"
            original_run = frontdoor.subprocess.run

            invocation_root = root / ".local/runs/native-cycle/run-runner-failure"

            def failing_runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
                invocation_root.mkdir(parents=True)
                return subprocess.CompletedProcess(
                    args=args,
                    returncode=1,
                    stdout=json.dumps({"preparedInvocation": {"invocationRoot": ".local/runs/native-cycle/run-runner-failure"}}),
                    stderr="runner failed",
                )

            frontdoor.subprocess.run = failing_runner
            try:
                result = frontdoor.run(root, source, prepared, request_path)
            finally:
                frontdoor.subprocess.run = original_run

            self.assertEqual(result["status"], "runnerFailure")
            self.assertEqual(result["cleanup"], "discarded")
            self.assertFalse(prepared.exists())

    def test_frontdoor_run_discards_prepared_tree_after_terminal_errors(self) -> None:
        frontdoor = load_frontdoor()
        scenarios = (
            ("malformed-output", lambda _: subprocess.CompletedProcess([], 0, "not-json", "")),
            ("timeout", lambda _: (_ for _ in ()).throw(subprocess.TimeoutExpired(["native"], 1))),
            (
                "protocol-error",
                lambda root: _runner_with_invalid_receipts(root),
            ),
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original_run = frontdoor.subprocess.run
            try:
                for name, outcome in scenarios:
                    with self.subTest(name=name):
                        source = root / name / "snapshot"
                        prepared = root / name / ".local/prepared" / "case"
                        request_path = root / name / "evidence/request.json"
                        write_frontdoor_snapshot(source)
                        frontdoor.subprocess.run = lambda *args, _root=root / name, **kwargs: outcome(_root)
                        with self.assertRaises((frontdoor.FrontDoorError, frontdoor.issue38_protocol.ProtocolError)):
                            frontdoor.run(root / name, source, prepared, request_path)
                        self.assertFalse(prepared.exists())
            finally:
                frontdoor.subprocess.run = original_run

    def test_frontdoor_run_rejects_external_invocation_root_and_discards_prepared_tree(self) -> None:
        frontdoor = load_frontdoor()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "snapshot"
            prepared = root / ".local/prepared" / "external-invocation"
            request_path = root / "evidence/request.json"
            outside = root.parent / f"issue38-external-{uuid.uuid4()}"
            write_frontdoor_snapshot(source)
            original_run = frontdoor.subprocess.run

            def external_runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
                request = json.loads(request_path.read_text(encoding="utf-8"))
                client, server = _success_receipts(request)
                evidence = outside / "run/evidence"
                evidence.mkdir(parents=True)
                receipt = evidence / "receipt.txt"
                receipt.write_bytes(client)
                receipt.with_name("receipt.txt.server").write_bytes(server)
                return subprocess.CompletedProcess(
                    [], 0, json.dumps({"preparedInvocation": {"invocationRoot": str(outside)}}), "",
                )

            frontdoor.subprocess.run = external_runner
            try:
                with self.assertRaisesRegex(frontdoor.FrontDoorError, "invocationRoot"):
                    frontdoor.run(root, source, prepared, request_path)
            finally:
                frontdoor.subprocess.run = original_run
                if outside.exists():
                    for path in sorted((outside, *outside.rglob("*")), key=lambda item: len(item.parts), reverse=True):
                        if path.is_file():
                            path.unlink()
                        else:
                            path.rmdir()
            self.assertFalse(prepared.exists())

    def test_frontdoor_run_rejects_non_object_runner_result_and_discards_prepared_tree(self) -> None:
        frontdoor = load_frontdoor()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "snapshot"
            prepared = root / ".local/prepared" / "scalar-runner-result"
            request_path = root / "evidence/request.json"
            write_frontdoor_snapshot(source)
            original_run = frontdoor.subprocess.run
            frontdoor.subprocess.run = lambda *args, **kwargs: subprocess.CompletedProcess([], 0, "null", "")
            try:
                with self.assertRaisesRegex(frontdoor.FrontDoorError, "JSON object"):
                    frontdoor.run(root, source, prepared, request_path)
            finally:
                frontdoor.subprocess.run = original_run
            self.assertFalse(prepared.exists())

    def test_frontdoor_run_rejects_unsafe_runner_failure_invocation_root_and_discards_prepared_tree(self) -> None:
        frontdoor = load_frontdoor()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "snapshot"
            prepared = root / ".local/prepared" / "unsafe-runner-failure"
            request_path = root / "evidence/request.json"
            write_frontdoor_snapshot(source)
            original_run = frontdoor.subprocess.run
            frontdoor.subprocess.run = lambda *args, **kwargs: subprocess.CompletedProcess(
                [], 1, json.dumps({"preparedInvocation": {"invocationRoot": "/outside/run-x"}}), "",
            )
            try:
                with self.assertRaisesRegex(frontdoor.FrontDoorError, "unsafe invocationRoot"):
                    frontdoor.run(root, source, prepared, request_path)
            finally:
                frontdoor.subprocess.run = original_run
            self.assertFalse(prepared.exists())

    def test_frontdoor_resolves_relative_paths_against_repo_root(self) -> None:
        frontdoor = load_frontdoor()
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as elsewhere:
            root = Path(tmp)
            source = root / "snapshot"
            write_frontdoor_snapshot(source)
            previous_cwd = Path.cwd()
            os.chdir(elsewhere)
            try:
                result = frontdoor.prepare(
                    root,
                    Path("snapshot"),
                    Path(".local/prepared/repo-relative"),
                    Path("evidence/request.json"),
                )
            finally:
                os.chdir(previous_cwd)
            self.assertEqual(result["preparedTree"], str(root / ".local/prepared/repo-relative"))
            self.assertTrue((root / ".local/prepared/repo-relative/Ext/ManagedApplicationModule.bsl").is_file())
            self.assertTrue((root / "evidence/request.json").is_file())

    def test_frontdoor_run_discards_prepared_tree_after_validated_response(self) -> None:
        frontdoor = load_frontdoor()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "snapshot"
            prepared = root / ".local/prepared" / "validated"
            request_path = root / "evidence/request.json"
            write_frontdoor_snapshot(source)
            original_run = frontdoor.subprocess.run

            def validated_runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
                request = json.loads(request_path.read_text(encoding="utf-8"))
                client, server = _success_receipts(request)
                evidence = root / ".local/runs/native-cycle/run-validated/run/evidence"
                evidence.mkdir(parents=True)
                receipt = evidence / "receipt.txt"
                receipt.write_bytes(client)
                receipt.with_name("receipt.txt.server").write_bytes(server)
                result = {"preparedInvocation": {"invocationRoot": ".local/runs/native-cycle/run-validated"}}
                return subprocess.CompletedProcess([], 0, json.dumps(result), "")

            frontdoor.subprocess.run = validated_runner
            try:
                result = frontdoor.run(root, source, prepared, request_path)
            finally:
                frontdoor.subprocess.run = original_run

            self.assertEqual(result["status"], "validated")
            self.assertEqual(result["cleanup"], "discarded")
            self.assertFalse(prepared.exists())

    def test_frontdoor_run_reports_prepared_cleanup_failure(self) -> None:
        frontdoor = load_frontdoor()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "snapshot"
            prepared = root / ".local/prepared" / "cleanup-failure"
            request_path = root / "evidence/request.json"
            write_frontdoor_snapshot(source)
            original_run = frontdoor.subprocess.run
            original_discard = frontdoor.managed_probe_prepare.discard_prepared_tree
            frontdoor.subprocess.run = lambda *args, **kwargs: subprocess.CompletedProcess([], 1, "{}", "")
            frontdoor.managed_probe_prepare.discard_prepared_tree = (
                lambda **kwargs: (_ for _ in ()).throw(ValueError("simulated cleanup refusal"))
            )
            try:
                with self.assertRaisesRegex(frontdoor.FrontDoorError, "prepared cleanup failed"):
                    frontdoor.run(root, source, prepared, request_path)
            finally:
                frontdoor.subprocess.run = original_run
                frontdoor.managed_probe_prepare.discard_prepared_tree = original_discard
                original_discard(repo_root=root, prepared_root=prepared)

    def test_frontdoor_cli_discard_removes_standalone_prepared_tree(self) -> None:
        frontdoor = load_frontdoor()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "snapshot"
            prepared = root / ".local/prepared" / "standalone"
            request_path = root / "evidence/request.json"
            write_frontdoor_snapshot(source)
            frontdoor.prepare(root, source, prepared, request_path)

            completed = subprocess.run(
                [
                    sys.executable, str(FRONTDOOR_PATH), "discard",
                    "--repo-root", str(root),
                    "--prepared-tree", str(prepared),
                ],
                text=True,
                capture_output=True,
                timeout=10,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["status"], "discarded")
            self.assertFalse(prepared.exists())

    def test_frontdoor_preserves_prepared_path_for_symlink_rejection(self) -> None:
        frontdoor = load_frontdoor()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "snapshot"
            prepared_base = root / ".local/prepared"
            prepared_base.mkdir(parents=True)
            prepared_link = prepared_base / "link"
            prepared_target = prepared_base / "target"
            prepared_link.symlink_to(prepared_target, target_is_directory=True)
            request_path = root / "evidence/request.json"
            write_frontdoor_snapshot(source)

            with self.assertRaisesRegex(frontdoor.FrontDoorError, "symlink"):
                frontdoor.prepare(root, source, prepared_link, request_path)
            self.assertTrue(prepared_link.is_symlink())
            self.assertFalse(prepared_target.exists())

    def test_frontdoor_preserves_source_path_for_symlink_rejection(self) -> None:
        frontdoor = load_frontdoor()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_target = root / "snapshot-target"
            source_link = root / "snapshot-link"
            prepared = root / ".local/prepared" / "case"
            request_path = root / "evidence/request.json"
            write_frontdoor_snapshot(source_target)
            source_link.symlink_to(source_target, target_is_directory=True)

            with self.assertRaisesRegex(frontdoor.FrontDoorError, "symlink"):
                frontdoor.prepare(root, source_link, prepared, request_path)
            self.assertTrue(source_link.is_symlink())
            self.assertFalse(prepared.exists())

    def test_frontdoor_discard_preserves_symlink_target(self) -> None:
        frontdoor = load_frontdoor()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepared_base = root / ".local/prepared"
            prepared_base.mkdir(parents=True)
            target = prepared_base / "target"
            target.mkdir()
            sentinel = target / "sentinel.txt"
            sentinel.write_text("must-survive", encoding="utf-8")
            link = prepared_base / "link"
            link.symlink_to(target, target_is_directory=True)

            with self.assertRaisesRegex(frontdoor.FrontDoorError, "symlink"):
                frontdoor.discard(root, link)
            self.assertTrue(link.is_symlink())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "must-survive")

    def test_frontdoor_prepare_keeps_existing_prepared_tree_on_rejection(self) -> None:
        frontdoor = load_frontdoor()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "snapshot"
            prepared = root / ".local/prepared" / "existing"
            write_frontdoor_snapshot(source)
            frontdoor.prepare(root, source, prepared, root / "evidence/first.json")

            with self.assertRaisesRegex(frontdoor.FrontDoorError, "already exists"):
                frontdoor.prepare(root, source, prepared, root / "evidence/second.json")
            self.assertTrue((prepared / "Ext/ManagedApplicationModule.bsl").is_file())

    def test_frontdoor_prepare_keeps_source_owned_prepared_descendant_on_rejection(self) -> None:
        frontdoor = load_frontdoor()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / ".local"
            prepared = source / "prepared" / "case"
            write_frontdoor_snapshot(source)
            prepared.mkdir(parents=True)
            sentinel = prepared / "sentinel.txt"
            sentinel.write_text("must-survive", encoding="utf-8")

            with self.assertRaisesRegex(frontdoor.FrontDoorError, "disjoint"):
                frontdoor.prepare(root, source, prepared, root / "evidence/request.json")
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "must-survive")

    def test_frontdoor_run_reports_successful_cleanup_failure_without_false_run_failure(self) -> None:
        frontdoor = load_frontdoor()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "snapshot"
            prepared = root / ".local/prepared" / "cleanup-after-success"
            request_path = root / "evidence/request.json"
            write_frontdoor_snapshot(source)
            original_run = frontdoor.subprocess.run
            original_discard = frontdoor.managed_probe_prepare.discard_prepared_tree

            def validated_runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
                request = json.loads(request_path.read_text(encoding="utf-8"))
                client, server = _success_receipts(request)
                evidence = root / ".local/runs/native-cycle/run-cleanup-success/run/evidence"
                evidence.mkdir(parents=True)
                receipt = evidence / "receipt.txt"
                receipt.write_bytes(client)
                receipt.with_name("receipt.txt.server").write_bytes(server)
                return subprocess.CompletedProcess(
                    [], 0, json.dumps({"preparedInvocation": {"invocationRoot": ".local/runs/native-cycle/run-cleanup-success"}}), "",
                )

            frontdoor.subprocess.run = validated_runner
            frontdoor.managed_probe_prepare.discard_prepared_tree = (
                lambda **kwargs: (_ for _ in ()).throw(ValueError("simulated cleanup refusal"))
            )
            try:
                with self.assertRaisesRegex(frontdoor.FrontDoorError, "^prepared cleanup failed") as raised:
                    frontdoor.run(root, source, prepared, request_path)
                self.assertNotIn("run failed", str(raised.exception))
            finally:
                frontdoor.subprocess.run = original_run
                frontdoor.managed_probe_prepare.discard_prepared_tree = original_discard
                original_discard(repo_root=root, prepared_root=prepared)

    def test_frontdoor_run_reports_terminal_and_cleanup_failure_together(self) -> None:
        frontdoor = load_frontdoor()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "snapshot"
            prepared = root / ".local/prepared" / "cleanup-after-terminal-error"
            request_path = root / "evidence/request.json"
            write_frontdoor_snapshot(source)
            original_run = frontdoor.subprocess.run
            original_discard = frontdoor.managed_probe_prepare.discard_prepared_tree
            frontdoor.subprocess.run = lambda *args, **kwargs: subprocess.CompletedProcess([], 0, "not-json", "")
            frontdoor.managed_probe_prepare.discard_prepared_tree = (
                lambda **kwargs: (_ for _ in ()).throw(ValueError("simulated cleanup refusal"))
            )
            try:
                with self.assertRaisesRegex(
                    frontdoor.FrontDoorError,
                    "^run failed: native cycle did not return one JSON result; prepared cleanup failed",
                ):
                    frontdoor.run(root, source, prepared, request_path)
            finally:
                frontdoor.subprocess.run = original_run
                frontdoor.managed_probe_prepare.discard_prepared_tree = original_discard
                original_discard(repo_root=root, prepared_root=prepared)

    def test_frontdoor_has_no_second_prepared_tree_mechanism(self) -> None:
        source = FRONTDOOR_PATH.read_text(encoding="utf-8")
        self.assertIn("managed_probe_prepare.prepare_probe(", source)
        for duplicate_mechanic in (
            "shutil.copytree(",
            "os.chmod(",
            "def _insert_on_start_probe(",
            "def _changed_files(",
        ):
            self.assertNotIn(duplicate_mechanic, source)

    def test_new_request_uses_v5_and_three_fresh_uuid4_identifiers(self) -> None:
        protocol = load_module()

        request = protocol.new_request()

        self.assertEqual(request["protocolVersion"], "issue38-v5")
        self.assertEqual(request["operation"], "serverWitness")
        self.assertIs(request["requiresServer"], True)
        identifiers = [request["runId"], request["caseId"], request["nonce"]]
        self.assertEqual(len(set(identifiers)), 3)
        for value in identifiers:
            parsed = uuid.UUID(value)
            self.assertEqual(parsed.version, 4)

    def test_validate_success_accepts_current_linked_client_and_server_receipts(self) -> None:
        protocol = load_module()
        request = {
            "protocolVersion": "issue38-v5",
            "runId": "11111111-1111-4111-8111-111111111111",
            "caseId": "22222222-2222-4222-8222-222222222222",
            "nonce": "33333333-3333-4333-8333-333333333333",
            "operation": "serverWitness",
            "requiresServer": True,
        }
        token = "server-token-01"
        client = _receipt([
            ("protocolVersion", "issue38-v5", "String"),
            ("runId", request["runId"], "String"),
            ("caseId", request["caseId"], "String"),
            ("nonce", request["nonce"], "String"),
            ("operation", "serverWitness", "String"),
            ("runtimeStarted", "true", "Boolean"),
            ("probeEntered", "true", "Boolean"),
            ("serverCallIssued", "true", "Boolean"),
            ("serverReached", "true", "Boolean"),
            ("caseStarted", "true", "Boolean"),
            ("businessResult", token, "String"),
            ("complete", "true", "Boolean"),
        ])
        server = _receipt([
            ("protocolVersion", "issue38-v5", "String"),
            ("runId", request["runId"], "String"),
            ("caseId", request["caseId"], "String"),
            ("nonce", request["nonce"], "String"),
            ("operation", "serverWitness", "String"),
            ("serverReached", "true", "Boolean"),
            ("caseStarted", "true", "Boolean"),
            ("businessResult", token, "String"),
            ("complete", "true", "Boolean"),
        ])

        result = protocol.validate_success(request, client, server)

        self.assertEqual(result, {"status": "success", "serverToken": token})

    def test_validate_success_rejects_client_only_echo_of_request_nonce(self) -> None:
        protocol = load_module()
        request = {
            "protocolVersion": "issue38-v5", "runId": "11111111-1111-4111-8111-111111111111",
            "caseId": "22222222-2222-4222-8222-222222222222", "nonce": "33333333-3333-4333-8333-333333333333",
            "operation": "serverWitness", "requiresServer": True,
        }
        client = _receipt([
            ("protocolVersion", "issue38-v5", "String"), ("runId", request["runId"], "String"),
            ("caseId", request["caseId"], "String"), ("nonce", request["nonce"], "String"),
            ("operation", "serverWitness", "String"), ("runtimeStarted", "true", "Boolean"),
            ("probeEntered", "true", "Boolean"), ("serverCallIssued", "true", "Boolean"),
            ("serverReached", "true", "Boolean"), ("caseStarted", "true", "Boolean"),
            ("businessResult", request["nonce"], "String"), ("complete", "true", "Boolean"),
        ])

        with self.assertRaisesRegex(protocol.ProtocolError, "server receipt"):
            protocol.validate_success(request, client, None)

    def test_validate_success_rejects_foreign_identity_and_extra_record(self) -> None:
        protocol = load_module()
        request = {
            "protocolVersion": "issue38-v5", "runId": "11111111-1111-4111-8111-111111111111",
            "caseId": "22222222-2222-4222-8222-222222222222", "nonce": "33333333-3333-4333-8333-333333333333",
            "operation": "serverWitness", "requiresServer": True,
        }
        client = _receipt([
            ("protocolVersion", "issue38-v5", "String"), ("runId", "44444444-4444-4444-8444-444444444444", "String"),
            ("caseId", request["caseId"], "String"), ("nonce", request["nonce"], "String"),
            ("operation", "serverWitness", "String"), ("runtimeStarted", "true", "Boolean"),
            ("probeEntered", "true", "Boolean"), ("serverCallIssued", "true", "Boolean"),
            ("serverReached", "true", "Boolean"), ("caseStarted", "true", "Boolean"),
            ("businessResult", "server-token-01", "String"), ("complete", "true", "Boolean"),
            ("extra", "true", "Boolean"),
        ])
        server = _receipt([
            ("protocolVersion", "issue38-v5", "String"), ("runId", request["runId"], "String"),
            ("caseId", request["caseId"], "String"), ("nonce", request["nonce"], "String"),
            ("operation", "serverWitness", "String"), ("serverReached", "true", "Boolean"),
            ("caseStarted", "true", "Boolean"), ("businessResult", "server-token-01", "String"),
            ("complete", "true", "Boolean"),
        ])

        with self.assertRaisesRegex(protocol.ProtocolError, "client receipt"):
            protocol.validate_success(request, client, server)

    def test_validate_terminal_returns_explicit_server_call_failure(self) -> None:
        protocol = load_module()
        request = _request()
        client = _receipt([
            *_headers(request),
            ("runtimeStarted", "true", "Boolean"),
            ("probeEntered", "true", "Boolean"),
            ("serverCallIssued", "true", "Boolean"),
            ("failureClass", "serverCallFailure", "String"),
            ("failureDetail", "call-failed", "String"),
            ("complete", "true", "Boolean"),
        ])

        result = protocol.validate_terminal(request, client, None)

        self.assertEqual(result, {
            "status": "failure", "failureClass": "serverCallFailure", "failureDetail": "call-failed",
        })

    def test_validate_terminal_rejects_extra_request_key_even_with_old_valid_receipts(self) -> None:
        protocol = load_module()
        request = _request()
        client, server = _success_receipts(request)
        request["taskInput"] = "mutated-after-freeze"

        with self.assertRaisesRegex(protocol.ProtocolError, "unknown key: taskInput"):
            protocol.validate_terminal(request, client, server)

    def test_validate_terminal_rejects_mutated_fixed_request_fields_even_with_old_valid_receipts(self) -> None:
        protocol = load_module()
        request = _request()
        client, server = _success_receipts(request)
        request["operation"] = "anotherOperation"

        with self.assertRaisesRegex(protocol.ProtocolError, "unsupported operation"):
            protocol.validate_terminal(request, client, server)

        request = _request()
        request["requiresServer"] = False
        with self.assertRaisesRegex(protocol.ProtocolError, "must require server"):
            protocol.validate_terminal(request, client, server)

    def test_validate_terminal_rejects_task_exception_before_case_start(self) -> None:
        protocol = load_module()
        request = _request()
        client = _receipt([
            *_headers(request),
            ("runtimeStarted", "true", "Boolean"),
            ("probeEntered", "true", "Boolean"),
            ("failureClass", "taskException", "String"),
            ("complete", "true", "Boolean"),
        ])

        with self.assertRaisesRegex(protocol.ProtocolError, "taskException"):
            protocol.validate_terminal(request, client, None)

    def test_validate_terminal_rejects_non_uuid_request_identity(self) -> None:
        protocol = load_module()
        request = _request()
        request["runId"] = "not-a-uuid"

        with self.assertRaisesRegex(protocol.ProtocolError, "runId"):
            protocol.validate_terminal(request, None, None)

    def test_validate_terminal_rejects_client_only_task_exception(self) -> None:
        protocol = load_module()
        request = _request()
        client = _receipt([
            *_headers(request),
            ("runtimeStarted", "true", "Boolean"),
            ("probeEntered", "true", "Boolean"),
            ("serverCallIssued", "true", "Boolean"),
            ("serverReached", "true", "Boolean"),
            ("caseStarted", "true", "Boolean"),
            ("failureClass", "taskException", "String"),
            ("complete", "true", "Boolean"),
        ])

        with self.assertRaisesRegex(protocol.ProtocolError, "server receipt is absent"):
            protocol.validate_terminal(request, client, None)

    def test_validate_terminal_accepts_server_witnessed_task_exception_after_case_start(self) -> None:
        protocol = load_module()
        request = _request()
        client = _receipt([
            *_headers(request),
            ("runtimeStarted", "true", "Boolean"),
            ("probeEntered", "true", "Boolean"),
            ("serverCallIssued", "true", "Boolean"),
            ("serverReached", "true", "Boolean"),
            ("caseStarted", "true", "Boolean"),
            ("failureClass", "taskException", "String"),
            ("failureDetail", "controlled-server-task-exception", "String"),
            ("complete", "true", "Boolean"),
        ])
        server = _receipt([
            *_headers(request),
            ("serverReached", "true", "Boolean"),
            ("caseStarted", "true", "Boolean"),
            ("failureClass", "taskException", "String"),
            ("failureDetail", "controlled-server-task-exception", "String"),
            ("complete", "true", "Boolean"),
        ])

        self.assertEqual(protocol.validate_terminal(request, client, server), {
            "status": "failure", "failureClass": "taskException",
            "failureDetail": "controlled-server-task-exception",
        })

    def test_validate_terminal_rejects_runner_level_timeout_claimed_by_client(self) -> None:
        protocol = load_module()
        request = _request()
        client = _receipt([
            *_headers(request),
            ("runtimeStarted", "true", "Boolean"),
            ("probeEntered", "true", "Boolean"),
            ("serverCallIssued", "true", "Boolean"),
            ("serverReached", "true", "Boolean"),
            ("caseStarted", "true", "Boolean"),
            ("failureClass", "timeoutAfterCaseStart", "String"),
            ("complete", "true", "Boolean"),
        ])

        with self.assertRaisesRegex(protocol.ProtocolError, "unsupported failure class"):
            protocol.validate_terminal(request, client, None)

    def test_validate_terminal_rejects_server_receipt_on_typed_client_failure(self) -> None:
        protocol = load_module()
        request = _request()
        client = _receipt([
            *_headers(request),
            ("runtimeStarted", "true", "Boolean"),
            ("probeEntered", "true", "Boolean"),
            ("serverCallIssued", "true", "Boolean"),
            ("failureClass", "serverCallFailure", "String"),
            ("complete", "true", "Boolean"),
        ])

        with self.assertRaisesRegex(protocol.ProtocolError, "server receipt"):
            protocol.validate_terminal(request, client, b"not-a-receipt\r\n")

    def test_validate_terminal_rejects_unicode_line_separator(self) -> None:
        protocol = load_module()
        request = _request()
        payload = ("###".join(("protocolVersion", "issue38-v5", "String")) + "\u0085").encode("utf-8")

        with self.assertRaisesRegex(protocol.ProtocolError, "line delimiters"):
            protocol.validate_terminal(request, payload, None)


def _managed_module() -> str:
    return '''Procedure OnStart()
	// StandardSubsystems
#If MobileClient Then
	Execute("StandardSubsystemsClient.OnStart()");
#Else
	StandardSubsystemsClient.OnStart();
#EndIf
	// End StandardSubsystems
EndProcedure
'''


def _success_receipts(request: dict[str, object]) -> tuple[bytes, bytes]:
    token = "server-token-01"
    return (
        _receipt([
            *_headers(request),
            ("runtimeStarted", "true", "Boolean"),
            ("probeEntered", "true", "Boolean"),
            ("serverCallIssued", "true", "Boolean"),
            ("serverReached", "true", "Boolean"),
            ("caseStarted", "true", "Boolean"),
            ("businessResult", token, "String"),
            ("complete", "true", "Boolean"),
        ]),
        _receipt([
            *_headers(request),
            ("serverReached", "true", "Boolean"),
            ("caseStarted", "true", "Boolean"),
            ("businessResult", token, "String"),
            ("complete", "true", "Boolean"),
        ]),
    )


def _runner_with_invalid_receipts(root: Path) -> subprocess.CompletedProcess[str]:
    evidence = root / ".local/runs/native-cycle/run-protocol-error/run/evidence"
    evidence.mkdir(parents=True)
    receipt = evidence / "receipt.txt"
    receipt.write_bytes(b"invalid\r\n")
    receipt.with_name("receipt.txt.server").write_bytes(b"invalid\r\n")
    return subprocess.CompletedProcess(
        [], 0, json.dumps({"preparedInvocation": {"invocationRoot": ".local/runs/native-cycle/run-protocol-error"}}), "",
    )


def _request() -> dict[str, object]:
    return {
        "protocolVersion": "issue38-v5", "runId": "11111111-1111-4111-8111-111111111111",
        "caseId": "22222222-2222-4222-8222-222222222222", "nonce": "33333333-3333-4333-8333-333333333333",
        "operation": "serverWitness", "requiresServer": True,
    }


def _headers(request: dict[str, object]) -> list[tuple[str, str, str]]:
    return [
        ("protocolVersion", str(request["protocolVersion"]), "String"),
        ("runId", str(request["runId"]), "String"),
        ("caseId", str(request["caseId"]), "String"),
        ("nonce", str(request["nonce"]), "String"),
        ("operation", str(request["operation"]), "String"),
    ]


def _receipt(rows: list[tuple[str, str, str]]) -> bytes:
    return ("\r\n".join("###".join(row) for row in rows) + "\r\n").encode("utf-8")


if __name__ == "__main__":
    unittest.main()
