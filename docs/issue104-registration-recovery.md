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

The repair is installed on 23 October 2026; both chat captures finished, but the
owner's true original policy is **not yet confirmed restored**. Refresh matched release IDs with the maintained
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

### Installed source and executed case — 23 October 2026

- Source `e4ea89f6b14d6d07dce350439f022e8763279365`, matched core/plugin artifact
  `sha256:b08132ccbe0fddb1a0d2199e410ea37a4f89d21b4af238503d69f906739fa1a1`.
  PR105 merged as `9602f28309b99707182b46fc21b13bb04b58fe6f`.
- Hermes recipe `7c5385d693351bea989a1d20b8f50a0702bd8429`, PR182 merged as
  `18d29bf6d9619e27c7dd3ee9854512a985425644`. The 44 Agent files, 44 engineering
  files and six native PluginManager files were matched to this pin. HOME source
  pin and Agent launcher switched through their existing owners. Handler bytes,
  target binding and coding oracle did not change. Exact HOME/launcher reverse
  previews passed; no rollback was applied. Installation needed no restart;
  the later live-case recovery required a separately admitted service restart.
- [Required source CI39932574657](https://github.com/Kwentin3/1c-agent-harness/actions/runs/39932574657)
  passed 550 tests on each Python3.9/3.12 job (three/two environment skips).
  The 31 focused Linux lifecycle/adapter checks and 27 plugin/artifact/coding
  checks passed. Matched Hermes required Shared39932906288, Office39932906266
  and AgentBridge39932906286 checks passed.

The owner admitted temporary Error/Warning preparation, a single ordinary chat
and restoration of the true original all-four policy, without restarts/business
writes. Native compare-set confirmed four -> Error/Warning without changing
lifecycle files. The new ordinary chat is `eed362c13b53`, using the supported
private trusted-operator WebUI/Gateway/model route; public SSO is not part of this
acceptance.

The first diagnostic start genuinely added Information/Note. A separate read of
the native settings confirmed all four levels and the owner's saved baseline
Error/Warning. Exactly one bounded native JR export was performed. Native,
retained and public Date/Event/Level/Comment multisets match **13/13/13**, including
duplicates, with zero omitted or invented captured records; timestamps also
match as exact strings. Output SHA256:
`6ab7fd2d371b699b34b9958f1e3c3bb4db49a61e6aca9f19903c57ee4a5d06aa`.
The same chat expanded an exact record and its first stop returned `ok/restored`.
Temporal coverage remains partial (`capture_consistency_unproven`); this is not
proof of complete history for the time window.

The attempted next start and status returned `blocked/native_exit_unproven`.
Read-only inspection found a new `prepared` capture, not an incorrectly completed
operation. The native page's actual detailed error was **Training version
limitation reached / Infobase connections limitation reached**. The generic Exit
reason alone did not establish that cause; the revealed native details did.
One earlier malformed extra status argument was rejected by the native tool
schema before invocation and the model corrected it; it is retained as an error,
not counted as a successful native operation.

No artificial live failure, second export or state-file edit was used.
There is no confirmed explanation yet for how connections accumulated.
Read-only publication inspection found no general `<pool>` override. The native
[file-mode administrator guide](https://1c-dn.com/library/tutorials/1c_enterprise_administrator_guide_file_mode_8_3_27/)
documents the default idle connection age as 20 minutes. One observation after
that idle interval failed to restore access. This does not prove a pool defect
or authorize changing the publication. Unrelated OData/analytics pool settings
do not establish the web-client pool's timeout.

The owner then admitted one `systemctl restart 1c-jet-demo.service`. It restored
native access. The operator's preview missed the unit's `ExecStopPost` Docker
stop and `ExecStartPre` Docker start: despite the stated no-container-restart
scope, that service restart stopped/started the existing demo container. Its ID
and image were preserved; its start time changed to 23 October 10:56:31 UTC.
Hermes and its containers were not restarted. This is a recorded operational
scope error, not a claim that all planned boundaries were kept.

A fresh native Get confirmed all four levels and the unchanged second prepared
capture. In the **same chat**, a registered start adopted exactly that saved
capture, its matching stop returned `ok/restored`, and final status returned
`ok/unchanged` without an active capture. Both distinct captures are now stopped,
with 16 matched durable tool calls/results overall. The stream ended inactive.
No third collection or second export was requested.

The subsequent operator action to return the owner's true original all-four
policy failed. One read-only diagnostic again revealed the native training
connection-limit error; the saved second capture remains `restored` and untouched.
Actual current native levels are unknown. Therefore the overall goal is still
incomplete. The owner explicitly accepts the connection limit as a normal
training-edition restriction, not a Harness defect to repair in this goal.
This does not itself confirm native levels or authorize another restart.
A concrete cleanup is prepared: one separately admitted service
restart (explicitly including demo-container stop/start), immediately followed by
the existing guarded native compare-set and fresh confirmation; no extra chat,
collection or export. This additional restart has **not** been executed or
authorized. Private evidence stays under the ignored operator directory above.
