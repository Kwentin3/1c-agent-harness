# Native lifecycle runner (issue #20)

`scripts/native_cycle.py` is the single trusted-lab entrypoint used **after** a task has prepared its own BSL patch, runtime probe and semantic oracle. It owns only the native 1C lifecycle and process cleanup.

## Prerequisites

- Run from the repository root.
- Use the pinned training-edition profile already provisioned under `.local/platform/`.
- Prepare a physically separate task-specific tree; do not point either command at the immutable source snapshot.
- The supported `run-prepared` path requires that tree below `.local/prepared/`. It may be writable or already read-only, but it must contain only directories and regular files and have no symlinks or symlinked path components. The command creates and freezes a separate generated copy; it never changes the supplied tree.
- The lower-level `run --spec` path remains available for an already frozen binding. Its input must have all write bits removed and its closed-tree SHA-256 must already be declared in the spec.
- Provide Linux procfs with readable `/proc/<pid>/task/<pid>/children` and support for `prctl(PR_SET_CHILD_SUBREAPER)`. The runner checks both before creating the run root and fails with a bounded preflight diagnostic when either prerequisite is unavailable.
- Choose a new, non-existing run root below `.local/runs/`.
- The task-specific probe must write a fresh receipt into the declared relative receipt path below the dedicated `runRoot/evidence/` directory and finish with the exact terminal line from `completeMarker`. The receipt cannot alias runner-owned logs, results, work copy, infobase or environment directories: every receipt path component is opened relative to a descriptor-bound `evidence` directory with `O_NOFOLLOW`, and the leaf must be a single-link regular file.

## Supported prepared-tree path

The task-specific probe uses the standard 1C global `LaunchParameter` as its receipt file path. One command owns freeze, closed-tree fingerprinting, unique spec/run-root/receipt binding and the accepted lifecycle executor:

```bash
python3 scripts/native_cycle.py run-prepared \
  --input-tree .local/prepared/example \
  --complete-marker 'complete###true' \
  --timeout-seconds 180
```

`run-prepared` passes the generated receipt path to `ENTERPRISE` through `/C`. The same exact caller argv can be repeated: every invocation creates a fresh root below `.local/runs/native-cycle/` and prints a repository-relative `resultPath`. The persisted result binds the prepared source before/after, generated frozen input identity, generated spec, generated `/C` runtime argv, executor copy and post-`chmod` Designer load tree. After the terminal source recheck it removes the current invocation's reproducible heavy trees and retains the compact result/evidence record. It does not parse task-specific receipt semantics.

## Frozen spec v1

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

### Headless probe boundary

A successful Designer load is not proof that a task-specific managed-client probe compiled or executed at `ENTERPRISE` runtime. In particular, a probe placed after `StandardSubsystemsClient.OnStart()` can remain unreachable in headless startup and emit no receipt. For the verified early-`OnStart`/server-call preparation pattern, case-isolated receipt observations, and the rule that a failed frozen attempt requires a fresh contract rather than a retry, see [Headless probe observability (issue #37)](issue-37-headless-probe-observability.md).

## Repeat and bounded current-invocation cleanup

For a repeat through the supported path, invoke the exact same `run-prepared` command again. The command generates a new frozen input, fingerprint, spec, run root, receipt binding and result location without caller edits. The task-specific preparation that produced the supplied tree remains outside the capability.

For the lower-level `run --spec` path, the caller still owns freezing/fingerprinting and a fresh spec. Do not reuse or pre-create a native run root.

After source revalidation, `run-prepared` automatically removes only five paths constructed from its current generated invocation: `frozen-input`, `run/work-copy`, `run/ib`, `run/home` and `run/tmp`. It retains `spec.json`, `run/result.json`, `run/evidence/` and `run/logs/`, including failure diagnostics. The result distinguishes configured targets from paths verified removed, and reports exact pre-compaction, removed and retained-excluding-result logical bytes, cleanup duration and zero manual cleanup actions. The final evidence ledger separately records sampled lifecycle peak and actual post-command retained total. Cleanup failure is fail-closed and persisted.

There is no cleanup command, glob, retention count or user-supplied deletion path. Prepared input, immutable snapshot, manifest, platform, live infobase, sibling invocation roots and older issue roots are never implicit targets. The lower-level `run --spec` path preserves its existing artifact behavior; bounded compaction belongs only to the generated `run-prepared` ownership boundary.

An invocation-owned Unix-domain socket left in generated HOME is removed as a socket leaf. Symlinks, FIFOs and device nodes remain fail-closed cleanup errors.

## Verification

Pure and fake-process contract tests:

```bash
python3 -m unittest tests.test_native_cycle -v
```

Full repository suite:

```bash
python3 -m unittest discover -s tests -v
```

The accepted product-core evidence is in [`experiments/issue20-native-cycle-20260827/`](../experiments/issue20-native-cycle-20260827/README.md). Fresh bounded-storage success/repeat evidence and sampled peak/retained measurements are in [`experiments/issue20-low-cost-native-cycle-20260828/`](../experiments/issue20-low-cost-native-cycle-20260828/README.md).
