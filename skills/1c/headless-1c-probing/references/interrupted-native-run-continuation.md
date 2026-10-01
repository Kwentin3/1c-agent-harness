# Continuing a native run after coordinator interruption

Use this when an agent/session timeout interrupts the SSH command that launched an already-admitted native run, but the remote executor and task-owned roots persist.

## Preserve the in-flight attempt

1. Do **not** immediately relaunch, kill, or classify the task as failed. The SSH client can disappear while the remote runner and 1C children continue.
2. Read the executor directly and identify the exact runner PID/argv, invocation root, prepared input, current lifecycle stage, and owned `1cv8t`/`Xvfb` processes.
3. If the existing runner is healthy and still within its declared timeout, let that same attempt finish. Poll its exact process or result path; do not spend a duplicate attempt.
4. After it exits, inspect the runner-owned `result.json`, raw receipt, retained logs, compaction record, and input-before/input-after identities. A coordinator timeout is not the native outcome.
5. If the parent shell was interrupted after the runner completed, perform only the skipped mechanical tail: copy portable evidence, run the already-frozen oracle, update the run ledger, and remove the exact task-owned prepared root. Do not rewrite the semantic contract or production patch.

## Acceptance identity repair

A fresh runner directory and stable receipt prevent accidental reuse, but they do not by themselves satisfy a contract that explicitly requires `runId`, `caseId`, and `nonce` in request and response.

- Bind all three identifiers into task-specific instrumentation **before** the final acceptance lanes.
- Emit them from the server-side receipt and compare an exact receipt dictionary against the frozen request.
- Require canonical UUIDv4 strings, distinct values within a lane, and different values across clean repeat lanes.
- Negative tests should reject at least: a foreign receipt identity, an identity collision/nonce echo, a partial receipt, and a business-wrong receipt.
- If earlier RED/GREEN lanes lack explicit identities, retain them honestly for chronological business evidence only. Run new clean identity-bound GREEN lanes rather than retroactively upgrading the old evidence.

## Cleanup

Copied snapshots may contain read-only directories. For an exact task-owned rejected/prepared root, first prove no owned process remains, grant owner `rwx` to directories only as needed, then remove that root. Preserve compact runner evidence until it has been copied and hash-checked. Never apply this cleanup to the canonical snapshot, platform tree, unknown roots, or another issue's evidence.
