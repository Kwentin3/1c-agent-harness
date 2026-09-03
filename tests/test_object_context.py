from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "object_context.py"


def run_inspect(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "inspect", "--snapshot", str(root), *arguments],
        text=True,
        capture_output=True,
        check=False,
    )


def write_document_snapshot(root: Path, name: str = "GoodsReceipt") -> Path:
    (root / "Documents" / name / "Ext").mkdir(parents=True)
    (root / "Documents" / name / "Forms" / "DocumentForm" / "Ext" / "Form").mkdir(parents=True)
    (root / "Roles" / "Purchases" / "Ext").mkdir(parents=True)
    (root / "EventSubscriptions").mkdir(parents=True)
    (root / "Configuration.xml").write_text(
        f"<Configuration><Documents><Document>{name}</Document></Documents></Configuration>\n",
        encoding="utf-8",
    )
    (root / "Documents" / f"{name}.xml").write_text(
        f"""<MetaDataObject>
  <Document>
    <Properties>
      <Name>{name}</Name>
      <Attributes>
        <Attribute><Name>Warehouse</Name><Type>CatalogRef.Warehouses</Type></Attribute>
      </Attributes>
      <TabularSections>
        <TabularSection><Name>Goods</Name><Attributes><Attribute><Name>Product</Name><Type>CatalogRef.Products</Type></Attribute></Attributes></TabularSection>
      </TabularSections>
      <Forms><Form>DocumentForm</Form></Forms>
      <Templates><Template>PrintForm</Template></Templates>
    </Properties>
  </Document>
</MetaDataObject>
""",
        encoding="utf-8",
    )
    (root / "Documents" / name / "Ext" / "ObjectModule.bsl").write_text(
        """Procedure Posting(Cancel, PostingMode) Export
    Movements.Stock.Write = True;
EndProcedure

Function CurrentWarehouse() Export
    Return Warehouse;
EndFunction
""",
        encoding="utf-8",
    )
    (root / "Documents" / name / "Ext" / "ManagerModule.bsl").write_text(
        "Procedure Initialize()\nEndProcedure\n",
        encoding="utf-8",
    )
    (root / "Documents" / name / "Forms" / "DocumentForm" / "Ext" / "Form.xml").write_text(
        """<Form>
  <Events><Event name="OnOpen">OnOpen</Event></Events>
  <Items>
    <InputField><DataPath>Object.Warehouse</DataPath><Events><Event name="OnChange">WarehouseOnChange</Event></Events></InputField>
    <CommandBar><CommandName>Form.Command.Post</CommandName></CommandBar>
  </Items>
  <Command><Name>Post</Name><Action>Posting</Action></Command>
</Form>
""",
        encoding="utf-8",
    )
    (root / "Documents" / name / "Forms" / "DocumentForm" / "Ext" / "Form" / "Module.bsl").write_text(
        "Procedure OnOpen(Cancel)\nEndProcedure\nProcedure WarehouseOnChange(Item)\nEndProcedure\n",
        encoding="utf-8",
    )
    (root / "Roles" / "Purchases" / "Ext" / "Rights.xml").write_text(
        f"<Rights><name>Document.{name}</name></Rights>\n", encoding="utf-8"
    )
    (root / "EventSubscriptions" / "OnDocumentWrite.xml").write_text(
        f"<EventSubscription><Source>Document.{name}</Source></EventSubscription>\n", encoding="utf-8"
    )
    return root


class ObjectContextTests(unittest.TestCase):
    def test_document_inspection_is_stable_bounded_and_cited(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = write_document_snapshot(Path(temporary))
            before = {p.relative_to(snapshot): p.read_bytes() for p in snapshot.rglob("*") if p.is_file()}

            first = run_inspect(snapshot, "--object", "Document.GoodsReceipt")
            second = run_inspect(snapshot, "--object", "Document.GoodsReceipt")

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout, second.stdout)
            self.assertLessEqual(len(first.stdout.encode("utf-8")), 32 * 1024)
            payload = json.loads(first.stdout)
            self.assertEqual(payload["status"], "ready")
            self.assertEqual(payload["object"]["canonicalName"], "Document.GoodsReceipt")
            self.assertEqual([item["name"] for item in payload["metadata"]["attributes"]], ["Warehouse"])
            self.assertEqual([item["name"] for item in payload["metadata"]["tabularSections"]], ["Goods"])
            self.assertEqual(
                [item["name"] for item in payload["bsl"]["outline"]],
                ["CurrentWarehouse", "Initialize", "OnOpen", "Posting", "WarehouseOnChange"],
            )
            self.assertEqual(
                [item["value"] for item in payload["forms"][0]["dataPaths"]],
                ["Object.Warehouse"],
            )
            kinds = {item["kind"] for item in payload["relations"]["confirmed"]}
            self.assertEqual(kinds, {"configuration", "eventSubscription", "role"})
            for section in (payload["metadata"]["attributes"], payload["bsl"]["outline"], payload["relations"]["confirmed"]):
                for item in section:
                    self.assertIn("locator", item)
                    self.assertIn("path", item["locator"])
                    self.assertIn("startLine", item["locator"])
            after = {p.relative_to(snapshot): p.read_bytes() for p in snapshot.rglob("*") if p.is_file()}
            self.assertEqual(before, after)

    def test_invalid_missing_and_unsupported_inputs_have_distinct_states(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = write_document_snapshot(Path(temporary))
            invalid = run_inspect(snapshot, "--object", "GoodsReceipt")
            missing = run_inspect(snapshot, "--object", "Document.Missing")
            unsupported = run_inspect(snapshot, "--object", "Catalog.Goods")
            absent_snapshot = run_inspect(snapshot / "absent", "--object", "Document.GoodsReceipt")

            self.assertEqual((invalid.returncode, json.loads(invalid.stdout)["reasonCode"]), (2, "invalid_object"))
            self.assertEqual((missing.returncode, json.loads(missing.stdout)["reasonCode"]), (2, "object_not_found"))
            self.assertEqual((unsupported.returncode, json.loads(unsupported.stdout)["status"]), (0, "unsupported"))
            self.assertEqual((absent_snapshot.returncode, json.loads(absent_snapshot.stdout)["reasonCode"]), (2, "snapshot_unavailable"))

    def test_limits_mark_truncation_without_hiding_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = write_document_snapshot(Path(temporary))
            result = run_inspect(snapshot, "--object", "Document.GoodsReceipt", "--limit", "1")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["truncated"])
            self.assertLessEqual(len(payload["bsl"]["outline"]), 1)
            self.assertTrue(payload["diagnostics"])

    def test_focus_terms_are_stable_and_only_filter_lexical_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = write_document_snapshot(Path(temporary))

            result = run_inspect(
                snapshot, "--object", "Document.GoodsReceipt", "--focus", "Stock", "--focus", "Stock"
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["focusTerms"], ["Stock"])
            self.assertEqual([item["name"] for item in payload["metadata"]["attributes"]], ["Warehouse"])


if __name__ == "__main__":
    unittest.main()
