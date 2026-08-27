# Issue #18 — SalesInvoice server-side derived amount normalization

Status: owner-accepted amendment 3 completed an honest native RED/GREEN core loop and a clean repeat; final exact candidate review is pending.

## Candidate

The second task is a cross-field calculation rule, semantically different from issue #14 row-quantity eligibility. The existing Jet client form calculates each `SalesInvoice.Inventory` row as `Amount = Quantity * Price`, then VAT and `Total`; server `BeforeWrite` currently only sums the already stored row totals. Posting consumes those stored values for Sales and CustomerBalance movements.

The original pre-patch contract is [`task-contract.json`](task-contract.json). Independent review found a surviving last-row-only countermodel and under-specified exchange/cost observations. The original remains immutable; [`task-contract-amendment-1.json`](task-contract-amendment-1.json) transparently supersedes only the deficient target matrix/oracle and adds an existing-helper source constraint. A second review showed that a correct helper loop plus an unauthorized `Inventory.Count() > 3` rejection still passed; [`task-contract-amendment-2.json`](task-contract-amendment-2.json) bounded the executable delta. The owner then kept HOLD despite reviewer PASS: [`task-contract-amendment-3.json`](task-contract-amendment-3.json) separates runtime semantics from patch policy, adds mixed correct/stale rows at two cardinalities/orders, narrows experimental VAT scope to `VATWithholding=false`/`ExemptFromVAT=false`, and treats inventory/cost vectors only as preservation controls. No production patch or native attempt existed before any amendment.

Cost measurement: [`cost-ledger.json`](cost-ledger.json). Core-loop time ends at first complete native GREEN; clean repeat/package/final review are recorded separately as milestone overhead.

## Source identities at freeze

- Source CF SHA-256: `5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a`
- Snapshot manifest SHA-256: `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`
- Snapshot: 5,099 declared/actual files; missing/mismatch/extra/symlink all zero at freeze.

The raw CF and snapshot remain local and untracked. Repository artifacts use stable snapshot-relative locators, not private run-root paths.

## Current stop boundary

Owner comment `5443057227` accepted amendment 3, authorized deletion of exactly two issue-2 disposable reconstruction roots, and authorized production/native RED/GREEN. Only those two roots were removed. Available space increased from 317,677,568 to 979,791,872 bytes; deleted bytes are not directly recoverable, while the roots remain reproducible from the tracked issue-2 recipe. Protected source/snapshot/manifests, issue #14 roots, platform and dist remained present and their checked identities were unchanged.

The same expectation-free probe then produced:

- honest RED on unmodified production bytes (`535bbbee…`): mixed targets persisted and posted stale totals `123` and `73`;
- GREEN on the one-file four-line production patch (`e617889f…`): the same targets persisted and posted normalized totals `34` and `40`;
- exact observation-key parity between RED and GREEN, with 32 behavior keys changed;
- unchanged consistent VAT20 behavior and unchanged atomic insufficient-stock rejection;
- unchanged inventory/cost preservation vectors.

Review artifacts:

- [`production-patch.diff`](production-patch.diff)
- [`instrumentation.diff`](instrumentation.diff)
- [`instrumentation-summary.json`](instrumentation-summary.json)
- [`native-invocations.json`](native-invocations.json)
- [`red-receipt.txt`](red-receipt.txt) and [`red-summary.json`](red-summary.json)
- [`green-receipt.txt`](green-receipt.txt) and [`green-summary.json`](green-summary.json)
- [`repeat-receipt.txt`](repeat-receipt.txt) and [`repeat-summary.json`](repeat-summary.json)

The required milestone repeat started from a new physical work copy and disposable IB reconstructed directly from the immutable snapshot. It used the same production bytes (`e617889f…`) and expectation-free probe template (`18b04dcb…`), and matched primary GREEN on every non-binding observation value. No driver, framework, skill change, or speculative evidence hardening was added.

The instrumentation diff is a reconstructable LF-normalized template, not merely readable text. It preserves the immutable source file's missing-final-newline marker, passes `git apply --check`, and reconstructs the sanitized RED/GREEN/repeat probe bytes exactly. [`instrumentation-summary.json`](instrumentation-summary.json) binds the patch hash, declared run bindings, and both reconstructed target hashes.

Measured verdict: **SECOND TASK PASS / COST NOT YET LOW**. RED→first GREEN took 289 seconds and the task-specific probe was smaller than #14 (270 vs 328 added lines), but frozen-contract→RED took 4,076 seconds because two independent countermodels, owner HOLD, remote-reviewability work and the disk gate were real churn. The full core-loop cost therefore did not demonstrate a reliable reduction.

The next gate is independent final source/evidence review of the exact tracked candidate. PR merge and issue closure remain owner decisions.
