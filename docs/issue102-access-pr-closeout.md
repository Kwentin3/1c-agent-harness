# Access source closeout — #95 / #98

Date: 23 October 2026. Tracks [Goal102](https://github.com/Kwentin3/1c-agent-harness/issues/102).
The owner requested final Git delivery of the remaining access sources while
preserving the accepted [Goal99 Harness](issue99-agent-logging.md).

## Decision and source ownership

The old branches contain useful operational source and dated evidence that were
not in `main`. They also contain an obsolete journal implementation. Integrate
their history and useful files through a normal Git merge, keep the accepted
current journal at its existing deployment path, and resolve Git's directory
rename detection explicitly. No running file, plugin, key, worker or setting is
installed or changed by this source delivery.

Compared source identities:

- Base main: `4cd8d59a72f12e027564fedf979f6e2259ea4434`.
- PR95: `0dbfa1c0cd9f61e547e95d4aef3b2d28531ad39c`.
- PR98: `38e70a871f6456e70063e786e9308b4c00313b6f`, stacked on PR95.

All seven distinct changed paths across the two PRs are accounted for:

| Old PR path | Disposition / current owner |
| --- | --- |
| `docs/issue94-current-journal-access.md` | Retain historical access evidence with a prominent current-status pointer. |
| `docs/issue97-engineering-access.md` | Retain engineering/browser/source-binding history; mark old paths, grants, quotas and installation snippets as historical. |
| `docs/issue97-engineering-evidence.json` | Retain the exact dated Git blob, not a current runtime or permission manifest. |
| `hermes-plugin/deployment/current-journal.py` | Superseded by accepted `deployment/goal91/current-journal.py`; preserve current bytes, do not add the old handler to the plugin. |
| `hermes-plugin/deployment/engineering-shell.py` | Unique existing operator-owned transport; retain identical source at `deployment/goal91/engineering-shell.py`, outside the plugin package. |
| `tests/test_current_journal_access.py` | Retain seven admission/refusal checks, retargeted to the actual current journal owner. |
| `tests/test_engineering_access.py` | Retain six admission/argv/refusal checks, retargeted to the operator source's new Git path. |

The imported engineering/browser handler is not a second Harness or model tool.
It accepts the existing forced SSH command into one fixed admitted unprivileged
container. The operator owns its container identity, image, isolation and
lifecycle. The normal source merge preserves the old source commits, including
the distinct installed engineering revision, for exact provenance and recovery.

The active journal handler remains SHA256
`5e08dabc03b612ab91c17089acc87515d6a13c31746f7a78760ef518895406bc`.
The installed Harness source `706b34e7`/artifact `bdaafda2` and its closed release
inputs are unchanged. The added operator source, historical documents and tests
do not enter that core/plugin artifact closure. No release refresh, companion
source-pin change or native PluginManager reinstall is needed.

## Exact historical and live identities

The retained engineering source is identical to PR98's final operator handler:
SHA256 `9e76e384ae3080a69668df31a1e61be25acab09e76e9bd9ac1cf45561015e38b`.
The retained evidence JSON's Git bytes are unchanged:
SHA256 `2260f2eb0dcc6bf238165e6ce2a0bc4f6ac2044fb8ec4fe590fa2824429a30d4`.
Hashes refer to committed Git bytes, independent of Windows checkout line endings.

A read-only HOME inspection found the original operator-owned root0555 files:

| Existing handler | SHA256 / source |
| --- | --- |
| `/home/roman/.local/issue97-engineering/operator/engineering-shell.py` | `141d35b42acca75de0553328fde3d859a4f792577a3abef75a380fcefd9cec68`; historical engineering source `bd40827a`. |
| `/home/roman/.local/issue97-browser/operator/engineering-shell.py` | `9e76e384ae3080a69668df31a1e61be25acab09e76e9bd9ac1cf45561015e38b`; later browser/init source `c6a8c951`. |

The later source includes the existing browser-specific network/Init admission;
its engineering branch keeps the earlier unprivileged invocation. Importing it
into Git does not silently replace the earlier installed engineering file.

The same running workers remain image
`sha256:036a932ca78ec1f161b83fc3d26d663d950a8e845002c160771950ec72ce6488`:
engineering ID `1f3565421de9c18af24408e6a04db29297ba7c3dd61810ec8f6806fa77ffd5ba`,
browser ID `b547e8ac370892449a89b16148ff7f2c3a0169b25dcf0198dad6ea7077bb39f8`.
Read-only metadata confirms UID/GID10001, read-only root/bind mounts, private
PID/IPC, dropped capabilities, existing bounded resources and tmpfs. Engineering
keeps network none; browser keeps bridge and native Init. This does not grant
new network, Docker socket, host, live-IB or business-write access.

## Current invocation and validation

Hermes uses the existing pinned SSH configurations under
`/opt/data/credentials/ssh/{engineering97,browser97}/config`. A fixed read-only
`id -u; pwd` command through each actual route returned UID10001 and
`/workspace/1c-agent-harness`, exit0. No 1C executable, logging cycle, browser
client/session, export, restart, installation or business write was requested.
Transport probes are not a new ordinary-model or native-platform acceptance.

The focused local checks pass: six engineering admission tests and seven current
journal admission/refusal tests. The engineering fixture tests production
admission/argv decisions; Docker isolation is supported by separate live metadata
and prior #97 evidence, not by mocked subprocess success. Required exact-head
Python3.9/3.12 CI must pass before this integration is merged.

Existing Goal99 ordinary-chat/source-parity acceptance remains the product
reference. In particular, JR temporal coverage stays partial; historical #90
budgets and maintenance grants are not reopened. Protected credentials and raw
runtime/source evidence are not included in Git.

## Management, update and recovery

Use the [maintained delivery/rollback procedure](https://github.com/Kwentin3/hermes/blob/master/docs/infra-ops/HERMES_DELIVERY_OPERATIONS.md)
for the current Harness/journal route. The old access grant and lifecycle receipts
below are evidence of their dated scope, not standing permission to reprovision.
The existing operator remains the owner of the two isolated access workers and
their pinned credential configuration; do not change the global Hermes terminal
backend or copy a second reader into the plugin.

This source-only integration requires no runtime rollback. The existing handler
bytes, both running workers, source generations, credentials and Goal99 rollback
assets are retained. A future authorized handler update must first match the
actual installed source and its fixed worker's admission, retain the old exact
bytes/mode/owner and change only that handler. Never restore all authorized keys
or another owner's state from an old snapshot. Retiring either access entry is a
separate lifecycle decision; closing the historical PRs does not revoke it.

After this integration reaches `main`, close both old PRs with the integration
commit and this path mapping. Their branch/commit history and accepted evidence
remain reachable; their old journal implementation does not become a live owner.
