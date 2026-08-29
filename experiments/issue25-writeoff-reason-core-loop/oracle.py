#!/usr/bin/env python3
"""External oracle for issue #25 receipts; the BSL probe emits no PASS."""
from pathlib import Path
import sys

def parse(path):
    rows={}
    for raw in Path(path).read_text(encoding="utf-8-sig").splitlines():
        if not raw: continue
        key, sep, value = raw.partition("###")
        if not sep or key in rows:
            raise RuntimeError(f"invalid receipt row: {raw!r}")
        rows[key]=value
    return rows

root=Path(__file__).resolve().parent
red=parse(root/'red-receipt.txt')
green=parse(root/'green-receipt.txt')
expected_red={
 'scenario':'issue25-red','reasonAttributeExists':'No',
 'oldRouteBlankRuleAbsent':'Yes','complete':'true'}
expected_green={
 'scenario':'issue25-green','reasonAttributeExists':'Yes','openingBalance':'10',
 'blankDraftSucceeded':'Yes','blankDraftError':'','blankReasonPersisted':'Yes',
 'blankPostingSucceeded':'No','blankPostingErrorPresent':'Yes','blankPosted':'No',
 'blankMovementCount':'0','blankBalanceUnchanged':'Yes',
 'storedReason':'Damaged during handling','validPosted':'Yes',
 'validMovementCount':'2','validBalanceDelta':'2',
 'insufficientPostingSucceeded':'No','insufficientPostingErrorPresent':'Yes',
 'insufficientPosted':'No','insufficientMovementCount':'0',
 'insufficientBalanceUnchanged':'Yes','complete':'true'}
if red != expected_red:
    raise RuntimeError(f"RED mismatch: {red!r}")
if green != expected_green:
    raise RuntimeError(f"GREEN mismatch: {green!r}")
print("PASS issue25 external oracle: honest RED and server-side GREEN behavior")
