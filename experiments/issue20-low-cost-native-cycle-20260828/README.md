# Issue #20 low-cost prepared-tree native evidence

This package binds fresh native success and clean-repeat runs to committed candidate `a4e1509d44147229b4a515c7cd0013efba34762b` / tree `070ac2fe8e93fce22a8771989e56dad8e9531457`.

Both runs use the same supported `run-prepared` caller command, reach `runtime_contract_completed`, preserve the prepared source identity, remove only the five fixed current-invocation disposable targets, retain compact result/spec/evidence/logs, and require zero manual cleanup actions.

Storage measurements are externally sampled at 0.1-second intervals. The product result reports exact pre-compaction, removed and retained-excluding-result logical bytes; the external measurement reports lifecycle peak and actual post-command retained total.

Common-code cost uses the full issue #20 low-cost goal-loop boundary: base `c4e40ff96a36c709cab46df651ee0564647f3146` to native runner candidate `a4e1509d44147229b4a515c7cd0013efba34762b`. The exact measured delta is `+530/-8` for `scripts/native_cycle.py` and `+681/-0` for `tests/test_native_cycle.py`. The narrower bounded-storage correction from `a352741…` is reported separately and is not presented as the full PR cost.

The full runner increase is justified by reproduced gaps: one-command preparation/binding, persisted failure/result location and source recheck, receipt/process races, and bounded fail-closed current-invocation storage. `run_cycle()` remains the sole lifecycle implementation; no semantic oracle, arbitrary command surface, general cleaner, cross-run retention framework, GUI, RAG/MCP or deployment layer was added.

- success peak: 224800941 bytes; retained: 43792 bytes
- repeat peak: 224800941 bytes; retained: 43792 bytes
- manual cleanup actions: 0 per run
- post-repeat native process scan: `[]`

Raw machine artifacts are gzip-wrapped and anchored by immutable decompressed SHA-256 constants in the validator. Sanitized companions are portable across checkout roots. The package manifest closes the exact tracked artifact set.

Verdict: **LOW-COST PREPARED-TREE LIFECYCLE PASS; TASK-SPECIFIC PREPARATION AND SEMANTIC ORACLE REMAIN OUTSIDE THE CAPABILITY.**
