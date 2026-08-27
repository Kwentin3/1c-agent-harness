# Issue #14 — InventoryWriteOff positive-quantity posting rule

This package is the reviewable evidence for PR #15 / issue #14. It remains a bounded Jet training-configuration experiment, not a general 1C write platform.

## Production change

The production change is only `production-patch.diff`, targeting `Documents/InventoryWriteOff/Ext/ObjectModule.bsl`. It inserts a `+6/-0` guard before posting movement initialization:

- iterate every persisted `Inventory` tabular-section row;
- if any `Quantity <= 0`, set `Cancel = True` and return before register movement construction/writes.

## Evidence package contract

`package-manifest.json` closes the exact tracked file set under this directory, excluding the manifest itself. `tests/test_issue14_evidence.py` verifies manifest closure, artifact hashes, receipt structure, summary-vs-receipt consistency, RED/GREEN expected observations, canonical byte equality, and a negative mutation where `green-production-summary.json` is changed to a false `inventoryAfterA=999` while the manifest is refreshed.

## Chronology

1. `task-contract.json` froze the initial contract before production code.
2. `task-contract-amendment-1.json` closed the semantic clauses but review 1 failed.
3. `pre-production-review-1.md` records the surviving row-count countermodel.
4. `task-contract-amendment-2.json` adds the distinguishing valid multi-row duplicate-product case.
5. `pre-production-review-2.md` records PASS for the strengthened pre-production contract.
6. `red-source-*` records native RED on source logic.
7. `green-production-*` records historical primary GREEN after the minimal patch.
8. `repeat-green-*` is canonical GREEN #1 after applying the published patch to a fresh copy.
9. `canonical-green-2-*` is canonical GREEN #2 with the same patched production-file hash as canonical #1.

## Native measurement program

The accepted measurement path is not an EPF. The failed EPF/on-start attempts remain local diagnostics only. Accepted runs use a probe-only managed-app entrypoint plus an exported `JetServerCall.Issue14RuntimeProbe` procedure; the sanitized instrumentation is published as `instrumentation.diff`. Per-run native argv, environment placeholders, run nonce/mode, published receipt hashes, local-only output hashes, applied instrumentation file hashes, DumpResult values, log hashes, and success markers are bound in `native-invocations.json`.

Instrumentation size: `328` added / `0` removed lines across two non-production files. It creates isolated catalog/document data, saves each draft, attempts posting, then records posted state, balances, and recorder movements for `InventoryInWarehouses` and `InventoryCost`. It does not contain expected pass/fail assertions; the assertions live in the Python evidence validator.

## Canonical production bytes

The historical primary GREEN used semantically equivalent but byte-different patched production bytes (`aac9b1...`, all-CRLF). Canonical representation is the result of applying the published zero-context patch to the source snapshot, which produces patched file SHA-256:

`d8124e2942426edf82394673561f96d914c8cf35503ccdc0048eb613e801ea3a`

Both `repeat-green-summary.json` and `canonical-green-2-summary.json` use that same patched production-file hash and their meaningful observation vectors match.

## Results

- RED: source logic allowed invalid quantity-rule postings (`negative_single`, `zero_single`, `mixed_same_product`).
- GREEN: invalid quantity-rule cases keep draft saving, fail posting, leave `Posted=false`, zero recorder movements, and unchanged balances.
- Existing positive insufficient-stock control still rejects atomically.
- Valid positive cases still post, including `0.001` and `[A:2, B:2, A:2]` aggregating to A `10 -> 6`, B `10 -> 8`.

Immutable inputs after repeat/canonical runs:

- snapshot manifest SHA-256: `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`
- source CF SHA-256: `5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a`
- snapshot file count: `5099`

## Practical cost and reuse

Cost was dominated by finding a reliable data-backed posting entrypoint, then by making the evidence self-checking enough to fail closed. Approximate wall-clock ranges for issue #14 were: rule/source reconnaissance about 20–40 minutes; failed runtime entrypoint diagnostics about 1–2 hours; accepted RED setup/run about 20–40 minutes; minimal patch plus primary GREEN about 15–30 minutes; canonical repeat/binding/package hardening about 1–2 hours. Reused from issue #10: training-edition native command shape, disposable file IB, managed-application probe entrypoint, semantic complete-marker polling, CRLF/BOM receipt handling, and the package-manifest validator pattern. New issue #14-specific work: explicit `Document.Date` before draft/post writes, per-product balance queries, recorder movement queries, and the semantic countermodel matrix for document posting.

Manual steps that remain: starting/accepting independent reviewer runs, publishing GitHub comments/PR text, and interpreting reviewer countermodels. The next similar task will still hurt around native runtime startup cost, 1C error-message opacity, and careful separation of production patch bytes from instrumentation bytes.

## Limits / non-claims

No claim is made for empty documents, UI validation/messages, imports, undo-posting, reposting, other documents/configurations, or other 1C platform versions. The rejection currently has no user-facing message; only atomic server-side cancellation is proven. Raw source snapshot, CF, disposable work copies, and infobases remain local under `.local/`; this package publishes only sanitized evidence.
