#!/usr/bin/env python3
"""DRAFT business oracle: fixed expectations, actual persisted observations only.

Not executed/admitted. Four proposal vectors plus proposed exempt preservation E.
Receipt parser/typed readers are literal reuse of the existing issue53 oracle.
"""
from __future__ import annotations
import argparse,json
from decimal import Decimal
from pathlib import Path

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

# Independent fixed expected values; never read expected results from request/probe.
EXPECTED={
 'A':('39.20',(('3','7','20','21','4.20','25.20'),('2','4','0','8','0','8'),('1','5','20','5','1','6'))),
 'B':('0',(('0','99','20','0','0','0'),)),
 'C':('0',()),
 'D':('12',(('1.5','8','0','12','0','12'),)),
 'E':('42',(('6','7','20','42','0','42'),)),
}
FIELDS=('quantity','price','vatRate','amount','vatAmount','total')

def evaluate(request,client_bytes,server_bytes):
 c=rows(client_bytes,False);s=rows(server_bytes,True)
 for k in ('runId','caseId','nonce'):
  if not isinstance(request[k],str) or not request[k] or c.get(k,(None,None))[0]!=request[k] or s.get(k,(None,None))[0]!=request[k]:raise ValueError('foreign request binding')
 token=c.get('responseToken',('',None))[0]
 if not token or token!=s.get('responseToken',('',None))[0] or token in (request['nonce'],request['runId']):raise ValueError('server witness mismatch')
 if c.get('complete')!=('true',None) or s.get('complete')!=('true',None):raise ValueError('incomplete native call')
 if num(s,'fixture.vat0')!=0 or num(s,'fixture.vat20')!=20:raise ValueError('native fixture rate resolution differs')
 required={'runId','caseId','nonce','responseToken','complete','fixture.vat0','fixture.vat20'}
 for case,(header,expected_rows) in EXPECTED.items():
  keys={case+'.writeSucceeded',case+'.postedAfter',case+'.exempt',case+'.rowCount',case+'.headerTotal'};required|=keys
  if not boolv(s,case+'.writeSucceeded') or boolv(s,case+'.postedAfter'):raise ValueError('ordinary draft write/reload failed '+case)
  if boolv(s,case+'.exempt')!=(case=='E'):raise ValueError('wrong exemption fixture '+case)
  if num(s,case+'.rowCount')!=len(expected_rows) or num(s,case+'.headerTotal')!=Decimal(header):raise ValueError('persisted header/row count differs '+case)
  for index,values in enumerate(expected_rows,1):
   for field,expected in zip(FIELDS,values):
    key=f'{case}.row{index}.{field}';required.add(key)
    if num(s,key)!=Decimal(expected):raise ValueError('persisted row differs '+key)
 if set(s)!=required:raise ValueError('missing or extra observation keys')
 return {'ordinaryDraftCases':4,'exemptPreservationControl':True,'persistedRowVectorsMatched':True,'postingClaim':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--client-receipt',type=Path,required=True);p.add_argument('--server-receipt',type=Path,required=True);a=p.parse_args()
 try:business=evaluate(json.loads(a.request.read_text(encoding='utf-8')),a.client_receipt.read_bytes(),a.server_receipt.read_bytes())
 except Exception as error:
  print('FAIL: '+str(error),file=__import__('sys').stderr);return 1
 print(json.dumps({'status':'PASS','task':'supplier-invoice-server-write','businessPayload':business},sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
