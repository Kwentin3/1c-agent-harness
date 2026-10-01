# Issue #75 — platform-authored 1C technological-journal observations

## Source and time semantics

The single source is the **1C:Enterprise technological journal** emitted by the
installed Linux training runtime **8.5.1.1150** in an isolated file-mode Jet run.
It is not a Harness receipt, runner exit code, or synthetic fixture.

The supported platform grammar is deliberately narrow:

- the platform documentation defines each log file as `yymmddhh.log`, with the
  file name carrying its one-hour interval: [1C:Enterprise Administrator Guide,
  “Technological log structure”](https://kb.1ci.com/1C_Enterprise_Platform/Guides/Administrator_Guides/1C_Enterprise_8.3.23_Administrator_Guide/6._Infobase_administration/6.14._Technological_log/6.14.4._Technological_log_structure/);
- the verified 8.5.1.1150 files use `mm:ss.ffffff-pid,EVENT,` at event start.

Harness combines file date/hour and event minute/second into a calendar occurrence.
It never uses file mtime. The executor supplies both `ONE_C_HARNESS_TECHLOG_ROOT`
and `ONE_C_HARNESS_TECHLOG_TIME_ZONE`; this canary verified `UTC`. A model asks for
inclusive local-source `start` and `end` such as `2026-09-18T15:25:00`, not raw file
names or source tokens. If the root or timezone is missing/invalid, the source is
`unavailable`; no silent timezone conversion or invented UTC occurs.

## Safe diagnostic meaning

`observe` groups `EXCP` records by event plus a deterministic error signature.
`expand_observation` returns a stable page from exactly the retained selection. A
record includes:

- platform event and calendar `occurredAt` (with the configured source offset);
- an allowlisted compact `Exception` technical token when the field is present and
  token-shaped; and
- a bounded projection of `Descr` plus its deterministic fingerprint.

The reader follows the documented text-format quoting rule, so commas and line breaks
inside a quoted property remain part of the same description. Expansion normalizes
whitespace and returns at most 480 characters. Credential/identity/business-value
assignments, paths, endpoints, addresses and opaque long identifiers are replaced by
explicit `<redacted:...>` markers; `redacted` and `truncated` say whether either loss
occurred. The projection is deliberately scoped to the authorized training TechLog
format, not presented as a universal sanitizer for arbitrary text. Raw record body,
unselected properties and Harness stack traces are never returned.

## Bounded collection and retained evidence

One observation is capped at 24 candidate files, 96 discovered paths, 256 KiB input,
2 seconds wall time, 8 KiB per source record, 200 retained records, 20 groups per
response and 20 expanded records per page. Collection is sequential. A limit returns
the useful retained part with `partial`, a coverage `reasonCode`, `bytesRead` and
`filesRead`; counts never claim an unscanned incident total. An accessible empty
interval is successful with `recordCount: 0`; unavailable and partially-read source
are separate results.

The task-local snapshot expires after one hour and is pruned only from its own cache.
Expansion reads that snapshot, not the mutable journal. A missing, altered or expired
snapshot fails closed as `evidence_not_found`.

## Real isolated source run

A task-owned hardlink copy of the training runtime carried the only `logcfg.xml`.
The shared runtime had no `logcfg.xml` before or after; CF and snapshot were not
changed. An EXCP-only configuration produced 3 platform log files / 47,170 bytes /
100 platform records (`EXCP` and `EXCPCNTX`). The initial broad-log canary produced
120,507,830 bytes and was rejected as noise; it is not the acceptance source.

The current candidate made this real question against retained platform logs:

> «Какие `EXCP` произошли в локальном времени источника с
> `2026-09-18T15:25:00` по `2026-09-18T15:25:59`?»

The accepted ordinary-Hermes run returned 44 selected records with complete
coverage. With `limit=5`, five groups were shown and `groupsTruncated=true` made the
omitted groups explicit. Expansion used the exact new `groupRef` and returned all
four records in one repeated group without page truncation. Their projected message
was `DatabaseException8: Database file is missing '<redacted:path>'`. The path,
specific file, initiating operation/component and root cause remain unknown.

## Hermes boundary and delivery state

`plugin.yaml`, registered schemas, runtime handlers and bundled skill now agree on
`one_c_observe` and `one_c_expand_observation`. They call the existing public
terminal boundary with closed JSON; the plugin has no SSH, executor path or domain
parser code. The companion and plugin still require matching existing release
`artifactId` and capability version.

The ordinary Hermes chat completed registered `one_c_observe` →
`one_c_expand_observation` on installed head
`7baa1ca47398e9979d66437daa951da019fb8bc7` and retained its normal
terminal/GitHub access. The accepted transcript is recorded in
[issue #75](https://github.com/Kwentin3/1c-agent-harness/issues/75#issuecomment-5759499600).
This proves the first bounded training scenario, not every group, a production
incident diagnosis or universal platform-log disclosure.

## Supported limits

- Only the observed 8.5.1.1150 file-mode technological-log grammar is supported.
- This source does not establish cluster activity, CPU use, BSL causality, or a root
  cause for a production incident.
- A safe `Descr` message cannot be guaranteed from arbitrary platform text; a
  bounded projection is returned when supported, while opaque/unsafe content remains
  redacted with its existence and stable fingerprint visible.
