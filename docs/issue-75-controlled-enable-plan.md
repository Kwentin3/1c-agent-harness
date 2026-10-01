# Issue #75 — controlled enablement and rollback record

> Status: **enabled and accepted for the bounded training slice**. This is the
> existing installation, compatible-update, disable, and rollback record; it
> does not establish general production readiness or authorize broader changes.

## Chosen executor layout

The existing executor bind mount is the only selected persistent location:

```text
/workspace/1c-agent-harness/.local/issue75-companion/
├── source/                 # clean detached worktree at the approved PR #74 HEAD
└── bin/one-c-harness       # deployment-owned fixed launcher
```

This is not a new Harness, package manager, or service. `source/` is a
read-only-as-used exact source worktree and `bin/one-c-harness` is a tiny fixed
launcher that changes to that worktree and invokes its installed Python module.
It has no model-controlled paths or arguments. Task-local retained selections
remain inside the worktree's ignored `.local/runs/techlog-observations/` root,
where the companion already owns their one-hour expiry and fail-closed reading.

The launcher binds the observed source rather than changing the domain code:

```text
ONE_C_HARNESS_TECHLOG_ROOT=
  /workspace/1c-agent-harness/.local/issue75-techlog-canary/techlog-excp
ONE_C_HARNESS_TECHLOG_TIME_ZONE=UTC
```

The root contains three `26091815.log` files (47,170 bytes total), produced by
the isolated training-runtime run described in
[`issue-75-techlog-observations.md`](issue-75-techlog-observations.md). It is
an existing platform source, not a Harness receipt. The installed and accepted
runtime implementation is PR #74 revision
`7baa1ca47398e9979d66437daa951da019fb8bc7`, tree
`20862e49e83a3076d59e14e815a5f2b3e62bc869`.

### Why this is the minimal workable location

Direct executor evidence on 2026-09-18:

- `/workspace/1c-agent-harness` is an ext4 mount owned by `executor` and
  writable at its existing `.local/` directory;
- `/home/executor` is read-only;
- `/tmp` is writable but a `noexec` tmpfs and is therefore not a persistent
  product route;
- `/ssh-state` is persistent but owned by root with mode `0711`, so it is not
  a task storage location.

No mount, permission broadening, system package, platform, shared `logcfg.xml`,
CF, snapshot, live IB, or neighboring process needs to change. The executor
itself does **not** need recreation for this selected layout.

## Installation and compatible update procedure

Any installation or compatible update approval covers all steps below and the
rollback in the next section. Each step is bounded to the existing VPS Hermes
and executor.

1. **Executor preparation — executor/deployment owner.**
   Create the exact task-owned directory above; fetch and create a clean
   detached Git worktree at the stated commit; create the fixed launcher with
   mode `0755`. The launcher may use the executor's existing `/usr/bin/python3`
   and source tree only. It must not install Python or system packages, modify
   the canonical checkout, or put files in `/tmp` as a permanent route.
   Before use, verify HEAD, tree, clean worktree status, launcher hash, source
   log hash manifest, and that the launcher returns a bounded companion result.

2. **Hermes deployment configuration — Hermes deployment owner.**
   Keep the global Hermes terminal backend at its pre-enable `local` value and
   keep the original local working-directory policy. Copy the tracked
   `hermes-plugin/` closure from the same exact PR #74 revision into
   `$HERMES_HOME/plugins/one-c-harness`, enable only `one-c-harness` with
   `allow_tool_override: false`, and enable toolset `one_c` for the existing
   `cli` WebUI surface.

   The pinned Hermes version has no public per-call terminal-backend selector;
   its public schema exposes `command`, `workdir`, timeout, PTY, and lifecycle
   fields only. Therefore install the tracked deployment command
   `hermes-plugin/deployment/one-c-harness` in the Hermes-managed
   `$HERMES_HOME/bin` directory and addresses it through that profile-scoped
   environment variable rather than relying on the local terminal's sanitized
   subprocess `PATH`. The plugin invokes only that fixed command. The
   deployment command
   validates the base64 token, reuses the existing `TERMINAL_SSH_*` identity,
   requires the standard pinned `known_hosts`, and invokes the fixed executor
   launcher with `BatchMode=yes`, `IdentitiesOnly=yes`, and
   `StrictHostKeyChecking=yes`. It accepts no model-controlled host, user, port,
   key, path, or remote command. SSH settings and executor paths remain outside
   the plugin/domain adapter; no credential is copied to the executor.

   Do not switch the global terminal backend to SSH for this feature. That would
   redirect unrelated terminal/file/code tools and is outside the bounded
   integration contract.

3. **Controlled Gateway restart — Hermes deployment owner.**
   Only after executor and terminal admission succeed: take a config/plugin
   backup, restart the process that owns the existing WebUI agent tool registry
   through its normal supervisor, and verify replacement process/health. A
   Gateway restart is required because this is a Python/runtime plugin. It does
   not recreate the executor. Open a new WebUI chat afterwards because the old
   chat keeps its frozen tool schema.

For a compatible source update, fetch the approved immutable revision into a
clean detached source worktree, verify its exact HEAD/tree and focused tests,
then switch the fixed launcher/plugin closure as one bounded deployment change.
Keep the prior immutable revision available for the rollback below. The accepted
update from `c31c399` to `7baa1ca` reused the existing registered plugin route;
it did not require another Gateway restart.

## Accepted installed state

- revision `7baa1ca47398e9979d66437daa951da019fb8bc7` was clean locally and
  on the executor worktree when accepted;
- exact-head CI passed on Python 3.9 and 3.12, including 258 repository tests
  and the JSON smoke check;
- an ordinary Hermes request used the registered `one_c_observe` and
  `one_c_expand_observation` tools: 44 EXCP records were observed, `limit=5`
  displayed five groups with `groupsTruncated=true`, and the selected repeated
  group returned all four records with `truncated=false`;
- the ordinary local terminal and existing GitHub read access remained usable;
- companion/plugin byte and capability identity contract, bounded JSON
  operations, terminal-only plugin dispatch, safe `Descr` redaction, stable
  retained expansion, source unavailable/empty/partial distinctions, and
  paging regressions are covered by focused tests.

## Accepted route and result

The accepted controlled transaction was checked in a new chat with an ordinary
request equivalent to:

> «Посмотри ошибки 1С за этот интервал. Дай короткую сводку, раскрой
> интересующую группу и объясни по содержанию записей, что произошло и что
> имеет смысл проверить дальше».

The required route is:

```text
Hermes → registered one_c_observe → public local terminal
→ fixed Hermes deployment command → strict pinned OpenSSH
→ executor launcher → companion → platform technological journal → summary
→ registered one_c_expand_observation → retained original selection
```

The ordinary-user acceptance is recorded in
[issue #75 comment 5759499600](https://github.com/Kwentin3/1c-agent-harness/issues/75#issuecomment-5759499600).
The selected group exposed the safe message
`DatabaseException8: Database file is missing '<redacted:path>'`. This proves
that the platform reported a missing database file in four matching records;
it does not identify the hidden path/file, initiating component or operation,
or root cause. The result is one repeated group, not four independently
diagnosed failures, and the truncated group list means other groups were not
accepted individually. No new native 1C process was launched for acceptance.

## Independent rollback

Rollback does not invoke the new plugin:

1. Disable `one-c-harness` and the `one_c` toolset in the existing Hermes
   configuration, then restart the owning WebUI agent process through the same
   supervisor and verify a new chat no longer receives those tools.
2. Restore the pre-enable config/plugin backup if needed; existing coding tools
   remain configured exactly as before.
3. Remove only `$HERMES_HOME/plugins/one-c-harness`, the installed
   `$HERMES_HOME/bin/one-c-harness` deployment command, and the
   task-owned `/workspace/1c-agent-harness/.local/issue75-companion/` directory
   after no owned process remains. Do not remove the platform-log source or any
   other `.local/` assets.
4. Verify the original executor checkout/source logs and the host-key pin are
   unchanged, and that old tools still work.

A failure in terminal admission, plugin discovery, restart health, or the first
real tool call triggers this rollback. It is not a reason to disable host-key
verification, accept a changed/unknown executor key, or silently fall back to
manual SSH.
