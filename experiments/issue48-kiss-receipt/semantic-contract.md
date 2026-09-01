# Issue 48 — compact proof over accepted Issue 46 GREEN

## Boundary

`shared preparation → native_cycle provenance receipt → task oracle`

## Ownership

- Shared preparation applies the exact ordered production/instrumentation patch bytes itself, then owns canonical-base, changed-path closure and prepared-input identities.
- `native_cycle` owns prepared/frozen input continuity, request/runtime artifacts and cleanup.
- This task oracle alone owns the SupplierInvoice business grammar below.
- GitHub owns candidate head/tree and exact-head CI.

## Business acceptance

For the accepted GREEN request:

- posting to a deleted warehouse fails;
- the rejected document remains unposted and has no recorder movements in Purchases, InventoryInWarehouses, SupplierBalance or InventoryCost;
- draft save succeeds;
- posting to an active warehouse succeeds and produces the expected four register effects;
- the raw server receipt carries the exact fresh request identities and the same opaque payload stored in the standard receipt.

The generic receipt code contains no SupplierInvoice, warehouse, register or task-field names.

## Compactness

This representative task layer contains only this contract, one standard receipt and one oracle. It has no task manifest, replay/preparer, lifecycle/cleanup implementation, large validator, duplicated Base64 receipt, candidate SHA, or task-specific mutation suite.
