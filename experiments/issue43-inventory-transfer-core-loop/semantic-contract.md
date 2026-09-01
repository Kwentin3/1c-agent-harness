# Issue #43 semantic contract

Frozen before the production patch and before native RED.

## Change

`Document.InventoryTransfer` currently allows the posting handler to continue when `Warehouse = WarehouseReceiver`. Required behavior: reject only posting in that case, while preserving draft saving and ordinary posting between two distinct warehouses.

## Source-grounded context

- `Documents/InventoryTransfer.xml:221-224` declares recorder writes to `AccumulationRegister.InventoryInWarehouses` and `AccumulationRegister.InventoryCost`.
- `Documents/InventoryTransfer.xml:253-309` defines header attributes `Warehouse` (“Warehouse from”) and `WarehouseReceiver` (“Warehouse to”), both `CatalogRef.Warehouses`.
- `Documents/InventoryTransfer/Ext/ObjectModule.bsl:11-34` is the server object posting handler. It currently initializes posting data, prepares and reflects both record sets, writes them, then checks negative stock. This is the earliest production boundary that covers direct object/API posting as well as form posting.
- `Documents/InventoryTransfer/Ext/ManagerModule.bsl:24-189` reads both warehouse headers and produces expense/receipt rows for both affected registers.
- `Documents/InventoryTransfer/Forms/DocumentForm/Ext/Form/Module.bsl:66-82` has only generic form fill/write hooks and no warehouse-equality rule; a form-only check would not cover direct server posting.

## Contract and observations

| Case | Pre-state | Input/action | Expected persisted/business post-state |
|---|---|---|---|
| Same warehouse | Product balance at warehouse A is quantity 10, cost quantity 10, amount 50 | Create transfer A→A for quantity 3; save draft; then request posting through `DocumentObject.Write(DocumentWriteMode.Posting)` | Draft save succeeds and persisted headers remain A/A; posting is rejected; `Posted=false`; recorder rows are exactly 0 in each of `InventoryInWarehouses` and `InventoryCost`; quantity/cost/amount balance remains exactly `10|10|50` |
| Distinct warehouses | Product balance A=`10|10|50`, B=`0|0|0` | Create transfer A→B for quantity 3 and post via the same server object API | `Posted=true`; exactly 2 recorder rows in each register (expense+receipt); A becomes `7|7|35`, B becomes `3|3|15` |

The seed balance is created by a normally posted `InventoryIncrease` document in the same fresh disposable infobase. The probe emits observations only; `oracle.py` owns PASS/FAIL and rejects missing, duplicate, extra, stale-scenario, or partial receipts.

## Plausible wrong implementations

1. Validate on every write: killed because the A→A draft must save and persist.
2. Validate only in the document form: killed because the native action calls the server object write API directly.
3. Set `Cancel` only after movements are prepared/written: killed by recorder-scoped zero-row checks in both registers and exact unchanged balance state.
4. Reject all transfers: killed by the A→B sufficient-stock preservation case and its exact register/balance effects.
5. Compare the wrong warehouse field or invert equality: killed jointly by A→A rejection and A→B success.

## Scope and unknowns

This proves server object posting for one nonempty same-warehouse pair and one ordinary distinct-warehouse case on canonical JetTr 1.0.3.1. It does not prove GUI message rendering, empty-warehouse UX, concurrent posting, repost/undo-post behavior, or deployment to a live infobase. The no-movement witness is recorder-scoped in both declared registers and is supplemented by exact balances.

READY FOR NATIVE
