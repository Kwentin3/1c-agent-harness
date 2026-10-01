# Terminal-bound executor companion

Use this pattern when a 1C runtime must remain on a remote executor but Hermes needs a repeatable, auditable tool surface. It is a source-and-local-test pattern; do not treat it as permission to deploy or to claim a remote canary passed.

## Boundary

```text
Hermes plugin → public PluginContext.dispatch_tool("terminal", ...)
              → selected terminal backend and its cwd
              → installed executor companion
              → existing canonical Harness lifecycle
```

The plugin must not contain SSH, host keys, private-key paths, remote paths, credentials, or executor discovery. The companion must not derive a workspace from plugin state: its sole project-root authority is the terminal process `cwd`.

## Minimal companion contract

- Install one package beside the executor runtime from an immutable revision.
- Expose one stdin/stdout JSON envelope with closed `schemaVersion`, `operation`, and `arguments` keys.
- Keep operations narrow: target `open`, admitted-snapshot `narrow`, and canonical `verify`.
- Return one bounded JSON object; reject duplicate JSON keys, unknown fields, absolute/traversal task paths, and an unadmitted SnapshotRef.
- Keep the data-only SnapshotRef byte/field exact. Put companion version in an outer response envelope, not inside SnapshotRef, because admission equality must remain exact.
- The plugin and companion carry the same capability version; plugin blocks a mismatch before returning any purported success.

## Package existing harness code rather than copying it

When the canonical harness consists of executable scripts, package that source directory directly (for example, a package-dir mapping) and add relative-import fallbacks so existing `python scripts/...` entrypoints still work. The package route should invoke its canonical lifecycle module, not copy or reimplement it in a business workspace.

If the lifecycle used a fixed workspace-local 1C platform path, change it to consume the established executor-owned runtime locator. Validate closed plan inputs first, then load the runtime contract before building native argv. Business workspaces may carry the minimal local locator if that is the existing executor contract, but must not carry the runtime distribution, Harness checkout, or transport credentials.

## Required local evidence before deployment

1. RED/GREEN tests cover `open → exact SnapshotRef → narrow`, raw-path rejection, version mismatch, and plugin dispatch only to `terminal`.
2. A native-plan regression uses an executor runtime outside the business workspace and proves no workspace-local platform tree is required.
3. Build/install the package into a disposable target or venv and execute its console entrypoint. A correct typed blocker is a valid source-only smoke when the local workspace lacks a target.
4. Run the full repository suite and syntax/diff checks.
5. Independently review the frozen source patch. Review neither authorizes deployment nor substitutes for an E2E executor canary.

## Deployment admission remains separate

Before a real canary, separately approve: strict pinned host-key behavior in the Hermes terminal backend, the selected remote workspace contract, installation of the exact companion revision near the executor, plugin activation, and a harmless `open → narrow` route. Stop before deployment/restart/merge unless the owner explicitly authorizes that boundary.
