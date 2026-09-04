from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "snapshot_search.py"
sys.path.insert(0, str(ROOT / "scripts"))

import target_admission
import snapshot_search


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def create_target(root: Path) -> tuple[Path, Path, Path]:
    snapshot = root / ".local/targets/sample/snapshot"
    files = {
        "Configuration.xml": (
            "<MetaDataObject><Configuration><Properties>"
            "<Name>Sample</Name><Version>2.0</Version>"
            "</Properties></Configuration></MetaDataObject>"
        ),
        "Documents/SalesInvoice.xml": "<Attribute><Name>PaymentDueDate</Name></Attribute>",
        "Documents/SalesInvoice/Ext/ObjectModule.bsl": "Procedure Posting(Cancel)\nEndProcedure\n",
        "Documents/SalesInvoice/Templates/PrintData/Ext/Template.xml": (
            "<field><dataPath>PaymentDueDate</dataPath></field>"
        ),
    }
    for relative, text in files.items():
        path = snapshot / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    manifest = target_admission.tree_manifest(snapshot)
    contract = {
        "schemaVersion": 2,
        "configuration": {"name": "Sample", "version": "2.0"},
        "source": {
            "kind": "hierarchical",
            "path": ".local/source/export",
            "contentId": f"sha256:{digest(manifest)}",
            "fileCount": 4,
        },
        "snapshot": {
            "root": ".local/targets/sample/snapshot",
            "manifest": ".local/targets/sample/snapshot.manifest",
            "contentId": f"sha256:{digest(manifest)}",
            "fileCount": 4,
        },
        "dailyNativeRoute": "scripts/shared_task_route.py run",
    }
    (root / "project-target.json").write_text(json.dumps(contract), encoding="utf-8")
    manifest_path = snapshot.parent / "snapshot.manifest"
    binding_path = snapshot.parent / "source.json"
    manifest_path.write_bytes(manifest)
    binding_path.write_bytes(target_admission.binding_bytes(contract))
    target_admission.freeze(snapshot, manifest_path, binding_path)
    ref = root / "snapshot-ref.json"
    ref.write_text(json.dumps(target_admission.snapshot_ref(contract, "reused")), encoding="utf-8")
    return snapshot, manifest_path, ref


def run_search(root: Path, ref: Path, query: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--repo-root",
            str(root),
            "--snapshot-ref",
            str(ref),
            "--query",
            query,
            *args,
        ],
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PATH": ""},
    )


class SnapshotSearchTests(unittest.TestCase):
    def test_search_without_system_rg_finds_bsl_and_xml_with_stable_paths_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot, manifest, ref = create_target(root)
            before = (target_admission.tree_manifest(snapshot), manifest.read_bytes())

            bsl = run_search(root, ref, r"Procedure\s+Posting", "--mode", "regex")
            xml = run_search(root, ref, "PaymentDueDate", "--mode", "literal")

            self.assertEqual(bsl.returncode, 0, bsl.stderr)
            self.assertEqual(xml.returncode, 0, xml.stderr)
            self.assertEqual(json.loads(bsl.stdout)["results"], [{
                "fragment": "Procedure Posting(Cancel)",
                "line": 1,
                "path": "Documents/SalesInvoice/Ext/ObjectModule.bsl",
            }])
            self.assertEqual(
                [(item["path"], item["line"]) for item in json.loads(xml.stdout)["results"]],
                [
                    ("Documents/SalesInvoice.xml", 1),
                    ("Documents/SalesInvoice/Templates/PrintData/Ext/Template.xml", 1),
                ],
            )
            self.assertEqual(before, (target_admission.tree_manifest(snapshot), manifest.read_bytes()))

    def test_result_is_byte_identical_deterministic_and_explicitly_truncated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, _, ref = create_target(root)

            first = run_search(root, ref, "PaymentDueDate", "--mode", "literal", "--limit", "1", "--max-bytes", "600")
            second = run_search(root, ref, "PaymentDueDate", "--mode", "literal", "--limit", "1", "--max-bytes", "600")

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout, second.stdout)
            self.assertLessEqual(len(first.stdout.encode("utf-8")), 600)
            payload = json.loads(first.stdout)
            self.assertTrue(payload["truncated"])
            self.assertEqual(len(payload["results"]), 1)

    def test_max_bytes_includes_the_final_stdout_newline(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, _, ref = create_target(root)

            baseline = run_search(root, ref, "PaymentDueDate", "--mode", "literal")
            self.assertEqual(baseline.returncode, 0, baseline.stderr)
            bounded = run_search(
                root,
                ref,
                "PaymentDueDate",
                "--mode",
                "literal",
                "--max-bytes",
                str(len(baseline.stdout.encode("utf-8")) - 1),
            )

            self.assertEqual(bounded.returncode, 0, bounded.stderr)
            self.assertLessEqual(
                len(bounded.stdout.encode("utf-8")),
                len(baseline.stdout.encode("utf-8")) - 1,
            )
            self.assertTrue(json.loads(bounded.stdout)["truncated"])

    def test_manifest_entry_read_or_decode_failure_is_not_silently_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary)
            with self.assertRaisesRegex(snapshot_search.SearchBlocked, "Snapshot content is unreadable"):
                list(snapshot_search._matching_lines(
                    snapshot,
                    {"Documents/Missing/Ext/ObjectModule.bsl": "sha256:unused"},
                    __import__("re").compile("Anything"),
                    None,
                ))

    def test_deadline_interrupts_a_slow_post_admission_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, _, ref = create_target(root)

            admitted = snapshot_search._admitted_snapshot(root, ref)

            def late_hits(*_args: object):
                time.sleep(0.03)
                if False:
                    yield {}

            with patch.object(snapshot_search, "SEARCH_DEADLINE_SECONDS", 0.01), patch.object(
                snapshot_search, "_admitted_snapshot", return_value=admitted
            ), patch.object(snapshot_search, "_matching_lines", late_hits):
                with self.assertRaisesRegex(snapshot_search.SearchBlocked, "deadline"):
                    snapshot_search.search(root, ref, "PaymentDueDate", "literal", None, 20, 32 * 1024)

    def test_path_prefix_limits_search_to_declared_subtree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, _, ref = create_target(root)

            completed = run_search(
                root,
                ref,
                "PaymentDueDate",
                "--mode",
                "literal",
                "--path-prefix",
                "Documents/SalesInvoice/Templates",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["results"], [{
                "fragment": "<field><dataPath>PaymentDueDate</dataPath></field>",
                "line": 1,
                "path": "Documents/SalesInvoice/Templates/PrintData/Ext/Template.xml",
            }])

    def test_regex_invalid_request_and_unadmitted_ref_fail_closed_without_paths_or_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, _, ref = create_target(root)

            invalid_regex = run_search(root, ref, "(", "--mode", "regex")
            escaped_path = run_search(root, ref, "Posting", "--path-prefix", "../outside")
            broken = json.loads(ref.read_text(encoding="utf-8"))
            broken["snapshot"]["root"] = ".local/targets/other/snapshot"
            ref.write_text(json.dumps(broken), encoding="utf-8")
            unadmitted = run_search(root, ref, "Posting")

            for completed, reason in ((invalid_regex, "invalid_request"), (escaped_path, "invalid_request"), (unadmitted, "snapshot_invalid")):
                self.assertEqual(completed.returncode, 1)
                payload = json.loads(completed.stdout)
                self.assertEqual(payload["status"], "blocked")
                self.assertEqual(payload["reasonCode"], reason)
                self.assertNotIn(str(root), completed.stdout)
                self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main()
