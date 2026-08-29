# Issue #29 semantic contract

Frozen before the production patch.

## Rule

For `Document.InventoryIncrease`, every row of `Inventory` must have `Price > 0` when the document is posted. An unposted draft may be saved with a zero or negative price. Posting a document with any zero or negative row price is rejected. An ordinary document whose every row has a positive price continues to post normally.

## Failure and preservation

- a zero-price draft saves, but posting it is rejected, leaves `Posted=false`, creates no recorder movements, and leaves warehouse/cost balances unchanged;
- a draft with a positive first row and a negative second-row price saves, but posting it is rejected with the same atomicity guarantees;
- an ordinary multi-row receipt with strictly positive prices posts and creates the expected inventory and cost movements/balances.

## Plausible wrong implementations and distinguishing observations

| Wrong implementation | Observation that rejects it |
|---|---|
| require a positive price on every write | zero and negative drafts both save |
| reject only `Price < 0` | zero-price posting is rejected |
| reject only `Price = 0` | negative-price posting is rejected |
| inspect only the first row | positive first row plus negative second row is rejected |
| validate a total/sum rather than every row | the mixed-price document has a positive total but is rejected |
| reject every posting | an ordinary two-row positive-price receipt posts |
| reject after side effects | rejected documents have zero recorder rows and unchanged balances |

The native probe emits observations only. `oracle.py` owns the PASS decision.
