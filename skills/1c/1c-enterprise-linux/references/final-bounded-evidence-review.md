# Bounded final review for 1C frozen evidence packages

Use this when a caller asks for a tight PASS/FAIL review of a completed 1C write-cycle evidence package at an exact Git HEAD/TREE, especially after a prior broad review timed out. This is a review lane, not a new native run.

## Scope discipline

- Freeze identity first and last: `git status --short`, `git rev-parse HEAD`, and `git rev-parse HEAD^{tree}` must match the requested identity and remain clean after the review.
- Stay inside the caller-named tracked package files. For issue-style packages this usually means `task-contract*.json`, `pre-production-review-*.md`, `red-source-*`, `production-patch.diff`, `green-production-*`, and `repeat-green-*`.
- Do not run broad searches over `.local/`; treat actual 1C source/work copies under `.local/` as local evidence, not the tracked production artifact, unless the caller explicitly asks for a native rerun or source inspection.
- Default to not inspect unrelated issue tests or whole-repository suites when the gate is a bounded final verdict. If the caller names exact verification commands (for example full `unittest discover`, PR checks, or false-positive challenges), treat those commands as part of the review scope; run and report them, but avoid additional broad exploration beyond the named checks.

## Review sequence

1. Reconstruct the semantic contract from the original contract and amendments. Check that amendments closing countermodels landed before RED/GREEN and production patch evidence.
2. Read the pre-production review verdicts to identify the strongest known surviving countermodels and confirm each has a distinguishing later case.
3. Inspect `production-patch.diff` as the production artifact. Confirm file count, allowed path, insertion/deletion stats, and that the guard is placed before movement initialization/record writes. For CRLF 1C dumps, it is acceptable to verify patch applicability with whitespace-aware/unidiff-zero semantics and claim normalized-content equivalence rather than byte equality when line endings normalize.
4. Use at most one deterministic receipt parser over the published receipts: compute SHA-256, check `complete###true`, ensure all expected cases have begin/end markers, and compare only meaningful fields. Ignore run nonce and platform-generated document numbers/timestamps only when the package says to.
5. If the package ships a fail-closed validator, actively challenge reproduced false positives in an isolated temporary copy, refreshing the manifest/hash metadata if the package exposes that helper. At minimum:
   - mutate one meaningful summarized observation (for example an invalid-case post-balance) and verify the validator rejects because the summary no longer matches the receipt/expected semantics;
   - mutate one native output identity (for example `native-invocations.json` → `runs.<run>.outputs.runtimeResultJsonSha256 = "0" * 64`) and verify the validator rejects because the frozen output identity no longer matches.
   Do not mutate the repository worktree for these challenges.
6. Check the published instrumentation/probe artifact as a template or exact per-run artifact. If it claims placeholders such as `<RECEIPT_FILE>`, `<STAGE_FILE>`, `<RUN_NONCE>`, or `<RUN_MODE>`, verify those placeholders really exist and no run-specific receipt path/mode remains hardcoded. Run `git diff --check` over the reviewed range so whitespace in `.diff` artifacts does not break repository checks.
7. Compare RED vs GREEN vs repeat observations: invalid cases should flip from source-posted to patch-rejected; draft saves must remain allowed; atomicity requires `Posted=false`, zero recorder rows in both registers, and unchanged warehouse/cost balances; positive controls and insufficient-stock rejection must remain unchanged; repeat GREEN must match primary GREEN on the meaningful observation vector.
8. Finish with a verdict in the exact caller-requested shape. If failing, give one concrete surviving counterexample or unverifiable claim, not a broad essay.

## Strong countermodels checklist

- `Quantity < 0` instead of `Quantity <= 0`.
- Aggregate-only validation over grouped rows rather than every tabular-section row.
- First-row, last-row, or endpoint-only validation.
- Rejecting invalid unposted drafts instead of only rejecting posting.
- Cancelling after residual register effects remain.
- Overstrict positive domain such as integer-only or `Quantity >= 1`.
- UI-only/server-bypass validation or stale/patch-independent evidence.
- Blanket multi-row rejection.
- Duplicate-product or single-product-only restriction.
- Regression of existing positive insufficient-stock control.

## Pitfalls

- Do not turn a prior timed-out transcript into approval; rerun the small final lane and quote the final HEAD/TREE.
- Do not broaden into native platform reruns just because `.local/` exists; bounded final review can be decided from the frozen tracked package plus one parser when the package already carries native receipts.
- Do not commit a new tracked `final-review.md` after a reviewer PASS on an exact HEAD/TREE unless you intentionally rerun review on the new commit. That extra commit invalidates the reviewed identity. Prefer putting the PASS verdict in the issue comment and PR body while opening the PR at the exact reviewed head.
- Before opening the PR, re-check `gh pr list --head <branch>` (or equivalent) to avoid duplicates, then verify the created PR's `headRefOid` equals the reviewed HEAD and leave it open/unmerged unless the user explicitly asked to merge.
- Do not overclaim unreviewed scope such as empty documents, UI messages, imports, undo-posting, reposting, or portability to other configurations/platforms.
- Do not read more files after the final identity check; if new evidence is needed, run it before the final clean identity pass.
