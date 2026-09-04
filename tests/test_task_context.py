from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import task_context
import target_admission


def write_snapshot(root: Path, *, lexical_candidate: bool = False) -> Path:
    (root / "Documents" / "GoodsReceipt" / "Ext").mkdir(parents=True)
    (root / "Documents" / "GoodsReceipt" / "Forms" / "DocumentForm" / "Ext").mkdir(parents=True)
    (root / "Documents" / "GoodsReceipt.xml").write_text(
        """<MetaDataObject><Document><Properties><Name>GoodsReceipt</Name><PostingAllowed>true</PostingAllowed></Properties>
<ChildObjects><Attribute><Properties><Name>Warehouse</Name><Type><v8:Type xmlns:v8="urn:test">CatalogRef.Warehouses</v8:Type></Type></Properties></Attribute></ChildObjects>
</Document></MetaDataObject>\n""",
        encoding="utf-8",
    )
    (root / "Documents" / "BankPayment.xml").write_text(
        "<MetaDataObject><Document><Properties><Name>BankPayment</Name></Properties></Document></MetaDataObject>\n",
        encoding="utf-8",
    )
    (root / "Documents" / "GoodsReceipt" / "Ext" / "ObjectModule.bsl").write_text(
        """Procedure Posting(Cancel, Mode)
    If Warehouse.DeletionMark Then
        Cancel = True;
        Return;
    EndIf;
    RecordSetWrites();
EndProcedure

Procedure Fill()
EndProcedure
""" + ("Use(Document.Other);\n" if lexical_candidate else ""),
        encoding="utf-8",
    )
    (root / "Documents" / "GoodsReceipt" / "Forms" / "DocumentForm" / "Ext" / "Form.xml").write_text(
        "<Form><DataPath>Object.Warehouse</DataPath></Form>\n", encoding="utf-8"
    )
    return root


def admitted_repo(root: Path, *, lexical_candidate: bool = False) -> tuple[Path, Path]:
    snapshot = write_snapshot(root / ".local" / "targets" / "test" / "snapshot", lexical_candidate=lexical_candidate)
    (snapshot / "Configuration.xml").write_text(
        "<MetaDataObject><Configuration><Properties><Name>Test</Name><Version>1</Version></Properties></Configuration></MetaDataObject>\n",
        encoding="utf-8",
    )
    manifest = target_admission.tree_manifest(snapshot)
    contract = {
        "schemaVersion": 2,
        "configuration": {"name": "Test", "version": "1"},
        "source": {"kind": "hierarchical", "path": ".local/source", "contentId": "sha256:" + "0" * 64, "fileCount": 1},
        "snapshot": {
            "root": ".local/targets/test/snapshot",
            "manifest": ".local/targets/test/snapshot.manifest",
            "contentId": "sha256:" + hashlib.sha256(manifest).hexdigest(),
            "fileCount": len(target_admission.manifest_entries(manifest)),
        },
        "dailyNativeRoute": "scripts/shared_task_route.py run",
    }
    (root / "project-target.json").write_text(json.dumps(contract), encoding="utf-8")
    target = snapshot.parent
    manifest_path = target / "snapshot.manifest"
    binding = target / "source.json"
    manifest_path.write_bytes(manifest)
    binding.write_bytes(target_admission.binding_bytes(contract))
    target_admission.freeze(snapshot, manifest_path, binding)
    reference = root / "snapshot-ref.json"
    reference.write_text(json.dumps(target_admission.snapshot_ref(contract, "reused")), encoding="utf-8")
    return snapshot, reference


class TaskContextTests(unittest.TestCase):
    def test_document_seed_returns_structural_facts_and_minimal_bsl_fragment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = write_snapshot(Path(temporary))
            request = {
                "schemaVersion": 1,
                "focus": ["Warehouse", "Posting"],
                "seeds": [
                    {"kind": "metadata", "value": "Document.GoodsReceipt", "state": "candidate"},
                    {"kind": "term", "value": "Warehouse", "state": "candidate"},
                ],
                "limit": 8,
            }

            payload = task_context.collect(snapshot, request)

            self.assertEqual(payload["status"], "ready")
            self.assertEqual(payload["confirmed"]["entities"], [{"canonicalName": "Document.GoodsReceipt", "kind": "Document"}])
            attribute = payload["confirmed"]["metadata"]["attributes"][0]
            self.assertEqual(attribute["name"], "Warehouse")
            self.assertEqual(attribute["type"], "CatalogRef.Warehouses")
            self.assertEqual(attribute["state"], "confirmed")
            fragment = payload["fragments"][0]
            self.assertEqual(fragment["procedure"], "Posting")
            self.assertIn("Warehouse.DeletionMark", fragment["text"])
            self.assertNotIn("Procedure Fill", fragment["text"])
            self.assertEqual(payload["candidates"]["lexical"], [])
            self.assertFalse(payload["truncated"])
            self.assertEqual(task_context.encode(payload), task_context.encode(task_context.collect(snapshot, request)))

    def test_artifact_seed_stays_candidate_without_hidden_read(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = write_snapshot(Path(temporary))
            payload = task_context.collect(snapshot, {"schemaVersion": 1, "focus": ["Warehouse"], "seeds": [{"kind": "metadata", "value": "Document.GoodsReceipt", "state": "candidate"}, {"kind": "artifact", "value": "Documents/BankPayment.xml", "state": "candidate"}], "limit": 8})

            self.assertEqual(payload["candidates"]["artifacts"], [{"state": "candidate", "locator": {"path": "Documents/BankPayment.xml", "startLine": 1, "endLine": 1}}])
            self.assertNotIn("Documents/BankPayment.xml", [item["locator"]["path"] for item in payload["confirmed"]["artifacts"]])

    def test_public_cli_requires_snapshot_ref_and_preserves_lexical_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            snapshot, reference = admitted_repo(repo, lexical_candidate=True)
            request = repo / "request.json"
            request.write_text(json.dumps({"schemaVersion": 1, "focus": ["Warehouse"], "seeds": [{"kind": "metadata", "value": "Document.GoodsReceipt", "state": "candidate"}], "limit": 8}), encoding="utf-8")

            result = subprocess.run([sys.executable, str(ROOT / "scripts" / "task_context.py"), "collect", "--repo-root", str(repo), "--snapshot-ref", str(reference), "--request", str(request)], text=True, capture_output=True, check=False)
            raw = subprocess.run([sys.executable, str(ROOT / "scripts" / "task_context.py"), "collect", "--snapshot", str(snapshot), "--request", str(request)], text=True, capture_output=True, check=False)

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ready")
            self.assertIn("Document.Other", [item["target"] for item in payload["candidates"]["lexical"]])
            self.assertNotIn("relations", payload["confirmed"])
            self.assertNotEqual(raw.returncode, 0)
            self.assertIn("required: --snapshot-ref", raw.stderr)


if __name__ == "__main__":
    unittest.main()
