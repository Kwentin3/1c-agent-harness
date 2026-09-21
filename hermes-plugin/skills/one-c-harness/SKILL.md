---
name: one-c-harness
description: "Use when investigating a 1C target through the terminal-bound companion."
version: 0.1.0
---

# 1C Harness terminal companion

Use this capability only after the Hermes terminal backend has selected the executor
and its project workspace. The plugin neither configures SSH nor accepts paths
outside that selected workspace.

1. Call `one_c_open` without arguments before configuration exploration.
2. Preserve the returned `snapshotRef` object exactly for `one_c_narrow_context` or
   `one_c_native_verify`.
3. To inspect platform errors, call `one_c_observe` with an inclusive **calendar**
   `start` and `end`, e.g. `2026-09-18T15:25:00`. They mean the local timezone that
   the executor reports in the response; do not calculate raw journal filename or
   minute/second tokens.
4. Use an exact returned group reference with `one_c_expand_observation`. It pages
   the same retained selection, not a journal that may have rotated since the query.

Observation details retain a platform event, calendar occurrence, an allowlisted
exception type when safely token-shaped, and deterministic fingerprints for redacted
descriptions. They do not reveal log body, paths, business values, credentials,
user names, connection strings, or Harness stack traces. Treat `partial` as an
incomplete source-coverage result, not a complete incident count; treat `blocked` or
`unavailable` as fail-closed. Do not replace a reference with a path or use shell/SSH
workarounds.
