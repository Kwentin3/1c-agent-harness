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

This candidate is not yet installed or product-accepted.

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

Acceptance still requires required Linux CI on the exact source, matched
installation/update/rollback, and one ordinary-chat case proving
the current target, temporary collection, current evidence and restoration.
There is no new 5/10/30-second performance experiment in this goal.

Refresh matched core/plugin artifact IDs with `python scripts/update_release.py`.
The existing historical eventlog EPF sources and the new deployment routes belong
to this artifact closure. Native receipts and private evidence stay outside Git.
