# Issue #43 — InventoryTransfer same-warehouse rule

## Result

A one-file production patch rejects posting `Document.InventoryTransfer` when `Warehouse = WarehouseReceiver` before posting initialization or register preparation. Draft writes remain allowed. The task-specific native probe calls the server object API directly and observes recorder-scoped movements plus exact inventory/cost balances.

## Native observations

| Lane | Runner | Observation |
|---|---|---|
| RED | `run-7vpvx0u8` | Same-warehouse draft saved; posting incorrectly succeeded; document became posted; 2 inventory and 2 cost rows. Distinct-warehouse control posted normally. |
| Bound GREEN 1 | `run-sppm3cya` | Same-warehouse draft saved; posting rejected; `Posted=false`; 0 inventory and 0 cost rows; balance unchanged. Distinct-warehouse control posted with exact A=`7|7|35`, B=`3|3|15`; receipt-bound fresh `runId/caseId/nonce`. |
| Bound GREEN 2 | `run-swvxtiga` | Exact GREEN repeated from a second fresh disposable IB with different request identities and stable terminal receipt. |

These are the three retained lanes: one RED and two accepted GREEN runs. The earlier intermediate GREEN/repeat were useful during development but duplicated the accepted lanes and are not part of the package claim.

## Package

- `semantic-contract.md` — source-grounded contract frozen before RED and production patch.
- `production.patch` — only production change; one BSL object module.
- `instrumentation.patch` — exact RED instrumentation.
- `bound-green-*-instrumentation.patch` — exact identity-bound task instrumentation.
- `bound-green-*-input-binding.json` — deterministic canonical+patch reconstruction identity, linked to the runner's prepared/frozen input.
- `*-request.json`, `*-receipt.txt`, `*-result.json`, `*-meta.json` — accepted native request/result evidence.
- `reconstruct_input.py` — task-specific, no-1C replay against the canonical snapshot; recomputes both prepared/frozen tree identities.
- `validate.py` — fail-closed semantic, request, patch-byte, reconstructed-input, runner, hash, and closure validation.
- `package-manifest.json` — exact package closure excluding itself.

The validator requires this chain for both GREEN lanes:

`canonical manifest + SHA(production.patch) + SHA(lane instrumentation) → reconstructed prepared/frozen tree → runner input identities → exact request-bound receipt`.

Changing any patch bytes and merely updating `package-manifest.json` therefore fails against the independently retained input binding.

Run:

```bash
python3 experiments/issue43-inventory-transfer-core-loop/validate.py
python3 -m unittest -v tests.test_issue43_evidence
# On the canonical executor only; copies/patches/hashes source and never starts 1C:
python3 experiments/issue43-inventory-transfer-core-loop/reconstruct_input.py
```

## Exact immutable target

- base commit/tree: `5c6b0e9c2b20a1fb15aa69ae49539b9786cf816b` / `03407c6c5fbcac550db3f5a2ea48bbdac0a791a3`
- JetTr `1.0.3.1`, 5,099 files
- source CF SHA-256: `5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a`
- manifest SHA-256: `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`
- runtime: training `1cv8t 8.5.1.1150`, SHA-256 `0d11379cfd37c029a472fa500cbd8a64050cc5e53f7904036f8f6ce6a7fe0574`

## Limits

This proves one server object-posting path for nonempty warehouses on the exact JetTr/training-runtime combination. It does not prove GUI rendering, empty-field UX, concurrent posting, repost/undo behavior, live deployment, other configurations, or cryptographic protection against a malicious same-UID writer. The canonical CF/snapshot/manifest and live IB were not changed.
