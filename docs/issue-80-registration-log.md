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

### Exact 8.5.1.1150 entry contract and next observation

The exact installed help file is
`shcntx_ru.hbk` (`sha256:b8bc0d3a1ee8d00e2f113a800339731304428cc35ae395e5094a8b022773f8ed`).
Its embedded member
`objects/Global context/properties/LaunchParameter2287.html`
(`sha256:4b3998e12dc265604ce73b26de1164d32fdbf7faee4955562ae081dbb5961049`)
defines `ПараметрЗапуска` / `LaunchParameter` as a read-only `String` property
for client contexts only (thin, web, mobile and thick client); it exposes the
`/C` command-line value. It is not a server method.

The EPF therefore reads `ПараметрЗапуска` exactly once in `ПриОткрытии` and
passes that resulting string to the server procedure. The former
`ПриСозданииНаСервере` marker was removed: it depended on an unavailable
client-only property and could not establish whether `/Execute` reached the
form. Required exporter receipts now begin with `client-entered`, then require
the server/export/complete chain. A static source test protects that precise
boundary; it is not a compile or native-run claim.

The same exact Jet `EventLog` module maps the accepted level presentations to
`EventLogLevel.Information`, `Error`, `Warning`, and `Note`. The EPF now applies
that mapping to the platform `Level` filter before `MaximumCount`; the Python
boundary rejects all other level values before any launch. Local XML filtering
remains a defensive cross-check, not the source filter.

For a future one-shot native check the deployment receipt must preserve the
existing bounded stderr, `/Out`, `/DumpResult`, process exit and five ordered
markers. It distinguishes (a) process error with platform output, (b) entry into
EPF client/server/export code, and (c) a timeout before client entry. It does
not distinguish an unfinished client startup from an EPF load/compile failure
when that last state yields no platform output. The executor currently has no
installed independent display-observation utility (`xwd`, `import`,
`xwininfo`, `xlsclients`, or Pillow); this PR neither installs one nor automates
the GUI. Any one-time capture of the owned Xvfb screen must be separately
authorized and declared before the next run.

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

The original selected-base attempt had no retained platform diagnostics, so its
absence of markers/XML did not identify a failing layer. The current exporter
therefore retains only a bounded failure receipt: lifecycle duration, wrapper exit
code, six marker-presence bits (including form server creation), and the
state/SHA-256/path-redacted excerpt of stderr, `/Out` and `/DumpResult`. The raw
command line, credentials and arbitrary diagnostic text are not returned to the
plugin. The companion exposes a diagnostic only when stderr is the exact safe
exporter JSON contract; other stderr remains `source_failed`.

A later authorized investigation exercised three fresh disposable bases without
modifying the immutable Jet snapshot, its manifest, the source configuration, or
a live infobase:

1. A form-bearing EPF built from the diagnostic head (6,194 bytes) was invoked
   against a blank disposable base. It timed out at the 115-second bound before
   every form/client/server/export marker, without stderr, `/Out` or `/DumpResult`.
2. The same EPF was invoked against a fresh disposable base made by copying the
   immutable snapshot and loading that copy with `CREATEINFOBASE` then
   `/LoadConfigFromFiles … /UpdateDBCfg` (both `DumpResult=0`). Its snapshot
   closure hash was unchanged before/after loading. The result was the same timeout
   before every marker, so an empty base was excluded as the cause.
3. Platform command-line documentation establishes that `/C` is read through the
   `LaunchParameter()` global-context method. The EPF had used the Russian alias
   without `()`. That was corrected and unit-tested; the rebuilt EPF was 6,192
   bytes (`sha256:5fa1674a02256004ceaa5e12babf0e1b2a491edd6dd2c6bf66f0427fa6c19e5c`).
   A new immutable-snapshot copy again loaded successfully, then timed out before
   `OnCreateAtServer`, `OnOpen`, all exporter markers, XML, `/Out` and `/DumpResult`.

These runs establish that the fixed command reaches a persistent 1C client process
but do **not** establish that `/Execute` instantiated the EPF or that the EPF,
native API, or client/server boundary itself failed. The failure precedes the first
observable form handler. The route remains `source_unavailable`, never an empty
registration log. No deployment command is claimed working.

Further runtime attempts must change the evidence method rather than repeat this
same headless client invocation: the available platform diagnostics are empty, and
this project explicitly does not use GUI automation as an alternate interface.

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
