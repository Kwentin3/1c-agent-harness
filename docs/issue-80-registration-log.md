# Issue #80 — registration log as a bounded evidence source

## Result and dependency boundary

This candidate adds a source-neutral registration-log contract on top of the
accepted diagnostic seams from draft PRs #77 (`#76`) and #79 (`#78`). The branch
is based on exact #78 head `5ad9295faaf0240c3811aa20dd054eef81fe45f2` and must be
reviewed as a stacked PR until those dependencies are admitted. It does not copy
or reimplement their terminal, companion, retained-ref, or response-compaction
mechanics.

The candidate adds three closed operations:

- `one_c_select_registration_log` creates one bounded retained selection;
- `one_c_page_registration_log` pages that exact selection;
- `one_c_read_registration_log_record` returns one exact retained record.

The plugin remains a thin adapter. Selection validation, source invocation, XML
projection, filtering, completeness classification, retained evidence and refs
belong to `one_c_harness/eventlog_observation.py`.

## Acquisition boundary

The model cannot choose a source path, connection string, executable, credential,
or arbitrary 1C arguments. Deployment selects one executable through:

```text
ONE_C_HARNESS_EVENTLOG_COMMAND=/absolute/fixed/exporter
ONE_C_HARNESS_EVENTLOG_TIME_ZONE=UTC
```

The companion invokes that executable with no arguments, sends one JSON request
to stdin and accepts only XML on stdout. The executable is deployment-owned and
is the only place that may bind a file or client/server infobase, credentials,
platform runtime and the native `UnloadEventLog` call. The tracked candidate does
not manage SSH, secrets, deployment or installation.

Request schema v1:

```json
{
  "schemaVersion": 1,
  "operation": "unloadEventLog",
  "start": "2026-09-22T06:44:00",
  "end": "2026-09-22T06:45:00",
  "filters": {
    "event": "_$Data$_.Update",
    "level": "Error",
    "user": "alice",
    "metadata": "Document.Invoice"
  },
  "columns": [
    "Date", "Level", "Event", "EventPresentation", "User",
    "UserPresentation", "Metadata", "MetadataPresentation",
    "TransactionStatus"
  ],
  "maximumCount": 100,
  "maximumBytes": 1048576
}
```

`filters` are optional individually but closed to those four exact keys. The
calendar interval is inclusive, source-local, offset-free and at most 24 hours.
The process timeout is 120 seconds. XML is capped at 1 MiB. The domain layer
reapplies the interval and every exact filter to the returned XML rather than
trusting the deployment command alone.

If the fixed command or timezone is absent, invalid, times out or exits nonzero,
the source is `unavailable`; it is never reported as an empty selection. A known
exporter failure may expose only the closed tuple `reasonCode`,
`stage=enterprise_process` and a bounded, path-redacted message. Arbitrary stderr
is not exposed. Malformed, unsafe or oversized XML is blocked. A valid empty
`EventLog` is an `ok` selection with zero records.

## Selection, page and record semantics

A successful selection retains only projected allowlisted fields under
`.local/runs/eventlog-selections/` for one hour. The response contains:

- opaque `selectionRef` and per-occurrence `recordRef` values;
- a first page of at most 20 records;
- exact requested window, source timezone and filters;
- retained, matched and raw XML source counts;
- bounded facets for event, level, user and metadata;
- explicit `complete`/`partial` coverage.

The selection file is integrity-bound. Altered, expired, missing, forged or
symlinked evidence returns `evidence_not_found`; page and record calls never
silently query the live source again. Ordering is the XML source order. The
contract does not infer causality from adjacency.

`maximumCount` is not treated as a trustworthy hard upper bound. The installed
8.5.1.1150 probe requested 100 and returned 105 records in the evidence published
at [issue comment 5772829223](https://github.com/Kwentin3/1c-agent-harness/issues/80#issuecomment-5772829223).
Therefore:

- fewer than the requested maximum is `complete`;
- exactly the maximum is `partial / maximum_count_boundary` because more records
  may exist;
- more than the maximum is truncated locally and returned as
  `partial / maximum_count_exceeded`.

The raw XML is never returned through the plugin. Record fields are individually
bounded; comments, data payloads, connection strings and arbitrary XML fields are
not projected.

## Native route decision and bounded evidence

The exact installed platform `8.5.1.1150` contains both the Designer batch command
`/LoadExternalDataProcessorOrReportFromFiles` and the Enterprise `/Execute`
parameter. This made an external EPF the smallest native candidate: it would avoid
a permanent configuration patch and could run against a deployment-selected base.

Two bounded admission attempts were used in an isolated disposable file infobase:

1. The first launcher stopped before any 1C process because its local `xvfb-run`
   environment did not expose `xauth`. It produced no receipt/XML and left the
   source unchanged.
2. The corrected attempt created the disposable infobase, compiled the minimal
   EPF from XML (`returnCode=0`, `DumpResult=0`, 4,355-byte EPF) and launched
   `ENTERPRISE /Execute`. A no-form external processor object module did not obtain
   control: no entry receipt or XML appeared, and the owned process was terminated
   at the 90-second bound. The disposable infobase was removed and no 1C/Xvfb
   process remained.

The latest selected-base attempt created the prepared EPF and invoked the exporter
once, but produced none of its five EPF markers, XML, `/Out`, `/DumpResult` or a
retained runtime exit code. This is not evidence that the form, `/Execute`, native
API or client/server boundary failed: the then-current exporter sent stderr to
`DEVNULL`, mapped every nonzero wrapper exit to `source_failed`, and removed its
temporary directory before preserving the platform files.

The minimal correction preserves one bounded failure receipt at that existing
exporter boundary: lifecycle duration, wrapper exit code, five marker-presence
bits, and the state/SHA-256/path-redacted excerpt of stderr, `/Out` and
`/DumpResult`. The raw command line, credentials and arbitrary diagnostic text are
not returned to the plugin. The companion exposes a diagnostic only when stderr is
the exact safe exporter JSON contract; other stderr remains `source_failed`.

No new native launch is authorized by this correction. Consequently this PR does
**not** claim that a working deployment exporter or selected-base round trip
exists. One future distinguishing run of this exact new head would separate: a
platform/wrapper exit with its bounded message and code, an entrypoint failure with
the marker pattern, and a successful XML receipt. It uses the existing selected
disposable file infobase, one exporter invocation, the same timeout/XML cap and
process cleanup; it persists only the bounded failure receipt under the existing
task-local metrics path. It does not fall back to a blank infobase or use the
historical temporary configuration patch as a permanent source.

## Verification and limits

Static tests cover:

- exact event/level/user/metadata filters and request forwarding;
- domain-side filter reapplication;
- valid empty versus unavailable and malformed source results;
- the platform-over-return and exact-boundary partial states;
- stable paging and one-record reading after source mutation;
- tamper, expiry, forged-ref and unknown-field rejection;
- companion/plugin/schema/manifest registration parity.

The prior successful patched-configuration probe proves the native method and XML
shape on 8.5.1.1150. It does not prove this new external-EPF acquisition route.
No deployment, credentials, service, database, index, Hermes core, source
configuration, snapshot, live infobase or production code is changed by this PR.

## Rollback

Revert the #80 commit. No data migration is required. Task-local retained
selections expire after one hour and may be removed only as deployment-owned
`.local/` data. The #76/#78 companion/plugin behavior remains unchanged.
