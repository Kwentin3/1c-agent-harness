from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock
import uuid

from one_c_harness import project_target, target_admission, task_artifacts


def fixture(root: Path) -> dict[str, object]:
    source = root / ".local/source/sample"
    source.mkdir(parents=True)
    (source / "Configuration.xml").write_text(
        "<MetaDataObject><Configuration><Properties><Name>Sample</Name>"
        "<Version>1.0</Version></Properties></Configuration></MetaDataObject>",
        encoding="utf-8",
    )
    (source / "Module.bsl").write_bytes(b"// synthetic source; never executed\n")
    content_id = "sha256:" + hashlib.sha256(target_admission.tree_manifest(source)).hexdigest()
    (root / "project-target.json").write_text(json.dumps({
        "schemaVersion": 2,
        "configuration": {"name": "Sample", "version": "1.0"},
        "source": {"kind": "hierarchical", "path": ".local/source/sample", "contentId": content_id, "fileCount": 2},
        "snapshot": {"root": ".local/targets/sample/snapshot", "manifest": ".local/targets/sample/snapshot.manifest", "contentId": content_id, "fileCount": 2},
        "dailyNativeRoute": "scripts/shared_task_route.py run",
    }), encoding="utf-8")
    # Real hierarchical admission/materialization; no native platform or stubs.
    reference = project_target.open_target(root)
    oracle = root / "experiments/sample/oracle.py"
    oracle.parent.mkdir(parents=True)
    oracle.write_bytes(b"raise RuntimeError('staging must not execute this file')\n")
    oracle.chmod(0o444)
    return reference


class TaskArtifactsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.addCleanup(self.cleanup)
        self.snapshot_ref = fixture(self.root)
        self.snapshot = self.root / str(self.snapshot_ref["snapshot"]["root"])
        self.oracle = self.root / "experiments/sample/oracle.py"
        self.source_before = target_admission.tree_manifest(self.snapshot)
        self.inputs = {
            "request": {"nonce": "fresh-test", "expected": "marker"},
            "production_patch": "not a patch: stage preserves exact UTF-8 \u00e9\r\n",
            "instrumentation_patch": "not executable instrumentation\n",
            "oracle": "experiments/sample/oracle.py",
        }

    def cleanup(self) -> None:
        # Only this explicitly created synthetic TemporaryDirectory is touched.
        if self.root.exists():
            for path in [self.root, *self.root.rglob("*")]:
                if not path.is_symlink():
                    path.chmod(path.stat().st_mode | stat.S_IRWXU)
        self.temporary.cleanup()

    def stage(self, **overrides: object) -> dict[str, object]:
        return task_artifacts.stage_task(
            repo_root=self.root, snapshot_ref=self.snapshot_ref, **{**self.inputs, **overrides},
        )

    def resolve(self, reference: dict[str, object], **overrides: object) -> dict[str, object]:
        return task_artifacts.resolve_task(**{
            "repo_root": self.root, "snapshot_ref": self.snapshot_ref,
            "task_ref": reference, **overrides,
        })

    def task(self, reference: dict[str, object]) -> Path:
        return self.root / ".local/task-artifacts" / str(reference["taskId"])

    def rewrite_manifest(self, reference: dict[str, object], mutate) -> dict[str, object]:
        path = self.task(reference) / "task.json"
        data = json.loads(path.read_bytes())
        mutate(data)
        payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
        self.overwrite(path, payload)
        return {**reference, "manifestSha256": hashlib.sha256(payload).hexdigest()}

    def overwrite(self, path: Path, payload: bytes) -> None:
        path.chmod(0o600)
        path.write_bytes(payload)
        path.chmod(0o400)

    def configured_oracle(self, relative: str = ".local/trusted-oracles/v1") -> Path:
        selected_root = self.root / relative
        oracle = selected_root / self.inputs["oracle"]
        oracle.parent.mkdir(parents=True)
        oracle.write_bytes(self.oracle.read_bytes())
        oracle.chmod(0o444)
        for directory in (oracle.parent, oracle.parent.parent, selected_root):
            directory.chmod(0o555)
        return oracle

    def test_stage_and_resolve_bind_real_inputs_without_execution_or_source_changes(self) -> None:
        oracle_before = self.oracle.read_bytes()
        reference = self.stage()
        self.assertEqual(set(reference), {"schemaVersion", "taskId", "manifestSha256"})
        self.assertEqual(uuid.UUID(reference["taskId"]).version, 4)
        task = self.task(reference)
        self.assertEqual({p.name for p in task.iterdir()}, {"request.json", "production.patch", "instrumentation.patch", "task.json"})
        self.assertEqual((task / "production.patch").read_bytes(), self.inputs["production_patch"].encode("utf-8"))
        self.assertEqual(json.loads((task / "request.json").read_bytes()), self.inputs["request"])
        self.assertEqual(json.loads((task / "task.json").read_bytes())["oracle"], {
            "root": ".", "path": self.inputs["oracle"],
            "sha256": hashlib.sha256(oracle_before).hexdigest(), "bytes": len(oracle_before),
        })
        resolved = self.resolve(reference)
        self.assertEqual(set(resolved), {"repo_root", "input_tree", "request_path", "patch_paths", "oracle_path", "receipt_path"})
        self.assertEqual(resolved["input_tree"], self.snapshot)
        self.assertEqual(self.root / resolved["request_path"], task / "request.json")
        self.assertEqual([role for role, _path in resolved["patch_paths"]], ["production", "instrumentation"])
        self.assertEqual(self.root / resolved["oracle_path"], self.oracle)
        self.assertEqual(self.root / resolved["receipt_path"], task / "receipt.json")
        self.assertFalse((task / "receipt.json").exists())
        self.assertFalse((self.root / ".local/prepared").exists())
        self.assertEqual(target_admission.tree_manifest(self.snapshot), self.source_before)
        self.assertEqual(self.oracle.read_bytes(), oracle_before)

    def test_configured_immutable_runtime_root_binds_manifest_and_actual_runner_path(self) -> None:
        relative = ".local/trusted-oracles/v1"
        oracle = self.configured_oracle(relative)
        before = target_admission.tree_manifest(self.root / relative)
        reference = self.stage(oracle_root=relative)
        manifest = json.loads((self.task(reference) / "task.json").read_bytes())
        self.assertEqual(manifest["oracle"], {
            "root": relative, "path": "experiments/sample/oracle.py",
            "sha256": hashlib.sha256(oracle.read_bytes()).hexdigest(), "bytes": oracle.stat().st_size,
        })
        resolved = self.resolve(reference, oracle_root=relative)
        self.assertEqual(resolved["oracle_path"], Path(relative) / "experiments/sample/oracle.py")
        self.assertEqual(self.root / resolved["oracle_path"], oracle)
        self.assertEqual(stat.S_IMODE((self.root / relative).stat().st_mode), 0o555)
        self.assertEqual(stat.S_IMODE(oracle.stat().st_mode), 0o444)
        self.assertEqual(target_admission.tree_manifest(self.root / relative), before)
        self.assertEqual(target_admission.tree_manifest(self.snapshot), self.source_before)
        self.assertFalse((self.root / resolved["receipt_path"]).exists())

    def test_explicit_repository_root_and_default_bind_the_same_canonical_root(self) -> None:
        reference = self.stage(oracle_root=".")
        self.assertEqual(self.resolve(reference), self.resolve(reference, oracle_root="."))
        self.assertEqual(self.resolve(reference)["oracle_path"], Path("experiments/sample/oracle.py"))

    def test_root_changes_refuse_identical_oracle_bytes_without_fallback(self) -> None:
        first = ".local/trusted-oracles/v1"
        second = ".local/trusted-oracles/v2"
        self.assertEqual(self.configured_oracle(first).read_bytes(), self.configured_oracle(second).read_bytes())
        reference = self.stage(oracle_root=first)
        before = target_admission.tree_manifest(self.task(reference))
        for selected in (None, second):
            with self.subTest(root=selected), self.assertRaisesRegex(ValueError, "oracle root binding"):
                self.resolve(reference, oracle_root=selected)
        default_reference = self.stage()
        with self.assertRaisesRegex(ValueError, "oracle root binding"):
            self.resolve(default_reference, oracle_root=first)
        self.assertEqual(target_admission.tree_manifest(self.task(reference)), before)

    def test_rehashed_manifest_cannot_replace_current_deployment_root(self) -> None:
        relative = ".local/trusted-oracles/v1"
        self.configured_oracle(relative)
        reference = self.stage(oracle_root=relative)
        forged = self.rewrite_manifest(reference, lambda data: data["oracle"].update(root="."))
        with self.assertRaisesRegex(ValueError, "oracle root binding"):
            self.resolve(forged, oracle_root=relative)

    def test_invalid_or_noncanonical_roots_refuse_stage_and_resolve(self) -> None:
        relative = ".local/trusted-oracles/v1"
        self.configured_oracle(relative)
        invalid = ("", 1, str(self.root), str(self.root.parent), "../" + self.root.name,
                   ".local/../experiments", "./" + relative, relative + "/",
                   relative.replace("/", "//", 1), ".local/no-such-root",
                   "experiments/sample/oracle.py")
        for selected in invalid:
            with self.subTest(root=selected), self.assertRaises(ValueError):
                self.stage(oracle_root=selected)
        self.assertFalse((self.root / ".local/task-artifacts").exists())
        reference = self.stage()
        before = target_admission.tree_manifest(self.task(reference))
        for selected in invalid:
            with self.subTest(root=selected), self.assertRaises(ValueError):
                self.resolve(reference, oracle_root=selected)
        self.assertEqual(target_admission.tree_manifest(self.task(reference)), before)

    def test_symlink_root_or_root_ancestor_is_rejected(self) -> None:
        relative = ".local/trusted-oracles/v1"
        self.configured_oracle(relative)
        linked = self.root / ".local/linked-oracle-root"
        linked.symlink_to(self.root / relative, target_is_directory=True)
        reference = self.stage()
        for selected in (".local/linked-oracle-root", ".local/linked-oracle-root/experiments"):
            with self.subTest(root=selected):
                with self.assertRaisesRegex(ValueError, "symlink"):
                    self.stage(oracle_root=selected)
                with self.assertRaisesRegex(ValueError, "symlink"):
                    self.resolve(reference, oracle_root=selected)

    def test_missing_configured_oracle_does_not_fall_back_to_project_oracle(self) -> None:
        missing = ".local/trusted-oracles/missing"
        (self.root / missing).mkdir(parents=True)
        with self.assertRaises(FileNotFoundError):
            self.stage(oracle_root=missing)
        self.assertFalse((self.root / ".local/task-artifacts").exists())
        relative = ".local/trusted-oracles/v1"
        oracle = self.configured_oracle(relative)
        reference = self.stage(oracle_root=relative)
        oracle.parent.chmod(0o755)
        oracle.unlink()
        oracle.parent.chmod(0o555)
        with self.assertRaises(FileNotFoundError):
            self.resolve(reference, oracle_root=relative)
        self.assertTrue(self.oracle.is_file())

    def test_configured_oracle_retains_readonly_and_byte_budget_checks(self) -> None:
        relative = ".local/trusted-oracles/v1"
        oracle = self.configured_oracle(relative)
        reference = self.stage(oracle_root=relative)
        before = target_admission.tree_manifest(self.task(reference))
        oracle.chmod(0o644)
        with self.assertRaises(ValueError):
            self.stage(oracle_root=relative)
        with self.assertRaises(ValueError):
            self.resolve(reference, oracle_root=relative)
        oracle.write_bytes(b"x" * 65537)
        oracle.chmod(0o444)
        with self.assertRaises(ValueError):
            self.stage(oracle_root=relative)
        with self.assertRaises(ValueError):
            self.resolve(reference, oracle_root=relative)
        self.assertEqual(target_admission.tree_manifest(self.task(reference)), before)

    def test_configured_oracle_rejects_symlink_and_extra_hardlink(self) -> None:
        relative = ".local/trusted-oracles/v1"
        oracle = self.configured_oracle(relative)
        reference = self.stage(oracle_root=relative)
        oracle.parent.chmod(0o755)
        held = oracle.with_name("held.py")
        oracle.rename(held)
        oracle.symlink_to(held)
        with self.assertRaises(ValueError):
            self.stage(oracle_root=relative)
        with self.assertRaises(ValueError):
            self.resolve(reference, oracle_root=relative)
        oracle.unlink()
        held.rename(oracle)
        oracle.parent.chmod(0o555)
        os.link(oracle, self.root / "extra-oracle-link")
        with self.assertRaises(ValueError):
            self.stage(oracle_root=relative)
        with self.assertRaises(ValueError):
            self.resolve(reference, oracle_root=relative)

    def test_inputs_accept_exact_byte_boundaries(self) -> None:
        reference = self.stage(request={"x": "a" * 4088}, production_patch="p" * 4096, instrumentation_patch="\u00e9" * 2048)
        task = self.task(reference)
        self.assertEqual(sum((task / name).stat().st_size for name in ("request.json", "production.patch", "instrumentation.patch")), 12288)
        self.resolve(reference)

    def test_each_patch_accepts_eight_kib_of_utf8_bytes_without_raising_total_budget(self) -> None:
        for patch in ("p" * 8192, "\u00e9" * 4096):
            with self.subTest(characters=len(patch)):
                reference = self.stage(request={"x": ""}, production_patch=patch,
                    instrumentation_patch="i" * 4088)
                task = self.task(reference)
                self.assertEqual((task / "production.patch").read_bytes(), patch.encode("utf-8"))
                self.assertEqual(sum((task / name).stat().st_size for name in
                    ("request.json", "production.patch", "instrumentation.patch")), 12288)
                self.resolve(reference)

    def test_over_budget_inputs_fail_before_task_writes(self) -> None:
        for overrides in ({"request": {"x": "a" * 4089}}, {"production_patch": "p" * 8193},
                          {"instrumentation_patch": "\u00e9" * 4097},
                          {"request": {"x": "a" * 4088}, "production_patch": "p" * 8192,
                           "instrumentation_patch": "i"}):
            with self.subTest(overrides=list(overrides)), self.assertRaises(ValueError):
                self.stage(**overrides)
        self.assertFalse((self.root / ".local/task-artifacts").exists())

    def test_nonfinite_and_non_json_requests_fail_before_writes(self) -> None:
        for value in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.stage(request={"nested": [value]})
        for request in ([], {1: "not a JSON key"}, {"tuple": (1, 2)}):
            with self.subTest(request=request), self.assertRaises(ValueError):
                self.stage(request=request)
        self.assertFalse((self.root / ".local/task-artifacts").exists())

    def test_invalid_patch_text_fails_before_writes(self) -> None:
        for text in ("", "abc\0def", b"bytes", "\ud800"):
            with self.subTest(text=repr(text)), self.assertRaises(ValueError):
                self.stage(production_patch=text)
        self.assertFalse((self.root / ".local/task-artifacts").exists())

    def test_foreign_snapshot_is_rejected_by_real_admission(self) -> None:
        foreign = copy.deepcopy(self.snapshot_ref)
        foreign["snapshot"]["contentId"] = "sha256:" + "0" * 64
        with self.assertRaises(target_admission.TargetBlocked):
            task_artifacts.stage_task(repo_root=self.root, snapshot_ref=foreign, **self.inputs)
        reference = self.stage()
        with self.assertRaises(target_admission.TargetBlocked):
            self.resolve(reference, snapshot_ref=foreign)

    def test_actual_snapshot_mutation_blocks_resolve(self) -> None:
        reference = self.stage()
        module = self.snapshot / "Module.bsl"
        module.chmod(0o644)
        module.write_bytes(b"// actual changed admitted source\n")
        module.chmod(0o444)
        with self.assertRaises(target_admission.TargetBlocked):
            self.resolve(reference)

    def test_handle_is_closed_and_uuid_is_canonical(self) -> None:
        reference = self.stage()
        variants = [
            {**reference, "receipt": "somewhere.py"},
            {**reference, "schemaVersion": True},
            {**reference, "taskId": "../outside"},
            {**reference, "taskId": reference["taskId"].upper()},
            {**reference, "taskId": "00000000-0000-1000-8000-000000000000"},
            {**reference, "manifestSha256": "0" * 63},
        ]
        for handle in variants:
            with self.subTest(handle=handle), self.assertRaises(ValueError):
                self.resolve(handle)

    def test_existing_uuid_directory_is_not_rewritten(self) -> None:
        reference = self.stage()
        before = target_admission.tree_manifest(self.task(reference))
        # Only entropy is fixed to exercise a real existing-directory collision.
        with mock.patch.object(task_artifacts.uuid, "uuid4", return_value=uuid.UUID(reference["taskId"])):
            with self.assertRaises(FileExistsError):
                self.stage(request={"different": True})
        self.assertEqual(target_admission.tree_manifest(self.task(reference)), before)

    def test_existing_receipt_refuses_reuse_without_writes(self) -> None:
        reference = self.stage()
        receipt = self.task(reference) / "receipt.json"
        receipt.write_bytes(b"existing native outcome")
        before = target_admission.tree_manifest(self.task(reference))
        with self.assertRaises(FileExistsError):
            self.resolve(reference)
        self.assertEqual(target_admission.tree_manifest(self.task(reference)), before)

    def test_real_input_tampering_is_rejected(self) -> None:
        for name in ("request.json", "production.patch", "instrumentation.patch"):
            with self.subTest(name=name):
                reference = self.stage()
                path = self.task(reference) / name
                self.overwrite(path, path.read_bytes() + b" ")
                with self.assertRaisesRegex(ValueError, "input identity"):
                    self.resolve(reference)

    def test_manifest_tampering_is_rejected(self) -> None:
        reference = self.stage()
        path = self.task(reference) / "task.json"
        self.overwrite(path, path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "manifest identity"):
            self.resolve(reference)

    def test_rehashed_manifest_cannot_change_snapshot_binding(self) -> None:
        reference = self.stage()
        def mutate(data):
            data["snapshotRef"]["snapshot"]["contentId"] = "sha256:" + "0" * 64
        forged = self.rewrite_manifest(reference, mutate)
        with self.assertRaisesRegex(ValueError, "task binding"):
            self.resolve(forged)

    def test_rehashed_manifest_cannot_promote_staged_data_to_oracle(self) -> None:
        reference = self.stage(production_patch="raise RuntimeError('untrusted staged Python')\n")
        staged = self.task(reference) / "production.patch"
        def mutate(data):
            data["oracle"] = {"root": ".", "path": staged.relative_to(self.root).as_posix(), "sha256": hashlib.sha256(staged.read_bytes()).hexdigest(), "bytes": staged.stat().st_size}
        forged = self.rewrite_manifest(reference, mutate)
        with self.assertRaisesRegex(ValueError, "operator-owned"):
            self.resolve(forged)

    def test_changed_real_oracle_is_rejected(self) -> None:
        reference = self.stage()
        self.oracle.chmod(0o644)
        self.oracle.write_bytes(b"raise RuntimeError('changed operator source')\n")
        self.oracle.chmod(0o444)
        with self.assertRaisesRegex(ValueError, "oracle identity"):
            self.resolve(reference)

    def test_writable_or_over_budget_oracle_is_rejected(self) -> None:
        self.oracle.chmod(0o644)
        with self.assertRaises(ValueError):
            self.stage()
        self.oracle.write_bytes(b"x" * 65537)
        self.oracle.chmod(0o444)
        with self.assertRaises(ValueError):
            self.stage()
        self.assertFalse((self.root / ".local/task-artifacts").exists())

    def test_oracle_locator_cannot_select_paths_or_other_python(self) -> None:
        other = self.oracle.with_name("other.py")
        other.write_bytes(self.oracle.read_bytes())
        other.chmod(0o444)
        rogue = self.root / ".local/rogue/oracle.py"
        rogue.parent.mkdir()
        rogue.write_bytes(self.oracle.read_bytes())
        rogue.chmod(0o444)
        for locator in (str(self.oracle), "experiments/../oracle.py", "experiments/sample/../sample/oracle.py", "experiments/sample/other.py", "experiments\\sample\\oracle.py", ".local/rogue/oracle.py"):
            with self.subTest(locator=locator), self.assertRaises(ValueError):
                self.stage(oracle=locator)
        self.assertFalse((self.root / ".local/task-artifacts").exists())

    def test_symlink_namespace_cannot_write_outside(self) -> None:
        external = self.root / "external"
        external.mkdir()
        sentinel = external / "sentinel"
        sentinel.write_bytes(b"preserve")
        (self.root / ".local/task-artifacts").symlink_to(external, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.stage()
        self.assertEqual({p.name for p in external.iterdir()}, {"sentinel"})
        self.assertEqual(sentinel.read_bytes(), b"preserve")

    def test_symlink_task_and_input_are_rejected(self) -> None:
        reference = self.stage()
        task = self.task(reference)
        moved = task.with_name("held")
        task.rename(moved)
        task.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.resolve(reference)
        task.unlink()
        moved.rename(task)
        (task / "request.json").unlink()
        (task / "request.json").symlink_to(self.oracle)
        with self.assertRaises(ValueError):
            self.resolve(reference)

    def test_symlink_or_hardlinked_oracle_is_rejected(self) -> None:
        for kind in ("symlink", "hardlink"):
            with self.subTest(kind=kind):
                other = self.root / "experiments" / kind
                other.mkdir()
                link = other / "oracle.py"
                if kind == "symlink":
                    link.symlink_to(self.oracle)
                else:
                    os.link(self.oracle, link)
                try:
                    with self.assertRaises(ValueError):
                        self.stage(oracle=link.relative_to(self.root).as_posix())
                finally:
                    link.unlink()

    def test_hardlinked_artifact_and_unknown_file_are_rejected(self) -> None:
        reference = self.stage()
        task = self.task(reference)
        external = self.root / "request-link"
        os.link(task / "request.json", external)
        with self.assertRaises(ValueError):
            self.resolve(reference)
        external.unlink()
        (task / "unexpected.py").write_bytes(b"unowned input")
        with self.assertRaisesRegex(ValueError, "file set"):
            self.resolve(reference)

    def test_manifest_is_closed_even_with_recalculated_checksum(self) -> None:
        reference = self.stage()
        forged = self.rewrite_manifest(reference, lambda data: data.update({"callerFilename": "evil.py"}))
        with self.assertRaisesRegex(ValueError, "task binding"):
            self.resolve(forged)

    def test_writable_staged_file_is_rejected_even_if_bytes_match(self) -> None:
        reference = self.stage()
        (self.task(reference) / "production.patch").chmod(0o600)
        with self.assertRaises(ValueError):
            self.resolve(reference)

    def test_rehashed_manifest_does_not_coerce_boolean_byte_count(self) -> None:
        reference = self.stage(production_patch="x")
        def mutate(data):
            data["inputs"]["productionPatch"]["bytes"] = True
        forged = self.rewrite_manifest(reference, mutate)
        with self.assertRaisesRegex(ValueError, "input identity"):
            self.resolve(forged)

    def test_existing_namespace_file_is_not_modified(self) -> None:
        namespace = self.root / ".local/task-artifacts"
        namespace.write_bytes(b"preexisting foreign data")
        with self.assertRaises(FileExistsError):
            self.stage()
        self.assertEqual(namespace.read_bytes(), b"preexisting foreign data")


if __name__ == "__main__":
    unittest.main()
