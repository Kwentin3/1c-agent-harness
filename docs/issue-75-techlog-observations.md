# Issue #75 — platform-authored 1C technological-journal observations

## What is observed

The source is the **1C:Enterprise technological journal** emitted by the installed
Linux training runtime **8.5.1.1150** in an isolated file-mode Jet run. This is not
a Harness receipt, test report, runner exit code or synthetic fixture.

The thin provider `one_c_harness.techlog_observation` has exactly two operations:

- `observe`: filters one source-date and source-time-token interval, groups selected
  platform event names, and retains a bounded immutable task-local selection;
- `expand_observation`: returns a requested page from exactly that retained selection.

The first token in the verified Linux log has the shape `25:25.291000`. Its precise
calendar/time-zone semantics were not established from this source, so the API calls
it `sourceTimeToken`, rather than inventing an ISO timestamp. The file-date token and
this source token are both preserved; file mtime is not used as event time.

`ONE_C_HARNESS_TECHLOG_ROOT` is executor-local configuration. It is absent by default,
which returns `source_unavailable`; it is never supplied by a model request, project
contract, SSH argument, or plugin argument.

## Real isolated run

A task-owned hardlink copy of the training runtime carried the only `logcfg.xml`.
The shared runtime had no `logcfg.xml` before or after. The selected configuration
logged only platform event `EXCP` into a task-owned directory. The native runtime
part was limited to 25 seconds; the whole create/load/runtime lifecycle took 91.488
seconds because the existing runner has separate setup stages.

Result: 3 platform log files, 47,170 bytes, 100 platform records (`EXCP` and
`EXCPCNTX`). No `1cv8t`, `1cv8ct`, or Xvfb process remained. The initial broad-log
canary produced 120,507,830 bytes and is explicitly not the acceptance source.

A real read-only companion query over the small source selected the actual source
window `260918 / 25:25.000000–25:25.999999` and event `EXCP`:

```json
{
  "summary": {"source": "1c_techlog", "recordCount": 1},
  "groups": [{"event": "EXCP", "count": 1}],
  "snapshot": {"stable": true, "partial": false}
}
```

Its group expansion returned the one safe source record. It identified the event and
source token but marked `process`, `OSThread`, `Exception`, `Descr`, and the body as
`<hidden>`. Hash manifests of all source log files matched before and after the
query. Changing a source log after `observe` is covered by a regression test: later
`expand_observation` uses the retained snapshot rather than rereading the source.

## Hermes boundary

The repository plugin registers two new closed tools:

- `one_c_observe`
- `one_c_expand_observation`

They serialize closed JSON into the existing public terminal tool and then into the
installed companion. `open`, `narrow`, and `verify` are unchanged. The task-local
companion route was exercised against the real source. The currently deployed Hermes
plugin is not changed by this branch; installing this tool pair would require a
separate owner-approved deployment/restart, so this is not claimed as full deployed
Hermes E2E.

## Limits

- Only the observed 8.5.1.1150 training-edition log grammar is supported.
- The source does not establish cluster activity, CPU use, BSL causality, or a cause
  of a production incident.
- A retained selection is capped at 200 records. If exceeded, `snapshot.partial` is
  explicit; it is not a monitoring database.
- Safe expansion intentionally hides values and full body. The raw log remains only
  in the executor task area.
