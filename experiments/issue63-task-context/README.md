# Issue #63 — frozen task-driven context comparison

This directory freezes the experiment **before** any scored lane starts.

- [`tasks.json`](tasks.json) contains only ordinary-language task inputs and fair-lane rules.
- [`ground-truth.json`](ground-truth.json) is the reviewer oracle. A fresh executor receives a physically separate source-only root and never receives this file, issue/PR history, or an earlier lane output.
- [`metrics.json`](metrics.json) defines complete accounting. Seed discovery and every later source fragment read count; a locator alone is not an already-read procedure body.

The frozen input is the admitted JetTr 1.0.3.1 snapshot declared in `tasks.json`. Both lanes receive the same task text and must preserve it unchanged.

The frozen comparison protocol forbids native runs, source mutation, persistent index/cache, daemons, network search, task-specific code paths, and product integration. A final result may be `TASK-DRIVEN CONTEXT WINS`, `RG BASELINE REMAINS`, `TASK-DRIVEN CONTEXT FAIL`, or a precise external `BLOCKED`.

## Attempt 4 result — `TASK-DRIVEN CONTEXT FAIL`

[`results.json`](results.json) is the accounting receipt and [`responses.json`](responses.json) preserves the six final fresh-executor JSON answers used for the frozen sufficiency check. The preceding attempts were explicitly excluded before scoring: attempt 1 could not execute `rg`, attempt 2 had an admission preflight query in its ledger, and attempt 3 lacked the frozen `activeElapsed` unit.

Both scored arms used separate copies of the same admitted snapshot. All six copies retained manifest content SHA-256 `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`, which evidences no snapshot-content mutation. The complete scored ledger records only `search`, `read`, and `collect` operations; it is not an independent attestation about unrecorded native processes, cache use, or network activity.

| Route | Delivered bytes | Operations | Active elapsed |
| --- | ---: | ---: | ---: |
| `rg-only` | 1,050,461 | 63 | 94.610 s |
| `task-driven` | 3,960,069 | 59 | 309.703 s |

The recovered final JSON changes the qualitative result. `rg-only` passes frozen sufficiency on all three tasks. The task-driven route fails it on two: for supplier, the seam is explicitly an unconfirmed `candidate` at module line 1 rather than a confirmed `Posting` boundary; for sales, the required `Documents/BankPayment.xml` optional-date precedent is absent. These are `missingRequiredSurface` / unconfirmed-seam failures under [`metrics.json`](metrics.json), so the single experiment verdict is **`TASK-DRIVEN CONTEXT FAIL`**.

The cost evidence points in the same direction: task-driven has **-276.98% byte reduction** (3.77× more bytes) and worse active elapsed. Thus it cannot meet the frozen Product PASS gate (at least 40% byte reduction and no worse active elapsed), independently of the qualitative failure.
