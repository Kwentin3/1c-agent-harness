from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "native_cycle.py"


def load_module(name: str = "native_cycle_under_test") -> object:
    spec = importlib.util.spec_from_file_location(name, CLI)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load native cycle module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def process_is_running(pid: int) -> bool:
    status = Path(f"/proc/{pid}/status")
    if not status.exists():
        return False
    state = next(
        (line for line in status.read_text(encoding="utf-8").splitlines() if line.startswith("State:")),
        "",
    )
    return "Z (zombie)" not in state


def freeze_tree(root: Path) -> None:
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_file():
            path.chmod(path.stat().st_mode & ~0o222)
        elif path.is_dir():
            path.chmod(path.stat().st_mode & ~0o222)
    root.chmod(root.stat().st_mode & ~0o222)


def create_fixed_profile(repo: Path, platform_body: str = "binary") -> tuple[Path, Path]:
    platform = repo / ".local/platform/1cv8t/x86_64/8.5.1.1150/1cv8t"
    platform.parent.mkdir(parents=True)
    platform.write_text(platform_body, encoding="utf-8")
    xvfb = repo / ".local/platform/libs/usr/bin/xvfb-run"
    xvfb.parent.mkdir(parents=True)
    xvfb.write_text("script", encoding="utf-8")
    fontconfig = repo / ".local/platform/fonts.conf"
    fontconfig.write_text("fonts", encoding="utf-8")
    (repo / ".local/platform/libs/usr/lib/x86_64-linux-gnu").mkdir(parents=True)
    return platform, xvfb


class NativeCycleContractTests(unittest.TestCase):
    def test_prepare_invocation_freezes_generated_copy_and_binds_receipt_without_mutating_source(self) -> None:
        native_cycle = load_module("native_cycle_prepare_invocation")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            source = repo / ".local" / "prepared" / "case-a"
            (source / "empty").mkdir(parents=True)
            module = source / "Ext" / "ManagedApplicationModule.bsl"
            module.parent.mkdir()
            module.write_text("probe uses LaunchParameter\n", encoding="utf-8")
            source_before = native_cycle.tree_identity(source)
            source_modes_before = {
                path.relative_to(source).as_posix(): stat.S_IMODE(path.lstat().st_mode)
                for path in (source, *source.rglob("*"))
            }

            invocation = native_cycle.prepare_invocation(
                repo,
                ".local/prepared/case-a",
                "complete###true",
                30,
            )

            self.assertEqual(native_cycle.tree_identity(source), source_before)
            self.assertEqual(
                {
                    path.relative_to(source).as_posix(): stat.S_IMODE(path.lstat().st_mode)
                    for path in (source, *source.rglob("*"))
                },
                source_modes_before,
            )
            self.assertTrue(invocation.invocation_root.is_relative_to(repo / ".local/runs/native-cycle"))
            self.assertTrue(invocation.spec_path.is_file())
            self.assertEqual(invocation.source_identity, source_before)
            self.assertEqual(
                invocation.frozen_identity,
                native_cycle.tree_identity(invocation.frozen_input),
            )
            self.assertNotEqual(invocation.source_identity["sha256"], invocation.frozen_identity["sha256"])
            self.assertTrue(all(
                not (path.lstat().st_mode & 0o222)
                for path in (invocation.frozen_input, *invocation.frozen_input.rglob("*"))
            ))
            plan = native_cycle.load_plan(
                invocation.spec_path,
                repo,
                bind_receipt_launch_parameter=True,
            )
            self.assertEqual(plan.input_tree, invocation.frozen_input)
            self.assertFalse(plan.run_root.exists())
            self.assertEqual(plan.runtime_argv.count("/C"), 1)
            launch_index = plan.runtime_argv.index("/C")
            self.assertEqual(plan.runtime_argv[launch_index + 1], str(plan.receipt))

    def test_prepare_invocation_rejects_multiline_completion_marker(self) -> None:
        native_cycle = load_module("native_cycle_multiline_marker")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            source = repo / ".local" / "prepared" / "case-a"
            source.mkdir(parents=True)
            (source / "Configuration.xml").write_text("<Configuration/>\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "single line"):
                native_cycle.prepare_invocation(repo, ".local/prepared/case-a", "complete###true\nextra", 5)

    def test_prepare_invocation_distinguishes_second_read_only_input_shape(self) -> None:
        native_cycle = load_module("native_cycle_second_shape")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            first = repo / ".local" / "prepared" / "first"
            second = repo / ".local" / "prepared" / "second"
            first.mkdir(parents=True)
            (first / "Configuration.xml").write_text("<Configuration/>\n", encoding="utf-8")
            (second / "empty-a" / "empty-b").mkdir(parents=True)
            (second / "Configuration.xml").write_text("<Configuration name='second'/>\n", encoding="utf-8")
            (second / "extra.txt").write_bytes(b"second-shape\n")
            freeze_tree(second)
            second_before = native_cycle.tree_identity(second)

            first_invocation = native_cycle.prepare_invocation(
                repo, ".local/prepared/first", "done", 30,
            )
            second_invocation = native_cycle.prepare_invocation(
                repo, ".local/prepared/second", "done", 30,
            )

            self.assertNotEqual(first_invocation.source_identity, second_invocation.source_identity)
            self.assertNotEqual(first_invocation.frozen_identity, second_invocation.frozen_identity)
            self.assertNotEqual(first_invocation.invocation_root, second_invocation.invocation_root)
            self.assertEqual(native_cycle.tree_identity(second), second_before)
            self.assertEqual(second_invocation.source_identity, second_invocation.frozen_identity)

    def test_run_prepared_special_input_fails_without_native_launch_and_persists_result_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            source = repo / ".local" / "prepared" / "fifo"
            source.mkdir(parents=True)
            os.mkfifo(source / "receipt-channel")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "run-prepared",
                    "--repo-root", str(repo),
                    "--input-tree", ".local/prepared/fifo",
                    "--complete-marker", "complete###true",
                    "--timeout-seconds", "5",
                ],
                text=True,
                capture_output=True,
                timeout=10,
            )

            self.assertEqual(completed.returncode, 1)
            output = json.loads(completed.stdout)
            self.assertEqual(output["status"], "precheck_failed")
            self.assertEqual(output["errorType"], "ValueError")
            self.assertIn("non-regular", output["error"])
            result_path = repo / output["resultPath"]
            self.assertTrue(result_path.is_file())
            self.assertEqual(json.loads(result_path.read_text(encoding="utf-8")), output)
            self.assertFalse((repo / ".local/platform/1cv8t").exists())

    def test_run_prepared_rechecks_source_after_generated_copy_failure(self) -> None:
        native_cycle = load_module("native_cycle_copy_failure_recheck")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            source = repo / ".local" / "prepared" / "case-a"
            source.mkdir(parents=True)
            source_file = source / "Configuration.xml"
            source_file.write_text("<Configuration/>\n", encoding="utf-8")

            def fail_copy(*_args: object, **_kwargs: object) -> None:
                source_file.write_text("<Configuration changed='true'/>\n", encoding="utf-8")
                raise OSError("simulated generated copy failure")

            with mock.patch.object(native_cycle.shutil, "copytree", side_effect=fail_copy):
                with self.assertRaises(OSError) as raised:
                    native_cycle.run_prepared(repo, ".local/prepared/case-a", "complete###true", 5)

            result_path = getattr(raised.exception, "result_path", None)
            self.assertIsNotNone(result_path)
            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "input_changed")
            self.assertEqual(result["failedStage"], "prepared-input-reverify")
            self.assertNotEqual(
                result["preparedInvocation"]["sourceBefore"],
                result["preparedInvocation"]["sourceAfter"],
            )
            self.assertEqual(result["preparedInvocation"]["generatedSpec"]["status"], "absent")
            self.assertIn("totalDurationSeconds", result)
            self.assertEqual(result["resultPath"], result_path.relative_to(repo).as_posix())
            invocation_root = repo / result["preparedInvocation"]["invocationRoot"]
            self.assertFalse((invocation_root / "frozen-input").exists())
            self.assertEqual(result["storageCompaction"]["status"], "completed")

    def test_run_prepared_persists_result_when_generated_plan_preflight_fails(self) -> None:
        native_cycle = load_module("native_cycle_generated_plan_preflight")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            source = repo / ".local" / "prepared" / "case-a"
            source.mkdir(parents=True)
            (source / "Configuration.xml").write_text("<Configuration/>\n", encoding="utf-8")

            with mock.patch.object(
                native_cycle,
                "load_plan",
                side_effect=RuntimeError("simulated procfs preflight failure"),
            ):
                with self.assertRaises(RuntimeError) as raised:
                    native_cycle.run_prepared(repo, ".local/prepared/case-a", "complete###true", 5)

            result_path = getattr(raised.exception, "result_path", None)
            self.assertIsNotNone(result_path)
            self.assertTrue(result_path.is_file())
            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "precheck_failed")
            self.assertEqual(result["failedStage"], "generated-plan-preflight")
            self.assertEqual(result["resultPath"], result_path.relative_to(repo).as_posix())
            self.assertEqual(result["preparedInvocation"]["sourceBefore"], result["preparedInvocation"]["sourceAfter"])
            invocation_root = repo / result["preparedInvocation"]["invocationRoot"]
            self.assertFalse((invocation_root / "frozen-input").exists())
            self.assertEqual(result["storageCompaction"]["status"], "completed")

    def test_run_prepared_failure_compacts_only_current_invocation_and_preserves_diagnostic(self) -> None:
        native_cycle = load_module("native_cycle_failure_compaction")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            source = repo / ".local" / "prepared" / "case-a"
            source.mkdir(parents=True)
            (source / "Configuration.xml").write_text("<Configuration/>\n", encoding="utf-8")
            source_before = native_cycle.tree_identity(source)

            def fake_plan(spec_path: Path, _repo: Path, **_kwargs: object) -> SimpleNamespace:
                invocation_root = spec_path.parent
                receipt = invocation_root / "run" / "evidence" / "receipt.txt"
                return SimpleNamespace(receipt=receipt, runtime_argv=["ENTERPRISE", "/C", str(receipt)])

            def fail_cycle(plan: SimpleNamespace, _spec_path: Path) -> None:
                run_root = plan.receipt.parents[1]
                for name in ("work-copy", "ib", "home", "tmp", "logs", "evidence"):
                    directory = run_root / name
                    directory.mkdir(parents=True, exist_ok=True)
                    (directory / "diagnostic.txt").write_bytes(b"diagnostic\n" * 128)
                result = {
                    "schemaVersion": 1,
                    "status": "runtime_timeout",
                    "failedStage": "runtime",
                    "errorType": "TimeoutError",
                    "error": "simulated timeout",
                }
                native_cycle._write_json_atomic(run_root / "result.json", result)
                raise TimeoutError("simulated timeout")

            with mock.patch.object(native_cycle, "load_plan", side_effect=fake_plan), mock.patch.object(
                native_cycle, "run_cycle", side_effect=fail_cycle
            ):
                with self.assertRaises(TimeoutError) as raised:
                    native_cycle.run_prepared(repo, ".local/prepared/case-a", "complete###true", 5)

            persisted = json.loads(Path(raised.exception.result_path).read_text(encoding="utf-8"))
            invocation_root = repo / persisted["preparedInvocation"]["invocationRoot"]
            self.assertEqual(persisted["status"], "runtime_timeout")
            self.assertEqual(persisted["storageCompaction"]["status"], "completed")
            self.assertEqual(native_cycle.tree_identity(source), source_before)
            self.assertFalse((invocation_root / "frozen-input").exists())
            for disposable in ("work-copy", "ib", "home", "tmp"):
                self.assertFalse((invocation_root / "run" / disposable).exists())
            self.assertTrue((invocation_root / "run" / "logs" / "diagnostic.txt").is_file())
            self.assertTrue((invocation_root / "run" / "evidence" / "diagnostic.txt").is_file())

    def test_remove_generated_tree_rejects_dangling_symlink_target(self) -> None:
        native_cycle = load_module("native_cycle_cleanup_dangling_symlink")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "frozen-input"
            target.symlink_to("missing-generated-tree", target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError, "not a directory"):
                native_cycle._remove_generated_tree(target)
            self.assertTrue(target.is_symlink())

    def test_compaction_final_result_write_failure_persists_non_success(self) -> None:
        native_cycle = load_module("native_cycle_compaction_final_write")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run-current"
            invocation = SimpleNamespace(
                invocation_root=root,
                frozen_input=root / "frozen-input",
                run_root=root / "run",
            )
            for path in (
                invocation.frozen_input,
                invocation.run_root / "work-copy",
                invocation.run_root / "ib",
                invocation.run_root / "home",
                invocation.run_root / "tmp",
                invocation.run_root / "logs",
                invocation.run_root / "evidence",
            ):
                path.mkdir(parents=True, exist_ok=True)
                (path / "artifact.bin").write_bytes(b"x" * 64)
            (root / "spec.json").write_text("{}\n", encoding="utf-8")
            result = {"schemaVersion": 1, "status": "runtime_contract_completed"}
            original_write = native_cycle._write_json_atomic
            calls = 0

            def fail_final_write(path: Path, value: object) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated final result write failure")
                original_write(path, value)

            with mock.patch.object(native_cycle, "_write_json_atomic", side_effect=fail_final_write):
                with self.assertRaises(OSError) as raised:
                    native_cycle._compact_prepared_invocation(invocation, result, time.monotonic())

            result_path = Path(raised.exception.result_path)
            persisted = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["status"], "artifact_cleanup_failed")
            self.assertEqual(persisted["failedStage"], "artifact-finalization")
            self.assertEqual(persisted["storageCompaction"]["status"], "failed")

    def test_run_prepared_cleanup_failure_cannot_remain_success(self) -> None:
        native_cycle = load_module("native_cycle_cleanup_failure")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            source = repo / ".local" / "prepared" / "case-a"
            source.mkdir(parents=True)
            (source / "Configuration.xml").write_text("<Configuration/>\n", encoding="utf-8")

            def fake_plan(spec_path: Path, _repo: Path, **_kwargs: object) -> SimpleNamespace:
                receipt = spec_path.parent / "run" / "evidence" / "receipt.txt"
                return SimpleNamespace(receipt=receipt, runtime_argv=["ENTERPRISE", "/C", str(receipt)])

            def successful_cycle(plan: SimpleNamespace, _spec_path: Path) -> dict[str, object]:
                run_root = plan.receipt.parents[1]
                for name in ("work-copy", "ib", "home", "tmp", "logs", "evidence"):
                    (run_root / name).mkdir(parents=True, exist_ok=True)
                return {"schemaVersion": 1, "status": "runtime_contract_completed", "durationSeconds": 1.0}

            with mock.patch.object(native_cycle, "load_plan", side_effect=fake_plan), mock.patch.object(
                native_cycle, "run_cycle", side_effect=successful_cycle
            ), mock.patch.object(
                native_cycle, "_remove_generated_tree", side_effect=OSError("simulated cleanup failure")
            ):
                with self.assertRaises(OSError) as raised:
                    native_cycle.run_prepared(repo, ".local/prepared/case-a", "complete###true", 5)

            persisted = json.loads(Path(raised.exception.result_path).read_text(encoding="utf-8"))
            self.assertEqual(persisted["status"], "artifact_cleanup_failed")
            self.assertEqual(persisted["failedStage"], "artifact-cleanup")
            self.assertEqual(persisted["storageCompaction"]["status"], "failed")
            self.assertIn("simulated cleanup failure", persisted["storageCompaction"]["error"])

    def test_run_prepared_prioritizes_input_change_during_generated_plan_failure(self) -> None:
        native_cycle = load_module("native_cycle_plan_failure_source_change")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            source = repo / ".local" / "prepared" / "case-a"
            source.mkdir(parents=True)
            source_file = source / "Configuration.xml"
            source_file.write_text("<Configuration/>\n", encoding="utf-8")

            def fail_plan(*_args: object, **_kwargs: object) -> None:
                source_file.write_text("<Configuration changed='true'/>\n", encoding="utf-8")
                raise RuntimeError("simulated generated plan failure")

            with mock.patch.object(native_cycle, "load_plan", side_effect=fail_plan):
                with self.assertRaises(RuntimeError) as raised:
                    native_cycle.run_prepared(repo, ".local/prepared/case-a", "complete###true", 5)

            result_path = getattr(raised.exception, "result_path", None)
            self.assertIsNotNone(result_path)
            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "input_changed")
            self.assertEqual(result["failedStage"], "prepared-input-reverify")
            self.assertNotEqual(
                result["preparedInvocation"]["sourceBefore"],
                result["preparedInvocation"]["sourceAfter"],
            )

    def test_run_prepared_reports_source_replacement_as_input_changed(self) -> None:
        native_cycle = load_module("native_cycle_source_replacement")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            source = repo / ".local" / "prepared" / "replace"
            source.mkdir(parents=True)
            configuration = source / "Configuration.xml"
            configuration.write_text("<Configuration/>\n", encoding="utf-8")

            def replace_source(_plan: SimpleNamespace, _spec_path: Path) -> dict[str, object]:
                configuration.unlink()
                configuration.symlink_to("missing.xml")
                return {"schemaVersion": 1, "status": "runtime_contract_completed"}

            with mock.patch.object(native_cycle, "run_cycle", side_effect=replace_source):
                with self.assertRaisesRegex(RuntimeError, "prepared input tree changed") as raised:
                    native_cycle.run_prepared(
                        repo,
                        ".local/prepared/replace",
                        "complete###true",
                        5,
                    )

            result_path = Path(raised.exception.result_path)
            persisted = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["status"], "input_changed")
            self.assertEqual(persisted["failedStage"], "prepared-input-reverify")
            self.assertEqual(
                persisted["preparedInvocation"]["sourceAfter"]["errorType"],
                "ValueError",
            )
            invocation_root = repo / persisted["preparedInvocation"]["invocationRoot"]
            self.assertFalse((invocation_root / "frozen-input").exists())
            self.assertEqual(persisted["storageCompaction"]["status"], "completed")

    def test_build_plan_uses_one_frozen_spec_without_path_substitution(self) -> None:
        native_cycle = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            source = repo / ".local" / "prepared" / "case-a"
            source.mkdir(parents=True)
            (source / "Configuration.xml").write_text("<Configuration/>\n", encoding="utf-8")
            platform, xvfb = create_fixed_profile(repo)
            expected_identity = native_cycle.tree_identity(source)["sha256"]
            spec_path = repo / ".local" / "spec.json"
            spec_path.write_text(json.dumps({
                "schemaVersion": 1,
                "inputTree": ".local/prepared/case-a",
                "inputTreeSha256": expected_identity,
                "runRoot": ".local/runs/issue20/case-a",
                "receipt": "evidence/receipt.txt",
                "completeMarker": "complete###true",
                "timeoutSeconds": 30,
            }), encoding="utf-8")

            plan = native_cycle.load_plan(spec_path, repo)

            run_root = repo / ".local" / "runs" / "issue20" / "case-a"
            self.assertEqual(plan.run_root, run_root)
            self.assertEqual(plan.work_copy, run_root / "work-copy")
            self.assertEqual(plan.infobase, run_root / "ib")
            self.assertEqual(plan.receipt, run_root / "evidence" / "receipt.txt")
            self.assertEqual(plan.create_argv[4:6], [str(platform), "CREATEINFOBASE"])
            self.assertIn(f"File={run_root / 'ib'}", plan.create_argv)
            self.assertIn(str(run_root / "work-copy"), plan.load_argv)
            self.assertNotIn("/C", plan.runtime_argv)
            self.assertEqual(plan.environment["HOME"], str(run_root / "home"))
            self.assertEqual(plan.environment["LD_LIBRARY_PATH"], ":".join([
                str(repo / ".local/platform/1cv8t/x86_64/8.5.1.1150"),
                str(repo / ".local/platform/libs/usr/lib/x86_64-linux-gnu"),
            ]))

    def test_load_plan_rejects_json_booleans_for_integer_fields(self) -> None:
        native_cycle = load_module("native_cycle_boolean_type_guard")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            base = {
                "schemaVersion": 1,
                "inputTree": ".local/prepared/case-a",
                "inputTreeSha256": "0" * 64,
                "runRoot": ".local/runs/issue20/case-a",
                "receipt": "evidence/receipt.txt",
                "completeMarker": "complete###true",
                "timeoutSeconds": 30,
            }
            for field in ("schemaVersion", "timeoutSeconds"):
                candidate = dict(base)
                candidate[field] = True
                spec_path = repo / f"{field}.json"
                spec_path.write_text(json.dumps(candidate), encoding="utf-8")
                with self.subTest(field=field), self.assertRaises(ValueError):
                    native_cycle.load_plan(spec_path, repo)

    def test_load_plan_rejects_receipt_outside_dedicated_evidence_directory(self) -> None:
        native_cycle = load_module("native_cycle_receipt_separation")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            base = {
                "schemaVersion": 1,
                "inputTree": ".local/prepared/case-a",
                "inputTreeSha256": "0" * 64,
                "runRoot": ".local/runs/issue20/case-a",
                "receipt": "evidence/receipt.txt",
                "completeMarker": "complete###true",
                "timeoutSeconds": 30,
            }
            for receipt in (
                "logs/run.log", "logs/create.result", "result.json",
                "work-copy/receipt.txt", "ib/receipt.txt", "home/receipt.txt",
                "tmp/receipt.txt", "evidence",
            ):
                candidate = dict(base)
                candidate["receipt"] = receipt
                spec_path = repo / "spec.json"
                spec_path.write_text(json.dumps(candidate), encoding="utf-8")
                with self.subTest(receipt=receipt), self.assertRaisesRegex(
                    ValueError, "receipt must be a file inside runRoot/evidence"
                ):
                    native_cycle.load_plan(spec_path, repo)

    def test_load_plan_rejects_run_root_outside_local_runs(self) -> None:
        native_cycle = load_module("native_cycle_path_guard")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            spec_path = repo / "spec.json"
            spec_path.write_text(json.dumps({
                "schemaVersion": 1,
                "inputTree": ".local/prepared/case-a",
                "inputTreeSha256": "0" * 64,
                "runRoot": ".local/prepared/not-a-run",
                "receipt": "evidence/receipt.txt",
                "completeMarker": "complete###true",
                "timeoutSeconds": 30,
            }), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "runRoot must be inside .local/runs"):
                native_cycle.load_plan(spec_path, repo)

    def test_load_plan_rejects_symlinked_input_and_runs_ancestors(self) -> None:
        native_cycle = load_module("native_cycle_symlinked_path_guard")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            real_input = repo / ".local/real-input"
            real_input.mkdir(parents=True)
            (repo / ".local/prepared").symlink_to(real_input, target_is_directory=True)
            real_runs = repo / "run-storage"
            real_runs.mkdir()
            (repo / ".local/runs").symlink_to(real_runs, target_is_directory=True)
            spec_path = repo / "spec.json"
            spec_path.write_text(json.dumps({
                "schemaVersion": 1,
                "inputTree": ".local/prepared",
                "inputTreeSha256": "0" * 64,
                "runRoot": ".local/runs/case-a",
                "receipt": "evidence/receipt.txt",
                "completeMarker": "complete###true",
                "timeoutSeconds": 30,
            }), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "symlink path component"):
                native_cycle.load_plan(spec_path, repo)

    def test_prepare_run_refuses_existing_root_and_copies_closed_input_tree(self) -> None:
        native_cycle = load_module("native_cycle_prepare")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            source = repo / ".local" / "prepared" / "case-a"
            source.mkdir(parents=True)
            (source / "Configuration.xml").write_text("<Configuration/>\n", encoding="utf-8")
            freeze_tree(source)
            run_root = repo / ".local" / "runs" / "issue20" / "case-a"
            expected = native_cycle.tree_identity(source)["sha256"]
            plan = SimpleNamespace(
                input_tree=source, run_root=run_root, work_copy=run_root / "work-copy",
                expected_input_tree_sha256=expected,
            )

            identity = native_cycle.prepare_run(plan)

            self.assertEqual(identity["files"], 1)
            self.assertEqual(identity["sourceTreeSha256"], identity["copiedTreeSha256"])
            self.assertEqual(
                identity["loadTreeSha256"],
                native_cycle.tree_identity(plan.work_copy)["sha256"],
            )
            self.assertNotEqual(identity["sourceTreeSha256"], identity["loadTreeSha256"])
            self.assertEqual((plan.work_copy / "Configuration.xml").read_text(encoding="utf-8"), "<Configuration/>\n")
            with self.assertRaisesRegex(FileExistsError, "runRoot already exists"):
                native_cycle.prepare_run(plan)

    def test_prepare_run_rejects_input_identity_mismatch_before_creating_root(self) -> None:
        native_cycle = load_module("native_cycle_identity_guard")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            source = repo / ".local/prepared/case-a"
            source.mkdir(parents=True)
            (source / "Configuration.xml").write_text("<Configuration/>\n", encoding="utf-8")
            run_root = repo / ".local/runs/issue20/case-a"
            plan = SimpleNamespace(
                input_tree=source, run_root=run_root, work_copy=run_root / "work-copy",
                expected_input_tree_sha256="0" * 64,
            )

            with self.assertRaisesRegex(ValueError, "input tree identity mismatch"):
                native_cycle.prepare_run(plan)
            self.assertFalse(run_root.exists())

    def test_prepare_run_rejects_writable_declared_input(self) -> None:
        native_cycle = load_module("native_cycle_read_only_guard")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            source = repo / ".local/prepared/case-a"
            source.mkdir(parents=True)
            candidate = source / "Configuration.xml"
            candidate.write_text("<Configuration/>\n", encoding="utf-8")
            run_root = repo / ".local/runs/issue20/case-a"
            plan = SimpleNamespace(
                input_tree=source, run_root=run_root, work_copy=run_root / "work-copy",
                expected_input_tree_sha256=native_cycle.tree_identity(source)["sha256"],
            )

            with self.assertRaisesRegex(ValueError, "input tree must be read-only"):
                native_cycle.prepare_run(plan)
            self.assertFalse(run_root.exists())

    def test_tree_identity_rejects_non_regular_input_entry(self) -> None:
        native_cycle = load_module("native_cycle_non_regular_guard")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input"
            source.mkdir()
            os.mkfifo(source / "surprise.fifo")

            with self.assertRaisesRegex(ValueError, "non-regular input entry"):
                native_cycle.tree_identity(source)

    def test_tree_identity_binds_empty_directories_and_modes(self) -> None:
        native_cycle = load_module("native_cycle_closed_tree_identity")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input"
            source.mkdir()
            candidate = source / "Configuration.xml"
            candidate.write_text("<Configuration/>\n", encoding="utf-8")
            initial = native_cycle.tree_identity(source)["sha256"]

            (source / "empty").mkdir()
            with_directory = native_cycle.tree_identity(source)["sha256"]
            candidate.chmod(candidate.stat().st_mode & ~stat.S_IWUSR)
            with_mode_change = native_cycle.tree_identity(source)["sha256"]

            self.assertNotEqual(initial, with_directory)
            self.assertNotEqual(with_directory, with_mode_change)

    def test_load_plan_rejects_duplicate_json_keys(self) -> None:
        native_cycle = load_module("native_cycle_duplicate_keys")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            spec_path = repo / "spec.json"
            spec_path.write_text(
                '{"schemaVersion":1,"inputTree":".local/a","inputTree":".local/b",'
                '"inputTreeSha256":"' + "0" * 64 + '","runRoot":".local/runs/x",'
                '"receipt":"evidence/receipt.txt","completeMarker":"complete###true",'
                '"timeoutSeconds":30}',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "duplicate JSON key: inputTree"):
                native_cycle.load_plan(spec_path, repo)

    def test_process_ownership_preflight_reports_missing_procfs_children(self) -> None:
        native_cycle = load_module("native_cycle_procfs_preflight")
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "proc-children"
            native_cycle._proc_children_path = lambda: missing

            with self.assertRaisesRegex(
                RuntimeError,
                "process ownership preflight failed.*procfs children interface unavailable",
            ):
                native_cycle._preflight_process_ownership()

    def test_batch_step_requires_fresh_zero_dump_result_and_success_marker(self) -> None:
        native_cycle = load_module("native_cycle_batch")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = root / "step.result"
            log = root / "step.log"
            fake = root / "fake-step"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "from pathlib import Path\n"
                "import sys\n"
                "Path(sys.argv[1]).write_bytes(b'\\xef\\xbb\\xbf0\\n')\n"
                "Path(sys.argv[2]).write_text('Configuration successfully updated\\n')\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

            outcome = native_cycle.run_batch_step(
                "load", [str(fake), str(result), str(log)], os.environ.copy(),
                result, log, "Configuration successfully updated", 10,
            )

            self.assertEqual(outcome["dumpResult"], "0")
            self.assertEqual(outcome["processReturn"], 0)
            self.assertEqual(len(outcome["resultSha256"]), 64)
            self.assertEqual(len(outcome["logSha256"]), 64)
            with self.assertRaisesRegex(RuntimeError, "stale load result"):
                native_cycle.run_batch_step(
                    "load", [str(fake), str(result), str(log)], os.environ.copy(),
                    result, log, "Configuration successfully updated", 10,
                )

    def test_batch_step_rejects_success_marker_as_substring(self) -> None:
        native_cycle = load_module("native_cycle_batch_exact_marker")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = root / "step.result"
            log = root / "step.log"
            fake = root / "fake-step"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "from pathlib import Path\n"
                "import sys\n"
                "Path(sys.argv[1]).write_text('0\\n')\n"
                "Path(sys.argv[2]).write_text('ERROR: not completed successfully; rollback occurred\\n')\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

            with self.assertRaisesRegex(RuntimeError, "successMarker=False"):
                native_cycle.run_batch_step(
                    "create", [str(fake), str(result), str(log)], os.environ.copy(),
                    result, log, "completed successfully", 10,
                )

    def test_batch_step_accepts_native_create_terminal_sentence(self) -> None:
        native_cycle = load_module("native_cycle_native_create_marker")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = root / "step.result"
            log = root / "step.log"
            fake = root / "fake-step"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "from pathlib import Path\n"
                "import sys\n"
                "Path(sys.argv[1]).write_text('0\\n')\n"
                "Path(sys.argv[2]).write_bytes(b'\\xef\\xbb\\xbfCreation of infobase (\\\"File=/tmp/ib\\\") completed successfully\\n')\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

            outcome = native_cycle.run_batch_step(
                "create", [str(fake), str(result), str(log)], os.environ.copy(),
                result, log, "completed successfully", 10,
            )
            self.assertEqual(outcome["dumpResult"], "0")

    def test_batch_timeout_cleans_child_process_group(self) -> None:
        native_cycle = load_module("native_cycle_batch_timeout")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = root / "step.result"
            log = root / "step.log"
            pid_file = root / "child.pid"
            fake = root / "fake-timeout"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "from pathlib import Path\n"
                "import subprocess, sys, time\n"
                "child = subprocess.Popen(['sleep', '60'])\n"
                "Path(sys.argv[1]).write_text(str(child.pid))\n"
                "time.sleep(60)\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

            with self.assertRaisesRegex(TimeoutError, "load timed out"):
                native_cycle.run_batch_step(
                    "load", [str(fake), str(pid_file)], os.environ.copy(),
                    result, log, "Configuration successfully updated", 1.0,
                )

            child_pid = int(pid_file.read_text(encoding="utf-8"))
            for _ in range(40):
                if not process_is_running(child_pid):
                    break
                time.sleep(0.025)
            self.assertFalse(process_is_running(child_pid), "batch child survived timeout cleanup")

    def test_batch_success_cleans_lingering_child_process_group(self) -> None:
        native_cycle = load_module("native_cycle_batch_success_cleanup")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = root / "step.result"
            log = root / "step.log"
            pid_file = root / "child.pid"
            fake = root / "fake-success-with-child"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "from pathlib import Path\n"
                "import subprocess, sys\n"
                "child = subprocess.Popen(['sleep', '60'])\n"
                "Path(sys.argv[1]).write_text(str(child.pid))\n"
                "Path(sys.argv[2]).write_text('0\\n')\n"
                "Path(sys.argv[3]).write_text('Configuration successfully updated\\n')\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

            outcome = native_cycle.run_batch_step(
                "load", [str(fake), str(pid_file), str(result), str(log)], os.environ.copy(),
                result, log, "Configuration successfully updated", 5,
            )

            self.assertEqual(outcome["processReturn"], 0)
            child_pid = int(pid_file.read_text(encoding="utf-8"))
            for _ in range(40):
                if not process_is_running(child_pid):
                    break
                time.sleep(0.025)
            self.assertFalse(process_is_running(child_pid), "batch child survived success cleanup")

    def test_batch_success_cleans_child_that_escaped_into_new_session(self) -> None:
        native_cycle = load_module("native_cycle_batch_escaped_child")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = root / "step.result"
            log = root / "step.log"
            pid_file = root / "child.pid"
            fake = root / "fake-success-with-escaped-child"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "from pathlib import Path\n"
                "import subprocess, sys\n"
                "child = subprocess.Popen(['sleep', '60'], start_new_session=True)\n"
                "Path(sys.argv[1]).write_text(str(child.pid))\n"
                "Path(sys.argv[2]).write_text('0\\n')\n"
                "Path(sys.argv[3]).write_text('Configuration successfully updated\\n')\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

            native_cycle.run_batch_step(
                "load", [str(fake), str(pid_file), str(result), str(log)], os.environ.copy(),
                result, log, "Configuration successfully updated", 5,
            )

            child_pid = int(pid_file.read_text(encoding="utf-8"))
            for _ in range(40):
                if not process_is_running(child_pid):
                    break
                time.sleep(0.025)
            self.assertFalse(process_is_running(child_pid), "escaped child survived success cleanup")

    def test_runtime_early_exit_reports_process_and_native_outputs(self) -> None:
        native_cycle = load_module("native_cycle_runtime_early_exit_diagnostic")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = root / "receipt.txt"
            log = root / "run.log"
            result = root / "run.result"
            fake = root / "fake-runtime"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "from pathlib import Path\n"
                "import sys\n"
                "Path(sys.argv[1]).write_text('platform failed\\n')\n"
                "Path(sys.argv[2]).write_text('7\\n')\n"
                "raise SystemExit(7)\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

            with self.assertRaisesRegex(RuntimeError, "runtime exited before completion") as raised:
                native_cycle.run_runtime(
                    [str(fake), str(log), str(result)], os.environ.copy(), receipt,
                    "complete###true", timeout_seconds=5,
                    receipt_root=root, log_path=log, result_path=result,
                    poll_seconds=0.025, stable_reads=2,
                )

            diagnostic = raised.exception.runtime_diagnostic
            self.assertEqual(diagnostic["failureKind"], "exited_before_completion")
            self.assertEqual(diagnostic["processReturn"], 7)
            self.assertEqual(diagnostic["receipt"], {"state": "absent"})
            self.assertEqual(diagnostic["outputs"]["log"]["state"], "regular")
            self.assertEqual(diagnostic["outputs"]["result"]["state"], "regular")
            self.assertEqual(len(diagnostic["outputs"]["log"]["sha256"]), 64)
            self.assertEqual(len(diagnostic["outputs"]["result"]["sha256"]), 64)

    def test_runtime_fifo_receipt_is_bounded_and_cleans_process(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "evidence"
            evidence.mkdir()
            receipt = evidence / "receipt.fifo"
            runtime_pid = root / "runtime.pid"
            fake = root / "fake-runtime"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "from pathlib import Path\n"
                "import os, sys, time\n"
                "Path(sys.argv[1]).write_text(str(os.getpid()))\n"
                "os.mkfifo(sys.argv[2])\n"
                "time.sleep(60)\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            helper = root / "helper.py"
            helper.write_text(
                "import importlib.util, os, sys\n"
                "from pathlib import Path\n"
                f"spec = importlib.util.spec_from_file_location('native_cycle_fifo', {str(CLI)!r})\n"
                "module = importlib.util.module_from_spec(spec)\n"
                "spec.loader.exec_module(module)\n"
                "try:\n"
                "    module.run_runtime(\n"
                "        [sys.argv[1], sys.argv[2], sys.argv[3]], os.environ.copy(),\n"
                "        Path(sys.argv[3]), 'complete###true', timeout_seconds=1,\n"
                "        receipt_root=Path(sys.argv[3]).parent, poll_seconds=0.025, stable_reads=2,\n"
                "    )\n"
                "except RuntimeError as exc:\n"
                "    if 'receipt channel' in str(exc): raise SystemExit(0)\n"
                "    raise\n"
                "raise SystemExit(2)\n",
                encoding="utf-8",
            )
            process = subprocess.Popen(
                ["python3", str(helper), str(fake), str(runtime_pid), str(receipt)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            try:
                stdout, stderr = process.communicate(timeout=4)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                if runtime_pid.is_file():
                    try:
                        os.kill(int(runtime_pid.read_text(encoding="utf-8")), 9)
                    except ProcessLookupError:
                        pass
                self.fail("FIFO receipt blocked past the independent subprocess deadline")
            self.assertEqual(process.returncode, 0, (stdout, stderr))
            pid = int(runtime_pid.read_text(encoding="utf-8"))
            for _ in range(40):
                if not process_is_running(pid):
                    break
                time.sleep(0.025)
            self.assertFalse(process_is_running(pid), "runtime survived FIFO receipt rejection")

    def test_runtime_rejects_symlink_alias_to_runner_owned_log(self) -> None:
        native_cycle = load_module("native_cycle_runtime_receipt_alias")
        for mode in ("leaf", "ancestor", "hardlink"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                evidence = root / "evidence"
                logs = root / "logs"
                evidence.mkdir()
                logs.mkdir()
                target = logs / "run.log"
                if mode == "leaf":
                    receipt = evidence / "receipt.txt"
                elif mode == "ancestor":
                    receipt = evidence / "alias" / "receipt.txt"
                else:
                    receipt = evidence / "receipt.txt"
                fake = root / "fake-runtime"
                fake.write_text(
                    "#!/usr/bin/env python3\n"
                    "from pathlib import Path\n"
                    "import os, sys, time\n"
                    "receipt, target, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]\n"
                    "if mode == 'leaf': receipt.symlink_to(target)\n"
                    "elif mode == 'ancestor': receipt.parent.symlink_to(target.parent, target_is_directory=True)\n"
                    "else:\n"
                    "    target.touch()\n"
                    "    os.link(target, receipt)\n"
                    "target.write_text('complete###true\\n')\n"
                    "time.sleep(60)\n",
                    encoding="utf-8",
                )
                fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

                with self.assertRaisesRegex(RuntimeError, "receipt channel"):
                    native_cycle.run_runtime(
                        [str(fake), str(receipt), str(target), mode], os.environ.copy(),
                        receipt, "complete###true", timeout_seconds=1,
                        receipt_root=evidence, poll_seconds=0.025, stable_reads=2,
                    )

    def test_receipt_read_rejects_link_count_change_without_retry_classification(self) -> None:
        native_cycle = load_module("native_cycle_receipt_nlink_change")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = root / "receipt.txt"
            receipt.write_text("complete###true\n", encoding="utf-8")
            original_fstat = native_cycle.os.fstat
            calls = 0

            def changed_nlink(fd: int):
                nonlocal calls
                current = original_fstat(fd)
                calls += 1
                if calls != 2:
                    return current
                return SimpleNamespace(
                    st_mode=current.st_mode,
                    st_nlink=2,
                    st_dev=current.st_dev,
                    st_ino=current.st_ino,
                    st_size=current.st_size,
                    st_mtime_ns=current.st_mtime_ns,
                    st_ctime_ns=current.st_ctime_ns,
                )

            with mock.patch.object(native_cycle.os, "fstat", side_effect=changed_nlink):
                with self.assertRaisesRegex(RuntimeError, "single-link"):
                    native_cycle._read_receipt_channel(root, receipt)

    def test_runtime_retries_same_file_change_during_receipt_observation(self) -> None:
        native_cycle = load_module("native_cycle_runtime_receipt_growth")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = root / "receipt.txt"
            fake = root / "fake-runtime"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import time\n"
                "time.sleep(60)\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            complete = b"started###true\ncomplete###true\n"
            changed = native_cycle._ReceiptChangedDuringRead(
                "runtime receipt channel changed during read"
            )

            with mock.patch.object(
                native_cycle,
                "_read_receipt_channel",
                side_effect=[changed, complete, complete, complete],
            ):
                outcome = native_cycle.run_runtime(
                    [str(fake)], os.environ.copy(), receipt,
                    "complete###true", timeout_seconds=5,
                    receipt_root=receipt.parent,
                    poll_seconds=0.01, stable_reads=2,
                )

            self.assertTrue(outcome["completed"])

    def test_runtime_confirms_stable_terminal_receipt_after_writer_exit(self) -> None:
        native_cycle = load_module("native_cycle_runtime_receipt_exit")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = root / "receipt.txt"
            fake = root / "fake-runtime"
            fake.write_text(
                "#!/usr/bin/env python3\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            complete = b"started###true\ncomplete###true\n"
            changed = native_cycle._ReceiptChangedDuringRead(
                "runtime receipt channel changed during read"
            )

            observations = iter([changed, complete, complete, complete])

            def observe(*_args):
                value = next(observations)
                if value is changed:
                    time.sleep(0.2)
                    raise value
                return value

            with mock.patch.object(
                native_cycle,
                "_read_receipt_channel",
                side_effect=observe,
            ):
                outcome = native_cycle.run_runtime(
                    [str(fake)], os.environ.copy(), receipt,
                    "complete###true", timeout_seconds=5,
                    receipt_root=receipt.parent,
                    poll_seconds=0.05, stable_reads=2,
                )

            self.assertTrue(outcome["completed"])
            self.assertEqual(outcome["processReturn"], 0)

    def test_runtime_waits_for_stable_marker_and_cleans_its_process_group(self) -> None:
        native_cycle = load_module("native_cycle_runtime")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = root / "receipt.txt"
            pid_file = root / "child.pid"
            fake = root / "fake-runtime"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "from pathlib import Path\n"
                "import subprocess, sys, time\n"
                "child = subprocess.Popen(['sleep', '60'])\n"
                "Path(sys.argv[2]).write_text(str(child.pid))\n"
                "Path(sys.argv[1]).write_text('started###true\\ncomplete###true\\n')\n"
                "time.sleep(60)\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

            outcome = native_cycle.run_runtime(
                [str(fake), str(receipt), str(pid_file)], os.environ.copy(),
                receipt, "complete###true", timeout_seconds=5,
                receipt_root=receipt.parent,
                poll_seconds=0.05, stable_reads=2,
            )

            child_pid = int(pid_file.read_text(encoding="utf-8"))
            self.assertTrue(outcome["completed"])
            self.assertEqual(outcome["completeMarker"], "complete###true")
            self.assertEqual(len(outcome["receiptSha256"]), 64)

            for _ in range(40):
                if not process_is_running(child_pid):
                    break
                time.sleep(0.025)
            self.assertFalse(process_is_running(child_pid), "runtime child survived cleanup")

    def test_runtime_rejects_lines_after_completion_marker(self) -> None:
        native_cycle = load_module("native_cycle_terminal_marker")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = root / "receipt.txt"
            fake = root / "fake-runtime"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "from pathlib import Path\n"
                "import sys, time\n"
                "Path(sys.argv[1]).write_text('complete###true\\nERROR###after-marker\\n')\n"
                "time.sleep(60)\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

            with self.assertRaisesRegex(TimeoutError, "completion marker not observed"):
                native_cycle.run_runtime(
                    [str(fake), str(receipt)], os.environ.copy(), receipt,
                    "complete###true", timeout_seconds=1.0,
                    receipt_root=receipt.parent,
                    poll_seconds=0.025, stable_reads=2,
                )

    def test_runtime_rejects_receipt_changed_by_sigterm_handler_during_cleanup(self) -> None:
        native_cycle = load_module("native_cycle_cleanup_receipt_race")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = root / "receipt.txt"
            fake = root / "fake-runtime"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "from pathlib import Path\n"
                "import signal, sys, time\n"
                "receipt = Path(sys.argv[1])\n"
                "def finish(signum, frame):\n"
                "    with receipt.open('a', encoding='utf-8') as stream:\n"
                "        stream.write('ERROR###after-marker\\n')\n"
                "    raise SystemExit(0)\n"
                "signal.signal(signal.SIGTERM, finish)\n"
                "receipt.write_text('started###true\\ncomplete###true\\n')\n"
                "time.sleep(60)\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

            with self.assertRaisesRegex(RuntimeError, "changed after completion"):
                native_cycle.run_runtime(
                    [str(fake), str(receipt)], os.environ.copy(), receipt,
                    "complete###true", timeout_seconds=5,
                    receipt_root=receipt.parent,
                    poll_seconds=0.05, stable_reads=2,
                )
            self.assertEqual(receipt.read_text(encoding="utf-8").splitlines()[-1], "ERROR###after-marker")

    def test_runtime_timeout_fails_closed_and_cleans_process(self) -> None:
        native_cycle = load_module("native_cycle_timeout")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = root / "receipt.txt"
            pid_file = root / "runtime.pid"
            fake = root / "fake-timeout"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "from pathlib import Path\n"
                "import os, sys, time\n"
                "Path(sys.argv[1]).write_text(str(os.getpid()))\n"
                "Path(sys.argv[2]).write_text('notcomplete###true\\n')\n"
                "time.sleep(60)\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

            with self.assertRaisesRegex(TimeoutError, "completion marker not observed"):
                native_cycle.run_runtime(
                    [str(fake), str(pid_file), str(receipt)], os.environ.copy(), receipt,
                    "complete###true", timeout_seconds=1.0,
                    receipt_root=receipt.parent,
                    poll_seconds=0.025, stable_reads=2,
                )

            pid = int(pid_file.read_text(encoding="utf-8"))
            for _ in range(40):
                if not process_is_running(pid):
                    break
                time.sleep(0.025)
            self.assertFalse(process_is_running(pid), "runtime survived timeout cleanup")

    def test_run_cycle_executes_one_complete_fake_lifecycle(self) -> None:
        native_cycle = load_module("native_cycle_end_to_end")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            source = repo / ".local" / "prepared" / "case-a"
            source.mkdir(parents=True)
            (source / "Configuration.xml").write_text("<Configuration/>\n", encoding="utf-8")
            freeze_tree(source)
            run_root = repo / ".local" / "runs" / "issue20" / "case-a"
            receipt = run_root / "evidence" / "receipt.txt"
            platform, xvfb = create_fixed_profile(repo)
            platform.write_text(
                "#!/usr/bin/env python3\n"
                "from pathlib import Path\n"
                "import sys, time\n"
                f"receipt = Path({str(receipt)!r})\n"
                "mode = sys.argv[1]\n"
                "out = Path(sys.argv[sys.argv.index('/Out') + 1])\n"
                "result = Path(sys.argv[sys.argv.index('/DumpResult') + 1])\n"
                "out.parent.mkdir(parents=True, exist_ok=True)\n"
                "if mode == 'CREATEINFOBASE':\n"
                "    Path(sys.argv[2].split('=', 1)[1]).mkdir(parents=True)\n"
                "    marker = 'completed successfully'\n"
                "elif mode == 'DESIGNER': marker = 'Configuration successfully updated'\n"
                "else:\n"
                "    receipt.parent.mkdir(parents=True, exist_ok=True)\n"
                "    receipt.write_text('complete###true\\n')\n"
                "    time.sleep(60)\n"
                "    marker = 'runtime'\n"
                "out.write_text(marker + '\\n')\n"
                "result.write_bytes(b'\\xef\\xbb\\xbf0\\n')\n",
                encoding="utf-8",
            )
            platform.chmod(platform.stat().st_mode | stat.S_IXUSR)
            xvfb.write_text(
                "#!/usr/bin/env python3\n"
                "import os, sys\n"
                "os.execv(sys.argv[4], sys.argv[4:])\n",
                encoding="utf-8",
            )
            xvfb.chmod(xvfb.stat().st_mode | stat.S_IXUSR)
            expected_identity = native_cycle.tree_identity(source)["sha256"]
            spec_path = repo / ".local" / "case-a.json"
            spec_path.write_text(json.dumps({
                "schemaVersion": 1,
                "inputTree": ".local/prepared/case-a",
                "inputTreeSha256": expected_identity,
                "runRoot": ".local/runs/issue20/case-a",
                "receipt": "evidence/receipt.txt",
                "completeMarker": "complete###true",
                "timeoutSeconds": 5,
            }), encoding="utf-8")

            result = native_cycle.run_cycle(native_cycle.load_plan(spec_path, repo), spec_path)

            self.assertEqual(result["status"], "runtime_contract_completed")
            self.assertTrue(result["runtime"]["completed"])
            self.assertEqual(result["create"]["dumpResult"], "0")
            self.assertEqual(result["load"]["dumpResult"], "0")
            self.assertEqual(result["inputAfter"]["sha256"], expected_identity)
            self.assertTrue((run_root / "result.json").is_file())
            self.assertEqual(
                json.loads((run_root / "result.json").read_text(encoding="utf-8"))["status"],
                "runtime_contract_completed",
            )

    def test_run_prepared_cli_repeats_same_command_with_unique_bindings_and_result_paths(self) -> None:
        native_cycle = load_module("native_cycle_prepared_cli")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            source = repo / ".local" / "prepared" / "case-a"
            source.mkdir(parents=True)
            (source / "Configuration.xml").write_text("<Configuration/>\n", encoding="utf-8")
            source_before = native_cycle.tree_identity(source)
            platform, xvfb = create_fixed_profile(repo)
            platform.write_text(
                "#!/usr/bin/env python3\n"
                "from pathlib import Path\n"
                "import sys, time\n"
                "mode = sys.argv[1]\n"
                "out = Path(sys.argv[sys.argv.index('/Out') + 1])\n"
                "result = Path(sys.argv[sys.argv.index('/DumpResult') + 1])\n"
                "out.parent.mkdir(parents=True, exist_ok=True)\n"
                "if mode == 'CREATEINFOBASE':\n"
                "    Path(sys.argv[2].split('=', 1)[1]).mkdir(parents=True)\n"
                "    marker = 'completed successfully'\n"
                "elif mode == 'DESIGNER': marker = 'Configuration successfully updated'\n"
                "else:\n"
                "    receipt = Path(sys.argv[sys.argv.index('/C') + 1])\n"
                "    receipt.parent.mkdir(parents=True, exist_ok=True)\n"
                "    receipt.write_text('complete###true\\n')\n"
                "    time.sleep(60)\n"
                "    marker = 'runtime'\n"
                "out.write_text(marker + '\\n')\n"
                "result.write_bytes(b'\\xef\\xbb\\xbf0\\n')\n",
                encoding="utf-8",
            )
            platform.chmod(platform.stat().st_mode | stat.S_IXUSR)
            xvfb.write_text(
                "#!/usr/bin/env python3\nimport os, sys\nos.execv(sys.argv[4], sys.argv[4:])\n",
                encoding="utf-8",
            )
            xvfb.chmod(xvfb.stat().st_mode | stat.S_IXUSR)
            argv = [
                sys.executable,
                str(CLI),
                "run-prepared",
                "--repo-root", str(repo),
                "--input-tree", ".local/prepared/case-a",
                "--complete-marker", "complete###true",
                "--timeout-seconds", "5",
            ]

            outputs = []
            for _ in range(2):
                completed = subprocess.run(argv, text=True, capture_output=True, timeout=20)
                self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
                outputs.append(json.loads(completed.stdout))

            self.assertEqual(native_cycle.tree_identity(source), source_before)
            self.assertNotEqual(outputs[0]["resultPath"], outputs[1]["resultPath"])
            for output in outputs:
                self.assertEqual(output["status"], "runtime_contract_completed")
                self.assertGreaterEqual(output["totalDurationSeconds"], output["durationSeconds"])
                self.assertEqual(
                    output["preparedInvocation"]["sourceBefore"],
                    output["preparedInvocation"]["sourceAfter"],
                )
                result_path = repo / output["resultPath"]
                self.assertTrue(result_path.is_file())
                persisted = json.loads(result_path.read_text(encoding="utf-8"))
                self.assertEqual(persisted, output)
                self.assertEqual(persisted["commands"]["runtime"].count("/C"), 1)
                binding = persisted["preparedInvocation"]["generatedBinding"]
                self.assertEqual(binding["kind"], "1c-enterprise-launch-parameter")
                self.assertEqual(len(binding["runtimeArgvSha256"]), 64)
                invocation_root = repo / persisted["preparedInvocation"]["invocationRoot"]
                self.assertFalse((invocation_root / "frozen-input").exists())
                for disposable in ("work-copy", "ib", "home", "tmp"):
                    self.assertFalse((invocation_root / "run" / disposable).exists())
                for retained in (
                    invocation_root / "spec.json",
                    invocation_root / "run" / "result.json",
                    invocation_root / "run" / "evidence" / "receipt.txt",
                    invocation_root / "run" / "logs" / "create.log",
                    invocation_root / "run" / "logs" / "load.log",
                ):
                    self.assertTrue(retained.is_file(), retained)
                storage = persisted["storageCompaction"]
                self.assertEqual(storage["status"], "completed")
                self.assertEqual(storage["policy"], "compact-current-invocation-v1")
                self.assertGreater(
                    storage["preCompactionLogicalBytes"],
                    storage["retainedLogicalBytesExcludingResult"],
                )
                self.assertGreater(storage["removedLogicalBytes"], 0)
                self.assertEqual(storage["manualCleanupActions"], 0)

    def test_run_cycle_timeout_preserves_completed_stage_diagnostics(self) -> None:
        native_cycle = load_module("native_cycle_failure_result")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            source = repo / ".local" / "prepared" / "timeout"
            source.mkdir(parents=True)
            (source / "Configuration.xml").write_text("<Configuration/>\n", encoding="utf-8")
            freeze_tree(source)
            run_root = repo / ".local" / "runs" / "issue20" / "timeout"
            platform, xvfb = create_fixed_profile(repo)
            platform.write_text(
                "#!/usr/bin/env python3\n"
                "from pathlib import Path\n"
                "import sys, time\n"
                "mode = sys.argv[1]\n"
                "out = Path(sys.argv[sys.argv.index('/Out') + 1])\n"
                "result = Path(sys.argv[sys.argv.index('/DumpResult') + 1])\n"
                "out.parent.mkdir(parents=True, exist_ok=True)\n"
                "if mode == 'CREATEINFOBASE':\n"
                "    Path(sys.argv[2].split('=', 1)[1]).mkdir(parents=True)\n"
                "    marker = 'completed successfully'\n"
                "elif mode == 'DESIGNER': marker = 'Configuration successfully updated'\n"
                "else: time.sleep(60)\n"
                "out.write_text(marker + '\\n')\n"
                "result.write_bytes(b'0\\n')\n",
                encoding="utf-8",
            )
            platform.chmod(platform.stat().st_mode | stat.S_IXUSR)
            xvfb.write_text(
                "#!/usr/bin/env python3\nimport os, sys\nos.execv(sys.argv[4], sys.argv[4:])\n",
                encoding="utf-8",
            )
            xvfb.chmod(xvfb.stat().st_mode | stat.S_IXUSR)
            expected_identity = native_cycle.tree_identity(source)["sha256"]
            spec_path = repo / ".local" / "timeout.json"
            spec_path.write_text(json.dumps({
                "schemaVersion": 1,
                "inputTree": ".local/prepared/timeout",
                "inputTreeSha256": expected_identity,
                "runRoot": ".local/runs/issue20/timeout",
                "receipt": "evidence/receipt.txt",
                "completeMarker": "complete###true",
                "timeoutSeconds": 1,
            }), encoding="utf-8")

            with self.assertRaisesRegex(TimeoutError, "completion marker not observed"):
                native_cycle.run_cycle(native_cycle.load_plan(spec_path, repo), spec_path)

            diagnostic = json.loads((run_root / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(diagnostic["status"], "runtime_timeout")
            self.assertEqual(diagnostic["failedStage"], "runtime")
            self.assertEqual(diagnostic["create"]["dumpResult"], "0")
            self.assertEqual(diagnostic["load"]["dumpResult"], "0")
            self.assertEqual(diagnostic["errorType"], "TimeoutError")
            runtime = diagnostic["runtime"]
            self.assertFalse(runtime["completed"])
            self.assertEqual(runtime["failureKind"], "timeout")
            self.assertEqual(runtime["processReturn"], -15)
            self.assertEqual(runtime["receipt"], {"state": "absent"})
            self.assertEqual(runtime["outputs"]["log"], {"state": "absent"})
            self.assertEqual(runtime["outputs"]["result"], {"state": "absent"})


if __name__ == "__main__":
    unittest.main()
