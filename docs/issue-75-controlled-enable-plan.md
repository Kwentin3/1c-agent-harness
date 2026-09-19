# Issue #75 — controlled enablement plan

> Status: **candidate only**. This document prepares one owner approval. It does
> not authorize activation of the Hermes plugin, a Gateway restart, a terminal
> backend change, executor recreation, or a native 1C run.

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

The approved launcher will bind the observed source rather than changing the
domain code:

```text
ONE_C_HARNESS_TECHLOG_ROOT=
  /workspace/1c-agent-harness/.local/issue75-techlog-canary/techlog-excp
ONE_C_HARNESS_TECHLOG_TIME_ZONE=UTC
```

The root contains three `26091815.log` files (47,170 bytes total), produced by
the isolated training-runtime run described in
[`issue-75-techlog-observations.md`](issue-75-techlog-observations.md). It is
an existing platform source, not a Harness receipt. The exact source revision
for this candidate is PR #74 head
`4d9ddc766b298e3104d03c9648ac4857654b840b`, tree
`beb6f5ae30e0b396ded9fda18bf6794f617a2d63`.

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

## One owner-approved enablement transaction

The owner approval must cover all steps below and the rollback in the next
section. Each step is bounded to the existing VPS Hermes and executor.

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

## What is already proven without enablement

- PR #74 head is clean locally and on the temporary executor worktree;
- 251 repository tests passed on the candidate before this plan; focused
  observation/companion/plugin tests also pass;
- exact-head CI is green on Python 3.9 and 3.12;
- the source → companion lower route has read real platform logs and produced
  bounded selection/expansion; it is explicitly **not** Hermes E2E;
- companion/plugin byte and capability identity contract, bounded JSON
  operations, terminal-only plugin dispatch, safe `Descr` redaction, stable
  retained expansion, source unavailable/empty/partial distinctions, and
  paging regressions are covered by focused tests.

## Post-enable acceptance and refusal checks

After the controlled transaction, in one new chat the agent will receive only
an ordinary request such as:

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

Acceptance observes a real group and a page from it, confirms the source hash
manifest did not change, and checks no owned 1C/Xvfb process remains. It must
say that technical exception token/repetition is evidence of a registered
exception, not a root-cause proof; redacted `Descr` fingerprints alone are not
an explanation. It also records one safe refusal path (unavailable source or
expired selection) and confirms existing `open → narrow → verify` tooling is
still registered and unaffected. No new native 1C launch is required unless the
existing source cannot answer the ordinary request.

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
