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

### Current cycle: the `OnStart` route and native export are confirmed

The exact executor route was admitted on an isolated worktree at
`4fab3258e0e144211a7ec749410f0538318a5e59` (tree
`6efeaa41cb1b48f1a07bc96cdca16de5a0104233`). A first, harmless disposable
control injected an early managed-application `OnStart` marker before normal
startup, then returned. It reached that marker in **4,433 ms**; create and load
completed in **2,304 ms** and **30,199 ms** respectively. This establishes the
entry that the earlier object-module controls did not.

A subsequent disposable `OnStart → &AtServer → UnloadEventLog` probe had one
static correction before retry: `TerminateSystem` is not defined by the exact
English BSL runtime; the platform returned that compile diagnostic before any
marker or export. It was removed rather than treated as a log failure.

The corrected run reached all ordered markers: `client-entered` at 9,767 ms,
`server-entered` and `export-started` at 9,767 ms, then `export-returned` and
`complete` at 9,789 ms. `UnloadEventLog` returned in **21 ms** and wrote a valid,
**193-byte** empty `EventLog` XML document
(`sha256:53cf6cd324804ee85e3e85f5c5cc2c9766444fc5c69fad097048f0156f821617`).
The process group was stopped only after `complete`; all disposable work-copy,
file-IB, HOME and TMP roots were removed. The immutable snapshot remained
5,099 files with closure
`e437eeb98382c571e42cecb3803d98b6228e4771cabfd81ebe0f79a6275fa594`.

This proves the native method and a client/server acquisition route on the exact
training runtime. The returned XML is correctly empty for the fresh disposable
IB and does **not** prove the supplied candidate can retrieve the prior history
of a separately selected persistent IB. Its tracked `/Execute` exporter has not
been requalified; no fabricated retained selection, page, or record is claimed.

### Bounded selected-log and positive-data controls: blocked inside native export

A copy of the already retained training IB (including its 570,348-byte `.lgp`
segment) was used three times with the proven `OnStart → server` entry. The
three differentiating requests were: a two-day interval with maximum 10, the
same interval with maximum 1, and a one-second interval with maximum 1.
Each entered both client and server in 6.3–8.1 seconds and created
`export-started`, but none returned from `UnloadEventLog` before the 120-second
bound. All had empty runtime/stderr/wrapper logs, no XML, and full cleanup. The
source IB and configuration checksums were unchanged in every run. Later
inspection showed **the requested September 20–21 interval did not contain
this segment's records**: the segment is named `20260920000000.lgp`, but its
actual events date to September 22. These controls therefore must not be used
to infer either an empty selected log or that a broad result volume caused the
block. A subsequent September 22 control also blocked; see below.

A final positive-data attempt then created a disposable IB and tried to write a
fresh `Issue80Probe` event before exporting it. The initial two-phase form
reached its harmless seed marker but stopped before the export preparation due
to an invalid generated-module anchor. Two one-run variants then stopped at
runtime compilation before client entry with the exact receipt
`ManagedApplicationModule(64,1): Unknown operator`. The installed exact-version
help payload contains the token `WriteLogEvent`, but the retained error does not
identify which generated expression or signature is rejected; it is therefore
recorded as an instrumentation compile failure, not as evidence about export or
journal contents.

This consumes the current issue-cycle allowance of eight experimental execution
operations: two fresh-IB entry/export controls, three selected-log controls, the
successful seed-only control, and two one-run seed/export compile controls. No
further native command is run under this cycle. No new runtime route,
deployment setting, source-configuration change, or retained selection is
claimed by this correction.

### Expanded-budget cycle: real records through the native file-input parameter

The owner tripled the testing/research/R&D limits for the *same* issue cycle
(24 application executions and 135 minutes of native commands total, inclusive
of the previously counted eight). This continuation made nine additional
`ENTERPRISE` attempts in eight bounded controls: 800,455 ms of native
create/load/Enterprise execution in those controls. Each Enterprise attempt
remained at or below 120 seconds; the revised execution count is 17/24. Do
not reset this tally on a new session. The prior cycle's exact native-minute
total is not reconstructed here, so 800,455 ms is a **new-cycle** subtotal,
not a claim about the overall 135-minute remainder.

A corrected two-phase seed control appended the `&AtServer` procedure *after*
the existing `OnStart` procedure rather than inside it. The exact installed
8.5.1.1150 help member
`shcntx_ru.hbk:objects/Global context/methods/catalog3403/WriteLogEvent1234.html`
confirms the six-argument `WriteLogEvent` signature and server availability.
The fresh disposable IB reached `seed-written` after its server call, proving
that this instrumentation compiles and writes an event; a second session
reached `export-started` but did not return in 120 seconds. An attempt to call
`Exit(True, True)` after the seed marker (also found in the configuration's
own BSL) did not exit the startup client within 120 seconds, so the planned
closed-log comparison was **not** made. Neither result establishes why the
current-IB export stalls. A selected-IB-copy control with the *correct*
September 22 date and maximum 1 still reached `export-started` but did not
return within 120 seconds. Source IB and snapshot closures remained unchanged.

The installed help member
`shcntx_ru.hbk:objects/Global context/methods/catalog3403/UnloadEventLog4040.html`
documents a fourth `InputFileName` argument. On the retained selected training
IB, the 570,348-byte `1Cv8Log/20260920000000.lgp` actually contains events
between `2026-09-22T10:56:10` and `10:59:33`; its *filename is not an event
time bound*. An isolated fresh IB with a copied `.lgp` passed as the input
returned the empty 193-byte XML in 20 ms even when the interval covered those
events. This does **not** mean the source file is empty. When the intact
`1Cv8Log` directory was copied and its **`1Cv8.lgf`** passed as the input,
`UnloadEventLog` returned **4,504 top-level Event records** (1,279,419 XML
bytes) in 61 ms for the September 22 interval. The requested maximum 10 was
not honored as a strict record bound in that probe. A one-second interval
`10:56:10`–`10:56:11` with maximum 1 produced **two** top-level records,
799 XML bytes, in 41 ms (XML SHA-256
`54b039e2527a18fc00223b4c2240e34efde61503caa732035e1362ed4e3c2b20`).
The initial probe counted nested `<Event>` field tags as records; this corrected
count comes from the XML root's immediate children. The two real events have
native names `_$Session$_.Authentication` and `_$Session$_.Start`, both at
`2026-09-22T10:56:10`, level `Information`, with `NotApplicable` transaction
status in the selected columns. No user, metadata, or cause is inferred;
source time zone is **not established** by these receipts. The native XML
represents selected historical records from the retained training IB, not
synthetic Harness rows and not the fresh IB's own history.

The 799-byte real XML was replayed unchanged (hash above) once to the existing
`companion eventlog_select` domain path: two records, one retained selection,
then `eventlog_page` and `eventlog_record`; a later retained refinement to
`_$Session$_.Start` returned one record with **zero additional source calls**.
This proves the downstream parsing/retention on real native XML, not the live
exporter/companion seam. The 1,279,419-byte broad export exceeds the current
1 MiB source byte cap and must be reported as limited/unavailable rather than
silently accepted. A one-second file-input query can still exceed the source
limit, and `MaximumCount` cannot be trusted as the only cap.

**Unresolved product entry.** All successful nonempty native acquisitions
injected `OnStart` solely into a disposable configuration work-copy for the
experiment. The final route is explicitly forbidden to depend on that change.
The previously built form-bound `/Execute` EPF had already timed out before
`client-entered` on the training configuration. A distinguishing control used
that **same EPF** on a newly created empty disposable IB: create succeeded in
993 ms, but `/Execute` again produced no form/client marker, stderr, XML or
runtime log before the 120-second bound. This does not diagnose the 1C client,
but repeated `/Execute` without a new entry mechanism is not a valid final
route. `ibcmd` is absent from the installed training-client distribution; the
server utility's compatibility with this retained legacy log has not been
tested. A copied, stable historical journal was used here; no claim is made
about coherent copying of a *live-writing* production journal.

**Historical decision boundary (superseded).** Before the owner's subsequent
permission, this work had proved the native file-input method and retained
selection independently, but no compliant product execution seam. A routine
disposable configuration work-copy was then an exception needing a decision.
The owner granted permission to proceed with that isolated option; its tested
outcome and remaining limits follow. This does not authorize deployment,
restart, merge or issue closure.

### Authorized disposable exporter candidate and connected companion proof

After the owner explicitly granted permission to continue, a fixed-command
candidate was added at `one_c_harness/eventlog_file_exporter.py`. It uses the
already selected read-only **retained, quiescent** `1Cv8Log` directory and
the immutable snapshot. It copies both into a private `.local/` request root,
inserts an early-returning `OnStart` into that **copy only**, creates a fresh
file IB, loads the copy through the installed Designer, and calls the native
`UnloadEventLog` with the copied `1Cv8.lgf` as its explicit input. It checks
source-tree hashes before and after, terminates its owned native process group
on a deadline or byte breach, rejects an incomplete result, and removes the
disposable configuration and IB. The existing companion and retained-selection
domain are unchanged; no new service, plugin or Hermes runtime change exists.
The selected source itself is never passed as the launched IB.

The first candidate failed before client entry on exact-runtime BSL
`ManagedApplicationModule(144,9): Unknown operator`: `ElseIf` was the wrong
English keyword; the snapshot itself uses `ElsIf`. After correction, client
and server entered but export timed out when the generated module read empty
optional-filter files. Substituting the five proven columns and then lowering
`MaximumCount` to one did not change that result. The static difference to the
successful minimal control was the optional-filter reads. The generator now
omits each absent filter block entirely; no caller string is interpolated into
BSL. The next run returned **exactly the earlier native 799-byte XML**,
SHA-256 `54b039e2527a18fc00223b4c2240e34efde61503caa732035e1362ed4e3c2b20`,
with two historical records, 41 ms export and 40,986 ms total native request.
Its owned work root was empty afterward. These timings include one disposable
create/load and startup, not a claim of a 41 ms user-facing selection.

The connected test used the *actual* existing companion in the exact executor
worktree, its `eventlog_select` operation, the executable candidate command,
the retained selected journal, and `eventlog_page`/`eventlog_record`. With
`maximumCount=1`, native export returned **two** rows, while the domain kept
one and correctly labeled selection, page and record as `partial` /
`maximum_count_exceeded`. The retained record was
`_$Session$_.Authentication` at `2026-09-22T10:56:10`, level `Information`,
transaction status `NotApplicable`. A refinement for `_$Session$_.Start`
returned zero **within the incomplete retained selection**; it must not be
reported as absence from the actual log. A later page/record call on the same
selection had no additional exporter invocation (metrics mtime unchanged).
Connected receipt: **56,039 ms** lifecycle, 40 ms native export, 799 XML bytes,
one source invocation and zero subsequent invocations. The 1C training host's
current system zone is UTC and `UTC` was supplied as a *deployment setting*;
the timezone embedded in historical log events remains independently unproven.
This is a companion→candidate→native source E2E, **not** an installed Hermes
chat-plugin E2E. No source or snapshot file changed in the verified run.

The candidate's command contract is one closed JSON request on stdin, XML on
stdout, typed error JSON on stderr. Deployment binds
`ONE_C_HARNESS_EVENTLOG_COMMAND` to the executable file exporter,
`ONE_C_HARNESS_EVENTLOG_RUNTIME_PROFILE` to the pinned training runtime,
`ONE_C_HARNESS_EVENTLOG_SNAPSHOT` to the admitted immutable hierarchical
snapshot, `ONE_C_HARNESS_EVENTLOG_JOURNAL` to a preselected **stable copied**
`1Cv8Log` directory, `ONE_C_HARNESS_EVENTLOG_WORK_ROOT` to a task-owned
`.local/` directory, and `ONE_C_HARNESS_EVENTLOG_TIME_ZONE` to an explicitly
configured IANA zone. The candidate needs a full matching training runtime
and this workload takes tens of seconds per *new* selection; pages/records
reuse the cached selection. A changing/live-writing source is **not admitted**:
before/after hashes can detect some concurrent changes, but cannot prove an
atomic snapshot. No compatibility claim is made for a production 1C build,
other log formats, broad requests over the 1 MiB limit, or filters not
individually exercised natively. The final verified candidate only emits five
columns (`Date,Level,Event,EventPresentation,TransactionStatus`); user and
metadata remain unavailable, **not** empty or known. No deployment or merge
has occurred. The total authorized execution count is **24/24** (17 prior,
seven candidate invocations, including the connected companion attempt).

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
