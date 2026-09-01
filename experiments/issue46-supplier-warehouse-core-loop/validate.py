#!/usr/bin/env python3
"""Fail-closed validator for the frozen Issue 46 evidence package."""
from __future__ import annotations
import argparse, base64, hashlib, json, os, subprocess, sys, uuid
from pathlib import Path

LANES = ("red", "green", "repeat")
IDS = ("runId", "deletedCaseId", "activeCaseId", "nonce")
REGS = ("Purchases", "InventoryInWarehouses", "SupplierBalance", "InventoryCost")
ROOT = Path(__file__).resolve().parent
FROZEN_CONTRACT = {
    "baseCommit": "6d69352e4f7bacf8c9578168990d7384b82e84d9",
    "baseTree": "23bd5c4a43c4b438835e8694f6007193ed15d7f1",
    "retainedPrepareSha256": "0bef9d0dda0cd8ea916c71a98fd1345a70ff817ca032df8091d17f2f23e95d53",
    "runnerPath": "scripts/native_cycle.py",
    "runnerSha256": "9afc9e99c6ae3bf853113605c2c4b3be8e049240c46256b196a45062e7678ad1",
    "snapshotFiles": 5099,
    "snapshotManifestSha256": "70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691",
    "sourceCfSha256": "5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a",
}
FROZEN_PRODUCTION_SHA256 = "4ebe30ff232822bd4a950b0d7ece25dad8c944c5e005dcc1b7e5a56759005343"
FROZEN_CHANGED = {
    "red": {"CommonModules/JetServerCall/Ext/Module.bsl":"9ec5730479541115b1075324ae623115903ce26a0dc2b1c1e1c39d3e16ad9711","Ext/ManagedApplicationModule.bsl":"2737c631ca9cf2c5569162f9fe155517eae02c3c4ed6f5bf4c431db3e581deb2"},
    "green": {"CommonModules/JetServerCall/Ext/Module.bsl":"9ec5730479541115b1075324ae623115903ce26a0dc2b1c1e1c39d3e16ad9711","Documents/SupplierInvoice/Ext/ObjectModule.bsl":"b1ecb83aae9911a0116a88ac2c34438be7ec01d4965ef9da556d51624263af70","Ext/ManagedApplicationModule.bsl":"3ed5639795728709c6ee8770f47d5c6680ba662efbd7a4de7d872262bdf7fca9"},
    "repeat": {"CommonModules/JetServerCall/Ext/Module.bsl":"9ec5730479541115b1075324ae623115903ce26a0dc2b1c1e1c39d3e16ad9711","Documents/SupplierInvoice/Ext/ObjectModule.bsl":"b1ecb83aae9911a0116a88ac2c34438be7ec01d4965ef9da556d51624263af70","Ext/ManagedApplicationModule.bsl":"7fa96a3ce267c01ebcfc58e7661631576d557795d506f375d503af988e092ac1"},
}
FROZEN_LANES = {
    "red": {
        "ids": ("8477ef5a-4ad5-4f0b-bd63-a96580ad2270", "eb67dee5-358d-49a7-8628-6a2ee095ed27", "397aeb50-1652-4466-90aa-9b9a160fe14e", "03d59cdf-a9af-460a-b731-af081d231dbd"),
        "token": "f2e9ec50-afb5-4c2a-9b8b-f39045def3fa", "instrumentation": "7952afb80fd5c5578b0be994d5bb46e754d6d134d44f3a238e3ba9d5fd01298d",
        "prepared": "4ca1f5bf73935b78b60f41bc393a4a1c3e5446f9f7de36659bd2587db392e62b", "runner": (5099, 4847, 61795952, "010d3082033ee761587ff70a5bad3517c5da374a307a8ef5f80435e0b772d6c3"), "duration": (71.082, 87.952),
    },
    "green": {
        "ids": ("55462446-a30a-4080-85cf-60ad91b081ac", "e0427a65-fb5d-45a5-a02d-2a17392dcd74", "4b0f1d06-c576-4147-ab00-60eec72d54d5", "04dd289c-b495-426c-bbcd-c05007d6f1b8"),
        "token": "8e81e0f7-7d46-4c43-ab4d-2d187a4fe3e5", "instrumentation": "97ecd7a9170d4df10a16bfbe8ad73fce4161df876dba54be81bb33086738b50b",
        "prepared": "1bbde5cb42a8e762d705d573b3e34f75c71431433b9532b8552953c30db08c7d", "runner": (5099, 4847, 61796026, "24b523dcd6d2d4293155bf0ea04e07c832d5d7b5abe1a744fe2543d7ae84f3c6"), "duration": (71.343, 89.107),
    },
    "repeat": {
        "ids": ("05b18edd-68a2-435d-848b-0a7ad62bc19e", "b2606d0e-107b-4150-9f1e-c8a6bb36ad4d", "8cfd52d9-b83b-48ac-ad39-aa4f6ef6ab6e", "327d42c4-d5fa-4348-97da-5e7299ae61c5"),
        "token": "d9f7aaef-d51c-4b6a-9be9-c9b4aa669922", "instrumentation": "4923aac9e5c1eb6c51015af24f5d95e2078a10cda8d79efb107939c18506e0cc",
        "prepared": "4b47585fb88b4ee653818c6298d59f032116b46181ad42fbf3836c1c1295a23e", "runner": (5099, 4847, 61796026, "b7c27bdb0ca3e1061aaf838bee0089ba0c14750fc3cb04b123f0fe9085b768f6"), "duration": (70.827, 86.715),
    },
}


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
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p != root/"manifest.json" and "__pycache__" not in p.parts}
    if actual != set(declared): fail(f"package closure mismatch: actual={sorted(actual)} declared={sorted(declared)}")
    for rel, digest in declared.items():
        if sha((root/rel).read_bytes()) != digest: fail(f"manifest hash mismatch: {rel}")
    return manifest

def git(root: Path, *args: str) -> str:
    return subprocess.run(["git",*args],cwd=root.parent.parent,check=True,text=True,stdout=subprocess.PIPE).stdout.strip()
def optional_git(root: Path, *args: str):
    result = subprocess.run(["git",*args],cwd=root.parent.parent,text=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    return result.stdout.strip() if result.returncode == 0 else None
def validate_shallow_pr_context(root: Path, contract: dict) -> None:
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request" or os.environ.get("GITHUB_REPOSITORY") != "Kwentin3/1c-agent-harness":
        fail("shallow validation requires trusted GitHub pull_request context")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path: fail("missing GitHub event path")
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    pull = event.get("pull_request", {})
    base_sha = pull.get("base", {}).get("sha")
    head_sha = pull.get("head", {}).get("sha")
    if pull.get("base", {}).get("ref") != "main" or base_sha != contract["baseCommit"]:
        fail("GitHub PR base identity mismatch")
    current = git(root,"rev-parse","HEAD")
    if current != head_sha:
        raw_commit = git(root,"cat-file","-p","HEAD")
        parents = [line.split()[1] for line in raw_commit.splitlines() if line.startswith("parent ")]
        if parents != [base_sha, head_sha]: fail("GitHub PR merge/head identity mismatch")

def validate(root: Path = ROOT, check_git: bool = True) -> dict:
    validate_manifest(root)
    evidence = json.loads((root/"evidence.json").read_text(encoding="utf-8"))
    instr = json.loads((root/"instrumentation.json").read_text(encoding="utf-8"))
    if evidence.get("schemaVersion") != 1 or instr.get("schemaVersion") != 1: fail("evidence schema")
    contract = evidence["contract"]
    if contract != FROZEN_CONTRACT: fail("frozen contract identity mismatch")
    if sha((root/"prepare.py").read_bytes()) != contract["retainedPrepareSha256"]: fail("retained replay implementation mismatch")
    if check_git:
        shallow = git(root,"rev-parse","--is-shallow-repository") == "true"
        origin_main = optional_git(root,"rev-parse","--verify","origin/main")
        base_tree = optional_git(root,"rev-parse",f'{contract["baseCommit"]}^{{tree}}')
        if shallow and (origin_main is None or base_tree is None): validate_shallow_pr_context(root, contract)
        if origin_main is None and not shallow: fail("missing origin/main in full clone")
        if origin_main is not None and origin_main != contract["baseCommit"]: fail("foreign/stale origin/main")
        if base_tree is None and not shallow: fail("missing base object in full clone")
        if base_tree is not None and base_tree != contract["baseTree"]: fail("base tree mismatch")
        runner = root.parent.parent/contract["runnerPath"]
        if sha(runner.read_bytes()) != contract["runnerSha256"]: fail("runner hash mismatch")
    production = (root/"production.patch").read_bytes()
    if sha(production) != FROZEN_PRODUCTION_SHA256 or evidence["productionPatchSha256"] != FROZEN_PRODUCTION_SHA256: fail("production patch hash mismatch")
    if b"If Warehouse.DeletionMark Then" not in production or production.index(b"If Warehouse.DeletionMark Then") > production.index(b"PostingManagement.Initialize"): fail("production guard not earliest")
    lanes = evidence.get("lanes", {})
    if set(lanes) != set(LANES) or set(instr.get("lanes",{})) != set(LANES): fail("partial/foreign lane set")
    seen = {key:set() for key in IDS}; businesses = {}
    modes = {"red":False,"green":True,"repeat":True}
    for lane in LANES:
        item, request, binding = lanes[lane], lanes[lane]["request"], lanes[lane]["binding"]
        frozen = FROZEN_LANES[lane]
        if request.get("lane") != lane or request.get("production") is not modes[lane]: fail(f"{lane}: mode mismatch")
        expected_paths = ["CommonModules/JetServerCall/Ext/Module.bsl","Ext/ManagedApplicationModule.bsl"] + (["Documents/SupplierInvoice/Ext/ObjectModule.bsl"] if modes[lane] else [])
        if request.get("changedPaths") != expected_paths: fail(f"{lane}: changed-path closure")
        if binding.get("changedFileSha256") != FROZEN_CHANGED[lane]: fail(f"{lane}: changed-file replay binding")
        if request.get("treeIdentity") != binding.get("preparedContentSha256"): fail(f"{lane}: prepared identity mismatch")
        if binding.get("preparedContentSha256") != frozen["prepared"]: fail(f"{lane}: foreign prepared identity")
        ri = binding.get("runnerInput",{}); runner = item.get("runner",{})
        expected_ri = dict(zip(("files", "directories", "bytes", "sha256"), frozen["runner"]))
        if ri != expected_ri: fail(f"{lane}: foreign runner input")
        for key in ("sourceBefore","sourceAfter","inputAfter","copiedBeforeFreeze","frozenInput"):
            if runner.get(key) != ri: fail(f"{lane}: runner binding {key}")
        if runner.get("status") != "runtime_contract_completed" or not runner.get("runtime",{}).get("completed"): fail(f"{lane}: incomplete runner")
        if runner.get("durationSeconds",0) <= 0 or runner.get("totalDurationSeconds",0) < runner.get("durationSeconds",0): fail(f"{lane}: durations")
        if (runner.get("durationSeconds"), runner.get("totalDurationSeconds")) != frozen["duration"]: fail(f"{lane}: foreign duration evidence")
        if runner.get("storageCompaction",{}).get("status") != "completed" or runner["storageCompaction"].get("manualCleanupActions") != 0: fail(f"{lane}: cleanup")
        patch = base64.b64decode(instr["lanes"][lane]["base64"],validate=True)
        if sha(patch) != frozen["instrumentation"] or instr["lanes"][lane]["sha256"] != frozen["instrumentation"] or binding["instrumentationPatchSha256"] != frozen["instrumentation"]: fail(f"{lane}: instrumentation binding")
        if modes[lane] and binding.get("productionPatchSha256") != FROZEN_PRODUCTION_SHA256: fail(f"{lane}: production binding")
        if not modes[lane] and binding.get("productionPatchSha256") is not None: fail("red unexpectedly binds production")
        client, server = receipt(item["clientReceipt"],f"{lane}.client"), receipt(item["serverReceipt"],f"{lane}.server")
        for key in IDS:
            value = canonical_uuid(request.get(key),f"{lane}.{key}")
            if value in seen[key]: fail(f"{lane}: reused {key}")
            seen[key].add(value)
            if client.get(key) != value or server.get(key) != value: fail(f"{lane}: receipt identity")
        if tuple(request[key] for key in IDS) != frozen["ids"]: fail(f"{lane}: foreign request identity")
        token = canonical_uuid(client.get("responseToken"),f"{lane}.responseToken")
        if token != frozen["token"]: fail(f"{lane}: foreign response token")
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
