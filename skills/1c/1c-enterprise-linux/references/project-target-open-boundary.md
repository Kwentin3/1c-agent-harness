# Project-target open boundary for 1C snapshots

Use this pattern when a fresh agent must turn one project-declared 1C configuration source into a stable `SnapshotRef` without learning platform/runtime internals.

## Boundary map

```text
project-owned source declaration
→ source/materialization coordinator
→ the existing authoritative snapshot admission function
→ atomically published retained target
→ data-only SnapshotRef
→ context or mutation consumers
```

Keep admission as the single owner of manifest closure, hashes, tree safety, configuration identity, and read-only checks. The coordinator may sequence source validation, an optional materializer, staging, admission, publication, and cleanup; it must not duplicate XML/BSL semantics or business logic.

## Minimal v1 behavior

- Reuse an existing admitted target without requiring the original source or native runtime.
- Admit a declared complete hierarchical export without launching 1C.
- Materialize a declared CF through a fixed repository-owned materializer; only its already-provisioned 1C runtime and GUI dependencies are external.
- Return only stable data: status, action, source identity, and a repository-relative snapshot root/manifest/content identity/configuration. Exclude timestamps, absolute paths, run IDs, Git/Hermes details, native argv, and runtime directories.
- Return one typed blocker (`source_missing`, `source_mismatch`, `unsupported_source`, `materializer_unavailable`, `materialization_failed`, or `snapshot_invalid`) with a short non-secret message. Never return a traceback or raw exception path.

## Atomic retained publication

1. Require the retained container to be a strict child of a dedicated persistent namespace such as `.local/targets/`, disjoint from disposable `.local/runs/` and `.local/prepared/`.
2. Serialize cooperating opens with `flock` on the already-open retained-base directory. This needs no daemon, lock database, or stale lock-file recovery.
3. Recheck the project contract after acquiring the lock.
4. Build a randomly named sibling staging container. Keep snapshot, manifest, and source binding inside that one container.
5. Validate source identity before copying/materialization and again afterward. A local materializer must receive only the immutable source, a new output path, and an owned work root; launch it in its own process session and fail if it times out, exits nonzero, or leaves its process group alive.
6. Generate the manifest from staged bytes, freeze write bits, and run the authoritative admission against staging.
7. Store a deterministic source-binding record alongside the snapshot and manifest. Bind at least `sourceIdentity` and `snapshotContentId`; otherwise a later contract edit can relabel the origin of an old retained target.
8. Verify the container has exactly the declared top-level entries, recheck contract/source continuity, then rename the whole staging container to the final target in one filesystem operation.
9. Re-run admission and binding checks from the published path before returning `ready`.
10. On any failure, remove only the owned staging/work tree. Never repair or overwrite an existing invalid retained target.

## CF materializer ownership

The **algorithm** that opens a declared CF belongs in a repository-owned module, not in a user-supplied `.local/` script. Keep the implementation narrow and fixed:

```text
CREATEINFOBASE → DESIGNER /LoadCfg <immutable-cf>
→ DESIGNER /DumpConfigToFiles <new-output> -Format Hierarchical
```

The runtime remains an external prerequisite: a supported 1C executable, Xvfb and required libraries/font configuration must already be provisioned. The harness must not download a distribution, accept a licence, install packages or use elevated permissions merely because `open` was called.

The materializer owns the fixed argv construction, a separate process session per native step, timeout and surviving-process-group failure handling, and verification of **each** process exit and exact `/DumpResult=0`. It receives only the immutable source plus new owned output/work paths. The surrounding coordinator owns source revalidation, manifest generation, the single authoritative admission call, atomic retained publication, and removal of the whole owned staging/work tree. A missing runtime is a typed external blocker; a missing external materializer script is a design defect, not a blocker.

## Tests that prove the seam

- Hierarchical cold open returns `materialized`; a tiny independent consumer reads `Configuration.xml` using only `snapshot.root`.
- Two warm opens return byte-identical stdout and the same `SnapshotRef`; source may be absent and file inode/mtime remains unchanged.
- A 5,000+-file warm fixture stays within the declared latency budget.
- Missing, mismatched, unsupported, symlinked, hard-linked, malformed, and corrupted inputs produce one blocker with no partial target.
- A zero-exit materializer that produces no valid snapshot is `materialization_failed`, not success or generic admission failure.
- Two parallel cold opens publish one complete target and invoke the materializer once.
- Rebinding the project contract to another source identity makes reuse fail closed.
- Existing run/prepared cleanup functions remove their owned state while the retained target and manifest remain unchanged.
- Sabotage at least one provenance control: remove the source-binding check and confirm the rebinding test fails.

## Pitfalls

- Putting retained snapshots under a run directory makes ordinary cleanup a product-data deletion path.
- Publishing snapshot and manifest as separate sibling renames exposes a partial ready-looking state; rename one containing directory instead.
- Treating a manifest hash as source provenance allows coordinated relabeling; retain a separate exact source binding.
- Emitting `str(exc)` can leak machine paths and unstable details. Map internal exceptions to closed reason codes and bounded messages.
- A successful materializer process does not prove output validity. Admission must run on produced bytes before publication.
- CI check metadata may bind the PR head while `actions/checkout` uses a synthetic merge commit. Compare the checked-out merge tree to the PR-head tree before claiming exact-tree CI; do not call it literal exact-head-commit execution.
