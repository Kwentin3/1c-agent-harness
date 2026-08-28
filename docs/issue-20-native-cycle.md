# Native lifecycle runner (issue #20)

`scripts/native_cycle.py` is the single trusted-lab entrypoint used **after** a task has prepared its own BSL patch, runtime probe and semantic oracle. It owns only the native 1C lifecycle and process cleanup.

## Prerequisites

- Run from the repository root.
- Use the pinned training-edition profile already provisioned under `.local/platform/`.
- Prepare a physically separate tree under `.local/`; do not point the runner at the immutable source snapshot.
- The prepared tree must contain only directories and regular files, have no symlinks or symlinked path components, and have all write bits removed before invocation.
- Compute and bind the declared closed-tree SHA-256. There is intentionally no supported preparation/fingerprint CLI in this capability: freezing the prepared tree, invoking the internal identity calculation and authoring a new spec are manual caller-owned actions recorded in the cost ledger.
- Provide Linux procfs with readable `/proc/<pid>/task/<pid>/children` and support for `prctl(PR_SET_CHILD_SUBREAPER)`. The runner checks both before creating the run root and fails with a bounded preflight diagnostic when either prerequisite is unavailable.
- Choose a new, non-existing run root below `.local/runs/`.
- The task-specific probe must write a fresh receipt into the declared relative receipt path below the dedicated `runRoot/evidence/` directory and finish with the exact terminal line from `completeMarker`. The receipt cannot alias runner-owned logs, results, work copy, infobase or environment directories: every receipt path component is opened relative to a descriptor-bound `evidence` directory with `O_NOFOLLOW`, and the leaf must be a single-link regular file.

## Spec v1

```json
{
  "schemaVersion": 1,
  "inputTree": ".local/prepared/example",
  "inputTreeSha256": "<64 lowercase hex characters>",
  "runRoot": ".local/runs/example/run-1",
  "receipt": "evidence/receipt.txt",
  "completeMarker": "complete###true",
  "timeoutSeconds": 180
}
```

The schema is closed. Duplicate keys, extra fields, JSON booleans in integer fields, absolute paths, traversal, paths escaping the repository and run roots outside `.local/runs/` are rejected. `receipt` must be a file below the dedicated `runRoot/evidence/` directory. `schemaVersion` and `timeoutSeconds` must be actual JSON integers; `true`/`false` are not accepted as numbers.

Run it once:

```bash
python3 scripts/native_cycle.py run --spec .local/example-spec.json
```

There are no per-run executable, argv, environment or success-marker knobs. The Linux training profile is fixed in product code so the common runner cannot become an arbitrary command executor or patch framework.

## Owned lifecycle

The command performs:

1. fixed-profile and process-ownership preflight, then declared input identity/read-only checks;
2. exclusive creation of `runRoot`;
3. byte-identical copy check, followed by a separately reported post-`chmod` `loadTreeSha256` for the exact work-copy state passed to Designer;
4. isolated `HOME`, `TMPDIR` and XDG directories;
5. `CREATEINFOBASE` into `runRoot/ib`;
6. `DESIGNER /LoadConfigFromFiles ... /UpdateDBCfg`;
7. `ENTERPRISE` receipt polling;
8. descriptor-bound, symlink-free, single-link regular receipt reads; exact terminal-line marker; two-equal-hash stability check; and final receipt revalidation after process cleanup;
9. process-group cleanup plus Linux child-subreaper cleanup for descendants that escape into a new session;
10. input identity recheck and atomic `runRoot/result.json`.

A nominal result state is `runtime_contract_completed`. This means only that the native execution contract completed. It is deliberately not a business or semantic `PASS`.

Closed failure states include `precheck_failed`, `copy_failed`, `create_failed`, `load_failed`, `runtime_timeout`, `runtime_exited_before_completion`, `input_changed` and `internal_error`. The CLI returns non-zero on every failure and preserves completed-stage diagnostics when a run root exists. Runtime success and failure both publish a machine-readable `runtime` object after cleanup: process return, completion/failure kind, receipt state and exact presence/size/SHA-256 state for `run.log` and `run.result`. These are mechanical platform diagnostics, not a semantic oracle.

## Repeat and cleanup

For a repeat, the caller must manually freeze and fingerprint a new prepared input binding, author a new spec with a new run root, then invoke the same native command. The runner removes reconstruction of native command sequences and cleanup, but does not claim that preparation/binding is automated or low-cost. Do not reuse or pre-create a run root.

The runner does not delete artifacts. After evidence has been copied or inspected, cleanup is an explicit caller action limited to the exact disposable root the caller created. It must not target the source snapshot, manifest, platform, live infobase or another issue's run.

## Verification

Pure and fake-process contract tests:

```bash
python3 -m unittest tests.test_native_cycle -v
```

Full repository suite:

```bash
python3 -m unittest discover -s tests -v
```

The committed native evidence, measurements and limitations are in [`experiments/issue20-native-cycle-20260827/`](../experiments/issue20-native-cycle-20260827/README.md).
