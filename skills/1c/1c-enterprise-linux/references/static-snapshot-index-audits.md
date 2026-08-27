# Static 1C snapshot index audits

Use this procedure when answering evidence questions from a hierarchical 1C configuration dump with a metadata index plus a BSL AST index.

## Workflow

1. Treat the snapshot as immutable. Write generated indexes only outside its tree, to a new path. Use absolute output paths when the command runs with the snapshot as its working directory; this avoids accidental relative writes under the read-only snapshot.
2. Run the metadata index with its documented named arguments. Accept a result only after exit 0, expected schema version, and `missing=0` or an explicit accounting of missing objects.
3. Parse JSON defensively: 1C-adjacent tools may emit UTF-8 with BOM (`utf-8-sig`).
4. Recheck every material metadata claim in `Configuration.xml` or the object XML. For root-object counts, count direct object entries and cite the contiguous line range or object locators.
5. Verify the AST CLI version, build its symbols index from the snapshot cwd, then use outline/search/usages only to narrow source inspection. When a frozen arm requires the AST database to remain in a declared cache, set `XDG_CACHE_HOME` to that cache for **every** AST command, run `ast-index db-path` before rebuilding, and verify that the returned database path is confined there. Do not assume the working directory controls the DB location.
6. Compare AST output with source declarations. If an outline begins partway through a module, a known declaration appears only as a content match, or exact source counts exceed indexed symbols, state the false negative and use source fallback.
7. For BSL public outlines, enumerate actual `Procedure`/`Function` declarations carrying `Export`; support multiline signatures and cite `path:line` for every member.
8. For duplicate event-handler names, keep three sets separate:
   - exact declarations (for example, `Procedure BeforeWrite(`),
   - exact-token textual matches,
   - candidate usages from the index.
   Never present usages or same-name matches as a call graph. Platform lifecycle handlers may have no explicit BSL caller.
9. For `ScheduledJob`, XML proves only static metadata such as `MethodName` and `Use`. It does not prove live enablement, runtime instances, successful scheduling, execution history, administrative blocking, or extension effects.
10. Once the requested facts are independently verified and the user says evidence is sufficient, stop rebuilds and broad searches and produce the requested output immediately.

## Frozen answer artifacts

- Record start epoch seconds before discovery and end epoch seconds after evidence collection; calculate `durationSeconds` with a tool rather than mentally.
- Keep all generated retriever databases, preflight output, answers, and verification artifacts under the arm's declared cache/output roots. Never reuse another arm's answers or oracle material.
- Model each fact, inference, assumption, and unknown as its own `{id, text}` claim. Use snapshot-relative locators with exact inclusive lines and `claimIds`; open the original XML/BSL for every material locator even when an index found it.
- Run the harness verifier against the finished answer. If verification fails, repair the answer and write the next verification result to a **new** filename so failed evidence is not overwritten.
- Count transcript tool operations honestly, including parallel subcalls and final verification/bookkeeping calls. If the metric is written before those final calls, budget only the exact known remaining calls; otherwise update and re-verify the artifact.
- Return artifact paths and hash only after the verifier reports `status: ok`.

## Reporting checklist

- Separate facts, inferences, unknowns, and locators.
- Report tool blind spots and source fallbacks explicitly.
- Report operationally relevant command errors concisely when the task asks for real operations and limitations; retain the successful recovery pattern, not a claim that the tool is broken.
- State whether snapshot integrity was hash-checked. If no post-run hash was taken, say only that no write command targeted the snapshot.
- Do not infer an object's purpose from its name.
