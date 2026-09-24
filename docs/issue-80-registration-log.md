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
to stdin and accepts only XML on stdout. The tracked executable binds only an
administrator-selected stable `1Cv8Log` directory and an official `ibcmd`
binary. It executes one fixed `ibcmd eventlog export` command; no caller value
can add an executable or arbitrary argument. The tracked candidate does not
manage SSH, secrets, deployment or installation.

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
The `ibcmd` backend applies the bounded time window natively. The domain layer
then reapplies `event`, `level`, `user` and `metadata` exactly over the returned
bounded document. This is deliberate: `ibcmd eventlog export` 8.5.1.1150 has no
native options for those four filters. Coverage is classified from the complete
bounded source result before local filtering, so a retained refinement cannot be
misreported as proof of absence outside a partial selection.

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

### Superseded disposable `UnloadEventLog` candidate and connected proof

This section records the predecessor that was tested before the official
server distribution was recovered. It is retained as historical evidence, not
as the current implementation. After the owner explicitly granted permission
to continue, a fixed-command candidate used the
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

The superseded candidate's command contract was one closed JSON request on
stdin, XML on stdout and typed error JSON on stderr. It bound
`ONE_C_HARNESS_EVENTLOG_COMMAND` to the executable file exporter,
`ONE_C_HARNESS_EVENTLOG_RUNTIME_PROFILE` to the pinned training runtime,
`ONE_C_HARNESS_EVENTLOG_SNAPSHOT` to the admitted immutable hierarchical
snapshot, and `ONE_C_HARNESS_EVENTLOG_JOURNAL` to a preselected **stable copied**
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
occurred. The original cycle used **24/24** native invocations (17 prior,
seven candidate invocations, including the connected companion attempt).
The owner then expanded the *total* budget to 50; see the bounded follow-up
below. The prior 24/24 statement is not the current budget.

### Follow-up without deployment or restart (expanded budget)

Five further isolated native runs on the same selected retained training
`1Cv8Log` brought the total to **29/50**. Each generated its own disposable
configuration and file IB under executor `.local/`; the candidate checked
source-tree content at admission, after copying and after load (and also after
export on successful paths), then removed its owned runtime work directory.
Raw receipts stay in the executor's `.local/issue80-cycle/candidate-{filter-1,
full-columns-1,complete-1,combined-1,byte-limit-1}/` directories, not Git.
The exact source remains the retained copy, not a live-writing IB.

| Control | Observed result |
| --- | --- |
| `filter-1` with `event=_$Session$_.Start` | One real event, 497 XML bytes, SHA-256 `80a8f170ad95a1d4224f066aafea51267e0d886e12e3f61b426fd87b3eb699b3`, 21 ms native export; clean owned work root. |
| `full-columns-1` with all nine requested output columns | Entered client/server and `export-started`, but did not return within 110 s; zero XML, `source_timeout`, clean owned work root. **Neither user nor metadata is observable from this exporter.** |
| `complete-1` through actual companion with `maximumCount=10` | Two records in 799 XML bytes, `coverage.complete=true`, 45,219 ms total, 20 ms native export. Retained page narrowed to one `_$Session$_.Start` record; record read succeeded, zero subsequent exporter invocations. |
| `combined-1` with `event=_$Session$_.Start`, `level=Information` | One real event, 497 bytes and the same XML hash as `filter-1`; 42,296 ms total; clean owned work root. |
| `byte-limit-1` with 4 KiB output limit | The native method returned and all five lifecycle markers appeared, but the candidate returned exit 2 / `source_byte_limit`, **zero XML stdout**, and removed its owned work root. |

At the end of this 50-operation stage, the production candidate kept the
**five proven output columns** and refused
`user` / `metadata` filters before native launch. Returning zero rows for these
filters would be a false absence claim: the companion's post-filter cannot
match fields missing from native output. `event` and `level` are proven
individually/combined on this historical slice; other combinations and runtime
builds remain unproven. The candidate now streams source-tree hashes, caps the
snapshot at 10,000 files / 128 MiB and the historical journal at 128 files /
64 MiB, and starts its 110-second deadline before the initial content hash.
The caller's 120-second bound remains outside that deadline. Oversized or
timed-out acquisitions fail closed; temporary copies are cleaned. These are
limits for this candidate, not a general capacity specification.

**Still unknown:** the retained `1Cv8Log` files have owner-write filesystem
permission. Their unchanged hashes during a request do not establish an atomic
or quiescent origin, and the exporter does not implement live-journal snapshot
acquisition. No fresh consistency guarantee or supported production source is
claimed. A running 1C installation or Hermes deployment was not restarted.

### Live-source and meaningful-field continuation (40-operation stage)

The owner opened a new 20-operation stage for the live-source goal and later
expanded that stage to **40 total operations**. All 40 were used; preparation,
source sessions and reader calls were counted conservatively as separate
operations. Every native command remained bounded to at most 120 seconds. The
immutable 5,099-file snapshot retained closure
`e437eeb98382c571e42cecb3803d98b6228e4771cabfd81ebe0f79a6275fa594`,
and no task-owned 1C process remained after the final timeout.

A disposable training IB wrote real platform journal events through the exact
8.5.1.1150 `WriteLogEvent` API. The useful rows include:

- `Issue80.Lab.Commit`, `Information`, `Document.SalesInvoice`, transaction
  `Committed`, comment `Committed invoice check`;
- `Issue80.Lab.Rollback`, `Warning`, `Catalog.Companies`, transaction
  `RolledBack`, comment `Rolled back company check`;
- `Issue80.Lab.Independent`, `Note`, `Document.InventoryWriteOff`, transaction
  `NotApplicable`, comment `Independent inventory check`;
- 25 `Issue80.Lab.Page` rows per writer session for paging controls.

The training runtime would not admit the planned named laboratory user: a
password is forbidden by the training-license boundary, while disabling standard
1C authentication would leave no authenticated administrator. The events were
therefore authored by the existing disposable-IB administrator. Its exported
technical `User` value is a non-empty UUID; no user presentation is inferred.

A coordinated lab copy was taken only after the writer emitted its
`events-written`/`source-ready` markers while that source session remained alive.
Before/source-after/copy closures matched: two files, 68,035 bytes, SHA-256
`99b4c039637979623e0a2fa755e0619c92e7b7350910ca949600d2b0aac540ce`.
This proves a quiescent application-controlled laboratory cut, not an atomic
snapshot of an arbitrarily live-writing production journal.

Column-isolation on that copy produced 324 native records for the day. The five
baseline columns returned in 4,382 ms. Adding each field separately returned:
`Comment` in 2,439 ms (124,834 XML bytes), technical `User` in 2,590 ms
(116,497 bytes), technical `Metadata` in 2,226 ms (110,181 bytes), and
`MetadataPresentation` in 2,121 ms (116,636 bytes). The fields are populated in
the known events above. `UserPresentation` alone reached `export-started` but
returned no XML within 45 seconds.

The limitation is interaction-sensitive rather than a blanket absence of these
fields. `User + Metadata`, with and without `Comment`, did not return within 40
seconds. Native `User` and `Metadata` filters likewise reached `export-started`
but returned no XML within 40 seconds, even though those same technical values
were present in the separately exported rows. A final candidate attempted four
individually safe native exports in one reader session and an identity-checked
XML merge. Its configuration loaded successfully in 30,823 ms, but the bounded
companion call stopped inside the first export before any XML was created. This
failed candidate was removed; the tracked five-column historical exporter was
the rollback-safe implementation at the end of that stage.

The direct utility is named **`ibcmd`**. Official 1C documentation identifies
`ibcmd eventlog export` as the shortest route because it reads an event-log
directory without a service infobase. The installed training-client subset did
not contain it. At this historical stage the previously supplied complete
server archive had not yet been recovered; the conclusion below was therefore
provisional and is superseded by the final `ibcmd` section.

**40-operation stage verdict: partially ready / stopped (superseded below).**
That stage proved current lab event
creation, a bounded quiescent cut, and the presence of useful user/metadata/text
fields, but it does not provide one supported acquisition that returns those
fields together while the source remains running. The minimum external resource
for the primary KISS path is an official Linux x86-64 server distribution that
contains `ibcmd` (preferably the matching 8.5.1.1150 build), made available in
the executor's task-owned `.local/` area or through an authenticated vendor
download handoff. Installation, deployment, restart, merge and issue closure
remain outside this result.

### Supported split-session exporter (100-operation stage)

The owner increased the total native budget from 40 to **100 operations**. The
previous single-reader-session merge failed because this exact training runtime
can block when several `UnloadEventLog` calls are made in one Enterprise
session. The successful minimum changes only that lifecycle boundary: one
request still creates and loads one disposable reader IB, but each known-safe
column group is exported by its own short Enterprise session. Four exports use
the common identity columns `Date,Level,Event,EventPresentation,
TransactionStatus` plus, respectively, `Comment`, `User`, `Metadata`, or
`MetadataPresentation`. The host accepts the result only when all four XML
documents have the same row count and every ordered identity tuple matches;
otherwise it fails closed. `UserPresentation` is not requested because its
isolated native probe timed out.

The isolated pre-product proof loaded the reader in 49,167 ms and returned 75
`Issue80.Lab.Page` rows from each session in 5,978 / 3,426 / 3,093 / 3,136 ms.
The identity-checked merged XML was 38,113 bytes, SHA-256
`797da150de585b70810d828536d2865836a352727250ffb3062a47784e53bb0a`.
The immutable snapshot still contained 5,099 files with closure
`e437eeb98382c571e42cecb3803d98b6228e4771cabfd81ebe0f79a6275fa594`.

The exact production candidate then passed through the real companion:

- one `eventlog_select` returned all 75 page events in 56,676 ms; exporter
  lifecycle was 55,388 ms and the four native exports totalled 10,928 ms;
- records simultaneously contain a meaningful comment, non-empty technical
  user UUID, metadata identifier/presentation, event, level and transaction
  status;
- `eventlog_page` at offset 10 with exact event/level/user/metadata refinement
  returned ten matching records in 4 ms;
- `eventlog_record` returned the cited row in 1 ms;
- the metrics mtime did not change during page/record, proving zero repeated
  source export; the owned work root was empty afterward;
- the admitted journal copy remained two files with closure
  `0912787526bd5e3c8971a41034293fbb9023ea856e2b0e04954c9ff50a577f24`,
  and the source snapshot closure was unchanged.

A new writer session then appended events to the disposable source IB. The old
selection file retained the same hash and continued to serve its old page
without changing exporter metrics. A new combined exact filter for event,
level, user and metadata returned 39 complete matches. A broad request returned
324 source rows, retained 100 and correctly reported `partial` /
`maximum_count_exceeded`. That request exposed a real 16,423-character system
comment; the earlier per-comment 512-character parser cap was removed because
the whole XML is already bounded to 1 MiB. The broad XML was 174,718 bytes.
Addressed product selections prove `Committed` and `NotApplicable`; an exact
`Issue80.Lab.Rollback` selection returned three rows with comment
`Rolled back company check`, `Catalog.Companies`, level `Warning`, the same
technical user and transaction status `RolledBack`.

`event` and `level` remain native filters in every split export. `user` and
`metadata` are deliberately reapplied in the domain over the merged bounded
selection because their native filters block on this runtime. Coverage remains
honest: if acquisition exceeds `maximumCount`, refinements are explicitly
limited to the retained selection and cannot prove absence outside it.

The stage used **88/100** authorized native operations. The final task-owned
process check was empty. No source/snapshot bytes, deployment, service, Hermes
runtime, restart or live production IB were changed. This split-session
implementation was a verified fallback, but it is superseded by the direct
official utility below.

The official-utility work conservatively counted nine subsequent invocations
(version/help discovery, two direct controls and repeated exact-product runs),
bringing the ledger to **97/100**. The owner then added 100 operations, making
the cumulative authorization **200**. The three final filter/coverage cases
below bring the current ledger to **100/200**, leaving **100** operations.

### Supported official `ibcmd` exporter (final candidate)

The owner-returned goal required rechecking the previously supplied complete
Linux distribution rather than treating it as absent. The recovered official
archive is `server64_with_all_clients_8_5_1_1150.zip`, 3,410,800,413 bytes,
SHA-256 `5fdea4f52861460c62fde833becee863b12f291b5f065e34ed2a8635d8bf2280`.
It contains `setup-full-8.5.1.1150-x86_64.run`. Only task-owned `.local/`
directories were used. An isolated non-root extraction installed the selected
`server,server_admin` components behind private `/opt` and `/usr/local/bin`
bindings; canaries verified that the executor's real paths were unchanged.

The resulting official ELF x86-64 binary reports `ibcmd --version` =
`8.5.1.1150` with exit code 0. It is 55,310,040 bytes with SHA-256
`62e72e15bb4550c4ffcf421f962c27fd1e1ddde1ba31e5bc0d7c9e0c2352dde7`.
Its own `ibcmd help eventlog` documents XML/JSON export, `--skip-root`, inclusive
`--from`/`--to`, `--out` and a positional event-log directory. No mirror or
third-party `ibcmd` binary was used.

The production candidate at `one_c_harness/eventlog_file_exporter.py` now uses
that interface directly. Deployment binds:

```text
ONE_C_HARNESS_EVENTLOG_COMMAND=/absolute/eventlog_file_exporter.py
ONE_C_HARNESS_EVENTLOG_IBCMD=/absolute/ibcmd
ONE_C_HARNESS_EVENTLOG_JOURNAL=/absolute/stable/1Cv8Log
ONE_C_HARNESS_EVENTLOG_WORK_ROOT=/absolute/task-owned/.local/work
ONE_C_HARNESS_EVENTLOG_TIME_ZONE=UTC
```

The exporter validates all paths before creating its work root, rejects symlinks
in every path component, source/work overlap and metrics hardlinks to either the
journal or executable, hashes the bounded selected journal before and after,
runs exactly one fixed-argument `ibcmd eventlog export --format=json
--skip-root`, enforces a 30-second process deadline and the request byte bound,
applies the four admitted exact filters before XML projection, and projects the
remaining JSON sequence into the existing XML contract. The domain layer
reapplies the same filters rather than trusting the exporter. `UserName` maps
to user presentation. `MetadataPresentation` is the stable technical metadata
name (`Document.SalesInvoice`, `Catalog.Companies`) and maps to both metadata
name and presentation; the source UUID is not mislabeled as a metadata name.
Malformed records, missing required fields, nonzero exit, timeout, oversized
output and changed journal closure fail closed. The prior snapshot copy,
disposable IB, BSL injection, Designer load and four Enterprise sessions have
been removed; there is no automatic legacy fallback.

A direct bounded control exported the retained September 23 journal in JSON:
324 records, 240,777 bytes, 564 ms, exit code 0 and empty stderr. It contained
all required event, level, user, metadata, transaction-status and comment fields,
including the `Committed`, `RolledBack` and `NotApplicable` laboratory records.
The two-file, 68,035-byte journal closure was unchanged:
`0912787526bd5e3c8971a41034293fbb9023ea856e2b0e04954c9ff50a577f24`.

The final exact-product E2E invoked the real companion three times. A combined
event + level + user + metadata selection completed in 630 ms, produced 39
matching rows / 18,825 XML bytes and correctly reported complete coverage. Its
retained page and exact record lookup each completed in 1 ms without changing
exporter metrics. A nonexistent event completed in 574 ms and returned a valid
complete-empty result (zero rows / 92 XML bytes). A broad unfiltered request
completed in 618 ms, saw 324 rows / 185,480 XML bytes, retained 100 and correctly
reported `partial` / `maximum_count_exceeded`. Native export time was 504–544 ms
per selection. The work root was empty and the two-file, 68,035-byte journal
closure still matched after all three runs.

### Agent-usable long text and failure diagnostics

The follow-up review exposed two response-boundary defects outside native
acquisition. First, a permitted long comment could make the complete 32 KiB
companion response collapse to `blocked/output_limit`. Select and page now return
a 256-byte UTF-8-safe comment preview plus `commentContinuation`; the complete
comment remains in the existing retained selection. `eventlog_record` accepts an
optional closed pair `commentOffset` / `commentMaxBytes` (maximum 16 KiB), returns
the next character-aligned chunk and its exact byte counts, and rejects offsets
inside a UTF-8 code point. Source coverage and visible-text continuation are
separate: preview truncation does not change event counts or coverage.

The offline end-to-end regression uses one 16,423-character Cyrillic comment and
nine 2,002-character Cyrillic comments. Select, a ten-record page and every
record chunk remain within the final 32 KiB serialized companion envelope. The
long comment reconstructs byte-for-byte from generated offsets, an invalid byte
offset fails closed, and an exporter call receipt remains exactly one. A separate
worst-case twenty-record page combines every bounded semantic field with long
Cyrillic comments and also remains below the final envelope.

Second, `ibcmd` stderr is no longer discarded. A dedicated reader drains it
concurrently, hashes all received bytes and retains at most the first 4 KiB. On
nonzero exit the public response contains the observed `ibcmd_process` stage,
integer exit code, a one-line 512-byte safe projection when stderr has safe
content, and an opaque evidence ref. Empty stderr is marked empty rather than
given an invented process message. Credentials, paths, endpoints, email-like
values and long token-like values are redacted from that projection. The bounded
original prefix, total byte count and digest are stored mode 0600 under the
deployment-owned work root with a one-hour logical TTL and an eight-receipt cap;
expired receipts are removed on a later failure. The stdout protocol remains
clean, oversized stderr is drained without unbounded memory/disk use, and the
owned process group is stopped so descendants cannot outlive the failed export.
Offline regressions cover safe exit-7 text, empty stderr and a 12 KiB sensitive
stderr stream; they verify safe model-visible output, retained evidence, explicit
truncation and descendant cleanup.

The later full-wire review found three remaining presentation defects and the
same response layer now closes them. Registration-log select/page/record output
is measured after the complete compact JSON envelope, UTF-8 encoding, JSON
escaping and final newline. List responses target 24 KiB rather than treating
the 32 KiB hard ceiling as a normal payload size. When all requested rows do not
fit, the response keeps window/filter/count context, source coverage, selection/record
refs and at least one useful row, and adds a separate `display` state with the
actual `returnedCount` and strictly advancing `nextOffset`. Following that
offset pages the retained selection without gaps or another export. Source
coverage, response display and comment continuation remain three distinct
states. Facets may be shortened only after rows; this is marked separately and
the underlying facts remain addressable through retained pages/records.

An exact-record comment is also fitted against the final serialized envelope,
so JSON escaping (including many backslashes) cannot turn the whole response
into `output_limit`. The returned UTF-8 byte offset is recalculated from the
actual shown fragment. Continuation requests smaller than four bytes are
rejected; every successful incomplete read is non-empty and advances. Offline
controls reconstruct a 20,004-byte backslash/Cyrillic comment exactly, reconstruct
`Я😀Я` with four-byte requests, page twenty maximal-field Cyrillic records with
no skipped or duplicate `selectionIndex`/`recordRef`, and observe exactly one
exporter invocation across select/page/record continuation.

Exporter failure JSON now uses unescaped UTF-8 and compact separators before
the existing 1,024-byte bounded receiver. A safe 515-byte Russian diagnostic
therefore retains `source_process_failed`, `ibcmd_process`, exit code, safe
meaning and the opaque private-evidence ref rather than becoming generic
`source_failed`. Empty stderr has no invented process message and remains
explicit through `diagnostic.state=empty`. The prior bounded capture, redaction,
mode 0600, one-hour TTL, eight-receipt cap, process-group cleanup and clean
stdout protocol are unchanged.

Example of the short model interpretation produced from the real tool chain on
the offline synthetic fixture:

```text
В выборке два события, coverage complete. В 10:00:01 пользователь u-1 записал
Document.SalesInvoice; результат Committed, комментарий «Счет записан».
В 10:00:02 тот же пользователь изменял Catalog.Companies; результат RolledBack,
комментарий «Изменение отменено». Текст обоих комментариев показан полностью.
```

The next detail call is direct, not a guessed byte-budget retry:

```json
{"recordRef":"<exact recordRef from the chosen row>"}
```

If `display.partial=true`, the next page call instead uses the same exact
`selectionRef`, the returned `nextOffset`, and a small `limit`.

## Verification and limits

Static tests cover:

- fixed `ibcmd` argv, JSON-sequence projection and exact event/level/user/metadata filtering;
- symlink/source-overlap rejection, byte/deadline bounds and immutable-journal checks;
- domain-side filter reapplication;
- valid empty versus unavailable and malformed source results;
- the platform-over-return and exact-boundary partial states;
- stable paging and one-record reading after source mutation;
- tamper, expiry, forged-ref and unknown-field rejection;
- companion/plugin/schema/manifest registration parity.

The exact `ibcmd` candidate is proven on the retained quiescent cut from the
running disposable 8.5.1.1150 source. It does not claim atomic acquisition from
an arbitrarily changing production journal or compatibility with other 1C
builds. An operator must first produce a stable copied journal cut and provide
the matching official utility. The complete local suite and exact-head CI on
Python 3.9 and 3.12 must pass before the PR result is accepted. No
deployment, credentials, service, database, index, Hermes core, source
configuration, snapshot, live infobase or production environment is changed by
this PR.

## Rollback

Revert the #80 commit. No data migration is required. Task-local retained
selections expire after one hour and may be removed only as deployment-owned
`.local/` data. The #76/#78 companion/plugin behavior remains unchanged.
