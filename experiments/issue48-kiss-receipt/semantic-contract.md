# Issue 48 — complete representative task layer

## Shared boundary

The published product entry is:

```text
scripts/shared_task_route.py run
  → exact ordered task patches
  → managed_probe_prepare.prepare_patched_tree
  → native_cycle.py run-prepared
  → task-owned oracle CLI
  → standard provenance receipt
  → prepared-tree cleanup
```

The shared route owns orchestration and provenance. `managed_probe_prepare.py` owns only disposable
copy, exact patch application, static closure and freeze. `native_cycle.py` owns native lifecycle,
prepared/frozen continuity and runner cleanup. This task oracle alone owns SupplierInvoice,
warehouse and register semantics.

A following task supplies its business contract, request, exact production patch, exact
instrumentation patch, completion marker and oracle. It does not implement a preparer, native
lifecycle, receipt collector or evidence framework.

## Exact accepted patch bytes

The accepted smoke bytes are retained directly in this task layer:

| Role | Artifact | SHA-256 in `receipt.json` |
|---|---|---|
| production | `exact-production.patch` | `4ebe30ff232822bd4a950b0d7ece25dad8c944c5e005dcc1b7e5a56759005343` |
| instrumentation | `exact-instrumentation.patch` | `61bf75af0846c5f227e5b3544bd284523e1307180224df80a42666ee425eae73` |

The shared route reads these bytes once, applies those same bytes in order, and records their
SHA-256 values in the preparation audit that becomes the receipt. The task oracle independently
rehashes both retained files when validating the frozen receipt. A substituted artifact or receipt
hash therefore fails without another native run.

## Business acceptance

For the accepted GREEN request:

- posting to a deleted warehouse fails;
- the rejected document remains unposted and has no recorder movements in Purchases,
  InventoryInWarehouses, SupplierBalance or InventoryCost;
- draft save succeeds;
- posting to an active warehouse succeeds and produces the expected four register effects;
- client and server receipts carry the exact fresh request identities and matching response token.

The generic route contains none of these task field names.

## Accepted native seam

The frozen `receipt.json` is unchanged. It came from the one accepted native smoke:

- `runtime_contract_completed`;
- task oracle PASS;
- 94.852 seconds;
- runner cleanup completed;
- prepared tree discarded;
- canonical target returned to `ready`.

This static correction performs no native execution, RED, repeat or reviewer cycle.

## Honest recurring size

The complete recurring task layer is every regular file in this directory:

1. `semantic-contract.md` — business contract and ownership;
2. `exact-production.patch` — exact production bytes;
3. `exact-instrumentation.patch` — exact instrumentation bytes;
4. `oracle.py` — maintainable task business oracle and shared CLI contract;
5. `receipt.json` — compact standard result.

Compactness is reported from all five files, using physical lines and bytes. No source file is
compressed to improve the count. Runtime-generated `request.json` and raw runner files are inputs
to the shared route and are already byte-bound inside the compact receipt; they are not a second
retained task implementation.

## Honest limits

This is trusted-lab provenance, not protection from an author who controls all code and artifacts.
The static correction proves recoverability of the exact accepted patch bytes and closes the
published shared route contract without claiming another native result.
