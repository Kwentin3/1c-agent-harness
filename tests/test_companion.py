from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import companion
import target_admission


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _project(root: Path) -> None:
    source = root / ".local/source/export"
    source.mkdir(parents=True)
    (source / "Configuration.xml").write_text(
        "<MetaDataObject><Configuration><Properties><Name>Sample</Name><Version>2.0</Version>"
        "</Properties></Configuration></MetaDataObject>", encoding="utf-8",
    )
    module = source / "Documents/Order/Ext/ObjectModule.bsl"
    module.parent.mkdir(parents=True)
    module.write_text("Procedure Posting(Cancel)\nEndProcedure\n", encoding="utf-8")
    manifest = target_admission.tree_manifest(source)
    contract = {
        "schemaVersion": 2,
        "configuration": {"name": "Sample", "version": "2.0"},
        "source": {
            "kind": "hierarchical", "path": ".local/source/export",
            "contentId": f"sha256:{_digest(manifest)}", "fileCount": 2,
        },
        "snapshot": {
            "root": ".local/targets/sample/snapshot",
            "manifest": ".local/targets/sample/snapshot.manifest",
            "contentId": f"sha256:{_digest(manifest)}", "fileCount": 2,
        },
        "dailyNativeRoute": "scripts/shared_task_route.py run",
    }
    (root / "project-target.json").write_text(json.dumps(contract), encoding="utf-8")


def _request(operation: str, arguments: dict[str, object]) -> bytes:
    return json.dumps({"schemaVersion": 1, "operation": operation, "arguments": arguments}).encode("utf-8")


class CompanionContractTests(unittest.TestCase):
    def test_open_then_narrow_uses_only_snapshot_ref_in_a_business_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "business-project"
            project.mkdir()
            _project(project)

            opened = companion.execute(_request("open", {}), project)
            narrow = companion.execute(_request("narrow", {
                "snapshotRef": opened["snapshotRef"],
                "query": "Procedure Posting",
                "mode": "literal",
                "limit": 10,
                "maxBytes": 4096,
            }), project)

            self.assertEqual(opened["status"], "ok")
            self.assertEqual(opened["snapshotRef"]["status"], "ready")
            self.assertEqual(opened["capabilityVersion"], companion.CAPABILITY_VERSION)
            self.assertEqual(narrow["status"], "ok")
            self.assertEqual(narrow["results"], [{
                "fragment": "Procedure Posting(Cancel)",
                "line": 1,
                "path": "Documents/Order/Ext/ObjectModule.bsl",
            }])
            self.assertFalse((project / "scripts").exists())

    def test_narrow_rejects_raw_snapshot_path_instead_of_bypassing_admission(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            _project(project)
            response = companion.execute(_request("narrow", {
                "snapshotRef": {"path": ".local/source/export"},
                "query": "Posting",
            }), project)

            self.assertEqual(response["status"], "blocked")
            self.assertEqual(response["reasonCode"], "snapshot_invalid")
            self.assertNotIn(str(project), json.dumps(response))

    def test_verify_rejects_an_unadmitted_snapshot_before_native_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            _project(project)
            response = companion.execute(_request("verify", {
                "snapshotRef": {"path": ".local/source/export"},
                "request": "tasks/request.json",
                "productionPatch": "tasks/production.patch",
                "instrumentationPatch": "tasks/instrumentation.patch",
                "oracle": "tasks/oracle.py",
                "receipt": ".local/receipt.json",
                "timeoutSeconds": 480,
            }), project)

        self.assertEqual(response["status"], "blocked")
        self.assertEqual(response["reasonCode"], "snapshot_invalid")

    def test_open_preserves_the_canonical_target_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            _project(project)
            shutil.rmtree(project / ".local/source")
            response = companion.execute(_request("open", {}), project)

        self.assertEqual(response["status"], "blocked")
        self.assertEqual(response["reasonCode"], "source_missing")
        self.assertNotIn(temporary, json.dumps(response))

    def test_invalid_request_is_one_bounded_blocker_without_stacktrace(self) -> None:
        response = companion.execute(b"{", Path.cwd())

        self.assertEqual(response["status"], "blocked")
        self.assertEqual(response["reasonCode"], "invalid_request")
        self.assertNotIn("Traceback", json.dumps(response))


if __name__ == "__main__":
    unittest.main()
