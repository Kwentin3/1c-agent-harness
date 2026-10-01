# Shared task-owned native route correction

Use this pattern when a repeated 1C business task must stop rebuilding its own preparer, lifecycle, receipt collector, and evidence package.

## Ownership shape

Publish one generic entry point that accepts:

- an opaque task request;
- exact ordered production and instrumentation patch files;
- the runner completion marker;
- one task-owned oracle;
- the output receipt location.

The route should compose existing owners rather than absorb them:

1. the product command allocates its own disposable prepared path; callers must not run a separate prepare step or precompute changed paths/tree identities;
2. preparation copies the immutable snapshot, applies the exact supplied bytes, audits changed paths, and freezes the disposable tree;
3. the unchanged native runner owns prepared/frozen continuity, runtime and runner cleanup;
4. the task oracle receives request plus raw client/server receipts and returns `PASS` with an opaque business payload;
5. the route issues one generic provenance receipt and removes the prepared tree.

Keep historical task front doors only as thin aliases/adapters to this same command. Remove their independent runner, receipt and cleanup lifecycle instead of documenting two supported product routes. A task request may carry fresh business identities, but it must not carry shared-derived `preparedTree`, `changedPaths`, `treeIdentity` or equivalent proof fields.

Business object, register and field names belong only in the task oracle. A historical task-specific front door may remain for its old task, but it must not be presented as the product entry for arbitrary future tasks. Remove new task-specific front-door wiring from the candidate once the generic route exists.

## Exact patch-byte retention

If accepted patches contain CRLF or source tabs, retain the exact bytes directly. Give exact replay artifacts a dedicated naming convention such as `exact-*.patch` and mark that convention `binary` in `.gitattributes`; this prevents whitespace checks and checkout normalization from rewriting or rejecting valid evidence.

Do not let binary Git presentation hide recurring cost. Independently count every task-owned artifact from exact Git blobs:

- regular-file count;
- physical lines via `bytes.splitlines()`;
- byte size;
- SHA-256 for exact patch files.

The task oracle should independently rehash retained patch files against the receipt. Also perform a static reconstruction on the canonical executor: apply both retained patches in order, recompute the runner tree identity, compare it with the frozen receipt, clean the prepared tree, and recheck canonical continuity. This consumes no native budget.

## Terminal classification

Separate functional closure from compactness. If the route works and exact patch/input provenance closes but the complete recurring layer exceeds the stated size orientation, report `FUNCTIONAL PASS / COMPLEXITY FAIL`; never omit patches from the count or compress maintainable oracle code to manufacture a PASS.

For GitHub reporting, count from committed blobs after the final commit, not from a pre-commit working tree. Read back edited PR bodies/comments byte-for-byte and correct stale counts without changing candidate bytes.