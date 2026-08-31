from __future__ import annotations

import base64
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "issue38_protocol.py"
FRONTDOOR_PATH = ROOT / "scripts" / "issue38_frontdoor.py"


def load_module() -> object:
    spec = importlib.util.spec_from_file_location("issue38_protocol_under_test", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load Issue 38 protocol module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
            prepared = root / "prepared"
            request_path = root / "evidence/request.json"
            completed = subprocess.run(
                [
                    sys.executable, str(FRONTDOOR_PATH), "prepare",
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
