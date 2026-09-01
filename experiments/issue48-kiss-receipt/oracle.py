#!/usr/bin/env python3
from __future__ import annotations
import base64, importlib.util, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location("provenance_receipt",ROOT/"scripts/managed_probe_prepare.py")
assert SPEC and SPEC.loader
N=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(N)
IDS=("runId","deletedCaseId","activeCaseId","nonce","responseToken")
REGS=("Purchases","InventoryInWarehouses","SupplierBalance","InventoryCost")

def expected() -> dict[str,str]:
    out={"deletedWarehouseMarked":"Yes","deletedDraftSucceeded":"Yes","deletedDraftRefFilled":"Yes",
         "deletedPostingSucceeded":"No","deletedPostingErrorPresent":"Yes","deletedPosted":"No",
         "activeWarehouseMarked":"No","activePostingSucceeded":"Yes","activePostingErrorPresent":"No",
         "activePosted":"Yes","complete":"true"}
    for prefix in ("deletedBefore","deletedAfter","activeBefore"):
        for reg in REGS:
            out[f"{prefix}{reg}Count"]="0"; out[f"{prefix}{reg}Quantity"]="0"; out[f"{prefix}{reg}Amount"]="0"
    for reg in REGS:
        out[f"activeAfter{reg}Count"]="1"; out[f"activeAfter{reg}Quantity"]="0"; out[f"activeAfter{reg}Amount"]="0"
    out.update({"activeAfterPurchasesQuantity":"2","activeAfterPurchasesAmount":"20",
                "activeAfterInventoryInWarehousesQuantity":"2","activeAfterSupplierBalanceAmount":"20",
                "activeAfterInventoryCostAmount":"20"})
    return out

def validate(receipt: dict[str,object]) -> None:
    N.validate_provenance_receipt(receipt)
    raw=base64.b64decode(receipt["business"]["rawReceipt"]["base64"],validate=True).decode("utf-8-sig")
    rows={}
    for line in raw.splitlines():
        key,sep,value=line.partition("###")
        if not sep or not key or key in rows: raise ValueError("malformed/duplicate business row")
        rows[key]=value
    request=receipt["request"]["payload"]
    for key in IDS[:-1]:
        if rows.get(key)!=request.get(key): raise ValueError(f"foreign {key}")
    payload={key:value for key,value in rows.items() if key not in IDS}
    if payload!=receipt["business"]["payload"] or payload!=expected(): raise ValueError("wrong business payload")
    if rows["responseToken"]==request["nonce"]: raise ValueError("response token echoes nonce")

def main() -> None:
    receipt=json.loads((Path(__file__).with_name("receipt.json")).read_text(encoding="utf-8"))
    validate(receipt)
    print(json.dumps({"status":"PASS","task":"issue46-green-on-standard-receipt"},sort_keys=True))

if __name__=="__main__":
    try: main()
    except Exception as exc:
        print(f"FAIL: {exc}",file=sys.stderr); raise SystemExit(1)
