# Goal #104: repeatable registration-log restoration

## Cause and scope

The audited `28f978ed3bb420927f3f96b1c19da5d57b166689` was still current main
when implementation began on 23 October 2026. `registration_logging.control`
saved `applied` before stop and only saved `restored` after the native callback
returned. The actual web adapter can Save successfully and then fail at fresh
readback, normal Exit, or resource cleanup. A failed final state write has the
same gap. A later successful Get sees the baseline but the old lifecycle
expects the applied levels and returns `configuration_conflict` forever.

The repair belongs to that same lifecycle and the existing per-target state
file/lock. It adds one internal phase, `restoring`, durably written **before**
native compare-set. No additional state owner, service, database, public tool,
transport, permissions or Hermes core patch is introduced.

## Recovery through existing tools

Keep the exact `targetRef` and `captureRef` from `one_c_logging(start)`.
After a failed stop, the original failure remains a failure. A later call must
complete a fresh native Get, including that adapter's normal Exit, before
declaring anything restored.

| Saved phase / observed policy | Existing-interface behavior |
| --- | --- |
| `restoring` / original `before` | `status` or matching `stop` durably finishes `restored`, without another Save. `start` can finish that old operation and create a new capture. |
| `restoring` / old `applied` | `status`/`start` report `conflict/restoration_pending` with the old capture. Repeat `stop` with its exact refs to perform the pending compare-set. |
| `restoring` / another policy | `configuration_conflict`; no settings write or state deletion. Owner must resolve the unexplained policy. |
| No stop intent (`applied`) / different policy, even the original baseline | Remains a real conflict; no evidence justifies inventing an earlier owned stop. |
| Failed/invalid fresh Get | No recovery claim and no final state transition. |

Wrong target/capture cannot finish a pending stop. A failed intent write prevents
the native Save. Existing compare-set still checks expected levels immediately
before writing, so an intervening foreign policy is preserved. Native UI settings
do not provide an atomic lock or actor provenance against external administrators:
an equal-value external write cannot be attributed. Recovery at the observed
baseline makes no further policy write and establishes the desired configuration,
not who last wrote equal values.

Old `prepared`, `applied` and `restored` records remain readable. An already
wedged old `applied` record has no durable stop intent and cannot be retrospectively
declared safe merely because its current levels equal the baseline. Report the
conflict to the owner; do not delete or rewrite it by hand as a product recovery.
Likewise, the old binary does not understand a new `restoring` record. Before a
source rollback, finish outstanding captures with the new version; if recovery
cannot finish, retain the candidate and the state for diagnosis instead of forcing
the old binary or discarding state.

## Focused evidence

The regression uses different native-policy sets: baseline `Error/Warning`,
diagnostic all four levels, then back to baseline. Against the audited Git blob,
both focused methods fail: loss after restore blocks each of `status/stop/start`,
and loss before final state replacement blocks the next stop. The same checks
pass with the repair; each recovery can start and finish another capture.

Additional tests cover a failure before Save (retry stop still needed), failure
before/after final state replacement, failed intent persistence, invalid Get,
foreign changes while applied or restoring, wrong refs, and an unchanged all-four
levels case separately. The native web visit test demonstrates Save changing
the policy before Exit raises. Only native boundaries are substituted; lifecycle,
Linux locks and persistent files are real in disposable directories. No live
failure injection or business change is used.

Focused command: `python -m unittest discover -s tests -p 'test_registration_*.py' -v`.
Required Linux Python 3.9/3.12 CI remains the broad source/contract gate, including
coding and packaging. Source tests do not replace ordinary-chat acceptance.
Private operator receipts remain outside Git under
`comfyUI/.local/jr-recovery-20261023/`.

## Delivery and final acceptance

Candidate preparation is in progress; installation and final live acceptance are
**not yet performed**. Refresh matched release IDs with the maintained
`scripts/update_release.py`; the Hermes companion source lock must name that exact
Git source, artifact and file hashes. Use the existing installer/pin transaction,
immutable Agent/engineering generations and native PluginManager. Preserve the
previous matching source, launcher/plugin and HOME pin for a scoped rollback.
No rebuild or restart of demo-1C, Hermes core or neighbouring services is required
by this lifecycle change.

Before activation, confirm current owner admission, target identity, no unfinished
capture and the original native policy. If all four levels remain enabled, the
old #99 case cannot meet this goal: preparing a reduced baseline would itself
temporarily change the owner's logging. Obtain concrete admission for that
preparation and restore the owner's true original policy after the short case.

The single ordinary-chat case must visibly add missing levels through registered
tools, read bounded registration events, stop to the prepared baseline, and start
and finish the next collection. Verify native policy before/during/after and
match native, retained and public evidence including omissions. State temporal
coverage honestly; no 5/10/30-second SLA or extra speed experiment is added.

The earlier [#99 acceptance](issue99-agent-logging.md) and
[#102 access closeout](issue102-access-pr-closeout.md) retain their exact historical
identities and evidence. In #99 all four JR levels were already enabled; its
successful no-op collection does not prove actual addition/restoration of missing
levels. This goal closes that distinct acceptance gap only after the new case.
