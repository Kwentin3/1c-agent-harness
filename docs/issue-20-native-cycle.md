# Native lifecycle runner (issue #20)

`scripts/native_cycle.py` is the single trusted-lab entrypoint used **after** a task has prepared its own BSL patch, runtime probe and semantic oracle. It owns only the native 1C lifecycle and process cleanup.

## Prerequisites

- Run from the repository root.
- Use the pinned training-edition profile already provisioned under `.local/platform/`.
- Prepare a physically separate tree under `.local/`; do not point the runner at the immutable source snapshot.
- The prepared tree must contain only directories and regular files, have no symlinks or symlinked path components, and have all write bits removed before invocation.
- Compute the declared closed-tree SHA-256 with the same `tree_identity` function used by the runner; it binds relative paths, entry types, modes, empty directories and file bytes.
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

1. preflight and declared input identity/read-only checks;
2. exclusive creation of `runRoot`;
3. byte-identical copy to `runRoot/work-copy` and copy identity check;
4. isolated `HOME`, `TMPDIR` and XDG directories;
5. `CREATEINFOBASE` into `runRoot/ib`;
6. `DESIGNER /LoadConfigFromFiles ... /UpdateDBCfg`;
7. `ENTERPRISE` receipt polling;
8. descriptor-bound, symlink-free, single-link regular receipt reads; exact terminal-line marker; two-equal-hash stability check; and final receipt revalidation after process cleanup;
9. process-group cleanup plus Linux child-subreaper cleanup for descendants that escape into a new session;
10. input identity recheck and atomic `runRoot/result.json`.

A nominal result state is `runtime_contract_completed`. This means only that the native execution contract completed. It is deliberately not a business or semantic `PASS`.

Closed failure states include `precheck_failed`, `copy_failed`, `create_failed`, `load_failed`, `runtime_timeout`, `runtime_exited_before_completion`, `input_changed` and `internal_error`. The CLI returns non-zero on every failure and preserves completed-stage diagnostics when a run root exists.

## Repeat and cleanup

For a repeat, prepare a new input binding and spec with a new run root, then invoke the same command. Do not reuse or pre-create a run root.

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
