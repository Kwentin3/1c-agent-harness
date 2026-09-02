from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "project_target.py"


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def run_cli(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "--repo-root", str(repo)],
        text=True,
        capture_output=True,
        check=False,
    )


def write_project(root: Path) -> None:
    source = root / ".local/dist/Jet-1.0.3.1-tr.cf"
    snapshot = root / ".local/runs/training-jet-review-final/snapshot"
    manifest = snapshot.parent / "snapshot.manifest"
    source.parent.mkdir(parents=True)
    snapshot.mkdir(parents=True)
    source.write_bytes(b"canonical-cf")
    files = {
        "Configuration.xml": (
            b'<?xml version="1.0" encoding="UTF-8"?>\n'
            b'<MetaDataObject><Configuration><Properties>'
            b'<Name>JetTr</Name><Version>1.0.3.1</Version>'
            b'</Properties></Configuration></MetaDataObject>\n'
        ),
        "CommonModules/Example/Ext/Module.bsl": b"Procedure Example()\nEndProcedure\n",
    }
    for relative, payload in files.items():
        path = snapshot / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    manifest_payload = "".join(
        f"{sha256(payload)}  {relative}\n"
        for relative, payload in sorted(files.items())
    ).encode()
    manifest.write_bytes(manifest_payload)
    contract = {
        "schemaVersion": 1,
        "configuration": {"name": "JetTr", "version": "1.0.3.1"},
        "sourceCf": {
            "path": ".local/dist/Jet-1.0.3.1-tr.cf",
            "sha256": sha256(b"canonical-cf"),
        },
        "snapshot": {
            "path": ".local/runs/training-jet-review-final/snapshot",
            "manifestPath": ".local/runs/training-jet-review-final/snapshot.manifest",
            "manifestSha256": sha256(manifest_payload),
            "fileCount": len(files),
        },
        "dailyNativeRoute": "scripts/shared_task_route.py run",
    }
    (root / "project-target.json").write_text(
        json.dumps(contract, indent=2) + "\n", encoding="utf-8"
    )


class ProjectTargetCliTests(unittest.TestCase):
    def test_project_owned_contract_can_define_another_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            write_project(repo)
            snapshot = repo / ".local/runs/training-jet-review-final/snapshot"
            configuration = snapshot / "Configuration.xml"
            configuration.write_bytes(
                b'<MetaDataObject><Configuration><Properties>'
                b'<Name>OtherProject</Name><Version>2.0</Version>'
                b'</Properties></Configuration></MetaDataObject>\n'
            )
            manifest = snapshot.parent / "snapshot.manifest"
            manifest_payload = "".join(
                f"{sha256(path.read_bytes())}  {path.relative_to(snapshot).as_posix()}\n"
                for path in sorted(snapshot.rglob("*"))
                if path.is_file()
            ).encode()
            manifest.write_bytes(manifest_payload)
            contract_path = repo / "project-target.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["configuration"] = {"name": "OtherProject", "version": "2.0"}
            contract["snapshot"]["manifestSha256"] = sha256(manifest_payload)
            contract_path.write_text(json.dumps(contract), encoding="utf-8")

            completed = run_cli(repo)

            self.assertEqual(completed.returncode, 0, completed.stdout)
            self.assertEqual(
                json.loads(completed.stdout)["configuration"],
                {"name": "OtherProject", "version": "2.0"},
            )

    def test_rejects_contract_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            outer = Path(temporary)
            repo = outer / "repo"
            repo.mkdir()
            write_project(repo)
            contract_path = repo / "project-target.json"
            outside = outer / "contract.json"
            outside.write_bytes(contract_path.read_bytes())
            contract_path.unlink()
            contract_path.symlink_to(outside)

            completed = run_cli(repo)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(
                json.loads(completed.stdout)["reason"],
                "project-target.json contains a symlink component",
            )

    def test_rejects_multiply_linked_identity_inputs(self) -> None:
        cases = {
            "project-target.json": "project-target.json",
            "source CF": ".local/dist/Jet-1.0.3.1-tr.cf",
            "snapshot manifest": ".local/runs/training-jet-review-final/snapshot.manifest",
        }
        for field, relative in cases.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                repo = Path(temporary)
                write_project(repo)
                target = repo / relative
                alias = repo / f"{field.replace(' ', '-')}.alias"
                alias.write_bytes(target.read_bytes())
                target.unlink()
                os.link(alias, target)

                completed = run_cli(repo)

                self.assertEqual(completed.returncode, 1, completed.stdout)
                self.assertEqual(
                    json.loads(completed.stdout)["reason"],
                    f"{field} must have exactly one hard link",
                )

    def test_reports_verified_target_and_single_daily_route(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            write_project(repo)

            completed = run_cli(repo)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["status"], "ready")
            self.assertEqual(result["configuration"], {"name": "JetTr", "version": "1.0.3.1"})
            self.assertEqual(result["sourceCf"]["actualSha256"], result["sourceCf"]["expectedSha256"])
            self.assertEqual(result["snapshot"]["actualManifestSha256"], result["snapshot"]["expectedManifestSha256"])
            self.assertEqual(result["snapshot"]["actualFileCount"], 2)
            self.assertEqual(result["dailyNativeRoute"], "scripts/shared_task_route.py run")

    def test_configuration_identity_uses_configuration_properties_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            write_project(repo)
            snapshot = repo / ".local/runs/training-jet-review-final/snapshot"
            configuration = snapshot / "Configuration.xml"
            configuration.write_bytes(
                b'<MetaDataObject><Configuration><Properties>'
                b'<Name>JetTr</Name><Version>1.0.3.1</Version>'
                b'</Properties><Distractor><Name>Other</Name><Version>9.9</Version>'
                b'</Distractor></Configuration></MetaDataObject>\n'
            )
            manifest = snapshot.parent / "snapshot.manifest"
            manifest_payload = "".join(
                f"{sha256(path.read_bytes())}  {path.relative_to(snapshot).as_posix()}\n"
                for path in sorted(snapshot.rglob("*"))
                if path.is_file()
            ).encode()
            manifest.write_bytes(manifest_payload)
            contract_path = repo / "project-target.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["snapshot"]["manifestSha256"] = sha256(manifest_payload)
            contract_path.write_text(json.dumps(contract), encoding="utf-8")

            completed = run_cli(repo)

            self.assertEqual(completed.returncode, 0, completed.stdout)
            self.assertEqual(
                json.loads(completed.stdout)["configuration"],
                {"name": "JetTr", "version": "1.0.3.1"},
            )

    def test_rejects_snapshot_bytes_not_bound_by_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            write_project(repo)
            (repo / ".local/runs/training-jet-review-final/snapshot/CommonModules/Example/Ext/Module.bsl").write_bytes(
                b"Procedure Changed()\nEndProcedure\n"
            )

            completed = run_cli(repo)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(json.loads(completed.stdout)["reason"], "snapshot content mismatch: CommonModules/Example/Ext/Module.bsl")

    def test_rejects_a_second_target_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            write_project(repo)
            contract_path = repo / "project-target.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["targets"] = [contract["configuration"]]
            contract_path.write_text(json.dumps(contract), encoding="utf-8")

            completed = run_cli(repo)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(
                json.loads(completed.stdout)["reason"],
                "contract keys mismatch: expected configuration, dailyNativeRoute, schemaVersion, snapshot, sourceCf",
            )

    def test_rejects_competing_daily_native_route(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            write_project(repo)
            contract_path = repo / "project-target.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["dailyNativeRoute"] = "scripts/native_cycle.py run"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")

            completed = run_cli(repo)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(
                json.loads(completed.stdout)["reason"],
                "dailyNativeRoute must be scripts/shared_task_route.py run",
            )

    def test_rejects_source_path_outside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            outer = Path(temporary)
            repo = outer / "repo"
            repo.mkdir()
            write_project(repo)
            outside = outer / "outside.cf"
            outside.write_bytes(b"outside-but-matching")
            contract_path = repo / "project-target.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["sourceCf"] = {
                "path": str(outside),
                "sha256": sha256(outside.read_bytes()),
            }
            contract_path.write_text(json.dumps(contract), encoding="utf-8")

            completed = run_cli(repo)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(
                json.loads(completed.stdout)["reason"],
                "sourceCf.path must stay within repository",
            )

    def test_rejects_duplicate_contract_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            write_project(repo)
            contract_path = repo / "project-target.json"
            text = contract_path.read_text(encoding="utf-8").replace(
                '"schemaVersion": 1,',
                '"schemaVersion": 1,\n  "schemaVersion": 1,',
                1,
            )
            contract_path.write_text(text, encoding="utf-8")

            completed = run_cli(repo)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(
                json.loads(completed.stdout)["reason"],
                "duplicate JSON key: schemaVersion",
            )

    def test_rejects_symlink_inside_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            write_project(repo)
            relative = "CommonModules/Example/Ext/Module.bsl"
            linked = repo / ".local/runs/training-jet-review-final/snapshot" / relative
            linked.unlink()
            outside = repo / "outside.bsl"
            outside.write_bytes(b"Procedure Example()\nEndProcedure\n")
            linked.symlink_to(outside)
            manifest = repo / ".local/runs/training-jet-review-final/snapshot.manifest"
            contract_path = repo / "project-target.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["snapshot"]["manifestSha256"] = sha256(manifest.read_bytes())
            contract_path.write_text(json.dumps(contract), encoding="utf-8")

            completed = run_cli(repo)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(
                json.loads(completed.stdout)["reason"],
                f"snapshot contains symlink: {relative}",
            )

    def test_rejects_5002_file_fixture_as_current_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            write_project(repo)
            snapshot = repo / ".local/runs/training-jet-review-final/snapshot"
            generated = snapshot / "Generated"
            generated.mkdir()
            for index in range(5000):
                (generated / f"{index:04d}.txt").write_bytes(b"")
            manifest = snapshot.parent / "snapshot.manifest"
            manifest_payload = "".join(
                f"{sha256(path.read_bytes())}  {path.relative_to(snapshot).as_posix()}\n"
                for path in sorted(snapshot.rglob("*"))
                if path.is_file()
            ).encode()
            manifest.write_bytes(manifest_payload)
            contract_path = repo / "project-target.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["snapshot"]["manifestSha256"] = sha256(manifest_payload)
            contract["snapshot"]["fileCount"] = 5099
            contract_path.write_text(json.dumps(contract), encoding="utf-8")

            completed = run_cli(repo)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(
                json.loads(completed.stdout)["reason"],
                "snapshot file count mismatch: expected 5099, got 5002",
            )

    def test_rejects_unsupported_contract_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            write_project(repo)
            contract_path = repo / "project-target.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["schemaVersion"] = 2
            contract_path.write_text(json.dumps(contract), encoding="utf-8")

            completed = run_cli(repo)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(
                json.loads(completed.stdout)["reason"],
                "unsupported schemaVersion: 2",
            )

    def test_rejects_fallback_source_in_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            write_project(repo)
            contract_path = repo / "project-target.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["sourceCf"]["fallbackPath"] = ".local/dist/Jet-1.0.2.1.cf"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")

            completed = run_cli(repo)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(
                json.loads(completed.stdout)["reason"],
                "sourceCf keys mismatch: expected path, sha256",
            )

    def test_rejects_boolean_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            write_project(repo)
            contract_path = repo / "project-target.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["schemaVersion"] = True
            contract_path.write_text(json.dumps(contract), encoding="utf-8")

            completed = run_cli(repo)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(
                json.loads(completed.stdout)["reason"],
                "schemaVersion must be integer 1",
            )

    def test_rejects_boolean_file_count(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            write_project(repo)
            snapshot = repo / ".local/runs/training-jet-review-final/snapshot"
            module = snapshot / "CommonModules/Example/Ext/Module.bsl"
            module.unlink()
            module.parent.rmdir()
            module.parent.parent.rmdir()
            module.parent.parent.parent.rmdir()
            configuration = snapshot / "Configuration.xml"
            manifest_payload = (
                f"{sha256(configuration.read_bytes())}  Configuration.xml\n"
            ).encode()
            manifest = snapshot.parent / "snapshot.manifest"
            manifest.write_bytes(manifest_payload)
            contract_path = repo / "project-target.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["snapshot"]["manifestSha256"] = sha256(manifest_payload)
            contract["snapshot"]["fileCount"] = True
            contract_path.write_text(json.dumps(contract), encoding="utf-8")

            completed = run_cli(repo)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(
                json.loads(completed.stdout)["reason"],
                "snapshot.fileCount must be a positive integer",
            )


if __name__ == "__main__":
    unittest.main()
