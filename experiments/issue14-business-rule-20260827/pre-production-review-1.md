# Pre-production contract review 1 — verbatim verdict

Reviewed exact identity:

- HEAD: `2434e83e3566fc8e7306a49d1c94cae73588d6a5`
- TREE: `77acc3173d8030e9fca66ed1988dd642dd75761c`
- PARENT: `7610c59ca373a5138aed2ecd2e762e6909a20637`

## Verdict

**FAIL**

## Material objection

A plausible materially wrong implementation survives every frozen case:

> During server-side posting, reject any `InventoryWriteOff` whose `Inventory` row count is not exactly one; for a one-row document, reject when `Quantity <= 0`; otherwise continue through normal posting and stock control. Do not validate draft writes.

This implementation passes all six frozen cases and observations:

- `[-1.000]`: rejected atomically.
- `[0.000]`: rejected atomically.
- `[2.000, -1.000, 2.000]`: rejected because it has multiple rows.
- `[11.000]`: passes the new check, then existing insufficient-stock control rejects atomically.
- `[4.000]`: posts normally.
- `[0.001]`: posts normally.
- Draft persistence remains allowed.
- Enforcement occurs in the server posting path, not only in UI code.
- Invalid-case `Posted`, recorder-count, and balance observations all match.
- Current-run nonce/object provenance can remain genuine.
- Removing this patch restores every specified invalid RED while preserving the controls.

It is nevertheless materially wrong: a document with two or more strictly positive rows—such as `[2.000, 2.000]`—must be allowed by the stated **iff every row has `Quantity > 0`** rule, but this implementation rejects it. The matrix has no valid multi-row case capable of distinguishing universal per-row validation from an overstrict row-cardinality restriction.

Therefore, the frozen observations do not establish the claimed semantic closure.

## Separate checks

- **Subject/domain and universal quantifier:** **FAIL.** The same-product invalid-middle case closes aggregate-only and endpoint-only checks, but no all-positive multi-row control closes overstrict cardinality/duplicate-product rejection.
- **Exact boundary:** Zero, `-1.000`, normal positive `4.000`, and metadata-minimum positive `0.001` cover the principal comparison and rounding mistakes. Source confirms signed `decimal(15,3)`, `AllowedSign=Any`, and no fill check.
- **Draft versus posting scope:** Covered for invalid drafts: unposted server-side write must succeed before initial posting is rejected.
- **Atomic rejection:** Frozen invalid observations check stored `Posted=false`, recorder counts for both `InventoryInWarehouses` and `InventoryCost`, warehouse quantity balance, and cost quantity/amount balances.
- **Preserved behavior:** Normal positive, minimum positive, and insufficient-stock single-row behavior are covered. **Positive multi-row behavior is not.**
- **Server-side enforcement:** The EPF is specified to call server-side object APIs, closing a UI-only implementation for the frozen cases.
- **Mutation/current-run provenance:** The amendment requires a current-run nonce and created-object identities and requires patch removal to restore all invalid REDs. These are presently requirements, not completed native evidence.
- **Unknown/out of scope:** Empty documents, UI/message behavior, imports, undo-posting, and reposting are explicitly and honestly excluded.
- **Source semantics:** Immutable source confirms row aggregation before Expense movements, both record sets being written during posting, negative-balance control checking only resulting balance `< 0`, and the stated quantity/cost resource precision.
- **No production patch/full RED/GREEN:** Verified for the exact Git tree. Relative to source commit `333ddd876a4cc748cf5cd3c04b60eeea303b229c`, HEAD adds only the five issue-14 documentation files; the permitted production module has no diff. The tree contains no RED/GREEN receipt or implementation artifact. `runtime-entrypoint-gap.md` explicitly records an incomplete diagnostic, not RED.
- **Amendment ordering:** Git history is honest: original contract commit `f070a128...` has tree `e068b717...` and parent/source `333ddd876...`; attribution follows; the amendment follows at the reviewed HEAD. The failed runtime diagnostic was documented with the amendment, so its claimed wall-clock occurrence before amendment freeze is documentary provenance rather than independently Git-timestamped execution evidence.

## Required correction

Add a distinguishing positive multi-row case—preferably same-product rows such as `[2.000, 2.000]`—that must post normally and produce exact recorder counts and both-register balance changes. Patch removal must preserve that control expectation.

## Residual limitations

- No native RED, production implementation, or GREEN was run or claimed.
- Frozen RED movement counts and `0.001` amount rounding remain predictions.
- Current-run nonce freshness and patch-removal mutation are specified but not yet backed by a frozen executable validator or receipt.
- The review does not claim behavior for the explicitly excluded empty-document, UI, undo-posting, or reposting paths.

**Files created or modified by reviewer:** none.
