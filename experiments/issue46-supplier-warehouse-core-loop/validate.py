#!/usr/bin/env python3
"""Fail-closed validator for the frozen Issue 46 evidence package."""
from __future__ import annotations
import argparse, base64, hashlib, json, subprocess, sys, uuid
from pathlib import Path

LANES = ("red", "green", "repeat")
IDS = ("runId", "deletedCaseId", "activeCaseId", "nonce")
REGS = ("Purchases", "InventoryInWarehouses", "SupplierBalance", "InventoryCost")
ROOT = Path(__file__).resolve().parent


def fail(message: str) -> None: raise ValueError(message)
def sha(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def canonical_uuid(value: object, label: str) -> str:
    if not isinstance(value, str): fail(f"{label}: not a string")
    try: parsed = uuid.UUID(value)
    except Exception as exc: raise ValueError(f"{label}: invalid UUID") from exc
    if parsed.version != 4 or str(parsed) != value: fail(f"{label}: not canonical UUIDv4")
    return value

def receipt(item: dict, label: str) -> dict[str, str]:
    raw = base64.b64decode(item["base64"], validate=True)
    if len(raw) != item["bytes"] or sha(raw) != item["sha256"]: fail(f"{label}: receipt byte/hash mismatch")
    rows = {}
    for line in raw.decode("utf-8-sig").splitlines():
        key, sep, value = line.partition("###")
        if not sep or not key or key in rows: fail(f"{label}: malformed/duplicate receipt row")
        rows[key] = value
    return rows

def movements(prefix: str, count: str, quantity="0", amount="0") -> dict[str, str]:
    out = {}
    for reg in REGS:
        out[f"{prefix}{reg}Count"] = count; out[f"{prefix}{reg}Quantity"] = "0"; out[f"{prefix}{reg}Amount"] = "0"
    if count == "1":
        out[f"{prefix}PurchasesQuantity"] = quantity; out[f"{prefix}PurchasesAmount"] = amount
        out[f"{prefix}InventoryInWarehousesQuantity"] = quantity
        out[f"{prefix}SupplierBalanceAmount"] = amount; out[f"{prefix}InventoryCostAmount"] = amount
    return out

def expected_business(production: bool) -> dict[str, str]:
    out = {"deletedWarehouseMarked":"Yes","deletedDraftSucceeded":"Yes","deletedDraftRefFilled":"Yes",
           "activeWarehouseMarked":"No","activePostingSucceeded":"Yes","activePostingErrorPresent":"No",
           "activePosted":"Yes","complete":"true"}
    out.update(movements("deletedBefore","0")); out.update(movements("activeBefore","0")); out.update(movements("activeAfter","1","2","20"))
    if production:
        out.update({"deletedPostingSucceeded":"No","deletedPostingErrorPresent":"Yes","deletedPosted":"No"}); out.update(movements("deletedAfter","0"))
    else:
        out.update({"deletedPostingSucceeded":"Yes","deletedPostingErrorPresent":"No","deletedPosted":"Yes"}); out.update(movements("deletedAfter","1","2","20"))
    return out

def validate_manifest(root: Path) -> dict:
    manifest = json.loads((root/"manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != 1: fail("manifest schema")
    declared = manifest.get("files")
    if not isinstance(declared, dict): fail("manifest files")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.name != "manifest.json" and "__pycache__" not in p.parts}
    if actual != set(declared): fail(f"package closure mismatch: actual={sorted(actual)} declared={sorted(declared)}")
    for rel, digest in declared.items():
        if sha((root/rel).read_bytes()) != digest: fail(f"manifest hash mismatch: {rel}")
    return manifest

def git(root: Path, *args: str) -> str:
    return subprocess.run(["git",*args],cwd=root.parent.parent,check=True,text=True,stdout=subprocess.PIPE).stdout.strip()

def validate(root: Path = ROOT, check_git: bool = True) -> dict:
    validate_manifest(root)
    evidence = json.loads((root/"evidence.json").read_text(encoding="utf-8"))
    instr = json.loads((root/"instrumentation.json").read_text(encoding="utf-8"))
    if evidence.get("schemaVersion") != 1 or instr.get("schemaVersion") != 1: fail("evidence schema")
    contract = evidence["contract"]
    if check_git:
        if git(root,"rev-parse","origin/main") != contract["baseCommit"]: fail("foreign/stale origin/main")
        if git(root,"rev-parse",f'{contract["baseCommit"]}^{{tree}}') != contract["baseTree"]: fail("base tree mismatch")
        runner = root.parent.parent/contract["runnerPath"]
        if sha(runner.read_bytes()) != contract["runnerSha256"]: fail("runner hash mismatch")
    production = (root/"production.patch").read_bytes()
    if sha(production) != evidence["productionPatchSha256"]: fail("production patch hash mismatch")
    if b"If Warehouse.DeletionMark Then" not in production or production.index(b"If Warehouse.DeletionMark Then") > production.index(b"PostingManagement.Initialize"): fail("production guard not earliest")
    lanes = evidence.get("lanes", {})
    if set(lanes) != set(LANES) or set(instr.get("lanes",{})) != set(LANES): fail("partial/foreign lane set")
    seen = {key:set() for key in IDS}; businesses = {}
    modes = {"red":False,"green":True,"repeat":True}
    for lane in LANES:
        item, request, binding = lanes[lane], lanes[lane]["request"], lanes[lane]["binding"]
        if request.get("lane") != lane or request.get("production") is not modes[lane]: fail(f"{lane}: mode mismatch")
        expected_paths = ["CommonModules/JetServerCall/Ext/Module.bsl","Ext/ManagedApplicationModule.bsl"] + (["Documents/SupplierInvoice/Ext/ObjectModule.bsl"] if modes[lane] else [])
        if request.get("changedPaths") != expected_paths: fail(f"{lane}: changed-path closure")
        if request.get("treeIdentity") != binding.get("preparedContentSha256"): fail(f"{lane}: prepared identity mismatch")
        ri = binding.get("runnerInput",{}); runner = item.get("runner",{})
        for key in ("sourceBefore","sourceAfter","inputAfter","copiedBeforeFreeze","frozenInput"):
            if runner.get(key) != ri: fail(f"{lane}: runner binding {key}")
        if runner.get("status") != "runtime_contract_completed" or not runner.get("runtime",{}).get("completed"): fail(f"{lane}: incomplete runner")
        if runner.get("durationSeconds",0) <= 0 or runner.get("totalDurationSeconds",0) < runner.get("durationSeconds",0): fail(f"{lane}: durations")
        if runner.get("storageCompaction",{}).get("status") != "completed" or runner["storageCompaction"].get("manualCleanupActions") != 0: fail(f"{lane}: cleanup")
        patch = base64.b64decode(instr["lanes"][lane]["base64"],validate=True)
        if sha(patch) != instr["lanes"][lane]["sha256"] or sha(patch) != binding["instrumentationPatchSha256"]: fail(f"{lane}: instrumentation binding")
        if modes[lane] and binding.get("productionPatchSha256") != sha(production): fail(f"{lane}: production binding")
        if not modes[lane] and binding.get("productionPatchSha256") is not None: fail("red unexpectedly binds production")
        client, server = receipt(item["clientReceipt"],f"{lane}.client"), receipt(item["serverReceipt"],f"{lane}.server")
        for key in IDS:
            value = canonical_uuid(request.get(key),f"{lane}.{key}")
            if value in seen[key]: fail(f"{lane}: reused {key}")
            seen[key].add(value)
            if client.get(key) != value or server.get(key) != value: fail(f"{lane}: receipt identity")
        token = canonical_uuid(client.get("responseToken"),f"{lane}.responseToken")
        if server.get("responseToken") != token or token == request["nonce"]: fail(f"{lane}: token binding")
        expected_client = {k:request[k] for k in IDS}|{"responseToken":token,"complete":"true"}
        if client != expected_client: fail(f"{lane}: client semantics")
        business = {k:v for k,v in server.items() if k not in IDS+("responseToken",)}
        if business != expected_business(modes[lane]) or item.get("business") != business: fail(f"{lane}: business semantics")
        businesses[lane] = business
    if businesses["green"] != businesses["repeat"]: fail("GREEN != clean repeat")
    return {"status":"PASS","lanes":list(LANES),"baseCommit":contract["baseCommit"]}

def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",type=Path,default=ROOT); ap.add_argument("--no-git",action="store_true"); args=ap.parse_args()
    try: print(json.dumps(validate(args.root.resolve(),not args.no_git),sort_keys=True))
    except Exception as exc: print(f"FAIL: {exc}",file=sys.stderr); raise SystemExit(1)
if __name__ == "__main__": main()
