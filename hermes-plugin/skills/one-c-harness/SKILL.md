---
name: one-c-harness
description: "Use when investigating a 1C target through the terminal-bound companion."
version: 0.1.0
---

# 1C Harness terminal companion

Use this capability only after the Hermes terminal backend has selected the executor and its project workspace. The plugin neither configures SSH nor accepts paths outside that selected workspace.

1. Call `one_c_open` without arguments.
2. Preserve the returned `snapshotRef` object exactly.
3. Use `one_c_narrow_context` with that exact object for bounded, cited exploration.
4. Use `one_c_native_verify` only with project-relative task artifacts and an admitted `snapshotRef`.

Treat any `blocked` result as fail-closed. Do not replace `snapshotRef` with a path, do not invoke a shell/SSH workaround, and do not use this capability to change the source configuration or live information base.
