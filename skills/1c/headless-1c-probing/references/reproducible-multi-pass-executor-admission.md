# Reproducible multi-pass executor admission

Use this pattern when a headless native proof must produce two or more clean PASS runs on one exact Git candidate, while runtime binaries and canonical targets live only in an executor-local `.local/` tree.

## Why this matters

A Git worktree contains tracked files, not executor-local platform binaries, libraries, CF files, snapshots, manifests, or caches. A fresh detached worktree can therefore be Git-correct but native-incomplete. Treat that as admission state before any platform process starts, not as a product attempt.

## Admission pattern

1. Verify the executor base first:
   - exact candidate commit and tree exist;
   - project target verifier reports `ready` with exact CF/manifest/file-count identities;
   - runtime binary has the expected SHA-256;
   - required `xvfb-run`, Xvfb, xauth, xkbcomp, fonts and shared libraries exist, and `ldd` has no `not found` entries;
   - disk bytes/inodes are sufficient;
   - no owned or competing 1C/Xvfb processes exist.
2. Create a new task-owned parent under `.local/`; refuse collisions rather than reusing an old lane.
3. Create one detached Git worktree per clean lane at the same exact commit/tree.
4. Populate only executor-local prerequisites:
   - copy the canonical CF, snapshot and manifest into each lane's ignored `.local/`, preserving bytes and read-only modes;
   - reuse the already installed immutable platform through an executor-local link or equivalent narrow mount, when the runner accepts that layout;
   - never copy runtime state into tracked Git or alter the executor base distribution.
5. In every lane, rerun the project target verifier, runtime hash check and shared-library check. Require clean Git and absent prepared/request/run roots before admitting native execution.
6. Run lanes sequentially through the one public front door. A lane is a PASS only when the runner reports terminal completion, the front door reports strict validation, the response token is server-generated and differs from the nonce, and cleanup succeeds.
7. Before admitting the next lane, independently revalidate copied raw client/server receipts, verify the target again, verify the prepared and heavy runtime roots are absent, and verify no platform processes remain.

## Final continuity audit

Freeze one compact machine-readable audit containing, for each lane:

- `startedUtc`, `endedUtc`, and wall-clock duration, so sequential non-overlap is directly checkable;
- exact HEAD/TREE and clean status;
- request identity and SHA-256;
- raw front-door result hash/status;
- runner status and duration;
- client/server receipt hashes and independently revalidated response;
- prepared/heavy-root absence and process absence;
- target status, manifest identity and file count.

Also prove identities differ across lanes and run the exact candidate's non-native negative protocol suite covering missing server witness, foreign/stale identity, extra/partial records, nonce echo or client-authored token, mutated request fields, and client-only failure claims. Positive receipts alone prove the observed happy paths; the negative suite proves the validator rejects bypass shapes without spending another native budget.

## Review-packet pitfall

Do not omit retained UTC timestamps or negative-validator evidence from a completion review packet. Their absence can make valid sequential runs or fail-closed behavior look unproven even when the underlying evidence exists. Include the concrete timestamps and named passing negative tests in the first frozen packet; do not create a reviewer retry merely to repair an avoidable packet omission.

## Boundaries

- This pattern repairs executor admission only; it does not authorize product-code changes after a real native failure.
- Do not use best-of-N, silently retry a failed native lane, or relabel precheck failures as product outcomes.
- Preserve small logs, receipts, results and hashes; remove only declared task-owned heavy roots.
- Same-UID file witnesses remain trusted-lab evidence, not cryptographic proof against a malicious same-UID writer.
