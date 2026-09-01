#!/usr/bin/env python3
"""Prepare one disposable Issue 46 native input tree."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import uuid
from pathlib import Path

SERVER_TEMPLATE = r'''

Function Issue46SupplierWarehouseProbe(ReceiptPath, RunId, DeletedCaseId, ActiveCaseId, Nonce) Export
	Writer = New TextWriter(ReceiptPath, TextEncoding.UTF8);
	ResponseToken = String(New UUID);
	Issue46WriteObservation(Writer, "runId", RunId);
	Issue46WriteObservation(Writer, "deletedCaseId", DeletedCaseId);
	Issue46WriteObservation(Writer, "activeCaseId", ActiveCaseId);
	Issue46WriteObservation(Writer, "nonce", Nonce);
	Issue46WriteObservation(Writer, "responseToken", ResponseToken);

	CurrencyObject = Catalogs.Currencies.CreateItem();
	CurrencyObject.Description = "Issue 46 currency";
	CurrencyObject.Write();

	SupplierObject = Catalogs.Counterparties.CreateItem();
	SupplierObject.Description = "Issue 46 supplier";
	SupplierObject.Supplier = True;
	SupplierObject.Write();

	UnitObject = Catalogs.Units.CreateItem();
	UnitObject.Description = "Issue 46 unit";
	UnitObject.Write();

	ProductObject = Catalogs.Products.CreateItem();
	ProductObject.Description = "Issue 46 product";
	ProductObject.ProductType = Enums.ProductTypes.Inventory;
	ProductObject.Unit = UnitObject.Ref;
	ProductObject.Write();

	DeletedWarehouseObject = Catalogs.Warehouses.CreateItem();
	DeletedWarehouseObject.Description = "Issue 46 deleted warehouse";
	DeletedWarehouseObject.Write();
	DeletedWarehouseObject.DeletionMark = True;
	DeletedWarehouseObject.Write();
	Issue46WriteObservation(Writer, "deletedWarehouseMarked", DeletedWarehouseObject.Ref.DeletionMark);

	DeletedDocument = Issue46NewSupplierInvoice(
		DeletedWarehouseObject.Ref, SupplierObject.Ref, CurrencyObject.Ref, ProductObject.Ref);
	DeletedDraftResult = Issue46TryWrite(DeletedDocument, False);
	Issue46WriteObservation(Writer, "deletedDraftSucceeded", DeletedDraftResult.Succeeded);
	Issue46WriteObservation(Writer, "deletedDraftRefFilled", ValueIsFilled(DeletedDocument.Ref));
	Issue46WriteMovements(Writer, "deletedBefore", DeletedDocument.Ref);
	DeletedPostingResult = Issue46TryWrite(DeletedDocument, True);
	Issue46WriteObservation(Writer, "deletedPostingSucceeded", DeletedPostingResult.Succeeded);
	Issue46WriteObservation(Writer, "deletedPostingErrorPresent", DeletedPostingResult.Error <> "");
	Issue46WriteObservation(Writer, "deletedPosted", DeletedDocument.Ref.Posted);
	Issue46WriteMovements(Writer, "deletedAfter", DeletedDocument.Ref);

	ActiveWarehouseObject = Catalogs.Warehouses.CreateItem();
	ActiveWarehouseObject.Description = "Issue 46 active warehouse";
	ActiveWarehouseObject.Write();
	Issue46WriteObservation(Writer, "activeWarehouseMarked", ActiveWarehouseObject.Ref.DeletionMark);

	ActiveDocument = Issue46NewSupplierInvoice(
		ActiveWarehouseObject.Ref, SupplierObject.Ref, CurrencyObject.Ref, ProductObject.Ref);
	Issue46WriteMovements(Writer, "activeBefore", ActiveDocument.Ref);
	ActivePostingResult = Issue46TryWrite(ActiveDocument, True);
	Issue46WriteObservation(Writer, "activePostingSucceeded", ActivePostingResult.Succeeded);
	Issue46WriteObservation(Writer, "activePostingErrorPresent", ActivePostingResult.Error <> "");
	Issue46WriteObservation(Writer, "activePosted", ActiveDocument.Ref.Posted);
	Issue46WriteMovements(Writer, "activeAfter", ActiveDocument.Ref);

	Issue46WriteObservation(Writer, "complete", "true");
	Writer.Close();
	Return ResponseToken;
EndFunction

Function Issue46NewSupplierInvoice(Warehouse, Supplier, Currency, Product)
	DocumentObject = Documents.SupplierInvoice.CreateDocument();
	DocumentObject.Date = CurrentDate();
	DocumentObject.Warehouse = Warehouse;
	DocumentObject.Supplier = Supplier;
	DocumentObject.Currency = Currency;
	DocumentObject.ExchangeRate = 1;
	DocumentObject.Multiplier = 1;
	Row = DocumentObject.Inventory.Add();
	Row.Product = Product;
	Row.Quantity = 2;
	Row.Price = 10;
	Row.Amount = 20;
	Row.VATAmount = 0;
	Row.Total = 20;
	Return DocumentObject;
EndFunction

Function Issue46TryWrite(DocumentObject, Posting)
	Result = New Structure("Succeeded,Error", True, "");
	Try
		If Posting Then
			DocumentObject.Write(DocumentWriteMode.Posting);
		Else
			DocumentObject.Write();
		EndIf;
	Except
		Result.Succeeded = False;
		Result.Error = ErrorDescription();
	EndTry;
	Return Result;
EndFunction

Procedure Issue46WriteMovements(Writer, Prefix, Recorder)
	Query = New Query;
	Query.Text =
	"SELECT ""Purchases"" AS RegisterName, COUNT(*) AS RowCount,
	|	ISNULL(SUM(Records.Quantity), 0) AS Quantity, ISNULL(SUM(Records.Amount), 0) AS Amount
	|FROM AccumulationRegister.Purchases AS Records WHERE Records.Recorder = &Recorder
	|UNION ALL
	|SELECT ""InventoryInWarehouses"", COUNT(*), ISNULL(SUM(Records.Quantity), 0), 0
	|FROM AccumulationRegister.InventoryInWarehouses AS Records WHERE Records.Recorder = &Recorder
	|UNION ALL
	|SELECT ""SupplierBalance"", COUNT(*), 0, ISNULL(SUM(Records.Amount), 0)
	|FROM AccumulationRegister.SupplierBalance AS Records WHERE Records.Recorder = &Recorder
	|UNION ALL
	|SELECT ""InventoryCost"", COUNT(*), 0, ISNULL(SUM(Records.Amount), 0)
	|FROM AccumulationRegister.InventoryCost AS Records WHERE Records.Recorder = &Recorder";
	Query.SetParameter("Recorder", Recorder);
	Selection = Query.Execute().Select();
	While Selection.Next() Do
		Issue46WriteObservation(Writer, Prefix + Selection.RegisterName + "Count", Selection.RowCount);
		Issue46WriteObservation(Writer, Prefix + Selection.RegisterName + "Quantity", Selection.Quantity);
		Issue46WriteObservation(Writer, Prefix + Selection.RegisterName + "Amount", Selection.Amount);
	EndDo;
EndProcedure

Procedure Issue46WriteObservation(Writer, Key, Value)
	Writer.Write(Key + "###" + String(Value) + Chars.LF);
EndProcedure
'''

CLIENT_TEMPLATE = r'''
	ClientWriter = New TextWriter(LaunchParameter, TextEncoding.UTF8);
	RunId = "@RUN_ID@";
	DeletedCaseId = "@DELETED_CASE_ID@";
	ActiveCaseId = "@ACTIVE_CASE_ID@";
	Nonce = "@NONCE@";
	Issue46WriteClientObservation(ClientWriter, "runId", RunId);
	Issue46WriteClientObservation(ClientWriter, "deletedCaseId", DeletedCaseId);
	Issue46WriteClientObservation(ClientWriter, "activeCaseId", ActiveCaseId);
	Issue46WriteClientObservation(ClientWriter, "nonce", Nonce);
	Try
		ResponseToken = JetServerCall.Issue46SupplierWarehouseProbe(
			LaunchParameter + ".server", RunId, DeletedCaseId, ActiveCaseId, Nonce);
		Issue46WriteClientObservation(ClientWriter, "responseToken", ResponseToken);
	Except
		Issue46WriteClientObservation(ClientWriter, "clientFailure", ErrorDescription());
	EndTry;
	Issue46WriteClientObservation(ClientWriter, "complete", "true");
	ClientWriter.Close();
	Return;

'''

CLIENT_HELPER = r'''

Procedure Issue46WriteClientObservation(Writer, Key, Value)
	Writer.Write(Key + "###" + String(Value) + Chars.LF);
EndProcedure
'''

PRODUCTION_BLOCK = '''\tIf Warehouse.DeletionMark Then
\t\tCancel = True;
\t\tReturn;
\tEndIf;
\t
'''


def read_source(path: Path) -> tuple[str, str, bool]:
    data = path.read_bytes()
    bom = data.startswith(b"\xef\xbb\xbf")
    text = data.decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in text else "\n"
    return text, newline, bom


def write_source(path: Path, text: str, newline: str, bom: bool) -> None:
    if newline == "\r\n":
        text = text.replace("\r\n", "\n").replace("\n", "\r\n")
    data = text.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    path.write_bytes(data)
    path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def inject(path: Path, anchor: str, block: str, *, last: bool = False) -> None:
    text, newline, bom = read_source(path)
    normalized = text.replace("\r\n", "\n")
    if normalized.count(anchor) != 1 and not last:
        raise RuntimeError(f"expected one anchor in {path}: {anchor!r}")
    index = normalized.rfind(anchor) if last else normalized.index(anchor)
    if index < 0:
        raise RuntimeError(f"anchor missing in {path}: {anchor!r}")
    normalized = normalized[:index] + block + normalized[index:]
    path.chmod(path.stat().st_mode | stat.S_IWUSR)
    write_source(path, normalized, newline, bom)


def inject_after(path: Path, anchor: str, block: str) -> None:
    text, newline, bom = read_source(path)
    normalized = text.replace("\r\n", "\n")
    if normalized.count(anchor) != 1:
        raise RuntimeError(f"expected one anchor in {path}: {anchor!r}")
    normalized = normalized.replace(anchor, anchor + block, 1)
    path.chmod(path.stat().st_mode | stat.S_IWUSR)
    write_source(path, normalized, newline, bom)


def audit_client_module(path: Path) -> dict[str, int]:
    text, _, _ = read_source(path)
    audit = {
        "onStartDeclarations": len(re.findall(r"(?im)^\s*Procedure\s+OnStart\s*\(\s*\)", text)),
        "procedureDeclarations": len(re.findall(r"(?im)^\s*Procedure\s+", text)),
        "procedureClosures": len(re.findall(r"(?im)^\s*EndProcedure\s*$", text)),
    }
    if audit["onStartDeclarations"] != 1:
        raise RuntimeError(f"generated client must contain one OnStart: {audit}")
    if audit["procedureDeclarations"] != audit["procedureClosures"]:
        raise RuntimeError(f"generated client procedure closure mismatch: {audit}")
    if text.count("JetServerCall.Issue46SupplierWarehouseProbe(") != 1:
        raise RuntimeError("generated client server-call closure mismatch")
    if len(re.findall(r"(?im)^\s*Procedure\s+Issue46WriteClientObservation\s*\(", text)) != 1:
        raise RuntimeError("generated client helper declaration mismatch")
    return audit


def audit_server_module(path: Path) -> dict[str, int]:
    text, _, _ = read_source(path)
    audit = {
        "functionDeclarations": len(re.findall(r"(?im)^\s*Function\s+", text)),
        "functionClosures": len(re.findall(r"(?im)^\s*EndFunction\s*$", text)),
        "procedureDeclarations": len(re.findall(r"(?im)^\s*Procedure\s+", text)),
        "procedureClosures": len(re.findall(r"(?im)^\s*EndProcedure\s*$", text)),
    }
    if audit["functionDeclarations"] != audit["functionClosures"]:
        raise RuntimeError(f"generated server function closure mismatch: {audit}")
    if audit["procedureDeclarations"] != audit["procedureClosures"]:
        raise RuntimeError(f"generated server procedure closure mismatch: {audit}")
    required = (
        "Issue46SupplierWarehouseProbe",
        "Issue46NewSupplierInvoice",
        "Issue46TryWrite",
        "Issue46WriteMovements",
        "Issue46WriteObservation",
    )
    for name in required:
        declarations = re.findall(rf"(?im)^\s*(?:Function|Procedure)\s+{name}\s*\(", text)
        if len(declarations) != 1:
            raise RuntimeError(f"generated server declaration mismatch for {name}")
    return audit


def audit_target_module(path: Path) -> dict[str, int | bool]:
    text, _, _ = read_source(path)
    posting_declarations = len(
        re.findall(r"(?im)^\s*Procedure\s+Posting\s*\(\s*Cancel\s*,\s*PostingMode\s*\)", text)
    )
    procedure_declarations = len(re.findall(r"(?im)^\s*Procedure\s+", text))
    procedure_closures = len(re.findall(r"(?im)^\s*EndProcedure\s*$", text))
    guard = text.find("If Warehouse.DeletionMark Then")
    preparation = text.find("PostingManagement.InitializeAdditionalPropertiesForPosting")
    audit: dict[str, int | bool] = {
        "postingDeclarations": posting_declarations,
        "procedureDeclarations": procedure_declarations,
        "procedureClosures": procedure_closures,
        "guardBeforePreparation": 0 <= guard < preparation,
    }
    if posting_declarations != 1 or procedure_declarations != procedure_closures:
        raise RuntimeError(f"generated target procedure closure mismatch: {audit}")
    if not audit["guardBeforePreparation"]:
        raise RuntimeError(f"generated target guard is not earliest: {audit}")
    return audit


def tree_identity(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix().encode()
        digest.update(relative + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def prepare(repo: Path, lane: str, production: bool) -> dict[str, object]:
    source = repo / ".local/runs/training-jet-review-final/snapshot"
    prepared_root = repo / ".local/prepared" / f"issue46-{lane}"
    tree = prepared_root / "input-tree"
    evidence = repo / ".local/issue46-fresh" / lane
    if prepared_root.exists():
        raise RuntimeError(f"prepared root already exists: {prepared_root}")
    evidence.mkdir(parents=True, exist_ok=False)
    shutil.copytree(source, tree, copy_function=shutil.copy2)
    identities = {
        "runId": str(uuid.uuid4()),
        "deletedCaseId": str(uuid.uuid4()),
        "activeCaseId": str(uuid.uuid4()),
        "nonce": str(uuid.uuid4()),
    }
    server = tree / "CommonModules/JetServerCall/Ext/Module.bsl"
    client = tree / "Ext/ManagedApplicationModule.bsl"
    target = tree / "Documents/SupplierInvoice/Ext/ObjectModule.bsl"
    inject(server, "\n#EndRegion", SERVER_TEMPLATE + "\n", last=True)
    client_block = CLIENT_TEMPLATE
    placeholders = {
        "runId": "@RUN_ID@",
        "deletedCaseId": "@DELETED_CASE_ID@",
        "activeCaseId": "@ACTIVE_CASE_ID@",
        "nonce": "@NONCE@",
    }
    for key, value in identities.items():
        client_block = client_block.replace(placeholders[key], value)
    inject_after(client, "Procedure OnStart()\n\t\n", client_block)
    inject(client, "\n#EndRegion", CLIENT_HELPER + "\n", last=True)
    if production:
        inject_after(target, "Procedure Posting(Cancel, PostingMode)\n\t\n", PRODUCTION_BLOCK)
    changed = [
        "CommonModules/JetServerCall/Ext/Module.bsl",
        "Ext/ManagedApplicationModule.bsl",
    ] + (["Documents/SupplierInvoice/Ext/ObjectModule.bsl"] if production else [])
    static_audit = {
        "client": audit_client_module(client),
        "server": audit_server_module(server),
    }
    if production:
        static_audit["target"] = audit_target_module(target)
    request = {
        "lane": lane,
        "production": production,
        **identities,
        "preparedTree": str(tree.relative_to(repo)),
        "treeIdentity": tree_identity(tree),
        "changedPaths": changed,
        "staticAudit": static_audit,
    }
    (evidence / "request.json").write_text(json.dumps(request, indent=2) + "\n")
    return request


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("lane")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--production", action="store_true")
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    print(json.dumps(prepare(repo, args.lane, args.production), indent=2))


if __name__ == "__main__":
    main()
