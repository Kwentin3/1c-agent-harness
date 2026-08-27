# Blind metadata arm: minimal change and frozen evidence

Use this checklist for isolated evaluation arms that permit only a public task, an immutable split-source snapshot, and its manifest.

## Boundaries

- Read only the explicitly permitted task, output contract/schema, immutable snapshot, and its named manifest.
- Do not inspect oracle material, prior attempts, candidate outputs, issue narratives, history, network sources, or sibling arms.
- Write only inside the assigned arm directory. Keep the tracked repository, immutable snapshot, and manifest untouched.
- Do not run 1C when native validation is explicitly reserved for the downstream evaluation gate.

## Proven workflow

1. Record baseline tracked status and verify manifest identity, entry count, and complete snapshot closure with SHA-256.
2. Copy the entire snapshot to `work-copy/` with physical file separation (`cp -a` is suitable).
3. If immutable files were copied with read-only modes, temporarily enable writes **only in the work copy**. After the edit, restore every copied path's mode from the source tree so mode-only noise does not enter the diff.
4. Use direct source inspection to find the target metadata object and one local serialization example for the requested attribute semantics. Keep an exact record of only the source fragments actually used.
5. Apply the smallest metadata edit. Preserve encoding and line endings with byte-oriented replacement when the source uses CRLF.
6. Verify with standard-library parsing and semantic assertions:
   - changed XML is well formed;
   - exactly one intended object/attribute was added;
   - requested presentation, type, default, and use semantics are exact;
   - full source/work-copy hash comparison reports exactly the intended changed source files.
7. Generate `change.diff` using `git diff --no-index --binary -- <immutable-file> <work-copy-file>`. Exit code 1 is expected for a real difference; require empty stderr and freeze stdout byte-for-byte.
8. Produce the contract artifacts (`answer.json`, `context.json`, `metrics.json`, `HANDOFF.md`). Facts and inferences must be locator-covered; assumptions and native-validation unknowns must be explicit.
9. Context fragments must include complete source-file digests from the bound manifest and exact inclusive-range byte counts under the original encoding. Deduplicate overlapping ranges before totals.
10. Metrics must be observed. Use `null` with an explanation for uninstrumented values. If `derivedDiskBytes` excludes self-referential `metrics.json`, state the exclusion explicitly.
11. Remove temporary implementation, inspection, and verification helpers unless the symmetric output contract explicitly requires them. Evaluation arms should contain only the required artifacts and `work-copy/`.
12. After helper removal and any HANDOFF update, recompute derived-byte metrics, then perform one final pass: manifest closure, exact changed-file set, XML parse/semantics, byte-exact diff reproduction, required output set, and empty tracked status.

## Pitfalls

- `cp -a` preserves restrictive modes. A broad `chmod -R u+w` is acceptable only as a temporary work-copy operation; restore source modes before freezing evidence.
- A root-level no-index diff can include mode noise across thousands of files. Compare complete hash maps to establish the changed-file set, then diff only the intended file(s).
- Do not leave helper scripts in an arm merely because they were useful during construction. They alter output symmetry and derived-byte accounting.
- Updating `HANDOFF.md` after calculating `derivedDiskBytes` makes the metric stale. Finalize HANDOFF, remove helpers, and only then recompute the measured total.
- Native acceptance must remain an honest unknown when 1C execution is out of scope; XML parsing is not a substitute.
