# Issue #20 low-cost prepared-tree native evidence

This package binds fresh native success and clean-repeat runs to committed candidate `a4e1509d44147229b4a515c7cd0013efba34762b` / tree `070ac2fe8e93fce22a8771989e56dad8e9531457`.

Both runs use the same supported `run-prepared` caller command, reach `runtime_contract_completed`, preserve the prepared source identity, remove only the five fixed current-invocation disposable targets, retain compact result/spec/evidence/logs, and require zero manual cleanup actions.

Storage measurements are externally sampled at 0.1-second intervals. The product result reports exact pre-compaction, removed and retained-excluding-result logical bytes; the external measurement reports lifecycle peak and actual post-command retained total.

- success peak: 224800941 bytes; retained: 43792 bytes
- repeat peak: 224800941 bytes; retained: 43792 bytes
- manual cleanup actions: 0 per run
- post-repeat native process scan: `[]`

Raw machine artifacts are gzip-wrapped and anchored by immutable decompressed SHA-256 constants in the validator. Sanitized companions are portable across checkout roots. The package manifest closes the exact tracked artifact set.

Verdict: **LOW-COST PREPARED-TREE LIFECYCLE PASS; TASK-SPECIFIC PREPARATION AND SEMANTIC ORACLE REMAIN OUTSIDE THE CAPABILITY.**
