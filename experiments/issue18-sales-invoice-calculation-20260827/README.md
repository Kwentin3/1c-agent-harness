# Issue #18 — SalesInvoice server-side derived amount normalization

Status: owner HOLD before production patch/native RED; amendment 3 awaits final independent review and explicit owner acceptance.

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

No production patch or native attempt exists. The final independent pre-patch review must challenge amendment 3 at its exact published identity, and explicit owner acceptance is still required even after a PASS. Native work is also blocked until sufficient local disk space is available or cleanup is authorized for exact inventoried disposable roots; no root has been deleted.
