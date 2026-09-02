#!/usr/bin/env python3
"""Business oracle for SalesInvoice.PaymentDueDate."""
from __future__ import annotations
import argparse,json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

CASES=("P1","B1","P2","P3","P4","N1","N2","N3","N4","R1","R2")
POS=("P1","B1","P2","P3","P4","R1")
NEG=("N1","N2","N3","N4","R2")
MOV=("salesRows","customerRows","inventoryRows","costRows")
STATE=("inventoryQuantity","costQuantity","costAmount","salesRows","customerAmount")

def rows(data:bytes,typed:bool)->dict[str,tuple[str,str|None]]:
 out={}
 for raw in data.decode("utf-8-sig").splitlines():
  parts=raw.split("###")
  if typed and len(parts)==3: key,value,kind=parts
  elif len(parts)==2: key,value=parts; kind=None
  else: raise ValueError("malformed receipt")
  if key in out: raise ValueError("duplicate receipt key")
  out[key]=(value,kind)
 return out

def boolv(r,k):
 v,t=r[k];
 if t!="Boolean" or v not in ("true","false"): raise ValueError(f"wrong boolean {k}")
 return v=="true"
def num(r,k):
 v,t=r[k];
 if t!="Number": raise ValueError(f"wrong number {k}")
 return Decimal(v)
def datev(r,k):
 v,t=r[k]
 if t!="Date": raise ValueError(f"wrong date {k}")
 if not v: return datetime(1,1,1)
 try: return datetime.fromisoformat(v)
 except ValueError:
  import re
  m=re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{1,4}) (\d{1,2}):(\d{2}):(\d{2}) (AM|PM)',v)
  if not m: raise
  month,day,year,hour,minute,second=map(int,m.groups()[:6]); hour=hour%12+(12 if m.group(7)=="PM" else 0)
  return datetime(year,month,day,hour,minute,second)

def evaluate(request,client_bytes,server_bytes):
 c=rows(client_bytes,False); s=rows(server_bytes,True)
 for k in ("runId","caseId","nonce"):
  if c.get(k,(None,None))[0]!=request[k] or s.get(k,(None,None))[0]!=request[k]: raise ValueError(f"foreign {k}")
 token=c.get("responseToken",("",None))[0]
 if not token or token!=s.get("responseToken",("",None))[0] or token==request["nonce"]: raise ValueError("bad response token")
 if c.get("complete")!=("true",None) or s.get("complete")!=("true",None): raise ValueError("incomplete")
 if not boolv(s,"metadata.attributeExists") or s["metadata.name"][0]!="PaymentDueDate" or not boolv(s,"metadata.containsDate") or not boolv(s,"metadata.dateOnly"): raise ValueError("wrong metadata")
 for case in CASES:
  if not boolv(s,f"{case}.draftSucceeded"): raise ValueError(f"draft failed {case}")
  if datev(s,f"{case}.draftDueDate")!=datev(s,f"{case}.dueDateInput") or datev(s,f"{case}.postDueDate")!=datev(s,f"{case}.dueDateInput"): raise ValueError(f"date not persisted {case}")
 for case in POS:
  if not boolv(s,f"{case}.postedAfter") or any(num(s,f"{case}.movements.{x}")!=1 for x in MOV): raise ValueError(f"valid posting failed {case}")
 for case in NEG:
  if boolv(s,f"{case}.postedAfter") or any(num(s,f"{case}.movements.{x}")!=0 for x in MOV): raise ValueError(f"invalid posting moved {case}")
  if any(num(s,f"{case}.before.{x}")!=num(s,f"{case}.after.{x}") for x in STATE): raise ValueError(f"state changed {case}")
 for case in ("N1","N2","N3","N4"):
  if boolv(s,f"{case}.postCallSucceeded") or not s[f"{case}.postError"][0]: raise ValueError(f"message-boundary rejection missing {case}")
  if not datev(s,f"{case}.dueDateInput").date()<datev(s,f"{case}.documentDate").date(): raise ValueError(f"not earlier {case}")
 if datev(s,"B1.dueDateInput").date()!=datev(s,"B1.documentDate").date(): raise ValueError("same-day case wrong")
 if datev(s,"R1.dueDateInput").year!=1: raise ValueError("blank case wrong")
 return {"cases":11,"validPosted":6,"earlierRejected":4,"existingStockFailurePreserved":True,"movementRegisters":list(MOV)}

def main():
 p=argparse.ArgumentParser(); p.add_argument("--request",type=Path,required=True); p.add_argument("--client-receipt",type=Path,required=True); p.add_argument("--server-receipt",type=Path,required=True); a=p.parse_args()
 try: business=evaluate(json.loads(a.request.read_text()),a.client_receipt.read_bytes(),a.server_receipt.read_bytes())
 except Exception as e: print(f"FAIL: {e}",file=__import__('sys').stderr); return 1
 print(json.dumps({"status":"PASS","task":"sales-invoice-payment-due-date","businessPayload":business},sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
