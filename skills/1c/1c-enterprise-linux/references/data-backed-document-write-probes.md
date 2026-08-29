# Data-backed document posting probes in 1C native write cycles

Use this reference when a write-cycle issue must prove server-side document posting semantics, not just a pure BSL function result. It generalizes the issue-14 learning: native RED/GREEN for `Document.InventoryWriteOff` quantity validation in a disposable Jet training infobase.

## Reliable probe shape

1. Work only in a fresh `.local/runs/<issue>/<nonce>/` run root: copied snapshot/work copy, disposable file IB, isolated `HOME`/`TMPDIR`/XDG dirs.
2. Keep production change and probe instrumentation separate:
   - production patch: only the target module/function under test;
   - probe instrumentation: managed application `OnStart` + exported server-call procedure in the disposable work copy only.
3. For data-backed document fixtures, explicitly populate standard document fields before `Write()` or `Write(DocumentWriteMode.Posting)`, especially `Date = CurrentDate()` (or a deterministic date if the contract needs it). In Jet, omitting `Date` made headless `Document.Write()` stop before the next marker with empty `/Out`; setting `Date` let the same write/posting proceed.
4. Seed required master data and balances through normal platform objects, not by editing storage files. For inventory/cost tests, seed with normal receipt/posting documents, then run the target posting cases.
5. For each case, record both draft and posting phases:
   - draft save succeeds/fails;
   - posting call succeeds/fails;
   - final `Posted` state;
   - recorder movement row counts/quantities/amounts for each relevant register;
   - before/after balances from native virtual tables such as `AccumulationRegister.<Register>.Balance(...)`.
6. Use a terminal receipt marker (`complete###true`) and a run nonce. A nonempty receipt is not enough; the client often stays open after the probe completes, so the external runner should wait for the marker and then terminate only its own process group.

## Pre-native 1C observation check

- Treat posting cancellation and exception behavior as separate observations. `Cancel = True` may surface through a client exception depending on the entry point and platform behavior; absence or presence of that exception is not an acceptance requirement unless the user task or a cited, pre-established 1C semantic source requires it. Unknown exception behavior must remain explicit and block any oracle clause that depends on it.
- Emit register state as scalar values for every relevant dimension and resource, for example quantity and amount before/after or their exact deltas. Do not compare separate 1C `Structure` instances with `=` and label the boolean as “balance unchanged”: that operator result is not externally regradable evidence of the contained balances.
- Before 1C, feed artificial complete RED/GREEN scalar receipts to the external oracle and apply the generic missing/extra/duplicate/wrong-value mutation checks from `semantic-contract-testing`.

## Distinguishing good evidence from false RED/GREEN

- A stage marker that stops immediately before `Document.Write()` is diagnostic only, not RED.
- If a probe times out but has no terminal receipt marker, preserve it as a failed attempt and rerun in a fresh IB; partial side effects are unknown.
- A valid multi-row case with repeated product plus a second product is useful when the rule is universal over tabular-section rows. It kills wrong implementations that reject all multi-row documents or single-product duplicates.
- For atomicity, check both absence of recorder movements and unchanged balances in every affected register. `Posted=false` alone is insufficient.
- Keep existing domain controls as negative controls: e.g. a positive but insufficient-stock document should remain rejected by the original stock logic after the new validation is added.

## Patch and receipt publication hygiene

- 1C `TextWriter` may produce UTF-8 BOM + CRLF even when the BSL writes `Chars.LF`. If the repository rejects trailing whitespace, publish an LF-normalized receipt for Git hygiene and record the raw local receipt SHA-256 separately.
- BSL files in hierarchical dumps often use CRLF and tab indentation. A stored `.diff` file with tabbed context lines can itself fail `git diff --check`. If you need a tracked patch artifact, either store an agreed normalized diff format or use a minimal/zero-context diff and prove it with `git apply --check --ignore-space-change --unidiff-zero` against a disposable snapshot copy plus normalized-content equality to the patched work copy.
- Do not claim byte equality after applying a text patch to a CRLF snapshot if the apply path normalizes line endings. Claim normalized-content equivalence and bind raw base/patched hashes separately.

## Minimal repeat gate

A repeat run should start from a new physical run root, copy the immutable snapshot again, apply the published production patch artifact, inject probe-only instrumentation, create/load a new disposable IB, run to `complete###true`, and compare a meaningful observation vector against the primary GREEN. Ignore only nonce and platform-generated document numbers/timestamps.
