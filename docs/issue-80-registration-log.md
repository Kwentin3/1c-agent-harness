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

### Verified launcher contract (maintainers)

The registered registration-log tool reaches the fixed command through this closed
chain: plugin → public terminal tool → companion `eventlog_select` →
deployment-selected command → `eventlog_exporter.run_once`. The model supplies
only the closed JSON request; `_environment` supplies the runtime environment,
`_prefix` supplies the wrapper invocation, and `run_once` supplies the fixed
1C child arguments.

The executor profile binds the 8.5.1.1150 training client, a Debian `xvfb-run`
wrapper (`sha256:97e86a102eee7212bfa3bf87d452b27dd4f16ef6e68658eeae20bca63db2ceee`)
and its sibling Xvfb binary
(`sha256:14e8ec7d8209bbaf105f9ade27a80b65f01709346690d18fbadb6116ada34912`).
The wrapper source and its `--help` establish these boundaries:

- `-a`, `-e <wrapper-log>` and `-s <server-args>` belong to `xvfb-run`;
- the one string after `-s` is passed to Xvfb; the wrapper itself adds
  `-nolisten tcp`;
- `ENTERPRISE`, connection, `/Execute`, `/C`, `/Out` and `/DumpResult` belong
  to the 1C child.

Accordingly the exporter now passes one `-nolisten tcp` (from the wrapper),
captures the wrapper's documented `-e` file, and leaves Xvfb arguments as the
single screen specification. Before this correction the exporter duplicated
`-nolisten tcp` and omitted `-e`, so wrapper, Xvfb and xauth diagnostics were
silently directed to the wrapper's default `/dev/null`. This was a real loss of
evidence; it is **not** evidence that either discrepancy caused the prior timeout.

The wrapper returns the 1C child status after a normal launch, but uses its own
failure status before that point. `launcherExitCode` therefore names the observed
wrapper-process exit only; it is not claimed to be a separately observed 1C exit
code. The bounded `wrapperLog`, `runtimeLog`, `/DumpResult` and child stderr make
the observable layers explicit without returning paths or arbitrary text.

The actual Xvfb `-help` lists `-fbdir directory`. It can be forwarded only inside
the existing `-s` argument. No framebuffer option or capture was added here:
the previous absence claim came from querying wrapper help rather than the X server
and is corrected below. The 1C client help/version switches are not usable without
a display in this installation (each returned the GTK display error); the pinned
runtime profile is the reproducible version identity. This is a launcher audit,
not a new native acceptance run.

The deployment receipt preserves bounded stderr, `/Out`, `/DumpResult`, process
exit and five ordered markers. It distinguishes process output/error, entry into
EPF client/server/export code, and a timeout before client entry. A timeout with
all those channels empty does not distinguish unfinished client startup from an
EPF load/compile failure.

The exact installed platform `8.5.1.1150` contains both the Designer batch command
`/LoadExternalDataProcessorOrReportFromFiles` and the Enterprise `/Execute`
parameter. This makes an external EPF the smallest native candidate: it avoids a
permanent configuration patch and can run against a deployment-selected base.

### Authorized corrected EPF attempt — still no entry evidence

On authorized head `8d45df6bcff1b8a52aad0c207af827b93d19ceee`
(`artifactId sha256:d935aad596f4121b08f7449ea723a198c2f191dfc4edd6a4a2e2d03e147f993e`),
a fresh task-owned file IB was made from the immutable Jet snapshot copy. The
preparation completed in 194,416 ms: `CREATEINFOBASE` and
`/LoadConfigFromFiles … /UpdateDBCfg` each returned `DumpResult=0`; the source
closure stayed `e437eeb98382c571e42cecb3803d98b6228e4771cabfd81ebe0f79a6275fa594`
(5,099 files). The single permitted EPF build completed in 21,855 ms, producing
6,174 bytes (`sha256:9f868a43e92c5c7ee84df070848d1bd4e98a5c11c5a6b92147f12264eeb98f4a`).

The candidate companion invoked its fixed exporter exactly once. Selection ended
as `source_timeout` after 116,059 ms; the exporter lifecycle measured 115,245 ms
and terminated its owned group (the historical receipt field was
`wrapperExitCode=-15`). There was no XML, no
client/server/export/complete marker, empty stderr, an empty `/Out`, and no
`/DumpResult`. Consequently no retained selection exists and page/refinement/record
operations were not run; a fabricated or historical XML was not substituted.

No XWD was saved in that attempt. The later launcher audit confirmed that Xvfb
does support `-fbdir`, but the installed executor has no `xwd` reader. No package,
viewer, VNC, GUI automation, common runner or product code was added. The
task-owned work copy, file IB, platform home, temporary area, logs and EPF were
removed after the bounded JSON receipts were retained; no 1C or Xvfb process
remained.

This attempt proves preparation, EPF compilation and the fixed exporter lifecycle,
but it does **not** prove that `/Execute` instantiated the EPF or that the EPF,
native API, or client/server boundary itself failed. The failure is before the
first observable form handler. The route remains `source_unavailable`, never an
empty registration log. No deployment command is claimed working. The one useful
next native observation, if separately authorized, is a task-owned `-fbdir`
capture plus the already-added wrapper error log; an `xwd` reader/viewer is the
single missing observation resource. Repeating the same headless invocation
without that new evidence would add no distinguishing evidence.

### Observation preflight after launcher correction

The authorized no-1C preflight used the same executor, Debian `xvfb-run`, its
documented `-e` wrapper log and Xvfb `-fbdir` through the wrapper's `-s` server
argument. It created a private 64×64 own-display capture (7,328 bytes,
`sha256:5828e5437285391f814db0988f2e73dd951ab8af7f047c1c53ce9d1cf027da7a`),
copied it through the existing authenticated path, and verified the copied hash.
The wrapper log was empty and no Xvfb or 1C process remained.

The capture was **not** accepted as a readable observation at that point: no
`xwud`, `xv`, `xloadimage`, ImageMagick, FFmpeg or Pillow was available. Creation
and hash equality alone are not a viewed image. Consequently no file IB was
prepared and no EPF build, exporter invocation or `ENTERPRISE /Execute` run
consumed the newly authorized native budget. The private preflight capture
remained task-local and was not published.

The authorized next step admitted one ready-made reader, Debian `netpbm 11.10.2`,
with its declared runtime libraries into a task-local `.local/` root only. Its
`xwdtopnm` opened the retained XWD; its `pnmtopng` made a PNG that the available
reader displayed. No executor/global package, custom decoder, public conversion
service or GUI automation was added.

### Authorized framebuffer observation — client process visible, EPF still unentered

The exact candidate was `01245895bf5854b5d2515325149e748239c6fd3c`
(`artifactId sha256:2abb57cef4c01d6015f688d24a45829d53beecaed98f6081049c5358901230eb`).
A detached, clean worktree at that commit was used; tracked product source and
EPF source were not changed. Two task-owned file-IB preparations each returned
`DumpResult=0` for `CREATEINFOBASE` and `/LoadConfigFromFiles … /UpdateDBCfg`.
Both before/after checks retained the immutable snapshot closure
`e437eeb98382c571e42cecb3803d98b6228e4771cabfd81ebe0f79a6275fa594`.

One EPF build succeeded: 6,174 bytes,
`sha256:083648ac188c42237d86cc93b8dd8744086bdf7b18625cff3025684ba227ac3a`.
The fixed exporter was then invoked exactly once through the candidate companion.
It returned `source_timeout` at `stage=enterprise_process`; exporter lifecycle was
115,071 ms and its owned process group ended with observed
`launcherExitCode=-15`. XML, all five EPF markers, stderr, runtime `/Out`,
`/DumpResult` and wrapper log were absent/empty. This remains an unavailable
source, not an empty registration log; no retained selection, page, refinement or
record was created.

The task-local `-fbdir` watcher saved 1,115 copies of the live Xvfb framebuffer;
the last is 789,664 bytes
(`sha256:4b0d72e63a56bf82fe75cb7113f378eb995abd25cf04d670fe58049be3824f95`).
`netpbm` converted it to a readable 1024×768 PNG. It shows a black screen with a
single pointer and no visible 1C window or error text. The watcher also recorded
only the owned `xvfb-run`, Xvfb and `1cv8t` process tree while active; cleanup
reported no remaining 1C/Xvfb processes. This proves client-process and
framebuffer existence during the bounded run, but does **not** prove that the EPF
form opened or identify the cause of the timeout.

The disposable IBs, work copies, homes, temporary areas, logs and remote
worktree were removed after bounded receipts and the task-local screenshot were
No production CF, live infobase, immutable snapshot or deployment setting changed. A
further native launch needs separate owner authorization; repeating this same
candidate is not justified by this evidence.

### Historical startup-route controls: invalidated entry assumption

The earlier controls after issue comment `5782298368` are retained as historical
evidence of their own bounded lifecycle and cleanup, but **not** as evidence
against `/Execute`, client startup, EPF loading, or the registration-log route.
They assembled an EPF with only `Ext/ObjectModule.bsl`, an unbound
`ПриОткрытии` procedure, an empty `DefaultForm`, and no child form. There was
therefore no form event binding or explicit call requiring the platform to invoke
that procedure. A missing `<receipt>.entered` marker cannot falsify a route whose
control did not have a valid expected positive observation.

This is distinct from the supplied candidate. Its metadata sets
`DefaultForm` to `ExternalDataProcessor.Issue80EventLog.Form.Main`; its managed
form declares `OnOpen → ПриОткрытии`; and that handler writes `client-entered`
before the server call. `tests/test_eventlog_exporter.py` statically checks this
chain. That static fact does not claim an EPF runtime result.

The old six `ENTERPRISE` controls and one `DESIGNER /Execute` control remain in
the chronology with their bounded cleanup and unchanged immutable snapshot
closure `e437eeb98382c571e42cecb3803d98b6228e4771cabfd81ebe0f79a6275fa594`,
but their black framebuffer, empty marker, and trace are no longer used to
conclude that ordinary startup did not reach an object-module entry. They neither
prove an empty log nor an EPF compilation/platform defect.

The current owner-authorized cycle begins its own budget. Before its first native
attempt, the executor route must be admitted on the exact prepared remote
workspace and the first control must use the form-bound entry above (or another
entry with an equally direct, version-supported positive contract). No new
runtime route, deployment setting, source-configuration change, or retained
selection is claimed by this correction.

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
