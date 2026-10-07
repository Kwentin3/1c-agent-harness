# Minimal native proof for an existing 1C spreadsheet print form

Use this reference when a product task adds an already-existing optional document value to a standard MXL/Spreadsheet print form, while metadata and posting must remain unchanged.

## Product-shaped route

1. Open the admitted retained snapshot through the existing route. Locate the document metadata, `PrintData` DCS template, and the existing MXL layout with ordinary repository search; do not build context collection or indexing machinery.
2. Prove the value already exists in document metadata before adding it to the DCS field list and query. Keep the production delta confined to the print-data template and layout unless the issue explicitly changes the domain model.
3. Render optional values with one conditional expression that returns an empty string when unfilled. Prefer platform formatting for values such as dates; do not introduce a separate blank row, placeholder, or technical zero-date representation.
4. Preserve exact 1C XML bytes and line endings when the repository delivers a patch artifact. Regenerate the patch from immutable canonical bytes, verify it applies to a disposable canonical copy, and prevent an SCM text-normalization rule from rewriting the artifact when exact CRLF context is required.
5. Add a narrow static contract for: the existing value being selected into print data; conditional empty-state behavior; localized/formatted filled behavior; and an explicit allowlist of changed product paths.
6. Run exactly one final native proof in a disposable work copy. Exercise filled, blank, and repeated-print cases; verify printing does not alter the document or its posted movements; verify source/snapshot identity and automatic cleanup.

## Training-runtime capability boundary

Do not assume a training platform can save or print a SpreadsheetDocument merely because it can create/render one in memory and bind it to a managed form. Training 8.5.1.1150 was observed rejecting `SpreadsheetDocument.Write(..., SpreadsheetDocumentFileType.HTML)` with `Current license limitation. Print and save spreadsheet functions are not available in the training version.` This is an export/print restriction, not evidence that a read-only dashboard cannot calculate or create its native form.

If exporting is not the product goal, omit it from the business proof. Verify native cell values, managed-form binding, repeated/empty behavior and unchanged source state through permitted read-only observations; a separately composed HTML receipt preview must remain explicitly a proxy, never a native export or screenshot. If actual printing/export is the goal, stop for the missing licensed capability; do not bypass licensing. Never mark a full oracle PASS when an optional export exception prevented later checks. Correct the probe within its admitted budget, or request one bounded extra attempt when that budget is exhausted; unanswered approval is not authorization.

For nested UNION queries, validate the placement of `ALLOWED` on the exact target runtime. A nested `SELECT ALLOWED` was rejected by the 1C engine as available only on the first query. Keep permission checks and top-level `SELECT ALLOWED`; remove illegal nested placements rather than enabling privileged mode or swallowing permission errors.

## Immutable-baseline prerequisite

If the retained canonical configuration intentionally predates an already-merged prerequisite, a native proof may compose that prerequisite patch with the task's print-only patch **only in the disposable work copy**. State the prerequisite and patch ordering in the receipt/report. Do not claim the print PR owns the prerequisite, and never alter the canonical snapshot or source CF.

## Delivery discipline

Publish the smallest auditable result: one draft PR, one native receipt, and concise mechanical-friction observations. Do not add a graph, registry, generic framework, or new runtime infrastructure solely to support a print-form task.
