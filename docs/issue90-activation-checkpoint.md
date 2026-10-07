# Goal #90: current-journal activation checkpoint

**PARTIAL / BLOCKED — current-journal access works; active registered fresh-event acceptance is incomplete.**
No new external review was initiated. Owner's unified reversible-enablement authorization:
[Goal90 comment](https://github.com/Kwentin3/1c-agent-harness/issues/90#issuecomment-6040941684).
This supersedes the earlier request for a separate activation approval; it does not supply missing credentials or prove deployment.

## Continuation #96, 2026-10-07

[Sanitised continuation receipt](../experiments/issue90-current-source/continuation96-checkpoint.json).
This continues PR93, not a new Goal, implementation, budget or PR. Local/PR93 HEAD at
intake was `2dbfdb494f706c0748ee3091c5c47d6fd4347820`; main remains
`646273a44e47223d920911bdaec4bd35ae2b9ed6`. PR95 is a separate, disjoint access
artifact: its three changed files do not overlap PR93; no automatic merge order is inferred.

- One new **non-native** current-journal probe passed in **6.395034s**. Its exact stdout
  hash matches the accepted post-cleanup probe. Reference/image/VRD/binary pins, UTC,
  UID10001/GID33, RO mounts and write-open denials remain admitted.
- Canonical ledger read succeeded in **3.232954s**: SHA256
  `86d8fc3551e2c81ca841fa455633ca42f013221a0dc73b81547893d9943fc24d`,
  **help2/3, exports4/12, session cycles0/2, native8.480200893012807/900s**;
  no STARTED entry. No native export, session cycle or coding attempt was spent here.
- All31 local staged source/plugin files still match exact Git bytes. Original installed
  wrapper/plugin match their rollback copies; active artifact remains the old415782… seal.
- **A previously missing activation prerequisite was demonstrated:** the candidate plugin
  checks one artifact seal for every operation (`hermes-plugin/adapter.py:257–269`). The
  old diagnostic companion returns415782…, so the offline candidate adapter rejects its
  real successful TechLog response with `companion_artifact_mismatch`. Installing only
  the eventlog pair would therefore break TechLog; the guard was not weakened.
- A separate23-file exact diagnostic companion was staged on the **existing** diagnostic
  executor, without changing its installed launcher. The derived startup preserves old
  cwd, selected environment and retained-reference roots. Its actual response has the
  candidate d22e95… seal and otherwise identical diagnostic facts; the offline candidate
  adapter accepts it. This is **staged parity**, not active-registry acceptance.
- A fixed dispatcher was prepared from the **original installed wrapper**, preserving
  its entire coding branch and known_hosts binding byte-for-byte; the raw source template
  has different deployment pins and must not be installed blindly. Its new destinations
  are the staged eventlog and matching diagnostic companions. Shell syntax passed; no
  active wrapper/plugin was replaced. One remote-source preparation failed syntax
  validation before any writes, was retained separately, then corrected and locally
  compiled before staging; native0 throughout.

### Actual stop and supported between-run handoff

Demo HTTPS still returns **401/Basic**. No demo credential key was found in the active
profile `.env` or admitted environment; configured Bitwarden source is disabled. One
request for a native secret locator was made; none was supplied. No password recovery,
guessing, reset, owner-cookie reuse or authentication bypass was attempted. Dedicated
CDP still refuses connection; no ordinary browser executable was found on PATH.
Two session witnesses and registered select/page/record/comment acceptance remain NOT_RUN.

The protected activation area contains an exact installation/rollback handoff to the
existing lifecycle owner. After this run ends, use the supported exact-ref native plugin
install and the prepared matched dispatcher, then the authenticated WebUI public
`POST /api/health/restart`; require its terminal receipt from
`GET /api/runtime/restart/status?request_id=…`, not merely in_progress. This uses the
existing active-run guard (`/app/api/plugin_activation.py:99–125`), not a registry patch
or self-restart. On refusal/failure restore the original pair at the idle boundary.
No new approval or review is needed. Neither a prepared handoff nor Plugin Doctor is
activation. A new ordinary chat must prove loaded identities and registered behavior.
Coding access remains revoked: source-only tests and an unchanged branch are not live
coding parity; key91 was not restored. Re-enabling that route would still need a matched
installed companion, not acceptance of an old artifact.

### Cost and verification

Historical full-query minus raw-capture latency is **9.128731 / 9.164487s**, including
accounting and local work; it is not a measured per-hop attribution. A new read-only
ledger round trip took3.232954s. No optimization or improved full-query result is claimed,
mandatory accounting remains, **<=10s is still NOT MET** and visibility<=30s NOT_RUN.
Do not spend further exports merely to repeat historical events while authentication
and registered activation remain missing.

Source suite **373/373 PASS,178.109s**; wrapper9/client1 source tests PASS; staged Plugin
Doctor PASS/nine tools. Registered old TechLog remains working. Existing debt dispositions
are retained, not reopened or rerun. No source/configuration/business-data/logging-policy,
SSH configuration, terminal backend, heavy runtime, demo or live plugin changes occurred;
only task-owned software stage/receipts and this documentation were added. No merge/release.
The source-only suite reproduces with `python3 -m unittest discover -s tests -v`; live
ordinary-chat acceptance cannot be reproduced without the explicit secret/browser and
between-run lifecycle prerequisites. Goal90 remains OPEN, not PRODUCT PASS.

## Executed result, 2026-10-07 (preceding checkpoint)

Exact runtime source: `64420b4efc960d8b0554548a0c4d85328b3bfdd4`, tree
`9c2a337a8b9cd0896665e4b5575f67940e9fcaab`.
31 installed code/plugin files were extracted from `git archive` and individually
compared to `git show` bytes. Plugin Doctor passed import/discovery and all nine registrations.
The original active wrapper/plugin were backed up and remain unchanged. The isolated
installed companion was executed against the real current journal through the existing
restricted capability, not against a fixture or a previously retained payload.

- First fresh capture: 878 source records in the requested 24-hour interval; all had
  Information level. Error-filtered retained selection contained zero records. It stayed
  **partial**, not an assertion of complete error absence.
- Second fresh capture: 196 source records in the observed source-local morning interval.
  Positive selection retained 100 distinct records; five pages returned all 100 without
  duplicates in that retained set.
- `record` and UTF-8 continuation read a 55-byte comment in four calls with a 16-byte bound.
- First selection's persisted bytes and page response were unchanged after the second query.
- Neither selection contains an acceptance witness for an event newly generated by this run.
  Source event timestamps are historical relative to capture; they are not treated as a
  freshness fence. Append/rotation/new-event visibility remain untested.
- Both captures admitted the same expected demo reference/image/VRD and official binary;
  before/after journal inventories were unchanged. This is not a flush/consistency guarantee.

Retained captures are private. No raw records/comments, credentials or connection strings
are published. [Sanitised execution receipt](../experiments/issue90-current-source/activation-checkpoint.json)
contains measured counts, hashes, statuses and costs only.

## Measured cost and budget

| Operation | Wall seconds | Native seconds | Output bytes |
|---|---:|---:|---:|
| First selection, including task-only remote ledger accounting | 18.826470 | 0.616627 | 590087 native JSON |
| Second selection, including task-only remote ledger accounting | 17.048482 | 0.570570 | 130666 native JSON |

Raw capture transport, excluding ledger reservation/completion, measured 9.697739 and
7.883995 seconds respectively. Those shorter measurements are **not** full selection
latency and are not substituted for the <=10-second product threshold. Page/record calls
used retained data and launched no further native exports. Visibility <=30 seconds was not tested.

Canonical ledger was reserved before each native call and read back after completion.
Cumulative budget: **help 2/3, exports 4/12, session cycles 0/2,
native 8.480200893012807/900 seconds**, no STARTED entries and no reset.
Ledger SHA-256: `86d8fc3551e2c81ca841fa455633ca42f013221a0dc73b81547893d9943fc24d`.

## Actual prerequisites, not additional approval gates

1. **Demo authentication is absent from admitted secret sources.** Checked native profile
   `.env` key names, relevant running-process key names, profile secret files and secret-source
   configuration without printing values. Demo HTTPS returns 401/Basic. No password was
   guessed, recovered from transcript, reset or put into workspace/Git. The owner was asked
   for a native secret locator, not to perform the test or repeat authorization; none arrived.
2. **Automation browser is unavailable:** the configured dedicated CDP endpoint refused the
   connection. An existing owner-browser session is not an accessible Hermes session.
3. **The supported WebUI activation transaction refuses an active chat run.** Source checks:
   `/app/api/plugin_activation.py:99-125` checks active streams/runs before forced discovery;
   `/app/api/runtime_restart.py:56-107` owns activation and the separate Gateway lifecycle;
   `/app/static/ui.js:9794-9803` calls the authenticated public control route. There is no
   supported active-run activation route. A fresh CLI registry or direct staged companion
   is not the current WebUI registry. No internal monkeypatch or restart-guard bypass was used.

The staged candidate is **not active in the ordinary chat registry**. Original active
artifact `sha256:415782d4419b82987e51f8539f0030cbcd3b3c5f3ae483541a1481bf25aa0ef9`
and wrapper SHA-256 `e67bea4eb6f998097811639ff0701687b3b2ab0f7f3c44a631dc559b1a468326`
were independently read back unchanged. Candidate artifact remains
`sha256:d22e95c3317acae51cb0a059333f2ea3917f3ce1bd291f7757556097ea2e52c7`.

Next work within the existing owner authorization: restore usable authenticated demo
session access, activate the matched deployment through the supported between-run lifecycle,
then perform the two authorized login/logout cycles and fresh registered selections,
pages, record/comment continuation and visibility/full-query measurements. A separate
approval or review cycle is not required. New credentials/permissions must still be supplied
through an admitted secret/access channel; no authentication bypass is authorized.

## Verification and preservation

- `python3 -m unittest discover -s tests -p 'test_eventlog*.py' -v`: **50 PASS, 21.088 seconds**.
- `hermes plugins doctor /workspace/1c-harnest/hermes-plugin --ci`: **PASS, nine tools**.
- [Existing exact runtime-source CI](https://github.com/Kwentin3/1c-agent-harness/actions/runs/37616334699):
  Python 3.9 and 3.12 SUCCESS. No runtime-source bytes were changed in this checkpoint.
- Registered `one_c_observation_info` before/after returned the same bounded UTC source
  coverage: three files, 47170 bytes, EXCP/EXCPCNTX. This verifies the existing retained TJ
  route, not current demo eventlog or native coding recovery.
- Ordinary local terminal and authenticated GitHub reads worked. Coding key was not restored;
  no new native coding regression run was attempted.
- Demo/service/config/auth/logging policy, source/snapshot and active plugin/wrapper were not
  modified. Journal write-open/read-only protection remains enforced by the existing capability.
  Whole current IB byte identity was not measured and is not asserted.
- No merge/release, service deployment/restart, new review, persistent service/timer or raw-data
  publication occurred. A staged private installation is not active installed acceptance.

Source-only tests reproduce from the runtime commit using the commands above. Live reads
require the previously accepted restricted route and task-owned exact installation; private
payload replay is not advertised as a clean-environment reproduction. Every additional native
export or session cycle must continue the same canonical ledger. Retained stage, rollback and
receipts remain in the workspace's protected `.local/issue90/activation/` area.
