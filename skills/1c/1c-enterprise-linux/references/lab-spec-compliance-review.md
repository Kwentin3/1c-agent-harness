# Documentation-only lab closure review

Use this checklist when reviewing whether a native 1C Linux lab can close an issue without adding a custom harness.

## Review from the staged artifact, not the working tree

1. Read the issue body as the result contract and the repository-wide agent rules.
2. Inspect the staged file list and staged diff; do not treat untracked evidence or local machine state as part of the deliverable.
3. Verify local evidence only to audit factual claims. Keep the distinction clear: a successful local run does not make an incomplete runbook reproducible.
4. Check that no wrapper, parser, supervisor, installer framework, test harness, or copied third-party code was added unless the issue proved it necessary.

## Closure gates

A documentation-only change may pass only when it records all issue-required facts and makes the intended scope reproducible:

- exact Workspace/Git root, actual Hermes terminal backend, OS, architecture, effective installation privileges, and persistence model;
- official platform version, acquisition page, installer identity/hash, license/download precondition, and training-edition limits;
- fixture release/asset identity and hash;
- source-to-working-copy boundary plus before/after endpoint hashes;
- exact native commands and a fresh output directory that prove a full, non-incremental dump;
- both shell process exit status and 1C `/DumpResult` for create/load/dump;
- structural checks (`Configuration.xml`, `ConfigDumpInfo.xml`, multiple metadata domains, BSL files), diagnostics, and repeat-dump comparison;
- snapshot root, artifact type/format, platform/command, UTC creation timestamp, content identifier, completeness/error statement, and log/manifest locations;
- pinned external-tool commit, isolation method, license, tested commands, and independent comparison against native output;
- one explicit absolute handoff path for the next stage;
- ignored local artifacts and a staged set containing only intended bootstrap/verification documentation or materials.

## Reproducibility versus an already prepared machine

A smoke sequence that works only after unspecified preparation is not a clean bootstrap recipe. If the contract promises reproduction from an empty or clean Workspace, document enough to rebuild the prerequisites without hidden state:

- exact dependency packages/artifacts and versions or hashes;
- acquisition and extraction layout;
- creation of required runtime configuration such as `fonts.conf`;
- Xvfb/XKB requirements and ownership boundary;
- safe vendor installer staging/verification/relocation steps;
- readiness checks for binary presence, library resolution, fonts, XKB, and platform startup.

This does not require inventing a custom installer. Native package/vendor commands and a bounded administrative procedure are preferable. If exact privileged commands cannot safely be generic, clearly narrow the reproducibility claim to the prepared Workspace and mark clean rebuild as unproven; do not claim full issue closure.

## Evidence wording

- A calendar date is not necessarily the required snapshot creation timestamp; record an unambiguous timezone, preferably UTC.
- `/DumpResult=0` is not the shell process exit code. Capture and report both.
- File counts and marker files prove nonempty expected structure for the fixture, not semantic completeness for arbitrary configurations.
- Matching endpoint hashes prove observed equality at checkpoints, not race-free immutability against a hostile same-uid process.
- A read-only Unix mode is workflow hardening, not immutable storage.

## Copy-paste and privileged-command safety

Audit every command as a fresh-shell paste, not merely as prose:

- require `set -euo pipefail` (or equivalent explicit status handling) in each independently pasted block, and recreate arrays, functions, and environment needed by later blocks;
- distinguish assertions from diagnostics: hashes, `/DumpResult`, process exits, `ldd`, package integrity, counts, and readiness markers must affect exit status rather than only print;
- refuse pre-existing output and publication destinations, including dangling symlinks; for downloads, prefer a fresh temporary file, verify its digest, then publish without clobbering a previously verified artifact;
- deterministic recipe-owned files may be rewritten only when the runbook explicitly requires a new/clean lab root; otherwise guard them like other destinations;
- keep root operations in random root-owned staging, verify exact installer/package hashes there, avoid package maintainer scripts when extraction suffices, publish only the required absent paths, and constrain cleanup to the known staging root;
- remember that a user-space APT root can still inherit `/etc/apt/apt.conf` and `apt.conf.d` hooks. Either isolate those config paths or explicitly neutralize relevant hooks, and test the exact documented APT options against the declared base image;
- pin signed repository snapshots and exact package versions. If package membership or extraction order changes, the previous clean extraction/smoke no longer proves the new list: rebuild in the published order, rerun `ldd`, readiness, and the full 1C smoke before updating evidence wording.

Within an explicitly trusted single-user clean-container model, do not demand protection from a simultaneous malicious same-uid actor. Still reject ordinary accidental clobbering and hidden host/container configuration dependencies.

## Staged-artifact freshness

After any mid-review edit or user steering, re-read the Git index before deciding:

1. Run `git status --short` and verify the intended files are staged with no `AM` or unstaged drift.
2. Re-read the current staged blobs (`git show :path`) rather than relying on earlier tool output or the working tree.
3. Re-run staged syntax, count, and hash checks affected by the edit.
4. Immediately before the verdict, re-check the staged diff or its digest so a concurrent update cannot make the review stale.
5. If an asynchronous verdict arrives after the commit was created, bind the verdict to the artifact before reporting success: require a clean worktree, inspect the committed path list, run `git show --check`, and confirm that no post-review edit or amend changed the reviewed tree. Never describe a late review as approving the commit solely because its prose names the same files.

A user saying that a file was staged is not evidence that the index already contains it; trust the live index. Conversely, if staging occurs concurrently after an earlier `AM` observation, refresh rather than failing on stale state. A successful late review is useful only after this review-to-commit binding check.

## Post-merge read-only audit

For an independent audit after merge, bind every conclusion to the merged Git artifact rather than the PR narrative:

1. Read the live issue thread and PR metadata through `gh`; treat the issue as the acceptance contract and the PR body only as a list of claims to verify. Include final state, files, comments, reviews, checks, PR head SHA, and merge SHA.
2. Confirm current `HEAD`, the merge commit, committed path set, `git show --check`, and a clean worktree. For a squash merge, do **not** expect the PR head to be a parent of the merge commit: compare `git rev-parse <head>^{tree}` with `git rev-parse <merge>^{tree}`. Equal trees bind the reviewed head to the merged artifact.
3. Confirm the exact PR head SHA is recorded in the PR report. If reporting metadata is missing after merge, add a factual verification comment; this can repair the report but cannot repair an incomplete merged deliverable.
4. Enumerate the committed tree and changed paths. Check explicitly that `.local/`, installers, fixtures, infobases, snapshots, logs, external checkouts, caches, credentials, and license-bearing artifacts are not tracked.
5. Use ignored `.local/` only as supporting evidence: recompute fixture/manifest hashes, file and BSL counts, required metadata domains, manifest-to-snapshot equality, write bits, pinned external-tool commit, and recorded `/DumpResult` values without treating those files as Git deliverables.
6. If this reviewer owns runtime verification, start from the correct Workspace/Git root in a new session, rerun readiness, create a fresh run directory and infobase, and require fresh process exits plus fresh `/DumpResult` values. Compare the recomputed manifest byte-for-byte with the canonical handoff; do not trust only stored counts or `snapshot.json`.
7. Re-run the pinned external adapter against that fresh infobase and compare its full manifest with the direct native dump. Run `cf-info` on the fresh snapshot and compare its key fields and object count independently with `Configuration.xml`.
8. If another reviewer owns an expensive native smoke, do not duplicate it. State that limitation explicitly. If local evidence has `/DumpResult` but no persisted shell exit statuses, distinguish “documented exit-code claim” from “independently re-derived exit code”.
9. Sweep README, agent rules, roadmap, architecture, and research for current-stage contradictions. Historical stage descriptions are not contradictions when a separate current-status marker is clear.
10. Recheck Git hygiene and live GitHub state immediately before the verdict. An empty GitHub checks list means CI was not configured; report local execution and independent review as such, never as green CI.
11. Return a compact machine-readable verdict (`passed`, `blockers`, `warnings`, `evidence`) and state whether any external comment or local evidence record was created.

## Contradiction sweep

Before passing, search all project documentation for stale state markers and recommendations:

- README current stage/status versus the newly completed stage and handoff;
- repository rules naming the current mission;
- roadmap stage/gate wording;
- research freshness dates and recommendations versus newly verified candidates;
- architecture snapshot fields versus the report's provenance fields.

Treat a post-merge README that still says the completed issue is current as a stale contradiction. Old research dates or candidate lists are usually nonblocking only when they are explicitly historical and do not conflict with the selected result.

## Decision rule

Set the review verdict to failed for missing issue-required provenance, hidden bootstrap state under a clean-rebuild promise, incorrect stage handoff, or contradictory current-state contracts. Keep optional hardening and editorial freshness in suggestions. An empty security-concerns list is appropriate when the documented trusted single-user threat model is honest and no new secret-bearing or privileged artifact is staged.
