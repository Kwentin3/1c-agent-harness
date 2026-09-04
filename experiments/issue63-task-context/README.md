# Issue #63 — frozen task-driven context comparison

This directory freezes the experiment **before** any scored lane starts.

- [`tasks.json`](tasks.json) contains only ordinary-language task inputs and fair-lane rules.
- [`ground-truth.json`](ground-truth.json) is the reviewer oracle. A fresh executor receives a physically separate source-only root and never receives this file, issue/PR history, or an earlier lane output.
- [`metrics.json`](metrics.json) defines complete accounting. Seed discovery and every later source fragment read count; a locator alone is not an already-read procedure body.

The frozen input is the admitted JetTr 1.0.3.1 snapshot declared in `tasks.json`. Both lanes receive the same task text and must preserve it unchanged.

The comparison has no native run, source mutation, persistent index/cache, daemon, network search, task-specific code path, or product integration. A final result may be `TASK-DRIVEN CONTEXT WINS`, `RG BASELINE REMAINS`, `TASK-DRIVEN CONTEXT FAIL`, or a precise external `BLOCKED`.

## Attempt 4 result — `NO MATERIAL WIN`

[`results.json`](results.json) is the accounting receipt for the only scored attempt. The preceding attempts were explicitly excluded before scoring: attempt 1 could not execute `rg`, attempt 2 had an admission preflight query in its ledger, and attempt 3 lacked the frozen `activeElapsed` unit.

Both scored arms used separate copies of the same admitted snapshot. All six copies retained manifest content SHA-256 `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`, which evidences no snapshot-content mutation. The complete scored ledger records only `search`, `read`, and `collect` operations; it is not an independent attestation about unrecorded native processes, cache use, or network activity.

| Route | Delivered bytes | Operations | Active elapsed |
| --- | ---: | ---: | ---: |
| `rg-only` | 1,050,461 | 63 | 94.610 s |
| `task-driven` | 3,960,069 | 59 | 309.703 s |

The task-driven route has **-276.98% byte reduction** (3.77× more bytes) and worse active elapsed. Thus it cannot meet the frozen Product PASS gate (at least 40% byte reduction and no worse active elapsed), irrespective of response-sufficiency scoring.

Response sufficiency is intentionally `INCONCLUSIVE`: the delegation durable result store was unavailable and the allowed live transcript truncates long final JSON. The report does not reconstruct or infer a task score from that partial evidence. This does not weaken the cost verdict: the immutable lane ledgers alone decisively rule out Product PASS.
