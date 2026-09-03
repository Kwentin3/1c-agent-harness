from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import managed_probe_prepare as preparation
import native_cycle
import shared_task_route as route
sys.path.pop(0)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _receipt() -> dict[str, object]:
    identity = {"files": 2, "directories": 1, "bytes": 7, "sha256": "a" * 64}
    request = {"runId": "11111111-1111-4111-8111-111111111111", "nonce": "22222222-2222-4222-8222-222222222222"}
    client = b"client\n"
    server = b"server\n"
    return {
        "version": 1,
        "canonical": {"files": 2, "sha256": "b" * 64},
        "patches": [
            {"role": "production", "sha256": "c" * 64},
            {"role": "instrumentation", "sha256": "d" * 64},
        ],
        "input": {"prepared": identity, "runner": identity, "frozen": identity},
        "request": {"sha256": route._json_sha(request), "payload": request},
        "result": {
            "client": {"bytes": len(client), "sha256": _sha(client), "base64": base64.b64encode(client).decode()},
            "server": {"bytes": len(server), "sha256": _sha(server), "base64": base64.b64encode(server).decode()},
            "business": {"accepted": True},
            "oracle": {"status": "PASS", "task": "sample"},
        },
        "cleanup": {"runner": {"status": "completed", "manualCleanupActions": 0}, "prepared": "discarded"},
    }


class SharedTaskRouteTests(unittest.TestCase):
    def test_committed_final_command_receipt_is_valid(self) -> None:
        receipt = json.loads((
            ROOT / "experiments/issue48-kiss-receipt/receipt.json"
        ).read_text(encoding="utf-8"))
        route.validate_receipt(receipt)
        request = json.loads((
            ROOT / "experiments/issue48-kiss-receipt/request.json"
        ).read_text(encoding="utf-8"))
        self.assertEqual(receipt["request"]["payload"], request)
        self.assertEqual(receipt["result"]["oracle"]["status"], "PASS")

    def test_one_call_owns_prepare_identity_runner_oracle_receipt_and_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            source = repo / "snapshot"
            source.mkdir()
            (source / "A.txt").write_text("base\n", encoding="utf-8")
            task = repo / "task"
            task.mkdir()
            production = task / "production.patch"
            instrumentation = task / "instrumentation.patch"
            oracle = task / "oracle.py"
            request_path = task / "request.json"
            production.write_bytes(b"--- a/A.txt\n+++ b/A.txt\n@@ -1 +1 @@\n-base\n+product\n")
            instrumentation.write_bytes(b"--- a/A.txt\n+++ b/A.txt\n@@ -1 +1 @@\n-product\n+instrumented\n")
            oracle.write_text("# opaque task oracle\n", encoding="utf-8")
            request = {"runId": "11111111-1111-4111-8111-111111111111", "nonce": "22222222-2222-4222-8222-222222222222"}
            request_path.write_text(json.dumps(request), encoding="utf-8")
            calls: list[list[str]] = []
            prepared_seen: Path | None = None

            def fake(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                nonlocal prepared_seen
                calls.append(command)
                if "run-prepared" in command:
                    self.assertNotIn("--complete-marker", command)
                    relative = Path(command[command.index("--input-tree") + 1])
                    prepared_seen = repo / relative
                    self.assertTrue(prepared_seen.is_dir())
                    self.assertEqual((prepared_seen / "A.txt").read_text(), "instrumented\n")

                    def fake_cycle(plan: SimpleNamespace, spec_path: Path) -> dict[str, object]:
                        self.assertEqual(
                            plan.complete_marker,
                            native_cycle.CANONICAL_COMPLETE_MARKER,
                        )
                        self.assertEqual(
                            json.loads(spec_path.read_text(encoding="utf-8"))["completeMarker"],
                            native_cycle.CANONICAL_COMPLETE_MARKER,
                        )
                        plan.receipt.parent.mkdir(parents=True)
                        plan.receipt.write_bytes(b"client\n")
                        plan.receipt.with_name("receipt.txt.server").write_bytes(b"server\n")
                        return {
                            "schemaVersion": 1,
                            "status": "runtime_contract_completed",
                            "durationSeconds": 0.0,
                            "inputAfter": native_cycle.tree_identity(plan.input_tree),
                        }

                    with mock.patch.object(native_cycle, "run_cycle", side_effect=fake_cycle):
                        runner = native_cycle.run_prepared(
                            repo,
                            relative.as_posix(),
                            int(command[command.index("--timeout-seconds") + 1]),
                        )
                    return subprocess.CompletedProcess(command, 0, json.dumps(runner), "")
                return subprocess.CompletedProcess(command, 0, json.dumps({
                    "status": "PASS", "task": "sample", "businessPayload": {"accepted": True},
                }), "")

            output = task / "receipt.json"
            receipt = route.run_task(
                repo_root=repo, input_tree=source, request_path=request_path,
                patch_paths=[("production", production), ("instrumentation", instrumentation)],
                oracle_path=oracle, receipt_path=output, timeout_seconds=30, execute=fake,
            )

            self.assertEqual(request, receipt["request"]["payload"])
            self.assertTrue(set(request).isdisjoint({"preparedTree", "changedPaths", "treeIdentity"}))
            self.assertEqual(receipt["input"]["prepared"], receipt["input"]["frozen"])
            self.assertEqual(receipt["result"]["business"], {"accepted": True})
            self.assertTrue(output.is_file())
            self.assertIsNotNone(prepared_seen)
            self.assertFalse(prepared_seen.exists())
            self.assertEqual(["run-prepared" in command for command in calls], [True, False])

    def test_cli_has_no_prepared_tree_or_prepare_command(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts/shared_task_route.py"), "--help"],
            text=True, capture_output=True, timeout=10,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertNotIn("--prepared-tree", completed.stdout)
        self.assertNotIn("--complete-marker", completed.stdout)
        self.assertNotIn("prepare", completed.stdout)

    def test_cli_rejects_retired_marker_before_preparation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            source = repo / "snapshot"
            source.mkdir()
            (source / "A.txt").write_text("base\n", encoding="utf-8")
            task = repo / "task"
            task.mkdir()
            for name in ("request.json", "production.patch", "instrumentation.patch", "oracle.py"):
                (task / name).write_text("placeholder\n", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable, str(ROOT / "scripts/shared_task_route.py"), "run",
                    "--repo-root", str(repo),
                    "--input-tree", "snapshot",
                    "--request", "task/request.json",
                    "--production-patch", "task/production.patch",
                    "--instrumentation-patch", "task/instrumentation.patch",
                    "--oracle", "task/oracle.py",
                    "--receipt", ".local/task/receipt.json",
                    "--complete-marker", "complete###true",
                ],
                text=True, capture_output=True, timeout=10,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertIn("unrecognized arguments: --complete-marker", completed.stderr)
            self.assertFalse((repo / ".local").exists())

    def test_receipt_rejects_common_stale_partial_and_cleanup_mismatches(self) -> None:
        mutations = (
            lambda value: value.pop("patches"),
            lambda value: value["request"].__setitem__("sha256", "0" * 64),
            lambda value: value["result"]["client"].__setitem__("sha256", "0" * 64),
            lambda value: value["result"]["oracle"].__setitem__("status", "FAIL"),
            lambda value: value["cleanup"].__setitem__("prepared", "retained"),
            lambda value: value["cleanup"]["runner"].__setitem__("status", "failed"),
        )
        for mutate in mutations:
            candidate = copy.deepcopy(_receipt())
            mutate(candidate)
            with self.assertRaises((ValueError, KeyError, TypeError)):
                route.validate_receipt(candidate)

    def test_shared_route_contains_no_representative_business_grammar(self) -> None:
        source = (ROOT / "scripts/shared_task_route.py").read_text(encoding="utf-8")
        for term in ("SupplierInvoice", "Warehouse", "Purchases", "InventoryCost"):
            self.assertNotIn(term, source)

    def test_exact_patch_preparation_is_still_fail_closed_inside_ignored_local_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / ".gitignore").write_text(".local/\n", encoding="utf-8")
            source = repo / "snapshot"
            source.mkdir()
            (source / "A.txt").write_text("before\n", encoding="utf-8")
            prepared = repo / ".local/prepared/task"
            audit = preparation.prepare_patched_tree(
                repo_root=repo, snapshot_root=source, prepared_root=prepared,
                patches=[("production", b"--- a/A.txt\n+++ b/A.txt\n@@ -1 +1 @@\n-before\n+after\n")],
            )
            self.assertEqual(audit["changedPaths"], ["A.txt"])
            self.assertEqual((prepared / "A.txt").read_text(), "after\n")


if __name__ == "__main__":
    unittest.main()
