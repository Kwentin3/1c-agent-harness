# Goal #99: current-1C logging lifecycle

Goal: the agent can inspect and configure logging for its admitted current 1C,
read bounded current evidence, and restore its own temporary settings. Existing
coding tools and their SnapshotRef/oracle admission remain unchanged.

## Owners and public contract

- Current live target: the existing HOME forced handler checks reference/image,
  service, VRD/File binding, timezone and journal directory identity. Its common
  `_binding()` is used by legacy capture and the new product command.
- Agent: one additional `one_c_logging` tool, with closed `status/start/stop` and
  `registration/technological` choices. Status returns `targetRef`; start requires
  that exact ref and `errors/diagnostic`; stop requires its own `captureRef`.
- ЖР levels: native `GetEventLogUsing/SetEventLogUsing`, through a repository-owned
  external processor. Before Set, preserve the baseline and compare expected
  levels in the native session. Start only adds levels, preserving existing ones.
- ТЖ configuration: native `logcfg.xml`; preserve original bytes/metadata or
  absence, append one narrow log destination, restore only when current bytes
  still match the installed configuration. A foreign change remains a conflict.
- Evidence: reuse existing registration selections/pages/comment continuation and
  technological observations/group/record navigation. No new parser or index.

The fixed source-owned deployment config is
`deployment/goal91/current-logging.json`. Paths and native source never come from
tool arguments. TargetRef is derived from the verified reference, image, VRD,
IB path and journal device/inode; it is not a coding SnapshotRef.

## Product route and historical experiment

`current-harness-v1` uses the same existing SSH alias/key/forced handler. It is
disabled unless deployment selects `CURRENT_HARNESS_SOURCE`. Native backend
source must be an immutable root-owned generation inside the verified reference.
The legacy `current-journal-v1` path, its #90 ledger, quota and worker remain
unchanged. Product capture reuses the same bounded read-only worker under the
separately selected product capability; it does not reserve or reset #90 rows.

The collector has no new service, listener, key, Docker mount or scheduler.
Native registration commands run as UID/GID33; only fixed technological config
changes use the existing operator's container administration boundary. Core
Hermes is not modified.

`configured` means configuration has been written. It never means the platform
has already reloaded it or that a fresh event was observed. The documented ТЖ
poll is 60 seconds; actual reload/event coverage needs native evidence. ТЖ scope
is the processes reading that configuration, so the selected deployment must
establish that this scope is permitted, separately from per-IB ЖР settings.

## Current evidence and remaining acceptance

Source candidate only; not installed or product-accepted.

- Local Windows: lifecycle/transport/backend focused suite 32 passed, 19 Linux
  fixtures skipped; existing plugin suite 27 passed. Skips are not Linux proof.
- Native blank disposable IB: creation and native EPF build returned result0.
  Compiled EPF is 7,048 bytes. A command-line build does not prove code entry.
- Native startup has not reached the EPF client marker. Bounded diagnostic
  observation found an actual mapped platform dialog before entry. Its cause
  remains under investigation; no Get/Set capability is claimed PASS.
- These rehearsals did not connect to the demo IB, change platform config or
  restart a service. Disposable roots were removed after retained evidence.

Before acceptance: resolve native entry, required Linux CI on the exact source,
maintained matched installation/update/rollback, and one ordinary-chat case that
demonstrates current target, temporary collection, actual evidence and restore.
No new 5/10/30-second performance experiment is an acceptance requirement here.

Refresh the existing matched artifact IDs after implementation changes with
`python scripts/update_release.py`; native EPF sources and deployment routes are
included in this artifact closure. Native binary build receipts remain separate.
