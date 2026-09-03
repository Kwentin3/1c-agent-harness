from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "object_context.py"
sys.path.insert(0, str(ROOT / "scripts"))

import object_context
import target_admission


def run_inspect(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    options = dict(zip(arguments[::2], arguments[1::2]))
    try:
        payload = object_context.inspect(
            root,
            str(options["--object"]),
            int(options.get("--limit") or object_context.DEFAULT_LIMIT),
            [value for flag, value in zip(arguments, arguments[1:]) if flag == "--focus"],
        )
    except object_context.InputBlocked as exc:
        return subprocess.CompletedProcess([], 2, object_context.encode(object_context.block(exc.reason_code, str(exc))), "")
    return subprocess.CompletedProcess([], 0, object_context.encode(payload), "")


def run_ref_inspect(repo: Path, snapshot_ref: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CLI),
            "inspect",
            "--repo-root",
            str(repo),
            "--snapshot-ref",
            str(snapshot_ref),
            *arguments,
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def write_document_snapshot(root: Path, name: str = "GoodsReceipt") -> Path:
    (root / "Documents" / name / "Ext").mkdir(parents=True)
    (root / "Documents" / name / "Forms" / "DocumentForm" / "Ext" / "Form").mkdir(parents=True)
    (root / "Documents" / name / "Commands" / "Print" / "Ext").mkdir(parents=True)
    (root / "Roles" / "Purchases" / "Ext").mkdir(parents=True)
    (root / "EventSubscriptions").mkdir(parents=True)
    (root / "Configuration.xml").write_text(
        f"<MetaDataObject><Configuration><ChildObjects><Document>{name}</Document></ChildObjects></Configuration></MetaDataObject>\n",
        encoding="utf-8",
    )
    (root / "Documents" / f"{name}.xml").write_text(
        f"""<MetaDataObject>
  <Document>
    <Properties>
      <Name>{name}</Name>
    </Properties>
    <ChildObjects>
      <Attribute><Name>Warehouse</Name><Type>CatalogRef.Warehouses</Type></Attribute>
      <TabularSection><Name>Goods</Name><Attributes><Attribute><Name>Product</Name><Type>CatalogRef.Products</Type></Attribute></Attributes></TabularSection>
      <Form><Name>DocumentForm</Name></Form>
      <Template><Name>PrintForm</Name></Template>
    </ChildObjects>
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
    (root / "Documents" / name / "Commands" / "Print" / "Ext" / "Command.xml").write_text(
        "<Command><Properties><Name>Print</Name></Properties></Command>\n", encoding="utf-8"
    )
    (root / "Roles" / "Purchases" / "Ext" / "Rights.xml").write_text(
        f"<Rights><object><name>Document.{name}</name></object></Rights>\n", encoding="utf-8"
    )
    (root / "EventSubscriptions" / "OnDocumentWrite.xml").write_text(
        f"<EventSubscription><Source>Document.{name}</Source></EventSubscription>\n", encoding="utf-8"
    )
    return root


def write_admitted_repository(root: Path) -> tuple[Path, Path]:
    snapshot = write_document_snapshot(root / ".local" / "targets" / "test" / "snapshot")
    (snapshot / "Configuration.xml").write_text(
        "<MetaDataObject><Configuration><Properties><Name>Test</Name><Version>1</Version></Properties>"
        "<ChildObjects><Document>GoodsReceipt</Document></ChildObjects></Configuration></MetaDataObject>\n",
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
    snapshot_ref = root / "snapshot-ref.json"
    snapshot_ref.write_text(json.dumps(target_admission.snapshot_ref(contract, "reused")), encoding="utf-8")
    return snapshot, snapshot_ref


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
                ["CurrentWarehouse", "Posting", "Initialize", "OnOpen", "WarehouseOnChange"],
            )
            self.assertEqual(
                [item["value"] for item in payload["forms"][0]["dataPaths"]],
                ["Object.Warehouse"],
            )
            kinds = {item["kind"] for item in payload["relations"]["confirmed"]}
            self.assertEqual(kinds, {"configuration", "eventSubscription", "role"})
            self.assertIn(
                {"kind": "command", "locator": {"path": "Documents/GoodsReceipt/Commands/Print/Ext/Command.xml", "startLine": 1, "endLine": 1}},
                payload["artifacts"],
            )
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

    def test_snapshot_ref_is_the_only_public_snapshot_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            _, snapshot_ref = write_admitted_repository(repo)

            result = run_ref_inspect(repo, snapshot_ref, "--object", "Document.GoodsReceipt")
            raw = subprocess.run(
                [sys.executable, str(CLI), "inspect", "--snapshot", str(repo), "--object", "Document.GoodsReceipt"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "ready")
            self.assertNotEqual(raw.returncode, 0)
            self.assertIn("required: --snapshot-ref", raw.stderr)

    def test_forged_snapshot_ref_is_blocked_before_context_read(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            _, snapshot_ref = write_admitted_repository(repo)
            forged = json.loads(snapshot_ref.read_text(encoding="utf-8"))
            forged["snapshot"]["root"] = ".local/elsewhere"
            snapshot_ref.write_text(json.dumps(forged), encoding="utf-8")

            result = run_ref_inspect(repo, snapshot_ref, "--object", "Document.GoodsReceipt")

            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["reasonCode"], "snapshot_ref_invalid")

    def test_russian_bsl_procedures_are_outlined(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = write_document_snapshot(Path(temporary))
            module = snapshot / "Documents" / "GoodsReceipt" / "Ext" / "ObjectModule.bsl"
            module.write_text("Процедура Проведение(Отказ, РежимПроведения) Экспорт\nКонецПроцедуры\n", encoding="utf-8")

            result = run_inspect(snapshot, "--object", "Document.GoodsReceipt")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertIn("Проведение", [item["name"] for item in payload["bsl"]["outline"]])

    def test_non_relational_xml_text_does_not_become_confirmed_relation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = write_document_snapshot(Path(temporary))
            (snapshot / "Roles" / "Purchases" / "Ext" / "Rights.xml").write_text(
                "<Rights><Comment>Document.GoodsReceipt</Comment></Rights>\n", encoding="utf-8"
            )

            result = run_inspect(snapshot, "--object", "Document.GoodsReceipt")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertNotIn("role", {item["kind"] for item in payload["relations"]["confirmed"]})

    def test_repeated_form_values_have_distinct_locators(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = write_document_snapshot(Path(temporary))
            form = snapshot / "Documents" / "GoodsReceipt" / "Forms" / "DocumentForm" / "Ext" / "Form.xml"
            form.write_text(
                "<Form><DataPath>Object.Warehouse</DataPath>\n<DataPath>Object.Warehouse</DataPath></Form>\n",
                encoding="utf-8",
            )

            result = run_inspect(snapshot, "--object", "Document.GoodsReceipt")

            self.assertEqual(result.returncode, 0, result.stderr)
            paths = json.loads(result.stdout)["forms"][0]["dataPaths"]
            self.assertEqual([item["locator"]["startLine"] for item in paths], [1, 2])


if __name__ == "__main__":
    unittest.main()
