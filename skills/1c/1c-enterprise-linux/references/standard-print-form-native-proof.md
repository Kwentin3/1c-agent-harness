# Minimal native proof for an existing 1C spreadsheet print form

Use this reference when a product task adds an already-existing optional document value to a standard MXL/Spreadsheet print form, while metadata and posting must remain unchanged.

## Product-shaped route

1. Open the admitted retained snapshot through the existing route. Locate the document metadata, `PrintData` DCS template, and the existing MXL layout with ordinary repository search; do not build context collection or indexing machinery.
2. Prove the value already exists in document metadata before adding it to the DCS field list and query. Keep the production delta confined to the print-data template and layout unless the issue explicitly changes the domain model.
3. Render optional values with one conditional expression that returns an empty string when unfilled. Prefer platform formatting for values such as dates; do not introduce a separate blank row, placeholder, or technical zero-date representation.
4. Preserve exact 1C XML bytes and line endings when the repository delivers a patch artifact. Regenerate the patch from immutable canonical bytes, verify it applies to a disposable canonical copy, and prevent an SCM text-normalization rule from rewriting the artifact when exact CRLF context is required.
5. Add a narrow static contract for: the existing value being selected into print data; conditional empty-state behavior; localized/formatted filled behavior; and an explicit allowlist of changed product paths.
6. Run exactly one final native proof in a disposable work copy. Exercise filled, blank, and repeated-print cases; verify printing does not alter the document or its posted movements; verify source/snapshot identity and automatic cleanup.

## Immutable-baseline prerequisite

If the retained canonical configuration intentionally predates an already-merged prerequisite, a native proof may compose that prerequisite patch with the task's print-only patch **only in the disposable work copy**. State the prerequisite and patch ordering in the receipt/report. Do not claim the print PR owns the prerequisite, and never alter the canonical snapshot or source CF.

## Delivery discipline

Publish the smallest auditable result: one draft PR, one native receipt, and concise mechanical-friction observations. Do not add a graph, registry, generic framework, or new runtime infrastructure solely to support a print-form task.
