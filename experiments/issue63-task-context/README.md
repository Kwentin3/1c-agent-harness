# Issue #63 — frozen task-driven context comparison

This directory freezes the experiment **before** any scored lane starts.

- [`tasks.json`](tasks.json) contains only ordinary-language task inputs and fair-lane rules.
- [`ground-truth.json`](ground-truth.json) is the reviewer oracle. A fresh executor receives a physically separate source-only root and never receives this file, issue/PR history, or an earlier lane output.
- [`metrics.json`](metrics.json) defines complete accounting. Seed discovery and every later source fragment read count; a locator alone is not an already-read procedure body.

The frozen input is the admitted JetTr 1.0.3.1 snapshot declared in `tasks.json`. Both lanes receive the same task text and must preserve it unchanged.

The comparison has no native run, source mutation, persistent index/cache, daemon, network search, task-specific code path, or product integration. A final result may be `TASK-DRIVEN CONTEXT WINS`, `RG BASELINE REMAINS`, `TASK-DRIVEN CONTEXT FAIL`, or a precise external `BLOCKED`.
