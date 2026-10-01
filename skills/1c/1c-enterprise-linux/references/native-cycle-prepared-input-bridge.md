# Native-cycle prepared-input bridge

Use this project-specific note when a 1C native task needs both an auditable task-owned run root and the existing `native_cycle.py run-prepared` lifecycle.

## Verified admission rule

`native_cycle.py run-prepared` rejects an `--input-tree` outside `.local/prepared/` during static precheck, before `CREATEINFOBASE`, Designer, Xvfb, or Enterprise starts. Treat this as **zero platform attempts** and never call it a RED, GREEN, or canary runtime result.

## Compatible layout

Freeze these paths before allocating a native budget:

```text
.local/runs/<issue>/<nonce>/
  evidence/                 # contract, raw logs, receipts, hashes, cleanup facts
.local/prepared/<issue>-<nonce>/
  input-tree/               # disposable, runner-admitted copy only
```

The prepared tree is not canonical input and is not the evidence root. Bind it to the run root by recording: canonical snapshot identity; prepared-tree identity/hash; exact allowed production/probe paths; runner invocation; cleanup owner; and a post-run canonical recheck.

## Admission decision

- If the task contract explicitly allows the disposable prepared bridge, create it under `.local/prepared/`, use the existing runner, and delete only that task-owned bridge during cleanup.
- If the contract requires every temporary file to live exclusively under `.local/runs/...`, the two requirements conflict. Stop `CONTEXT BLOCKED` before a native invocation; do not move the canonical tree, change runner policy, or create a wrapper merely to bypass the admission rule.

This note governs runner-layout compatibility only. It does not prove BSL compilation, client/server transport, or business behavior.
