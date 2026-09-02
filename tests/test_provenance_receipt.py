from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("provenance_receipt", ROOT / "scripts/shared_task_route.py")
assert SPEC and SPEC.loader
N = importlib.util.module_from_spec(SPEC)
import sys
sys.path.insert(0, str(ROOT / "scripts"))
SPEC.loader.exec_module(N)
sys.path.pop(0)
PREPARATION_SPEC = importlib.util.spec_from_file_location(
    "managed_probe_prepare_for_receipt_tests",
    ROOT / "scripts/managed_probe_prepare.py",
)
assert PREPARATION_SPEC and PREPARATION_SPEC.loader
P = importlib.util.module_from_spec(PREPARATION_SPEC)
PREPARATION_SPEC.loader.exec_module(P)


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sample() -> dict[str, object]:
    identity = {"files": 3, "directories": 2, "bytes": 19, "sha256": "a" * 64}
    request = {"runId": "11111111-1111-4111-8111-111111111111", "nonce": "22222222-2222-4222-8222-222222222222"}
    client = b"client-current\n"
    server = b"server-business\n"
    payload = {"posted": "No", "movements": 0}
    return N.build_provenance_receipt(
        preparation={
            "canonicalBase": {"files": 5099, "sha256": "b" * 64},
            "patches": [
                {"role": "production", "sha256": "c" * 64},
                {"role": "instrumentation", "sha256": "d" * 64},
            ],
            "changedPaths": ["A.bsl", "B.bsl"],
            "runnerInput": identity,
        },
        request=request,
        runner={
            "status": "runtime_contract_completed",
            "preparedInvocation": {
                "sourceBefore": identity,
                "sourceAfter": identity,
                "copiedBeforeFreeze": identity,
                "frozenInput": {"identity": identity},
            },
            "inputAfter": identity,
            "runtime": {"completed": True, "receiptSha256": sha(client), "receiptBytes": len(client)},
            "storageCompaction": {"status": "completed", "manualCleanupActions": 0},
        },
        client_receipt=client,
        server_receipt=server,
        business_payload=payload,
        oracle={"status": "PASS"},
        prepared_cleanup="discarded",
    )


class ProvenanceReceiptTests(unittest.TestCase):
    def test_shared_route_owns_prepare_runner_oracle_receipt_and_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            source = repo / "snapshot"
            source.mkdir()
            (source / "A.txt").write_text("base\n", encoding="utf-8")
            production = repo / "task/production.patch"
            instrumentation = repo / "task/instrumentation.patch"
            oracle = repo / "task/oracle.py"
            production.parent.mkdir()
            production.write_bytes(
                b"--- a/A.txt\n+++ b/A.txt\n@@ -1 +1 @@\n-base\n+product\n"
            )
            instrumentation.write_bytes(
                b"--- a/A.txt\n+++ b/A.txt\n@@ -1 +1 @@\n-product\n+instrumented\n"
            )
            oracle.write_text("# task-owned oracle\n", encoding="utf-8")
            prepared = repo / ".local/prepared/task"

            probe = P.prepare_patched_tree(
                repo_root=repo,
                snapshot_root=source,
                prepared_root=prepared,
                patches=[
                    ("production", production.read_bytes()),
                    ("instrumentation", instrumentation.read_bytes()),
                ],
            )
            identity = N.native_cycle.tree_identity(prepared)
            P.discard_prepared_tree(repo_root=repo, prepared_root=prepared)
            request = {
                "runId": "11111111-1111-4111-8111-111111111111",
                "preparedTree": ".local/prepared/task",
                "changedPaths": probe["changedPaths"],
                "treeIdentity": identity["sha256"],
            }
            request_path = repo / "task/request.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            calls: list[list[str]] = []

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                calls.append(command)
                if "run-prepared" in command:
                    invocation = repo / ".local/runs/native-cycle/run-test"
                    evidence = invocation / "run/evidence"
                    evidence.mkdir(parents=True)
                    (evidence / "receipt.txt").write_bytes(b"client\n")
                    (evidence / "receipt.txt.server").write_bytes(b"server\n")
                    runner = {
                        "status": "runtime_contract_completed",
                        "preparedInvocation": {
                            "invocationRoot": ".local/runs/native-cycle/run-test",
                            "sourceBefore": identity,
                            "sourceAfter": identity,
                            "copiedBeforeFreeze": identity,
                            "frozenInput": {"identity": identity},
                        },
                        "inputAfter": identity,
                        "runtime": {"completed": True},
                        "storageCompaction": {
                            "status": "completed",
                            "manualCleanupActions": 0,
                        },
                    }
                    return subprocess.CompletedProcess(command, 0, json.dumps(runner), "")
                oracle_result = {
                    "status": "PASS",
                    "task": "sample",
                    "businessPayload": {"accepted": True},
                }
                return subprocess.CompletedProcess(command, 0, json.dumps(oracle_result), "")

            receipt_path = repo / "task/receipt.json"
            receipt = N.run_task(
                repo_root=repo,
                input_tree=source,
                prepared_tree=prepared,
                request_path=request_path,
                patch_paths=[
                    ("production", production),
                    ("instrumentation", instrumentation),
                ],
                complete_marker="complete###true",
                oracle_path=oracle,
                receipt_path=receipt_path,
                timeout_seconds=30,
                run_command=fake_run,
            )

            self.assertEqual(receipt["business"]["payload"], {"accepted": True})
            self.assertEqual(receipt["patches"], [
                {"role": "production", "sha256": sha(production.read_bytes())},
                {"role": "instrumentation", "sha256": sha(instrumentation.read_bytes())},
            ])
            self.assertTrue(receipt_path.is_file())
            self.assertFalse(prepared.exists())
            self.assertIn("run-prepared", calls[0])
            self.assertEqual(calls[1][1], str(oracle))
            self.assertIn("--client-receipt", calls[1])
            self.assertIn("--server-receipt", calls[1])

    def test_shared_preparation_applies_exact_patch_bytes_and_freezes_the_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            source = repo / "snapshot"
            source.mkdir()
            (source / "A.txt").write_text("before-a\n", encoding="utf-8")
            (source / "B.txt").write_text("before-b\n", encoding="utf-8")
            prepared = repo / ".local/prepared/task"
            patch_a = b"--- a/A.txt\n+++ b/A.txt\n@@ -1 +1 @@\n-before-a\n+after-a\n"
            patch_b = b"--- a/B.txt\n+++ b/B.txt\n@@ -1 +1 @@\n-before-b\n+after-b\n"

            audit = P.prepare_patched_tree(
                repo_root=repo,
                snapshot_root=source,
                prepared_root=prepared,
                patches=[("production", patch_a), ("instrumentation", patch_b)],
            )

            self.assertEqual((prepared / "A.txt").read_text(), "after-a\n")
            self.assertEqual((prepared / "B.txt").read_text(), "after-b\n")
            self.assertEqual(audit["changedPaths"], ["A.txt", "B.txt"])
            self.assertEqual(audit["patches"], [
                {"role": "production", "sha256": sha(patch_a)},
                {"role": "instrumentation", "sha256": sha(patch_b)},
            ])
            self.assertNotEqual(audit["canonicalBase"], audit["preparedInput"])
            self.assertTrue(all(not (path.stat().st_mode & 0o222) for path in (prepared, *prepared.rglob("*"))))

    def test_shared_preparation_does_not_escape_to_an_enclosing_git_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / ".gitignore").write_text(".local/\n", encoding="utf-8")
            source = repo / "snapshot"
            source.mkdir()
            (source / "A.txt").write_text("before\n", encoding="utf-8")
            prepared = repo / ".local/prepared/task"
            patch = b"--- a/A.txt\n+++ b/A.txt\n@@ -1 +1 @@\n-before\n+after\n"
            prepared.parent.mkdir(parents=True)
            prepared.mkdir()
            (prepared / "A.txt").write_text("before\n", encoding="utf-8")
            ignored = subprocess.run(
                ["git", "check-ignore", "-q", str(prepared / "A.txt")], cwd=repo,
            )
            self.assertEqual(ignored.returncode, 0, "regression fixture must be ignored by the enclosing worktree")
            (prepared / "A.txt").unlink()
            prepared.rmdir()

            audit = P.prepare_patched_tree(
                repo_root=repo,
                snapshot_root=source,
                prepared_root=prepared,
                patches=[("production", patch)],
            )

            self.assertEqual((source / "A.txt").read_text(), "before\n")
            self.assertEqual((prepared / "A.txt").read_text(), "after\n")
            self.assertEqual(audit["changedPaths"], ["A.txt"])

    def test_shared_preparation_rejects_a_patch_that_does_not_apply(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            source = repo / "snapshot"
            source.mkdir()
            (source / "A.txt").write_text("actual\n", encoding="utf-8")
            prepared = repo / ".local/prepared/task"
            stale = b"--- a/A.txt\n+++ b/A.txt\n@@ -1 +1 @@\n-stale\n+changed\n"
            with self.assertRaises(ValueError):
                P.prepare_patched_tree(
                    repo_root=repo,
                    snapshot_root=source,
                    prepared_root=prepared,
                    patches=[("production", stale)],
                )
            self.assertFalse(prepared.exists())

    def test_shared_preparation_rejects_overlapping_source_and_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            source = repo / ".local/prepared/source"
            source.mkdir(parents=True)
            (source / "A.txt").write_text("before\n", encoding="utf-8")
            patch = b"--- a/A.txt\n+++ b/A.txt\n@@ -1 +1 @@\n-before\n+after\n"
            with self.assertRaisesRegex(ValueError, "must be disjoint"):
                P.prepare_patched_tree(
                    repo_root=repo,
                    snapshot_root=source,
                    prepared_root=source / "child",
                    patches=[("production", patch)],
                )
            self.assertEqual((source / "A.txt").read_text(), "before\n")

    def test_compact_receipt_binds_the_complete_shared_chain(self) -> None:
        receipt = sample()
        self.assertEqual(N.validate_provenance_receipt(receipt)["status"], "PASS")
        self.assertEqual(receipt["schemaVersion"], 1)
        self.assertEqual(receipt["business"]["payload"], {"posted": "No", "movements": 0})
        self.assertEqual(base64.b64decode(receipt["business"]["rawReceipt"]["base64"]), b"server-business\n")

    def test_stale_foreign_partial_patch_input_runtime_and_cleanup_are_rejected(self) -> None:
        mutations = [
            ("stale request", lambda r: r["request"].__setitem__("sha256", "0" * 64)),
            ("duplicate patch", lambda r: r["patches"].append(copy.deepcopy(r["patches"][0]))),
            ("input mismatch", lambda r: r["input"]["frozen"].__setitem__("sha256", "0" * 64)),
            ("runtime status", lambda r: r["runtime"].__setitem__("status", "runtime_timeout")),
            ("runtime completion", lambda r: r["runtime"].__setitem__("completed", False)),
            ("cleanup", lambda r: r["cleanup"]["runner"].__setitem__("status", "failed")),
            ("prepared cleanup", lambda r: r["cleanup"].__setitem__("preparedTree", "retained")),
            ("raw receipt", lambda r: r["business"]["rawReceipt"].__setitem__("sha256", "0" * 64)),
            ("oracle", lambda r: r["oracle"].__setitem__("status", "FAIL")),
            ("partial", lambda r: r.pop("patches")),
        ]
        for name, mutate in mutations:
            with self.subTest(mutation=name):
                receipt = copy.deepcopy(sample())
                mutate(receipt)
                with self.assertRaises((ValueError, KeyError, TypeError)):
                    N.validate_provenance_receipt(receipt)

    def test_oracle_binding_rejects_wrong_identity_or_business_payload(self) -> None:
        for section in ("requestSha256", "businessPayloadSha256", "serverReceiptSha256"):
            receipt = sample()
            receipt["oracle"][section] = "0" * 64
            with self.subTest(section=section), self.assertRaises(ValueError):
                N.validate_provenance_receipt(receipt)
    def test_task_oracle_rejects_coordinated_identity_and_business_lies(self) -> None:
        task_dir = ROOT / "experiments/issue48-kiss-receipt"
        oracle_spec = importlib.util.spec_from_file_location("issue48_task_oracle", task_dir / "oracle.py")
        assert oracle_spec and oracle_spec.loader
        oracle = importlib.util.module_from_spec(oracle_spec)
        oracle_spec.loader.exec_module(oracle)
        original = json.loads((task_dir / "receipt.json").read_text(encoding="utf-8"))
        oracle.validate(original)
        mutations = []
        identity = copy.deepcopy(original)
        identity["request"]["payload"]["runId"] = "99999999-9999-4999-8999-999999999999"
        identity["request"]["sha256"] = N._canonical_sha256(identity["request"]["payload"])
        identity["oracle"]["requestSha256"] = identity["request"]["sha256"]
        mutations.append(identity)
        business = copy.deepcopy(original)
        business["business"]["payload"]["activePosted"] = "No"
        business["business"]["payloadSha256"] = N._canonical_sha256(business["business"]["payload"])
        business["oracle"]["businessPayloadSha256"] = business["business"]["payloadSha256"]
        mutations.append(business)
        patch = copy.deepcopy(original)
        patch["patches"][0]["sha256"] = "0" * 64
        mutations.append(patch)
        for receipt in mutations:
            self.assertEqual(N.validate_provenance_receipt(receipt)["status"], "PASS")
            with self.assertRaises(ValueError):
                oracle.validate(receipt)

    def test_task_oracle_cli_accepts_the_frozen_raw_route_inputs(self) -> None:
        task_dir = ROOT / "experiments/issue48-kiss-receipt"
        receipt = json.loads((task_dir / "receipt.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request = root / "request.json"
            client = root / "client.txt"
            server = root / "server.txt"
            request.write_text(json.dumps(receipt["request"]["payload"]), encoding="utf-8")
            client.write_bytes(base64.b64decode(receipt["runtime"]["clientReceipt"]["base64"]))
            server.write_bytes(base64.b64decode(receipt["business"]["rawReceipt"]["base64"]))
            completed = subprocess.run(
                [
                    sys.executable,
                    str(task_dir / "oracle.py"),
                    "--request", str(request),
                    "--client-receipt", str(client),
                    "--server-receipt", str(server),
                ],
                text=True,
                capture_output=True,
                timeout=10,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["businessPayload"], receipt["business"]["payload"])

    def test_shared_route_contains_no_representative_business_grammar(self) -> None:
        source = (ROOT / "scripts/shared_task_route.py").read_text(encoding="utf-8")
        for term in ("SupplierInvoice", "Warehouse", "Purchases", "InventoryCost"):
            self.assertNotIn(term, source)

    def test_frozen_issue46_red_green_repeat_project_to_the_same_contract(self) -> None:
        package = ROOT / "experiments/issue46-supplier-warehouse-core-loop"
        validate_spec = importlib.util.spec_from_file_location("issue46_frozen", package / "validate.py")
        assert validate_spec and validate_spec.loader
        frozen = importlib.util.module_from_spec(validate_spec)
        validate_spec.loader.exec_module(frozen)
        self.assertEqual(frozen.validate(package)["status"], "PASS")
        evidence = json.loads((package / "evidence.json").read_text(encoding="utf-8"))
        for lane_name in ("red", "green", "repeat"):
            lane = evidence["lanes"][lane_name]
            patches = [{"role": "instrumentation", "sha256": lane["binding"]["instrumentationPatchSha256"]}]
            if lane["binding"]["productionPatchSha256"] is not None:
                patches.insert(0, {"role": "production", "sha256": lane["binding"]["productionPatchSha256"]})
            runner = dict(lane["runner"])
            runner["preparedInvocation"] = {
                "sourceBefore": lane["runner"]["sourceBefore"],
                "sourceAfter": lane["runner"]["sourceAfter"],
                "copiedBeforeFreeze": lane["runner"]["copiedBeforeFreeze"],
                "frozenInput": {"identity": lane["runner"]["frozenInput"]},
            }
            receipt = N.build_provenance_receipt(
                preparation={
                    "canonicalBase": {
                        "files": evidence["contract"]["snapshotFiles"],
                        "sha256": evidence["contract"]["snapshotManifestSha256"],
                    },
                    "patches": patches,
                    "changedPaths": lane["request"]["changedPaths"],
                    "runnerInput": lane["binding"]["runnerInput"],
                },
                request=lane["request"],
                runner=runner,
                client_receipt=base64.b64decode(lane["clientReceipt"]["base64"]),
                server_receipt=base64.b64decode(lane["serverReceipt"]["base64"]),
                business_payload=lane["business"],
                oracle={"status": "PASS", "task": "issue46", "lane": lane_name},
                prepared_cleanup="discarded",
            )
            with self.subTest(lane=lane_name):
                self.assertEqual(N.validate_provenance_receipt(receipt)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
