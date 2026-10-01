# Frozen multi-arm context-front-door comparison

Use this pattern when the question is **which read-only investigation front door helps a 1C change-planning task**, rather than whether a proposed BSL patch is already correct.

## Purpose and boundary

Compare a small set of materially different context mechanisms (for example direct source navigation, a static index, or a narrowly admitted external structural skill) without letting one arm's discoveries become another arm's prompt context. The outcome is a context-pass winner; it is **not** authorization for a production edit or native run.

## Staged protocol

1. **Establish immutable input first.** Bind the Git commit, CF hash when applicable, snapshot manifest hash, regular-file count, and no-symlink condition. Run the project front door before and after every arm.
2. **Research candidates from primary sources.** Record version/commit, licence, release-asset hash, expected runtime and intended commands. Do not call a repository name itself evidence that the candidate fits.
3. **Run admission separately from scoring.** Verify the exact binary or script starts in a harmless help/status mode, and verify its runtime/dependency boundary. If it cannot be launched under the pinned admission set, exclude it *before* the task is frozen; do not silently add a new dependency or substitute a different tool mid-round.
4. **Isolate mutable indexes.** Many indexers create state beside their input. Never point them at the canonical snapshot. Make a task-owned full byte-copy, verify it against the same manifest before indexing, and account for copy/index time plus storage separately. Do not use hardlinks when source integrity checks include link count or immutable-file semantics.
5. **Freeze the experiment before any scored model starts.** Publish one exact task, allowed context per arm, model/client, time budget, source-write prohibition, telemetry fields, product gates, and tie-breakers. Hash the frozen protocol and place identical bytes in the executor's declared task root.
6. **Use fresh isolated executors.** Give each only the task, static-input locator, and its explicit allowed front door. Deny issue/PR history, prior experiment artifacts, network search, GUI, unlisted skills, and inter-arm outputs. Require every material conclusion to cite an actual source locator, not an index result alone.
7. **Evaluate only after all arms end.** Build the reference answer independently after the context passes. Treat an unavailable telemetry field as `not available`, not as zero cost. A timeout, source mutation, missing required result, or unsupported claim is a recorded failure, never a quiet fallback.
8. **Choose one winner with gates first.** Correct execution locator/mechanism, distinguishing semantic branches, minimality/preservation, acceptance cases, and explicit unknowns outrank convenience. Use task-time/tool cost and then separately recorded setup/storage cost only as tie-breakers. Native RED/GREEN is a later, winner-only phase with its own contract.

## Candidate admission checklist

For every admitted arm retain a task-owned receipt containing:

- source URL/release tag or commit; exact licence evidence;
- artifact SHA-256 and actual command path;
- harmless launch result (`--help`, `status`, or equivalent);
- required runtime/dependency versions and hashes;
- index copy identity proof (if applicable), index statistics and logical bytes;
- pre/post available bytes and inodes; named task-owned roots.

## Evidence shape

The public freeze should make the task and fairness constraints reviewable, while avoiding the private expected answer. The per-arm evidence should retain the exact final structured response, observed pre/post integrity checks, timing, command/tool summary, and any error/retry. Keep task downloads, indexes, copies and temporary probes exclusively in a declared `.local/<issue-root>/`; do not clean any artifact until the evidence handoff says which named roots are disposable.

## Pitfalls

- A structural index accelerates navigation but does not prove business semantics; require the arm to inspect and cite the underlying XML/BSL.
- A prebuilt index has non-zero cold cost even if the model sees it instantly. Report its build cost apart from task time.
- Do not rescue a failed arm with ad-hoc context, an extra package, or the previous arm's locator after freeze. Record the failure and preserve fairness.
- Compare the **full** required Git SHA, not only a shared prefix. A successful project/snapshot readiness check does not cure a Git-head mismatch: preserve the read-only evidence if useful, but mark frozen-head compliance blocked and report the observed SHA separately.
- Do not turn a context-pass plan into a source patch before the native experiment has an explicit write-safety contract.
