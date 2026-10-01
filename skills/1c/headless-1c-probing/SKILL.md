---
name: headless-1c-probing
description: Use when proving a headless 1C client-server route safely.
version: 1.0.1
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [1c, headless, read-only, evidence, server-witness]
    related_skills: [1c-enterprise-linux]
---

# Headless 1C probing

## When to Use

Use when a headless 1C investigation must prove that a client entry crossed into server code and returned a current response, while preserving canonical inputs and avoiding GUI/business writes.

Use this skill to design, execute, and assess a bounded **read-only or disposable** 1C client-to-server probe. It is for proving transport/observability, not for validating a business change.

## Outcome contract

A successful probe must prove one ordered chain:

1. A fresh immutable request is created (`runId`, `caseId`, `nonce`; UUIDv4 where applicable).
2. Client entry writes a receipt with the request identity and pre-server milestones.
3. A server-call-only module writes an independent server receipt after server entry.
4. The server returns a newly generated token to the client.
5. The client appends completion only after the synchronous call returns.
6. A host-side validator reads both raw receipts, requires identity equality and the same token, and rejects a token equal to the request nonce.

A lone client receipt, a missing/foreign server receipt, an unstable receipt, or a runner timeout is never success.

## Safe execution sequence

1. **Discover and admit the actual executor first.** Check the active Hermes terminal backend, then the exact platform version, snapshot/manifest identity, workspace state, and no live 1C process on the execution host. Before interpreting an unconfigured backend as the absence of a remote executor, consult current-session history and deployment-owned credential references for an established direct SSH route; verify that exact route read-only, with its pinned host-key policy. Do not substitute an AgentBridge device inventory for a direct SSH route. Prefer an already prepared remote executor over local installation. Do not print private-key contents; credential filenames and modes are sufficient for discovery. A device-context inventory is not an execution route: require an operational status and an exposed handoff/command boundary, and require a configured remote destination before treating it as an executor. Distinguish a proven direct SSH route from a Hermes-selected remote terminal boundary: the former establishes topology, but the latter is required before a plugin may claim it operates through the active Hermes workspace/backend. If the public backend cannot preserve the established route's host-key policy or workspace binding, report that exact upstream-compatible seam rather than recreating SSH inside the plugin. If the topology gate fails, report `context blocked` before materialising a target, copying canonical inputs to the VPS, or building a second runner; it consumes no native budget. Use `references/remote-executor-topology.md` for the complete evidence and decision rule. For unit tests that execute temporary fake helpers, inspect mount flags first: if `/tmp` is `noexec`, set `TMPDIR` to a fresh task-owned executable directory under the repository's `.local/` area and remove that directory in `finally`. This test-harness workaround is not a native invocation or a native-budget use.
2. **Respect an owner-bounded final correction.** When an owner narrows an open headless-1C PR to one lifecycle fix, first reproduce it through the public front door. If a primitive has claimed a disposable tree but request/evidence writing is interrupted, clean only that owned tree. Re-raise `KeyboardInterrupt` and `SystemExit` unchanged after successful cleanup; if cleanup also fails, report both exception classes. Keep the patch to that boundary and its direct regressions—do not add parsers, generic interfaces, transport arms, native invocations, or new reviewer cycles when forbidden. Commit first, then update the PR body from the exact published HEAD/tree and actual test/CI counts; helper readiness never becomes an unrun native or business claim.
3. **Treat the latest owner comment as the active contract.** Before resuming an Issue after a long run, compaction, or delayed delivery, re-read the newest relevant owner decision rather than treating an earlier report, checkpoint, or assistant summary as current instructions. If the owner explicitly supersedes a tracked report or README promotion, remove it in an ordinary follow-up commit—never rewrite history—and preserve the designated GitHub receipt as the canonical evidence. Publish exactly the requested communication pattern (for example one pre-run checkpoint and one terminal receipt); do not add review packets, proposal documents, or extra comments merely because they are technically informative.
4. **Freeze one bounded request and scope.** Name the disposable work-copy and evidence locations; list the only allowed source paths and forbidden business calls/writes. One native invocation per viable arm means static preparation failures must be recorded separately and must not be disguised as runtime attempts.
4. **Prepare a new writable work copy.** Snapshots often retain read-only mode bits. Make only the copy owner-writable; never chmod or alter the canonical snapshot. Preserve a rejected preparation rather than mutating it in place.
5. **Inject the smallest probe.** Prefix the existing early client entry and return before normal startup. Do not reconstruct or retype unchanged standard code. Put the server writer in a module whose server-call metadata is verified from the immutable source.
6. **Statically audit before 1C starts.** Verify the exact changed-path closure, no dynamic-code primitive or business-object operation in the generated probe, current request literals, and expected work-copy hash.
7. **Prove the public adapter→runner handoff without launching 1C.** Before a scored comparison is frozen, trace the adapter's exact generated command into the runner's input parser. Test path shape and anchoring (for example repository-relative versus absolute inputs), declared receipt roots, and required markers against the runner's actual admission rules. Two isolated unit suites can both pass while their CLI boundary rejects the adapter's generated argument.

   For a real-seam regression, run `frontdoor.run` against a byte-identical `native_cycle.py` copied into a fresh temporary repository; do not stub the runner. Provide a task-owned executable fake `xvfb-run` that records its argv and exits before it could `exec` a deliberately non-executable placeholder `1cv8t`. Assert that the runner moved past `inputTree` admission (for example, `create_failed` at the first batch boundary), records the expected repository-relative `.local/prepared/...` source path, records the blocked `CREATEINFOBASE` argv, never executes the placeholder, and cleans the prepared tree. On the unfixed boundary the same test must RED with the runner's real `precheck_failed` path error. This technique proves the cross-script contract without consuming a 1C budget.

   This preflight must not create a platform process; retain its result with the freeze. If it fails, correct or re-freeze before the first scored attempt rather than relabelling it as a 1C runtime outcome.

   **Bind completion literally before a native budget.** The caller-supplied runner marker must equal the complete final physical receipt record, including type fields when the receipt grammar uses them. Test this direct producer→adapter→runner boundary; a protocol validator may correctly accept a typed final record while a generic runner times out waiting for a shortened marker. Keep ownership narrow: the issue-specific front door chooses its one literal from its receipt template; the generic runner observes that one supplied literal and must not learn the issue grammar or accept alternate completions. A post-timeout host-side validation of files is evidence for diagnosis, never a retroactive runner PASS.
8. **Review concrete artifacts, not file references.** Give reviewers the exact generated BSL and frozen contract. Independently check any disputed dialect/syntax claim against the target's immutable source or official versioned documentation; do not choose by reviewer vote.
9. **Run once through the existing lifecycle runner.** Bound runtime timeout, retain raw logs/receipts/result, and require runner cleanup/process containment.
10. **Validate after the runner returns.** Run the portable validator against copied raw receipt bytes, then re-check canonical identity and absence of owned platform processes. Record platform-level success separately from protocol-level PASS.

## Terminal-bound executor companion

When a remote executor must remain remote but needs a reusable Hermes surface, use the public terminal boundary rather than direct SSH in a plugin. The plugin must be a thin closed-JSON adapter that calls `PluginContext.dispatch_tool("terminal", ...)`; the installed companion takes its project root from terminal `cwd`, accepts only admitted SnapshotRef data, and calls the canonical Harness lifecycle. Pin plugin and companion to one immutable revision and fail closed on version mismatch. This is source-only work until strict terminal host identity, selected remote workspace, companion installation, plugin activation, and a harmless `open → narrow` canary are separately admitted. See [terminal-bound-executor-companion.md](references/terminal-bound-executor-companion.md).

## Evidence and limitations

- Record request, exact source hashes, runner result, both receipt hashes, validator verdict, cleanup/process check, and canonical post-check.
- A same-UID file witness is trusted-lab evidence. It is not a cryptographic proof against a malicious same-UID writer.
- `create`/`load` success proves only lifecycle stages. It does not prove client entry or a server call.
- Never reuse a terminally failed runtime contract for a new business conclusion; create a new frozen contract.

## User communication

For this work, explain progress in plain Russian unless the user requests otherwise: say whether access is available, what the last bounded check proved, and what is being checked next. Do not lead with runner internals or long logs. Be explicit when a candidate is **context blocked** rather than failed.

## Reference

See `references/server-witness-contract.md` for a compact generic receipt grammar, preflight checklist, and pitfalls observed in a real disposable route proof.

For repeated clean PASS runs from detached Git worktrees on an executor whose runtime and canonical target live only under ignored `.local/`, use `references/reproducible-multi-pass-executor-admission.md`. It covers per-lane admission, safe reuse of an immutable installed runtime, sequential timestamp evidence, between-run cleanup gates, final continuity auditing, and the negative-validator evidence that should be included in the first completion-review packet.

When the coordinating session or SSH client disappears while an admitted native run may still be alive, read `references/interrupted-native-run-continuation.md`. It explains how to preserve the in-flight attempt, distinguish coordinator interruption from the native result, finish only the skipped mechanical evidence tail, and add explicit request/receipt identities in new clean acceptance lanes without rewriting earlier RED/GREEN history.
