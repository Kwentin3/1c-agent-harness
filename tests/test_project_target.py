from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "project_target.py"
sys.path.insert(0, str(ROOT / "scripts"))

import cf_materializer
import managed_probe_prepare
import native_cycle
import target_admission
from one_c_harness import project_target


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def manifest(root: Path) -> bytes:
    records = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            records.append(
                f"{digest(path.read_bytes())}  {path.relative_to(root).as_posix()}\n"
            )
    return "".join(records).encode("utf-8")


def export(root: Path, *, name: str = "Sample", version: str = "2.0") -> Path:
    source = root / ".local/source/export"
    source.mkdir(parents=True)
    configuration = (
        "<MetaDataObject><Configuration><Properties>"
        f"<Name>{name}</Name><Version>{version}</Version>"
        "</Properties></Configuration></MetaDataObject>"
    )
    (source / "Configuration.xml").write_text(configuration, encoding="utf-8")
    document = source / "Documents/Order.xml"
    document.parent.mkdir()
    document.write_text("<MetaDataObject/>", encoding="utf-8")
    return source


def write_contract(
    root: Path,
    source: dict[str, object],
    content_id: str,
    *,
    file_count: int = 2,
) -> None:
    value = {
        "schemaVersion": 2,
        "configuration": {"name": "Sample", "version": "2.0"},
        "source": source,
        "snapshot": {
            "root": ".local/targets/sample/snapshot",
            "manifest": ".local/targets/sample/snapshot.manifest",
            "contentId": f"sha256:{content_id}",
            "fileCount": file_count,
        },
        "dailyNativeRoute": "scripts/shared_task_route.py run",
    }
    (root / "project-target.json").write_text(json.dumps(value), encoding="utf-8")


def hierarchical_project(root: Path) -> Path:
    source = export(root)
    source_manifest = manifest(source)
    write_contract(
        root,
        {
            "kind": "hierarchical",
            "path": ".local/source/export",
            "contentId": f"sha256:{digest(source_manifest)}",
            "fileCount": 2,
        },
        digest(source_manifest),
    )
    return source


def run_open(root: Path, *, legacy_alias: bool = False) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(CLI)]
    if not legacy_alias:
        command.append("open")
    command.extend(("--repo-root", str(root)))
    return subprocess.run(command, text=True, capture_output=True, check=False)


def response(completed: subprocess.CompletedProcess[str]) -> dict[str, object]:
    return json.loads(completed.stdout)


class ProjectTargetTests(unittest.TestCase):
    def test_hierarchical_source_and_legacy_alias_share_open_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = hierarchical_project(root)

            cold = run_open(root)
            alias = run_open(root, legacy_alias=True)

            self.assertEqual(cold.returncode, 0, cold.stdout)
            self.assertEqual(alias.returncode, 0, alias.stdout)
            self.assertEqual(response(cold)["action"], "materialized")
            self.assertEqual(response(alias)["action"], "reused")
            snapshot = root / str(response(cold)["snapshot"]["root"])
            self.assertIn(b"Sample", (snapshot / "Configuration.xml").read_bytes())
            self.assertEqual(manifest(source), manifest(snapshot))

    def test_warm_reuse_is_deterministic_without_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = hierarchical_project(root)
            self.assertEqual(run_open(root).returncode, 0)
            shutil.rmtree(source)

            first = run_open(root)
            second = run_open(root)

            self.assertEqual(first.returncode, 0, first.stdout)
            self.assertEqual(first.stdout, second.stdout)
            self.assertEqual(response(first)["action"], "reused")

    def test_invalid_source_and_corrupted_retained_target_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = hierarchical_project(root)
            (source / "Documents/Order.xml").write_text("bad", encoding="utf-8")

            self.assertEqual(response(run_open(root))["reasonCode"], "source_mismatch")
            self.assertFalse((root / ".local/targets/sample").exists())

            (source / "Documents/Order.xml").write_text("<MetaDataObject/>", encoding="utf-8")
            source_manifest = manifest(source)
            write_contract(
                root,
                {
                    "kind": "hierarchical",
                    "path": ".local/source/export",
                    "contentId": f"sha256:{digest(source_manifest)}",
                    "fileCount": 2,
                },
                digest(source_manifest),
            )
            self.assertEqual(run_open(root).returncode, 0)

            retained = root / ".local/targets/sample/snapshot/Documents/Order.xml"
            retained.chmod(0o644)
            retained.write_text("bad", encoding="utf-8")
            self.assertEqual(response(run_open(root))["reasonCode"], "snapshot_invalid")
            self.assertEqual(retained.read_text(encoding="utf-8"), "bad")

    def test_cf_open_uses_repo_owned_algorithm_and_warm_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            template = export(root)
            expected = manifest(template)
            shutil.rmtree(template)
            source = root / ".local/dist/sample.cf"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"cf")
            write_contract(
                root,
                {"kind": "cf", "path": ".local/dist/sample.cf", "sha256": digest(b"cf")},
                digest(expected),
            )
            self.write_fake_runtime(root)

            cold = run_open(root)
            warm = run_open(root)

            self.assertEqual(cold.returncode, 0, cold.stdout)
            self.assertEqual(response(cold)["action"], "materialized")
            self.assertEqual(response(warm)["action"], "reused")
            self.assertEqual(source.read_bytes(), b"cf")
            self.assertEqual((root / ".local/runtime-count").read_text(), "1\n1\n1\n")

    def test_executor_runtime_contract_does_not_embed_jet_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            template = export(root)
            expected = manifest(template)
            shutil.rmtree(template)
            source = root / ".local/dist/sample.cf"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"cf")
            write_contract(
                root,
                {"kind": "cf", "path": ".local/dist/sample.cf", "sha256": digest(b"cf")},
                digest(expected),
            )
            self.write_fake_runtime(root, platform="executor/runtime/bin/custom-1c")

            opened = run_open(root)

            self.assertEqual(opened.returncode, 0, opened.stdout)
            self.assertEqual(response(opened)["action"], "materialized")

    def test_missing_or_malformed_runtime_contract_is_materializer_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / ".local/dist/sample.cf"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"cf")
            write_contract(
                root,
                {"kind": "cf", "path": ".local/dist/sample.cf", "sha256": digest(b"cf")},
                "0" * 64,
            )

            missing = response(run_open(root))
            self.assertEqual(missing["reasonCode"], "materializer_unavailable")
            self.assertEqual(missing["locator"], "docs/lab-bootstrap.md")

            invalid = root / "executor/runtime/one-c-runtime.json"
            invalid.parent.mkdir(parents=True)
            invalid.write_text('{"schemaVersion":1,"platform":"relative"}', encoding="utf-8")
            os.environ["ONE_C_HARNESS_RUNTIME_CONFIG"] = str(invalid)
            self.assertEqual(response(run_open(root))["reasonCode"], "materializer_unavailable")

    def test_parallel_cf_open_materializes_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            template = export(root)
            expected = manifest(template)
            shutil.rmtree(template)
            source = root / ".local/dist/sample.cf"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"cf")
            write_contract(
                root,
                {"kind": "cf", "path": ".local/dist/sample.cf", "sha256": digest(b"cf")},
                digest(expected),
            )
            self.write_fake_runtime(root)
            argv = [sys.executable, str(CLI), "open", "--repo-root", str(root)]

            first = subprocess.Popen(argv, text=True, stdout=subprocess.PIPE)
            second = subprocess.Popen(argv, text=True, stdout=subprocess.PIPE)
            first_output, _ = first.communicate(timeout=15)
            second_output, _ = second.communicate(timeout=15)

            self.assertEqual((first.returncode, second.returncode), (0, 0))
            actions = {json.loads(first_output)["action"], json.loads(second_output)["action"]}
            self.assertEqual(actions, {"materialized", "reused"})
            self.assertEqual((root / ".local/runtime-count").read_text(), "1\n1\n1\n")

    def test_failed_open_retains_only_existing_diagnostics_before_cleanup(self) -> None:
        for failure in (cf_materializer.MaterializationFailed("failed"), KeyboardInterrupt()):
            with self.subTest(failure=type(failure).__name__), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / ".local/dist/sample.cf"
                source.parent.mkdir(parents=True)
                source.write_bytes(b"cf")
                source.chmod(0o440)
                write_contract(root, {"kind": "cf", "path": ".local/dist/sample.cf",
                                      "sha256": digest(b"cf")}, "0" * 64)
                before = (source.read_bytes(), source.stat().st_mode)
                diagnostics = {"create.log": b"created\r\n", "create.result": b"0",
                               "load.log": b"\xffnative error", "load.result": b"1"}

                def fail(**kwargs):
                    work = kwargs["work_root"]
                    (work / "logs").mkdir(parents=True)
                    for name, payload in diagnostics.items():
                        (work / "logs" / name).write_bytes(payload)
                    (work / "ib").mkdir()
                    (work / "ib/1Cv8.1CD").write_bytes(b"database")
                    (work / "logs/unrelated.bin").write_bytes(b"not a diagnostic")
                    kwargs["output"].mkdir()
                    (kwargs["output"] / "partial.xml").write_bytes(b"partial")
                    raise failure

                with mock.patch.object(project_target, "materialize_cf", side_effect=fail):
                    with self.assertRaises((project_target.TargetBlocked, KeyboardInterrupt)) as caught:
                        project_target.open_target(root)
                retained = list((root / ".local/runs").glob("project-target-failed-*"))
                self.assertEqual(len(retained), 1)
                self.assertEqual({p.name: p.read_bytes() for p in retained[0].iterdir()}, diagnostics)
                self.assertEqual(list((root / ".local/targets").iterdir()), [])
                self.assertEqual((source.read_bytes(), source.stat().st_mode), before)
                if isinstance(failure, KeyboardInterrupt):
                    self.assertIs(caught.exception, failure)
                else:
                    self.assertEqual(caught.exception.reason_code, "materialization_failed")
                    self.assertIs(caught.exception.__cause__, failure)
                    self.assertEqual(caught.exception.locator, retained[0].relative_to(root).as_posix())

    def test_retention_failure_preserves_primary_error_and_cleans_staging(self) -> None:
        for obstacle in ("runs-symlink", "logs-symlink", "file-symlink", "work-symlink", "copy-error"):
            with self.subTest(obstacle=obstacle), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / ".local/dist/sample.cf"
                source.parent.mkdir(parents=True)
                source.write_bytes(b"cf")
                write_contract(root, {"kind": "cf", "path": ".local/dist/sample.cf",
                                      "sha256": digest(b"cf")}, "0" * 64)
                external = root / "external"
                external.mkdir()
                sentinel = external / "create.log"
                sentinel.write_bytes(b"untouched")
                sentinel.chmod(0o440)
                before = (sentinel.read_bytes(), sentinel.stat().st_mode)
                failure = project_target.TargetBlocked("materialization_failed", "primary failure")

                def fail(**kwargs):
                    work = kwargs["work_root"]
                    if obstacle == "work-symlink":
                        work.symlink_to(external, target_is_directory=True)
                    else:
                        work.mkdir()
                        logs = work / "logs"
                        if obstacle == "logs-symlink":
                            logs.symlink_to(external, target_is_directory=True)
                        else:
                            logs.mkdir()
                            if obstacle == "file-symlink":
                                (logs / "create.log").symlink_to(sentinel)
                            else:
                                (logs / "create.log").write_bytes(b"diagnostic")
                    if obstacle == "runs-symlink":
                        (root / ".local/runs").symlink_to(external, target_is_directory=True)
                    raise failure

                original_copy = project_target.shutil.copyfile
                def copy(*args, **kwargs):
                    if obstacle == "copy-error":
                        raise OSError("disk failure")
                    return original_copy(*args, **kwargs)

                with mock.patch.object(project_target, "materialize_cf", side_effect=fail), \
                     mock.patch.object(project_target.shutil, "copyfile", side_effect=copy):
                    with self.assertRaises(project_target.TargetBlocked) as caught:
                        project_target.open_target(root)
                self.assertIs(caught.exception, failure)
                self.assertEqual(failure.reason_code, "materialization_failed")
                self.assertIn("diagnostic retention failed", failure.message)
                self.assertTrue(any("diagnostic retention failed" in note for note in failure.__notes__))
                self.assertEqual(list((root / ".local/targets").iterdir()), [])
                self.assertEqual((sentinel.read_bytes(), sentinel.stat().st_mode), before)
                self.assertEqual(list(external.iterdir()), [sentinel])

    def test_snapshot_mismatch_retains_successful_native_step_logs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / ".local/dist/sample.cf"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"cf")
            write_contract(root, {"kind": "cf", "path": ".local/dist/sample.cf",
                                  "sha256": digest(b"cf")}, "0" * 64)

            def materialize(**kwargs):
                logs = kwargs["work_root"] / "logs"
                logs.mkdir(parents=True)
                (logs / "dump.log").write_bytes(b"export finished")
                (logs / "dump.result").write_bytes(b"0")
                kwargs["output"].mkdir()
                (kwargs["output"] / "unexpected.xml").write_bytes(b"unexpected")

            with mock.patch.object(project_target, "materialize_cf", side_effect=materialize):
                with self.assertRaises(project_target.TargetBlocked) as caught:
                    project_target.open_target(root)
            self.assertEqual(caught.exception.reason_code, "materialization_failed")
            retained = list((root / ".local/runs").glob("project-target-failed-*"))
            self.assertEqual(len(retained), 1)
            self.assertEqual((retained[0] / "dump.log").read_bytes(), b"export finished")
            self.assertEqual(list((root / ".local/targets").iterdir()), [])

    def test_diagnostics_preserve_failure_without_callable_add_note(self) -> None:
        class MissingAddNote:
            def __getattribute__(self, name):
                if name == "add_note":
                    raise AttributeError(name)
                return super().__getattribute__(name)

        class LegacyBlocked(MissingAddNote, project_target.TargetBlocked):
            pass

        class LegacyInterrupt(MissingAddNote, KeyboardInterrupt):
            pass

        for api in ("missing", "noncallable"):
            for interrupted in (False, True):
                for outcome in ("retained", "retention-error", "cleanup-error"):
                    with self.subTest(api=api, interrupted=interrupted, outcome=outcome), \
                         tempfile.TemporaryDirectory() as temporary:
                        root = Path(temporary)
                        source = root / ".local/dist/sample.cf"
                        source.parent.mkdir(parents=True)
                        source.write_bytes(b"cf")
                        write_contract(root, {"kind": "cf", "path": ".local/dist/sample.cf",
                                              "sha256": digest(b"cf")}, "0" * 64)
                        if api == "missing":
                            failure = (LegacyInterrupt() if interrupted else
                                       LegacyBlocked("materialization_failed", "primary failure"))
                        else:
                            failure = (KeyboardInterrupt() if interrupted else
                                       project_target.TargetBlocked("materialization_failed", "primary failure"))
                            failure.add_note = None

                        def fail(**kwargs):
                            logs = kwargs["work_root"] / "logs"
                            logs.mkdir(parents=True)
                            (logs / "create.log").write_bytes(b"diagnostic")
                            if outcome == "retention-error":
                                (root / ".local/runs").write_bytes(b"not a directory")
                            raise failure

                        original_remove = project_target.remove_owned

                        def remove(path):
                            if outcome == "cleanup-error":
                                raise OSError("cleanup failed")
                            original_remove(path)

                        with mock.patch.object(project_target, "materialize_cf", side_effect=fail), \
                             mock.patch.object(project_target, "remove_owned", side_effect=remove):
                            with self.assertRaises(type(failure)) as caught:
                                project_target.open_target(root)
                        self.assertIs(caught.exception, failure)
                        expected = {"retained": "Failure diagnostics retained at",
                                    "retention-error": "diagnostic retention failed",
                                    "cleanup-error": "staging cleanup failed"}[outcome]
                        self.assertTrue(any(expected in note for note in failure.__notes__))
                        if not interrupted:
                            self.assertEqual(failure.reason_code, "materialization_failed")
                            if outcome == "retention-error" or outcome == "cleanup-error":
                                self.assertIn(expected, failure.message)
                            else:
                                self.assertEqual((root / failure.locator / "create.log").read_bytes(), b"diagnostic")
                        if outcome != "cleanup-error":
                            self.assertEqual(list((root / ".local/targets").iterdir()), [])

    def test_cleanup_failure_does_not_replace_primary_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / ".local/dist/sample.cf"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"cf")
            write_contract(root, {"kind": "cf", "path": ".local/dist/sample.cf",
                                  "sha256": digest(b"cf")}, "0" * 64)
            failure = project_target.TargetBlocked("materialization_failed", "primary failure")
            with mock.patch.object(project_target, "materialize_cf", side_effect=failure), \
                 mock.patch.object(project_target, "remove_owned", side_effect=OSError("cleanup failed")):
                with self.assertRaises(project_target.TargetBlocked) as caught:
                    project_target.open_target(root)
            self.assertIs(caught.exception, failure)
            self.assertIn("staging cleanup failed", failure.message)
            self.assertTrue(any("staging cleanup failed" in note for note in failure.__notes__))

    def test_cf_materializer_rejects_bad_dump_result_and_cleans_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.cf"
            source.write_bytes(b"cf")
            output = root / "output"
            work = root / "work"
            self.write_fake_runtime(root)

            def bad_runner(argv, **_kwargs):
                result = Path(argv[argv.index("/DumpResult") + 1])
                result.parent.mkdir(parents=True, exist_ok=True)
                result.write_text("1", encoding="utf-8")
                return subprocess.CompletedProcess(argv, 0)

            with self.assertRaises(cf_materializer.MaterializationFailed):
                cf_materializer.materialize_cf(
                    repo_root=root,
                    source=source,
                    output=output,
                    work_root=work,
                    runner=bad_runner,
                )
            self.assertFalse(output.exists())

    def test_cf_materializer_cleans_xvfb_process_group_after_successful_step(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = root / "result"
            result.write_text("0", encoding="utf-8")

            class FinishedProcess:
                pid = 4321
                returncode = 0

                def communicate(self, timeout):
                    return (b"", b"")

            group_alive = True

            def process_group(signal_number):
                nonlocal group_alive
                if signal_number == 0 and not group_alive:
                    raise ProcessLookupError()
                if signal_number == signal.SIGTERM:
                    group_alive = False

            with mock.patch.object(cf_materializer.subprocess, "Popen", return_value=FinishedProcess()), \
                 mock.patch.object(cf_materializer.os, "killpg", side_effect=lambda _pid, signal_number: process_group(signal_number)):
                cf_materializer._run_step(["native"], {}, result, runner=subprocess.run)

    def test_owned_cleanup_does_not_follow_symlink_to_external_sentinel(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sentinel = root / "external-sentinel"
            sentinel.write_bytes(b"do not touch")
            sentinel.chmod(0o640)
            owned = root / "owned"
            owned.mkdir()
            (owned / "escape").symlink_to(sentinel)
            before = (sentinel.read_bytes(), stat.S_IMODE(sentinel.stat().st_mode))

            target_admission.remove_owned(owned)

            self.assertFalse(owned.exists())
            self.assertEqual(
                (sentinel.read_bytes(), stat.S_IMODE(sentinel.stat().st_mode)), before
            )

    def test_symlink_and_hardlink_source_entries_do_not_bypass_admission(self) -> None:
        for kind in ("symlink", "hardlink"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = hierarchical_project(root)
                document = source / "Documents/Order.xml"
                if kind == "symlink":
                    replacement = root / "external.xml"
                    replacement.write_text("<MetaDataObject/>", encoding="utf-8")
                    document.unlink()
                    document.symlink_to(replacement)
                else:
                    duplicate = source / "Documents/Duplicate.xml"
                    os.link(document, duplicate)

                blocked = response(run_open(root))

                self.assertEqual(blocked["reasonCode"], "source_mismatch")
                self.assertFalse((root / ".local/targets/sample").exists())

    def test_duplicate_keys_and_boolean_file_count_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hierarchical_project(root)
            duplicate_contract = (
                '{"schemaVersion":2,"schemaVersion":2,"configuration":{},'
                '"source":{},"snapshot":{},"dailyNativeRoute":""}'
            )
            (root / "project-target.json").write_text(duplicate_contract, encoding="utf-8")
            self.assertEqual(response(run_open(root))["reasonCode"], "snapshot_invalid")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = hierarchical_project(root)
            value = json.loads((root / "project-target.json").read_text(encoding="utf-8"))
            value["snapshot"]["fileCount"] = True
            (root / "project-target.json").write_text(json.dumps(value), encoding="utf-8")

            self.assertEqual(response(run_open(root))["reasonCode"], "snapshot_invalid")
            self.assertTrue(source.exists())

    def test_unsupported_source_is_distinct_from_invalid_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_contract(root, {"kind": "edt", "path": ".local/source"}, "0" * 64)
            self.assertEqual(response(run_open(root))["reasonCode"], "unsupported_source")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / ".local/dist/sample.cf"
            source.parent.mkdir(parents=True)
            source.mkdir()
            write_contract(
                root,
                {"kind": "cf", "path": ".local/dist/sample.cf", "sha256": "0" * 64},
                "0" * 64,
            )
            self.assertEqual(response(run_open(root))["reasonCode"], "source_mismatch")

    def test_run_and_prepared_cleanup_do_not_touch_retained_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hierarchical_project(root)
            self.assertEqual(run_open(root).returncode, 0)
            retained = root / ".local/targets/sample"
            prepared = root / ".local/prepared/task-owned"
            generated = root / ".local/runs/task-owned/run/work-copy"
            prepared.mkdir(parents=True)
            generated.mkdir(parents=True)
            (prepared / "temporary.txt").write_text("temporary", encoding="utf-8")
            (generated / "temporary.txt").write_text("temporary", encoding="utf-8")

            managed_probe_prepare.discard_prepared_tree(
                repo_root=root,
                prepared_root=prepared,
            )
            native_cycle._remove_generated_tree(generated)

            self.assertFalse(prepared.exists())
            self.assertFalse(generated.exists())
            self.assertTrue((retained / "snapshot/Configuration.xml").is_file())
            self.assertTrue((retained / "snapshot.manifest").is_file())

    @staticmethod
    def write_fake_runtime(
        root: Path,
        *,
        platform: str = "executor/runtime/bin/1cv8t",
    ) -> None:
        binary = root / platform
        xvfb = root / "executor/runtime/bin/xvfb-run"
        fontconfig = root / "executor/runtime/fonts.conf"
        libraries = root / "executor/runtime/libs"
        binary.parent.mkdir(parents=True, exist_ok=True)
        xvfb.parent.mkdir(parents=True, exist_ok=True)
        fontconfig.parent.mkdir(parents=True, exist_ok=True)
        libraries.mkdir(parents=True, exist_ok=True)
        binary.write_text("x", encoding="utf-8")
        fontconfig.write_text("<fontconfig/>", encoding="utf-8")
        runtime_contract = root / "executor/runtime/one-c-runtime.json"
        runtime_contract.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "platform": str(binary),
                    "xvfb": str(xvfb),
                    "fontconfig": str(fontconfig),
                    "libs": str(libraries),
                }
            ),
            encoding="utf-8",
        )
        os.environ["ONE_C_HARNESS_RUNTIME_CONFIG"] = str(runtime_contract)
        script = f'''#!/usr/bin/env python3
import sys
from pathlib import Path

args = sys.argv[1:]
root = Path({str(root)!r})
with (root / ".local/runtime-count").open("a") as stream:
    stream.write("1\\n")
result = Path(args[args.index("/DumpResult") + 1])
result.parent.mkdir(parents=True, exist_ok=True)
result.write_text("0", encoding="utf-8")
if "/DumpConfigToFiles" in args:
    output = Path(args[args.index("/DumpConfigToFiles") + 1])
    output.mkdir()
    (output / "Configuration.xml").write_text(
        "<MetaDataObject><Configuration><Properties><Name>Sample</Name>"
        "<Version>2.0</Version></Properties></Configuration></MetaDataObject>",
        encoding="utf-8",
    )
    (output / "Documents").mkdir()
    (output / "Documents/Order.xml").write_text("<MetaDataObject/>", encoding="utf-8")
'''
        xvfb.write_text(script, encoding="utf-8")
        xvfb.chmod(0o755)
        binary.chmod(0o755)


if __name__ == "__main__":
    unittest.main()
