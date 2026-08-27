# Pre-production contract review 2 — verbatim verdict

PASS

**Reviewed immutable identity**

- HEAD: `7cf144298ad6c671b0781d30c3a86f5db6bb76eb`
- TREE: `387d896cf8927ed0fb9aa705a58d85025a8d0081`
- PARENT: `2434e83e3566fc8e7306a49d1c94cae73588d6a5`

**Read-only checks performed**

- Verified the exact HEAD/TREE/PARENT before and after review.
- Final index and tracked worktree were clean; both diffs against HEAD returned exit `0`.
- Read the original contract, both amendments, verbatim prior FAIL, semantic checklist, runtime-entrypoint gap record, and attribution record.
- Parsed all three contract JSON files successfully.
- Confirmed the combined matrix has exactly seven unique cases and ten unique named countermodels.
- Read only the relevant immutable Jet locators and matched all seven files to their entries in the pinned 5,099-file snapshot manifest.
- Reverified:
  - source CF SHA-256: `5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a`
  - snapshot manifest SHA-256: `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`

**Prior countermodel reproduction**

The prior implementation—

> reject when Inventory row count is not exactly one; otherwise reject Quantity <= 0

—matched all six previous outcomes. Against the combined matrix it fails the added case: ordered rows `[productA:2.000, productB:2.000, productA:2.000]` are all positive and must post, while the countermodel rejects them. The added case therefore kills the exact prior row-cardinality countermodel.

**Independent adversarial result**

No materially wrong plausible implementation survived all seven cases and required observations:

- Negative, zero, and `0.001` close the exact signed `decimal(15,3)` positivity boundary.
- The invalid middle row with positive aggregate closes aggregate-only and first/last-only validation.
- The added positive three-row case closes blanket multi-row rejection.
- Its non-adjacent duplicate `productA` rows and distinct `productB` close duplicate-product and single-product-only restrictions.
- Draft observations require invalid persisted drafts to remain writable with `Posted=false` and no movements.
- Post-attempt observations cover `Posted`, both recorder sets, and quantity/amount balances, closing residual-effect cancellation.
- Normal positive, minimum positive, and existing insufficient-stock behavior are preserved.
- The EPF contract invokes server-side object APIs and is explicitly instrumentation rather than production code.
- Current-run nonce/object identities and patch-removal mutation are required, preventing stale, constant, or patch-independent success when later executed.

**Added-case arithmetic**

Jet groups by warehouse/product:

- `productA`: `2.000 + 2.000 = 4.000`; opening quantity/amount `10.000/10.00` gives expense amount `4.00`, closing quantity `6.000`, closing amount `6.00`.
- `productB`: aggregate `2.000`; expense amount `2.00`, closing quantity `8.000`, closing amount `8.00`.
- Expected recorder cardinality is exactly two rows in each register, keyed to those two product aggregates.

**Ordering and scope**

Git history preserves the original freeze, amendment 1, its reviewed parent tree, and amendment 2 as a later ordinary commit. Relative to source base `333ddd876a4cc748cf5cd3c04b60eeea303b229c`, only the seven issue-14 documentation files exist; the permitted production module has no diff. No production patch, HANDOFF, RED/GREEN receipt, implementation artifact, or full native RED/GREEN was found or run.

**Material objections:** none.

**Residual limitations**

- Native RED, production implementation, GREEN, nonce freshness, and patch-removal mutation remain future requirements, not completed evidence.
- Frozen RED movement behavior and decimal(15,2) cost rounding remain predictions that must fail closed on native mismatch.
- Empty documents, UI/messages, imports, undo-posting, and reposting are explicitly excluded.
- Arbitrary malicious overfitting is not exhaustively proven; no materially plausible Jet-derived countermodel survives.

**Files created or modified by this review:** none.
