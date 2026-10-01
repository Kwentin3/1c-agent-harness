"""Task oracle: strict fresh client/server observations, not process success."""
import argparse,json
from pathlib import Path
CASES = ('emptyDraft','emptyPosted','stockCount','costCount','stockValues','costValues',
         'filledDraft','filledPosted','stockUnchanged','costUnchanged','shortageRejected',
         'rejectedStockZero','rejectedCostZero')
def rows(path):
    values={}
    for line in Path(path).read_bytes().decode('utf-8-sig').splitlines():
        key,sep,value=line.partition('###')
        if not sep or not key or key in values:
            raise ValueError('malformed/duplicate receipt row')
        values[key]=value
    return values
def validate(request,client,server):
    if set(client)!={'run','nonce','token','returned','complete'}:
        raise ValueError('incomplete client receipt')
    if set(server)!={'run','nonce','token','serverComplete',*CASES}:
        raise ValueError('incomplete server receipt')
    for record in (client,server):
        if record['run']!=request['runId'] or record['nonce']!=request['nonce']:
            raise ValueError('stale request binding')
    if (not server['token'] or server['token']==request['nonce']
        or server['token']!=client['token']):
        raise ValueError('server witness mismatch')
    for name in CASES:
        if server[name]!='true':
            raise ValueError('business observation failed: '+name)
    if client['returned']!='true' or client['complete']!='true' or server['serverComplete']!='true':
        raise ValueError('not complete')
    return {'status':'PASS','businessPayload':{'observations':{k:True for k in CASES},
            'scope':'native document save/post/read; static form binding, not interactive UI'}}
def main():
    p=argparse.ArgumentParser()
    for name in ('request','client-receipt','server-receipt'):p.add_argument('--'+name,required=True)
    a=p.parse_args()
    print(json.dumps(validate(json.loads(Path(a.request).read_text()), rows(a.client_receipt), rows(a.server_receipt))))
if __name__=='__main__': main()
