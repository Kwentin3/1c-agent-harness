from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "project_target.py"


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def manifest_for(root: Path) -> bytes:
    return "".join(
        f"{digest(path.read_bytes())}  {path.relative_to(root).as_posix()}\n"
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ).encode("utf-8")


def write_source(root: Path, relative: str = ".local/source/export") -> Path:
    source = root / relative
    source.mkdir(parents=True)
    files = {
        "Configuration.xml": (
            b'<MetaDataObject><Configuration><Properties>'
            b'<Name>Sample</Name><Version>2.0</Version>'
            b'</Properties></Configuration></MetaDataObject>\n'
        ),
        "Documents/Order.xml": b"<MetaDataObject/>\n",
    }
    for name, payload in files.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return source


def write_contract(
    root: Path,
    *,
    source: dict[str, object],
    content_id: str,
    file_count: int = 2,
) -> None:
    contract = {
        "schemaVersion": 2,
        "configuration": {"name": "Sample", "version": "2.0"},
        "source": source,
        "snapshot": {
            "root": ".local/targets/sample-2.0/snapshot",
            "manifest": ".local/targets/sample-2.0/snapshot.manifest",
            "contentId": f"sha256:{content_id}",
            "fileCount": file_count,
        },
        "dailyNativeRoute": "scripts/shared_task_route.py run",
    }
    (root / "project-target.json").write_text(
        json.dumps(contract, indent=2) + "\n", encoding="utf-8"
    )


def hierarchical_project(root: Path) -> Path:
    source = write_source(root)
    payload = manifest_for(source)
    write_contract(
        root,
        source={
            "kind": "hierarchical",
            "path": ".local/source/export",
            "contentId": f"sha256:{digest(payload)}",
            "fileCount": 2,
        },
        content_id=digest(payload),
    )
    return source


def run_open(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "open", "--repo-root", str(root)],
        text=True,
        capture_output=True,
        check=False,
    )


def parsed(completed: subprocess.CompletedProcess[str]) -> dict[str, object]:
    return json.loads(completed.stdout)


class ProjectTargetOpenTests(unittest.TestCase):
    def test_hierarchical_source_materializes_snapshot_ref_for_source_agnostic_consumer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            source = hierarchical_project(repo)
            source_before = manifest_for(source)

            completed = run_open(repo)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = parsed(completed)
            self.assertEqual(
                result,
                {
                    "action": "materialized",
                    "schemaVersion": 1,
                    "snapshot": {
                        "configuration": {"name": "Sample", "version": "2.0"},
                        "contentId": f"sha256:{digest(source_before)}",
                        "fileCount": 2,
                        "format": "hierarchical",
                        "kind": "1c-configuration-files",
                        "manifest": ".local/targets/sample-2.0/snapshot.manifest",
                        "root": ".local/targets/sample-2.0/snapshot",
                    },
                    "sourceIdentity": f"sha256:{digest(source_before)}",
                    "status": "ready",
                },
            )
            snapshot_ref = result["snapshot"]
            self.assertIsInstance(snapshot_ref, dict)
            configuration = repo / str(snapshot_ref["root"]) / "Configuration.xml"
            self.assertIn(b"<Name>Sample</Name>", configuration.read_bytes())
            self.assertEqual(manifest_for(source), source_before)
            self.assertNotIn(str(repo), completed.stdout)

    def test_warm_open_is_deterministic_reuse_without_source_or_native(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            source = hierarchical_project(repo)
            cold = run_open(repo)
            self.assertEqual(cold.returncode, 0, cold.stdout)
            target = repo / ".local/targets/sample-2.0"
            before = {
                path.relative_to(target).as_posix(): (path.stat().st_ino, path.stat().st_mtime_ns)
                for path in target.rglob("*")
                if path.is_file()
            }
            shutil.rmtree(source)

            first = run_open(repo)
            second = run_open(repo)

            self.assertEqual(first.returncode, 0, first.stdout)
            self.assertEqual(first.stdout, second.stdout)
            self.assertEqual(parsed(first)["action"], "reused")
            self.assertEqual(parsed(first)["snapshot"], parsed(cold)["snapshot"])
            after = {
                path.relative_to(target).as_posix(): (path.stat().st_ino, path.stat().st_mtime_ns)
                for path in target.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, before)

    def test_reuse_rejects_contract_rebinding_to_another_source_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            source = hierarchical_project(repo)
            self.assertEqual(run_open(repo).returncode, 0)
            shutil.rmtree(source)
            contract_path = repo / "project-target.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["source"]["contentId"] = f"sha256:{'1' * 64}"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")

            completed = run_open(repo)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(parsed(completed)["reasonCode"], "snapshot_invalid")

    def test_missing_hierarchical_source_returns_one_stable_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            source = hierarchical_project(repo)
            shutil.rmtree(source)

            completed = run_open(repo)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(
                parsed(completed),
                {
                    "message": "declared source does not exist",
                    "reasonCode": "source_missing",
                    "schemaVersion": 1,
                    "status": "blocked",
                },
            )
            self.assertEqual(completed.stderr, "")
            self.assertFalse((repo / ".local/targets/sample-2.0").exists())

    def test_unsupported_source_returns_exact_blocker_without_touching_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            write_contract(
                repo,
                source={"kind": "edt", "path": ".local/source/project"},
                content_id="0" * 64,
            )

            completed = run_open(repo)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(parsed(completed)["reasonCode"], "unsupported_source")
            self.assertNotIn("Traceback", completed.stdout + completed.stderr)
            self.assertFalse((repo / ".local/targets/sample-2.0").exists())

    def test_mismatched_hierarchical_source_is_not_partially_published(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            source = hierarchical_project(repo)
            (source / "Documents/Order.xml").write_bytes(b"changed")

            completed = run_open(repo)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(parsed(completed)["reasonCode"], "source_mismatch")
            self.assertFalse((repo / ".local/targets/sample-2.0").exists())
            targets = repo / ".local/targets"
            self.assertFalse(any(targets.glob(".sample-2.0.staging-*")))

    def test_corrupted_retained_target_is_not_repaired_or_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            hierarchical_project(repo)
            self.assertEqual(run_open(repo).returncode, 0)
            target_file = repo / ".local/targets/sample-2.0/snapshot/Documents/Order.xml"
            target_file.chmod(target_file.stat().st_mode | stat.S_IWUSR)
            target_file.write_bytes(b"corrupted")
            corrupted = target_file.read_bytes()

            completed = run_open(repo)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(parsed(completed)["reasonCode"], "snapshot_invalid")
            self.assertEqual(target_file.read_bytes(), corrupted)

    def test_cf_without_local_capability_returns_actionable_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            source = repo / ".local/dist/sample.cf"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"sample-cf")
            write_contract(
                repo,
                source={"kind": "cf", "path": ".local/dist/sample.cf", "sha256": digest(b"sample-cf")},
                content_id="0" * 64,
            )

            completed = run_open(repo)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(
                parsed(completed),
                {
                    "locator": "docs/lab-bootstrap.md",
                    "message": "local cf_to_hierarchical_snapshot capability is unavailable",
                    "reasonCode": "materializer_unavailable",
                    "schemaVersion": 1,
                    "status": "blocked",
                },
            )
            self.assertFalse((repo / ".local/targets/sample-2.0").exists())

    def test_cf_capability_without_snapshot_is_materialization_failed_and_cleans_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            source = repo / ".local/dist/sample.cf"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"sample-cf")
            write_contract(
                repo,
                source={"kind": "cf", "path": ".local/dist/sample.cf", "sha256": digest(b"sample-cf")},
                content_id="0" * 64,
            )
            capability = repo / ".local/capabilities/cf_to_hierarchical_snapshot"
            capability.parent.mkdir(parents=True)
            capability.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            capability.chmod(0o755)

            completed = run_open(repo)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(parsed(completed)["reasonCode"], "materialization_failed")
            targets = repo / ".local/targets"
            self.assertFalse((targets / "sample-2.0").exists())
            self.assertFalse(any(targets.glob(".sample-2.0.staging-*")))

    def test_cf_capability_materializes_once_and_cleans_staging_work(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            template = write_source(repo, ".local/template")
            payload = manifest_for(template)
            source = repo / ".local/dist/sample.cf"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"sample-cf")
            source_before = source.read_bytes()
            write_contract(
                repo,
                source={"kind": "cf", "path": ".local/dist/sample.cf", "sha256": digest(source_before)},
                content_id=digest(payload),
            )
            self._write_capability(repo, template)

            cold = run_open(repo)
            warm = run_open(repo)

            self.assertEqual(cold.returncode, 0, cold.stdout)
            self.assertEqual(parsed(cold)["action"], "materialized")
            self.assertEqual(parsed(warm)["action"], "reused")
            self.assertEqual(source.read_bytes(), source_before)
            self.assertEqual((repo / ".local/capability-count").read_text(), "1\n")
            targets = repo / ".local/targets"
            self.assertFalse(any(targets.glob(".sample-2.0.staging-*")))

    def test_parallel_cf_open_publishes_one_target_and_runs_capability_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            template = write_source(repo, ".local/template")
            payload = manifest_for(template)
            source = repo / ".local/dist/sample.cf"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"sample-cf")
            write_contract(
                repo,
                source={"kind": "cf", "path": ".local/dist/sample.cf", "sha256": digest(b"sample-cf")},
                content_id=digest(payload),
            )
            self._write_capability(repo, template, delay=0.3)
            argv = [sys.executable, str(CLI), "open", "--repo-root", str(repo)]

            first = subprocess.Popen(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            second = subprocess.Popen(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            first_out, first_err = first.communicate(timeout=10)
            second_out, second_err = second.communicate(timeout=10)

            self.assertEqual((first.returncode, second.returncode), (0, 0), first_err + second_err)
            actions = {json.loads(first_out)["action"], json.loads(second_out)["action"]}
            self.assertEqual(actions, {"materialized", "reused"})
            self.assertEqual((repo / ".local/capability-count").read_text(), "1\n")
            self.assertTrue((repo / ".local/targets/sample-2.0/snapshot/Configuration.xml").is_file())

    def test_existing_cleanup_seams_cannot_remove_retained_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            hierarchical_project(repo)
            self.assertEqual(run_open(repo).returncode, 0)
            retained = repo / ".local/targets/sample-2.0"
            prepared = repo / ".local/prepared/task-owned"
            prepared.mkdir(parents=True)
            (prepared / "temporary.txt").write_text("temporary")
            invocation = repo / ".local/runs/invocation/run/work-copy"
            invocation.mkdir(parents=True)
            (invocation / "temporary.txt").write_text("temporary")
            sys.path.insert(0, str(ROOT / "scripts"))
            try:
                import managed_probe_prepare
                import native_cycle

                managed_probe_prepare.discard_prepared_tree(
                    repo_root=repo, prepared_root=prepared
                )
                native_cycle._remove_generated_tree(invocation)
            finally:
                sys.path.pop(0)

            self.assertFalse(prepared.exists())
            self.assertFalse(invocation.exists())
            self.assertTrue((retained / "snapshot/Configuration.xml").is_file())
            self.assertTrue((retained / "snapshot.manifest").is_file())

    @staticmethod
    def _write_capability(repo: Path, template: Path, delay: float = 0.0) -> None:
        capability = repo / ".local/capabilities/cf_to_hierarchical_snapshot"
        capability.parent.mkdir(parents=True)
        script = f"""#!/usr/bin/env python3
import argparse
from pathlib import Path
import shutil
import time
p = argparse.ArgumentParser()
p.add_argument('--source', required=True)
p.add_argument('--output', required=True)
p.add_argument('--work-root', required=True)
a = p.parse_args()
Path(a.work_root).mkdir(parents=True, exist_ok=True)
with (Path({str(repo / '.local/capability-count')!r})).open('a') as stream:
    stream.write('1\\n')
time.sleep({delay!r})
shutil.copytree(Path({str(template)!r}), Path(a.output))
"""
        capability.write_text(script, encoding="utf-8")
        capability.chmod(0o755)


if __name__ == "__main__":
    unittest.main()
