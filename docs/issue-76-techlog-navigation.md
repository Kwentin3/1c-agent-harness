# Issue #76 — bounded technological-journal discovery and navigation

## Product gap and chosen slice

The accepted #75 route could read one known calendar interval, return the first page
of grouped `EXCP` records, and page records inside one group. It could not tell an
ordinary agent which source interval and events were actually observed, page groups
past `groupsTruncated`, filter safe technical content, address one record, or inspect
nearby retained events.

The #76 candidate keeps the same source, reader, task-local snapshots, plugin and
terminal deployment seam. It adds no service, database, index, parser framework,
query language or Hermes-core change:

- `one_c_observation_info` performs one bounded source inspection and reports the
  configured source, source timezone, exact first/last occurrence observed during
  that pass, observed event names, supported filters and coverage. The interval is
  not a history-retention guarantee. `complete: false` and `partial` make bounded
  inspection explicit.
- `one_c_observe` keeps its existing required `events` argument and accepts an optional
  `filters` object. `text`, `sourceComponent` and `process` are AND filters. Text search
  sees only the already-safe projected technical content; hidden raw values cannot
  become a search side channel. Text is bounded to 120 Unicode characters;
  `sourceComponent` and `process` accept only the published ASCII technical-token
  pattern. Session values, when present, are exposed only as
  selection-scoped opaque fingerprints for comparison inside that retained result,
  not as cross-query filter keys.
- `one_c_expand_observation` keeps the existing `groupRef` form and adds two explicit
  ref forms. `observationRef + offset + limit` pages stable groups;
  `recordRef + before + after` returns one record and at most five records on each
  side from the retained filtered selection. The response states this scope and says
  that time adjacency does not imply causality.

## Stable selection and meaning

An observation retains only the filtered, bounded records and all derived groups in
its existing one-hour task-local snapshot. Group counts are explicitly scoped to
`retainedFilteredSelection`. Each group carries its first/last retained occurrence and
a short meaning derived from the allowlisted exception token and safe projected
description. Each expanded record carries a snapshot-bound `recordRef`.

Source mutation or rotation does not change group pages, record pages or neighbors
for an existing ref. Missing, altered or expired snapshots remain
`evidence_not_found`; the reader does not silently replace them with a fresh source
read.

`SrcName` and safe token-shaped `process` values can be returned and filtered.
`SessionID` is never returned: a snapshot-selection-scoped keyed fingerprint permits
matching records inside one retained result without enabling enumeration or
cross-selection correlation. Description fingerprints and derived group refs use the
same selection-scoped keyed boundary, so redacted low-entropy values cannot be tested
with an offline dictionary. Error signatures and derived group refs are keyed directly,
including events without a projected description. Each `recordRef` combines the
retained selection index with a selection-scoped keyed record token, so private
fields do not leak through an unkeyed raw-record digest while byte-identical
occurrences remain separately addressable.
Description projection, redaction and truncation rules from #75 remain unchanged.

## Bounds and incomplete results

The existing bounds remain: 96 discovered paths, 24 candidate files, 256 KiB input,
2 seconds, 8 KiB per record, 200 retained records, 20 groups or records per page and
a one-hour snapshot TTL. Neighbor expansion is additionally capped at five records
before and five after.

A pre-existing bounded-reader defect was exposed by the new discovery test: when
file discovery found more than 24 candidates, `_read` stopped before reading the
already-admitted first 24. The candidate now returns those useful bounded records
with `partial: true`, `reasonCode: file_budget`, and `complete: false`. It still does
not claim that later history is absent.

## Verification contract

Static fixtures cover:

- source timezone, observed interval/events and complete versus partial discovery;
- text/component/process filtering over safe projected values only;
- selection-scoped session fingerprints without raw `SessionID` disclosure;
- short group meaning and unambiguous count scope;
- group and record pagination beyond the first page;
- exact record references, retained-selection neighbors and boundary clipping;
- source mutation after observation, expiry, unavailable/empty/partial distinctions;
- companion closed-request validation and Hermes manifest/schema/handler parity.

No 1C process is needed or allowed for these tests. The installed #75 implementation
remains the verified live version until an owner separately approves the compatible
update below.

## Compatible update and rollback

Candidate companion and plugin version: `0.2.0`. They must be built from the same
immutable approved revision and carry the same changed `artifactId`.

After owner approval, reuse the accepted #75 transaction:

1. create a new clean detached executor source worktree at the approved exact commit;
2. run focused and full tests there without changing the configured TechLog source;
3. stage the matching tracked plugin closure in the Hermes profile and atomically
   switch the fixed executor launcher to the new immutable worktree;
4. restart the owning WebUI/Gateway process only if plugin schema discovery requires
   it, then open a new chat and run the issue's ordinary-chat acceptance;
5. verify local terminal and GitHub access remain local and functional.

Rollback independently restores the prior accepted plugin closure and fixed launcher
target at `7baa1ca47398e9979d66437daa951da019fb8bc7`, restarts the owning process only if
required, and removes only the new task-owned worktree after no owned process remains.
The TechLog source, SSH policy, global terminal backend, platform, CF, snapshot and
infobase are not changed.

## Current evidence boundary

This document describes the source candidate and fixture-backed behavior. It does
not claim an installed ordinary-chat run, real-source response-volume measurement,
deployment, restart or merge. Those require the separate owner-approved compatible
update and acceptance. The acceptance run must report actual tool-call count,
`bytesRead`, and serialized response bytes; model token count is reported only if the
runtime exposes it.
