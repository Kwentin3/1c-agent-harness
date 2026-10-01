# Issue 48 — one verification command

## Product boundary

The only product entry is:

```text
scripts/shared_task_route.py run
```

A task supplies only business-owned artifacts:

- `request.json` with fresh scenario identities and no prepared-tree facts;
- exact production patch bytes;
- exact instrumentation patch bytes;
- one oracle that understands the business receipt;
- the literal completion marker.

The shared route owns the rest in one call:

```text
copy canonical input → apply exact patches → derive prepared identity
→ native_cycle.py run-prepared → verify frozen continuity
→ task oracle over raw 1C receipts → short receipt → prepared cleanup
```

`managed_probe_prepare.py` owns copy/patch/freeze. The unchanged `native_cycle.py` owns native
lifecycle and runner cleanup. `shared_task_route.py` owns only their orchestration and the short
generic receipt. `oracle.py` alone owns SupplierInvoice, warehouse and register semantics.

`issue38_frontdoor.py` is a compatibility alias to `shared_task_route.main`; it has no prepare,
runner, receipt or cleanup implementation.

## No hidden ceremony

`request.json` contains no `preparedTree`, `changedPaths`, `treeIdentity`, manifest or replay data.
The CLI has no `prepare` command and no `--prepared-tree` argument. Its positive contract test calls
`run_task` directly from business inputs; the shared route allocates the prepared path and derives
all input identities during that same call.

## Receipt

The command returns and writes one JSON object answering only:

- canonical content identity;
- ordered exact patch hashes;
- prepared/runner/frozen input identity;
- exact request and its hash;
- raw client/server 1C receipts and accepted business payload;
- oracle PASS;
- runner and prepared cleanup.

Exact-schema, request-hash, raw-byte/hash, input-continuity, oracle-PASS and cleanup checks reject
ordinary partial, stale or foreign results. There is no task manifest, replay, schema framework,
storage service or task-specific provenance validator.

## Representative task inputs

| Ownership | Artifact |
|---|---|
| business contract | `semantic-contract.md` |
| fresh business request | `request.json` |
| production | `exact-production.patch` |
| instrumentation | `exact-instrumentation.patch` |
| business oracle | `oracle.py` |

`receipt.json` is command output, not an input or recurring implementation artifact.

## Final-path native smoke

The published command was invoked once with these five inputs and no preceding prepare command.
The resulting `receipt.json` records:

- production patch `4ebe30ff232822bd4a950b0d7ece25dad8c944c5e005dcc1b7e5a56759005343`;
- instrumentation patch `45decea4cf7bc6a8b0ad52dd2274a3f9269d25aafe58a1418b533a33fca29fcc`;
- prepared/runner/frozen input `93569aa33e4c34d2a982722156eae43050cd65e5cb0fca073fd982fb990798f2`;
- request `a9f8486ea07c26c5e0664f0b65dd1725f82044a8d02db98baa2bc62585d299d9`;
- task oracle `PASS`;
- runner cleanup `completed`, zero manual actions, and prepared cleanup `discarded`.

The native runner completed in 66.604 seconds. Canonical target verification remained `ready` and
no owned 1C/Xvfb/native process or `shared-task-*` prepared directory remained afterward.
