# Local Linux Relay delivery

The deployment adapter changes delivery only. The current-journal controller
continues to own demo binding, locks, bootstrap and logging. The engineering
controller continues to own container admission and unprivileged execution.
No SSH client is used in this route.

The normal command is `/usr/local/bin/one-c-harness-local --request-stdin`.
Input is the existing closed companion JSON (at most 16 KiB); stdout/exit retain
the existing owner contract. Relay must deliver input with native job stdin.

Install the **same script bytes as regular executable files**, root-owned and
not group/other writable, under these deployment-selected names:

| Path | Input/role |
| --- | --- |
| `/usr/local/bin/one-c-harness-local` | `--request-stdin`; user request |
| `/usr/local/bin/one-c-harness-local-capture` | no arguments; existing capture JSON |
| `/usr/local/bin/one-c-harness-local-logging` | no arguments; existing logging JSON |
| `/usr/local/bin/one-c-harness-local-exporter` | no arguments; existing exporter JSON |
| `/usr/local/libexec/one-c-harness-local-controller` | no arguments; privileged closed request |

Separate no-argument adapter executable names are required by the existing
exporter/logging command contracts. They contain no separate implementation.
The privileged name rejects a non-root process. A deployment administrator may
admit **only that exact no-argument command** for the selected Relay account;
for example, the sudoers command specification ends with
`/usr/local/libexec/one-c-harness-local-controller ""`. Never admit Python,
Docker, shell, arbitrary arguments or environment preservation.

Configuration is fixed at `/etc/one-c-harness/relay-local.json`, root-owned,
not group/other writable, with exactly these fields (replace locators and hashes
with live admitted values; the example is not an installable configuration):

```json
{
  "schemaVersion": 1,
  "source": "/opt/one-c-harness/ACCEPTED_GENERATION",
  "workspace": "/var/lib/one-c-harness-relay/current-journal",
  "captureBinding": "/etc/one-c-harness/current-journal-binding.json",
  "journalController": "/home/roman/.local/issue94-current-journal/current-journal.py",
  "journalControllerSha256": "EXACT_INSTALLED_SHA256",
  "engineeringController": "/home/roman/.local/issue97-engineering/operator/engineering-shell.py",
  "engineeringControllerSha256": "EXACT_INSTALLED_SHA256",
  "engineeringContainer": "EXACT_ADMITTED_CID",
  "codingSource": "/workspace/1c-agent-harness/.local/hermes-modernization/runtime/ACCEPTED_GENERATION",
  "codingRuntime": "/workspace/1c-agent-harness/.local/one-c-runtime.json",
  "codingOracleRoot": ".local/hermes-modernization/runtime/ACCEPTED_ORACLE_GENERATION",
  "journalRuntimeRoot": "/opt/ADMITTED_IBCMD_RUNTIME"
}
```

Source/runtime roots, controllers and capture binding must exist and be
root-owned, without group/other write; controller bytes must match the configured
hashes. Paths reject symlink components. This preserves the existing handler
trust model; it does not claim that user-owned parent directories are immutable.
The current-journal owner also verifies its existing source pin. Install its
new stdin-capable source and matched pin using the maintained handler installer.
Install the local-capable engineering source deliberately; the old historical
engineering source lacks the `execute` seam. Preserve old exact identities.

The cache workspace must be precreated for the Relay UID with mode 0700. It
retains selection refs locally. Logging and TJ observation state stay at their
existing locations inside the admitted demo. Coding state stays in the existing
engineering namespace. Do not copy or reset those states.

Before activation, inspect exact device/container/source identities and rehearse
the actual request through the owner. First use only `observation_info`; it
performs no native export or logging change. Its JSON does not expose technical
target identity, so source provenance also needs controller/deployment readback.
Long operations and cancellation require separate Relay lifecycle acceptance.
The existing product capture path's budget policy must be checked before A2;
this adapter does not create or reset a ledger.

Activation/rollback are operator actions. Back up the exact changed scripts,
config, source pins and isolated sudoers entry before installation. Validate
sudoers using `visudo -cf`, verify file/hash readback and exact command admission,
then enable the explicit Relay transport in Hermes. Preserve the old terminal
route during acceptance. Rollback selects the previous Hermes transport and
restores only this task's exact files/admission after active calls finish;
retain all diagnostic evidence and lifecycle state. No unit, account, grant,
installation or switch is performed by this source package.

## Reproducible operator candidate

`install-local.py` prepares the local delivery files only. It does not install
Harness generations, change the demo/reference, update controller source pins,
or enable Relay. It reads the existing source lock and reuses the adapter's
configuration validation. It refuses installation until the installed journal
and engineering controller hashes match that lock and the configured host source
generation reports its artifact ID. Source provenance/full bundle verification
remain the responsibility of the existing source delivery and handler installer.

First prepare the matched bundle/lock and private operator state directory.
The latter must be root-owned 0700; the helper will not create or overwrite a
receipt path. Use the maintained Hermes installer for the journal controller,
matched pin and demo-side source generation (preview, then the same command
with `--apply` under the admitted operator):

```sh
python3 "$HERMES_SOURCE/deploy/hermes-devops-agent/ops/install_one_c_handler.py" \
  --bundle "$BUNDLE" --lock "$PIN" --current-harness \
  --expected-current-sha256 "$OLD_JOURNAL_SHA"
```

Retain its exact handler/pin backup hashes and source identities. Its inverse is
the same maintained command with `--current-harness --rollback "$OLD_JOURNAL_SHA"`
and `--rollback-pin "$OLD_PIN_SHA_OR_ABSENT"`, plus
`--expected-current-sha256 "$NEW_JOURNAL_SHA"`; preview before apply. Do not reset
its lock or retained logging state.

The engineering handler has an independent historical identity. Before updating
it, copy its actual bytes/metadata to the protected operator backup and record
the hash. Compare the candidate file
`deployment/goal91/engineering-shell.py` against that same source lock. Replace
only the admitted root-owned engineering handler, with root:root 0555, after the
actual current hash matches the recorded old hash. Keep the engineering container
unchanged. Its inverse restores that exact protected file, after verifying the
currently installed new hash. Do not substitute the historical browser handler
for the engineering handler. Host source generation/capture binding preparation
also uses the existing source delivery owner; no native session is needed.

Place a candidate config at a root-owned non-writable regular path outside the
installed destination. It must name the actual prepared host source generation,
runtime, capture binding and controllers. Pick the admitted unprivileged Relay
account; its UID/GID own the private cache, independently of the demo UID33 and
engineering UID10001.

```sh
python3 "$BUNDLE/deployment/relay/install-local.py" \
  --bundle "$BUNDLE" --lock "$PIN" --config "$CANDIDATE_CONFIG" \
  --relay-user "$RELAY_USER" --receipt "$PRIVATE_STATE/install-receipt.json"
```

Review the preview's exact paths, modes, hashes, user and cache. On approved
application, run the same command as root with `--apply`. The helper stores the
root0600 inverse receipt before changing files. It prepares the cache first,
publishes SAME5 files/config, and installs only this task's sudoers file last.
The exact generated rule is:

```sudoers
RELAY_USER ALL=(root) NOPASSWD: NOSETENV: /usr/local/libexec/one-c-harness-local-controller ""
```

The real account replaces `RELAY_USER`; `""` requires no command arguments.
`visudo -cf` validates candidate syntax before any installation. Afterwards,
read back owner/mode/hash and inspect exact admission using
`sudo -n -l -U "$RELAY_USER" -- /usr/local/libexec/one-c-harness-local-controller`.
That listing is an access check, not product acceptance. No arbitrary command,
Python/shell grant, preserved environment or Docker socket is introduced.

Local-delivery rollback also previews by default:

```sh
python3 "$BUNDLE/deployment/relay/install-local.py" \
  --rollback --receipt "$PRIVATE_STATE/install-receipt.json"
```

After calls finish and Hermes selects the previous transport, apply that inverse
as root with `--apply`. It refuses unexpected edits, revokes only its sudoers
entry, restores the recorded files and then any previous rule. It retains the
cache/results, evidence receipt and nonempty directories. A partially completed
installation can use the same inverse receipt; inspect the failure first.
Controller/source rollback is a separate step using the preserved identities
above. No package installation, service restart or business-data operation is
part of either helper command.

The exporter role supplies absolute capture-command, binding and work-root
locators. The existing exporter chooses its capture backend before checking
direct `IBCMD`/`JOURNAL` settings, so those direct-source variables are unnecessary.
The companion runs with its fixed private cache as cwd; an incoming Relay cwd
of `/` cannot move selection caches into the root filesystem.
