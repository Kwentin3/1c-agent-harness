# Issue #25 semantic contract

Frozen before the production patch.

## Rule

`Document.InventoryWriteOff` stores a free-text `Reason`. An unposted draft may be saved with an empty reason. Posting rejects an empty or whitespace-only reason before movements are created. A nonblank reason persists through write/read.

## Failure and preservation

- rejected blank posting remains `Posted=false`, has zero recorder rows, and leaves warehouse and cost balances unchanged;
- a reason-filled ordinary write-off still posts and reduces stock;
- a reason-filled write-off exceeding available stock remains rejected atomically by the existing stock check.

## Plausible wrong implementations and distinguishing observations

| Wrong implementation | Observation that rejects it |
|---|---|
| metadata only | RED shows the old blank posting route still succeeds; GREEN rejects it |
| required on every write | blank draft saves |
| transient/nonpersisted reason | exact text is read back |
| reject every posting | valid reason case posts and moves exactly two register rows |
| replace/bypass stock control | excessive reason-filled write-off remains unposted with zero rows and unchanged balances |
| late rejection after side effects | blank rejection has zero rows and unchanged warehouse/cost state |

The probe emits observations only. `oracle.py` owns the PASS decision.
