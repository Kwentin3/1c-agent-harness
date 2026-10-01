# SnapshotRef inspector: exact-head read-only canary

Use this reference when a bounded read-only inspector consumes a retained hierarchical 1C snapshot on a remote executor. It is a static evidence lane: do **not** launch 1C, materialize a CF, or modify the canonical snapshot.

## Preconditions

1. Freeze the candidate commit and tree, and create a task-owned remote worktree at that exact commit.
2. If the worktree needs the retained target, copy only the already admitted target directory into the worktree's ignored `.local/targets/...`; never point the public inspector at the source worktree's raw snapshot.
3. Before the run, compare the copied and source `snapshot.manifest` digests. The copied target must pass the existing authoritative admission routine.
4. Invoke the project command with an explicit repository root. A remote SSH login's `cwd` is not the task worktree:

   ```bash
   python3 "$WT/scripts/project_target.py" open --repo-root "$WT" > "$E/snapshot-ref.json"
   ```

## Minimal receipt

For each frozen object, run the inspector twice through only the emitted `SnapshotRef` and compare output bytes:

```bash
PYTHONWARNINGS=error::DeprecationWarning \
  python3 "$WT/scripts/object_context.py" inspect \
    --repo-root "$WT" --snapshot-ref "$E/snapshot-ref.json" \
    --object "Document.Example" > "$E/one.json"
# repeat identically, then cmp -s one.json repeat.json
```

Capture all of:

- exact Git HEAD and tree;
- `open` result (`status=ready`, normally `action=reused`);
- manifest SHA-256 before and after, byte-identical;
- repeated JSON byte equality, output sizes, and durations;
- no-new-native-process evidence before/after.

For process evidence, filter exact command names (for example `1cv8t`, `1cv8`, `Xvfb`) from `ps -eo pid=,comm=`. Avoid a `pgrep -af` pattern that can match the probe's own shell command.

If the executor is unavailable, record the bounded connectivity failure and preserve the local candidate; do not recreate a plausible remote receipt from local data. Once access returns, continue from the retained worktree/assets and run only the unfinished static canary.

## Cost accounting

Measure the whole agent route, not just inspector JSON. An inspector locator identifies where to read; it does not replace the procedure body, patch boundary, or an external precedent. For every task, count required follow-up reads and sum all bytes/operations. Compare the aggregate route only against an aggregate baseline. Do not multiply a baseline that already covers all evaluation tasks, and do not omit required reads to meet a threshold. If the honest route misses the product threshold, report `NO MATERIAL WIN` while preserving the useful read-only evidence.
