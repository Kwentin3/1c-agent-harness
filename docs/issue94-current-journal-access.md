# #94 — fixed current-journal access capability

**SOURCE_CANDIDATE / NOT_PROVISIONED / HERMES_ACCEPTANCE_NOT_RUN.**
Contract: [operator task #94](https://github.com/Kwentin3/1c-agent-harness/issues/94).
This access prerequisite leaves the exporter/reader and product acceptance of
[#90](https://github.com/Kwentin3/1c-agent-harness/issues/90) with Hermes.

Read-only operator discovery confirms the exact retained demo reference/image,
running `1c-jet-demo.service`, native VRD `/jetcontrol` binding to its file IB,
and that IB's actual `1Cv8Log`. It contains LGF plus two LGP segments; service UID/GID33,
timezoneUTC. The old diagnostic namespace UID10001 has no access to this source.
Exact official ibcmd8.5.1.1150 is already installed there, SHA256
`62e72e15bb4550c4ffcf421f962c27fd1e1ddde1ba31e5bc0d7c9e0c2352dde7`.
These facts do not prove live-export consistency, coverage or product freshness.

## Concrete provisioning proposal; owner approval still required

Add one restricted forced-command entry for the existing Hermes diagnostic
identity to home SSH, with a separate pinned SSH config on Hermes. The revoked
coding key is unused. The root-owned [capability](../hermes-plugin/deployment/current-journal.py)
accepts only `current-journal-v1 BASE64_JSON`, closed probe/export requests,
bounded timestamps/format/follow, and no source/runtime/output path or shell input.

Each request resolves the running exact reference through Docker and verifies
the service and exact VRD. It bind-mounts only the current journal from that PID's
root and the already installed runtime into a short-lived worker made from the
existing executor image. Both mounts and root filesystem are read-only;
UID10001/GID33, no capabilities/network/socket/IB mount. Native output/HOME/TMP use
one32MiB tmpfs `/work`; output≤1MiB, native≤30s, controller≤40s plus exact helper cleanup,
oneCPU/256MiB/128PIDs. No retained worker, new daemon or runtime installation.

The closed probe opens16bytes of each admitted journal file and reports UID,
timezone, binary/source metadata, mount protection and safe write-open denials.
It invokes no platform. Export returns bounded exact ibcmd output as base64 plus
argv/time/hash metadata; it does not implement the Harness parser/reader or
assert a freshness fence. Failed/timeout attempts still consume #90's budget.
Source/control/error checks cannot be promoted to product PASS.

The existing diagnostic/coding launchers, source pair, credentials, demo service,
auth and logging policy stay under their current owners. Authorization is for
the new restricted entry/config and per-call read-only mounts, not general access.
The capability persists without an expiry timer. On planned service restart,
the next call resolves the same reference's new PID; identity mismatch fails closed.

Before provisioning, save exact file/ownership backups. Rollback removes only
the marked new key entry and new SSH config/capability/lock after active helper
cleanup; existing reference, data and access stay. Deployment owner is the home
operator; re-enrollment/rotation uses the established protected SSH credential
mechanism. No secret/public-key bytes or raw journal content belong in Git.

## Handoff and acceptance

Operator provides the pinned config and source identity directly to Hermes in
the current ordinary WebUI session. Before native, Hermes runs the closed probe
and invalid-source/output requests. After operator temporary helper cleanup,
Hermes repeats the same route and performs the agreed bounded export itself.
No owner relay or root-native smoke substitutes for this acceptance.

Use an UTF8 task-owned request file, base64-encode its bytes, then run:
`ssh -F <operator-provisioned-config> -T current-journal "current-journal-v1 <token>"`.
Capture stdout privately to a task-owned file before inspecting receipt/hash;
raw output must not enter public reports. Probe JSON:
`{"schemaVersion":1,"operation":"probe"}`. Export JSON also has exactly
`start`, `end` (UTC naive ISO seconds), `format` (`json`/`xml`), and
`followMilliseconds` (0–1000); it accepts no caller source/output path.

Preserve the existing #90 ledger: help2/3, export0/12, session cycles0/2,
native0.534354449s/900s at discovery. Hermes owns its accounting and subsequent
research; the operator performs no export/session witness in parallel.

## Source validation and unverified boundaries

`python -m unittest discover -s tests -p test_current_journal_access.py -v`
checks actual forced-command refusals without Docker/platform calls.
Compile both the deployment module and its embedded worker; normal project CI
remains required. Installed worker/runtime dependency and ordinary Hermes
readbacks remain **NOT_RUN** until the concrete provisioning is approved.

The file-IB→journal convention is documented by
[1C](https://kb.1ci.com/1C_Enterprise_Platform/FAQ/Administration/DBMS/Data_structure_in_1C_Enterprise_8/?language=en).
Protection uses native [read-only Docker bind mounts](https://docs.docker.com/engine/storage/bind-mounts/)
and [OpenSSH forced-command restrictions](https://man.openbsd.net/sshd.8).
