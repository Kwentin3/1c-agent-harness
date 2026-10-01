# Issue #73 — first live read-only Runtime Diagnostics slice

## Chosen source

The first provider is `native_run_history`. It reads only retained result receipts
from previous native 1C training runs made by the existing Harness on the selected
executor. It does not start 1C, call a cluster, open a network connection, change a
file, or create a monitoring service.

This is real historical runtime evidence, not a synthetic fixture. A current
inventory of the executor found 28 valid retained `native-cycle` result receipts:
21 `runtime_contract_completed`, 3 `runtime_exited_before_completion`, and 4
`runtime_timeout`. Their current timestamped filesystem metadata supplies the
available history window. This source cannot explain a root cause or describe a
currently running session; it proves only the retained native-run outcomes.

RAC/RAS, TechLog, registration-log, and an existing monitoring endpoint were not
present in the executor inventory, so this provider is the smallest available
read-only source. No source setup or fallback collector is added.

## Route

```text
Hermes terminal dispatch
  -> task-local exact `one-c-harness` companion (existing terminal boundary)
  -> investigate / expand
  -> native_run_history provider
  -> retained native-cycle result receipt
```

The provider creates opaque record IDs from the receipt bytes. It maps only a
fixed safe subset to the normalized record: result status, total duration, and the
receipt file modification time. Absolute paths, command arguments, environment,
stack traces, and arbitrary receipt fields never cross the provider boundary.

The executor currently lacks `ensurepip`/`venv`, so this canary invokes the exact
companion source through its task-local Python module instead of altering the host
or downloading dependencies. This still uses the existing terminal/companion
boundary; a future persistent executor installation is packaging work, not a
second transport or provider.

## Model-facing operations

`investigate` requires one timezone-aware incident window, a bounded non-empty
focus list and `limit <= 20`. It returns:

- the number of records and status counts;
- a deterministic finding for every retained non-success status;
- one evidence group per status, with opaque record refs;
- no causal explanation.

A finding is `derived_deterministically`: it is a count and maximum duration over
its evidence records. It does not assert why a timeout or early exit happened.

`expand` accepts exactly one `findingRef` or `evidenceRef` and a bounded limit. It
returns the selected normalized records and their safe source representation. An
unknown or expired reference returns a bounded blocker; it never reruns a different
query or exposes a path.

## Scope deliberately excluded

- live cluster/session diagnostics;
- RAC, TechLog, registration-log, Prometheus, database or OS provider;
- monitoring storage, daemon, scheduler, dashboard, MCP, alerting or remediation;
- modification of 1C, the canonical CF/snapshot, TechLog configuration, or executor
  runtime;
- a runtime-to-code bridge: retained native receipts have no stable metadata/job
  identity, so no heuristic source match is attempted.

## Reproduction

Run the focused contract tests:

```bash
python3 -m unittest -v tests.test_native_run_history tests.test_runtime_diagnostics tests.test_companion
```

The executor E2E receipt is retained as
[`issue-73-runtime-diagnostics-live-receipt.json`](issue-73-runtime-diagnostics-live-receipt.json).
It was produced only from its existing task-owned runtime history through the
exact companion source in an isolated worktree. It contains the bounded result
only: 28 records, one finding and a three-record expand response.
