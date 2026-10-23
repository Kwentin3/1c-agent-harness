# Goal #99: current-1C logging lifecycle

The agent must inspect and configure logging for its admitted current 1C,
read bounded current evidence, and restore its own temporary settings. Existing
coding tools and their SnapshotRef/oracle admission remain unchanged.

## Owners and public contract

- The existing HOME forced handler verifies reference/image, service,
  VRD/File binding, timezone and journal directory identity. Its `_binding()`
  serves legacy capture and the explicitly selected product route.
- One additional `one_c_logging` tool has closed `status/start/stop` and
  `registration/technological` choices. Status returns `targetRef`; start requires
  that ref and `errors/diagnostic`; stop requires the collection's `captureRef`.
- Registration settings use the actual native `EventLogSettings` web form.
  Start only adds necessary levels, preserving existing logging. Preserve the
  baseline before Save, compare expected levels, preserve storage period, confirm
  persisted settings in a fresh form, and exit each owned session normally.
  There is no claim of an atomic lock against unrelated 1C administrators.
- Technological settings use native `logcfg.xml`: preserve original bytes,
  permissions and ownership or absence; add one narrow destination; restore only
  if the current bytes still match our configuration. Foreign edits conflict.
- Reads reuse existing registration selections/pages/comment continuation and
  technological observations/group/record navigation. No new parser or index.

Fixed deployment paths are in `deployment/goal91/current-logging.json`; model
arguments cannot choose them. TargetRef hashes the verified reference, image,
VRD, IB path and journal directory device/inode. It is not a coding SnapshotRef.

## Native deployment and maintenance

`current-harness-v1` uses the existing SSH alias/key/forced handler and access
lock. Deployment selects immutable, root-owned source through an explicit
`CURRENT_HARNESS_SOURCE` or an adjacent root-owned canonical `one-c-source.json`.
The pin is selected under the same lock as the handler/pin installer.

The legacy `current-journal-v1` route and #90 accounting remain unchanged.
Product capture reuses the existing bounded read-only worker under its own
selected capability; it neither reserves nor resets historical #90 rows.

The existing reference already contains Playwright and Chromium. Registration
commands run as UID/GID33; only fixed technological config writes use the
existing container administration boundary. There is no new service, listener,
key, mount, scheduler or Hermes core patch.

The deployed platform's version `conf.cfg` points at `/opt/1cv8t/conf` through
`ConfLocation`; the fixed log configuration uses that shared native directory.
Read-only inspection found one published IB. Technological logging applies to
processes reading that config; another deployment must establish its own allowed
scope. [Native ConfLocation documentation](https://kb.1ci.com/1C_Enterprise_Platform/Guides/Administrator_Guides/1C_Enterprise_8.3.23_Administrator_Guide/Appendix_3._Description_and_location_of_internal_files/3.16._conf.cfg/3.16.2._ConfLocation/).

`configured` proves the configuration write, not platform reload or fresh-event
capture. Native polling is documented as 60 seconds; actual reload needs observed
evidence. [Native technological log documentation](https://1c-dn.com/library/tutorials/1c_enterprise_administrator_guide_file_mode_8_3_27/).

## Evidence and acceptance boundary

The matched source is installed and its ordinary-chat case is accepted within
the admitted demo scope described below. This does not establish portability
to other IBs/platform versions, production-1C acceptance or a performance SLA.

The actual native web form was opened in the current demo, its five level choices
and current `Week` storage period were read, then Cancel/File/Exit returned to
native Log in. The automated read-only inspection took 5.56 seconds; it is not a
performance acceptance threshold. A second native check used the exact candidate
adapter to read, Save the same values, then read the persisted policy in a fresh
session. Levels and storage period remained unchanged; all three visits exited
normally. The full sequence took 14.42 seconds. No business data changed.

A separate external-processor approach built successfully on a disposable blank
IB but failed before its entry marker. It was removed from the new product path;
build success is not represented as native logging-control success.

### Installed ordinary-chat acceptance — 22 October 2026

- Installed source: [`706b34e7aec767dccff7b0bccbc67a265c0b7039`](https://github.com/Kwentin3/1c-agent-harness/commit/706b34e7aec767dccff7b0bccbc67a265c0b7039).
  Matched core/plugin artifact:
  `sha256:bdaafda26024b0b8e66f160a26cb6954720f906a027df1c2fafe60f85686c901`.
- Matched Hermes recipe: [`6a21772bce6a623f80ed0f26bcd1baed69983ad7`](https://github.com/Kwentin3/hermes/commit/6a21772bce6a623f80ed0f26bcd1baed69983ad7).
  The existing native PluginManager installed six plugin files at that source;
  both Agent and engineering source generations verified the same 44-file pin.
- Exact-source [Linux CI run 39809606959](https://github.com/Kwentin3/1c-agent-harness/actions/runs/39809606959)
  passed on Python 3.9 and 3.12. Matched Hermes Shared
  [39809651730](https://github.com/Kwentin3/hermes/actions/runs/39809651730), Office
  [39809651951](https://github.com/Kwentin3/hermes/actions/runs/39809651951) and AgentBridge
  [39809651924](https://github.com/Kwentin3/hermes/actions/runs/39809651924) checks passed.
  CI supplements the executed case; it is not its substitute.

One ordinary model chat used the registered public tools to inspect and start
both diagnostic collections on the same verified current target, read current
evidence, drill down, stop both using the exact returned refs, and inspect final
status. All 20 tool calls have matching durable results and the stream ended
inactive. This used the supported private trusted-operator path to the ordinary
WebUI chat/model owner; public Authelia SSO was not tested.

The comparison included source records and omissions, not only tool statuses:

- JR native capture, retained selection and reconstructed public records match
  as multisets of Date/Event/Level/Comment: **13/13/13**, zero omissions or
  invented records from that captured output. Its output SHA256 is
  `d770260392e835a1d4a2820a2379e252cf2f1c79d5db7e1d85508c25e92f4a57`.
  Temporal coverage remains **partial**, with `capture_consistency_unproven`
  and `completeThrough=null`; this is not proof of complete temporal history.
- TJ produced natural EXCP evidence after the native polling interval, without
  a manufactured business error. Source headers within the requested window,
  retained records and public selection match **12/12/12**, with zero omissions;
  11 groups, group drilldown and exact-record drilldown refer to that selection.
  Later source appends do not alter the retained selection.
- JR returned to its original four levels, confirmed through the native form.
  TJ returned to its original configuration absence; its owned state/backup
  were removed. Retained evidence remains available under its original TTL.
  Source/CI tests cover foreign-change conflicts; no unrelated administrator's
  live settings were changed to manufacture that test.
- The same chat successfully reused the exact `SnapshotRef` from `one_c_open`
  for a bounded positive `one_c_narrow_context` result. Existing coding owners
  and SnapshotRef/oracle admission remain preserved; this was not a new coding
  write/native-verification experiment.

The maintained installer applied the handler/source-pin pair under the existing
access lock and retained its previous pair. The exact reverse pair passed
rollback preview; the accepted installation was not rolled back. No Hermes
restart, new permissions or business-data write was part of this delivery.
Post-case Gateway/WebUI active-agent/run/stream counts were zero.

Known unresolved Hermes core issue: its native failure classifier marks nested
diagnostic `error` data as a failed tool result and increments the failure
streak. Both successful TJ drilldowns in this case received that annotation;
the agent correctly read the domain results and completed restoration. The
classifier is **not fixed in the installed runtime**. This limits any broader
claim about uninterrupted longer workflows; the acceptance above is the
demonstrated functional Harness case only.

Operator evidence is retained outside Git at
`comfyUI/.local/harness-goal99-20261022/`. The following immutable locators bind
the claims without publishing raw logs, credentials or private transcripts:

| Receipt | SHA256 |
| --- | --- |
| `acceptance.safe.json` — source/cache/public parity and restoration | `4e2fe0169e0d9c1a891bed54a0c8ded1c312c9de68d85adcaf9cc0f532047880` |
| `chat-case-start.private.json` — ordinary-chat status/start | `52c2e891491b5c867ad2ef783ed9ae51045327de4a1692c41ed1136ee664f8f5` |
| `chat-case-finish.private.json` — reads/drilldown/stop/coding | `9295f86ee17352fcbe089d6149ef48cb1787566bfb75b9ff9b53890a0d061072` |
| `log-source-after-stop.private.json` — source/config restoration | `9317402639d5f29b291322e3e5c08847cd06b866a67a753ca3d82b84b1ea40d5` |
| `home-apply.safe.json` — paired handler/pin install | `75b194a7ffdcfd643723b6b74b5677499b3ebff412b98087c0aeaec61cc373de` |
| `runtime-stage-apply.safe.jsonl` — matched 44+44 source files | `e89f2b20633bff183f2389149247405d89c67fedb4706c905ec5957bdbd923ae` |
| `runtime-launcher-apply.safe.json` — existing launcher activation | `8957cea44232fcefd743eb7878d7cf2e507c26b60a13768982ea7ef7e69d517a` |
| `plugin-apply.private.json` — native pinned PluginManager install | `fba9041bf69e24373cdcca638b70eb9f97556e9e790aed523c9146bbb8e725e1` |
| `post-case-idle.safe.jsonl` — final native idle/pointer readback | `865d2f2aeaed6ad7e2db1009681e4a39c731c71e2aa0f841fa173b7a9b2cdd9a` |

PR #100 and the matched Hermes PR #178 remain draft/unmerged at this checkpoint.
This receipt does not authorize merge/release or activation of a Hermes core fix.
There is no new 5/10/30-second performance experiment in this goal.

Refresh matched core/plugin artifact IDs with `python scripts/update_release.py`.
The existing historical eventlog EPF sources and the new deployment routes belong
to this artifact closure. Native receipts and private evidence stay outside Git.
