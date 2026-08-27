# Freezing a minimal synthetic 1C metadata task

Use this pattern when a historical change is too broad for a focused split-source metadata benchmark and the selection phase must not run native 1C validation.

## Goal

Freeze the smallest meaningful task: add one business attribute to one existing metadata object in an immutable hierarchical configuration snapshot. The later evaluator, not the selector, runs native Designer acceptance.

## Procedure

1. **Bind the immutable input.** Identify the snapshot by the SHA-256 of its sibling file manifest and its manifest entry count. Verify the manifest before freezing artifacts. Never modify or dump Designer output over the snapshot.
2. **Choose a stable owner.** Prefer an existing business object whose meaning follows directly from user wording and whose owner XML has a conventional `ChildObjects` container. Avoid changes requiring registration, forms, modules, runtime behavior, or multiple source files.
3. **Keep the public contract narrow.** Limit `public-task.json` to task ID, snapshot root/identity, business wording, acceptance, and blindness. Business wording may identify the real-world entity and presentation, but must not disclose the exact source path, XML insertion recipe, internal UUID, or oracle-only distractors.
4. **Make the oracle exact.** Record the qualified metadata owner, exact child kind/internal name/type/default/use, expected changed-file set, deterministic UUID policy, static acceptance, native acceptance, and dangerous distractors.
5. **Use deterministic UUIDs.** When the child requires a UUID, freeze UUIDv5 with a stated namespace and canonical string such as `<task-id>|<qualified-metadata-child>`. Record both policy and expected UUID privately.
6. **Separate selection from native evaluation.** State honestly that native validation was not run. Freeze `/LoadConfigFromFiles` and `/UpdateDBCfg` as later gates in a disposable infobase. Do not run Enterprise/runtime probes for a metadata-only task.
7. **Explain synthetic selection.** In `selection-report.md`, quantify why the available historical candidate was too broad and explain how the synthetic task isolates metadata location, valid XML construction, serialization preservation, and native platform acceptance.
8. **Close the package.** Create `SHA256SUMS` over `public-task.json`, `oracle.json`, and `selection-report.md`, excluding the checksum file itself. Verify with `sha256sum -c SHA256SUMS` from the package directory.

## Dangerous distractors to encode privately

- Implementing runtime enforcement, posting logic, forms, BSL, registers, constants, or functional options.
- Modeling a direct owner attribute as an additional-property definition or tabular-section row.
- Editing `Configuration.xml` or `ConfigDumpInfo.xml` when the child belongs inside an already registered owner.
- Letting Designer reserialize the source during selection, which can normalize versions, namespaces, translations, properties, BOMs, or line endings.
- Copying prior validation workspaces that contain collateral reserialization changes.
- Claiming native success when native commands were intentionally not run.

## Verification checklist

- Snapshot manifest check passes before and after artifact creation.
- Public JSON has exactly the allowed top-level contract fields and no private path/XML/UUID leakage.
- Oracle contains every exact evaluator requirement and the source file's baseline SHA-256.
- Selection report explicitly says native validation was not run.
- `sha256sum -c SHA256SUMS` passes from the package directory.
- Final handoff follows the task's disclosure boundary; if asked for task text and hashes only, return only those and no oracle details or paths.
