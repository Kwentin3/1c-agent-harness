---
name: one-c-harness
description: "Use when investigating a 1C target through the terminal-bound companion."
version: 0.2.0
---

# 1C Harness terminal companion

Use this capability only after the Hermes terminal backend has selected the executor
and its project workspace. The plugin neither configures SSH nor accepts paths
outside that selected workspace.

## Configuration investigation

1. Call `one_c_open` without arguments before configuration exploration.
2. Preserve the returned `snapshotRef` object exactly for `one_c_narrow_context` or
   `one_c_native_verify`. Never replace it with a filesystem path.

## Technological-journal observations

1. Call `one_c_observation_info` first when the source interval, timezone, observed
   events or supported filters are unknown. Its interval describes only the bounded
   inspected data; `partial` and `complete: false` mean that more history may exist.
2. Call `one_c_observe` with an inclusive source-local calendar `start` and `end`,
   selected `events`, a small `limit`, and optional AND `filters`. Text filtering
   searches only the safe projected technical content, never hidden raw text.
3. Preserve the returned `observationRef`. If `groupsTruncated` is true, pass that ref
   to `one_c_expand_observation` with `offset` and `limit` to page the remaining groups.
4. Pass an exact `groupRef` to page that group's records. Each returned record has a
   `recordRef`; pass it with small `before` and `after` values to inspect neighbors.
   Neighbor scope is the retained filtered selection, not the unread journal, and
   time adjacency does not prove relation or cause.
5. Old refs address the retained immutable selection and expire after one hour. Never
   replace an expired ref with a fresh read while presenting it as the old evidence.

Observation details retain a platform event, calendar occurrence, allowlisted
technical tokens and bounded projected descriptions. Session-like values,
redacted-description fingerprints and record identities use selection-scoped keyed
tokens for comparison or addressing only inside one retained result; they are neither
identities nor cross-query filter keys. Raw bodies, paths, business values, credentials, user names and connection
strings are not returned. Treat `partial` as incomplete source
coverage, and `blocked` or `unavailable` as fail-closed. Do not use shell/SSH
workarounds for product observation.
