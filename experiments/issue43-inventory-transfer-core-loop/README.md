# Issue #43 — InventoryTransfer same-warehouse rule

## Result

A one-file production patch rejects posting `Document.InventoryTransfer` when `Warehouse = WarehouseReceiver` before posting initialization or register preparation. Draft writes remain allowed. The task-specific native probe calls the server object API directly and observes recorder-scoped movements plus exact inventory/cost balances.

## Native observations

| Lane | Runner | Observation |
|---|---|---|
| RED | `run-7vpvx0u8` | Same-warehouse draft saved; posting incorrectly succeeded; document became posted; 2 inventory and 2 cost rows. Distinct-warehouse control posted normally. |
| GREEN | `run-b2m5djmf` | Same-warehouse draft saved; posting rejected; `Posted=false`; 0 inventory and 0 cost rows; balance unchanged. Distinct-warehouse control posted with exact A=`7|7|35`, B=`3|3|15`. |
| Clean repeat | `run-7fl4mw2c` | Exact GREEN business observations repeated from a fresh disposable IB. |
| Bound GREEN 1 | `run-sppm3cya` | Exact GREEN plus receipt-bound fresh `runId/caseId/nonce`; stable terminal receipt. |
| Bound GREEN 2 | `run-swvxtiga` | Exact GREEN repeated in a second clean state with different identities; stable terminal receipt. |

The two final lanes are the acceptance lanes for identity binding and reproducibility. The earlier RED/GREEN/repeat establish the chronological business change cycle but their receipts lack explicit request identities; they are not used to claim stale/foreign protection.

## Package

- `semantic-contract.md` — source-grounded contract frozen before RED and production patch.
- `production.patch` — only production change; one BSL object module.
- `instrumentation.patch` — original RED/GREEN instrumentation.
- `bound-green-*-instrumentation.patch` — exact identity-bound task instrumentation.
- `*-request.json`, `*-receipt.txt`, `*-result.json`, `*-meta.json` — native bindings and runner evidence.
- `validate.py` — fail-closed semantic, identity, runner, hash, and closure validation.
- `package-manifest.json` — exact package closure excluding itself.

Run:

```bash
python3 experiments/issue43-inventory-transfer-core-loop/validate.py
python3 -m unittest -v tests.test_issue43_evidence
```

## Exact immutable target

- base commit/tree: `5c6b0e9c2b20a1fb15aa69ae49539b9786cf816b` / `03407c6c5fbcac550db3f5a2ea48bbdac0a791a3`
- JetTr `1.0.3.1`, 5,099 files
- source CF SHA-256: `5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a`
- manifest SHA-256: `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`
- runtime: training `1cv8t 8.5.1.1150`, SHA-256 `0d11379cfd37c029a472fa500cbd8a64050cc5e53f7904036f8f6ce6a7fe0574`

## Limits

This proves one server object-posting path for nonempty warehouses on the exact JetTr/training-runtime combination. It does not prove GUI rendering, empty-field UX, concurrent posting, repost/undo behavior, live deployment, other configurations, or cryptographic protection against a malicious same-UID writer. The canonical CF/snapshot/manifest and live IB were not changed.
