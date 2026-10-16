"""Real artifact admission/composition tests; the native execution seam is isolated."""
from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

from one_c_harness import companion, target_admission, task_artifacts
from test_task_artifacts import fixture


class CompanionTaskArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.addCleanup(self.cleanup)
        self.snapshot_ref = fixture(self.root)
        self.snapshot = self.root / self.snapshot_ref["snapshot"]["root"]
        self.source_before = target_admission.tree_manifest(self.snapshot)
        self.arguments = {
            "snapshotRef": self.snapshot_ref,
            "request": {"nonce": "composition-only", "expected": "marker"},
            "productionPatch": "unexecuted production data\n",
            "instrumentationPatch": "unexecuted instrumentation data\n",
            "oracle": "experiments/sample/oracle.py",
        }

    def cleanup(self) -> None:
        if self.root.exists():
            for path in [self.root, *self.root.rglob("*")]:
                if not path.is_symlink():
                    path.chmod(path.stat().st_mode | stat.S_IRWXU)
        self.temporary.cleanup()

    def execute(self, operation: str, arguments: dict[str, object]) -> dict[str, object]:
        return companion.execute(json.dumps({
            "schemaVersion": 1, "operation": operation, "arguments": arguments,
        }).encode("utf-8"), self.root)

    def stage(self) -> dict[str, object]:
        response = self.execute("stage_task", self.arguments)
        self.assertEqual(response["status"], "ok", response)
        return response["taskRef"]

    def verify_args(self, reference: dict[str, object]) -> dict[str, object]:
        return {"snapshotRef": self.snapshot_ref, "taskRef": reference, "timeoutSeconds": 17}

    def resolve(self, reference: dict[str, object]) -> dict[str, object]:
        return task_artifacts.resolve_task(
            repo_root=self.root, snapshot_ref=self.snapshot_ref, task_ref=reference,
        )

    def test_stage_front_door_publishes_only_bound_data_without_native_execution(self) -> None:
        with mock.patch.object(companion.shared_task_route, "run_task") as native:
            reference = self.stage()
        native.assert_not_called()
        resolved = self.resolve(reference)
        self.assertEqual(json.loads((self.root / resolved["request_path"]).read_bytes()), self.arguments["request"])
        self.assertEqual((self.root / resolved["patch_paths"][0][1]).read_text(), self.arguments["productionPatch"])
        self.assertFalse((self.root / resolved["receipt_path"]).exists())
        self.assertEqual(target_admission.tree_manifest(self.snapshot), self.source_before)

    def test_staged_verify_uses_existing_runner_once_under_real_lock_then_refuses_replay(self) -> None:
        reference = self.stage()
        resolved = self.resolve(reference)
        receipt = {"cleanup": {"status": "discarded"}, "result": {"oracle": {"status": "passed"}}}
        receipt_bytes = json.dumps(receipt).encode()

        def run_task(**arguments):
            self.assertEqual(arguments, {**resolved, "timeout_seconds": 17})
            with (self.root / resolved["request_path"]).open("rb") as second:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(second, fcntl.LOCK_EX | fcntl.LOCK_NB)
            (self.root / resolved["receipt_path"]).write_bytes(receipt_bytes)
            return receipt

        with mock.patch.object(companion.shared_task_route, "run_task", side_effect=run_task) as native:
            response = self.execute("verify", self.verify_args(reference))
            replay = self.execute("verify", self.verify_args(reference))
        self.assertEqual(native.call_count, 1)
        self.assertEqual(response["status"], "ok", response)
        self.assertEqual(response["receipt"], {
            "path": resolved["receipt_path"].as_posix(), "sha256": hashlib.sha256(receipt_bytes).hexdigest(),
        })
        self.assertEqual(response["cleanup"], receipt["cleanup"])
        self.assertEqual(response["oracleStatus"], "passed")
        self.assertEqual(replay["status"], "blocked")
        self.assertEqual(target_admission.tree_manifest(self.snapshot), self.source_before)

    def test_busy_task_is_refused_before_native_execution_and_lock_is_not_removed(self) -> None:
        reference = self.stage()
        resolved = self.resolve(reference)
        path = self.root / resolved["request_path"]
        inode = path.stat().st_ino
        with path.open("rb") as holder:
            fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with mock.patch.object(companion.shared_task_route, "run_task") as native:
                response = self.execute("verify", self.verify_args(reference))
            native.assert_not_called()
        self.assertEqual(response["reasonCode"], "task_busy")
        self.assertEqual(path.stat().st_ino, inode)
        self.resolve(reference)

    def test_operator_selected_oracle_root_reaches_stage_and_existing_runner(self) -> None:
        relative = ".local/installed-source/candidate"
        oracle = self.root / relative / self.arguments["oracle"]
        oracle.parent.mkdir(parents=True)
        oracle.write_bytes((self.root / self.arguments["oracle"]).read_bytes())
        oracle.chmod(0o444)
        with mock.patch.dict(os.environ, {"ONE_C_HARNESS_TASK_ORACLE_ROOT": relative}):
            reference = self.stage()
            resolved = task_artifacts.resolve_task(
                repo_root=self.root, snapshot_ref=self.snapshot_ref,
                task_ref=reference, oracle_root=relative,
            )
            self.assertEqual(resolved["oracle_path"], Path(relative) / self.arguments["oracle"])

            def run_task(**arguments):
                self.assertEqual(arguments, {**resolved, "timeout_seconds": 17})
                receipt = {"cleanup": {}, "result": {"oracle": {"status": "PASS"}}}
                (self.root / resolved["receipt_path"]).write_text(json.dumps(receipt))
                return receipt

            with mock.patch.object(companion.shared_task_route, "run_task", side_effect=run_task) as native:
                response = self.execute("verify", self.verify_args(reference))
            native.assert_called_once()
            self.assertEqual(response["oracleStatus"], "PASS", response)

    def test_tool_arguments_cannot_select_operator_oracle_root(self) -> None:
        response = self.execute("stage_task", {**self.arguments, "oracleRoot": ".local/arbitrary"})
        self.assertEqual(response["reasonCode"], "invalid_request")
        self.assertFalse((self.root / task_artifacts.TASK_NAMESPACE).exists())

    def test_configured_oracle_root_refuses_legacy_path_form_before_runner(self) -> None:
        legacy = {
            "snapshotRef": self.snapshot_ref, "request": "operator/request.json",
            "productionPatch": "operator/production.patch", "instrumentationPatch": "operator/instrumentation.patch",
            "oracle": "experiments/sample/oracle.py", "receipt": ".local/operator-receipt.json", "timeoutSeconds": 17,
        }
        with mock.patch.dict(os.environ, {"ONE_C_HARNESS_TASK_ORACLE_ROOT": ".local/installed-source/candidate"}):
            with mock.patch.object(companion.shared_task_route, "run_task") as native:
                response = self.execute("verify", legacy)
        native.assert_not_called()
        self.assertEqual(response["reasonCode"], "invalid_request")
        self.assertFalse((self.root / task_artifacts.TASK_NAMESPACE).exists())

    def test_changed_input_is_refused_before_existing_runner(self) -> None:
        reference = self.stage()
        path = self.root / self.resolve(reference)["request_path"]
        path.chmod(0o600)
        path.write_bytes(b'{"nonce":"different"}')
        path.chmod(0o400)
        with mock.patch.object(companion.shared_task_route, "run_task") as native:
            response = self.execute("verify", self.verify_args(reference))
        native.assert_not_called()
        self.assertEqual(response["status"], "blocked")

    def test_legacy_form_cannot_address_any_managed_task_input_or_receipt(self) -> None:
        reference = self.stage()
        resolved = self.resolve(reference)
        legacy = {
            "snapshotRef": self.snapshot_ref, "request": "operator/request.json",
            "productionPatch": "operator/production.patch", "instrumentationPatch": "operator/instrumentation.patch",
            "oracle": "experiments/sample/oracle.py", "receipt": ".local/operator-receipt.json", "timeoutSeconds": 17,
        }
        managed = resolved["request_path"].as_posix()
        with mock.patch.object(companion.shared_task_route, "run_task") as native:
            for field in ("request", "productionPatch", "instrumentationPatch", "oracle", "receipt"):
                with self.subTest(field=field):
                    response = self.execute("verify", {**legacy, field: managed})
                    self.assertEqual(response["reasonCode"], "invalid_request")
        native.assert_not_called()

    def test_stage_cannot_choose_submitted_data_as_executable_oracle(self) -> None:
        reference = self.stage()
        submitted_patch = self.resolve(reference)["patch_paths"][0][1].as_posix()
        before = set((self.root / task_artifacts.TASK_NAMESPACE).iterdir())
        with mock.patch.object(companion.shared_task_route, "run_task") as native:
            response = self.execute("stage_task", {**self.arguments, "oracle": submitted_patch})
        native.assert_not_called()
        self.assertEqual(response["status"], "blocked")
        self.assertEqual(set((self.root / task_artifacts.TASK_NAMESPACE).iterdir()), before)

    def test_closed_forms_refuse_mixed_keys_and_invalid_timeout_without_native(self) -> None:
        reference = self.stage()
        base = self.verify_args(reference)
        variants = [{**base, "oracle": "experiments/sample/oracle.py"}, {k: v for k, v in base.items() if k != "taskRef"}]
        variants += [{**base, "timeoutSeconds": value} for value in (0, 481, True, "17")]
        with mock.patch.object(companion.shared_task_route, "run_task") as native:
            for arguments in variants:
                with self.subTest(arguments=arguments):
                    response = self.execute("verify", arguments)
                    self.assertEqual(response["reasonCode"], "invalid_request")
            for arguments in ({**self.arguments, "taskRef": reference}, {k: v for k, v in self.arguments.items() if k != "oracle"}):
                response = self.execute("stage_task", arguments)
                self.assertEqual(response["reasonCode"], "invalid_request")
        native.assert_not_called()

    def test_oversized_wire_request_is_refused_before_artifact_creation(self) -> None:
        response = self.execute("stage_task", {**self.arguments, "productionPatch": "x" * companion.MAX_REQUEST_BYTES})
        self.assertEqual(response["reasonCode"], "invalid_request")
        self.assertFalse((self.root / task_artifacts.TASK_NAMESPACE).exists())

    def test_success_without_actual_receipt_is_not_accepted(self) -> None:
        reference = self.stage()
        with mock.patch.object(companion.shared_task_route, "run_task", return_value={"cleanup": {}, "result": {}}) as native:
            response = self.execute("verify", self.verify_args(reference))
        native.assert_called_once()
        self.assertEqual(response["reasonCode"], "invalid_request")
        self.assertNotIn("receipt", response)

    def test_unadmitted_snapshot_cannot_stage_any_data(self) -> None:
        reference = copy.deepcopy(self.snapshot_ref)
        reference["snapshot"]["contentId"] = "sha256:" + "0" * 64
        response = self.execute("stage_task", {**self.arguments, "snapshotRef": reference})
        self.assertEqual(response["status"], "blocked")
        self.assertFalse((self.root / task_artifacts.TASK_NAMESPACE).exists())


if __name__ == "__main__":
    unittest.main()
