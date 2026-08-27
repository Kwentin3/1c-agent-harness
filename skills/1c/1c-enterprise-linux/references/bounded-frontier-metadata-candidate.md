# Blind bounded-frontier metadata candidate workflow

Use this for a frozen split-source 1C metadata task where solution leakage is forbidden and the candidate must be independently auditable.

## Protocol

1. **Bind before discovery.** Record the public task ID and SHA-256, immutable snapshot root, manifest path/digest, manifest entry count, and content ID. Verify manifest digest, every covered file, and closed-set equality before reading source.
2. **Honor the blindness boundary.** Read only the public task, identified snapshot, and explicitly allowed manifest. Do not inspect oracles, prior attempts, reports, baseline output, history, network results, or solution-oriented instructions.
3. **Derive search terms from public wording.** Log each term, scope, hit count, selected hits, and rejection rationale. Use direct filesystem search only; do not use indexes, RAG, or source parsers for discovery.
4. **Expand only through the bounded frontier.** Start with the likely owning metadata object. Read only enough owning metadata and peer/sibling attribute serialization to prove:
   - correct owner;
   - property type and default serialization;
   - item/folder use semantics;
   - correct `ChildObjects` placement/order;
   - excluded form/module/runtime scope.
5. **Record every used fragment.** For each fragment store `path`, inclusive line range, inclusive byte range, fragment SHA-256, rationale, and exact claim supported. Treat the immutable source as authoritative.
6. **Run a sufficiency gate before editing.** Require explicit results for owner, requested semantics, serialization scope, collateral-edit exclusion, and native target. If any material fact remains unsupported, request the next narrow layer or stop as `PARTIAL/BLOCKED`.
7. **Copy physically, then edit minimally.** Create a complete writable work copy under the designated arm, preserve file bytes/line endings, and modify only the owning metadata file. Generate UUIDs independently; never infer an expected UUID.
8. **Freeze evidence.** Produce a binary-safe `git diff --no-index --binary` against the immutable source plus machine-readable answer/context/metrics and a concise handoff. Record observed counts and hashes, not estimates.
9. **Final continuity gate.** Reverify the immutable manifest and closed set, work-copy file-set equality, exact changed-file closure, XML well-formedness, artifact JSON validity, and tracked Git cleanliness. If native 1C is an evaluator-only gate, do not run it; label it deferred rather than passed. Make the work copy and evidence read-only only after this gate, then do not inspect candidate files again.

## Useful evidence pattern for Boolean Catalog attributes

When the target object lacks a direct peer attribute, inspect a narrow peer Catalog attribute block. Confirm these independently rather than guessing:

- direct `Attribute` membership under the Catalog's `ChildObjects`;
- `<v8:Type>xs:boolean</v8:Type>`;
- explicit false serialization when required: `<FillValue xsi:type="xs:boolean">false</FillValue>`;
- `<Use>ForItem</Use>` for item-only semantics.

Do not add forms merely to expose the attribute when the contract says metadata only.

## Pitfalls

- File-name search can succeed when text search misses because XML line endings/encoding or search-tool behavior differs. Log the miss, pivot to direct bounded file-name discovery, and continue without broadening into forbidden sources.
- `git diff --no-index` returns exit status 1 when differences exist; treat that as expected only after confirming the diff file is non-empty and contains exactly the intended path.
- XML parsing is appropriate for final well-formedness validation even when parsers are forbidden for discovery; record this distinction.
- A well-formed XML result is not native Designer acceptance. Report the native gate honestly as deferred when the task reserves it for evaluation.
