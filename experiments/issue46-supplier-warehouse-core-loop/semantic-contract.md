# Supplier invoice / deleted warehouse semantic contract

Frozen before the production patch and before native RED.

## Change

A `Document.SupplierInvoice` draft may be saved when its `Warehouse` is marked for deletion, but posting that draft must be rejected before any posting preparation or register reflection. A supplier invoice for an active warehouse must retain the existing posting behavior.

## Context and execution layer

- `Documents/SupplierInvoice.xml:216-226` allows posting and declares recorder movements in `Purchases`, `SupplierBalance`, `InventoryInWarehouses`, and `InventoryCost`.
- `Documents/SupplierInvoice.xml:300-342` defines the required `Warehouse` header reference.
- `Documents/SupplierInvoice/Ext/ObjectModule.bsl:11-35` is the server-side posting handler; today it initializes document data, prepares record sets, reflects all four registers, and writes them without checking `Warehouse.DeletionMark`.
- `Documents/SupplierInvoice/Ext/ManagerModule.bsl:12-181` derives all four record tables from the persisted supplier invoice.
- `CommonModules/PostingManagement/Ext/Module.bsl:70-82,112-124,175-208` loads the four record sets when `Cancel` is false.

The nearest material bypass is direct server-side `DocumentObject.Write(DocumentWriteMode.Posting)`, so the rule belongs at the beginning of the object posting handler rather than in a form. Draft `Write()` reaches `BeforeWrite`, not `Posting`, and therefore remains allowed.

## Cases and observations

| Case | Pre-state | Action | Expected persisted/business post-state |
|---|---|---|---|
| deleted warehouse | Fresh persisted warehouse has `DeletionMark=true`; fresh supplier invoice references it and has one inventory row; all four recorder counts are zero | Save draft, then request posting | Draft save succeeds and has a non-empty reference; posting raises/reports rejection; `Posted=false`; recorder-scoped counts remain exactly zero in `Purchases`, `InventoryInWarehouses`, `SupplierBalance`, and `InventoryCost` |
| active warehouse | Fresh persisted warehouse has `DeletionMark=false`; fresh otherwise-equivalent supplier invoice has one inventory row; all four recorder counts are zero | Request posting | `Posted=true`; each of the four declared registers has exactly one recorder row; inventory quantity and purchase quantity are 2; purchase/cost/supplier amounts are 20 |

Each native request carries fresh UUIDv4 `runId`, `deletedCaseId`, `activeCaseId`, and `nonce`. The server writes an independent sibling receipt and returns a newly generated response token; the client receipt must repeat the request identity and matching token, and the token must differ from the nonce. The external oracle owns PASS/FAIL.

## Plausible wrong implementations

1. **Validate on every write** — rejected because the deleted-warehouse draft must persist successfully.
2. **Validate only in the document form** — rejected because the native probe posts through a direct server call.
3. **Set `Cancel` after record preparation/reflection/writing** — rejected by the earliest-point static locator and by zero recorder rows in every declared register.
4. **Reject all supplier-invoice postings** — rejected by the active-warehouse preservation case and its expected four-register movements.
5. **Check whether the invoice itself is marked for deletion** — rejected because only the warehouse is marked while the saved invoice is not.

## Scope and unknowns

This proves the normal server-side supplier-invoice `Write(DocumentWriteMode.Posting)` path in a fresh disposable JetTr file infobase. It does not cover `DataExchange.Load`, undo-posting, concurrent deletion-mark changes, or other document types. No live or canonical infobase is modified.

READY FOR NATIVE
