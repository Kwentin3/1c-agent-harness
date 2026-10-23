from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "snapshot_search.py"
from one_c_harness import target_admission
from one_c_harness import snapshot_search


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def create_target(root: Path, *, module_text: str | None = None) -> tuple[Path, Path, Path]:
    snapshot = root / ".local/targets/sample/snapshot"
    files = {
        "Configuration.xml": (
            "<MetaDataObject><Configuration><Properties>"
            "<Name>Sample</Name><Version>2.0</Version>"
            "</Properties></Configuration></MetaDataObject>"
        ),
        "Documents/SalesInvoice.xml": "<Attribute><Name>PaymentDueDate</Name></Attribute>",
        "Documents/SalesInvoice/Ext/ObjectModule.bsl": (
            "Procedure Posting(Cancel)\nEndProcedure\n" if module_text is None else module_text
        ),
        "Documents/SalesInvoice/Templates/PrintData/Ext/Template.xml": (
            "<field><dataPath>PaymentDueDate</dataPath></field>"
        ),
    }
    for relative, text in files.items():
        path = snapshot / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
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
                "fragmentTruncated": False,
                "line": 1,
                "lineEnding": "\n",
                "path": "Documents/SalesInvoice/Ext/ObjectModule.bsl",
                "utf8Bom": False,
            }])
            self.assertEqual(
                [(item["path"], item["line"]) for item in json.loads(xml.stdout)["results"]],
                [
                    ("Documents/SalesInvoice.xml", 1),
                    ("Documents/SalesInvoice/Templates/PrintData/Ext/Template.xml", 1),
                ],
            )
            self.assertEqual(before, (target_admission.tree_manifest(snapshot), manifest.read_bytes()))

    def test_bom_crlf_whitespace_and_unterminated_eof_round_trip_without_source_changes(self) -> None:
        source = "\ufeffProcedure Posting(Cancel)\r\n\tValue = 1;  \t\r\n\t\r\nEndProcedure\r\n// EOF  "
        relative = "Documents/SalesInvoice/Ext/ObjectModule.bsl"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot, manifest, ref = create_target(root, module_text=source)
            before = (target_admission.tree_manifest(snapshot), manifest.read_bytes())

            completed = run_search(root, ref, "^", "--mode", "regex", "--path-prefix", relative)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            hits = payload["results"]
            self.assertFalse(payload["truncated"])
            self.assertEqual([hit["line"] for hit in hits], [1, 2, 3, 4, 5])
            self.assertEqual([hit["path"] for hit in hits], [relative] * 5)
            self.assertEqual([hit["lineEnding"] for hit in hits], ["\r\n"] * 4 + [""])
            self.assertTrue(all(hit["utf8Bom"] for hit in hits))
            self.assertTrue(all(not hit["fragmentTruncated"] for hit in hits))
            self.assertEqual(hits[2]["fragment"], "\t")
            reconstructed = "".join(hit["fragment"] + hit["lineEnding"] for hit in hits).encode("utf-8")
            self.assertEqual(reconstructed, source.encode("utf-8"))
            self.assertEqual(before, (target_admission.tree_manifest(snapshot), manifest.read_bytes()))

    def test_all_splitlines_separators_keep_line_numbers_and_do_not_enter_query_matching(self) -> None:
        separators = ["\r\n", "\n", "\r", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"]
        bodies = [f"Line {number}" for number in range(1, len(separators) + 2)]
        source = "".join(body + ending for body, ending in zip(bodies, separators + [""]))
        relative = "Documents/SalesInvoice/Ext/ObjectModule.bsl"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, _, ref = create_target(root, module_text=source)

            completed = run_search(root, ref, "^", "--mode", "regex", "--path-prefix", relative)
            ending_query = run_search(root, ref, r"[\r\n\v\f\x1c-\x1e\x85\u2028\u2029]", "--mode", "regex", "--path-prefix", relative)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            hits = json.loads(completed.stdout)["results"]
            self.assertEqual([hit["line"] for hit in hits], list(range(1, len(bodies) + 1)))
            self.assertEqual([hit["fragment"] for hit in hits], bodies)
            self.assertEqual([hit["lineEnding"] for hit in hits], separators + [""])
            self.assertTrue(all(not hit["utf8Bom"] for hit in hits))
            self.assertEqual(ending_query.returncode, 0, ending_query.stderr)
            self.assertEqual(json.loads(ending_query.stdout)["results"], [])

    def test_multibyte_fragments_preserve_body_and_mark_only_actual_byte_truncation(self) -> None:
        complete = "\t" + "\u754c" * 169 + "  \t "
        oversized = "\t" + "\u754c" * 170 + "  "
        bodies = [complete, oversized, "\tLiteral ellipsis \u2026  "]
        self.assertEqual(len(complete.encode("utf-8")), snapshot_search.MAX_FRAGMENT_BYTES)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, _, ref = create_target(root, module_text="\r\n".join(bodies))

            completed = run_search(root, ref, "^", "--mode", "regex", "--path-prefix", "Documents/SalesInvoice/Ext")

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            hits = payload["results"]
            self.assertFalse(payload["truncated"])
            self.assertEqual([hit["fragmentTruncated"] for hit in hits], [False, True, False])
            self.assertEqual(hits[0]["fragment"], complete)
            self.assertEqual(hits[1]["fragment"], "\t" + "\u754c" * 169 + "\u2026")
            self.assertEqual(hits[2]["fragment"], bodies[2])
            self.assertTrue(all(len(hit["fragment"].encode("utf-8")) <= snapshot_search.MAX_FRAGMENT_BYTES for hit in hits))

    def test_line_metadata_counts_toward_the_response_byte_budget(self) -> None:
        relative = "Documents/SalesInvoice/Ext/ObjectModule.bsl"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, _, ref = create_target(root, module_text="\ufeff\tPosting();  \t\r\n")
            args = ("--mode", "regex", "--path-prefix", relative)
            baseline = run_search(root, ref, "^", *args)
            self.assertEqual(baseline.returncode, 0, baseline.stderr)
            baseline_payload = json.loads(baseline.stdout)
            self.assertEqual(len(baseline_payload["results"]), 1)
            self.assertIn("fragmentTruncated", baseline_payload["results"][0])
            self.assertIn("lineEnding", baseline_payload["results"][0])
            self.assertIn("utf8Bom", baseline_payload["results"][0])
            maximum = len(baseline.stdout.encode("utf-8"))

            exact = run_search(root, ref, "^", *args, "--max-bytes", str(maximum))
            bounded = run_search(root, ref, "^", *args, "--max-bytes", str(maximum - 1))

            self.assertEqual(exact.returncode, 0, exact.stderr)
            self.assertEqual(exact.stdout, baseline.stdout)
            self.assertFalse(baseline_payload["truncated"])
            self.assertEqual(bounded.returncode, 0, bounded.stderr)
            self.assertLessEqual(len(bounded.stdout.encode("utf-8")), maximum - 1)
            self.assertEqual(json.loads(bounded.stdout)["results"], [])
            self.assertTrue(json.loads(bounded.stdout)["truncated"])

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

    def test_search_uses_one_target_owned_snapshot_resolver(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, _, ref = create_target(root)
            resolved = target_admission.resolve_snapshot_ref(root, ref)

            with patch.object(snapshot_search, "resolve_snapshot_ref", return_value=resolved) as resolver:
                payload = snapshot_search.search(root, ref, "PaymentDueDate", "literal", None, 20, 32 * 1024)

            self.assertEqual(payload["status"], "ok")
            resolver.assert_called_once_with(root, ref)

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
                "fragmentTruncated": False,
                "line": 1,
                "lineEnding": "",
                "path": "Documents/SalesInvoice/Templates/PrintData/Ext/Template.xml",
                "utf8Bom": False,
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
