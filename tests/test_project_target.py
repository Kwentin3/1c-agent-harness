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
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "project_target.py"
sys.path.insert(0, str(ROOT / "scripts"))

import cf_materializer
import managed_probe_prepare
import native_cycle
import target_admission


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

            (root / ".local/one-c-runtime.json").write_text(
                '{"schemaVersion":1,"platform":"relative"}', encoding="utf-8"
            )
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
        platform: str = ".local/platform/1cv8t/x86_64/8.5.1.1150/1cv8t",
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
        (root / ".local/one-c-runtime.json").write_text(
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
