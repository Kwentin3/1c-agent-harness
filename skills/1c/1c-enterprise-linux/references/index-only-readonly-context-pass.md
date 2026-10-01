# Index-only read-only context pass

Use this when a frozen-review task permits only `stats` and `query` on a prebuilt index over a physically separate source copy. The task contract overrides normal snapshot-inspection practice.

## Admitted inspection-script variant

Some frozen lanes admit named inspection scripts from an external checkout (for example, metadata/configuration summary tools) plus ordinary read-only inspection of the canonical snapshot. This is still a restricted front door, not permission to explore the checkout or use other skills.

1. Read only the usage documentation and help for the admitted scripts, then invoke only those scripts with the exact environment named by the task.
2. Use script output to identify candidate objects and paths; bind every material mechanism claim to canonical, line-numbered source before reporting.
3. Do not use local repository copies, task roots, prior outputs, network/history, or non-admitted checkout content. Do not start 1C, a database, or a GUI in a read-only context pass.
4. When checking the required clean worktree without risking an index write, prefer `GIT_OPTIONAL_LOCKS=0 git status --porcelain` where Git supports it.
5. For a machine-validated result, emit only the required JSON fields. Mark static candidates as un-applied; include empty-input, mismatch, no-fallback, and preserving-match cases for a currency-compatible selection rule.


1. Run the declared project/readiness verifier before any investigation. Record every required identity verbatim: readiness status, full Git SHA, clean status, manifest SHA, and file count.
2. Run only the allowed index subcommands, from the admitted source-copy root (or with its documented path option). Do not invoke index creation, refresh, cleaning, serving, or direct database access.
3. Use exact-symbol queries to establish declarations and function bodies. Treat indexed variable hits as metadata/type locators, not proof of an execution path or a call graph.
4. Separate facts from gaps. For example, a generic `FillDocument` routine that ultimately calls `FillPropertyValues` establishes generic property application, but does **not** establish the caller, selection order, or validation in a specific document-to-document route.
5. Run the verifier and Git checks again as the final action. Any declared identity mismatch is `CONTEXT BLOCKED`; do not reconcile or modify anything.

## Catalog-only minimal-context variant

Use this variant when the contract admits only a prebuilt metadata catalog command and a line-ranged read command over a frozen canonical snapshot.

1. Query the catalog first for each business object and concept. Read only paths returned by that catalog, even when a conventional 1C path seems obvious. Never inspect repository docs, history, prior lane outputs, raw catalog storage, or terminal spill files when the contract excludes them.
2. Keep a per-task set of unique files read and enforce the declared cap. Re-reading a narrower range of the same file does not expand the unique-file set, but record the file once in the final `filesRead` array.
3. Avoid oversized batched reads: tool-output truncation can hide the middle objects while still consuming context. Prefer one object module plus bounded metadata/manager ranges, then re-read targeted ranges of those same admitted files for exact locators.
4. Treat catalog hits as navigation candidates. Bind every owner, procedure, dependency, bypass, register, and patch-boundary claim to line-numbered canonical reads. Treat an empty term result as bounded catalog evidence, not proof of global absence.
5. For posting-only rules, inspect three surfaces together: document metadata (posting and declared registers), the object module's `Posting`/`BeforeWrite` handlers, and the nearest manager-module initialization. To preserve draft writes and reject without movements, place the guard at the first executable lines of `Posting`, before locks, initialization, record-set preparation, reflection, or writes; set `Cancel` and immediately `Return`.
6. For a new optional document attribute, separate the core storage/rule boundary (document metadata plus object-module posting validation) from explicit-form usability. If the managed form enumerates controls, report its form XML as a conditional or required boundary according to whether standard-form editing is in scope; do not silently infer print, EDI, movement, or fill propagation.
7. Write only the allowed result artifact and emit exactly the requested machine schema. Include material unknowns, exact locators, and the audited unique-file list; keep the final chat response to the requested confirmation when the task says so.

## Locator discipline

- Report only a path that the allowed tool actually emitted or that is independently authorized by the task.
- If the index supplies only `file_id` and a line, retain it as `file_id=<n>, lines <range>` and put the missing path in `uncertainties`; do not infer a conventional 1C serialization path.
- A query that returns no exact symbol is an index limitation, not evidence that the runtime mechanism does not exist.
- State candidate changes as un-applied and conditional on confirming the execution hook in an authorized later phase.

## Output discipline

When the task has a machine schema, emit exactly that schema, with no prose. `source_mutated` is true only if the source/canonical input/Git worktree/index/task root was written; ordinary read-only queries do not make it true. Include the exact tool scope used and retain material unknowns instead of turning them into implementation assertions.

### Finalize-now steering

If the user says to stop further analysis/search and finish from already collected facts, treat that as a hard frontier:

1. Do not open a new search direction, broaden candidate discovery, or add a review lane.
2. Use only evidence already returned. Continue canonical reads only when the user's wording explicitly permits them; otherwise preserve missing details in `unknowns`.
3. Write the required machine artifact immediately, rely on the write tool's syntax validation, and return only the requested confirmation (for example, the output path).
4. Do not delay delivery for optional completeness work. A bounded result with explicit unknowns is preferable to violating the stop instruction.

## Pinned code-index MCP argument and fallback notes

For `code-index-mcp` lanes driven through a restricted experiment wrapper:

- `search_code_advanced` uses the required JSON argument `pattern`; do not assume a generic `query` field.
- Use `find_files` or successful indexed hits to authorize a relative path before canonical line reads.
- A shallow index may summarize XML while returning `needs_deep_index` for BSL in `get_file_summary`, and `get_symbol_body` may likewise be unavailable. Under a no-index-mutation contract, do **not** build the requested deep index; fall back to the explicitly admitted canonical `read` command for only MCP-discovered files.
- Count unique canonical files read per task, not read invocations, and keep that count inside the declared task budget.
- Broad standard-field terms such as `DeletionMark` can be noisy; once the owner metadata path is known, prefer bounded canonical reads of that discovered owner file over pagination across unrelated objects.
