# #85 — owner dashboard for yesterday

[Actual result and limits](RESULTS.md) · [Product/query contract](CONTRACT.md) · [Pre-run API admission](ADMISSION.md) · [Actual observations](OBSERVED.json) · [Russian structural/data proxy](preview.html).

- Existing native Report.Dashboard; production delta is exactly3 files.
- Real sales-posting/query/managed-form creation observed; values match independent expectation.
- Full strict oracle **FAIL**: training platform rejects test-only HTML spreadsheet export; later acceptance checks did not execute.2/2 attempts used, third not authorized; issue stays open.
- `product/` is the readable UTF8/LF code; `exact-production.patch` preserves canonical BOM/CRLF for exact application. `exact-instrumentation.patch` matches run2, including its failing helper export. These are task artifacts, not new harness/runtime features.
- `evidence/` contains actual raw receipts/results/API member hashes/preflight; no synthetic external evidence, full snapshot, CF or IB.
- Native preview not claimed: composed HTML proxy uses actual test receipts; no interactive GUI screenshot/native export.
- No live/source database change, deployment, restart, merge or release.
